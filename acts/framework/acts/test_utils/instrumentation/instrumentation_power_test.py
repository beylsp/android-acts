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
import shutil
import tempfile
import time

from acts.controllers.android_device import SL4A_APK_NAME
from acts.metrics.loggers.blackbox import BlackboxMappedMetricLogger
from acts.test_utils.instrumentation import instrumentation_proto_parser \
    as proto_parser
from acts.test_utils.instrumentation.instrumentation_base_test \
    import InstrumentationBaseTest
from acts.test_utils.instrumentation.instrumentation_base_test \
    import InstrumentationTestError
from acts.test_utils.instrumentation.instrumentation_command_builder import \
    DEFAULT_NOHUP_LOG
from acts.test_utils.instrumentation.instrumentation_command_builder import \
    InstrumentationTestCommandBuilder
from acts.test_utils.instrumentation.instrumentation_proto_parser import \
    DEFAULT_INST_LOG_DIR
from acts.test_utils.instrumentation.power_metrics import Measurement
from acts.test_utils.instrumentation.power_metrics import PowerMetrics

from acts import context
from acts import signals

ACCEPTANCE_THRESHOLD = 'acceptance_threshold'
AUTOTESTER_LOG = 'autotester.log'
DISCONNECT_USB_FILE = 'disconnectusb.log'
POLLING_INTERVAL = 0.5


class InstrumentationPowerTest(InstrumentationBaseTest):
    """Instrumentation test for measuring and validating power metrics.

    Params:
        metric_logger: Blackbox metric logger used to store test metrics.
        _instr_cmd_builder: Builder for the instrumentation command
    """

    def __init__(self, configs):
        super().__init__(configs)
        self.metric_logger = BlackboxMappedMetricLogger.for_test_class()

    def setup_class(self):
        super().setup_class()
        self.monsoon = self.monsoons[0]
        self._setup_monsoon()
        self._instr_cmd_builder = self.power_instrumentation_command_builder()
        self._sl4a_apk = None

    def _prepare_device(self):
        """Prepares the device for power testing."""
        super()._prepare_device()
        self._cleanup_test_files()
        self.install_test_apk()
        self.grant_permissions()

    def _cleanup_device(self):
        """Clean up device after power testing."""
        self._cleanup_test_files()

    def _setup_monsoon(self):
        """Set up the Monsoon controller for this testclass/testcase."""
        self.log.info('Setting up Monsoon %s' % self.monsoon.serial)
        monsoon_config = self._get_merged_config('Monsoon')
        self._monsoon_voltage = monsoon_config.get_numeric('voltage', 4.2)
        self.monsoon.set_voltage_safe(self._monsoon_voltage)
        if 'max_current' in monsoon_config:
            self.monsoon.set_max_current(
                monsoon_config.get_numeric('max_current'))

        self.monsoon.usb('on')
        self.monsoon.set_on_disconnect(self._on_disconnect)
        self.monsoon.set_on_reconnect(self._on_reconnect)

        self._disconnect_usb_timeout = monsoon_config.get_numeric(
            'usb_disconnection_timeout', 240)

        self._measurement_args = dict(
            duration=monsoon_config.get_numeric('duration'),
            hz=monsoon_config.get_numeric('frequency'),
            measure_after_seconds=monsoon_config.get_numeric('delay')
        )

    def _on_disconnect(self):
        """Callback invoked by device disconnection from the Monsoon."""
        self.ad_dut.log.info('Disconnecting device.')
        self.ad_dut.stop_services()
        # Uninstall SL4A
        self._sl4a_apk = self.ad_apps.pull_apk(
            SL4A_APK_NAME, tempfile.mkdtemp(prefix='sl4a'))
        self.ad_apps.uninstall(self._sl4a_apk)
        time.sleep(1)

    def _on_reconnect(self):
        """Callback invoked by device reconnection to the Monsoon"""
        # Reinstall SL4A
        if not self.ad_dut.is_sl4a_installed() and self._sl4a_apk:
            self.ad_apps.install(self._sl4a_apk)
            shutil.rmtree(os.path.dirname(self._sl4a_apk))
            self._sl4a_apk = None
        self.ad_dut.start_services()
        # Release wake lock to put device into sleep.
        self.ad_dut.droid.goToSleepNow()
        self.ad_dut.log.info('Device reconnected.')

    def install_test_apk(self):
        """Installs test apk on the device."""
        test_apk_file = self._instrumentation_config.get_file('test_apk')
        self.ad_apps.install(test_apk_file, '-g')
        if not self.ad_apps.is_installed(test_apk_file):
            raise InstrumentationTestError('Failed to install test APK.')
        self._test_pkg = self.ad_apps.get_package_name(test_apk_file)

    def _cleanup_test_files(self):
        """Remove test-generated files from the device."""
        self.ad_dut.log.info('Cleaning up test generated files.')
        for file_name in [DISCONNECT_USB_FILE, DEFAULT_INST_LOG_DIR,
                          DEFAULT_NOHUP_LOG, AUTOTESTER_LOG]:
            path = os.path.join(
                self.ad_dut.adb.shell('echo $EXTERNAL_STORAGE'), file_name)
            self.adb_run('rm -rf %s' % path)

    # Test runtime utils

    def power_instrumentation_command_builder(self):
        """Return the default command builder for power tests"""
        builder = InstrumentationTestCommandBuilder.default()
        builder.set_manifest_package(self._test_pkg)
        builder.set_nohup()
        return builder

    def _wait_for_disconnect_signal(self):
        """Poll the device for a disconnect USB signal file. This will indicate
        to the Monsoon that the device is ready to be disconnected.
        """
        self.log.info('Waiting for USB disconnect signal')
        disconnect_file = os.path.join(
            self.ad_dut.adb.shell('echo $EXTERNAL_STORAGE'),
            DISCONNECT_USB_FILE)
        start_time = time.time()
        while time.time() < start_time + self._disconnect_usb_timeout:
            if self.ad_dut.adb.shell('ls %s' % disconnect_file):
                return
            time.sleep(POLLING_INTERVAL)
        raise InstrumentationTestError('Timeout while waiting for USB '
                                       'disconnect signal.')

    def measure_power(self):
        """Measures power consumption with the Monsoon. See monsoon_lib API for
        details.
        """
        if not hasattr(self, '_measurement_args'):
            raise InstrumentationTestError('Missing Monsoon measurement args.')

        # Start measurement after receiving disconnect signal
        self._wait_for_disconnect_signal()
        power_data_path = os.path.join(
            context.get_current_context().get_full_output_path(), 'power_data')
        self.monsoon.usb('auto')
        measure_start_time = time.time()
        result = self.monsoon.measure_power(
            **self._measurement_args, output_path=power_data_path)
        self.monsoon.usb('on')

        # Gather relevant metrics from measurements
        session = self.dump_instrumentation_result_proto()
        self._power_metrics = PowerMetrics(self._monsoon_voltage,
                                           start_time=measure_start_time)
        self._power_metrics.generate_test_metrics(
            PowerMetrics.import_raw_data(power_data_path),
            proto_parser.get_test_timestamps(session))
        self._log_metrics()
        return result

    def run_and_measure(self, instr_class, instr_method=None, req_params=None):
        """Convenience method for setting up the instrumentation test command,
        running it on the device, and starting the Monsoon measurement.

        Args:
            instr_class: Fully qualified name of the instrumentation test class
            instr_method: Name of the instrumentation test method
            req_params: List of required parameter names

        Returns: summary of Monsoon measurement
        """
        if instr_method:
            self._instr_cmd_builder.add_test_method(instr_class, instr_method)
        else:
            self._instr_cmd_builder.add_test_class(instr_class)
        params = {}
        instr_call_config = self._get_merged_config('instrumentation_call')
        # Add required parameters
        for param_name in req_params or []:
            params[param_name] = instr_call_config.get(
                param_name, verify_fn=lambda x: x is not None,
                failure_msg='%s is a required parameter.' % param_name)
        # Add all other parameters
        params.update(instr_call_config)
        for name, value in params.items():
            self._instr_cmd_builder.add_key_value_param(name, value)
        instr_cmd = self._instr_cmd_builder.build()
        self.adb_run_async(instr_cmd)
        return self.measure_power()

    def _log_metrics(self):
        """Record the collected metrics with the metric logger."""
        for metric_name in PowerMetrics.ALL_METRICS:
            for instr_test_name in self._power_metrics.test_metrics:
                metric_value = getattr(
                    self._power_metrics.test_metrics[instr_test_name],
                    metric_name).value
                self.metric_logger.add_metric(
                    '%s__%s' % (metric_name, instr_test_name), metric_value)

    def validate_power_results(self, *instr_test_names):
        """Compare power measurements with target values and set the test result
        accordingly.

        Args:
            instr_test_names: Name(s) of the instrumentation test method.
                If none specified, defaults to all test methods run.

        Raises:
            signals.TestFailure if one or more metrics do not satisfy threshold
            signals.TestPass otherwise
        """
        summaries = {}
        failures = {}
        all_thresholds = self._get_merged_config(ACCEPTANCE_THRESHOLD)

        if not instr_test_names:
            instr_test_names = all_thresholds.keys()

        for instr_test_name in instr_test_names:
            try:
                test_metrics = self._power_metrics.test_metrics[instr_test_name]
            except KeyError:
                raise InstrumentationTestError(
                    'Unable to find test method %s in instrumentation output. '
                    'Check instrumentation call results in '
                    'instrumentation_proto.txt.'
                    % instr_test_name)

            summaries[instr_test_name] = test_metrics.summary
            failures[instr_test_name] = {}
            test_thresholds = all_thresholds.get_config(instr_test_name)
            for metric_name, metric in test_thresholds.items():
                try:
                    actual_result = getattr(test_metrics, metric_name)
                except AttributeError:
                    continue

                if 'unit_type' not in metric or 'unit' not in metric:
                    continue
                unit_type = metric['unit_type']
                unit = metric['unit']

                lower_value = metric.get_numeric('lower_limit', float('-inf'))
                upper_value = metric.get_numeric('upper_limit', float('inf'))
                if 'expected_value' in metric and 'percent_deviation' in metric:
                    expected_value = metric.get_numeric('expected_value')
                    percent_deviation = metric.get_numeric('percent_deviation')
                    lower_value = expected_value * (1 - percent_deviation / 100)
                    upper_value = expected_value * (1 + percent_deviation / 100)

                lower_bound = Measurement(lower_value, unit_type, unit)
                upper_bound = Measurement(upper_value, unit_type, unit)
                if not lower_bound <= actual_result <= upper_bound:
                    failures[instr_test_name][metric_name] = {
                        'expected': '[%s, %s]' % (lower_bound, upper_bound),
                        'actual': str(actual_result)
                    }
        self.log.info('Summary of measurements: %s' % summaries)
        if any(failures.values()):
            raise signals.TestFailure('One or more measurements do not meet '
                                      'the specified criteria', failures)
        raise signals.TestPass('All measurements meet the specified criteria')
