#!/usr/bin/python
# Filename: ul_latency_breakdown_analyzer.py
"""
ul_latency_breakdown_analyzer.py
An KPI analyzer to monitor and manage uplink latency breakdown

Author: Zhehui Zhang
"""

__all__ = ["UlLatBreakdownAnalyzer"]

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from mobile_insight.analyzer.analyzer import *
import time
import dis
from ul_mac_latency_analyzer import UlMacLatencyAnalyzer
from writer import write


class UlLatBreakdownAnalyzer(Analyzer):
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

        self.include_analyzer('UlMacLatencyAnalyzer', [self.__map_callback])
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

        
    def set_sample_rate(self, rate):
        self.sample_rate = rate

    def set_sample_on_time(self):
        self.sample_on_t = True

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


    def __get_time_inter(self, a_sys_time, b_sys_time):
        inter = abs(a_sys_time-b_sys_time)
        if inter > 10000:
            inter = abs(inter - 10240)
        return inter


    def __map_callback(self, msg):
        self.get_analyzer('UlMacLatencyAnalyzer').enable_mapping()

        # For each incoming PDCP packet, map it to an rlc packet and then get the waiting/processing delay accordingly.
        # print "called"
        if msg.type_id == "LTE_PDCP_UL_Cipher_Data_PDU":
            self.cnt1+=1
            # self.log_info(str(msg.timestamp))
            before_decode_time = time.time()
            if not self.__init_time:
                self.__init_time = time.time()
                self.get_analyzer('UlMacLatencyAnalyzer').set_init_time(time.time())
                self.get_analyzer('UlMacLatencyAnalyzer').set_sample_rate(self.sample_rate)
            if (not self.sample_on_t and ((self.cnt1+self.shift_l) % (1/self.pdcp_sample_rate) == 0)) or \
                (self.sample_on_t and self.__init_time and (( \
                before_decode_time - self.__init_time)  % 1 < self.pdcp_sample_rate_t)):
                self.log_cnt1 += 1

                log_item = msg.data.decode()
                self.log_info(str(log_item))
                if log_item == None:
                    return
                self.log_info(str(log_item['timestamp']))
                self.__decode_delay += time.time() - before_decode_time
                before_ana_time = time.time()
                if 'Subpackets' in log_item:
                    subPkt = log_item['Subpackets'][0]
                    self.bytes1 += subPkt['Subpacket Size']
                    listPDU = subPkt['PDCPUL CIPH DATA']
                    for pduItem in listPDU:
                        if pduItem['Cfg Idx'] == 3:
                        # print pduItem
                        # sn = int(pduItem['SN'])
                            sys_fn = int(pduItem['Sys FN'])
                            sub_fn = int(pduItem['Sub FN'])
                            pdu_size = int(pduItem['PDU Size'])
                            self.pdcp_buffer.append([log_item['timestamp'], sys_fn*10+sub_fn, pdu_size, pdu_size])
                            # print 'New PDCP: ', log_item['timestamp'], sys_fn*10+sub_fn, pdu_size, pdu_size
                    self._ana_delay1 += time.time() - before_ana_time
                    self._ana_delay += time.time() - before_ana_time

        elif msg.type_id == "LTE_RLC_UL_AM_All_PDU":
            self.cnt2 += 1
            before_decode_time = time.time()
            if (not self.sample_on_t and (self.cnt2 % (1 / self.rlc_sample_rate) == 0)) or \
                    (self.sample_on_t and self.__init_time and (( \
                    before_decode_time - self.__init_time)  % 1 < self.rlc_sample_rate_t)):
                self.log_cnt2 += 1
                log_item = msg.data.decode()
                if(log_item == None):
                    return
                self.__decode_delay += time.time() - before_decode_time
                before_ana_time = time.time()
                # print log_item_dict
                before_ana_time221 = time.time()
                if 'Subpackets' in log_item:
                    subPkt = log_item['Subpackets'][0]
                    self.bytes2 += subPkt['Subpacket Size']
                    listPDU = subPkt['RLCUL PDUs']
                    self._ana_delay211 += time.time() - before_ana_time221
                    for pduItem in listPDU:
                        before_ana_time211 = time.time()
                        if pduItem['PDU TYPE'] == 'RLCUL DATA' and pduItem['rb_cfg_idx'] == 3:
                            sn = int(pduItem['SN'])
                            sys_fn = int(pduItem['sys_fn'])
                            sub_fn = int(pduItem['sub_fn'])
                            hdr_len = int(pduItem['logged_bytes'])  # rlc_pdu_size = pdcp_pdu_size + rlc_hdr_len
                            sdu_size = int(pduItem['pdu_bytes']) - hdr_len
                            li_flag = len(pduItem['RLC DATA LI']) if 'RLC DATA LI' in pduItem else 0
                            fi = pduItem['FI'] # FI: 01 stands for begining of segments, \
                                               # 10 stands for end of segments, 11 stands for middle segments
                            # TODO: check if all rlc packets seq # is ordered
                            # print log_item['timestamp'], sn, sys_fn*10 + sub_fn, sdu_size, fi, li_flag
                            if len(self.rlc_buffer) > 0 and sn - self.rlc_buffer[-1][0] > 1:
                                pass
                                # print "Debug info: ", self.rlc_buffer[-1][-1], sn
                            if fi == '01' or fi == '00':
                                self.rlc_buffer = [log_item['timestamp'], (sn, sys_fn*10 + sub_fn, sdu_size, li_flag)]
                            elif fi == '10' or fi == '11':
                                if self.rlc_buffer:
                                    self.rlc_buffer.append((sn, sys_fn*10 + sub_fn, sdu_size))
                                elif fi == '10': # A rlc segment starts while former one didn't end
                                    self.log_debug("Packet loss. Buffer=" + str(self.rlc_buffer))
                            else:
                                self.log_error("Unknown FI field in RLC_UL_AM_ALL_PDU.")
                            self._ana_delay211 += time.time() - before_ana_time211
                            before_ana_time212 = time.time()
                            if fi == '00' or fi == '10':
                                # print 'PDCP:', self.pdcp_buffer
                                # print 'RLC:', self.rlc_buffer
                                while self.pdcp_buffer and self.rlc_buffer and self.__sn_is_before(self.pdcp_buffer[0][0],
                                        self.pdcp_buffer[0][1], self.rlc_buffer[0],
                                        self.rlc_buffer[1][1]):
                                    # self.log_info("Warning: discarded PDCP packet. " + str(self.pdcp_buffer[0]))
                                    del self.pdcp_buffer[0]
                                while len(self.rlc_buffer) > 1 and self.pdcp_buffer:
                                    # print 'This round PDCP:', self.pdcp_buffer
                                    # print 'This round RLC: ', self.rlc_buffer
                                    if not self.pdcp_buffer:
                                        break
                                    if self.__sn_is_before(self.rlc_buffer[0], self.rlc_buffer[1][1], \
                                                           self.pdcp_buffer[0][0], self.pdcp_buffer[0][1], ):
                                        del self.rlc_buffer[1]
                                    else:
                                        # TODO: check if there are matched RLC packets
                                        # print rlc_sdu, pdcp_pdu
                                        rlc_sdu_size = self.rlc_buffer[1][2]
                                        if rlc_sdu_size > self.pdcp_buffer[0][3]:
                                            while self.pdcp_buffer and rlc_sdu_size > self.pdcp_buffer[0][3]:
                                                # matched
                                                # print 'PDCP: ', self.pdcp_buffer[0], '\nRLC: ', self.rlc_buffer[1]
                                                self.mapped_pdcp_rlc.append((self.rlc_buffer[0], \
                                                        self.pdcp_buffer[0][1], self.pdcp_buffer[0][2], \
                                                        self.__get_time_inter(self.rlc_buffer[1][1], \
                                                        self.pdcp_buffer[0][1])))
                                                rlc_sdu_size -= self.pdcp_buffer[0][3]
                                                del self.pdcp_buffer[0]
                                            if self.pdcp_buffer:
                                                if rlc_sdu_size == self.pdcp_buffer[0][3]:
                                                    # matched
                                                    # print 'PDCP: ', self.pdcp_buffer[0], '\nRLC: ', self.rlc_buffer[1]
                                                    self.mapped_pdcp_rlc.append((self.rlc_buffer[0], \
                                                        self.pdcp_buffer[0][1], self.pdcp_buffer[0][2], \
                                                        self.__get_time_inter(self.rlc_buffer[1][1], \
                                                        self.pdcp_buffer[0][1])))
                                                    del self.pdcp_buffer[0]
                                                    del self.rlc_buffer[1]
                                                else:
                                                    self.pdcp_buffer[0][3] -= rlc_sdu_size
                                                    del self.rlc_buffer[1]
                                        elif rlc_sdu_size == self.pdcp_buffer[0][2]:
                                            # matched
                                            self.mapped_pdcp_rlc.append((self.rlc_buffer[0], \
                                                    self.pdcp_buffer[0][1], self.pdcp_buffer[0][2], \
                                                    self.__get_time_inter(self.rlc_buffer[1][1], \
                                                    self.pdcp_buffer[0][1])))
                                            # print 'PDCP: ', self.pdcp_buffer[0], '\nRLC: ', self.rlc_buffer[1]
                                            del self.pdcp_buffer[0]
                                            del self.rlc_buffer[1]
                                        else:
                                            self.pdcp_buffer[0][3] -= rlc_sdu_size
                                            del self.rlc_buffer[1]
                                if len(self.rlc_buffer) == 1:
                                    self.rlc_buffer = []
                            self._ana_delay212 += time.time() - before_ana_time212

                    self._ana_delay21 += time.time() - before_ana_time
                    before_ana_time22 = time.time()
                    if self.mapped_pdcp_rlc:
                        # print 'PDCP and RLC: ', self.mapped_pdcp_rlc
                        # print 'MAC: ', self.get_analyzer('UlMacLatencyAnalyzer').lat_stat

                        before_ana_time221 = time.time()
                        mac_pkts = self.get_analyzer('UlMacLatencyAnalyzer').lat_stat

                        # self.log_debug("len(mac_pkts): "+str(len(mac_pkts)))

                        self._ana_delay221 += time.time() - before_ana_time221


                        # discard the pdcp packet if it arrives before current mac packet
                        while self.mapped_pdcp_rlc and mac_pkts:
                            before_ana_time222 = time.time()
                            while self.mapped_pdcp_rlc and mac_pkts \
                                    and self.__sn_is_before(self.mapped_pdcp_rlc[0][0], self.mapped_pdcp_rlc[0][1] \
                                            , mac_pkts[0][0], mac_pkts[0][1]):
                                # self.log_info("Warning: discarded PDCP packet. " + str(self.mapped_pdcp_rlc[0]))
                                del self.mapped_pdcp_rlc[0]
                            self._ana_delay222 += time.time() - before_ana_time222
                            before_ana_time223 = time.time()
                            while self.mapped_pdcp_rlc and mac_pkts \
                                    and self.__sn_is_before(mac_pkts[0][0], mac_pkts[0][1], \
                                            self.mapped_pdcp_rlc[0][0], self.mapped_pdcp_rlc[0][1]):
                                # self.log_info("Warning: discarded MAC packet. " + str(mac_pkts[0]))
                                del mac_pkts[0]
                            self._ana_delay223 += time.time() - before_ana_time223

                            if self.mapped_pdcp_rlc and mac_pkts:
                                before_ana_time224 = time.time()
                                pkt_size = self.mapped_pdcp_rlc[0][2]
                                trans_delay = self.mapped_pdcp_rlc[0][3]
                                wait_delay = mac_pkts[0][3]
                                if wait_delay > 4:
                                    wait_delay -= 4
                                    proc_delay = 4
                                else:
                                    proc_delay = wait_delay
                                    wait_delay = 0
                                self._ana_delay2241 += time.time() - before_ana_time224
                                before_ana_time2242 = time.time()
                                # kpi = {}
                                # kpi['pkt_size'] = str(pkt_size)
                                # kpi['wait_delay'] = str(wait_delay)
                                # kpi['proc_delay'] = str(proc_delay)
                                # kpi['trans_delay'] = str(trans_delay)
                                # self.broadcast_info('UL_LAT_BREAKDOWN', kpi)
                                self._ana_delay2242 += time.time() - before_ana_time2242
                                before_ana_time2243 = time.time()
                                # self.log_debug('UL_LAT_BREAKDOWN: ' + str(kpi))
                                self._ul_pkt_num += 1
                                # self.log_info(str(self._ul_pkt_num))
                                self._ana_delay2243 += time.time() - before_ana_time2243
                                before_ana_time2244 = time.time()
                                print "Mapped: ", self.mapped_pdcp_rlc[0][0], pkt_size, wait_delay, proc_delay, trans_delay
                                del self.mapped_pdcp_rlc[0]
                                del mac_pkts[0]
                                self._ana_delay2244 += time.time() - before_ana_time2244
                                self._ana_delay224 += time.time() - before_ana_time224
                    self._ana_delay22 += time.time() - before_ana_time22
                    self._ana_delay2 += time.time() - before_ana_time
                    self._ana_delay += time.time() - before_ana_time


        elif msg.type_id == "LTE_PHY_PUCCH_Tx_Report":
            self.cnt3 += 1
            before_decode_time = time.time()
            if (not self.sample_on_t and (self.cnt3 % (1 / self.phy_sample_rate) == 0)) or \
                    (self.sample_on_t and self.__init_time and (( \
                    before_decode_time - self.__init_time)  % 1 < self.phy_sample_rate_t)):
                self.log_cnt3 += 1
                log_item = msg.data.decode()
                if(log_item == None):
                    return
                self.__decode_delay += time.time() - before_decode_time
                before_ana_time = time.time()
                if log_item == None:
                    return
                if 'Records' in log_item:
                    records = log_item['Records']
                    timestamp = str(log_item['timestamp'])

                    for record in records:
                        # pucch_tx_power = record['PUCCH Tx Power (dBm)']
                        # bcast_dict = {}
                        # bcast_dict['tx power'] = pucch_tx_power
                        # bcast_dict['timestamp'] = timestamp
                        # self.broadcast_info("PUCCH_TX_POWER", bcast_dict)
                        # self.log_info("PUCCH_TX_POWER: " + str(bcast_dict))
                        uciformat = record['Format']
                        if uciformat == 'Format 1':
                            self.init_flag = True
                            self.rb_slot1 = record['Start RB Slot 0']
                            self.rb_slot2 = record['Start RB Slot 1']
                            self.sr_sfn = record['Current SFN SF'] % 10  # subframenumber
                            self.sr_buffer.append([timestamp, record['Current SFN SF']])
                        elif uciformat == 'Format 1B' or uciformat == 'Format 1A':
                            # TODO: reset init_flag for new logs
                            if self.init_flag:
                                if int(record['Start RB Slot 1']) == self.rb_slot2 and int(record['Start RB Slot 0']) == self.rb_slot1 \
                                        and record['Current SFN SF'] % 10 == self.sr_sfn:
                                    self.sr_buffer.append([timestamp, record['Current SFN SF']])
                        elif uciformat == "Format 3":
                            # TODO: Deal with SR event in format 3
                            pass
                        if len(self.sr_buffer) > 40:
                            del self.sr_buffer[0]
                    self._ana_delay3 += time.time() - before_ana_time
                    self._ana_delay += time.time() - before_ana_time


        # get bsr and get mac harq retx delay
        elif msg.type_id == "LTE_MAC_UL_Transport_Block":
            self.cnt4 += 1
            before_decode_time = time.time()
            if (not self.sample_on_t and (self.cnt4 % (1 / self.mac_tx_sample_rate) == 0)) or \
                    (self.sample_on_t and self.__init_time and (( \
                    before_decode_time - self.__init_time)  % 1 < self.mac_tx_sample_rate_t)):
                self.log_cnt4 += 1
                log_item = msg.data.decode()
                if(log_item == None):
                    return
                self.__decode_delay += time.time() - before_decode_time
                before_ana_time = time.time()
                ts = str(log_item['timestamp'])

                # self.log_info(str(log_item))
                if 'Subpackets' in log_item:
                    self.bytes4 += log_item['Subpackets'][0]['SubPacket Size']
                    for pkt in log_item['Subpackets'][0]['Samples']:
                        grant = pkt['Grant (bytes)']
                        harq_id = pkt['HARQ ID']
                        pkt_size = grant - pkt['Padding (bytes)']
                        fn = int(pkt['SFN'])
                        sfn = int(pkt['Sub-FN'])
                        # self.log_info(str(pkt))
                        cell_id = 0 #int(pkt['Cell Id'])
                        self.bsr_buffer.append((ts, fn, sfn))
                        if self.mac_buffer[cell_id*8+harq_id-1] != []:
                            pkt_alias = self.mac_buffer[cell_id*8+harq_id-1]
                            self.trans_delay.append((pkt_alias[1], pkt_alias[2], pkt_alias[3], self.__get_time_inter(pkt_alias[2]*10 + pkt_alias[3], fn *10 + sfn)))
                        self.mac_buffer[cell_id*8+harq_id-1] = (pkt_size,ts,fn,sfn)
                        if len(self.trans_delay) > 40:
                            del self.trans_delay[0]

                self._ana_delay4 += time.time() - before_ana_time
                self._ana_delay += time.time() - before_ana_time


            if self._debug:
                self.log_info('decode ' + str(self.__decode_delay))
                self.log_info('ana ' + str(self._ana_delay))
                self.log_info('ana1 ' + str(self._ana_delay1))
                self.log_info('ana2 ' + str(self._ana_delay2))
                self.log_info('ana21 ' + str(self._ana_delay21))
                self.log_info('ana211 ' + str(self._ana_delay211))
                self.log_info('ana212 ' + str(self._ana_delay212))
                self.log_info('ana22 ' + str(self._ana_delay22))
                self.log_info('ana221 ' + str(self._ana_delay221))
                self.log_info('ana222 ' + str(self._ana_delay222))
                self.log_info('ana223 ' + str(self._ana_delay223))
                self.log_info('ana224 ' + str(self._ana_delay224))
                # self.log_info('ana2241 ' + str(self._ana_delay2241))
                # self.log_info('ana2242 ' + str(self._ana_delay2242))
                # self.log_info('ana2243 ' + str(self._ana_delay2243))
                # self.log_info('ana2244 ' + str(self._ana_delay2244))
                self.log_info('ana3 ' + str(self._ana_delay3))
                self.log_info('ana4 ' + str(self._ana_delay4))
                self.log_info('cnt1 ' + str(self.cnt1))
                self.log_info('cnt2 ' + str(self.cnt2))
                self.log_info('cnt3 ' + str(self.cnt3))
                self.log_info('cnt4 ' + str(self.cnt4))
                self.log_info('log_cnt1 ' + str(self.log_cnt1))
                self.log_info('log_cnt2 ' + str(self.log_cnt2))
                self.log_info('log_cnt3 ' + str(self.log_cnt3))
                self.log_info('log_cnt4 ' + str(self.log_cnt4))
                self.log_info('bytes1 ' + str(self.bytes1))
                self.log_info('bytes2 ' + str(self.bytes2))
                self.log_info('bytes4 ' + str(self.bytes4))
                from writer import write
                write(",".join(["UL_LAT_BD", str(self.__decode_delay),str(self._ana_delay), str(self._ana_delay1),str(self._ana_delay2), str(self._ana_delay21), str(self._ana_delay211), str(self._ana_delay212), str(self._ana_delay22), str(self._ana_delay221), str(self._ana_delay222), str(self._ana_delay223), str(self._ana_delay224), str(self._ana_delay3), str(self._ana_delay4), str(self.cnt1), str(self.cnt2), str(self.cnt3), str(self.cnt4),str(self.log_cnt1), str(self.log_cnt2), str(self.log_cnt3), str(self.log_cnt4), str(self.bytes1),  str(self.bytes2),  str(self.bytes4)]) +"/n", action="direct")
