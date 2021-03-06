# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#*** nmeta - Network Metadata - TC Static Class and Methods

"""
This module is part of the nmeta suite running on top of Ryu SDN controller
to provide network identity and flow (traffic classification) metadata
"""

import sys
import datetime

import traceback

#*** Import netaddr for IP address checking:
from netaddr import IPAddress
from netaddr import IPNetwork
from netaddr import EUI
from netaddr import iter_iprange

#*** For logging configuration:
from baseclass import BaseClass

class StaticInspect(BaseClass):
    """
    This class provides methods to check
    static traffic classification (TC) classifier matches
    """
    def __init__(self, config, policy):
        #*** Required for BaseClass:
        self.config = config
        #*** Set up Logging with inherited base class method:
        self.configure_logging(__name__, "tc_static_logging_level_s",
                                                   "tc_static_logging_level_c")
        self.policy = policy

    def check_static(self, classifier_result, pkt):
        """
        Passed TCClassifierResult and Flow.Packet class objects
        Update the classifier_result match with boolean of result
        of match checks
        """
        policy_attr = classifier_result.policy_attr
        policy_value = classifier_result.policy_value
        if policy_attr == 'location_src':
            classifier_result.match = self.policy.locations.get_location(
                                        pkt.dpid, pkt.in_port) == policy_value
        elif policy_attr == 'time_of_day':
            classifier_result.match = \
                            self.is_match_time_of_day(policy_value)
        elif policy_attr == 'eth_src':
            classifier_result.match = \
                            self.is_match_macaddress(pkt.eth_src, policy_value)
        elif policy_attr == 'eth_dst':
            classifier_result.match = \
                            self.is_match_macaddress(pkt.eth_dst, policy_value)
        elif policy_attr == 'eth_type':
            classifier_result.match = \
                            self.is_match_ethertype(pkt.eth_type, policy_value)
        elif policy_attr == 'ip_src':
            classifier_result.match = \
                               self.is_match_ip_space(pkt.ip_src, policy_value)
        elif policy_attr == 'ip_dst':
            classifier_result.match = \
                               self.is_match_ip_space(pkt.ip_dst, policy_value)
        elif policy_attr == 'tcp_src':
            classifier_result.match = pkt.proto == 6 and pkt.tp_src == policy_value
        elif policy_attr == 'tcp_dst':
            classifier_result.match = pkt.proto == 6 and pkt.tp_dst == policy_value
        elif policy_attr == 'udp_src':
            classifier_result.match = pkt.proto == 17 and pkt.tp_src == policy_value
        elif policy_attr == 'udp_dst':
            classifier_result.match = pkt.proto == 17 and pkt.tp_dst == policy_value
        else:
            #*** didn't match any policy classifiers so return false and
            #***  log an error:
            self.logger.error("Unsupported static classifier policy_attr=%s",
                                                                   policy_attr)
            classifier_result.match = False

    def is_valid_macaddress(self, value_to_check):
        """
        Passed a prospective MAC address and check that
        it is valid.
        Return 1 for is valid IP address and 0 for not valid
        """
        try:
            result = EUI(value_to_check)
            if result.version != 48:
                self.logger.debug("Check of is_valid_macaddress on %s "
                        "returned false", value_to_check)
                return 0
        except:
            self.logger.debug("Check of "
                    "is_valid_macaddress on %s raised an exception",
                    value_to_check)
            return 0
        return 1

    def is_valid_ethertype(self, value_to_check):
        """
        Passed a prospective EtherType and check that
        it is valid. Can be hex (0x*) or decimal
        Return 1 for is valid IP address and 0 for not valid
        """
        if value_to_check[:2] == '0x':
            #*** Looks like hex:
            try:
                if not (int(value_to_check, 16) > 0 and \
                               int(value_to_check, 16) < 65536):
                    self.logger.debug("Check of "
                        "is_valid_ethertype as hex on %s returned false",
                        value_to_check)
                    return 0
            except:
                self.logger.debug("Check of "
                    "is_valid_ethertype as hex on %s raised an exception",
                        value_to_check)
                return 0
        else:
            #*** Perhaps it's decimal?
            try:
                if not (int(value_to_check) > 0 and \
                                  int(value_to_check) < 65536):
                    self.logger.debug("Check of "
                        "is_valid_ethertype as decimal on %s returned false",
                        value_to_check)
                    return 0
            except:
                self.logger.debug("Check of "
                    "is_valid_ethertype as decimal on %s raised an exception",
                        value_to_check)
                return 0
        return 1

    def is_valid_ip_space(self, value_to_check):
        """
        Passed a prospective IP address and check that
        it is valid. Can be IPv4 or IPv6 and can be range or have CIDR mask
        Return 1 for is valid IP address and 0 for not valid
        """
        #*** Does it look like a CIDR network?:
        if "/" in value_to_check:
            try:
                if not IPNetwork(value_to_check):
                    self.logger.debug("Network check "
                        "of is_valid_ip_space on %s returned false",
                        value_to_check)
                    return 0
            except:
                self.logger.debug("Network check of "
                    "is_valid_ip_space on %s raised an exception",
                    value_to_check)
                return 0
            return 1
        #*** Does it look like an IP range?:
        elif "-" in value_to_check:
            ip_range = value_to_check.split("-")
            if len(ip_range) != 2:
                self.logger.debug("Range check of "
                    "is_valid_ip_space on %s failed as not 2 items in list",
                    value_to_check)
                return 0
            try:
                if not (IPAddress(ip_range[0]) and IPAddress(ip_range[1])):
                    self.logger.debug("Range check "
                        "of is_valid_ip_space on %s returned false",
                        value_to_check)
                    return 0
            except:
                self.logger.debug("Range check of "
                    "is_valid_ip_space on %s raised an exception",
                    value_to_check)
                return 0
            #*** Check second value in range greater than first value:
            if IPAddress(ip_range[0]).value >= IPAddress(ip_range[1]).value:
                self.logger.debug("Range check of "
                    "is_valid_ip_space on %s failed as range is negative",
                    value_to_check)
                return 0
            #*** Check both IP addresses are the same version:
            if IPAddress(ip_range[0]).version != \
                                 IPAddress(ip_range[1]).version:
                self.logger.debug("Range check of "
                    "is_valid_ip_space on %s failed as IP versions are "
                    "different", value_to_check)
                return 0
            return 1
        else:
            #*** Or is it just a plain simple IP address?:
            try:
                if not IPAddress(value_to_check):
                    self.logger.debug("Check of "
                        "is_valid_ip_space on %s returned false",
                        value_to_check)
                    return 0
            except:
                self.logger.debug("Check of "
                    "is_valid_ip_space on %s raised an exception",
                    value_to_check)
                return 0
        return 1

    def is_valid_transport_port(self, value_to_check):
        """
        Passed a prospective TCP or UDP port number and check that
        it is an integer in the correct range.
        Return 1 for is valid port number and 0 for not valid port
        number
        """
        try:
            if not (int(value_to_check) > 0 and int(value_to_check) < 65536):
                self.logger.debug("Check of "
                    "is_valid_transport_port on %s returned false",
                    value_to_check)
                return 0
        except:
            self.logger.debug("Check of "
                "is_valid_transport_port on %s raised an exception",
                value_to_check)
            return 0
        return 1

    def is_match_time_of_day(self, time_of_day_range, time_now=datetime.datetime.now().time()):
        """
        Passed a time of day range (format HH:MM-HH:MM) and check to
        see if the current time is in that range.
        Return True if time is in range, otherwise False
        """
        #*** Turn range into two datetime format objects:
        time_of_day_range = str(time_of_day_range)
        (time_of_day1, time_of_day2) = time_of_day_range.split('-')
        (time_of_day1h, time_of_day1m) = time_of_day1.split(':')
        time_of_day1 = datetime.time(int(time_of_day1h), int(time_of_day1m))
        (time_of_day2h, time_of_day2m) = time_of_day2.split(':')
        time_of_day2 = datetime.time(int(time_of_day2h), int(time_of_day2m))
        #*** Check current time against range:
        if time_of_day1 <= time_of_day2:
            return time_of_day1 <= time_now <= time_of_day2
        else:
            return time_of_day1 <= time_now or time_now <= time_of_day2

    def is_match_macaddress(self, value_to_check1, value_to_check2):
        """
        Passed a two prospective MAC addresses and check to
        see if they are the same address.
        Return 1 for both the same MAC address and 0 for different
        """
        try:
            if not EUI(value_to_check1) == EUI(value_to_check2):
                self.logger.debug("Check of "
                        "is_match_macaddress on %s vs %s returned false",
                        value_to_check1, value_to_check2)
                return 0
        except:
            self.logger.debug("Check of "
                    "is_match_macaddress on %s vs %s raised an exception",
                    value_to_check1, value_to_check2)
            return 0
        return 1

    def is_match_ethertype(self, value_to_check1, value_to_check2):
        """
        Passed a two prospective EtherTypes and check to
        see if they are the same.
        Return 1 for both the same EtherType and 0 for different
        Values can be hex or decimal and are 2 bytes in length
        """
        #*** Normalise any hex to decimal integers:
        if str(value_to_check1)[:2] == '0x':
            #*** Looks like hex:
            try:
                value_to_check1_dec = int(value_to_check1, 16)
            except:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                self.logger.error("error=E1000010 "
                        "Failed to convert hex to dec. Exception %s, %s, %s",
                            exc_type, exc_value, exc_traceback)
                return 0
        else:
            #*** Not hex:
            try:
                value_to_check1_dec = int(value_to_check1)
            except:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                self.logger.error("error=E1000011 "
                        "Failed to convert to integer. Exception %s, %s, %s",
                            exc_type, exc_value, exc_traceback)
                return 0
        if str(value_to_check2)[:2] == '0x':
            #*** Looks like hex:
            try:
                value_to_check2_dec = int(value_to_check2, 16)
            except:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                self.logger.error("error=E1000012 "
                        "Failed to convert hex to dec. Exception %s, %s, %s",
                            exc_type, exc_value, exc_traceback)
                return 0
        else:
            #*** Not hex:
            try:
                value_to_check2_dec = int(value_to_check2)
            except:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                self.logger.error("error=E1000013 "
                        "Failed to convert to integer. Exception %s, %s, %s",
                            exc_type, exc_value, exc_traceback)
                return 0
        if value_to_check1_dec == value_to_check2_dec:
            return 1
        else:
            return 0

    def is_match_ip_space(self, ip_addr, ip_space):
        """
        Passed an IP address and an IP address space and check
        if the IP address belongs to the IP address space.
        If it does return 1 otherwise return 0
        """
        if not ip_addr:
            #*** Non-IP so return 0
            return 0
        #*** Does ip_space look like a CIDR network?:
        if "/" in ip_space:
            try:
                ip_space_object = IPNetwork(ip_space)
            except:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                self.logger.error("error=E1000015 "
                        "Exception converting ip_space=%s to IPNetwork object."
                        " Exception %s, %s, %s",
                            ip_space, exc_type, exc_value,
                            traceback.format_tb(exc_traceback))
                return 0
        #*** Does it look like an IP range?:
        elif "-" in ip_space:
            ip_range = ip_space.split("-")
            if len(ip_range) != 2:
                self.logger.error("error=E1000016 "
                    "Range split of ip_space %s on - was not len 2 but %s",
                    ip_space, len(ip_range))
                return 0
            try:
                ip_space_object = list(iter_iprange(ip_range[0], ip_range[1]))
            except:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                self.logger.error("error=E1000017 "
                        "Exception on conversion of ip_range=%s to "
                        "iter_iprange. Exception %s, %s, %s",
                        ip_range, exc_type, exc_value,
                        traceback.format_tb(exc_traceback))
                return 0
        else:
            #*** Or is it just a plain simple IP address?:
            try:
                ip_space_object = list(iter_iprange(ip_space, ip_space))
            except:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                self.logger.error("error=E1000019 "
                        "Exception converting ip_space=%s to iter_iprange"
                        " object. Exception %s, %s, %s",
                            ip_space, exc_type, exc_value,
                            traceback.format_tb(exc_traceback))
                return 0
        #*** Convert the IP address to a netaddr IPAddress object:
        try:
            ip_addr_object = IPAddress(ip_addr)
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.logger.error("error=E1000021 "
                            "Exception converting ip_addr=%s to IPAddress "
                            "object. Exception %s, %s, %s",
                            ip_addr, exc_type, exc_value,
                            traceback.format_tb(exc_traceback))
            return 0
        #*** Now we have both in netaddr form, so do the match comparison:
        if ip_addr_object in ip_space_object:
            return 1
        else:
            return 0
