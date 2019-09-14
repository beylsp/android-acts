#!/usr/bin/env python3
#
#   Copyright 2019 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the 'License');
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an 'AS IS' BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os

import tzlocal
import yaml
from acts.keys import Config
from acts.test_utils.instrumentation import app_installer
from acts.test_utils.instrumentation.adb_command_types import DeviceGServices
from acts.test_utils.instrumentation.adb_command_types import DeviceSetting
from acts.test_utils.instrumentation.adb_commands import common
from acts.test_utils.instrumentation.adb_commands import goog
from acts.test_utils.instrumentation.brightness import \
    get_brightness_for_200_nits
from acts.test_utils.instrumentation.config_wrapper import ConfigWrapper
from acts.test_utils.instrumentation.instrumentation_command_builder import \
    InstrumentationCommandBuilder

from acts import base_test

RESOLVE_FILE_MARKER = 'FILE'
FILE_NOT_FOUND = 'File is missing from ACTS config'
DEFAULT_INSTRUMENTATION_CONFIG_FILE = 'instrumentation_config.yaml'


class InstrumentationTestError(Exception):
    pass


class InstrumentationBaseTest(base_test.BaseTestClass):
    """Base class for tests based on am instrument."""

    def __init__(self, configs):
        """Initialize an InstrumentationBaseTest

        Args:
            configs: Dict representing the test configuration
        """
        super().__init__(configs)
        # Take instrumentation config path directly from ACTS config if found,
        # otherwise try to find the instrumentation config in the same directory
        # as the ACTS config
        instrumentation_config_path = ''
        if 'instrumentation_config' in self.user_params:
            instrumentation_config_path = (
                self.user_params['instrumentation_config'][0])
        elif Config.key_config_path.value in self.user_params:
            instrumentation_config_path = os.path.join(
                self.user_params[Config.key_config_path.value],
                DEFAULT_INSTRUMENTATION_CONFIG_FILE)
        self._instrumentation_config = None
        if os.path.exists(instrumentation_config_path):
            self._instrumentation_config = self._load_instrumentation_config(
                instrumentation_config_path)
        else:
            self.log.warning(
                'Instrumentation config file %s does not exist' %
                instrumentation_config_path)

    def _load_instrumentation_config(self, path):
        """Load the instrumentation config file into an
        InstrumentationConfigWrapper object.

        Args:
            path: Path to the instrumentation config file.

        Returns: The loaded instrumentation config as an
        InstrumentationConfigWrapper
        """
        try:
            with open(path, mode='r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f)
        except Exception as e:
            raise InstrumentationTestError(
                'Cannot open or parse instrumentation config file %s'
                % path) from e
        if not self._resolve_file_paths(config_dict):
            self.log.warning('File paths missing from instrumentation config.')

        # Write out a copy of the resolved instrumentation config
        with open(os.path.join(
                self.log_path, 'resolved_instrumentation_config.yaml'),
                  mode='w', encoding='utf-8') as f:
            yaml.safe_dump(config_dict, f)

        return ConfigWrapper(config_dict)

    def _resolve_file_paths(self, config):
        """Recursively resolve all 'FILE' markers found in the instrumentation
        config to their corresponding paths in the ACTS config, i.e. in
        self.user_params.

        Args:
            config: The instrumentation config to update

        Returns: True if all 'FILE' markers are resolved.
        """
        success = True
        for key, value in config.items():
            # Recursive call; resolve files in nested maps
            if isinstance(value, dict):
                success &= self._resolve_file_paths(value)
            # Replace file resolver markers with paths from ACTS config
            elif value == RESOLVE_FILE_MARKER:
                if key not in self.user_params:
                    success = False
                    config[key] = FILE_NOT_FOUND
                else:
                    config[key] = self.user_params[key]
        return success

    def setup_class(self):
        """Class setup"""
        self.ad_dut = self.android_devices[0]
        self.ad_apps = app_installer.AppInstaller(self.ad_dut)
        self._prepare_device()

    def teardown_class(self):
        """Class teardown"""
        self._cleanup_device()

    def _prepare_device(self):
        """Prepares the device for testing."""
        pass

    def _cleanup_device(self):
        """Clean up device after test completion."""
        pass

    def _get_controller_config(self, controller_name):
        """Get the controller config from the instrumentation config, at the
        level of the current test class or test case.

        Args:
            controller_name: Name of the controller config to fetch
        Returns: The controller config, as a ConfigWrapper
        """
        class_config = self._instrumentation_config.get_config(
            self.__class__.__name__)
        if self.current_test_name:
            # Return the testcase level config, used for setting up test
            case_config = class_config.get_config(self.current_test_name)
            return case_config.get_config(controller_name)
        else:
            # Merge the base and testclass level configs, used for setting up
            # class.
            merged_config = self._instrumentation_config.get_config(
                controller_name)
            merged_config.update(class_config.get_config(controller_name))
            return merged_config

    def adb_run(self, cmds):
        """Run the specified command, or list of commands, with the ADB shell.

        Args:
            cmds: A string or list of strings representing ADB shell command(s)

        Returns: dict mapping command to resulting stdout
        """
        if isinstance(cmds, str):
            cmds = [cmds]
        out = {}
        for cmd in cmds:
            out[cmd] = self.ad_dut.adb.shell(cmd)
        return out

    def adb_run_async(self, cmds):
        """Run the specified command, or list of commands, with the ADB shell.
        (async)

        Args:
            cmds: A string or list of strings representing ADB shell command(s)

        Returns: dict mapping command to resulting subprocess.Popen object
        """
        if isinstance(cmds, str):
            cmds = [cmds]
        procs = {}
        for cmd in cmds:
            procs[cmd] = self.ad_dut.adb.shell_nb(cmd)
        return procs

    # Basic setup methods

    def mode_airplane(self):
        """Mode for turning on airplane mode only."""
        self.log.info('Enabling airplane mode.')
        self.adb_run(common.airplane_mode.toggle(True))
        self.adb_run(common.auto_time.toggle(False))
        self.adb_run(common.auto_timezone.toggle(False))
        self.adb_run(common.location_gps.toggle(False))
        self.adb_run(common.location_network.toggle(False))
        self.adb_run(common.wifi.toggle(False))
        self.adb_run(common.bluetooth.toggle(False))

    def mode_wifi(self):
        """Mode for turning on airplane mode and wifi."""
        self.log.info('Enabling airplane mode and wifi.')
        self.adb_run(common.airplane_mode.toggle(True))
        self.adb_run(common.location_gps.toggle(False))
        self.adb_run(common.location_network.toggle(False))
        self.adb_run(common.wifi.toggle(True))
        self.adb_run(common.bluetooth.toggle(False))

    def mode_bluetooth(self):
        """Mode for turning on airplane mode and bluetooth."""
        self.log.info('Enabling airplane mode and bluetooth.')
        self.adb_run(common.airplane_mode.toggle(True))
        self.adb_run(common.auto_time.toggle(False))
        self.adb_run(common.auto_timezone.toggle(False))
        self.adb_run(common.location_gps.toggle(False))
        self.adb_run(common.location_network.toggle(False))
        self.adb_run(common.wifi.toggle(False))
        self.adb_run(common.bluetooth.toggle(True))

    def grant_permissions(self):
        """Grant all runtime permissions with PermissionUtils."""
        self.log.info('Granting all revoked runtime permissions.')

        # Install PermissionUtils.apk
        permissions_apk_path = self._instrumentation_config.get_file(
            'permissions_apk')
        self.ad_apps.install(permissions_apk_path)
        if not self.ad_apps.is_installed(permissions_apk_path):
            raise InstrumentationTestError(
                'Failed to install PermissionUtils.apk, abort!')
        package_name = self.ad_apps.get_package_name(permissions_apk_path)

        # Run the instrumentation command
        cmd_builder = InstrumentationCommandBuilder()
        cmd_builder.set_manifest_package(package_name)
        cmd_builder.set_runner('.PermissionInstrumentation')
        cmd_builder.add_flag('-w')
        cmd_builder.add_flag('-r')
        cmd_builder.add_key_value_param('command', 'grant-all')
        cmd = cmd_builder.build()
        self.log.debug('Instrumentation call: %s' % cmd)
        self.adb_run(cmd)

        # Uninstall PermissionUtils.apk
        self.ad_apps.uninstall(permissions_apk_path)

    def base_device_configuration(self):
        """Run the base setup commands for power testing."""
        self.log.info('Running base device setup commands.')

        self.ad_dut.adb.ensure_root()

        # Screen
        self.adb_run(common.screen_adaptive_brightness.toggle(False))
        self.adb_run(common.screen_brightness.set_value(
            get_brightness_for_200_nits(self.ad_dut.model)))
        self.adb_run(common.screen_timeout_ms.set_value(1800000))
        self.adb_run(common.notification_led.toggle(False))
        self.adb_run(common.screensaver.toggle(False))
        self.adb_run(common.wake_gesture.toggle(False))
        self.adb_run(common.doze_mode.toggle(False))

        # Accelerometer
        self.adb_run(common.auto_rotate.toggle(False))

        # Time
        self.adb_run(common.auto_time.toggle(False))
        self.adb_run(common.auto_timezone.toggle(False))
        self.adb_run(common.timezone.set_value(str(tzlocal.get_localzone())))

        # Location
        self.adb_run(common.location_gps.toggle(False))
        self.adb_run(common.location_network.toggle(False))

        # Power
        self.adb_run(common.battery_saver_mode.toggle(False))
        self.adb_run(common.battery_saver_trigger.set_value(0))
        self.adb_run(common.enable_full_batterystats_history)
        self.adb_run(common.disable_doze)

        # Gestures
        gestures = {
            'doze_pulse_on_pick_up': False,
            'doze_pulse_on_double_tap': False,
            'camera_double_tap_power_gesture_disabled': True,
            'camera_double_twist_to_flip_enabled': False,
            'assist_gesture_enabled': False,
            'assist_gesture_silence_alerts_enabled': False,
            'assist_gesture_wake_enabled': False,
            'system_navigation_keys_enabled': False,
            'camera_lift_trigger_enabled': False,
            'doze_always_on': False,
            'aware_enabled': False,
            'doze_wake_screen_gesture': False,
            'skip_gesture': False,
            'silence_gesture': False
        }
        self.adb_run(
            [DeviceSetting(common.SECURE, k).toggle(v)
             for k, v in gestures.items()])

        # GServices
        self.adb_run(goog.location_collection.toggle(False))
        self.adb_run(goog.cast_broadcast.toggle(False))
        self.adb_run(DeviceGServices(
            'location:compact_log_enabled').toggle(True))
        self.adb_run(DeviceGServices('gms:magictether:enable').toggle(False))
        self.adb_run(DeviceGServices('ocr.cc_ocr_enabled').toggle(False))
        self.adb_run(DeviceGServices(
            'gms:phenotype:phenotype_flag:debug_bypass_phenotype').toggle(True))
        self.adb_run(DeviceGServices(
            'gms_icing_extension_download_enabled').toggle(False))

        # Misc. Google features
        self.adb_run(goog.disable_playstore)
        self.adb_run(goog.disable_volta)
        self.adb_run(goog.disable_chre)
        self.adb_run(goog.disable_musiciq)
        self.adb_run(goog.disable_hotword)

        # Enable clock dump info
        self.adb_run('echo 1 > /d/clk/debug_suspend')
