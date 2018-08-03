#!/usr/bin/python
# Filename: ul_mac_latency_analyzer.py
"""
ul_latency_breakdown_analyzer.py
An KPI analyzer to monitor mac layer waiting and processing latency

Author: Zhehui Zhang
"""

__all__ = ["UlMacLatencyAnalyzer"]

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from mobile_insight.analyzer import *
import time
import dis


class UlMacLatencyAnalyzer(Analyzer):
    """
    An KPI analyzer to monitor and manage uplink latency breakdown
    """
    def __init__(self):
        Analyzer.__init__(self)

        self.add_source_callback(self.__msg_callback)
        self.last_bytes = {} # LACI -> bytes <int> Last remaining bytes in MAC UL buffer
        self.buffer = {} # LCID -> [sys_time, packet_bytes] buffered mac ul packets
        self.ctrl_pkt_sfn = {} # LCID -> sys_fn*10 + sun_fn when last mac ul control packet comes
        self.cur_fn = -1 # Record current sys_fn*10+ sub_fn for mac ul buffer
        self.lat_stat = [] # Record ul waiting latency (ts, sys_time, pdu_size)
        self.queue_length = 0
        self.mapping = False
        self.bcast_dict = {}
        self.mac_buffer_dict = {}

        self._ana_delay = 0
        self._ana_delay1 = 0
        self._ana_delay2 = 0
        self._ana_delay3 = 0
        self._ana_delay4 = 0
        self._ul_pkt_num = 0
        self.__decode_delay = 0
        self._bytes = 0
        self._debug = False

        self.cnt = 0
        self.log_cnt = 0

        self.sample_rate = 0.2
        self.shift_l = 0  # shift in packet cnt
        self.shift_t = 0  # shift on timestamp in seconds
        self.sample_on_t = False

        self.mac_buf_sample_rate = self.sample_rate
        self.mac_buf_sample_rate_t = self.sample_rate

        self.init_time = None

        # dis.dis(self.__msg_callback)
        self.decode = True
        self.analyze = True
    def set_source(self, source):
        """
        Set the trace source. Enable the cellular signaling messages

        :param source: the trace source (collector).
        """
        Analyzer.set_source(self, source)

        # Phy-layer logs
        source.enable_log("LTE_MAC_UL_Buffer_Status_Internal")

    def set_sample_rate(self, rate):
        self.sample_rate = rate
        self.mac_buf_sample_rate = self.sample_rate
        self.mac_buf_sample_rate_t = self.sample_rate

    def enable_mapping(self):
        self.mapping = True

    def set_init_time(self, ts):
        self.init_time = ts

    def __del_lat_stat(self):
        """
        Delete one lat_buffer after it is matched with rlc packet
        :return:
        """
        del self.lat_stat[0]

    def set_decode(self,t):
        self.decode = t
    def set_analyze(self,t):
        self.analyze = t
    def __msg_callback(self, msg):

        if msg.type_id == "LTE_MAC_UL_Buffer_Status_Internal":

            # self.log_info("Received")
            before_decode_time = time.time()
            self.cnt += 1
            if (not self.sample_on_t and (self.cnt % (1 / self.mac_buf_sample_rate) == 0)) or \
                    (self.sample_on_t and self.init_time and (( \
                     before_decode_time - self.init_time)  % 1 < self.mac_buf_sample_rate_t)):
                self.log_cnt += 1
                if(self.decode == True):
                    log_item = msg.data.decode(True)
                else:
                    self.log_info("Decode Turned Off")
                    return  
                self.__decode_delay += time.time() - before_decode_time
                # if str(log_item['timestamp']).startswith('2018-03-09 21:45:53'):
                    # print log_item['timestamp'], self.buffer, self.last_bytes

                before_ana_time = time.time()
                if 'Subpackets' in log_item and len(log_item['Subpackets']) > 0:
                    pkt_version = log_item['Subpackets'][0]['Version']
                    for sample in log_item['Subpackets'][0]['Samples']:
                        before_ana_time1 = time.time()
                        sub_fn = int(sample['Sub FN'])
                        sys_fn = int(sample['Sys FN'])
                        sys_time = sys_fn*10 + sub_fn
                        if(not self.analyze):
                            self.log_info("analyze Turned Off")
                            return 
                        if sys_time < 10240:
                            if self.cur_fn > 0:
                                # reset historical data if time lag is bigger than 1ms
                        # Incorrect sys_fn and sub_fn are normally 1023 and 15
                        # print log_item['timestamp'], sys_time, self.cur_fn
                                lag = sys_time - self.cur_fn
                                if lag > 1 or -10239 < lag < 0:
                                    self.last_bytes = {}
                                    self.buffer = {}
                                    self.ctrl_pkt_sfn = {}
                            self.cur_fn = sys_time
                        elif self.cur_fn >= 0: # if invalid and inited, add current sfn
                            self.cur_fn = (self.cur_fn + 1)%10240
                        else:
                            continue

                        self._ana_delay1 += time.time() - before_ana_time1

                        for lcid in sample['LCIDs']:
                            before_ana_time2 = time.time()
                            idx = lcid['Ld Id']
                            if idx < 3:
                                continue
                            #FIXME: Are these initializations valid?
                            if pkt_version == 24:
                                new_bytes = lcid.get('New Compressed Bytes', 0)
                            else:
                                new_bytes = lcid.get('New bytes', 0)
                            ctrl_bytes = lcid.get('Ctrl bytes', 0)
                            total_bytes = new_bytes + ctrl_bytes # if 'Total Bytes' not in lcid else int(lcid['Total Bytes'])

                            self._ana_delay2 += time.time() - before_ana_time2
                            before_ana_time3 = time.time()

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

                            self._ana_delay3 += time.time() - before_ana_time3
                            before_ana_time4 = time.time()


                            if self.last_bytes[idx] > total_bytes:
                                # print log_item['timestamp'], self.cur_fn, self.last_bytes[idx]
                                sent_bytes = self.last_bytes[idx] - total_bytes
                                # print log_item['timestamp'], self.cur_fn, sent_bytes
                                # if str(log_item['timestamp']).startswith('2018-03-09 21:45:53'):
                                #     print log_item['timestamp'], self.buffer, self.last_bytes
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
                                        # print log_item['timestamp'], self.cur_fn, pkt[3], pkt_delay, wait_delay
                                        if self.mapping: # avoid storage overhead when uplink rlc analyzer is not enabled
                                            self.lat_stat.append((log_item['timestamp'], self.cur_fn, pkt[1], pkt_delay))
                                    else:
                                        pkt[1] -= sent_bytes
                                        sent_bytes = 0
                                    if pkt[1] == 0:
                                        pkt_delay = (self.cur_fn - pkt[0]) % 10240
                                        wait_delay = (self.cur_fn - pkt[2]) % 10240
                                        self.buffer[idx].pop(0)
                                        sent_bytes -= pkt[1]
                                        # print log_item['timestamp'], self.cur_fn, pkt[3], pkt_delay, wait_delay
                                        if self.mapping:  # avoid storage overhead when uplink rlc analyzer is not enabled
                                            self.lat_stat.append((log_item['timestamp'], self.cur_fn, pkt[1], pkt_delay))

                            self.last_bytes[idx] = total_bytes
                            self._ana_delay4 += time.time() - before_ana_time4

                        self.queue_length = sum(self.last_bytes.values())

                self._ana_delay += time.time() - before_ana_time

            if self._debug:
                self.log_info('decode ' + str(self.__decode_delay))
                self.log_info('cnt ' + str(self.cnt))
                self.log_info('log_cnt ' + str(self.log_cnt))
                self.log_info('ana ' + str(self._ana_delay))
                self.log_info('ana1 ' + str(self._ana_delay1))
                self.log_info('ana2 ' + str(self._ana_delay2))
                self.log_info('ana3 ' + str(self._ana_delay3))
                self.log_info('ana4 ' + str(self._ana_delay4))
                self.log_info('bytes ' + str(self._bytes))

