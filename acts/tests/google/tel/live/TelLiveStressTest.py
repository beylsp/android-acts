#!/usr/bin/env python3.4
#
#   Copyright 2017 - Google
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
"""
    Test Script for Telephony Stress Call Test
"""

import collections
import json
import os
import random
import time

from acts import utils
from acts.asserts import fail
from acts.test_decorators import test_tracker_info
from acts.test_utils.tel.TelephonyBaseTest import TelephonyBaseTest
from acts.test_utils.tel.tel_defines import MAX_WAIT_TIME_SMS_RECEIVE
from acts.test_utils.tel.tel_defines import NETWORK_MODE_WCDMA_ONLY
from acts.test_utils.tel.tel_defines import NETWORK_MODE_GLOBAL
from acts.test_utils.tel.tel_defines import NETWORK_MODE_CDMA
from acts.test_utils.tel.tel_defines import NETWORK_MODE_GSM_ONLY
from acts.test_utils.tel.tel_defines import NETWORK_MODE_TDSCDMA_GSM_WCDMA
from acts.test_utils.tel.tel_defines import NETWORK_MODE_LTE_CDMA_EVDO_GSM_WCDMA
from acts.test_utils.tel.tel_defines import WAIT_TIME_AFTER_MODE_CHANGE
from acts.test_utils.tel.tel_defines import WFC_MODE_WIFI_PREFERRED
from acts.test_utils.tel.tel_test_utils import STORY_LINE
from acts.test_utils.tel.tel_test_utils import active_file_download_test
from acts.test_utils.tel.tel_test_utils import is_phone_in_call
from acts.test_utils.tel.tel_test_utils import call_setup_teardown
from acts.test_utils.tel.tel_test_utils import ensure_wifi_connected
from acts.test_utils.tel.tel_test_utils import hangup_call
from acts.test_utils.tel.tel_test_utils import hangup_call_by_adb
from acts.test_utils.tel.tel_test_utils import initiate_call
from acts.test_utils.tel.tel_test_utils import is_voice_attached
from acts.test_utils.tel.tel_test_utils import run_multithread_func
from acts.test_utils.tel.tel_test_utils import set_wfc_mode
from acts.test_utils.tel.tel_test_utils import sms_send_receive_verify
from acts.test_utils.tel.tel_test_utils import start_qxdm_loggers
from acts.test_utils.tel.tel_test_utils import mms_send_receive_verify
from acts.test_utils.tel.tel_test_utils import set_preferred_network_mode_pref
from acts.test_utils.tel.tel_test_utils import verify_internet_connection
from acts.test_utils.tel.tel_test_utils import wait_for_in_call_active
from acts.test_utils.tel.tel_voice_utils import is_phone_in_call_3g
from acts.test_utils.tel.tel_voice_utils import is_phone_in_call_2g
from acts.test_utils.tel.tel_voice_utils import is_phone_in_call_csfb
from acts.test_utils.tel.tel_voice_utils import is_phone_in_call_iwlan
from acts.test_utils.tel.tel_voice_utils import is_phone_in_call_volte
from acts.test_utils.tel.tel_voice_utils import phone_setup_csfb
from acts.test_utils.tel.tel_voice_utils import phone_setup_iwlan
from acts.test_utils.tel.tel_voice_utils import phone_setup_voice_3g
from acts.test_utils.tel.tel_voice_utils import phone_setup_voice_2g
from acts.test_utils.tel.tel_voice_utils import phone_setup_volte
from acts.test_utils.tel.tel_voice_utils import phone_idle_iwlan
from acts.test_utils.tel.tel_voice_utils import get_current_voice_rat
from acts.utils import get_current_epoch_time
from acts.utils import rand_ascii_str

EXCEPTION_TOLERANCE = 5
BINDER_LOGS = ["/sys/kernel/debug/binder"]


class TelLiveStressTest(TelephonyBaseTest):
    def setup_class(self):
        super(TelLiveStressTest, self).setup_class()
        self.dut = self.android_devices[0]
        self.single_phone_test = self.user_params.get("single_phone_test",
                                                      False)
        # supported file download methods: chrome, sl4a, curl
        self.file_download_method = self.user_params.get(
            "file_download_method", "curl")
        self.get_binder_logs = self.user_params.get("get_binder_logs", False)
        if len(self.android_devices) == 1:
            self.single_phone_test = True
        if self.single_phone_test:
            self.android_devices = self.android_devices[:1]
            self.call_server_number = self.user_params.get(
                "call_server_number", STORY_LINE)
            if self.file_download_method == "sl4a":
                # with single device, do not use sl4a file download
                # due to stability issue
                self.file_download_method = "curl"
        else:
            self.android_devices = self.android_devices[:2]
        self.user_params["telephony_auto_rerun"] = 0
        self.phone_call_iteration = int(
            self.user_params.get("phone_call_iteration", 500))
        self.max_phone_call_duration = int(
            self.user_params.get("max_phone_call_duration", 600))
        self.min_sleep_time = int(self.user_params.get("min_sleep_time", 10))
        self.max_sleep_time = int(self.user_params.get("max_sleep_time", 60))
        self.max_run_time = int(self.user_params.get("max_run_time", 14400))
        self.max_sms_length = int(self.user_params.get("max_sms_length", 1000))
        self.max_mms_length = int(self.user_params.get("max_mms_length", 160))
        self.min_sms_length = int(self.user_params.get("min_sms_length", 1))
        self.min_mms_length = int(self.user_params.get("min_mms_length", 1))
        self.min_phone_call_duration = int(
            self.user_params.get("min_phone_call_duration", 10))
        self.crash_check_interval = int(
            self.user_params.get("crash_check_interval", 300))

        return True

    def setup_test(self):
        super(TelLiveStressTest, self).setup_test()
        self.result_info = collections.defaultdict(int)
        self._init_perf_json()

    def on_fail(self, test_name, begin_time):
        pass

    def _setup_wfc(self):
        for ad in self.android_devices:
            if not ensure_wifi_connected(
                    self.log,
                    ad,
                    self.wifi_network_ssid,
                    self.wifi_network_pass,
                    retries=3):
                ad.log.error("Bringing up Wifi connection fails.")
                return False
            ad.log.info("Phone WIFI is connected successfully.")
            if not set_wfc_mode(self.log, ad, WFC_MODE_WIFI_PREFERRED):
                ad.log.error("Phone failed to enable Wifi-Calling.")
                return False
            ad.log.info("Phone is set in Wifi-Calling successfully.")
            if not phone_idle_iwlan(self.log, ad):
                ad.log.error("Phone is not in WFC enabled state.")
                return False
            ad.log.info("Phone is in WFC enabled state.")
        return True

    def _setup_wfc_apm(self):
        for ad in self.android_devices:
            if not phone_setup_iwlan(
                    self.log, ad, True, WFC_MODE_WIFI_PREFERRED,
                    self.wifi_network_ssid, self.wifi_network_pass):
                ad.log.error("Failed to setup WFC.")
                return False
        return True

    def _setup_lte_volte_enabled(self):
        for ad in self.android_devices:
            if not phone_setup_volte(self.log, ad):
                ad.log.error("Phone failed to enable VoLTE.")
                return False
            ad.log.info("Phone VOLTE is enabled successfully.")
        return True

    def _setup_lte_volte_disabled(self):
        for ad in self.android_devices:
            if not phone_setup_csfb(self.log, ad):
                ad.log.error("Phone failed to setup CSFB.")
                return False
            ad.log.info("Phone VOLTE is disabled successfully.")
        return True

    def _setup_3g(self):
        for ad in self.android_devices:
            if not phone_setup_voice_3g(self.log, ad):
                ad.log.error("Phone failed to setup 3g.")
                return False
            ad.log.info("Phone RAT 3G is enabled successfully.")
        return True

    def _setup_2g(self):
        for ad in self.android_devices:
            if not phone_setup_voice_2g(self.log, ad):
                ad.log.error("Phone failed to setup 2g.")
                return False
            ad.log.info("RAT 2G is enabled successfully.")
        return True

    def _send_message(self, max_wait_time=2 * MAX_WAIT_TIME_SMS_RECEIVE):
        if self.single_phone_test:
            ads = [self.dut, self.dut]
        else:
            ads = self.android_devices[:]
            random.shuffle(ads)
        selection = random.randrange(0, 2)
        message_type_map = {0: "SMS", 1: "MMS"}
        max_length_map = {0: self.max_sms_length, 1: self.max_mms_length}
        min_length_map = {0: self.min_sms_length, 1: self.min_mms_length}
        length = random.randrange(min_length_map[selection],
                                  max_length_map[selection] + 1)
        message_func_map = {
            0: sms_send_receive_verify,
            1: mms_send_receive_verify
        }
        message_type = message_type_map[selection]
        the_number = self.result_info["%s Total" % message_type] + 1
        begin_time = get_current_epoch_time()
        start_qxdm_loggers(self.log, self.android_devices)
        log_msg = "The %s-th %s test: of length %s from %s to %s" % (
            the_number, message_type, length, ads[0].serial, ads[1].serial)
        self.log.info(log_msg)
        for ad in self.android_devices:
            if not getattr(ad, "messaging_droid", None):
                ad.messaging_droid, ad.messaging_ed = ad.get_droid()
                ad.messaging_ed.start()
            else:
                try:
                    if not ad.messaging_droid.is_live:
                        ad.messaging_droid, ad.messaging_ed = ad.get_droid()
                        ad.messaging_ed.start()
                    else:
                        ad.messaging_ed.clear_all_events()
                except Exception:
                    ad.log.info("Create new sl4a session for messaging")
                    ad.messaging_droid, ad.messaging_ed = ad.get_droid()
                    ad.messaging_ed.start()
            ad.messaging_droid.logI(log_msg)
        text = "%s: " % log_msg
        text_length = len(text)
        if length < text_length:
            text = text[:length]
        else:
            text += rand_ascii_str(length - text_length)
        message_content_map = {0: [text], 1: [(log_msg, text, None)]}
        incall_non_ims = False
        for ad in self.android_devices:
            if ad.droid.telecomIsInCall() and (
                    not ad.droid.telephonyIsImsRegistered()):
                incall_non_ims = True
                break

        if not message_func_map[selection](self.log, ads[0], ads[1],
                                           message_content_map[selection],
                                           max_wait_time):
            self.result_info["%s Total" % message_type] += 1
            if message_type == "SMS":
                self.log.error("%s fails", log_msg)
                self.result_info["%s Failure" % message_type] += 1
                try:
                    self._take_bug_report("%s_%s_No_%s_failure" %
                                          (self.test_name, message_type,
                                           the_number), begin_time)
                except Exception as e:
                    self.log.exception(e)
            else:
                if incall_non_ims:
                    self.log.info(
                        "Device not in IMS, MMS in call is not support")
                    self.result_info["Expected In-call MMS failure"] += 1
                    return True
                else:
                    self.log.error("%s fails", log_msg)
                    self.result_info["MMS Failure"] += 1
                    if self.result_info["MMS Failure"] == 1:
                        try:
                            self._take_bug_report("%s_%s_No_%s_failure" %
                                                  (self.test_name,
                                                   message_type, the_number),
                                                  begin_time)
                        except Exception as e:
                            self.log.exception(e)
            return False
        else:
            self.result_info["%s Total" % message_type] += 1
            self.log.info("%s succeed", log_msg)
            self.result_info["%s Success" % message_type] += 1
            return True

    def _make_phone_call(self, call_verification_func=None):
        ads = self.android_devices[:]
        if not self.single_phone_test:
            random.shuffle(ads)
        for ad in ads:
            hangup_call_by_adb(ad)
        the_number = self.result_info["Call Total"] + 1
        duration = random.randrange(self.min_phone_call_duration,
                                    self.max_phone_call_duration)
        result = True
        if self.single_phone_test:
            log_msg = "The %s-th phone call test for %ssec duration" % (
                the_number, duration)
        else:
            log_msg = "The %s-th phone call test from %s to %s for %ssec" % (
                the_number, ads[0].serial, ads[1].serial, duration)
        self.log.info(log_msg)
        for ad in self.android_devices:
            if not getattr(ad, "droid", None):
                ad.droid, ad.ed = ad.get_droid()
                ad.ed.start()
            else:
                try:
                    if not ad.droid.is_live:
                        ad.droid, ad.ed = ad.get_droid()
                        ad.ed.start()
                    else:
                        ad.ed.clear_all_events()
                except Exception:
                    ad.log.info("Create new sl4a session for phone call")
                    ad.droid, ad.ed = ad.get_droid()
                    ad.ed.start()
            ad.droid.logI(log_msg)
        begin_time = get_current_epoch_time()
        start_qxdm_loggers(self.log, self.android_devices, begin_time)
        failure_reasons = set()
        rat_change = None
        if self.single_phone_test:
            call_setup_result = initiate_call(
                self.log, self.dut,
                self.call_server_number) and wait_for_in_call_active(
                    self.dut, 60, 3)
        else:
            call_setup_result = call_setup_teardown(
                self.log,
                ads[0],
                ads[1],
                ad_hangup=None,
                verify_caller_func=call_verification_func,
                verify_callee_func=call_verification_func,
                wait_time_in_call=0)
        if not call_setup_result:
            self.log.error("%s: Setup Call failed.", log_msg)
            failure_reasons.add("Setup")
            result = False
        else:
            elapsed_time = 0
            check_interval = 5
            while (elapsed_time < duration):
                check_interval = min(check_interval, duration - elapsed_time)
                time.sleep(check_interval)
                elapsed_time += check_interval
                time_message = "at <%s>/<%s> second." % (elapsed_time,
                                                         duration)
                for ad in ads:
                    if not call_verification_func(self.log, ad):
                        ad.log.warning("Call is NOT in correct %s state at %s",
                                       call_verification_func.__name__,
                                       time_message)
                        if call_verification_func.__name__ == "is_phone_in_call_iwlan":
                            if is_phone_in_call(self.log, ad):
                                if getattr(ad, "data_rat_state_error_count",
                                           0) < 1:
                                    setattr(ad, "data_rat_state_error_count",
                                            1)
                                    continue
                        failure_reasons.add("Maintenance")
                        reasons = ad.search_logcat(
                            "qcril_qmi_voice_map_qmi_to_ril_last_call_failure_cause",
                            begin_time)
                        if reasons:
                            ad.log.info(reasons[-1]["log_message"])
                        hangup_call(self.log, ads[0])
                        result = False
                    else:
                        ad.log.info("Call is in correct %s state at %s",
                                    call_verification_func.__name__,
                                    time_message)
                if not result:
                    break
        if not hangup_call(self.log, ads[0]):
            time.sleep(10)
            for ad in ads:
                if ad.droid.telecomIsInCall():
                    ad.log.error("Still in call after hungup")
                    failure_reasons.add("Teardown")
                    result = False
        self.result_info["Call Total"] += 1
        if not result:
            self.log.info("%s test failed", log_msg)
            for reason in failure_reasons:
                self.result_info["Call %s Failure" % reason] += 1
            test_name = "%s_call_No_%s_%s_failure" % (
                self.test_name, the_number, "_".join(failure_reasons))
            for ad in ads:
                log_path = os.path.join(self.log_path, test_name,
                                        "%s_binder_logs" % ad.serial)
                utils.create_dir(log_path)
                ad.pull_files(BINDER_LOGS, log_path)
            try:
                self._take_bug_report(test_name, begin_time)
            except Exception as e:
                self.log.exception(e)
        else:
            self.log.info("%s test succeed", log_msg)
            self.result_info["Call Success"] += 1
            if self.get_binder_logs and self.result_info["Call Total"] % 50 == 0:
                test_name = "%s_call_No_%s_success_binder_logs" % (
                    self.test_name, the_number)
                for ad in ads:
                    log_path = os.path.join(self.log_path, test_name,
                                            "%s_binder_logs" % ad.serial)
                    utils.create_dir(log_path)
                    ad.pull_files(BINDER_LOGS, log_path)
        return result

    def _prefnetwork_mode_change(self, sub_id):
        # ModePref change to non-LTE
        begin_time = get_current_epoch_time()
        start_qxdm_loggers(self.log, self.android_devices)
        network_preference_list = [
            NETWORK_MODE_TDSCDMA_GSM_WCDMA, NETWORK_MODE_WCDMA_ONLY,
            NETWORK_MODE_GLOBAL, NETWORK_MODE_CDMA, NETWORK_MODE_GSM_ONLY
        ]
        network_preference = random.choice(network_preference_list)
        set_preferred_network_mode_pref(self.log, self.dut, sub_id,
                                        network_preference)
        time.sleep(WAIT_TIME_AFTER_MODE_CHANGE)
        self.dut.log.info("Current Voice RAT is %s",
                          get_current_voice_rat(self.log, self.dut))

        # ModePref change back to with LTE
        set_preferred_network_mode_pref(self.log, self.dut, sub_id,
                                        NETWORK_MODE_LTE_CDMA_EVDO_GSM_WCDMA)
        time.sleep(WAIT_TIME_AFTER_MODE_CHANGE)
        rat = get_current_voice_rat(self.log, self.dut)
        self.dut.log.info("Current Voice RAT is %s", rat)
        self.result_info["RAT Change Total"] += 1
        if rat != "LTE":
            self.result_info["RAT Change Failure"] += 1
            try:
                self._take_bug_report("%s_rat_change_failure" % self.test_name,
                                      begin_time)
            except Exception as e:
                self.log.exception(e)
            return False
        else:
            self.result_info["RAT Change Success"] += 1
            return True

    def _get_result_message(self):
        msg_list = [
            "%s: %s" % (count, self.result_info[count])
            for count in sorted(self.result_info.keys())
        ]
        return ", ".join(msg_list)

    def _write_perf_json(self):
        json_str = json.dumps(self.perf_data, indent=4, sort_keys=True)
        with open(self.perf_file, 'w') as f:
            f.write(json_str)

    def _init_perf_json(self):
        self.perf_file = os.path.join(self.log_path, "%s_perf_data_%s.json" %
                                      (self.test_name, self.begin_time))
        self.perf_data = self.android_devices[0].build_info.copy()
        self.perf_data["model"] = self.android_devices[0].model
        self._write_perf_json()

    def _update_perf_json(self):
        for result_key, result_value in self.result_info.items():
            self.perf_data[result_key] = result_value
        self._write_perf_json()

    def crash_check_test(self):
        failure = 0
        while time.time() < self.finishing_time:
            try:
                self.log.info(dict(self.result_info))
                self._update_perf_json()
                begin_time = get_current_epoch_time()
                run_time_in_seconds = (begin_time - self.begin_time) / 1000
                test_name = "%s_crash_%s_seconds_after_start" % (
                    self.test_name, run_time_in_seconds)
                time.sleep(self.crash_check_interval)
                for ad in self.android_devices:
                    crash_report = ad.check_crash_report(
                        test_name, begin_time, log_crash_report=True)
                    if crash_report:
                        ad.log.error("Find new crash reports %s", crash_report)
                        failure += 1
                        self.result_info["Crashes"] += 1
                        for crash in crash_report:
                            if "ramdump_modem" in crash:
                                self.result_info["Crashes-Modem"] += 1
                        try:
                            ad.take_bug_report(test_name, begin_time)
                        except Exception as e:
                            self.log.exception(e)
            except Exception as e:
                self.log.error("Exception error %s", str(e))
                self.result_info["Exception Errors"] += 1
            self.log.info("Crashes found: %s", failure)
            if self.result_info["Exception Errors"] >= EXCEPTION_TOLERANCE:
                self.log.error("Too many exception errors, quit test")
                return False
        if failure:
            return False
        else:
            return True

    def call_test(self, call_verification_func=None):
        while time.time() < self.finishing_time:
            try:
                self._make_phone_call(call_verification_func)
            except Exception as e:
                self.log.error("Exception error %s", str(e))
                self.result_info["Exception Errors"] += 1
            if self.result_info["Exception Errors"] >= EXCEPTION_TOLERANCE:
                self.log.error("Too many exception errors, quit test")
                return False
            self.log.info("%s", dict(self.result_info))
            time.sleep(
                random.randrange(self.min_sleep_time, self.max_sleep_time))
        if any([
                self.result_info["Call Setup Failure"],
                self.result_info["Call Maintenance Failure"],
                self.result_info["Call Teardown Failure"]
        ]):
            return False
        else:
            return True

    def message_test(self, max_wait_time=MAX_WAIT_TIME_SMS_RECEIVE):
        while time.time() < self.finishing_time:
            try:
                self._send_message(max_wait_time=max_wait_time)
            except Exception as e:
                self.log.error("Exception error %s", str(e))
                self.result_info["Exception Errors"] += 1
            self.log.info(dict(self.result_info))
            if self.result_info["Exception Errors"] >= EXCEPTION_TOLERANCE:
                self.log.error("Too many exception errors, quit test")
                return False
            time.sleep(
                random.randrange(self.min_sleep_time, self.max_sleep_time))
        if self.result_info["SMS Failure"] or (
                self.result_info["MMS Failure"] / self.result_info["MMS Total"]
                > 0.3):
            return False
        else:
            return True

    def _data_download(self):
        #file_names = ["5MB", "10MB", "20MB", "50MB", "200MB", "512MB", "1GB"]
        file_names = ["5MB", "10MB", "20MB", "50MB", "200MB"]
        begin_time = get_current_epoch_time()
        start_qxdm_loggers(self.log, self.android_devices)
        self.dut.log.info(dict(self.result_info))
        selection = random.randrange(0, len(file_names))
        file_name = file_names[selection]
        self.result_info["Internet Connection Check Total"] += 1
        if not verify_internet_connection(self.log, self.dut):
            self.result_info["Internet Connection Check Failure"] += 1
            test_name = "%s_internet_connection_No_%s_failure" % (
                self.test_name,
                self.result_info["Internet Connection Check Failure"])
            try:
                self._ad_take_extra_logs(self.dut, test_name, begin_time)
                self._ad_take_bugreport(self.dut, test_name, begin_time)
            except Exception as e:
                self.log.exception(e)
            return False
        else:
            self.result_info["Internet Connection Check Success"] += 1

        self.result_info["File Download Total"] += 1
        if not active_file_download_test(
                self.log, self.dut, file_name,
                method=self.file_download_method):
            self.result_info["File Download Failure"] += 1
            if self.result_info["File Download Failure"] == 1:
                try:
                    self._ad_take_extra_logs(
                        self.dut, "%s_file_download_failure" % self.test_name,
                        begin_time)
                    self._ad_take_bugreport(
                        self.dut, "%s_file_download_failure" % self.test_name,
                        begin_time)
                except Exception as e:
                    self.log.exception(e)
            return False
        else:
            self.result_info["File Download Success"] += 1
            return True

    def data_test(self):
        while time.time() < self.finishing_time:
            try:
                self._data_download()
            except Exception as e:
                self.log.error("Exception error %s", str(e))
                self.result_info["Exception Errors"] += 1
            self.log.info("%s", dict(self.result_info))
            if self.result_info["Exception Errors"] >= EXCEPTION_TOLERANCE:
                self.log.error("Too many exception errors, quit test")
                return False
            time.sleep(
                random.randrange(self.min_sleep_time, self.max_sleep_time))
        if self.result_info["Internet Connection Check Failure"]:
            return False
        else:
            return True

    def parallel_tests(self, setup_func=None, call_verification_func=None):
        self.log.info(self._get_result_message())
        if setup_func and not setup_func():
            msg = "Test setup %s failed" % setup_func.__name__
            self.log.error(msg)
            fail(msg)
        if not call_verification_func:
            call_verification_func = is_phone_in_call
        self.finishing_time = time.time() + self.max_run_time
        results = run_multithread_func(
            self.log, [(self.call_test, [call_verification_func]),
                       (self.message_test, []), (self.data_test, []),
                       (self.crash_check_test, [])])
        result_message = self._get_result_message()
        self.log.info(result_message)
        self._update_perf_json()
        self.result_detail = result_message
        return all(results)

    def volte_modechange_volte_test(self):
        sub_id = self.dut.droid.subscriptionGetDefaultSubId()
        while time.time() < self.finishing_time:
            try:
                run_multithread_func(
                    self.log,
                    [(self._data_download, []),
                     (self._make_phone_call, [is_phone_in_call_volte]),
                     (self._send_message, [])])
                self._prefnetwork_mode_change(sub_id)
            except Exception as e:
                self.log.error("Exception error %s", str(e))
                self.result_info["Exception Errors"] += 1
            self.log.info(dict(self.result_info))
            if self.result_info["Exception Errors"] >= EXCEPTION_TOLERANCE:
                self.log.error("Too many exception errors, quit test")
                return False
        if self.result_info["Call Failure"] or self.result_info["RAT Change Failure"] or self.result_info["SMS Failure"]:
            return False
        else:
            return True

    def parallel_with_network_change_tests(self, setup_func=None):
        if setup_func and not setup_func():
            self.log.error("Test setup %s failed", setup_func.__name__)
            return False
        self.finishing_time = time.time() + self.max_run_time
        results = run_multithread_func(self.log,
                                       [(self.volte_modechange_volte_test, []),
                                        (self.crash_check_test, [])])
        result_message = self._get_result_message()
        self.log.info(result_message)
        self._update_perf_json()
        self.result_detail = result_message
        return all(results)

    """ Tests Begin """

    @test_tracker_info(uuid="d035e5b9-476a-4e3d-b4e9-6fd86c51a68d")
    @TelephonyBaseTest.tel_test_wrap
    def test_default_parallel_stress(self):
        """ Default state stress test"""
        return self.parallel_tests()

    @test_tracker_info(uuid="c21e1f17-3282-4f0b-b527-19f048798098")
    @TelephonyBaseTest.tel_test_wrap
    def test_lte_volte_parallel_stress(self):
        """ VoLTE on stress test"""
        return self.parallel_tests(
            setup_func=self._setup_lte_volte_enabled,
            call_verification_func=is_phone_in_call_volte)

    @test_tracker_info(uuid="a317c23a-41e0-4ef8-af67-661451cfefcf")
    @TelephonyBaseTest.tel_test_wrap
    def test_csfb_parallel_stress(self):
        """ LTE non-VoLTE stress test"""
        return self.parallel_tests(
            setup_func=self._setup_lte_volte_disabled,
            call_verification_func=is_phone_in_call_csfb)

    @test_tracker_info(uuid="fdb791bf-c414-4333-9fa3-cc18c9b3b234")
    @TelephonyBaseTest.tel_test_wrap
    def test_wfc_parallel_stress(self):
        """ Wifi calling APM mode off stress test"""
        return self.parallel_tests(
            setup_func=self._setup_wfc,
            call_verification_func=is_phone_in_call_iwlan)

    @test_tracker_info(uuid="e334c1b3-4378-49bb-bf57-1573fa1b23fa")
    @TelephonyBaseTest.tel_test_wrap
    def test_wfc_apm_parallel_stress(self):
        """ Wifi calling in APM mode on stress test"""
        return self.parallel_tests(
            setup_func=self._setup_wfc_apm,
            call_verification_func=is_phone_in_call_iwlan)

    @test_tracker_info(uuid="4566eef6-55de-4ac8-87ee-58f2ef41a3e8")
    @TelephonyBaseTest.tel_test_wrap
    def test_3g_parallel_stress(self):
        """ 3G stress test"""
        return self.parallel_tests(
            setup_func=self._setup_3g,
            call_verification_func=is_phone_in_call_3g)

    @test_tracker_info(uuid="f34f1a31-3948-4675-8698-372a83b8088d")
    @TelephonyBaseTest.tel_test_wrap
    def test_call_2g_parallel_stress(self):
        """ 2G call stress test"""
        return self.parallel_tests(
            setup_func=self._setup_2g,
            call_verification_func=is_phone_in_call_2g)

    @test_tracker_info(uuid="af580fca-fea6-4ca5-b981-b8c710302d37")
    @TelephonyBaseTest.tel_test_wrap
    def test_volte_modeprefchange_parallel_stress(self):
        """ VoLTE Mode Pref call stress test"""
        return self.parallel_with_network_change_tests(
            setup_func=self._setup_lte_volte_enabled)

    """ Tests End """
