#!/usr/bin/python


# send packets and create traffic
def send(pkt_size, ulPktSize = 500, num_pkt = 100, interval = 10000, heart_beat_interval = 10000):
    l  = []

    '''<Server IP> <Server Port>   <TotalPkt>  <PktSize> <ulPktSize> <Interval> <Heart beat interval>",
    '''
    #p = subprocess.Popen('./Program 45.63.11.171 9999 {} 100 {} 1 1'.format(num_pkt, pkt_size), shell =True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    TotalPkt = pkt_size // 11579 + 1
    pkt_size = pkt_size if pkt_size < 11579 else 11579 # because of max limit buffer

    args = ' '.join([str(x) for x in [TotalPkt, pkt_size, ulPktSize, interval, heart_beat_interval]])
    import subprocess
    p = subprocess.Popen('./Program 127.0.0.1 9999 ' + args, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout.readlines():
        l.append(line)
    retval = p.wait()
    return l

# configuration class
# given a
class Config():
    def __init__(self):
        self.d = {
            # prediction based
            "prediction_navigation" : 0, # 0 to 30, how many prediction used
            "prediction_impulse" : 0, #0 to 30, how many prediction used

            # IMR
            "wide_angle" : 90, # 90 + 30 * n 
            "partial_cube_quality": 0, # 0 low, 1 medium 2 high
            "dual_view": 0, # 0 off 1 on 
            
            # compression
            "compression": 0, # 0 off 1 on

            # cache
            "checkpoint" : 0, # 0 off 1 on
            "compression": 0, # 0 off 1 on

            # quality
            "level_of_detail": 0,  # 0 low, 1 medium 2 high
            "rendering_quality": 0, # 0 low, 1 medium 2 high
            "rendered_quality": 0 # 0 low, 1 medium 2 high
        }

        self.frame_size_mul = 1
        self.frame_size_bias = 0

        self.lat_mul = 1
        self.lat_bias = 0

    # process frame size and lat based on current config
    # @ ret none
    
    def proc(self):
        pass
    
# a packet that 
class Packet():
    def __init__(self):
        self.frame_size = 40000 # 40k for single frame
        self.num_frame = 1

    # send the packet with designed size / #
    # @ret : network delay
    def send(self):
        l = send(self.frame_size * self.num_frame)
        return _parse(l)

    # parse the stdout of vr application
    # return the delay
    # TODO
    def _parse(pkt):
        return 0
        
