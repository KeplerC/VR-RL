# Deep Q-Network
This is a very basic DQN (with experience replay) implementation, which uses OpenAI's gym environment. 

This is only an implementation of DQN without any knowledge of network/analyzers/etc. Thus, this model can be easily changed to other models that work in gym environment. 

### Usage
First, make sure the sample server is running.
Then run
```bash
python3 dqn.py
```

To tune the hyperparameters, please go to comments of ./config.py

### References
- https://www.cs.toronto.edu/~vmnih/docs/dqn.pdf
