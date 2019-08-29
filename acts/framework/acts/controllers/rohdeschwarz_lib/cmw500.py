#!/usr/bin/env python3
#
#   Copyright 2019 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#           http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import time

from acts.controllers.gnssinst_lib import abstract_inst


class Cmw500(abstract_inst.SocketInstrument):

    def __init__(self, ip_addr, port):
        """Init method to setup variables for controllers.

        Args:
              ip_addr: Controller's ip address.
              port: Port
        """
        super(Cmw500, self).__init__(ip_addr, port)
        self._connect_socket()
        self._send('*CLS')
        self._send('*ESE 0;*SRE 0')
        self._send('*CLS')
        self._send('*ESE 1;*SRE 4')
        self._send('SYST:DISP:UPD ON')

    def switch_lte_signalling(self, state):
        """Turns LTE signalling ON/OFF.

        Args:
              state: ON/OFF.

        Returns:
              status: Status of LTE state change.
        """
        cmd = 'SOURce:LTE:SIGN:CELL:STATe {}'.format(state)
        self._send(cmd)
        time.sleep(5)  # Wait until LTE turns on.
        state = self._send_and_recv('SOURce:LTE:SIGN:CELL:STATe:ALL?')
        return state

    def enable_packet_switching(self):
        """Enable packet switching in call box

        Returns:
            state: Status of pswitched state.
        """
        self._send('CALL:LTE:SIGN:PSWitched:ACTion CONNect')
        state = self._send_and_recv('FETCh:LTE:SIGN:PSWitched:STATe?')
        return state

    @property
    def duplex_mode(self):
        """Gets current duplex of cell."""
        return self._send_and_recv('CONFigure:LTE:SIGN:DMODe?')

    @duplex_mode.setter
    def duplex_mode(self, mode):
        """Sets the Duplex mode of cell.

        Args:
            mode: String indicating FDD or TDD.
        """
        cmd = 'CONFigure:LTE:SIGN:DMODe {}'.format(mode)
        self._send(cmd)

    @property
    def band(self):
        """Gets the current band of cell."""
        return self._send_and_recv('CONFigure:LTE:SIGN:PCC:BAND?')

    @band.setter
    def band(self, band):
        """Sets the Band of cell.

        Args:
            band: band of cell.
        """
        cmd = 'CONFigure:LTE:SIGN:PCC:BAND {}'.format(band)
        self._send(cmd)

    @property
    def dl_channel(self):
        """Gets the downlink channel of cell."""
        return self._send_and_recv('CONFigure:LTE:SIGN:RFSettings:PCC:CHANnel'
                                   ':DL?')

    @dl_channel.setter
    def dl_channel(self, channel):
        """Sets the downlink channel number of cell.

        Args:
            channel: downlink channel number of cell.
        """
        cmd = 'CONFigure:LTE:SIGN:RFSettings:PCC:CHANnel:DL {}'.format(channel)
        self._send(cmd)

    @property
    def ul_channel(self):
        """Gets the uplink channel of cell."""
        return self._send_and_recv('CONFigure:LTE:SIGN:RFSettings:PCC:CHANnel'
                                   ':UL?')

    @ul_channel.setter
    def ul_channel(self, channel):
        """Sets the up link channel number of cell.

        Args:
            channel: up link channel number of cell.
        """
        cmd = 'CONFigure:LTE:SIGN:RFSettings:PCC:CHANnel:UL {}'.format(channel)
        self._send(cmd)

    @property
    def bandwidth(self):
        """Get the channel bandwidth of the cell."""
        return self._send_and_recv('CONFigure:LTE:SIGN:CELL:BANDwidth:PCC:DL?')

    @bandwidth.setter
    def bandwidth(self, bandwidth):
        """Sets the channel bandwidth of the cell.

        Args:
            bandwidth: channel bandwidth of cell.
        """
        cmd = 'CONFigure:LTE:SIGN:CELL:BANDwidth:PCC:DL {}'.format(bandwidth)
        self._send(cmd)

    @property
    def ul_frequency(self):
        """Get the uplink frequency of the cell."""
        return self._send_and_recv('CONFigure:LTE:SIGN:RFSettings:PCC:CHANnel'
                                   ':UL? MHZ')

    @ul_frequency.setter
    def ul_frequency(self, freq):
        """Get the uplink frequency of the cell.

        Args:
            freq: uplink frequency of the cell.
        """
        cmd = 'CONFigure:LTE:SIGN:RFSettings:PCC:CHANnel:UL {} MHZ'.format(
            freq)
        self._send(cmd)

    @property
    def dl_frequency(self):
        """Get the downlink frequency of the cell"""
        return self._send_and_recv('CONFigure:LTE:SIGN:RFSettings:PCC:CHANnel'
                                   ':DL? MHZ')

    @dl_frequency.setter
    def dl_frequency(self, freq):
        """Get the downlink frequency of the cell.

        Args:
            freq: downlink frequency of the cell.
        """
        cmd = 'CONFigure:LTE:SIGN:RFSettings:PCC:CHANnel:DL {} MHZ'.format(
            freq)
        self._send(cmd)

    def transmode(self, tm_mode):
        """Sets the TM of cell.

        Args:
            tm_mode: TM of cell.
        """
        cmd = 'CONFigure:LTE:SIGN:CONNection:PCC:TRANsmission {}'.format(
            tm_mode)
        self._send(cmd)

    def set_mimo(self):
        """Sets the scenario for the test."""
        # TODO:(ganeshganesh) Create a common function to set mimo modes.
        self._send('ROUTe:LTE:SIGN:SCENario:SCELl:FLEXible SUW1,RF1C,'
                   'RX1,RF1C,TX1')

    def wait_for_connected_state(self, timeout=120):
        """Attach the controller with device.

        Args:
            timeout: timeout for phone to get attached.
        """
        end_time = time.time() + timeout
        while time.time() <= end_time:
            state = self._send_and_recv('FETCh:LTE:SIGN:PSWitched:STATe?')

            if state == 'ATT':
                self._logger.debug('Call box attached with device')
                break
        else:
            raise CmwError('Device could not be attached')

        conn_state = self._send_and_recv('SENSe:LTE:SIGN:RRCState?')

        if conn_state == 'CONN':
            self._logger.debug('Call box connected with device')
        else:
            raise CmwError('Call box could not be connected with device')

    def set_downlink_power_level(self, pwlevel):
        """Modifies RSPRE level.

        Args:
            pwlevel: power level in dBm.
        """
        cmd = 'CONFigure:LTE:SIGN:DL:PCC:RSEPre:LEVel {}'.format(pwlevel)
        self._send(cmd)

    def reset(self):
        """System level reset"""
        self._send('*RST; *OPC')

    def _send_and_recv(self, cmd):
        """Send and recv the status of the command.

        Args:
            cmd: Command to send.

        Returns:
            status: returns the status of the command sent.
        """

        self._send(cmd)
        status = self._recv()
        return status

    def disconnect(self):
        """Detach controller from device and switch to local mode."""
        self.switch_lte_signalling('OFF')
        self._send('&GTL')
        self._close_socket()


class CmwError(Exception):
    """Class to raise exceptions related to cmw."""
