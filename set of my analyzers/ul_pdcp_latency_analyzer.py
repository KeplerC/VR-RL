#!/usr/bin/python
# Filename: ul_latency_breakdown_analyzer.py
"""
ul_latency_breakdown_analyzer.py
An KPI analyzer to monitor and manage uplink latency breakdown

Author: Kaiyuan Chen
"""

__all__ = ["UlLatBreakdownAnalyzer"]

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from mobile_insight.analyzer.analyzer import *
import time
import dis

class UlPDCPAnalyzer(Analyzer):
    """
    An KPI analyzer to monitor and manage uplink latency breakdown
    """

    def __init__(self):
        Analyzer.__init__(self)

        self.pdcp_buffer = [] # [[sequency #, sys_time, size, remianing size]]
        self.rlc_buffer = [] # [[timestamp, (sequence #, sys_time #, size)]]
        self.mapped_pdcp_rlc = [] # [(ts, rlc_sys_time, pdcp_size, trans_lat)

        self.bsr_buffer = []
        self.sr_buffer = []
        self.mac_buffer = [[]]*24
        self.trans_delay = []

        self.cnt1 = 0
        self.cnt2 = 0
        self.cnt3 = 0
        self.cnt4 = 0

        self.log_cnt1 = 0
        self.log_cnt2 = 0
        self.log_cnt3 = 0
        self.log_cnt4 = 0

        self.bytes1 = 0
        self.bytes2 = 0
        self.bytes3 = 0
        self.bytes4 = 0
        # add callback function
        self.add_source_callback(self.__map_callback)

        self._ana_delay = 0
        self._ana_delay1 = 0
        self._ana_delay2 = 0
        self._ana_delay21 = 0
        self._ana_delay211 = 0
        self._ana_delay212 = 0
        self._ana_delay22 = 0
        self._ana_delay221 = 0
        self._ana_delay222 = 0
        self._ana_delay223 = 0
        self._ana_delay224 = 0
        self._ana_delay2241 = 0
        self._ana_delay2242 = 0
        self._ana_delay2243 = 0
        self._ana_delay2244 = 0
        self._ana_delay3 = 0
        self._ana_delay4 = 0
        self.__decode_delay = 0
        self._ul_pkt_num = 0

        # Flag to show if it is the first sr event
        self.init_flag = False

        # Resource slot used by SR
        self.rb_slot1 = None
        self.rb_slot2 = None

        # Scheduled SR subframenumber
        self.sr_sfn = None
        self._debug = True

        # dis.dis(self.__map_callback)

        self.sample_rate = 1
        self.shift_l = 0 # shift in packet cnt
        self.shift_t = 0 # shift on timestamp in seconds
        self.sample_on_t = False
        self.__init_time = None

        # sample rate based on log sequence
        self.mac_tx_sample_rate = self.sample_rate
        self.rlc_sample_rate = self.sample_rate
        self.pdcp_sample_rate = self.sample_rate
        self.phy_sample_rate = self.sample_rate

        # sample rate based on time
        self.mac_tx_sample_rate_t = self.sample_rate
        self.rlc_sample_rate_t = self.sample_rate
        self.pdcp_sample_rate_t = self.sample_rate
        self.phy_sample_rate_t = self.sample_rate

        #ky defined
        self.decode = True
        self.analyze = True
        self.SN = 0
    def set_sample_rate(self, rate):
        self.sample_rate = rate

    def set_sample_on_time(self):
        self.sample_on_t = True
    def set_decode_off(self):
        self.decode = False 
    def set_analyzer_off(self):
        self.analyze = False
    def set_source(self,source):
        """
        Set the trace source. Enable the LTE ESM messages.

        :param source: the trace source.
        :type source: trace collector
        """
        Analyzer.set_source(self,source)
        #enable LTE PDCP and RLC logs
        source.enable_log("LTE_PDCP_UL_Cipher_Data_PDU")

    def __map_callback(self, msg):
        
        # For each incoming PDCP packet, map it to an rlc packet and then get the waiting/processing delay accordingly.
        # print "called"
        if msg.type_id == "LTE_PDCP_UL_Cipher_Data_PDU":
            self.cnt1+=1
            # self.log_info(str(msg.timestamp))
            before_decode_time = time.time()
            if not self.__init_time:
                self.__init_time = time.time()
            if (not self.sample_on_t and ((self.cnt1+self.shift_l) % (1/self.pdcp_sample_rate) == 0)) or \
                (self.sample_on_t and self.__init_time and (( \
                before_decode_time - self.__init_time)  % 1 < self.pdcp_sample_rate_t)):
                self.log_cnt1 += 1
                if(self.decode):
                    log_item = msg.data.decode(True)
                else:
                    self.log_info("Decode Turned Off")
                    return 
                self.log_info(str(log_item['timestamp']))
                self.__decode_delay += time.time() - before_decode_time
                before_ana_time = time.time()
                self.__decode_delay += time.time() - before_decode_time
                before_ana_time = time.time()
                if 'Subpackets' in log_item:
                    subPkt = log_item['Subpackets'][0]
                    self.bytes1 += subPkt['Subpacket Size']
                    listPDU = subPkt['PDCPUL CIPH DATA']
                    for pduItem in listPDU:
                        self.SN = pduItem["SN"]

            if self._debug:
                self.log_info('SN ' + str(self.SN))
                self.log_info("decode" + str(self.decode))
                self.log_info("analyze" + str(self.analyze))

