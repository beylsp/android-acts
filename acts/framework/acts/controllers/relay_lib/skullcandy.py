#!/usr/bin/env python
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
import enum
import time

from acts.controllers.relay_lib.devices.bluetooth_relay_device import BluetoothRelayDevice

PAIRING_MODE_WAIT_TIME = 5
POWER_TOGGLE_WAIT_TIME = 1


class Buttons(enum.Enum):
    POWER = 'Power'


class Skullcandy(BluetoothRelayDevice):
    """Skullcandy Bluetooth Speaker model

    Wraps the button presses, as well as the special features like pairing.
    """

    def __init__(self, config, relay_rig):
        BluetoothRelayDevice.__init__(self, config, relay_rig)
        self._ensure_config_contains_relays(button.value for button in Buttons)

    def _hold_button(self, button, seconds):
        self.hold_down(button.value)
        time.sleep(seconds)
        self.release(button.value)

    def power_off(self):
        self._hold_button(Buttons.POWER, POWER_TOGGLE_WAIT_TIME)

    def turn_power_on_and_enter_pairing_mode(self):
        self._hold_button(Buttons.POWER, PAIRING_MODE_WAIT_TIME)

    def setup(self):
        """Sets all relays to their default state (off)."""
        BluetoothRelayDevice.setup(self)

    def clean_up(self):
        """Sets all relays to their default state (off)."""
        BluetoothRelayDevice.clean_up(self)
