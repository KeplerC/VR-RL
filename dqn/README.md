# DQN in Keras + TensorFlow + OpenAI Gym
This is an implementation of DQN (based on [Mnih et al., 2015](http://www.nature.com/nature/journal/v518/n7540/full/nature14236.html)) in Keras + TensorFlow + OpenAI Gym.  

## Requirements
- gym (Atari environment)
- scikit-image
- keras
- tensorflow


## Usage
#### Training
For DQN, run:

```
python dqn.py
```

#### Visualizing learning with TensorBoard
Run the following:

```
tensorboard --logdir=summary/
```

## References
- [Mnih et al., 2013, Playing atari with deep reinforcement learning](https://arxiv.org/abs/1312.5602)
- [Mnih et al., 2015, Human-level control through deep reinforcement learning](http://www.nature.com/nature/journal/v518/n7540/full/nature14236.html)
- [van Hasselt et al., 2016, Deep Reinforcement Learning with Double Q-learning](http://arxiv.org/abs/1509.06461)
- [devsisters/DQN-tensorflow](https://github.com/devsisters/DQN-tensorflow)
- [spragunr/deep_q_rl](https://github.com/spragunr/deep_q_rl)
