# Reinforcement Learning and VR

### Files Included
vr
- log: set of logs extracted from ouput of MI analyzers
- set of analyzers: the analyzer scripts I am using
- VR_REIN: a pip package for vr gym environment
- dqn: a deep Q-Learn model
- net-tools: source code for generating ./Program

### Usage
First we need to install VR training environment by

cd VR_REIN
pip install -e .

Then run
cd dqn
python dqn.py