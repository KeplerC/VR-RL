'''
A gym environment for 
* MI components 
* Reward for each action

'''

import gym
from gym import error, spaces, utils
from gym.utils import seeding
import numpy as np
from . import vr 
import copy
import pandas as pd
import os

num_actions = 5
step_size = 5

class FooEnv(gym.Env):
  metadata = {'render.modes': ['human']}
  
  def __init__(self):
    self.action_space = spaces.Discrete(5)
    self.config = {
      "IBR_ANG": 0, #real frame + 90
      "PRED_FRAM": 100
    }
    self.bound_action = []

  def step(self, action):
    '''
    observation, reward, done, info = env.step(action)
    @para
    action from action_space 

    @ret:
    observation: MI outputs
    reward: latency reduced + latency masked 
    done: given characteristic of this problem, we don't need to reset it 
    info: all the configurations 
    '''
    
    assert self.action_space.contains(action)
    
    #not done by default 
    done = False
    
    #perform action
    self._perform_action(action)
    self._check_in_bound()
    info = copy.deepcopy(self.config)
    info["bound"] = self.bound_action

    #calculate reward
    reward = self._get_traffic_lat_by_config()
    if action == 0:
      reward -= 100
    print(reward)
    
    #get a new set of observation
    #by calling MI
    observation = self._get_MI_obser()
    
    return observation, reward, done, info

  def reset(self):
    '''
    reset environment to initial state 
      '''
    self.config = {
      "IBR_ANG": 0,
      "PRED_FRAM": 100
    }
    return self._get_MI_obser()

  def _get_MI_obser(self, log_dir = "./log/", all_files = False):
    '''
    Read in MI logs 
    @ret: an observation np matrix 
      '''
    num_analyzer = 2
    num_feat= 28
    bin_interval = 20
    num_time_slots = 128
    
    '''
    take out all files except the last one(which MI may still writing to it)
    '''
    if all_files:
      all_f = [f for f in os.listdir(log_dir) if f.startswith("1")]
    else:
      from random import randint
      all_f = [[f for f in os.listdir(log_dir) if f.startswith("1")][randint(1, 30)]]

    fileframes = []
    for f in all_f:
      fileframes.append(pd.read_csv(log_dir + f, names=list('0123456789012345678901234567')))
    df = pd.concat(fileframes, axis = 0)

    '''
    Cleaning all the data
    * changing analyzer's type to categorical data
    * changing read_csv output from string to double
    * round all the times into individual bins 
    * align analyzers' output of different sizes
        - from Nan to zero-paddings
    '''
    def roundTime(dt, roundTo):
      roundTo = roundTo * 1000
      dt = dt.microsecond // roundTo
      return dt

    output = []
    i = 0
    for analyzer in pd.unique(df['0']):
      temp_mat = df.loc[df['0'] == analyzer]
      temp_mat['0'] = np.ones((temp_mat.shape[0], 1), dtype=np.int) * i
      temp_mat['1'] = [roundTime(pd.to_datetime(t), bin_interval) for t in temp_mat['1']]
      temp_mat.set_index('1').sum().T
      output.append(temp_mat)
    a = pd.concat(output, axis = 0).sort_values(by='1')
    a = a.apply(pd.to_numeric, errors='coerce')
    
    '''
    Putting processed panda dataframes into trainable numpy matrix
    make it in a shape of 
    (number of analyzers, each of analyzer feature, time step)
    '''
    ret = np.zeros((num_analyzer,num_time_slots,num_feat))
    for index, row in a.iterrows():
      ana = int(row["0"])
      time_slot = int(row["1"])
      ret[ana][time_slot] = row.fillna(0)

    ret.swapaxes(1,2)
    return ret
    #return np.ones((feat_size, step_size)) * (self.config["IBR_ANG"] -self.config["PRED_FRAM"])

  def _perform_action(self, action):
    '''    
    perform by 
    @para action
    update current config
    if action is out of bound, perform random action

    '''
    action_type = ACTION_MEANING[action]
    if action_type == "NOOP":
      pass 
    elif action_type == "IBR_ANG_INC":
      self.config["IBR_ANG"] += step_size
    elif action_type == "IBR_ANG_DEC":
      self.config["IBR_ANG"] -= step_size
    elif action_type == "PRED_FRAM_INC":
      self.config["PRED_FRAM"] += step_size
    elif action_type == "PRED_FRAM_DEC":
      self.config["PRED_FRAM"] -= step_size
    else:
      print('Unrecognized action %d' % action_type)

  def _get_traffic_lat_by_config(self):
    '''
    by current configuration, 
    prepare for appropriate step size and prediction frame 
    @ret traffic delay for this frame 
    '''

    #A single 1080p frame by a single Youtube frame 
    frame_size = 4400 #bytes 
    '''
    frame size by configuration
    frame size =  frame_size + IBR angle * frame_size / 360
    '''
    frame_size = frame_size + self.config["IBR_ANG"] * frame_size / 360
        
    '''
    pkt_size = frame_size * predicted frame number
    '''
    pkt_size = frame_size * self.config["PRED_FRAM"]

    # sending the packet specified by pkt_size, 
    # wait until receiving the traffic delay
    #delay = vr.send(pkt_size)
    #delay = delay / 1000
    delay = pkt_size / 10000
    #TODO: change this
    return - delay

  def _get_masked_lat_by_config(self):
    '''
    by current configuration, 
    prepare for appropriate step size and prediction frame 
    @ret masked delay for this frame 
    '''
    mask = 0

    # iterate through mask reward table and accumulate all rewards 
    for config, value in self.config.items():
      mask += MSK_REWARD_TAB[config] * value 

    return mask 
      
  def render(self, mode='human', close=False):
    '''
    required method for gym class
    don't have to implement in cour case
    '''
    pass

  def _check_in_bound(self):
    self.bound_action = []

    for index in ACTION_MEANING:
      name = ACTION_MEANING[index]
      if name == "IBR_ANG_INC" and (self.config["IBR_ANG"] + step_size) >= ACTION_BD_TAB["IBR_ANG"][1]:
        self.bound_action.append(index)
      if name == "IBR_ANG_DEC" and self.config["IBR_ANG"] - step_size <= ACTION_BD_TAB["IBR_ANG"][0]:
        self.bound_action.append(index)
      if name == "PRED_FRAM_INC" and self.config["PRED_FRAM"] + step_size >= ACTION_BD_TAB["PRED_FRAM"][1]:
        self.bound_action.append(index)
      if name == "PRED_FRAM_DEC" and self.config["PRED_FRAM"] - step_size <= ACTION_BD_TAB["PRED_FRAM"][0]:
        self.bound_action.append(index)
    
ACTION_MEANING = {
  0: "NOOP",
  1: "IBR_ANG_INC",
  2: "IBR_ANG_DEC",
  3: "PRED_FRAM_INC",
  4: "PRED_FRAM_DEC"
}

'''
For each configuration, how many rewards to be assigned
it is a multiplier by 1, 
e.g. IBR_ANG latency masked = IBR_ANG * 2
detailed on each property can be seen on comment
'''
MSK_REWARD_TAB = {
  "IBR_ANG" : 2, 
  "PRED_FRAM" : 10
}

'''
action bound 
for each configuration, there is a bound associated with it
detailed on each property can be seen on comment
'''
ACTION_BD_TAB = {
    "IBR_ANG": (-10, 270), #Image based rendering has 80 ~ 360 degree of rendering
    "PRED_FRAM" :(1, 1000)  
}
