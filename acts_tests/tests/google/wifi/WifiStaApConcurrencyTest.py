#!/usr/bin/env python3.4
#
#   Copyright 2018 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import pprint
import time

from acts import asserts
from acts import base_test
from acts.controllers.ap_lib import hostapd_constants
import acts.signals as signals
from acts.test_decorators import test_tracker_info
from acts.test_utils.tel.tel_test_utils import WIFI_CONFIG_APBAND_2G
from acts.test_utils.tel.tel_test_utils import WIFI_CONFIG_APBAND_5G
import acts.test_utils.wifi.wifi_test_utils as wutils
from acts.test_utils.wifi.WifiBaseTest import WifiBaseTest
import acts.utils as utils

WifiEnums = wutils.WifiEnums
WLAN = "wlan0"
# Channels to configure the AP for various test scenarios.
WIFI_NETWORK_AP_CHANNEL_2G = 1
WIFI_NETWORK_AP_CHANNEL_5G = 36
WIFI_NETWORK_AP_CHANNEL_5G_DFS = 132


class WifiStaApConcurrencyTest(WifiBaseTest):
    """Tests for STA + AP concurrency scenarios.

    Test Bed Requirement:
    * Two Android devices (For AP)
    * One Wi-Fi network visible to the device (for STA).
    """

    def setup_class(self):
        super().setup_class()

        self.dut = self.android_devices[0]
        self.dut_client = self.android_devices[1]

        # Do a simple version of init - mainly just sync the time and enable
        # verbose logging.  This test will fail if the DUT has a sim and cell
        # data is disabled.  We would also like to test with phones in less
        # constrained states (or add variations where we specifically
        # constrain).
        utils.require_sl4a(self.android_devices)

        for ad in self.android_devices:
            wutils.wifi_test_device_init(ad)
            utils.sync_device_time(ad)
            # Set country code explicitly to "US".
            wutils.set_wifi_country_code(ad, WifiEnums.CountryCode.US)
            # Enable verbose logging on the duts.
            ad.droid.wifiEnableVerboseLogging(1)

        req_params = ["dbs_supported_models",
                      "iperf_server_address",
                      "iperf_server_port"]
        self.unpack_userparams(req_param_names=req_params,)
        asserts.abort_class_if(
            self.dut.model not in self.dbs_supported_models,
            "Device %s does not support dual interfaces." % self.dut.model)

    def setup_test(self):
        for ad in self.android_devices:
            ad.droid.wakeLockAcquireBright()
            ad.droid.wakeUpNow()
        self.turn_location_off_and_scan_toggle_off()

    def teardown_test(self):
        # Prevent the stop wifi tethering failure to block ap close
        try:
            wutils.stop_wifi_tethering(self.dut)
        except signals.TestFailure:
            pass
        for ad in self.android_devices:
            ad.droid.wakeLockRelease()
            ad.droid.goToSleepNow()
            wutils.reset_wifi(ad)
        self.turn_location_on_and_scan_toggle_on()
        wutils.wifi_toggle_state(self.dut, True)
        self.access_points[0].close()
        del self.user_params["reference_networks"]
        del self.user_params["open_network"]

    def on_fail(self, test_name, begin_time):
        for ad in self.android_devices:
            ad.take_bug_report(test_name, begin_time)
            ad.cat_adb_log(test_name, begin_time)

    ### Helper Functions ###

    def configure_ap(self, channel_2g=None, channel_5g=None):
        """Configure and bring up AP on required channel.

        Args:
            channel_2g: The channel number to use for 2GHz network.
            channel_5g: The channel number to use for 5GHz network.

        """
        if not channel_2g:
            channel_2g = hostapd_constants.AP_DEFAULT_CHANNEL_2G
        if not channel_5g:
            channel_5g = hostapd_constants.AP_DEFAULT_CHANNEL_5G
        self.legacy_configure_ap_and_start(channel_2g=channel_2g,
                                           channel_5g=channel_5g)
        self.open_2g = self.open_network[0]["2g"]
        self.open_5g = self.open_network[0]["5g"]

    def turn_location_on_and_scan_toggle_on(self):
        """Turns on wifi location scans."""
        utils.set_location_service(self.dut, True)
        self.dut.droid.wifiScannerToggleAlwaysAvailable(True)
        msg = "Failed to turn on location service's scan."
        asserts.assert_true(self.dut.droid.wifiScannerIsAlwaysAvailable(), msg)

    def turn_location_off_and_scan_toggle_off(self):
        """Turns off wifi location scans."""
        utils.set_location_service(self.dut, False)
        self.dut.droid.wifiScannerToggleAlwaysAvailable(False)
        msg = "Failed to turn off location service's scan."
        asserts.assert_false(self.dut.droid.wifiScannerIsAlwaysAvailable(), msg)

    def run_iperf_client(self, params):
        """Run iperf traffic after connection.

        Args:
            params: A tuple of network info and AndroidDevice object.
        """
        if "iperf_server_address" in self.user_params:
            wait_time = 5
            network, ad = params
            ssid = network[WifiEnums.SSID_KEY]
            self.log.info("Starting iperf traffic through {}".format(ssid))
            time.sleep(wait_time)
            port_arg = "-p {}".format(self.iperf_server_port)
            success, data = ad.run_iperf_client(self.iperf_server_address,
                                                port_arg)
            self.log.debug(pprint.pformat(data))
            asserts.assert_true(success, "Error occurred in iPerf traffic.")

    def create_softap_config(self):
        """Create a softap config with ssid and password."""
        ap_ssid = "softap_" + utils.rand_ascii_str(8)
        ap_password = utils.rand_ascii_str(8)
        self.dut.log.info("softap setup: %s %s", ap_ssid, ap_password)
        config = {wutils.WifiEnums.SSID_KEY: ap_ssid}
        config[wutils.WifiEnums.PWD_KEY] = ap_password
        return config

    def start_softap_and_verify(self, band, check_connectivity=True):
        """Test startup of softap.

        1. Bring up AP mode.
        2. Verify SoftAP active using the client device.

        Args:
            band: wifi band to start soft ap on
            check_connectivity: If set, verify internet connectivity

        Returns:
            Softap config
        """
        config = self.create_softap_config()
        wutils.start_wifi_tethering(self.dut,
                                    config[WifiEnums.SSID_KEY],
                                    config[WifiEnums.PWD_KEY],
                                    band)
        for ad in self.android_devices[1:]:
            wutils.connect_to_wifi_network(
                ad, config, check_connectivity=check_connectivity)
        return config

    def connect_to_wifi_network_and_start_softap(self, nw_params, softap_band):
        """Test concurrent wifi connection and softap.

        This helper method first makes a wifi connection and then starts SoftAp.
        1. Bring up wifi.
        2. Establish connection to a network.
        3. Bring up softap and verify AP can be connected by a client device.
        4. Run iperf on the wifi/softap connection to the network.

        Args:
            nw_params: Params for network STA connection.
            softap_band: Band for the AP.
        """
        wutils.connect_to_wifi_network(self.dut, nw_params)
        softap_config = self.start_softap_and_verify(softap_band)
        self.run_iperf_client((nw_params, self.dut))
        self.run_iperf_client((softap_config, self.dut_client))

        if len(self.android_devices) > 2:
            self.log.info("Testbed has extra devices, do more validation")
            self.verify_traffic_between_dut_clients(
                self.dut_client, self.android_devices[2])

        asserts.assert_true(self.dut.droid.wifiCheckState(),
                            "Wifi is not reported as running")
        asserts.assert_true(self.dut.droid.wifiIsApEnabled(),
                            "SoftAp is not reported as running")

    def start_softap_and_connect_to_wifi_network(self, nw_params, softap_band):
        """Test concurrent wifi connection and softap.

        This helper method first starts SoftAp and then makes a wifi connection.
        1. Bring up softap and verify AP can be connected by a client device.
        2. Bring up wifi.
        3. Establish connection to a network.
        4. Run iperf on the wifi/softap connection to the network.
        5. Verify wifi state and softap state.

        Args:
            nw_params: Params for network STA connection.
            softap_band: Band for the AP.
        """
        softap_config = self.start_softap_and_verify(softap_band, False)
        wutils.connect_to_wifi_network(self.dut, nw_params)
        self.run_iperf_client((nw_params, self.dut))
        self.run_iperf_client((softap_config, self.dut_client))

        if len(self.android_devices) > 2:
            self.log.info("Testbed has extra devices, do more validation")
            self.verify_traffic_between_dut_clients(
                self.dut, self.android_devices[2])

        asserts.assert_true(self.dut.droid.wifiCheckState(),
                            "Wifi is not reported as running")
        asserts.assert_true(self.dut.droid.wifiIsApEnabled(),
                            "SoftAp is not reported as running")

    def verify_traffic_between_dut_clients(self, ad1, ad2, num_of_tries=2):
        """Test the clients that connect to DUT's softap can ping each other.

        Args:
            ad1: DUT 1
            ad2: DUT 2
            num_of_tries: the retry times of ping test.
        """
        ad1_ip = ad1.droid.connectivityGetIPv4Addresses(WLAN)[0]
        ad2_ip = ad2.droid.connectivityGetIPv4Addresses(WLAN)[0]
        # Ping each other
        for _ in range(num_of_tries):
            if utils.adb_shell_ping(ad1, count=10, dest_ip=ad2_ip, timeout=20):
                break
        else:
            asserts.fail("%s ping %s failed" % (ad1.serial, ad2_ip))
        for _ in range(num_of_tries):
            if utils.adb_shell_ping(ad2, count=10, dest_ip=ad1_ip, timeout=20):
                break
        else:
            asserts.fail("%s ping %s failed" % (ad2.serial, ad1_ip))

    ### Tests ###

    @test_tracker_info(uuid="c396e7ac-cf22-4736-a623-aa6d3c50193a")
    def test_wifi_connection_2G_softap_2G(self):
        """Test connection to 2G network followed by SoftAp on 2G."""
        self.configure_ap(channel_2g=WIFI_NETWORK_AP_CHANNEL_2G)
        self.connect_to_wifi_network_and_start_softap(
            self.open_2g, WIFI_CONFIG_APBAND_2G)

    @test_tracker_info(uuid="1cd6120d-3db4-4624-9bae-55c976533a48")
    def test_wifi_connection_5G_softap_5G(self):
        """Test connection to 5G network followed by SoftAp on 5G."""
        self.configure_ap(channel_5g=WIFI_NETWORK_AP_CHANNEL_5G)
        self.connect_to_wifi_network_and_start_softap(
            self.open_5g, WIFI_CONFIG_APBAND_5G)

    @test_tracker_info(uuid="5f980007-3490-413e-b94e-7700ffab8534")
    def test_wifi_connection_5G_DFS_softap_5G(self):
        """Test connection to 5G DFS network followed by SoftAp on 5G."""
        self.configure_ap(channel_5g=WIFI_NETWORK_AP_CHANNEL_5G_DFS)
        self.connect_to_wifi_network_and_start_softap(
            self.open_5g, WIFI_CONFIG_APBAND_5G)

    @test_tracker_info(uuid="d05d5d44-c738-4372-9f01-ce2a640a2f25")
    def test_wifi_connection_5G_softap_2G(self):
        """Test connection to 5G network followed by SoftAp on 2G."""
        self.configure_ap(channel_5g=WIFI_NETWORK_AP_CHANNEL_5G)
        self.connect_to_wifi_network_and_start_softap(
            self.open_5g, WIFI_CONFIG_APBAND_2G)

    @test_tracker_info(uuid="909ac713-1ad3-4dad-9be3-ad60f00ed25e")
    def test_wifi_connection_5G_DFS_softap_2G(self):
        """Test connection to 5G DFS network followed by SoftAp on 2G."""
        self.configure_ap(channel_5g=WIFI_NETWORK_AP_CHANNEL_5G_DFS)
        self.connect_to_wifi_network_and_start_softap(
            self.open_5g, WIFI_CONFIG_APBAND_2G)

    @test_tracker_info(uuid="e8de724a-25d3-4801-94cc-22e9e0ecc8d1")
    def test_wifi_connection_2G_softap_5G(self):
        """Test connection to 2G network followed by SoftAp on 5G."""
        self.configure_ap(channel_2g=WIFI_NETWORK_AP_CHANNEL_2G)
        self.connect_to_wifi_network_and_start_softap(
            self.open_2g, WIFI_CONFIG_APBAND_5G)

    @test_tracker_info(uuid="647f4e17-5c7a-4249-98af-f791d163a39f")
    def test_wifi_connection_5G_softap_2G_with_location_scan_on(self):
        """Test connection to 5G network, SoftAp on 2G with location scan on."""
        self.configure_ap(channel_5g=WIFI_NETWORK_AP_CHANNEL_5G)
        self.turn_location_on_and_scan_toggle_on()
        self.connect_to_wifi_network_and_start_softap(
            self.open_5g, WIFI_CONFIG_APBAND_2G)
        # Now toggle wifi off & ensure we can still scan.
        wutils.wifi_toggle_state(self.dut, False)
        wutils.start_wifi_connection_scan_and_ensure_network_found(
            self.dut, self.open_5g[WifiEnums.SSID_KEY])

    @test_tracker_info(uuid="4aa56c11-e5bc-480b-bd61-4b4ee577a5da")
    def test_softap_2G_wifi_connection_2G(self):
        """Test SoftAp on 2G followed by connection to 2G network."""
        self.configure_ap(channel_2g=WIFI_NETWORK_AP_CHANNEL_2G)
        self.start_softap_and_connect_to_wifi_network(
            self.open_2g, WIFI_CONFIG_APBAND_2G)

    @test_tracker_info(uuid="5f954957-ad20-4de1-b20c-6c97d0463bdd")
    def test_softap_5G_wifi_connection_5G(self):
        """Test SoftAp on 5G followed by connection to 5G network."""
        self.configure_ap(channel_5g=WIFI_NETWORK_AP_CHANNEL_5G)
        self.start_softap_and_connect_to_wifi_network(
            self.open_5g, WIFI_CONFIG_APBAND_5G)

    @test_tracker_info(uuid="1306aafc-a07e-4654-ba78-674f90cf748e")
    def test_softap_5G_wifi_connection_5G_DFS(self):
        """Test SoftAp on 5G followed by connection to 5G DFS network."""
        self.configure_ap(channel_5g=WIFI_NETWORK_AP_CHANNEL_5G_DFS)
        self.start_softap_and_connect_to_wifi_network(
            self.open_5g, WIFI_CONFIG_APBAND_5G)

    @test_tracker_info(uuid="5e28e8b5-3faa-4cff-a782-13a796d7f572")
    def test_softap_5G_wifi_connection_2G(self):
        """Test SoftAp on 5G followed by connection to 2G network."""
        self.configure_ap(channel_2g=WIFI_NETWORK_AP_CHANNEL_2G)
        self.start_softap_and_connect_to_wifi_network(
            self.open_2g, WIFI_CONFIG_APBAND_5G)

    @test_tracker_info(uuid="a2c62bc6-9ccd-4bc4-8a23-9a1b5d0b4b5c")
    def test_softap_2G_wifi_connection_5G(self):
        """Test SoftAp on 2G followed by connection to 5G network."""
        self.configure_ap(channel_5g=WIFI_NETWORK_AP_CHANNEL_5G)
        self.start_softap_and_connect_to_wifi_network(
            self.open_5g, WIFI_CONFIG_APBAND_2G)

    @test_tracker_info(uuid="75400685-a9d9-4091-8af3-97bd539c246a")
    def test_softap_2G_wifi_connection_5G_DFS(self):
        """Test SoftAp on 2G followed by connection to 5G DFS network."""
        self.configure_ap(channel_5g=WIFI_NETWORK_AP_CHANNEL_5G_DFS)
        self.start_softap_and_connect_to_wifi_network(
            self.open_5g, WIFI_CONFIG_APBAND_2G)

    @test_tracker_info(uuid="aa23a3fc-31a1-4d5c-8cf5-2eb9fdf9e7ce")
    def test_softap_5G_wifi_connection_2G_with_location_scan_on(self):
        """Test SoftAp on 5G, connection to 2G network with location scan on."""
        self.configure_ap(channel_2g=WIFI_NETWORK_AP_CHANNEL_2G)
        self.turn_location_on_and_scan_toggle_on()
        self.start_softap_and_connect_to_wifi_network(
            self.open_2g, WIFI_CONFIG_APBAND_5G)
        # Now toggle wifi off & ensure we can still scan.
        wutils.wifi_toggle_state(self.dut, False)
        wutils.start_wifi_connection_scan_and_ensure_network_found(
            self.dut, self.open_2g[WifiEnums.SSID_KEY])