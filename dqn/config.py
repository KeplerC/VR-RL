# in test phase, we don't update learning
istest = False
# job name
jobid = "123123"
path = os.path.join(jobid, "model")
#number of total training steps
num_steps = 10000000
# 0: don't print everything
# 1: print by specific epoch
verbosity = 1
# number of steps on each training step
learn_freq = 4
# number of training steps between copies of online DQN to target DQN")
copy_step = 4096
# how many steps to save the model
save_steps = 10000
# number of steps of exploration
explore_steps = 100000



# hyperparameter
learning_rate = 1e-4
training_start = 10000  # start training after 10,000 game steps
discount_rate = 0.99
batch_size = 1

# dimension of input matrices
num_time_step = 128
num_analyzer = 2
num_feature = 28

# epsilon-greedy policy with decaying epsilon
eps_min = 0.01
eps_max = 1.0 if not istest else eps_min


