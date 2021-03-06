#!/usr/bin/env python3.4
#
# Copyright 2016 - The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import os
import traceback
from concurrent.futures import ThreadPoolExecutor

from acts import asserts
from acts import keys
from acts import logger
from acts import records
from acts import signals
from acts import tracelogger
from acts import utils

# Macro strings for test result reporting
TEST_CASE_TOKEN = "[Test Case]"
RESULT_LINE_TEMPLATE = TEST_CASE_TOKEN + " %s %s"


class Error(Exception):
    """Raised for exceptions that occured in BaseTestClass."""


class BaseTestClass(object):
    """Base class for all test classes to inherit from.

    This class gets all the controller objects from test_runner and executes
    the test cases requested within itself.

    Most attributes of this class are set at runtime based on the configuration
    provided.

    Attributes:
        tests: A list of strings, each representing a test case name.
        TAG: A string used to refer to a test class. Default is the test class
             name.
        log: A logger object used for logging.
        results: A records.TestResult object for aggregating test results from
                 the execution of test cases.
        current_test_name: A string that's the name of the test case currently
                           being executed. If no test is executing, this should
                           be None.
    """

    TAG = None

    def __init__(self, configs):
        self.tests = []
        if not self.TAG:
            self.TAG = self.__class__.__name__
        # Set all the controller objects and params.
        for name, value in configs.items():
            setattr(self, name, value)
        self.results = records.TestResult()
        self.current_test_name = None
        self.log = tracelogger.TraceLogger(self.log)
        self.size_limit_reached = False
        if 'android_devices' in self.__dict__:
            for ad in self.android_devices:
                if ad.droid:
                    utils.set_location_service(ad, False)
                    utils.sync_device_time(ad)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._exec_func(self.clean_up)

    def unpack_userparams(self,
                          req_param_names=[],
                          opt_param_names=[],
                          **kwargs):
        """An optional function that unpacks user defined parameters into
        individual variables.

        After unpacking, the params can be directly accessed with self.xxx.

        If a required param is not provided, an exception is raised. If an
        optional param is not provided, a warning line will be logged.

        To provide a param, add it in the config file or pass it in as a kwarg.
        If a param appears in both the config file and kwarg, the value in the
        config file is used.

        User params from the config file can also be directly accessed in
        self.user_params.

        Args:
            req_param_names: A list of names of the required user params.
            opt_param_names: A list of names of the optional user params.
            **kwargs: Arguments that provide default values.
                e.g. unpack_userparams(required_list, opt_list, arg_a="hello")
                     self.arg_a will be "hello" unless it is specified again in
                     required_list or opt_list.

        Raises:
            Error is raised if a required user params is not provided.
        """
        for k, v in kwargs.items():
            if k in self.user_params:
                v = self.user_params[k]
            setattr(self, k, v)
        for name in req_param_names:
            if hasattr(self, name):
                continue
            if name not in self.user_params:
                raise Error(("Missing required user param '%s' in test "
                             "configuration.") % name)
            setattr(self, name, self.user_params[name])
        for name in opt_param_names:
            if hasattr(self, name):
                continue
            if name in self.user_params:
                setattr(self, name, self.user_params[name])
            else:
                self.log.warning(("Missing optional user param '%s' in "
                                  "configuration, continue."), name)

        capablity_of_devices = utils.CapablityPerDevice
        if "additional_energy_info_models" in self.user_params:
            self.energy_info_models = (capablity_of_devices.energy_info_models
                                       + self.additional_energy_info_models)
        else:
            self.energy_info_models = capablity_of_devices.energy_info_models
        self.user_params["energy_info_models"] = self.energy_info_models

        if "additional_tdls_models" in self.user_params:
            self.tdls_models = (capablity_of_devices.energy_info_models +
                                self.additional_tdls_models)
        else:
            self.tdls_models = capablity_of_devices.energy_info_models
        self.user_params["tdls_models"] = self.tdls_models

    def _setup_class(self):
        """Proxy function to guarantee the base implementation of setup_class
        is called.
        """
        return self.setup_class()

    def setup_class(self):
        """Setup function that will be called before executing any test case in
        the test class.

        To signal setup failure, return False or raise an exception. If
        exceptions were raised, the stack trace would appear in log, but the
        exceptions would not propagate to upper levels.

        Implementation is optional.
        """

    def teardown_class(self):
        """Teardown function that will be called after all the selected test
        cases in the test class have been executed.

        Implementation is optional.
        """

    def _setup_test(self, test_name):
        """Proxy function to guarantee the base implementation of setup_test is
        called.
        """
        self.current_test_name = test_name
        try:
            # Write test start token to adb log if android device is attached.
            if hasattr(self, 'android_devices'):
                for ad in self.android_devices:
                    if not ad.skip_sl4a:
                        ad.droid.logV("%s BEGIN %s" % (TEST_CASE_TOKEN,
                                                       test_name))
        except Exception as e:
            self.log.warning(
                'Unable to send BEGIN log command to all devices.')
            self.log.warning('Error: %s' % e)
        return self.setup_test()

    def setup_test(self):
        """Setup function that will be called every time before executing each
        test case in the test class.

        To signal setup failure, return False or raise an exception. If
        exceptions were raised, the stack trace would appear in log, but the
        exceptions would not propagate to upper levels.

        Implementation is optional.
        """
        return True

    def _teardown_test(self, test_name):
        """Proxy function to guarantee the base implementation of teardown_test
        is called.
        """
        self.log.debug('Tearing down test %s' % test_name)
        try:
            # Write test end token to adb log if android device is attached.
            for ad in self.android_devices:
                ad.droid.logV("%s END %s" % (TEST_CASE_TOKEN, test_name))
        except Exception as e:
            self.log.warning('Unable to send END log command to all devices.')
            self.log.warning('Error: %s' % e)
        try:
            self.teardown_test()
        finally:
            self.current_test_name = None

    def teardown_test(self):
        """Teardown function that will be called every time a test case has
        been executed.

        Implementation is optional.
        """

    def _on_fail(self, record):
        """Proxy function to guarantee the base implementation of on_fail is
        called.

        Args:
            record: The records.TestResultRecord object for the failed test
                    case.
        """
        if record.details:
            self.log.error(record.details)
        self.log.info(RESULT_LINE_TEMPLATE, record.test_name, record.result)
        self.on_fail(record.test_name, record.begin_time)

    def on_fail(self, test_name, begin_time):
        """A function that is executed upon a test case failure.

        User implementation is optional.

        Args:
            test_name: Name of the test that triggered this function.
            begin_time: Logline format timestamp taken when the test started.
        """

    def _on_pass(self, record):
        """Proxy function to guarantee the base implementation of on_pass is
        called.

        Args:
            record: The records.TestResultRecord object for the passed test
                    case.
        """
        msg = record.details
        if msg:
            self.log.info(msg)
        self.log.info(RESULT_LINE_TEMPLATE, record.test_name, record.result)
        self.on_pass(record.test_name, record.begin_time)

    def on_pass(self, test_name, begin_time):
        """A function that is executed upon a test case passing.

        Implementation is optional.

        Args:
            test_name: Name of the test that triggered this function.
            begin_time: Logline format timestamp taken when the test started.
        """

    def _on_skip(self, record):
        """Proxy function to guarantee the base implementation of on_skip is
        called.

        Args:
            record: The records.TestResultRecord object for the skipped test
                    case.
        """
        self.log.info(RESULT_LINE_TEMPLATE, record.test_name, record.result)
        self.log.info("Reason to skip: %s", record.details)
        self.on_skip(record.test_name, record.begin_time)

    def on_skip(self, test_name, begin_time):
        """A function that is executed upon a test case being skipped.

        Implementation is optional.

        Args:
            test_name: Name of the test that triggered this function.
            begin_time: Logline format timestamp taken when the test started.
        """

    def _on_blocked(self, record):
        """Proxy function to guarantee the base implementation of on_blocked
        is called.

        Args:
            record: The records.TestResultRecord object for the blocked test
                    case.
        """
        self.log.info(RESULT_LINE_TEMPLATE, record.test_name, record.result)
        self.log.info("Reason to block: %s", record.details)
        self.on_blocked(record.test_name, record.begin_time)

    def on_blocked(self, test_name, begin_time):
        """A function that is executed upon a test begin skipped.

        Args:
            test_name: Name of the test that triggered this function.
            begin_time: Logline format timestamp taken when the test started.
        """

    def _on_exception(self, record):
        """Proxy function to guarantee the base implementation of on_exception
        is called.

        Args:
            record: The records.TestResultRecord object for the failed test
                    case.
        """
        self.log.exception(record.details)
        self.on_exception(record.test_name, record.begin_time)

    def on_exception(self, test_name, begin_time):
        """A function that is executed upon an unhandled exception from a test
        case.

        Implementation is optional.

        Args:
            test_name: Name of the test that triggered this function.
            begin_time: Logline format timestamp taken when the test started.
        """

    def _exec_procedure_func(self, func, tr_record):
        """Executes a procedure function like on_pass, on_fail etc.

        This function will alternate the 'Result' of the test's record if
        exceptions happened when executing the procedure function.

        This will let signals.TestAbortAll through so abort_all works in all
        procedure functions.

        Args:
            func: The procedure function to be executed.
            tr_record: The TestResultRecord object associated with the test
                       case executed.
        """
        try:
            func(tr_record)
        except signals.TestAbortAll:
            raise
        except Exception as e:
            self.log.exception("Exception happened when executing %s for %s.",
                               func.__name__, self.current_test_name)
            tr_record.add_error(func.__name__, e)

    def exec_one_testcase(self, test_name, test_func, args, **kwargs):
        """Executes one test case and update test results.

        Executes one test case, create a records.TestResultRecord object with
        the execution information, and add the record to the test class's test
        results.

        Args:
            test_name: Name of the test.
            test_func: The test function.
            args: A tuple of params.
            kwargs: Extra kwargs.
        """
        is_generate_trigger = False
        tr_record = records.TestResultRecord(test_name, self.TAG)
        tr_record.test_begin()
        self.begin_time = int(tr_record.begin_time)
        self.log_begin_time = tr_record.log_begin_time
        self.test_name = tr_record.test_name
        self.log.info("%s %s", TEST_CASE_TOKEN, test_name)
        verdict = None
        try:
            try:
                if hasattr(self, 'android_devices'):
                    for ad in self.android_devices:
                        if not ad.is_adb_logcat_on:
                            ad.start_adb_logcat(cont_logcat_file=True)
                ret = self._setup_test(self.test_name)
                asserts.assert_true(ret is not False,
                                    "Setup for %s failed." % test_name)
                if args or kwargs:
                    verdict = test_func(*args, **kwargs)
                else:
                    verdict = test_func()
            finally:
                try:
                    self._teardown_test(self.test_name)
                except signals.TestAbortAll:
                    raise
                except Exception as e:
                    self.log.error(traceback.format_exc())
                    tr_record.add_error("teardown_test", e)
                    self._exec_procedure_func(self._on_exception, tr_record)
        except (signals.TestFailure, AssertionError) as e:
            if self.user_params.get(
                    keys.Config.key_test_failure_tracebacks.value, False):
                self.log.exception(e)
            else:
                self.log.error(e)
            tr_record.test_fail(e)
            self._exec_procedure_func(self._on_fail, tr_record)
        except signals.TestSkip as e:
            # Test skipped.
            tr_record.test_skip(e)
            self._exec_procedure_func(self._on_skip, tr_record)
        except (signals.TestAbortClass, signals.TestAbortAll) as e:
            # Abort signals, pass along.
            tr_record.test_fail(e)
            self._exec_procedure_func(self._on_fail, tr_record)
            raise e
        except signals.TestPass as e:
            # Explicit test pass.
            tr_record.test_pass(e)
            self._exec_procedure_func(self._on_pass, tr_record)
        except signals.TestSilent as e:
            # This is a trigger test for generated tests, suppress reporting.
            is_generate_trigger = True
            self.results.requested.remove(test_name)
        except signals.TestBlocked as e:
            tr_record.test_blocked(e)
            self._exec_procedure_func(self._on_blocked, tr_record)
        except Exception as e:
            self.log.error(traceback.format_exc())
            # Exception happened during test.
            tr_record.test_unknown(e)
            self._exec_procedure_func(self._on_exception, tr_record)
            self._exec_procedure_func(self._on_fail, tr_record)
        else:
            if verdict or (verdict is None):
                # Test passed.
                tr_record.test_pass()
                self._exec_procedure_func(self._on_pass, tr_record)
                return
            tr_record.test_fail()
            self._exec_procedure_func(self._on_fail, tr_record)
        finally:
            if not is_generate_trigger:
                self.results.add_record(tr_record)

    def run_generated_testcases(self,
                                test_func,
                                settings,
                                args=None,
                                kwargs=None,
                                tag="",
                                name_func=None,
                                format_args=False):
        """Runs generated test cases.

        Generated test cases are not written down as functions, but as a list
        of parameter sets. This way we reduce code repetition and improve
        test case scalability.

        Args:
            test_func: The common logic shared by all these generated test
                       cases. This function should take at least one argument,
                       which is a parameter set.
            settings: A list of strings representing parameter sets. These are
                      usually json strings that get loaded in the test_func.
            args: Iterable of additional position args to be passed to
                  test_func.
            kwargs: Dict of additional keyword args to be passed to test_func
            tag: Name of this group of generated test cases. Ignored if
                 name_func is provided and operates properly.
            name_func: A function that takes a test setting and generates a
                       proper test name. The test name should be shorter than
                       utils.MAX_FILENAME_LEN. Names over the limit will be
                       truncated.
            format_args: If True, args will be appended as the first argument
                         in the args list passed to test_func.

        Returns:
            A list of settings that did not pass.
        """
        args = args or ()
        kwargs = kwargs or {}
        failed_settings = []

        for setting in settings:
            test_name = "{} {}".format(tag, setting)

            if name_func:
                try:
                    test_name = name_func(setting, *args, **kwargs)
                except:
                    self.log.exception(("Failed to get test name from "
                                        "test_func. Fall back to default %s"),
                                       test_name)

            self.results.requested.append(test_name)

            if len(test_name) > utils.MAX_FILENAME_LEN:
                test_name = test_name[:utils.MAX_FILENAME_LEN]

            previous_success_cnt = len(self.results.passed)

            if format_args:
                self.exec_one_testcase(test_name, test_func,
                                       args + (setting,), **kwargs)
            else:
                self.exec_one_testcase(test_name, test_func,
                                       (setting,) + args, **kwargs)

            if len(self.results.passed) - previous_success_cnt != 1:
                failed_settings.append(setting)

        return failed_settings

    def _exec_func(self, func, *args):
        """Executes a function with exception safeguard.

        This will let signals.TestAbortAll through so abort_all works in all
        procedure functions.

        Args:
            func: Function to be executed.
            args: Arguments to be passed to the function.

        Returns:
            Whatever the function returns, or False if unhandled exception
            occured.
        """
        try:
            return func(*args)
        except signals.TestAbortAll:
            raise
        except:
            self.log.exception("Exception happened when executing %s in %s.",
                               func.__name__, self.TAG)
            return False

    def _get_all_test_names(self):
        """Finds all the function names that match the test case naming
        convention in this class.

        Returns:
            A list of strings, each is a test case name.
        """
        test_names = []
        for name in dir(self):
            if name.startswith("test_"):
                test_names.append(name)
        return test_names

    def _get_test_funcs(self, test_names):
        """Obtain the actual functions of test cases based on test names.

        Args:
            test_names: A list of strings, each string is a test case name.

        Returns:
            A list of tuples of (string, function). String is the test case
            name, function is the actual test case function.

        Raises:
            Error is raised if the test name does not follow
            naming convention "test_*". This can only be caused by user input
            here.
        """
        test_funcs = []
        for test_name in test_names:
            test_funcs.append(self._get_test_func(test_name))

        return test_funcs

    def _get_test_func(self, test_name):
        """Obtain the actual function of test cases based on the test name.

        Args:
            test_name: String, The name of the test.

        Returns:
            A tuples of (string, function). String is the test case
            name, function is the actual test case function.

        Raises:
            Error is raised if the test name does not follow
            naming convention "test_*". This can only be caused by user input
            here.
        """
        if not test_name.startswith("test_"):
            raise Error(("Test case name %s does not follow naming "
                         "convention test_*, abort.") % test_name)
        try:
            return test_name, getattr(self, test_name)
        except:

            def test_skip_func(*args, **kwargs):
                raise signals.TestSkip("Test %s does not exist" % test_name)

            self.log.info("Test case %s not found in %s.", test_name, self.TAG)
            return test_name, test_skip_func

    def _block_all_test_cases(self, tests):
        """
        Block all passed in test cases.
        Args:
            tests: The tests to block.
        """
        for test_name, test_func in tests:
            signal = signals.TestBlocked("Failed class setup")
            record = records.TestResultRecord(test_name, self.TAG)
            record.test_begin()
            if hasattr(test_func, 'gather'):
                signal.extras = test_func.gather()
            record.test_blocked(signal)
            self.results.add_record(record)
            self._on_blocked(record)

    def run(self, test_names=None, test_case_iterations=1):
        """Runs test cases within a test class by the order they appear in the
        execution list.

        One of these test cases lists will be executed, shown here in priority
        order:
        1. The test_names list, which is passed from cmd line. Invalid names
           are guarded by cmd line arg parsing.
        2. The self.tests list defined in test class. Invalid names are
           ignored.
        3. All function that matches test case naming convention in the test
           class.

        Args:
            test_names: A list of string that are test case names requested in
                cmd line.

        Returns:
            The test results object of this class.
        """
        self.log.info("==========> %s <==========", self.TAG)
        # Devise the actual test cases to run in the test class.
        if not test_names:
            if self.tests:
                # Specified by run list in class.
                test_names = list(self.tests)
            else:
                # No test case specified by user, execute all in the test class
                test_names = self._get_all_test_names()
        self.results.requested = test_names
        tests = self._get_test_funcs(test_names)
        # A TestResultRecord used for when setup_class fails.
        # Setup for the class.
        try:
            if self._setup_class() is False:
                self.log.error("Failed to setup %s.", self.TAG)
                self._block_all_test_cases(tests)
                return self.results
        except Exception as e:
            self.log.exception("Failed to setup %s.", self.TAG)
            self._exec_func(self.teardown_class)
            self._block_all_test_cases(tests)
            return self.results
        # Run tests in order.
        try:
            for test_name, test_func in tests:
                for _ in range(test_case_iterations):
                    self.exec_one_testcase(test_name, test_func, self.cli_args)
            return self.results
        except signals.TestAbortClass:
            return self.results
        except signals.TestAbortAll as e:
            # Piggy-back test results on this exception object so we don't lose
            # results from this test class.
            setattr(e, "results", self.results)
            raise e
        finally:
            self._exec_func(self.teardown_class)
            self.log.info("Summary for test class %s: %s", self.TAG,
                          self.results.summary_str())

    def clean_up(self):
        """A function that is executed upon completion of all tests cases
        selected in the test class.

        This function should clean up objects initialized in the constructor by
        user.
        """

    def _ad_take_bugreport(self, ad, test_name, begin_time):
        for i in range(3):
            try:
                ad.take_bug_report(test_name, begin_time)
                return True
            except Exception as e:
                ad.log.error("bugreport attempt %s error: %s", i + 1, e)

    def _ad_take_extra_logs(self, ad, test_name, begin_time):
        result = True
        if getattr(ad, "qxdm_log", False):
            # Gather qxdm log modified 3 minutes earlier than test start time
            if begin_time:
                qxdm_begin_time = begin_time - 1000 * 60 * 3
            else:
                qxdm_begin_time = None
            try:
                ad.get_qxdm_logs(test_name, qxdm_begin_time)
            except Exception as e:
                ad.log.error("Failed to get QXDM log for %s with error %s",
                             test_name, e)
                result = False

        try:
            ad.check_crash_report(test_name, begin_time, log_crash_report=True)
        except Exception as e:
            ad.log.error("Failed to check crash report for %s with error %s",
                         test_name, e)
            result = False
        return result

    def _skip_bug_report(self):
        """A function to check whether we should skip creating a bug report."""
        if "no_bug_report_on_fail" in self.user_params:
            return True

        # Once we hit a certain log path size, it's not going to get smaller.
        # We cache the result so we don't have to keep doing directory walks.
        if self.size_limit_reached:
            return True
        try:
            max_log_size = int(
                self.user_params.get("soft_output_size_limit") or "invalid")
            log_path = getattr(logging, "log_path", None)
            if log_path:
                curr_log_size = utils.get_directory_size(log_path)
                if curr_log_size > max_log_size:
                    self.log.info(
                        "Skipping bug report, as we've reached the size limit."
                    )
                    self.size_limit_reached = True
                    return True
        except ValueError:
            pass
        return False

    def _take_bug_report(self, test_name, begin_time):
        if self._skip_bug_report():
            return

        executor = ThreadPoolExecutor(max_workers=10)
        for ad in getattr(self, 'android_devices', []):
            executor.submit(self._ad_take_bugreport, ad, test_name, begin_time)
            executor.submit(self._ad_take_extra_logs, ad, test_name,
                            begin_time)
        executor.shutdown()

    def _reboot_device(self, ad):
        ad.log.info("Rebooting device.")
        ad = ad.reboot()

    def _cleanup_logger_sessions(self):
        for (mylogger, session) in self.logger_sessions:
            self.log.info("Resetting a diagnostic session %s, %s", mylogger,
                          session)
            mylogger.reset()
        self.logger_sessions = []

    def _pull_diag_logs(self, test_name, begin_time):
        for (mylogger, session) in self.logger_sessions:
            self.log.info("Pulling diagnostic session %s", mylogger)
            mylogger.stop(session)
            diag_path = os.path.join(
                self.log_path, logger.epoch_to_log_line_timestamp(begin_time))
            utils.create_dir(diag_path)
            mylogger.pull(session, diag_path)
