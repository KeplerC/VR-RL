#!/usr/bin/python
# Filename: ul_latency_breakdown_analyzer.py
"""
ul_latency_breakdown_analyzer.py
An KPI analyzer to monitor and manage uplink latency breakdown

Author: Zhehui Zhang
"""

__all__ = ["UlSampleAnalyzer"]

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from mobile_insight.analyzer.analyzer import *
import time
import dis
from ul_mac_latency_analyzer import UlMacLatencyAnalyzer

class UlSampleAnalyzer(Analyzer):
    """
    An KPI analyzer to monitor and manage uplink latency breakdown
    """

    def __init__(self):
        Analyzer.__init__(self)
        self.add_source_callback(self.__map_callback)

        self.pdcp_buffer = [] # [[sequency #, sys_time, size, remianing size]]
        self.rlc_buffer = [] # [[timestamp, (sequence #, sys_time #, size)]]
        self.mac_buffer = [] # [(ts, rlc_sys_time, pdcp_size, trans_lat)

        self.init_flag = False
        # Resource slot used by SR
        self.rb_slot1 = None
        self.rb_slot2 = None

        # Scheduled SR subframenumber
        self.sr_sfn = None

        self.bsr_buffer = []
        self.sr_buffer = []
        # self.mac_buffer = [[]]*24
        self.trans_delay = []

        self.last_bytes = {}  # LACI -> bytes <int> Last remaining bytes in MAC UL buffer
        self.buffer = {}  # LCID -> [sys_time, packet_bytes] buffered mac ul packets
        self.ctrl_pkt_sfn = {}  # LCID -> sys_fn*10 + sun_fn when last mac ul control packet comes
        self.cur_fn = -1  # Record current sys_fn*10+ sub_fn for mac ul buffer
        self.lat_stat = []  # Record ul waiting latency (ts, sys_time, pdu_size)
        self.queue_length = 0
        self.mapping = False
        self.bcast_dict = {}
        self.mac_buffer_dict = {}

        self.__init_time = None
        self.cfg_idx = 4

        self.pdcp_cnt = 0
        self.rlc_cnt = 0
        self.mac_cnt = 0

        sample_rate = 0.05
        self.shift_l = 1
        self.shift_t = 0.2
        self.sample_on_t = True

        # sample rate based on log sequence
        self.mac_buf_sample_rate = sample_rate
        self.mac_tx_sample_rate = 0.1
        self.rlc_sample_rate = sample_rate
        self.pdcp_sample_rate = sample_rate
        self.phy_sample_rate = 0.1

        # sample rate based on time
        self.mac_buf_sample_rate_t = sample_rate
        self.mac_tx_sample_rate_t = 0.1
        self.rlc_sample_rate_t = sample_rate
        self.pdcp_sample_rate_t = sample_rate
        self.phy_sample_rate_t = 0.1

    def set_source(self,source):
        """
        Set the trace source. Enable the LTE ESM messages.

        :param source: the trace source.
        :type source: trace collector
        """
        Analyzer.set_source(self,source)
        #enable LTE PDCP and RLC logs
        source.enable_log("LTE_PDCP_UL_Cipher_Data_PDU")
        source.enable_log("LTE_RLC_UL_AM_All_PDU")
        source.enable_log("LTE_PHY_PUCCH_Tx_Report")
        source.enable_log("LTE_MAC_UL_Transport_Block")
        source.enable_log("LTE_MAC_UL_Buffer_Status_Internal")

    def __sn_is_before(self, a_ts, a_sys_time, b_ts, b_sys_time):
        """
        Check if time a is before time b
        :param a_ts: timestamp of a
        :param a_sys_fn: system frame number of a
        :param a_sub_fn: subframe number of a
        :param b_ts: timestamp of b
        :param b_sys_fn: system frame number of b
        :param b_sub_fn: subframe number of b
        :return: Boolean
        """
        ts_inter = (a_ts - b_ts).total_seconds()
        if ts_inter < -0.3:
            return True
        elif ts_inter > 0.3:
            return False
        else:
            return a_sys_time < b_sys_time or (a_sys_time > 9000 and b_sys_time < 3000)

    def __rlc_sn_is_before(self, a_sys_time, b_sys_time):
        """
        Check if suquence a is before time b
        :param a_sn: sequence number of a
        :param b_sn: sequence number of b
        :return: Boolean
        """
        return a_sys_time < b_sys_time or (a_sys_time > 9000 and b_sys_time < 3000)

    def __get_time_inter(self, a_sys_time, b_sys_time):
        inter = abs(a_sys_time-b_sys_time)
        if inter > 10000:
            inter = abs(inter - 10240)
        return inter


    def __map_callback(self, msg):

        if msg.type_id == "LTE_PDCP_UL_Cipher_Data_PDU":

            log_item = msg.data.decode()
            self.pdcp_cnt += 1
            if not self.__init_time:
                self.__init_time = log_item['timestamp']
            if self.__init_time:
                print (log_item['timestamp'] - self.__init_time).total_seconds() % 1
            if (not self.sample_on_t and ((self.pdcp_cnt+self.shift_l) % (1/self.pdcp_sample_rate) == 0)) or \
                (self.sample_on_t and self.__init_time and (( \
                log_item['timestamp'] - self.__init_time + self.shift_t).total_seconds() % 1 < self.pdcp_sample_rate_t)):
                print self.pdcp_cnt
                if 'Subpackets' in log_item:
                    subPkt = log_item['Subpackets'][0]
                    listPDU = subPkt['PDCPUL CIPH DATA']
                    for pduItem in listPDU:
                        if pduItem['Cfg Idx'] == self.cfg_idx:
                        # print pduItem
                        # sn = int(pduItem['SN'])
                            sys_fn = int(pduItem['Sys FN'])
                            sub_fn = int(pduItem['Sub FN'])
                            pdu_size = int(pduItem['PDU Size'])
                            print 'New PDCP: ', log_item['timestamp'], sys_fn*10+sub_fn, pdu_size, pdu_size
                            self.pdcp_buffer.append((log_item['timestamp'], sys_fn*10+sub_fn))

        elif msg.type_id == "LTE_RLC_UL_AM_All_PDU":
            log_item = msg.data.decode()
            # print log_item_dict
            self.rlc_cnt += 1
            if (not self.sample_on_t and (self.rlc_cnt % (1 / self.rlc_sample_rate) == 0)) or \
                    (self.sample_on_t and self.__init_time and (( \
                   log_item['timestamp'] - self.__init_time).total_seconds() % 1 < self.rlc_sample_rate_t)):
                if 'Subpackets' in log_item:
                    subPkt = log_item['Subpackets'][0]
                    listPDU = subPkt['RLCUL PDUs']
                    for pduItem in listPDU:
                        if pduItem['PDU TYPE'] == 'RLCUL DATA' and pduItem['rb_cfg_idx'] == self.cfg_idx:
                            sn = int(pduItem['SN'])
                            sys_fn = int(pduItem['sys_fn'])
                            sub_fn = int(pduItem['sub_fn'])
                            hdr_len = int(pduItem['logged_bytes'])  # rlc_pdu_size = pdcp_pdu_size + rlc_hdr_len
                            sdu_size = int(pduItem['pdu_bytes']) - hdr_len
                            li_flag = len(pduItem['RLC DATA LI']) if 'RLC DATA LI' in pduItem else 0
                            fi = pduItem['FI'] # FI: 01 stands for begining of segments, \
                                               # 10 stands for end of segments, 11 stands for middle segments
                            # TODO: check if all rlc packets seq # is ordered
                            for i in range(len(self.rlc_buffer)):
                                if self.__rlc_sn_is_before(sn, self.rlc_buffer[i][2]):
                                    self.rlc_buffer.insert(i, (log_item['timestamp'], sys_fn * 10 + sub_fn, sn))
                                    break
                                if i == len(self.rlc_buffer) - 1:
                                    self.rlc_buffer.append((log_item['timestamp'], sys_fn * 10 + sub_fn, sn))
                            if not self.rlc_buffer:
                                self.rlc_buffer.append((log_item['timestamp'], sys_fn * 10 + sub_fn, sn))
                            print 'New RLC: ', log_item['timestamp'], sn, sys_fn*10 + sub_fn, sdu_size, fi, li_flag

        # elif msg.type_id == "LTE_PHY_PUCCH_Tx_Report":
        #     pass
        #     log_item = msg.data.decode()
        #
        #     if 'Records' in log_item:
        #         records = log_item['Records']
        #         timestamp = str(log_item['timestamp'])
        #
        #         for record in records:
        #             print 'New PHY: ', timestamp, record['Current SFN SF']
        #             uciformat = record['Format']
        #             if uciformat == 'Format 1':
        #                 self.init_flag = True
        #                 self.rb_slot1 = record['Start RB Slot 0']
        #                 self.rb_slot2 = record['Start RB Slot 1']
        #                 self.sr_sfn = record['Current SFN SF'] % 10  # subframenumber
        #                 self.sr_buffer.append([timestamp, record['Current SFN SF']])
        #             elif uciformat == 'Format 1B' or uciformat == 'Format 1A':
        #                 # TODO: reset init_flag for new logs
        #                 if self.init_flag:
        #                     if int(record['Start RB Slot 1']) == self.rb_slot2 and int(record['Start RB Slot 0']) == self.rb_slot1 \
        #                             and record['Current SFN SF'] % 10 == self.sr_sfn:
        #                         self.sr_buffer.append([timestamp, record['Current SFN SF']])
        #             elif uciformat == "Format 3":
        #                 # TODO: Deal with SR event in format 3
        #                 pass
        #             if len(self.sr_buffer) > 40:
        #                 del self.sr_buffer[0]

        # get bsr and get mac harq retx delay
        # elif msg.type_id == "LTE_MAC_UL_Transport_Block":
        #     log_item = msg.data.decode()
        #     ts = str(log_item['timestamp'])
        #
        #     if 'Subpackets' in log_item:
        #         for pkt in log_item['Subpackets'][0]['Samples']:
        #             grant = pkt['Grant (bytes)']
        #             harq_id = pkt['HARQ ID']
        #             pkt_size = grant - pkt['Padding (bytes)']
        #             fn = int(pkt['SFN'])
        #             sfn = int(pkt['Sub-FN'])
        #             cell_id = int(pkt['Cell Id'])
        #             print 'New RLC: ', ts, fn*10+sfn

        elif msg.type_id == "LTE_MAC_UL_Buffer_Status_Internal":

            log_item = msg.data.decode()

            pkt_version = log_item['Subpackets'][0]['Version']
            self.mac_cnt += 1
            if (not self.sample_on_t and (self.mac_cnt % (1 / self.mac_buf_sample_rate) == 0)) or \
                    (self.sample_on_t and self.__init_time and (( \
                    log_item['timestamp'] - self.__init_time).total_seconds() % 1 < self.mac_buf_sample_rate_t)):
                for sample in log_item['Subpackets'][0]['Samples']:
                    sub_fn = int(sample['Sub FN'])
                    sys_fn = int(sample['Sys FN'])
                    sys_time = sys_fn * 10 + sub_fn
                    # Incorrect sys_fn and sub_fn are normally 1023 and 15
                    # print log_item['timestamp'], sys_time, self.cur_fn
                    if sys_time < 10240:
                        if self.cur_fn > 0:
                            # reset historical data if time lag is bigger than 1ms
                            lag = sys_time - self.cur_fn
                            if lag > 1 or -10239 < lag < 0:
                                self.last_bytes = {}
                                self.buffer = {}
                                self.ctrl_pkt_sfn = {}
                        self.cur_fn = sys_time
                    elif self.cur_fn >= 0:  # if invalid and inited, add current sfn
                        self.cur_fn = (self.cur_fn + 1) % 10240
                    else:
                        continue


                    for lcid in sample['LCIDs']:
                        idx = lcid['Ld Id']
                        if idx != 4:
                            continue
                        # FIXME: Are these initializations valid?
                        if pkt_version == 24:
                            new_bytes = lcid.get('New Compressed Bytes', 0)
                        else:
                            new_bytes = lcid.get('New bytes', 0)
                        ctrl_bytes = lcid.get('Ctrl bytes', 0)
                        total_bytes = new_bytes + ctrl_bytes  # if 'Total Bytes' not in lcid else int(lcid['Total Bytes'])


                        if idx not in self.buffer:
                            self.buffer[idx] = []
                            self.last_bytes[idx] = 0
                            self.ctrl_pkt_sfn[idx] = None

                        # add new packet to buffer
                        if not new_bytes == 0:
                            # TODO: Need a better way to decided if it is a new packet or left packet
                            if new_bytes > self.last_bytes[idx]:
                                new_bytes = new_bytes - self.last_bytes[idx]
                                self.buffer[idx].append([self.cur_fn, new_bytes])

                        if not ctrl_bytes == 0:
                            total_bytes -= 2
                            if not self.ctrl_pkt_sfn[idx]:
                                self.ctrl_pkt_sfn[idx] = self.cur_fn
                        elif self.ctrl_pkt_sfn[idx]:
                            ctrl_pkt_delay = self.cur_fn - self.ctrl_pkt_sfn[idx]
                            ctrl_pkt_delay %= 10240
                            self.ctrl_pkt_sfn[idx] = None


                        if self.last_bytes[idx] > total_bytes:
                            # print log_item['timestamp'], self.cur_fn, self.last_bytes[idx]
                            sent_bytes = self.last_bytes[idx] - total_bytes
                            if self.__init_time:
                                print 'New MAC Buf: ', str(log_item['timestamp']-self.__init_time), self.cur_fn
                            while len(self.buffer[idx]) > 0 and sent_bytes > 0:
                                # if str(log_item['timestamp']) == '2018-03-09 21:47:01.053043':
                                #     print self.buffer, self.last_bytes
                                pkt = self.buffer[idx][0]
                                if len(pkt) == 2:
                                    pkt.append(self.cur_fn)
                                    pkt.append(pkt[1])
                                if pkt[1] <= sent_bytes:
                                    pkt_delay = (self.cur_fn - pkt[0])%10240
                                    wait_delay = (self.cur_fn - pkt[2])%10240
                                    self.buffer[idx].pop(0)
                                    sent_bytes -= pkt[1]
                                    print 'Delay:', log_item['timestamp'], self.cur_fn, pkt[3], pkt_delay, wait_delay
                                    self.mac_buffer.append((log_item['timestamp'], pkt[2], pkt_delay, wait_delay))
                                    if self.mapping: # avoid storage overhead when uplink rlc analyzer is not enabled
                                        self.lat_stat.append((log_item['timestamp'], self.cur_fn, pkt[1], pkt_delay))
                                else:
                                    pkt[1] -= sent_bytes
                                    sent_bytes = 0
                                if pkt[1] == 0:
                                    pkt_delay = (self.cur_fn - pkt[0]) % 10240
                                    wait_delay = (self.cur_fn - pkt[2]) % 10240 # trans delay
                                    sent_bytes -= pkt[1]
                                    print 'Delay:', log_item['timestamp'], self.cur_fn, pkt[3], pkt_delay, wait_delay
                                    self.mac_buffer.append((log_item['timestamp'], pkt[2], pkt_delay, wait_delay))
                                    if self.mapping:  # avoid storage overhead when uplink rlc analyzer is not enabled
                                        self.lat_stat.append((log_item['timestamp'], self.cur_fn, pkt[1], pkt_delay))
                                    self.buffer[idx].pop(0)

                        self.last_bytes[idx] = total_bytes
                # print self.mac_buffer,'\n', self.rlc_buffer,'\n', self.pdcp_buffer
                if self.__init_time and (log_item['timestamp'] - self.__init_time).total_seconds() > 666:
                    print (log_item['timestamp'] - self.__init_time).total_seconds()
                    exit(0)
                # if len(self.mac_buffer) > 9 or len(self.rlc_buffer) > 9:
                    # exit(0)
                while self.mac_buffer and self.rlc_buffer and self.pdcp_buffer:
                    while self.mac_buffer and self.rlc_buffer and self.__sn_is_before(self.mac_buffer[0][0], self.mac_buffer[0][1], self.rlc_buffer[0][0], self.rlc_buffer[0][1]):
                        # print '1'
                        del self.mac_buffer[0]
                    while self.mac_buffer and self.rlc_buffer and self.__sn_is_before(self.rlc_buffer[0][0], self.rlc_buffer[0][1], self.mac_buffer[0][0], self.mac_buffer[0][1]):
                        # print '2'
                        del self.rlc_buffer[0]
                    if self.mac_buffer and self.rlc_buffer and self.mac_buffer[0][1] == self.rlc_buffer[0][1]:
                        # print '3'
                        while self.mac_buffer and self.pdcp_buffer and self.__sn_is_before(self.mac_buffer[0][0],
                                                                                          self.mac_buffer[0][1],
                                                                                          self.pdcp_buffer[0][0],
                                                                                          self.pdcp_buffer[0][1]):
                            # print '4'
                            del self.mac_buffer[0]
                        while self.mac_buffer and self.pdcp_buffer and self.__sn_is_before(self.pdcp_buffer[0][0],
                                                                                          self.pdcp_buffer[0][1],
                                                                                          self.mac_buffer[0][0],
                                                                                          self.mac_buffer[0][1]):
                            # print '5'
                            del self.pdcp_buffer[0]
                        if self.mac_buffer and self.pdcp_buffer and self.mac_buffer[0][1] == self.pdcp_buffer[0][1]:
                            print 'yes', self.mac_buffer[0][0], self.mac_buffer[0][1:]
                            del self.mac_buffer[0]
                            del self.pdcp_buffer[0]
                            # del self.rlc_buffer[0]




