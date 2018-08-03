# Reinforcement Learning and VR

### Files Included
vr
- gym-vr: a pip package for VR gym environment
- dqn: a deep Q-Learn model
- netDelay: source code for generating ./Program
- FYI
  - log: set of logs extracted from ouput of MI analyzers
  - set of analyzers: the analyzer scripts I am using

### Usage
First we need to **install VR training environment** by

```bash
cd VR_REIN
pip install -e .
```
This environment strictly follows package "gym"'s requirement, which gives observation, reward for each action in action space.

Then we start a **sample server** which listens to 127.0.0.1 with port number 9999 by
```bash
cd netDelay/server
./Program
```

Then we run the model by 
```bash
cd dqn
python dqn.py
```
