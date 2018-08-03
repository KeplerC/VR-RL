#!/usr/bin/python

# send packets and create traffic
def send(pkt_size, ulPktSize = 500, num_pkt = 100, interval = 10000, heart_beat_interval = 10000):
    l  = []
    
    '''
	<Server IP> <Server Port>   <TotalPkt>  <PktSize> <ulPktSize> <Interval> <Heart beat interval>",
    '''

    #p = subprocess.Popen('./Program 45.63.11.171 9999 {} 100 {} 1 1'.format(num_pkt, pkt_size), shell =True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    TotalPkt = pkt_size // 10000 + 1
    pkt_size = pkt_size if pkt_size < 10000 else 10000 # because of max limit buffer

    args = ' '.join([str(x) for x in [TotalPkt, pkt_size, ulPktSize, interval, heart_beat_interval]])
    import subprocess
    #print('./Program 127.0.0.1 9999 ' + args)
    p = subprocess.Popen('/home/chenkaiyuan_g_ucla_edu/VR-RL/VR_REIN/gym_foo/envs/Program 127.0.0.1 9999 ' + args, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    retval = p.wait()
    for line in p.stdout.readlines():
        l.append(line)
    #retval = p.wait()
    #print(l)
    return process_output(l)


def process_output(l):
    '''	
    given output of ./Program
    @ret delay
    '''
    if not l:
        return 0
    
    l = [i.decode('utf-8').split(",") for i in l]
    '''
    Take round trip time to be packet first sent and last received
    '''	
    first_send = min(l, key=lambda x: x[1])
    last_recv = max(l, key=lambda x: x[1])
	
	
    '''
    As we can measure proccess and transmission delay, 
    I will use the summation of both of them
    '''
    proc_delay = max(int(first_send[2]), int(last_recv[2]))
    trans_delay = int(last_recv[1]) - int(first_send[1])
    return proc_delay + trans_delay
