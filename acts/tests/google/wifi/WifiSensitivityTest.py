#!/usr/bin/env python3.4
#
#   Copyright 2017 - The Android Open Source Project
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

import collections
import csv
import itertools
import json
import logging
import os
from acts import asserts
from acts import base_test
from acts import utils
from acts.controllers import iperf_client
from acts.controllers.utils_lib import ssh
from acts.metrics.loggers.blackbox import BlackboxMetricLogger
from acts.test_utils.wifi import wifi_performance_test_utils as wputils
from acts.test_utils.wifi import wifi_test_utils as wutils
from acts.test_utils.wifi import wifi_retail_ap as retail_ap
from WifiRvrTest import WifiRvrTest
from WifiPingTest import WifiPingTest


class WifiSensitivityTest(WifiRvrTest, WifiPingTest):
    """Class to test WiFi sensitivity tests.

    This class implements measures WiFi sensitivity per rate. It heavily
    leverages the WifiRvrTest class and introduced minor differences to set
    specific rates and the access point, and implements a different pass/fail
    check. For an example config file to run this test class see
    example_connectivity_performance_ap_sta.json.
    """

    RSSI_POLL_INTERVAL = 0.2
    VALID_TEST_CONFIGS = {
        1: ["legacy", "VHT20"],
        2: ["legacy", "VHT20"],
        6: ["legacy", "VHT20"],
        10: ["legacy", "VHT20"],
        11: ["legacy", "VHT20"],
        36: ["legacy", "VHT20", "VHT40", "VHT80"],
        40: ["legacy", "VHT20"],
        44: ["legacy", "VHT20"],
        48: ["legacy", "VHT20"],
        149: ["legacy", "VHT20", "VHT40", "VHT80"],
        153: ["legacy", "VHT20"],
        157: ["legacy", "VHT20"],
        161: ["legacy", "VHT20"]
    }
    RateTuple = collections.namedtuple(("RateTuple"),
                                       ["mcs", "streams", "data_rate"])
    #yapf:disable
    VALID_RATES = {
        "legacy_2GHz": [
            RateTuple(54, 1, 54), RateTuple(48, 1, 48),
            RateTuple(36, 1, 36), RateTuple(24, 1, 24),
            RateTuple(18, 1, 18), RateTuple(12, 1, 12),
            RateTuple(11, 1, 11), RateTuple(9, 1, 9),
            RateTuple(6, 1, 6), RateTuple(5.5, 1, 5.5),
            RateTuple(2, 1, 2), RateTuple(1, 1, 1)],
        "legacy_5GHz": [
            RateTuple(54, 1, 54), RateTuple(48, 1, 48),
            RateTuple(36, 1, 36), RateTuple(24, 1, 24),
            RateTuple(18, 1, 18), RateTuple(12, 1, 12),
            RateTuple(9, 1, 9), RateTuple(6, 1, 6)],
        "HT20": [
            RateTuple(7, 1, 72.2), RateTuple(6, 1, 65),
            RateTuple(5, 1, 57.8), RateTuple(4, 1, 43.3),
            RateTuple(3, 1, 26), RateTuple(2, 1, 21.7),
            RateTuple(1, 1, 14.4), RateTuple(0, 1, 7.2),
            RateTuple(15, 2, 144.4), RateTuple(14, 2, 130),
            RateTuple(13, 2, 115.6), RateTuple(12, 2, 86.7),
            RateTuple(11, 2, 57.8), RateTuple(10, 2, 43.4),
            RateTuple(9, 2, 28.9), RateTuple(8, 2, 14.4)],
        "VHT20": [
            RateTuple(9, 1, 96), RateTuple(8, 1, 86.7),
            RateTuple(7, 1, 72.2), RateTuple(6, 1, 65),
            RateTuple(5, 1, 57.8), RateTuple(4, 1, 43.3),
            RateTuple(3, 1, 28.9), RateTuple(2, 1, 21.7),
            RateTuple(1, 1, 14.4), RateTuple(0, 1, 7.2),
            RateTuple(9, 2, 192), RateTuple(8, 2, 173.3),
            RateTuple(7, 2, 144.4), RateTuple(6, 2, 130.3),
            RateTuple(5, 2, 115.6), RateTuple(4, 2, 86.7),
            RateTuple(3, 2, 57.8), RateTuple(2, 2, 43.3),
            RateTuple(1, 2, 28.9), RateTuple(0, 2, 14.4)],
        "VHT40": [
            RateTuple(9, 1, 96), RateTuple(8, 1, 86.7),
            RateTuple(7, 1, 72.2), RateTuple(6, 1, 65),
            RateTuple(5, 1, 57.8), RateTuple(4, 1, 43.3),
            RateTuple(3, 1, 28.9), RateTuple(2, 1, 21.7),
            RateTuple(1, 1, 14.4), RateTuple(0, 1, 7.2),
            RateTuple(9, 2, 192), RateTuple(8, 2, 173.3),
            RateTuple(7, 2, 144.4), RateTuple(6, 2, 130.3),
            RateTuple(5, 2, 115.6), RateTuple(4, 2, 86.7),
            RateTuple(3, 2, 57.8), RateTuple(2, 2, 43.3),
            RateTuple(1, 2, 28.9), RateTuple(0, 2, 14.4)],
        "VHT80": [
            RateTuple(9, 1, 96), RateTuple(8, 1, 86.7),
            RateTuple(7, 1, 72.2), RateTuple(6, 1, 65),
            RateTuple(5, 1, 57.8), RateTuple(4, 1, 43.3),
            RateTuple(3, 1, 28.9), RateTuple(2, 1, 21.7),
            RateTuple(1, 1, 14.4), RateTuple(0, 1, 7.2),
            RateTuple(9, 2, 192), RateTuple(8, 2, 173.3),
            RateTuple(7, 2, 144.4), RateTuple(6, 2, 130.3),
            RateTuple(5, 2, 115.6), RateTuple(4, 2, 86.7),
            RateTuple(3, 2, 57.8), RateTuple(2, 2, 43.3),
            RateTuple(1, 2, 28.9), RateTuple(0, 2, 14.4)],
    }
    #yapf:enable

    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.failure_count_metric = BlackboxMetricLogger.for_test_case(
            metric_name='sensitivity')

    def setup_class(self):
        """Initializes common test hardware and parameters.

        This function initializes hardwares and compiles parameters that are
        common to all tests in this class.
        """
        self.client_dut = self.android_devices[-1]
        req_params = [
            "RetailAccessPoints", "sensitivity_test_params", "testbed_params",
            "RemoteServer"
        ]
        opt_params = ["main_network", "golden_files_list"]
        self.unpack_userparams(req_params, opt_params)
        self.testclass_params = self.sensitivity_test_params
        self.num_atten = self.attenuators[0].instrument.num_atten
        self.ping_server = ssh.connection.SshConnection(
            ssh.settings.from_config(self.RemoteServer[0]["ssh_config"]))
        self.iperf_server = self.iperf_servers[0]
        self.iperf_client = self.iperf_clients[0]
        self.access_point = retail_ap.create(self.RetailAccessPoints)[0]
        self.log.info("Access Point Configuration: {}".format(
            self.access_point.ap_settings))
        self.log_path = os.path.join(logging.log_path, "results")
        utils.create_dir(self.log_path)
        if not hasattr(self, "golden_files_list"):
            self.golden_files_list = [
                os.path.join(self.testbed_params["golden_results_path"], file)
                for file in os.listdir(
                    self.testbed_params["golden_results_path"])
            ]
        self.testclass_results = []

        # Turn WiFi ON
        for dev in self.android_devices:
            wutils.wifi_toggle_state(dev, True)

    def teardown_class(self):
        # Turn WiFi OFF
        for dev in self.android_devices:
            wutils.wifi_toggle_state(dev, False)
        self.process_testclass_results()

    def pass_fail_check(self, result):
        """Checks sensitivity against golden results and decides on pass/fail.

        Args:
            result: dict containing attenuation, throughput and other meta
            data
        """
        try:
            golden_path = next(file_name
                               for file_name in self.golden_files_list
                               if "sensitivity_targets" in file_name)
            with open(golden_path, 'r') as golden_file:
                golden_results = json.load(golden_file)
            golden_sensitivity = golden_results[
                self.current_test_name]["sensitivity"]
        except:
            golden_sensitivity = float("nan")

        result_string = ("Througput = {}%, Sensitivity = {}."
                         "Target Sensitivity = {}".format(
                             result["peak_throughput_pct"],
                             result["sensitivity"], golden_sensitivity))
        if result["peak_throughput_pct"] < 100:
            self.log.warning("Result unreliable. Peak rate unstable")
        if result["sensitivity"] - golden_sensitivity < self.testclass_params[
                "sensitivity_tolerance"]:
            asserts.explicit_pass("Test Passed. {}".format(result_string))
        else:
            asserts.fail("Test Failed. {}".format(result_string))

    def process_testclass_results(self):
        """Saves and plots test results from all executed test cases."""
        # write json output
        testclass_results_dict = collections.OrderedDict()
        id_fields = ["mode", "rate", "num_streams", "chain_mask"]
        channels_tested = []
        for result in self.testclass_results:
            testcase_params = self.parse_test_params(result["test_name"])
            test_id = collections.OrderedDict(
                (key, value) for key, value in testcase_params.items()
                if key in id_fields)
            test_id = tuple(test_id.items())
            if test_id not in testclass_results_dict:
                testclass_results_dict[test_id] = collections.OrderedDict()
            channel = testcase_params["channel"]
            if channel not in channels_tested:
                channels_tested.append(channel)
            if result["peak_throughput_pct"] == 100:
                testclass_results_dict[test_id][channel] = result[
                    "sensitivity"]
            else:
                testclass_results_dict[test_id][channel] = ''

        # write csv
        csv_header = ["Mode", "MCS", "Streams", "Chain", "Rate (Mbps)"]
        for channel in channels_tested:
            csv_header.append("Ch. " + str(channel))
        results_file_path = os.path.join(self.log_path, 'results.csv')
        with open(results_file_path, mode='w') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=csv_header)
            writer.writeheader()
            for test_id, test_results in testclass_results_dict.items():
                test_id_dict = dict(test_id)
                if "legacy" in test_id_dict["mode"]:
                    rate_list = self.VALID_RATES["legacy_2GHz"]
                else:
                    rate_list = self.VALID_RATES[test_id_dict["mode"]]
                data_rate = next(rate.data_rate for rate in rate_list
                                 if rate[:-1] == (test_id_dict["rate"],
                                                  test_id_dict["num_streams"]))
                row_value = {
                    "Mode": test_id_dict["mode"],
                    "MCS": test_id_dict["rate"],
                    "Streams": test_id_dict["num_streams"],
                    "Chain": test_id_dict["chain_mask"],
                    "Rate (Mbps)": data_rate,
                }
                for channel in channels_tested:
                    row_value["Ch. " + str(channel)] = test_results.pop(
                        channel, " ")
                writer.writerow(row_value)

        if not self.testclass_params["traffic_type"].lower() == "ping":
            WifiRvrTest.process_testclass_results(self)

    def process_rvr_test_results(self, testcase_params, rvr_result):
        """Post processes RvR results to compute sensitivity.

        Takes in the results of the RvR tests and computes the sensitivity of
        the current rate by looking at the point at which throughput drops
        below the percentage specified in the config file. The function then
        calls on its parent class process_test_results to plot the result.

        Args:
            rvr_result: dict containing attenuation, throughput and other meta
            data
        """
        rvr_result["peak_throughput"] = max(rvr_result["throughput_receive"])
        rvr_result["peak_throughput_pct"] = 100
        throughput_check = [
            throughput < rvr_result["peak_throughput"] *
            (self.testclass_params["throughput_pct_at_sensitivity"] / 100)
            for throughput in rvr_result["throughput_receive"]
        ]
        consistency_check = [
            idx for idx in range(len(throughput_check))
            if all(throughput_check[idx:])
        ]
        rvr_result["atten_at_range"] = rvr_result["attenuation"][
            consistency_check[0] - 1]
        rvr_result["range"] = rvr_result["fixed_attenuation"] + (
            rvr_result["atten_at_range"])
        rvr_result["sensitivity"] = self.testclass_params["ap_tx_power"] + (
            self.testbed_params["ap_tx_power_offset"][str(
                testcase_params["channel"])] - rvr_result["range"])
        WifiRvrTest.process_test_results(self, rvr_result)

    def process_ping_test_results(self, testcase_params, ping_result):
        """Post processes RvR results to compute sensitivity.

        Takes in the results of the RvR tests and computes the sensitivity of
        the current rate by looking at the point at which throughput drops
        below the percentage specified in the config file. The function then
        calls on its parent class process_test_results to plot the result.

        Args:
            rvr_result: dict containing attenuation, throughput and other meta
            data
        """
        testcase_params["range_ping_loss_threshold"] = 100 - testcase_params[
            "throughput_pct_at_sensitivity"]
        WifiPingTest.process_ping_results(self, testcase_params, ping_result)
        ping_result["sensitivity"] = self.testclass_params["ap_tx_power"] + (
            self.testbed_params["ap_tx_power_offset"][str(
                testcase_params["channel"])] - ping_result["range"])

    def setup_sensitivity_test(self, testcase_params):
        if testcase_params["traffic_type"].lower() == "ping":
            self.setup_ping_test(testcase_params)
            self.run_sensitivity_test = self.run_ping_test
            self.process_sensitivity_test_results = (
                self.process_ping_test_results)
        else:
            self.setup_rvr_test(testcase_params)
            self.run_sensitivity_test = self.run_rvr_test
            self.process_sensitivity_test_results = (
                self.process_rvr_test_results)

    def setup_ap(self, testcase_params):
        """Sets up the AP and attenuator to compensate for AP chain imbalance.

        Args:
            testcase_params: dict containing AP and other test params
        """
        band = self.access_point.band_lookup_by_channel(
            testcase_params["channel"])
        if "2G" in band:
            frequency = wutils.WifiEnums.channel_2G_to_freq[
                testcase_params["channel"]]
        else:
            frequency = wutils.WifiEnums.channel_5G_to_freq[
                testcase_params["channel"]]
        if frequency in wutils.WifiEnums.DFS_5G_FREQUENCIES:
            self.access_point.set_region(self.testbed_params["DFS_region"])
        else:
            self.access_point.set_region(self.testbed_params["default_region"])
        self.access_point.set_channel(band, testcase_params["channel"])
        self.access_point.set_bandwidth(band, testcase_params["mode"])
        self.access_point.set_power(band, testcase_params["ap_tx_power"])
        self.access_point.set_rate(
            band, testcase_params["mode"], testcase_params["num_streams"],
            testcase_params["rate"], testcase_params["short_gi"])
        # Set attenuator offsets and set attenuators to initial condition
        atten_offsets = self.testbed_params['chain_offset'][str(
            testcase_params['channel'])]
        for atten in self.attenuators:
            if 'AP-Chain-0' in atten.path:
                atten.offset = atten_offsets[0]
            elif 'AP-Chain-1' in atten.path:
                atten.offset = atten_offsets[1]
        self.log.info("Access Point Configuration: {}".format(
            self.access_point.ap_settings))

    def setup_dut(self, testcase_params):
        """Sets up the DUT in the configuration required by the test.

        Args:
            testcase_params: dict containing AP and other test params
        """
        band = self.access_point.band_lookup_by_channel(
            testcase_params["channel"])
        wutils.reset_wifi(self.client_dut)
        self.client_dut.droid.wifiSetCountryCode(
            self.testclass_params["country_code"])
        self.main_network[band]["channel"] = testcase_params["channel"]
        wutils.wifi_connect(
            self.client_dut,
            self.main_network[band],
            num_of_tries=5,
            check_connectivity=False)
        self.dut_ip = self.client_dut.droid.connectivityGetIPv4Addresses(
            "wlan0")[0]
        atten_dut_chain_map = wputils.get_atten_dut_chain_map(
            self.attenuators, self.client_dut, self.ping_server, self.dut_ip)
        for idx, atten in enumerate(self.attenuators):
            if atten_dut_chain_map[idx] == testcase_params["attenuated_chain"]:
                atten.offset = atten.instrument.max_atten

    def get_start_atten(self):
        """Gets the starting attenuation for this sensitivity test.

        The function gets the starting attenuation by checking whether a test
        as the next higher MCS has been executed. If so it sets the starting
        point a configurable number of dBs below the next MCS's sensitivity.

        Returns:
            start_atten: starting attenuation for current test
        """
        # Get the current and reference test config. The reference test is the
        # one performed at the current MCS+1
        current_test_params = self.parse_test_params(self.current_test_name)
        current_rate = current_test_params["rate"]
        ref_test_params = current_test_params.copy()
        if "legacy" in current_test_params["mode"]:
            if current_test_params["channel"] <= 13:
                rate_list = self.VALID_RATES["legacy_2GHz"]
            else:
                rate_list = self.VALID_RATES["legacy_5GHz"]
            ref_index = max(
                0,
                rate_list.index(self.RateTuple(current_rate, 1, current_rate))
                - 1)
            ref_test_params["rate"] = rate_list[ref_index].mcs
        else:
            ref_test_params["rate"] = current_rate + 1

        # Check if reference test has been run and set attenuation accordingly
        previous_params = [
            self.parse_test_params(result["test_name"])
            for result in self.testclass_results
        ]
        try:
            ref_index = previous_params.index(ref_test_params)
            start_atten = self.testclass_results[ref_index][
                "atten_at_range"] - (
                    self.testclass_params["adjacent_mcs_range_gap"])
        except ValueError:
            print("Reference test not found. Starting from {} dB".format(
                self.testclass_params["atten_start"]))
            start_atten = self.testclass_params["atten_start"]
        return start_atten

    def parse_test_params(self, test_name):
        """Function that generates test params based on the test name."""
        test_name_params = test_name.split("_")
        testcase_params = collections.OrderedDict()
        testcase_params["channel"] = int(test_name_params[2][2:])
        testcase_params["mode"] = test_name_params[3]

        if "legacy" in testcase_params["mode"].lower():
            testcase_params["rate"] = float(
                str(test_name_params[4]).replace("p", "."))
        else:
            testcase_params["rate"] = int(test_name_params[4][3:])
        testcase_params["num_streams"] = int(test_name_params[5][3:])
        testcase_params["short_gi"] = 1
        testcase_params["chain_mask"] = test_name_params[6][2:]
        if testcase_params["chain_mask"] in ["0", "1"]:
            testcase_params["attenuated_chain"] = "DUT-Chain-{}".format(
                1 if testcase_params['chain_mask'] == "0" else 0)
        else:
            testcase_params["attenuated_chain"] = None

        if self.testclass_params["traffic_type"] == "UDP":
            testcase_params["iperf_args"] = '-i 1 -t {} -J -u -b {}'.format(
                self.testclass_params["iperf_duration"],
                self.testclass_params["UDP_rates"][testcase_params["mode"]])
        elif self.testclass_params["traffic_type"] == "TCP":
            testcase_params["iperf_args"] = '-i 1 -t {} -J'.format(
                self.testclass_params["iperf_duration"])

        if self.testclass_params["traffic_type"] != "ping" and isinstance(
                self.iperf_client, iperf_client.IPerfClientOverAdb):
            testcase_params["iperf_args"] += ' -R'
            testcase_params["use_client_output"] = True
        else:
            testcase_params["use_client_output"] = False

        return testcase_params

    def _test_sensitivity(self):
        """ Function that gets called for each test case

        The function gets called in each rvr test case. The function customizes
        the rvr test based on the test name of the test that called it
        """
        # Compile test parameters from config and test name
        testcase_params = self.parse_test_params(self.current_test_name)
        testcase_params.update(self.testclass_params)
        testcase_params["atten_start"] = self.get_start_atten()
        num_atten_steps = int(
            (testcase_params["atten_stop"] - testcase_params["atten_start"]) /
            testcase_params["atten_step"])
        testcase_params["atten_range"] = [
            testcase_params["atten_start"] + x * testcase_params["atten_step"]
            for x in range(0, num_atten_steps)
        ]

        # Prepare devices and run test
        self.setup_sensitivity_test(testcase_params)
        result = self.run_sensitivity_test(testcase_params)
        self.process_sensitivity_test_results(testcase_params, result)

        # Post-process results
        self.testclass_results.append(result)
        self.pass_fail_check(result)

    def generate_test_cases(self, channels, chain_mask):
        """Function that auto-generates test cases for a test class."""
        testcase_wrapper = self._test_sensitivity
        for channel in channels:
            for mode in self.VALID_TEST_CONFIGS[channel]:
                if "VHT" in mode:
                    rates = self.VALID_RATES[mode]
                elif "HT" in mode:
                    rates = self.VALID_RATES[mode]
                elif "legacy" in mode and channel < 14:
                    rates = self.VALID_RATES["legacy_2GHz"]
                elif "legacy" in mode and channel > 14:
                    rates = self.VALID_RATES["legacy_5GHz"]
                else:
                    raise ValueError("Invalid test mode.")
                for chain, rate in itertools.product(chain_mask, rates):
                    if str(chain) in ["0", "1"] and rate[1] == 2:
                        # Do not test 2-stream rates in single chain mode
                        continue
                    if "legacy" in mode:
                        testcase_name = ("test_sensitivity_ch{}_{}_{}_nss{}"
                                         "_ch{}".format(
                                             channel, mode,
                                             str(rate.mcs).replace(".", "p"),
                                             rate.streams, chain))
                    else:
                        testcase_name = ("test_sensitivity_ch{}_{}_mcs{}_nss{}"
                                         "_ch{}".format(
                                             channel, mode, rate.mcs,
                                             rate.streams, chain))
                    setattr(self, testcase_name, testcase_wrapper)
                    self.tests.append(testcase_name)


class WifiSensitivity_AllChannels_Test(WifiSensitivityTest):
    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.generate_test_cases(
            [1, 2, 6, 10, 11, 36, 40, 44, 48, 149, 153, 157, 161],
            ["0", "1", "2x2"])


class WifiSensitivity_2GHz_Test(WifiSensitivityTest):
    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.generate_test_cases([1, 2, 6, 10, 11], ["0", "1", "2x2"])


class WifiSensitivity_5GHz_Test(WifiSensitivityTest):
    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.generate_test_cases([36, 40, 44, 48, 149, 153, 157, 161],
                                 ["0", "1", "2x2"])


class WifiSensitivity_UNII1_Test(WifiSensitivityTest):
    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.generate_test_cases([36, 40, 44, 48], ["0", "1", "2x2"])


class WifiSensitivity_UNII3_Test(WifiSensitivityTest):
    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.generate_test_cases([149, 153, 157, 161], ["0", "1", "2x2"])


class WifiSensitivity_ch1_Test(WifiSensitivityTest):
    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.generate_test_cases([1], ["0", "1", "2x2"])


class WifiSensitivity_ch2_Test(WifiSensitivityTest):
    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.generate_test_cases([2], ["0", "1", "2x2"])


class WifiSensitivity_ch6_Test(WifiSensitivityTest):
    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.generate_test_cases([6], ["0", "1", "2x2"])


class WifiSensitivity_ch10_Test(WifiSensitivityTest):
    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.generate_test_cases([10], ["0", "1", "2x2"])


class WifiSensitivity_ch11_Test(WifiSensitivityTest):
    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.generate_test_cases([11], ["0", "1", "2x2"])


class WifiSensitivity_ch36_Test(WifiSensitivityTest):
    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.generate_test_cases([36], ["0", "1", "2x2"])


class WifiSensitivity_ch40_Test(WifiSensitivityTest):
    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.generate_test_cases([40], ["0", "1", "2x2"])


class WifiSensitivity_ch44_Test(WifiSensitivityTest):
    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.generate_test_cases([44], ["0", "1", "2x2"])


class WifiSensitivity_ch48_Test(WifiSensitivityTest):
    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.generate_test_cases([48], ["0", "1", "2x2"])


class WifiSensitivity_ch149_Test(WifiSensitivityTest):
    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.generate_test_cases([149], ["0", "1", "2x2"])


class WifiSensitivity_ch153_Test(WifiSensitivityTest):
    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.generate_test_cases([153], ["0", "1", "2x2"])


class WifiSensitivity_ch157_Test(WifiSensitivityTest):
    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.generate_test_cases([157], ["0", "1", "2x2"])


class WifiSensitivity_ch161_Test(WifiSensitivityTest):
    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.generate_test_cases([161], ["0", "1", "2x2"])
