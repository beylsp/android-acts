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

import itertools
import pprint
import queue
import time

import acts.base_test
import acts.signals as signals
import acts.test_utils.wifi.wifi_test_utils as wutils
import acts.utils

from acts import asserts
from acts.test_decorators import test_tracker_info
from acts.test_utils.wifi.WifiBaseTest import WifiBaseTest
from acts.test_utils.wifi import wifi_constants

WifiEnums = wutils.WifiEnums

# Network request timeout to use.
NETWORK_REQUEST_TIMEOUT_MS = 60 * 1000

class WifiNetworkRequestTest(WifiBaseTest):
    """Tests for NetworkRequest with WifiNetworkSpecifier API surface.

    Test Bed Requirement:
    * one Android device
    * Several Wi-Fi networks visible to the device, including an open Wi-Fi
      network.
    """

    def __init__(self, controllers):
        WifiBaseTest.__init__(self, controllers)

    def setup_class(self):
        self.dut = self.android_devices[0]
        wutils.wifi_test_device_init(self.dut)
        req_params = []
        opt_param = [
            "open_network", "reference_networks"
        ]
        self.unpack_userparams(
            req_param_names=req_params, opt_param_names=opt_param)

        if "AccessPoint" in self.user_params:
            self.legacy_configure_ap_and_start(wpa_network=True,
                                               wep_network=True)

        asserts.assert_true(
            len(self.reference_networks) > 0,
            "Need at least one reference network with psk.")
        self.wpa_psk_2g = self.reference_networks[0]["2g"]
        self.wpa_psk_5g = self.reference_networks[0]["5g"]
        self.open_2g = self.open_network[0]["2g"]
        self.open_5g = self.open_network[0]["5g"]

    def setup_test(self):
        self.dut.droid.wakeLockAcquireBright()
        self.dut.droid.wakeUpNow()
        wutils.wifi_toggle_state(self.dut, True)

    def teardown_test(self):
        self.dut.droid.wakeLockRelease()
        self.dut.droid.goToSleepNow()
        self.dut.droid.wifiReleaseNetworkAll()
        wutils.reset_wifi(self.dut)

    def on_fail(self, test_name, begin_time):
        self.dut.take_bug_report(test_name, begin_time)
        self.dut.cat_adb_log(test_name, begin_time)

    def teardown_class(self):
        if "AccessPoint" in self.user_params:
            del self.user_params["reference_networks"]
            del self.user_params["open_network"]

    """Helper Functions"""
    def wait_for_network_lost(self):
        """
        Wait for network lost callback from connectivity service (wifi
        disconnect).

        Args:
            ad: Android device object.
        """
        try:
            self.dut.droid.wifiStartTrackingStateChange()
            event = self.dut.ed.pop_event(
                wifi_constants.WIFI_NETWORK_CB_ON_LOST, 10)
            self.dut.droid.wifiStopTrackingStateChange()
        except queue.Empty:
            raise signals.TestFailure(
                "Device did not disconnect from the network")


    @test_tracker_info(uuid="")
    def test_connect_to_wpa_psk_2g_with_ssid(self):
        """
        Initiates a connection to network via network request with specific SSID

        Steps:
        1. Send a network specifier with the specific SSID/credentials of
           WPA-PSK 2G network.
        2. Wait for platform to scan and find matching networks.
        3. Simulate user selecting the network.
        4. Ensure that the device connects to the network.
        """
        wutils.wifi_connect_using_network_request(self.dut, self.wpa_psk_2g,
                                                  self.wpa_psk_2g)

    @test_tracker_info(uuid="")
    def test_connect_to_open_5g_with_ssid(self):
        """
        Initiates a connection to network via network request with specific SSID

        Steps:
        1. Send a network specifier with the specific SSID of Open 5G network.
        2. Wait for platform to scan and find matching networks.
        3. Simulate user selecting the network.
        4. Ensure that the device connects to the network.
        """
        wutils.wifi_connect_using_network_request(self.dut, self.open_5g,
                                                  self.open_5g)

    @test_tracker_info(uuid="")
    def test_connect_to_wpa_psk_5g_with_ssid_pattern(self):
        """
        Initiates a connection to network via network request with SSID pattern

        Steps:
        1. Send a network specifier with the SSID pattern/credentials of
           WPA-PSK 5G network.
        2. Wait for platform to scan and find matching networks.
        3. Simulate user selecting the network.
        4. Ensure that the device connects to the network.
        """
        network_specifier = self.wpa_psk_5g.copy();
        # Remove ssid & replace with ssid pattern.
        network_ssid = network_specifier.pop(WifiEnums.SSID_KEY)
        # Remove the last element of ssid & replace with .* to create a matching
        # pattern.
        network_specifier[WifiEnums.SSID_PATTERN_KEY] = network_ssid[:-1] + ".*"
        wutils.wifi_connect_using_network_request(self.dut, self.wpa_psk_5g,
                                                  network_specifier)

    @test_tracker_info(uuid="")
    def test_connect_to_open_5g_after_connecting_to_wpa_psk_2g(self):
        """
        Initiates a connection to network via network request with SSID pattern

        Steps:
        1. Send a network specifier with the specific SSID of Open 5G network.
        2. Wait for platform to scan and find matching networks.
        3. Simulate user selecting the network.
        4. Ensure that the device connects to the network.
        5. Release the network request.
        6. Send another network specifier with the specific SSID & credentials
           of WPA-PSK 2G network.
        7. Ensure we disconnect from the previous network.
        8. Wait for platform to scan and find matching networks.
        9. Simulate user selecting the new network.
        10. Ensure that the device connects to the new network.
        """
        # Complete flow for the first request.
        wutils.wifi_connect_using_network_request(self.dut, self.wpa_psk_2g,
                                                  self.wpa_psk_2g)
        # Release the request.
        self.dut.droid.wifiReleaseNetwork(self.wpa_psk_2g)
        # Ensure we disconnected from the previous network.
        wutils.wait_for_disconnect(self.dut)
        self.dut.log.info("Disconnected from network %s", self.wpa_psk_2g)
        # Complete flow for the second request.
        wutils.wifi_connect_using_network_request(self.dut, self.open_5g,
                                                  self.open_5g)

    def test_connect_to_open_5g_with_ssid(self):
        """
        Initiates a connection to network via network request with specific SSID

        Steps:
        1. Send a network specifier with the specific SSID of Open 5G network.
        2. Wait for platform to scan and find matching networks.
        3. Simulate user selecting the network.
        4. Ensure that the device connects to the network.
        """
        wutils.wifi_connect_using_network_request(self.dut, self.open_5g,
                                                  self.open_5g)


    @test_tracker_info(uuid="")
    def test_connect_to_wpa_psk_5g_while_connecting_to_open_2g(self):
        """
        Initiates a connection to network via network request with specific SSID

        Steps:
        1. Send a network specifier with the specific SSID & credentials of
           WPA-PSK 5G network.
        2. Send another network specifier with the specific SSID of Open 2G
           network.
        3. Ensure we disconnect from the previous network.
        4. Wait for platform to scan and find matching networks.
        5. Simulate user selecting the new network.
        6. Ensure that the device connects to the new network.
        """
        # Make the first request.
        self.dut.droid.wifiRequestNetworkWithSpecifier(self.open_2g)
        self.dut.log.info("Sent network request with %s", self.open_2g)
        # Complete flow for the second request.
        wutils.wifi_connect_using_network_request(self.dut, self.wpa_psk_5g,
                                                  self.wpa_psk_5g)

    @test_tracker_info(uuid="")
    def test_connect_to_open_5g_while_connected_to_wpa_psk_2g(self):
        """
        Initiates a connection to network via network request with specific SSID

        Steps:
        1. Send a network specifier with the specific SSID of Open 5G network.
        2. Wait for platform to scan and find matching networks.
        3. Simulate user selecting the network.
        4. Ensure that the device connects to the network.
        5. Send another network specifier with the specific SSID & credentials
           of WPA-PSK 2G network.
        6. Ensure we disconnect from the previous network.
        7. Wait for platform to scan and find matching networks.
        8. Simulate user selecting the new network.
        9. Ensure that the device connects to the new network.
        """
        # Complete flow for the first request.
        wutils.wifi_connect_using_network_request(self.dut, self.wpa_psk_2g,
                                                  self.wpa_psk_2g)
        # Send the second request.
        self.dut.droid.wifiRequestNetworkWithSpecifier(self.open_5g)
        self.dut.log.info("Sent network request with %s", self.open_5g)
        # Ensure we disconnected from the previous network.
        wutils.wait_for_disconnect(self.dut)
        self.dut.log.info("Disconnected from network %s", self.wpa_psk_2g)
        # Ensure we received the network lost callback because the previous
        # request is still active.
        self.wait_for_network_lost()

        # Ensure we connected to second request.
        wutils.wait_for_wifi_connect_after_network_request(self.dut,
                                                           self.open_5g)

    @test_tracker_info(uuid="")
    def test_match_failure_with_invalid_ssid_pattern(self):
        """
        Initiates a connection to network via network request with SSID pattern
        that does not match any networks.

        Steps:
        1. Send a network specifier with the non-matching SSID pattern.
        2. Ensure that the platform does not retrun any matching networks.
        3. Wait for the request to timeout.
        """
        network = self.wpa_psk_5g
        network_specifier = self.wpa_psk_5g.copy();
        # Remove ssid & replace with invalid ssid pattern.
        network_ssid = network_specifier.pop(WifiEnums.SSID_KEY)
        network_specifier[WifiEnums.SSID_PATTERN_KEY] = \
            network_ssid + "blah" + ".*"

        self.dut.droid.wifiStartTrackingStateChange()
        expected_ssid = network[WifiEnums.SSID_KEY]

        self.dut.droid.wifiRequestNetworkWithSpecifierWithTimeout(
              network_specifier, NETWORK_REQUEST_TIMEOUT_MS)
        self.dut.log.info("Sent network request with invalid specifier %s",
                    network_specifier)
        time.sleep(wifi_constants.NETWORK_REQUEST_CB_REGISTER_DELAY_SEC)
        self.dut.droid.wifiRegisterNetworkRequestMatchCallback()
        # Wait for the request to timeout. In the meantime, platform will scan
        # and return matching networks. Ensure the matching networks list is
        # empty.
        start_time = time.time()
        has_request_timedout = False
        try:
          while not has_request_timedout and time.time() - start_time <= \
              NETWORK_REQUEST_TIMEOUT_MS / 1000:
                # Pop all network request related events.
                network_request_events = \
                    self.dut.ed.pop_events("WifiManagerNetwork.*", 30)
                asserts.assert_true(network_request_events, "invalid events")
                for network_request_event in network_request_events:
                    # Handle the network match callbacks.
                    if network_request_event["name"] == \
                        wifi_constants.WIFI_NETWORK_REQUEST_MATCH_CB_ON_MATCH:
                        matched_scan_results = network_request_event["data"]
                        self.dut.log.debug(
                            "Network request on match results %s",
                            matched_scan_results)
                        asserts.assert_false(matched_scan_results,
                                             "Empty network matches expected")
                    # Handle the network request unavailable timeout.
                    if network_request_event["name"] == \
                        wifi_constants.WIFI_NETWORK_CB_ON_UNAVAILABLE:
                        self.dut.log.info("Network request timed out")
                        has_request_timedout = True
        except queue.Empty:
            asserts.fail("No events returned")
        finally:
            self.dut.droid.wifiStopTrackingStateChange()
        asserts.assert_true(has_request_timedout,
                            "Network request did not timeout")
