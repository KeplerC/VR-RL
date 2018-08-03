#!/usr/bin/python
# Filename: dl_latency_breakdown_analyzer.py
"""
ul_latency_breakdown_analyzer.py
An KPI analyzer to monitor and manage uplink latency breakdown

Author: Kaiyuan(Eric) Chen
"""

__all__ = ["DlLatBreakdownAnalyzer"]

#from kpi_analyzer import KpiAnalyzer
from writer import write
from mobile_insight.analyzer.analyzer import *


class DlLatBreakdownAnalyzer(Analyzer):
    """
    An KPI analyzer to monitor and manage uplink latency breakdown to 
    - wait latency
    - processing latency
    - transmission latency
    """
    
    def __init__(self):
        Analyzer.__init__(self)
        self.add_source_callback(self.__map_callback)

        self.header = 2 #number of entries to jump ahead
        self.config_to_pdcp = dict()#dict mapping from logical channel to pdcp packets
        self.config_to_rlc = dict() #dict mapping from logical channel to rlc packets
        self.latency_blocks = list() #list of unmapped blocks from PDSCH logs
        self.unmapped_pdcp_rlc = list()
        self.mapped_all = list() #(pdcp, rlc, mac transport block, mac delay)
        self.last_ordered_packet = dict()
        self.not_ordered_packet = dict()
        self.last_round_complete = dict()
        self.last_packet_processed = dict()
        self.updated_SN = dict()
        self.cell_id = dict()  # cell_name -> idx Keep index for each type of cell
        self.idx = 0 # current recorded cell idx
        self.failed_harq = [0] * 8 * 3 * 2
        self.mac_delays = list()
        self.kpi = list()
        self.discarded_packets_stat = {"pdcp":0,
                                    "mac":0,
                                    "rlc":0,
                                    "mapped_pdcp_rlc":0,
                                    "mapped_pdcp_rlc_mac":0,
                                    "latency_block":0
        }
        
    def set_source(self,source):
        """
        Set the trace source. Enable the LTE ESM messages.

        :param source: the trace source.
        :type source: trace collector
        """
        Analyzer.set_source(self,source)
        #enable LTE PDCP and RLC logs
        source.enable_log("LTE_PDCP_DL_Cipher_Data_PDU")
        source.enable_log("LTE_RLC_DL_AM_All_PDU")
        
        #enable LTE MAC logs 
        source.enable_log("LTE_PHY_PDSCH_Stat_Indication")

    def __sn_is_before(self, a_ts, (a_sys_fn, a_sub_fn), b_ts, (b_sys_fn, b_sub_fn), threshold = 0.4, diff = False):
        """
        Check if time a is before time b
        :param a_ts: timestamp of a
        :param (a_sys_fn
        :param a_sub_fn)
        :param b_ts: timestamp of b
        :param (b_sys_fn,
               b_sub_fn)
        """
        ts_inter = (a_ts - b_ts).total_seconds()
        if(diff and abs(ts_inter) < threshold):
            return False
        if ts_inter < -threshold:
            return True
        elif ts_inter > threshold:
            return False
        else:
            a = a_sys_fn * 10 + a_sub_fn
            b = b_sys_fn * 10 + b_sub_fn
            return a < b or (a > 9000 and b < 3000)
        
    def __map_callback(self, msg):
        
        #order packets by sequence number
        #allowdup: if duplicated sequence number is allowed
        def __order_by_SN(log_items, allowdup = True):            
            if allowdup:
                return sorted(log_items, key=lambda x:x["SN"])
            else:
                log_items = sorted(log_items, key=lambda x:x["SN"])
                if(len(log_items) < 4):
                    return log_items
                #removing repeated items
                #following code equivalent to:
                #log_items[:] = [log_items[i] for i in range(0, len(log_items)-1) if log_items[i]["SN"] != log_items[i+1]["SN"]]
                del_element = []
                for i in range(len(log_items) -1):
                    if(log_items[i]["SN"] == log_items[i+1]["SN"]):
                        del_element.append(i)
                log_items = [i for j, i in enumerate(log_items) if j not in del_element]
                return log_items

        #check if sequence number of a list is incremental
        def check_SN_is_incremental(l):
            if l == []:
                return True

            #in case of double indexing
            if len(l) >= 3 and [a["SN"] for a in l[1:]] == list(range(l[1]["SN"], l[-1]["SN"]+1)):
                return True

            #checking the sequence is a list increases only by 1
            if [a["SN"] for a in l] == list(range(l[0]["SN"], l[-1]["SN"]+1)):
                return True
            else:
                return False
                            
        cfg_idx = ""        
        if msg.type_id == "LTE_PDCP_DL_Cipher_Data_PDU":            
            message = msg.data.decode()
            write(str(message), action="direct")
            write("something /n", action = "direct")
            if(message == None):
                return
            log_item = message["Subpackets"][0]
            for pduitem in log_item["PDCPDL CIPH DATA"]:
                cfg_idx = pduitem["Cfg Idx"]
                ret = self.config_to_pdcp.setdefault(cfg_idx, [])
                #initialize corresponding index without harming existing index
                self.updated_SN.setdefault(cfg_idx, False)
                pdcp = dict()
                pdcp["timestamp"] = message["timestamp"]
                pdcp["PDU Size"] = pduitem["PDU Size"]# - pduitem["Logged Bytes"]
                pdcp["sys/sub_fn"] = (pduitem["Sys FN"], pduitem["Sub FN"])
                pdcp["SN"] = pduitem["SN"]
                #list of rlc packets matched by this pdcp packet
                pdcp["rlc"] = list() 
                #a counter to account for decomposed rlc packet
                pdcp["decomposed"] = 0
                #print("pdcp size", pdcp["PDU Size"])
                self.config_to_pdcp[cfg_idx].append(pdcp)
                #if the SN is not incremental, that means we have a handover/gap in the records
                if not check_SN_is_incremental(__order_by_SN(self.config_to_pdcp[cfg_idx])):
                    #print(__order_by_SN(self.config_to_pdcp[cfg_idx]))
                    #print("Triggered")
                    self.updated_SN[cfg_idx] = True
                self.discarded_packets_stat["pdcp"] += 1
                
        if msg.type_id == "LTE_RLC_DL_AM_All_PDU":
            #to jump the header records if needed
            if(self.header != 0):
                self.header -= 1
                return
            message = msg.data.decode()
            if(message == None):
                return 
            log_item = message["Subpackets"][0]

            #sometimes, the order of RLC is not guranteed
            #removing duplicated sequence numbersx
            size = 0
            for pduitem in __order_by_SN(log_item["RLCDL PDUs"], False):
                if(pduitem["Status"] !="PDU DATA"):
                    #opt out "PCU CTRL"
                    continue

                cfg_idx = pduitem["rb_cfg_idx"]
                
                #initialization of dictionary to prevent access value error
                self.last_packet_processed.setdefault(cfg_idx, -1)
                self.not_ordered_packet.setdefault(cfg_idx, [])
                self.config_to_rlc.setdefault(cfg_idx, [])
                self.updated_SN.setdefault(cfg_idx, False)
                self.last_round_complete.setdefault(cfg_idx, True)
                
                #there might be one missing packet that leads to an accumulation of errors
                if(len(self.not_ordered_packet[cfg_idx]) > 80):
                    self.last_ordered_packet[cfg_idx] = max(self.not_ordered_packet[cfg_idx][39]["SN"],self.last_ordered_packet[cfg_idx])                    
                    self.config_to_rlc[cfg_idx] += self.not_ordered_packet[cfg_idx][:40]
                    self.not_ordered_packet[cfg_idx] = self.not_ordered_packet[cfg_idx][40:]
                    if(self.config_to_rlc[cfg_idx][-1]["FI"][-1] == "0"):
                        self.last_round_complete[cfg_idx] = True
                    else:
                        self.last_round_complete[cfg_idx] = False

                if(self.updated_SN[cfg_idx]):
                    #the last system time of pdcp, use it to track rlc packets
                    std_sys = self.config_to_pdcp[cfg_idx][-1]["sys/sub_fn"][0]
                    #the last pdcp's SN, use it to track other pdcp packets 
                    std_sn = self.config_to_pdcp[cfg_idx][-1]["SN"]

                    #pdcp/rlc before handover
                    rlc_pre = []
                    for i in range(len(self.config_to_pdcp[cfg_idx]) -1,-1, -1):
                        #comparing by back-counting elements
                        if self.config_to_pdcp[cfg_idx][i]["SN"] != std_sn - (len(self.config_to_pdcp[cfg_idx]) - i - 1):
                            self.config_to_pdcp[cfg_idx].remove(self.config_to_pdcp[cfg_idx][i])

                    #use interval of pdcp to get a range of correct rlc time
                    mi = min([i["sys/sub_fn"][0] for i in self.config_to_pdcp[cfg_idx]])
                    ma = max([i["sys/sub_fn"][0] for i in self.config_to_pdcp[cfg_idx]])
                    #a modifiable metric to rule out rlc
                    def metric(i):
                        return i["sys/sub_fn"][0] < mi or i["sys/sub_fn"][0] > ma
                    for i in self.config_to_rlc[cfg_idx][:]:
                        if(metric(i)):
                            self.config_to_rlc[cfg_idx].remove(i)
                    for i in self.not_ordered_packet[cfg_idx][:]:
                        if(metric(i)):
                            rlc_pre.append(i)
                            self.not_ordered_packet[cfg_idx].remove(i)
                    #self.config_to_rlc[cfg_idx] += rlc_pre
                    self.config_to_rlc[cfg_idx] = __order_by_SN(self.config_to_rlc[cfg_idx])
                    #determine last ordered packet
                    #if there is no correct rlc packets, then simply reset it
                    if self.config_to_rlc[cfg_idx]:
                        self.last_ordered_packet[cfg_idx] = self.config_to_rlc[cfg_idx][-1]["SN"]
                    elif self.not_ordered_packet[cfg_idx]:
                        self.last_ordered_packet[cfg_idx] = self.not_ordered_packet[cfg_idx][0]["SN"] - 1
                    else:
                        self.last_ordered_packet.pop(cfg_idx, None)
                    self.updated_SN[cfg_idx] = False

                    
                d = dict()
                d["timestamp"] = message["timestamp"]
                d["PDU Size"] = pduitem["pdu_bytes"] - pduitem["logged_bytes"]
                d["block_size"] = int(pduitem["pdu_bytes"])
                d["sys/sub_fn"] = (pduitem["sys_fn"], pduitem["sub_fn"])
                d["SN"] = pduitem["SN"]
                d["FI"] = pduitem["FI"]
                size += d["PDU Size"]

                #TODO: delete me, the following code only works for VR_example since it has a jump in time
                '''
                if(d["SN"] == 497):
                    d["PDU Size"] += 125 
                '''

                
                #to spot incomplete packets(e.g. previous 01 and current 00)
                #then thow previous one away
                self.last_ordered_packet.setdefault(cfg_idx, d["SN"] -1)

                #print("last ordered:", self.last_ordered_packet[cfg_idx])
                #print("current:", d["SN"])
                    
                #if SN larger, that means some packets have not arrived
                if(d["SN"] > self.last_ordered_packet[cfg_idx] + 1):
                    self.not_ordered_packet[cfg_idx].append(d)
                elif (d["SN"] < self.last_ordered_packet[cfg_idx] + 1):
                    #if SN is 0 and last one is 0(just is case we have two SN=0 packet          
                    if(d["SN"] == 0 and self.last_ordered_packet[cfg_idx] != 0):
                        self.not_ordered_packet[cfg_idx].append(d)
                        self.last_ordered_packet[cfg_idx] = 0
                    elif(self.not_ordered_packet[cfg_idx] and self.not_ordered_packet[cfg_idx][0]["SN"] == 0):
                        self.config_to_rlc[cfg_idx] += self.not_ordered_packet[cfg_idx]
                        self.not_ordered_packet[cfg_idx] = [d]
                        #self.not_ordered_packet[cfg_idx].append(d)
                    else:
                        #resend this packet with a complete version
                        if(d["SN"] == self.last_ordered_packet[cfg_idx]\
                           and self.config_to_rlc[cfg_idx] \
                           and self.config_to_rlc[cfg_idx][-1]["FI"][-1] == '1'\
                           and d["FI"][-1] == "0"):
                            del self.config_to_rlc[cfg_idx][-1]
                            self.config_to_rlc[cfg_idx].append(d)
                            #Not Common for out of window packets
                        continue
                else:
                    assert(d["SN"] == self.last_ordered_packet[cfg_idx] + 1)
                    if(self.last_round_complete[cfg_idx]):
                        self.config_to_rlc[cfg_idx].append(d)
                        self.last_ordered_packet[cfg_idx] = self.config_to_rlc[cfg_idx][-1]["SN"]
                    else:
                        self.not_ordered_packet[cfg_idx].append(d)

                #print(self.not_ordered_packet[cfg_idx])
                #print(self.config_to_rlc[cfg_idx])
                #print([i["SN"] for i in self.not_ordered_packet[cfg_idx]])
                
                if (pduitem["FI"][-1] == "0"):
                    self.last_round_complete[cfg_idx] = True
                else:
                    self.last_round_complete[cfg_idx] = False
                    continue
                    
                if(check_SN_is_incremental([{"SN":self.last_ordered_packet[cfg_idx]}]+ __order_by_SN(self.not_ordered_packet[cfg_idx]))):
                    self.config_to_rlc[cfg_idx] += self.not_ordered_packet[cfg_idx]
                    self.last_ordered_packet[cfg_idx] = self.config_to_rlc[cfg_idx][-1]["SN"]                    
                    self.not_ordered_packet[cfg_idx] = []
                    self.config_to_rlc[cfg_idx] = __order_by_SN(self.config_to_rlc[cfg_idx])
                else:
                    self.last_round_complete[cfg_idx] = False
                    continue
                
        if(msg.type_id == "LTE_PHY_PDSCH_Stat_Indication"):
            log_item = msg.data.decode()
            if(log_item == None):
                return
            timestamp = log_item['timestamp']
            for item in log_item["Records"]:
                cell_id_str = item['Serving Cell Index']
                if cell_id_str not in self.cell_id:
                    self.cell_id[cell_id_str] = self.idx
                    cell_idx = self.idx
                    self.idx += 1
                else:
                    cell_idx = self.cell_id[cell_id_str]
                sn = int(item['Frame Num'])
                sfn = int(item['Subframe Num'])
                sn_sfn = sn * 10 + sfn
                for blocks in item['Transport Blocks']:
                    harq_id = int(blocks['HARQ ID'])
                    tb_idx = int(blocks['TB Index'])
                    is_retx = True if blocks['Did Recombining'][-2:] == "es" else False
                    crc_check = True if blocks['CRC Result'][-2:] == "ss" else False
                    tb_size = int(blocks['TB Size'])
                    rv_value = int(blocks['RV'])
                    id = harq_id + cell_idx * 8 + tb_idx * 24
                    retx = False
                    #note: following codes are adapted from Mac analyzer
                    if not crc_check:  # add retx instance or add retx time for existing instance
                        cur_fail = [timestamp, cell_idx, harq_id, tb_idx, tb_size, False, 0, False, sn_sfn]
                        if self.failed_harq[id] != 0:
                            if rv_value > 0:
                                self.failed_harq[id][6] += 1
                            else:
                                self.failed_harq[id][-2] = True
                                delay = sn_sfn - self.failed_harq[id][-1]
                                d = {}
                                d['block_size'] = self.failed_harq[id][4]                                        
                                d['timestamp'] = timestamp
                                d["sys/sub_fn"] = (sn, sfn)
                                d['delay'] = delay
                                #RLC
                                self.latency_blocks.append(d)
                                retx = True
                        elif rv_value == 0:
                            self.failed_harq[id] = cur_fail
                    else:
                        if self.failed_harq[id] != 0:
                            if rv_value > 0 or is_retx:
                                self.failed_harq[id][6] += 1
                                self.failed_harq[id][-4] = True
                                delay = sn_sfn - self.failed_harq[id][-1]
                                d = {}
                                d['block_size'] = self.failed_harq[id][4]             
                                d['timestamp'] = timestamp
                                d["sys/sub_fn"] = (sn, sfn)
                                d['delay'] = delay
                                retx = True
                                #MAC retx
                                self.latency_blocks.append(d)
                            else:
                                self.failed_harq[id][-2] = True
                                delay = sn_sfn - self.failed_harq[id][-1]
                                d = {}
                                d['block_size'] = self.failed_harq[id][4]                                  
                                d['timestamp'] = timestamp
                                d["sys/sub_fn"] = (sn, sfn)
                                d['delay'] = delay
                                retx = True
                                #RLC retx
                                self.latency_blocks.append(d)
                            self.failed_harq[id] = 0
                    #retransmission does not happen, delay is 0
                    if not retx:
                        d = {}
                        d['block_size'] = tb_size         
                        d['timestamp'] = timestamp
                        d["sys/sub_fn"] = (sn, sfn)
                        d['delay'] = 0
                        self.latency_blocks.append(d)

        if not self.last_round_complete.setdefault(cfg_idx, True):
            return

        #mapping from pdcp to rlc
        self.config_to_rlc.setdefault(cfg_idx, [])
        self.config_to_pdcp.setdefault(cfg_idx, [])
        
        while self.config_to_rlc[cfg_idx] and self.config_to_pdcp[cfg_idx]:
            #deleting out of phase packets 
            threshold = 0.4
            while self.config_to_rlc[cfg_idx] and self.config_to_pdcp[cfg_idx] and self.__sn_is_before(self.config_to_rlc[cfg_idx][0]["timestamp"],self.config_to_rlc[cfg_idx][0]["sys/sub_fn"], self.config_to_pdcp[cfg_idx][0]["timestamp"], self.config_to_pdcp[cfg_idx][0]["sys/sub_fn"], threshold = threshold, diff = True):
                #print("deleted", self.config_to_rlc[cfg_idx][0]["SN"], self.config_to_rlc[cfg_idx][0]["PDU Size"] )
                del self.config_to_rlc[cfg_idx][0]
                
            while self.config_to_rlc[cfg_idx] and self.config_to_pdcp[cfg_idx] and self.__sn_is_before(self.config_to_pdcp[cfg_idx][0]["timestamp"],self.config_to_pdcp[cfg_idx][0]["sys/sub_fn"], self.config_to_rlc[cfg_idx][0]["timestamp"], self.config_to_rlc[cfg_idx][0]["sys/sub_fn"], threshold= threshold, diff = True):
                #raw_input("Warning, deleted pdcp")
                self.discarded_packets_stat["rlc"] +=1
                del self.config_to_pdcp[cfg_idx][0]
            
                
            while self.config_to_rlc[cfg_idx] and self.config_to_pdcp[cfg_idx]:
                rlc = self.config_to_rlc[cfg_idx]
                pdcp = self.config_to_pdcp[cfg_idx]
                #print("{}:{}:{}".format("pdcp", pdcp[0]["PDU Size"], str(pdcp[0]["SN"])))
                #print("{}:{}:{}".format("rlc", rlc[0]["PDU Size"],str(rlc[0]["SN"])))
                #note: following comment is essential for debugging
                #print(pdcp[0]["PDU Size"] - rlc[0]["PDU Size"])
            
                if(rlc[0]["PDU Size"] == pdcp[0]["PDU Size"]):
                    #perfectly matched
                    pdcp[0]["rlc"].append(rlc[0])
                    self.unmapped_pdcp_rlc.append((rlc[0], pdcp[0]))
                    #print("Perfectly Matched")
                    #debug_print(self.unmapped_pdcp_rlc[-1])
                    del self.config_to_rlc[cfg_idx][0]
                    del self.config_to_pdcp[cfg_idx][0]

                elif(rlc[0]["PDU Size"] <  pdcp[0]["PDU Size"]):
                    #pdcp is decomposed
                    pdcp[0]["rlc"].append(rlc[0])
                    self.config_to_pdcp[cfg_idx][0]["PDU Size"] -= rlc[0]["PDU Size"]
                    del self.config_to_rlc[cfg_idx][0]                
                else:
                    #rlc is decomposed
                    self.config_to_rlc[cfg_idx][0]["PDU Size"] -= pdcp[0]["PDU Size"]
                    pdcp[0]["decomposed"] += 1
                    pdcp[0]["rlc"].append(rlc[0])
                    self.unmapped_pdcp_rlc.append((rlc[0],pdcp[0]))
                    del self.config_to_pdcp[cfg_idx][0]

        #mapping mapped pdcp-rlc tuples to latency blocks
        while self.unmapped_pdcp_rlc and self.latency_blocks:
            while self.unmapped_pdcp_rlc and self.latency_blocks and self.__sn_is_before(self.unmapped_pdcp_rlc[0][1]["rlc"][0]["timestamp"],self.unmapped_pdcp_rlc[0][1]["rlc"][0]["sys/sub_fn"], self.latency_blocks[0]["timestamp"], self.latency_blocks[0]["sys/sub_fn"]):
                self.discarded_packets_stat["mapped_pdcp_rlc"] += 1
                #print("unmapped")
                self.mapped_all.append((self.unmapped_pdcp_rlc[0][1], self.unmapped_pdcp_rlc[0][0], {"delay": 0}))
                del self.unmapped_pdcp_rlc[0]
            while self.unmapped_pdcp_rlc and self.latency_blocks and self.__sn_is_before(self.latency_blocks[0]["timestamp"], self.latency_blocks[0]["sys/sub_fn"], self.unmapped_pdcp_rlc[0][1]["rlc"][0]["timestamp"],self.unmapped_pdcp_rlc[0][1]["rlc"][0]["sys/sub_fn"]):
                #print("deleted mac")
                #print(self.latency_blocks[0])
                self.discarded_packets_stat["latency_block"] += 1
                del self.latency_blocks[0]
            if(self.latency_blocks and self.unmapped_pdcp_rlc):
                self.mapped_all.append((self.unmapped_pdcp_rlc[0][1], self.unmapped_pdcp_rlc[0][0],  self.latency_blocks[0]))
                #print(self.mapped_all[-1])
                if(self.unmapped_pdcp_rlc[0][1]["decomposed"] > 0):
                    self.unmapped_pdcp_rlc[0][1]["decomposed"] -= 1
                    #print("d_mapped")
                else:
                    #print("mapped")
                    del self.latency_blocks[0]
                del self.unmapped_pdcp_rlc[0]
                
        
        # print("unmapped pdcp rlc tuple : " + str(len(self.unmapped_pdcp_rlc)))
        # print("pdcp rlc mac tuple:   " + str(len(self.unmapped_pdcp_rlc)))
        # print("latency block number: " + str(len(self.latency_blocks)))
        # print("ultimate mapping:     " + str(len(self.mapped_all)))

        #upload everything
        while(self.mapped_all):
            pdcp = self.mapped_all[0][0]
            rlc = self.mapped_all[0][1]
            mac = self.mapped_all[0][2]

            #helper function for getting time interval
            def get_time_inter((a_sys_fn, a_sub_fn), (b_sys_fn, b_sub_fn)):
                a = a_sys_fn * 10 + a_sub_fn
                b = b_sys_fn * 10 + b_sub_fn
                inter = abs(a-b)
                if inter > 10000:
                    inter = abs(inter - 10240)
                return inter
            def get_packet_size(pdcp):
                if(len(pdcp["rlc"]) == 1):
                    return pdcp["PDU Size"]
                else:
                    sum = 0
                    for i in pdcp["rlc"][:-1]:
                        sum += i["PDU Size"]
                    return sum + pdcp["PDU Size"]
                                   
            kpi = dict()
            kpi["name"] = "DL_LAT_BD"
            kpi["ts"] = pdcp["timestamp"]
            kpi["pkt_size"] = get_packet_size(pdcp)
            kpi["mac_retx_time"] = mac["delay"]
            
            if(pdcp["rlc"] == []): #only one rlc, no multiple rlc transmission time
                kpi["rlc_wait_time"] = 0
            else:
                kpi["rlc_wait_time"] = get_time_inter(rlc["sys/sub_fn"], pdcp["rlc"][0]["sys/sub_fn"])#last pdu receipt time - first pdu receipt time
            kpi["pdcp_reordering_time"] = get_time_inter(rlc["sys/sub_fn"], pdcp["sys/sub_fn"])#pdcp layer time - last pdu receipt time
            #print(kpi)
            #if(kpi["pdcp_reordering_time"] > 3000 or kpi["rlc_wait_time"] > 3000):
                #debug_print(pdcp)
                #debug_print(kpi)                
                #raw_input("what")
            #self.kpi.append(kpi)
            #self.kpi.append(kpi)
        
            #self.broadcast_info('DL_LAT_BREAKDOWN', kpi)
            #self.log_debug('DL_LAT_BREAKDOWN: ' + str(kpi))
            #self.store_kpi("KPI_Integrity_DL_LATENCY_BREAKDOWN", kpi, str(pdcp["timestamp"]))
            #self.upload_kpi("KPI.Integrity.UL_LAT_BREAKDOWN", kpi)
            write(kpi)
            del self.mapped_all[0]
            
from pprint import pprint
def debug_print(k):
    pprint(k, width = 3)

if __name__=="__main__":
    from mobile_insight.monitor import OfflineReplayer
    from mobile_insight.analyzer import MsgLogger
    #from ul_lat_breakdown_analyzer import UlLatBreakdownAnalyzer
    #from lte_handover_disruption_analyzer import LteHandoverDisruptionAnalyzer
    #from ul_mac_latency_analyzer import  UlMacLatencyAnalyzer
    #from dl_lat_breakdown_analyzer import DlLatBreakdownAnalyzer
    import inspect

    # Initialize a 3G/4G monitor
    src = OfflineReplayer()
    #src.set_input_path("./5.qmdl")
    #src.set_input_path("./att.mi2log")
    #src.set_input_path("./q.qmdl")
    src.set_input_path("./VR_sample_log.qmdl")
    logger = MsgLogger()
    logger.set_decode_format(MsgLogger.JSON)
    logger.set_dump_type(MsgLogger.FILE_ONLY)
    logger.save_decoded_msg_as("./test.txt")
    logger.set_source(src)

    alyzer = DlLatBreakdownAnalyzer()
    alyzer.set_source(src)
    src.run()
    #print(alyzer.unmapped_pdcp_rl)
    #debug_print(alyzer.mapped_pdcp_rlc)
    #debug_print(alyzer.config_to_pdcp)
    #debug_print(alyzer.config_to_rlc)
    #debug_print(alyzer.mapped_all)
    debug_print(alyzer.kpi)
    #print(len(alyzer.unmapped_pdcp_rlc))    
    print(alyzer.discarded_packets_stat)
    #debug_print(alyzer.kpi)

    print(len(alyzer.unmapped_pdcp_rlc))
    print(len(alyzer.kpi))
    #print(len(alyzer.config_to_pdcp[3]))
