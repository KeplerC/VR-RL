#!/usr/bin/python
# Filename: pkt_loss_analyzer.py

from mobile_insight.analyzer.analyzer import *
import datetime
from heapq import *


__all__ = ["RlcUlRetxAnalyzer"]
global debug
debug = True

class RadioBearerEntity(Analyzer):
    def __init__(self, num):
        self.idx = num
        self.ordered_idx = -1

        self.pdcp_buffer = []  # [[sequency #, frame #, sub frame #, size, remianing size]]
        self.ordered_rlc_buffer = []  # a heap of [timestamp, sequence #, frame #, sub frame #, size]
        self.disordered_rlc_buffer = []  # a heap of [timestamp, sequence #, frame #, sub frame #, size]
        self.mapped_pdcp_rlc = []  # [(pdcp packet, rlc packet)] -> (ts, rlc_sn, rlc_sfn, pdcp_size, trans_lat)
        self.last_submitted_idx = -1

    def update_ordered_idx(self, num):
        # if self.ordered_idx != num:
        self.last_submitted_idx = self.ordered_idx
        self.ordered_idx = num
        if self.last_submitted_idx > self.ordered_idx and self.last_submitted_idx < 700 and self.ordered_idx < 100:
            self.last_submitted_idx = -1

    def sn_is_before(self, sn_a, sn_b):
        if sn_a < sn_b and sn_b -sn_a < 600:
            return True
        elif (sn_b < sn_a and sn_b < 200 and sn_a > 700):
            return True
        else:
            return False

    def recv_rlc_data(self, pdu, timestamp):
        global debug
        if 'LSF' in pdu and pdu['LSF'] == 0:
            return

        sys_time = pdu['sys_fn'] * 10 + pdu['sub_fn']
        sn = pdu['SN']
        hdr_len = int(pdu['logged_bytes'])  # rlc_pdu_size = pdcp_pdu_size + rlc_hdr_len
        sdu_size = int(pdu['pdu_bytes']) - hdr_len
        # if 58.60 <= float(str(timestamp)[-9:-4]) <= 58.70 and sn == 881:
        #     print pdu
        # if pdu['Status'] != 'PDU DATA':
        #     print pdu['Status']

        # if 52.80 <= float(str(timestamp)[-9:-4]) <= 52.88 and sn == 547:
        #     print 'update'
        #     print 'disordered:', sorted(self.disordered_rlc_buffer)
        #     print 'ordered:', sorted(self.ordered_rlc_buffer)
        #     print 'ordered_idx:', self.ordered_idx
        #     print 'last_ordered_idx:', self.last_submitted_idx

        if self.sn_is_before(sn, self.ordered_idx) and (self.sn_is_before(self.last_submitted_idx, sn) or sn == self.last_submitted_idx):
            if sn not in [i[0] for i in self.ordered_rlc_buffer]:
                heappush(self.ordered_rlc_buffer, [sn, timestamp, sys_time, sdu_size])
            else:
                pass
                # print '[Warning]: Duplicate ordered pacekts', timestamp, 'SN:', sn
                # for item in self.ordered_rlc_buffer:
                #     if item[0] == sn:
                #         print item, [sn, timestamp, sys_time, sdu_size]
                #         print 'disordered:', sorted(self.disordered_rlc_buffer)
                #         print 'ordered:', sorted(self.ordered_rlc_buffer)
                # debug = False
        elif self.sn_is_before(sn, self.last_submitted_idx):
            pass
            # print '[Warning]: Duplicate rx pacekts', timestamp, 'SN:', sn
            # print 'ordered_idx:', self.ordered_idx
            # print 'last_ordered_idx:', self.last_submitted_idx
        else:
            if sn not in [i[0] for i in self.disordered_rlc_buffer]:
                heappush(self.disordered_rlc_buffer, [sn, timestamp, sys_time, sdu_size])
            else:
                pass
                # print '[Warning]: Duplicate disordered pacekts', timestamp, 'SN:', sn
                # for item in self.disordered_rlc_buffer:
                #     if item[0] == sn:
                #         print item
                #         print 'disordered:', sorted(self.disordered_rlc_buffer)
                #         print 'ordered:', sorted(self.ordered_rlc_buffer)

        # print 'Ordered', self.ordered_rlc_buffer
        # print 'Disordered', self.disordered_rlc_buffer

    def submit_rlc_buffer(self, timestamp):
        global debug
        # check if all the ordered pkts are complete

        # put disordered packets into ordered ones.
        head_buf = []

        # if 1.70 <= float(str(timestamp)[-9:-4]) <= 1.78:
        #     print 'Begin'
        #     print 'disordered:', sorted(self.disordered_rlc_buffer)
        #     print 'ordered:', sorted(self.ordered_rlc_buffer)
        #     print 'ordered_idx:', self.ordered_idx
        #     print 'last_ordered_idx:', self.last_submitted_idx

        for i in range(len(self.disordered_rlc_buffer)):
            min_sn = min(self.disordered_rlc_buffer)[0]
            if self.sn_is_before(min_sn, self.ordered_idx):
                if min_sn not in [i[0] for i in self.ordered_rlc_buffer]:
                    heappush(self.ordered_rlc_buffer, min(self.disordered_rlc_buffer))
                else:
                    # for item in self.ordered_rlc_buffer:
                    #     if item[0] == min_sn:
                    #         print item
                    #         print 'disordered:', sorted(self.disordered_rlc_buffer)
                    #         print 'ordered:', sorted(self.ordered_rlc_buffer)
                    pass
                    # print '[Warning]: Duplicate ordered pacekts', timestamp, 'SN:', min_sn
                    # debug = False
                heappop(self.disordered_rlc_buffer)
            else:
                head_buf.append(heappop(self.disordered_rlc_buffer))
        for head_item in head_buf:
            heappush(self.disordered_rlc_buffer, head_item)
        list = [heappop(self.ordered_rlc_buffer)[0] for i in range(len(self.ordered_rlc_buffer))]
        if len(list) == 0:
            return
        elif len(list) == 1:
            # check if the ordered pdu is the same as the vr(r)
            if list[0] != self.ordered_idx - 1:
                # pass
                self.log_info(''.join((map(str, ['[Error] RLC packet gap ', timestamp, 'Expected idx :', self.ordered_idx, '; Real idx :', list[0]]))))
                # print 'disordered:', sorted(self.disordered_rlc_buffer)
                # print 'ordered:', sorted(self.ordered_rlc_buffer)
                # print list, self.last_submitted_idx, self.ordered_idx
                # debug = False
            else:
                # submit the pdu to pdcp layer
                self.ordered_rlc_buffer = []
        elif (list[-1] - list[0]) == len(list) and list[-1] > list[0]:
            # submit the pdu to pdcp layer
            self.ordered_rlc_buffer = []
        else:
            for idx in range(len(list)-1):
                if list[idx+1] - list[idx] != 1:
                    gap = list[idx+1] - list[idx]
                    if gap + len(list) != 1025:
                        self.log_info(''.join((map(str, ['[Error] RLC packet gap ', timestamp, ' Expected idx :',
                                                         list[idx+1], '; Gap :', list[idx+1] - list[idx]]))))
                        # print 'disordered:', sorted(self.disordered_rlc_buffer)
                        # print 'ordered:', sorted(self.ordered_rlc_buffer)
                        # print list, self.last_submitted_idx, self.ordered_idx
                        # debug = False
        # submit the pdu to pdcp layer
        self.ordered_rlc_buffer = []

        # if 52.80 <= float(str(timestamp)[-9:-4]) <= 52.88:
        #     print 'End'
        #     print 'disordered:', sorted(self.disordered_rlc_buffer)
        #     print 'ordered:', sorted(self.ordered_rlc_buffer)

class RlcUlRetxAnalyzer(Analyzer):
    def __init__(self):
        Analyzer.__init__(self)
        self.add_source_callback(self.__msg_callback)
        self.bearer_entity = {}

    def set_source(self, source):
        Analyzer.set_source(self, source)
        source.enable_log("LTE_RLC_DL_AM_All_PDU")

    def __msg_callback(self, msg):
        global debug

        if debug:
            if msg.type_id == "LTE_RLC_DL_AM_All_PDU":
                self.__msg_rlc_dl_callback(msg)

    def __msg_rlc_dl_callback(self, msg):
        # if self.flag:
        # 	return
        log_item = msg.data.decode()
        subpkt = log_item['Subpackets'][0]
        cfg_idx = subpkt['RB Cfg Idx']

        timestamp = log_item['timestamp']

        if cfg_idx not in self.bearer_entity:
            self.bearer_entity[cfg_idx] = RadioBearerEntity(cfg_idx)

        for pdu in subpkt['RLCDL PDUs']:
            if pdu['PDU TYPE'] == 'RLCDL CTRL' and 'RLC CTRL NACK' in pdu:
                self.log_info('missing'+str(log_item))
                print log_item
