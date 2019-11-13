#   Copyright 2019 - The Android Open Source Project
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

from acts.controllers.ap_lib import hostapd_config
from acts.controllers.ap_lib import hostapd_constants


def _merge_dicts(*dict_args):
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def tplink_archerc5(iface_wlan_2g=None,
                    iface_wlan_5g=None,
                    channel=None,
                    security=None,
                    ssid=None):
    """A simulated implementation of an TPLink ArcherC5 AP.
    Args:
        iface_wlan_2g: The 2.4Ghz interface of the test AP.
        iface_wlan_5g: The 5GHz interface of the test AP.
        channel: What channel to use.
        security: A security profile (None or WPA2).
        ssid: The network name.
    Returns:
        A hostapd config.
    Differences from real ArcherC5:
        2.4GHz:
            Rates:
                ArcherC5:
                    Supported: 1, 2, 5.5, 11, 18, 24, 36, 54
                    Extended: 6, 9, 12, 48
                Simulated:
                    Supported: 1, 2, 5.5, 11, 6, 9, 12, 18
                    Extended: 24, 36, 48, 54
            HT Capab:
                Info:
                    ArcherC5: Green Field supported
                    Simulated: Green Field not supported by driver
        5GHz:
            VHT Capab:
                ArcherC5:
                    SU Beamformer Supported,
                    SU Beamformee Supported,
                    Beamformee STS Capability: 3,
                    Number of Sounding Dimensions: 3,
                    VHT Link Adaptation: Both
                Simulated:
                    Above are not supported by driver
            VHT Operation Info:
                ArcherC5: Basic MCS Map (0x0000)
                Simulated: Basic MCS Map (0xfffc)
            VHT Tx Power Envelope:
                ArcherC5: Local Max Tx Pwr Constraint: 1.0 dBm
                Simulated: Local Max Tx Pwr Constraint: 23.0 dBm
        Both:
            HT Capab:
                A-MPDU
                    ArcherC5: MPDU Density 4
                    Simulated: MPDU Density 8
            HT Info:
                ArcherC5: RIFS Permitted
                Simulated: RIFS Prohibited
    """
    if not iface_wlan_2g or not iface_wlan_5g:
        raise ValueError('Wlan interface for 2G and/or 5G is missing.')
    if (iface_wlan_2g not in hostapd_constants.INTERFACE_2G_LIST
            or iface_wlan_5g not in hostapd_constants.INTERFACE_5G_LIST):
        raise ValueError('Invalid interface name was passed.')
    if security:
        if security.security_mode is hostapd_constants.WPA2:
            if not security.wpa2_cipher == 'CCMP':
                raise ValueError(
                    'The mock TPLink ArcherC5 only supports a WPA2 '
                    'unicast and multicast cipher of CCMP. '
                    'Invalid cipher mode (%s)' % security.security.wpa2_cipher)
        else:
            raise ValueError(
                'The TPLink ArcherC5 only supports WPA2 or open. Invalid '
                'security mode (%s)' % security.security_mode)

    # Common Parameters
    rates = {'supported_rates': '10 20 55 110 60 90 120 180 240 360 480 540'}
    n_capabilities = [
        hostapd_constants.N_CAPABILITY_SGI20,
        hostapd_constants.N_CAPABILITY_TX_STBC,
        hostapd_constants.N_CAPABILITY_RX_STBC1,
        hostapd_constants.N_CAPABILITY_MAX_AMSDU_7935
    ]
    # WPS IE
    # Broadcom IE
    vendor_elements = {
        'vendor_elements':
        'dd310050f204104a000110104400010210470010d96c7efc2f8938f1efbd6e5148bfa8'
        '12103c0001031049000600372a000120'
        'dd090010180200001c0000'
    }
    qbss = {'bss_load_update_period': 50, 'chan_util_avg_period': 600}

    # 2.4GHz
    if channel <= 11:
        interface = iface_wlan_2g
        rates['basic_rates'] = '10 20 55 110'
        short_preamble = True
        mode = hostapd_constants.MODE_11N_MIXED
        n_capabilities.append(hostapd_constants.N_CAPABILITY_DSSS_CCK_40)
        ac_capabilities = None
        vht_channel_width = None
        vht_center_channel = None

    # 5GHz
    else:
        interface = iface_wlan_5g
        rates['basic_rates'] = '60 120 240'
        short_preamble = False
        mode = hostapd_constants.MODE_11AC_MIXED
        n_capabilities.append(hostapd_constants.N_CAPABILITY_LDPC)
        ac_capabilities = [
            hostapd_constants.AC_CAPABILITY_MAX_MPDU_11454,
            hostapd_constants.AC_CAPABILITY_SHORT_GI_80,
            hostapd_constants.AC_CAPABILITY_RXLDPC,
            hostapd_constants.AC_CAPABILITY_TX_STBC_2BY1,
            hostapd_constants.AC_CAPABILITY_RX_STBC_1,
            hostapd_constants.AC_CAPABILITY_MAX_A_MPDU_LEN_EXP7,
        ]
        vht_channel_width = 40
        vht_center_channel = 36

    additional_params = _merge_dicts(
        rates, vendor_elements, qbss,
        hostapd_constants.ENABLE_RRM_BEACON_REPORT,
        hostapd_constants.ENABLE_RRM_NEIGHBOR_REPORT,
        hostapd_constants.UAPSD_ENABLED)

    config = hostapd_config.HostapdConfig(
        ssid=ssid,
        channel=channel,
        hidden=False,
        security=security,
        interface=interface,
        mode=mode,
        force_wmm=True,
        beacon_interval=100,
        dtim_period=1,
        short_preamble=short_preamble,
        n_capabilities=n_capabilities,
        ac_capabilities=ac_capabilities,
        vht_channel_width=vht_channel_width,
        vht_center_channel=vht_center_channel,
        additional_parameters=additional_params)
    return config


def tplink_archerc7(iface_wlan_2g=None,
                    iface_wlan_5g=None,
                    channel=None,
                    security=None,
                    ssid=None):
    # TODO(b/143104825): Permit RIFS once it is supported
    """A simulated implementation of an TPLink ArcherC7 AP.
    Args:
        iface_wlan_2g: The 2.4Ghz interface of the test AP.
        iface_wlan_5g: The 5GHz interface of the test AP.
        channel: What channel to use.
        security: A security profile (None or WPA2).
        ssid: The network name.
    Returns:
        A hostapd config.
    Differences from real ArcherC7:
        5GHz:
            Country Code:
                Simulated: Has two country code IEs, one that matches
                the actual, and another explicit IE that was required for
                hostapd's 802.11d to work.
        Both:
            HT Info:
                ArcherC7: RIFS Permitted
                Simulated: RIFS Prohibited
            RSN Capabilities:
                ArcherC7: 0x000c (RSN PTKSA Replay Counter Capab: 16)
                Simulated: 0x0000 (RSN PTKSA Replay Counter Capab: 1)
    """
    if not iface_wlan_2g or not iface_wlan_5g:
        raise ValueError('Wlan interface for 2G and/or 5G is missing.')
    if (iface_wlan_2g not in hostapd_constants.INTERFACE_2G_LIST
            or iface_wlan_5g not in hostapd_constants.INTERFACE_5G_LIST):
        raise ValueError('Invalid interface name was passed.')
    if security:
        if security.security_mode is hostapd_constants.WPA2:
            if not security.wpa2_cipher == 'CCMP':
                raise ValueError(
                    'The mock TPLink ArcherC7 only supports a WPA2 '
                    'unicast and multicast cipher of CCMP. '
                    'Invalid cipher mode (%s)' % security.security.wpa2_cipher)
        else:
            raise ValueError(
                'The TPLink ArcherC7 only supports WPA2 or open. Invalid '
                'security mode (%s)' % security.security_mode)

    # Common Parameters
    rates = {'supported_rates': '10 20 55 110 60 90 120 180 240 360 480 540'}
    n_capabilities = [
        hostapd_constants.N_CAPABILITY_LDPC,
        hostapd_constants.N_CAPABILITY_SGI20,
        hostapd_constants.N_CAPABILITY_TX_STBC,
        hostapd_constants.N_CAPABILITY_RX_STBC1
    ]
    # Atheros IE
    # WPS IE
    vendor_elements = {
        'vendor_elements':
        'dd0900037f01010000ff7f'
        'dd180050f204104a00011010440001021049000600372a000120'
    }

    # 2.4GHz
    if channel <= 11:
        interface = iface_wlan_2g
        rates['basic_rates'] = '10 20 55 110'
        short_preamble = True
        mode = hostapd_constants.MODE_11N_MIXED
        spectrum_mgmt = False
        pwr_constraint = {}
        ac_capabilities = None
        vht_channel_width = None
        vht_center_channel = None

    # 5GHz
    else:
        interface = iface_wlan_5g
        rates['basic_rates'] = '60 120 240'
        short_preamble = False
        mode = hostapd_constants.MODE_11AC_MIXED
        spectrum_mgmt = True
        # Country Information IE (w/ individual channel info)
        vendor_elements['vendor_elements'] += (
            '074255532024011e28011e2c011e30'
            '011e3401173801173c01174001176401176801176c0117700117740117840117'
            '8801178c011795011e99011e9d011ea1011ea5011e')
        pwr_constraint = {'local_pwr_constraint': 3}
        n_capabilities += [
            hostapd_constants.N_CAPABILITY_HT40_PLUS,
            hostapd_constants.N_CAPABILITY_SGI40,
            hostapd_constants.N_CAPABILITY_MAX_AMSDU_7935
        ]
        ac_capabilities = [
            hostapd_constants.AC_CAPABILITY_MAX_MPDU_11454,
            hostapd_constants.AC_CAPABILITY_RXLDPC,
            hostapd_constants.AC_CAPABILITY_SHORT_GI_80,
            hostapd_constants.AC_CAPABILITY_TX_STBC_2BY1,
            hostapd_constants.AC_CAPABILITY_RX_STBC_1,
            hostapd_constants.AC_CAPABILITY_MAX_A_MPDU_LEN_EXP7,
            hostapd_constants.AC_CAPABILITY_RX_ANTENNA_PATTERN,
            hostapd_constants.AC_CAPABILITY_TX_ANTENNA_PATTERN
        ]
        vht_channel_width = 80
        vht_center_channel = 42

    additional_params = _merge_dicts(rates, vendor_elements,
                                     hostapd_constants.UAPSD_ENABLED,
                                     pwr_constraint)

    config = hostapd_config.HostapdConfig(
        ssid=ssid,
        channel=channel,
        hidden=False,
        security=security,
        interface=interface,
        mode=mode,
        force_wmm=True,
        beacon_interval=100,
        dtim_period=1,
        short_preamble=short_preamble,
        n_capabilities=n_capabilities,
        ac_capabilities=ac_capabilities,
        vht_channel_width=vht_channel_width,
        vht_center_channel=vht_center_channel,
        spectrum_mgmt_required=spectrum_mgmt,
        additional_parameters=additional_params)
    return config


def tplink_c1200(iface_wlan_2g=None,
                 iface_wlan_5g=None,
                 channel=None,
                 security=None,
                 ssid=None):
    # TODO(b/143104825): Permit RIFS once it is supported
    """A simulated implementation of an TPLink C1200 AP.
    Args:
        iface_wlan_2g: The 2.4Ghz interface of the test AP.
        iface_wlan_5g: The 5GHz interface of the test AP.
        channel: What channel to use.
        security: A security profile (None or WPA2).
        ssid: The network name.
    Returns:
        A hostapd config.
    Differences from real C1200:
        2.4GHz:
            Rates:
                C1200:
                    Supported: 1, 2, 5.5, 11, 18, 24, 36, 54
                    Extended: 6, 9, 12, 48
                Simulated:
                    Supported: 1, 2, 5.5, 11, 6, 9, 12, 18
                    Extended: 24, 36, 48, 54
            HT Capab:
                Info:
                    C1200: Green Field supported
                    Simulated: Green Field not supported by driver
        5GHz:
            VHT Operation Info:
                C1200: Basic MCS Map (0x0000)
                Simulated: Basic MCS Map (0xfffc)
            VHT Tx Power Envelope:
                C1200: Local Max Tx Pwr Constraint: 7.0 dBm
                Simulated: Local Max Tx Pwr Constraint: 23.0 dBm
        Both:
            HT Info:
                C1200: RIFS Permitted
                Simulated: RIFS Prohibited
    """
    if not iface_wlan_2g or not iface_wlan_5g:
        raise ValueError('Wlan interface for 2G and/or 5G is missing.')
    if (iface_wlan_2g not in hostapd_constants.INTERFACE_2G_LIST
            or iface_wlan_5g not in hostapd_constants.INTERFACE_5G_LIST):
        raise ValueError('Invalid interface name was passed.')
    if security:
        if security.security_mode is hostapd_constants.WPA2:
            if not security.wpa2_cipher == 'CCMP':
                raise ValueError('The mock TPLink C1200 only supports a WPA2 '
                                 'unicast and multicast cipher of CCMP. '
                                 'Invalid cipher mode (%s)' %
                                 security.security.wpa2_cipher)
        else:
            raise ValueError(
                'The TPLink C1200 only supports WPA2 or open. Invalid '
                'security mode (%s)' % security.security_mode)

    # Common Parameters
    rates = {'supported_rates': '10 20 55 110 60 90 120 180 240 360 480 540'}
    n_capabilities = [
        hostapd_constants.N_CAPABILITY_SGI20,
        hostapd_constants.N_CAPABILITY_TX_STBC,
        hostapd_constants.N_CAPABILITY_RX_STBC1,
        hostapd_constants.N_CAPABILITY_MAX_AMSDU_7935
    ]
    # WPS IE
    # Broadcom IE
    vendor_elements = {
        'vendor_elements':
        'dd350050f204104a000110104400010210470010000000000000000000000000000000'
        '00103c0001031049000a00372a00012005022688'
        'dd090010180200000c0000'
    }

    # 2.4GHz
    if channel <= 11:
        interface = iface_wlan_2g
        rates['basic_rates'] = '10 20 55 110'
        short_preamble = True
        mode = hostapd_constants.MODE_11N_MIXED
        ac_capabilities = None
        vht_channel_width = None
        vht_center_channel = None

    # 5GHz
    else:
        interface = iface_wlan_5g
        rates['basic_rates'] = '60 120 240'
        short_preamble = False
        mode = hostapd_constants.MODE_11AC_MIXED
        n_capabilities.append(hostapd_constants.N_CAPABILITY_LDPC)
        ac_capabilities = [
            hostapd_constants.AC_CAPABILITY_MAX_MPDU_11454,
            hostapd_constants.AC_CAPABILITY_SHORT_GI_80,
            hostapd_constants.AC_CAPABILITY_RXLDPC,
            hostapd_constants.AC_CAPABILITY_TX_STBC_2BY1,
            hostapd_constants.AC_CAPABILITY_RX_STBC_1,
            hostapd_constants.AC_CAPABILITY_MAX_A_MPDU_LEN_EXP7,
        ]
        vht_channel_width = 40
        vht_center_channel = 36

    additional_params = _merge_dicts(
        rates, vendor_elements, hostapd_constants.ENABLE_RRM_BEACON_REPORT,
        hostapd_constants.ENABLE_RRM_NEIGHBOR_REPORT,
        hostapd_constants.UAPSD_ENABLED)

    config = hostapd_config.HostapdConfig(
        ssid=ssid,
        channel=channel,
        hidden=False,
        security=security,
        interface=interface,
        mode=mode,
        force_wmm=True,
        beacon_interval=100,
        dtim_period=1,
        short_preamble=short_preamble,
        n_capabilities=n_capabilities,
        ac_capabilities=ac_capabilities,
        vht_channel_width=vht_channel_width,
        vht_center_channel=vht_center_channel,
        additional_parameters=additional_params)
    return config


def tplink_tlwr940n(iface_wlan_2g=None, channel=None, security=None,
                    ssid=None):
    # TODO(b/143104825): Permit RIFS once it is supported
    """A simulated implementation of an TPLink TLWR940N AP.
    Args:
        iface_wlan_2g: The 2.4Ghz interface of the test AP.
        channel: What channel to use.
        security: A security profile (None or WPA2).
        ssid: The network name.
    Returns:
        A hostapd config.
    Differences from real TLWR940N:
        HT Info:
            TLWR940N: RIFS Permitted
            Simulated: RIFS Prohibited
        RSN Capabilities:
            TLWR940N: 0x0000 (RSN PTKSA Replay Counter Capab: 1)
            Simulated: 0x000c (RSN PTKSA Replay Counter Capab: 16)
    """
    if channel > 11:
        raise ValueError('The mock TP-Link TLWR940N does not support 5Ghz. '
                         'Invalid channel (%s)' % channel)
    if (iface_wlan_2g not in hostapd_constants.INTERFACE_2G_LIST):
        raise ValueError('Invalid interface name was passed.')

    if security:
        if security.security_mode is hostapd_constants.WPA2:
            if not security.wpa2_cipher == 'CCMP':
                raise ValueError('The mock TP-Link TLWR940N only supports a '
                                 'WPA2 unicast and multicast cipher of CCMP.'
                                 'Invalid cipher mode (%s)' %
                                 security.security.wpa2_cipher)
        else:
            raise ValueError('The mock TP-Link TLWR940N only supports WPA2. '
                             'Invalid security mode (%s)' %
                             security.security_mode)

    n_capabilities = [
        hostapd_constants.N_CAPABILITY_SGI20,
        hostapd_constants.N_CAPABILITY_TX_STBC,
        hostapd_constants.N_CAPABILITY_RX_STBC1
    ]

    rates = {
        'basic_rates': '10 20 55 110',
        'supported_rates': '10 20 55 110 60 90 120 180 240 360 480 540'
    }

    # Atheros Communications, Inc. IE
    # WPS IE
    vendor_elements = {
        'vendor_elements':
        'dd0900037f01010000ff7f'
        'dd260050f204104a0001101044000102104900140024e2600200010160000002000160'
        '0100020001'
    }

    additional_params = _merge_dicts(rates, vendor_elements,
                                     hostapd_constants.UAPSD_ENABLED)

    config = hostapd_config.HostapdConfig(
        ssid=ssid,
        channel=channel,
        hidden=False,
        security=security,
        interface=iface_wlan_2g,
        mode=hostapd_constants.MODE_11N_MIXED,
        force_wmm=True,
        beacon_interval=100,
        dtim_period=1,
        short_preamble=True,
        n_capabilities=n_capabilities,
        additional_parameters=additional_params)

    return config
