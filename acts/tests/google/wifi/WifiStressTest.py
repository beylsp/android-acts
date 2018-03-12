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

import acts.base_test
import acts.test_utils.wifi.wifi_test_utils as wutils
import acts.utils

from acts import asserts
from acts import signals
from acts import utils
from acts.test_decorators import test_tracker_info
from acts.test_utils.wifi.WifiBaseTest import WifiBaseTest
WifiEnums = wutils.WifiEnums

WAIT_FOR_AUTO_CONNECT = 40
WAIT_BEFORE_CONNECTION = 30

TIMEOUT = 1


class WifiStressTest(WifiBaseTest):
    """WiFi Stress test class.

    Test Bed Requirement:
    * Two Android device
    * Several Wi-Fi networks visible to the device, including an open Wi-Fi
      network.
    """

    def __init__(self, controllers):
        WifiBaseTest.__init__(self, controllers)

    def setup_class(self):
        self.dut = self.android_devices[0]
        self.dut_client = self.android_devices[1]
        wutils.wifi_test_device_init(self.dut)
        req_params = []
        opt_param = [
            "open_network", "reference_networks", "iperf_server_address",
            "stress_count"]
        self.unpack_userparams(
            req_param_names=req_params, opt_param_names=opt_param)

        if "AccessPoint" in self.user_params:
            self.legacy_configure_ap_and_start()

        asserts.assert_true(
            len(self.reference_networks) > 0,
            "Need at least one reference network with psk.")
        self.wpa_2g = self.reference_networks[0]["2g"]
        self.wpa_5g = self.reference_networks[0]["5g"]
        self.open_2g = self.open_network[0]["2g"]
        self.open_5g = self.open_network[0]["5g"]
        self.networks = [self.wpa_2g, self.wpa_5g, self.open_2g, self.open_5g]
        if "iperf_server_address" in self.user_params:
            self.iperf_server = self.iperf_servers[0]
        if hasattr(self, 'iperf_server'):
            self.iperf_server.start()

    def setup_test(self):
        self.dut.droid.wakeLockAcquireBright()
        self.dut.droid.wakeUpNow()

    def teardown_test(self):
        self.dut.droid.wakeLockRelease()
        self.dut.droid.goToSleepNow()

    def on_fail(self, test_name, begin_time):
        self.dut.take_bug_report(test_name, begin_time)
        self.dut.cat_adb_log(test_name, begin_time)
        pass

    def teardown_class(self):
        wutils.reset_wifi(self.dut)
        if hasattr(self, 'iperf_server'):
            self.iperf_server.stop()
        if "AccessPoint" in self.user_params:
            del self.user_params["reference_networks"]
            del self.user_params["open_network"]

    """Helper Functions"""

    def scan_and_connect_by_ssid(self, network):
        """Scan for network and connect using network information.

        Args:
            network: A dictionary representing the network to connect to.

        """
        ssid = network[WifiEnums.SSID_KEY]
        wutils.start_wifi_connection_scan_and_ensure_network_found(self.dut,
            ssid)
        wutils.wifi_connect(self.dut, network, num_of_tries=3)

    def scan_and_connect_by_id(self, network, net_id):
        """Scan for network and connect using network id.

        Args:
            net_id: Integer specifying the network id of the network.

        """
        ssid = network[WifiEnums.SSID_KEY]
        wutils.start_wifi_connection_scan_and_ensure_network_found(self.dut,
            ssid)
        wutils.wifi_connect_by_id(self.dut, net_id)


    """Tests"""

    @test_tracker_info(uuid="")
    def test_stress_toggle_wifi_state(self):
        """Toggle WiFi state ON and OFF for N times."""
        for count in range(self.stress_count):
            """Test toggling wifi"""
            self.log.debug("Going from on to off.")
            wutils.wifi_toggle_state(self.dut, False)
            self.log.debug("Going from off to on.")
            startTime = time.time()
            wutils.wifi_toggle_state(self.dut, True)
            startup_time = time.time() - startTime
            self.log.debug("WiFi was enabled on the device in %s s." % startup_time)

    @test_tracker_info(uuid="")
    def test_stress_connect_traffic_disconnect_5g(self):
        """Test to connect and disconnect from a network for N times.

           Steps:
               1. Scan and connect to a network.
               2. Run IPerf to upload data for few seconds.
               3. Disconnect.
               4. Repeat 1-3.

        """
        net_id = self.dut.droid.wifiAddNetwork(self.wpa_5g)
        asserts.assert_true(net_id != -1, "Add network %r failed" % self.wpa_5g)
        self.dut.droid.wifiEnableNetwork(net_id, 0)
        for count in range(self.stress_count):
            self.scan_and_connect_by_id(self.wpa_5g, net_id)
            # Start IPerf traffic from phone to server.
            # Upload data for 10s.
            args = "-p {} -t {}".format(self.iperf_server.port, 10)
            self.log.info("Running iperf client {}".format(args))
            result, data = self.dut.run_iperf_client(self.iperf_server_address, args)
            self.dut.droid.wifiDisconnect()
            time.sleep(WAIT_BEFORE_CONNECTION)
            if not result:
                self.log.debug("Error occurred in iPerf traffic.")
                raise signals.TestFailure("Error occurred in iPerf traffic. Current"
                    " WiFi state = %d" % self.dut.droid.wifiCheckState())

    @test_tracker_info(uuid="")
    def test_stress_connect_long_traffic_5g(self):
        """Test to connect to network and hold connection for few hours.

           Steps:
               1. Scan and connect to a network.
               2. Run IPerf to download data for few hours.
               3. Verify no WiFi disconnects/data interruption.

        """
        self.scan_and_connect_by_ssid(self.wpa_5g)
        # Start IPerf traffic from server to phone.
        # Download data for 5 hours.
        sec = 60
        args = "-p {} -t {} -R".format(self.iperf_server.port, sec)
        self.log.info("Running iperf client {}".format(args))
        result, data = self.dut.run_iperf_client(self.iperf_server_address,
            args, timeout=sec+1)
        self.dut.droid.wifiDisconnect()
        if not result:
            self.log.debug("Error occurred in iPerf traffic.")
            raise signals.TestFailure("Error occurred in iPerf traffic. Current"
                " WiFi state = %d" % self.dut.droid.wifiCheckState())

    @test_tracker_info(uuid="")
    def test_stress_wifi_failover(self):
        """This test does aggressive failover to several networks in list.

           Steps:
               1. Add and enable few networks.
               2. Let device auto-connect.
               3. Remove the connected network.
               4. Repeat 2-3.
               5. Device should connect to a network until all networks are
                  exhausted.

        """
        for count in range(self.stress_count):
            ssids = list()
            for network in self.networks:
                ssids.append(network[WifiEnums.SSID_KEY])
                ret = self.dut.droid.wifiAddNetwork(network)
                asserts.assert_true(ret != -1, "Add network %r failed" % network)
                self.dut.droid.wifiEnableNetwork(ret, 0)
            time.sleep(WAIT_FOR_AUTO_CONNECT)
            cur_network = self.dut.droid.wifiGetConnectionInfo()
            cur_ssid = cur_network[WifiEnums.SSID_KEY]
            for count in range(0,len(self.networks)):
                self.log.debug("Forget network %s" % cur_ssid)
                wutils.wifi_forget_network(self.dut, cur_ssid)
                time.sleep(WAIT_FOR_AUTO_CONNECT)
                cur_network = self.dut.droid.wifiGetConnectionInfo()
                cur_ssid = cur_network[WifiEnums.SSID_KEY]
                if count == len(self.networks) - 1:
                    break
                if cur_ssid not in ssids:
                    raise signals.TestFailure("Device did not failover to the "
                        "expected network. SSID = %s" % cur_ssid)
            network_config = self.dut.droid.wifiGetConfiguredNetworks()
            if len(network_config):
                raise signals.TestFailure("All the network configurations were not "
                        "removed. Configured networks = %s" % network_config)

    @test_tracker_info(uuid="")
    def test_stress_softAP_startup_and_stop_5g(self):
        """Test to bring up softAP and down for N times.

        Steps:
            1. Bring up softAP on 5G.
            2. Check for softAP on teh client device.
            3. Turn ON WiFi.
            4. Verify softAP is turned down and WiFi is up.

        """
        ap_ssid = "softap_" + utils.rand_ascii_str(8)
        ap_password = utils.rand_ascii_str(8)
        self.dut.log.info("softap setup: %s %s", ap_ssid, ap_password)
        config = {wutils.WifiEnums.SSID_KEY: ap_ssid}
        config[wutils.WifiEnums.PWD_KEY] = ap_password
        # Set country code explicitly to "US".
        self.dut.droid.wifiSetCountryCode(wutils.WifiEnums.CountryCode.US)
        self.dut_client.droid.wifiSetCountryCode(wutils.WifiEnums.CountryCode.US)
        for count in range(self.stress_count):
            initial_wifi_state = self.dut.droid.wifiCheckState()
            wutils.start_wifi_tethering(self.dut,
                ap_ssid,
                ap_password,
                WifiEnums.WIFI_CONFIG_APBAND_5G)
            wutils.start_wifi_connection_scan_and_ensure_network_found(
                self.dut_client, ap_ssid)
            # Toggle WiFi ON, which inturn calls softAP teardown.
            wutils.wifi_toggle_state(self.dut, True)
            time.sleep(TIMEOUT)
            asserts.assert_false(self.dut.droid.wifiIsApEnabled(),
                                 "SoftAp failed to shutdown!")
            time.sleep(TIMEOUT)
            cur_wifi_state = self.dut.droid.wifiCheckState()
            if initial_wifi_state != cur_wifi_state:
                raise signals.TestFailure("Wifi state was %d before softAP and %d now!" %
                    (initial_wifi_state, cur_wifi_state))
