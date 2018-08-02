
def write(object, action="serialize",log_path = "/sdcard/mobileinsight/plugins/test_analyzer/vr_log.mi2log"):
    if(action =="direct"):
        with open(log_path, "a") as f:            
            f.write(object)         
    if(action == "serialize"):
        ostream = ""
        with open(log_path, "a") as f:            
            name = object["name"]
            if(name == "DL_LAT_BD"):
                ostream += "{},{},{},{},{},{}\n".format(object["name"], object["ts"],object["pkt_size"],object["mac_retx_time"],object["rlc_wait_time"],object["pdcp_reordering_time"])
            f.write(ostream)
 
