#!/usr/bin/env python3.4
#
#   Copyright 2016 - The Android Open Source Project
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

import importlib
import logging
import os

ACTS_CONTROLLER_CONFIG_NAME = "DiagLogger"
ACTS_CONTROLLER_REFERENCE_NAME = "diag_logger"


class DiagLoggerError(Exception):
    """This is the base exception class for errors generated by
    DiagLogger modules.
    """
    pass


def create(configs):
    """Initializes the Diagnotic Logger instances based on the
    provided JSON configuration(s). The expected keys are:

    Package: A package name containing the diagnostic logger
        module. It should be in python path of the environment.
    Type: A first-level type for the Logger, which should correspond
        the name of the module containing the Logger implementation.
    SubType: The exact implementation of the sniffer, which should
        correspond to the name of the class to be used.
    HostLogPath: This is the default directory used to dump any logs
        that are captured or any other files that are stored as part
        of the logging process. It's use is implementation specific,
        but it should be provided by all loggers for completeness.
    Configs: A dictionary specifying baseline configurations of the
        particular Logger. These configurations may be overridden at
        the start of a session.
    """
    objs = []
    for c in configs:
        diag_package_name = c["Package"]  # package containing module
        diag_logger_type = c["Type"]  # module name
        diag_logger_name = c["SubType"]  # class name
        host_log_path = c["HostLogPath"]
        base_configs = c["Configs"]
        module_name = "{}.{}".format(diag_package_name, diag_logger_type)
        module = importlib.import_module(module_name)
        logger_class = getattr(module, diag_logger_name)

        objs.append(logger_class(host_log_path,
                                 None,
                                 config_container=base_configs))
    return objs


def destroy(objs):
    """Stops all ongoing logger sessions, deletes any temporary files, and
    prepares logger objects for destruction.
    """
    for diag_logger in objs:
        try:
            diag_logger.reset()
        except DiagLoggerError:
            # TODO: log if things go badly here
            pass


class DiagLoggerBase():
    """Base Class for Proprietary Diagnostic Log Collection

    The DiagLoggerBase is a simple interface for running on-device logging via
    a standard workflow that can be integrated without the caller actually
    needing to know the details of what logs are captured or how.
    The workflow is as follows:

    1) Create a DiagLoggerBase Object
    2) Call start() to begin an active logging session.
    3) Call stop() to end an active logging session.
    4) Call pull() to ensure all collected logs are stored at
       'host_log_path'
    5) Call reset() to stop all logging and clear any unretrieved logs.
    """

    def __init__(self, host_log_path, logger=None, config_container=None):
        """Create a Diagnostic Logging Proxy Object

        Args:
            host_log_path: File path where retrieved logs should be stored
            config_container: A transparent container used to pass config info
        """
        self.host_log_path = os.path.realpath(os.path.expanduser(
            host_log_path))
        self.config_container = config_container
        if not os.path.isdir(self.host_log_path):
            os.mkdir(self.host_log_path)
        self.logger = logger
        if not self.logger:
            self.logger = logging.getLogger(self.__class__.__name__)

    def start(self, config_container=None):
        """Start collecting Diagnostic Logs

        Args:
            config_container: A transparent container used to pass config info

        Returns:
            A logging session ID that can be later used to stop the session
            For Diag interfaces supporting only one session this is unneeded
        """
        raise NotImplementedError("Base class should not be invoked directly!")

    def stop(self, session_id=None):
        """Stop collecting Diagnostic Logs

        Args:
            session_id: an optional session id provided for multi session
                        logging support

        Returns:
        """
        raise NotImplementedError("Base class should not be invoked directly!")

    def pull(self, session_id=None, out_path=None):
        """Save all cached diagnostic logs collected to the host

        Args:
            session_id: an optional session id provided for multi session
                        logging support

            out_path: an optional override to host_log_path for a specific set
                      of logs

        Returns:
            An integer representing a port number on the host available for adb
            forward.
        """
        raise NotImplementedError("Base class should not be invoked directly!")

    def reset(self):
        """Stop any ongoing logging sessions and clear any cached logs that have
        not been retrieved with pull(). This must delete all session records and
        return the logging object to a state equal to when constructed.
        """
        raise NotImplementedError("Base class should not be invoked directly!")

    def get_log_path(self):
        """Return the log path for this object"""
        return self.host_log_path
