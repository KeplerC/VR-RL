
# Path variables 
ENV_NAME = 'VR'  # Environment name
import datetime
ts = str(datetime.datetime.now())
SAVE_NETWORK_PATH = 'saved_networks/' + ENV_NAME + " " + ts
SAVE_SUMMARY_PATH = 'summary/' + ENV_NAME + " " + ts

# Training specific 
NUM_EPISODES = 12000  # Number of episodes the agent plays
STATE_LENGTH = 1  # Number of most recent frames to produce the input to the network
GAMMA = 0.99  # Discount factor
EXPLORATION_STEPS = 100000  # Number of steps over which the initial value of epsilon is linearly annealed to its final value
INITIAL_EPSILON = 1.0  # Initial value of epsilon in epsilon-greedy
FINAL_EPSILON = 0.1  # Final value of epsilon in epsilon-greedy
INITIAL_REPLAY_SIZE = 100 #20000  # Number of steps to populate the replay memory before training starts
NUM_REPLAY_MEMORY = 4000  # Number of replay memory the agent uses for training
BATCH_SIZE = 1  # Mini batch size
TARGET_UPDATE_INTERVAL = 1000  # The frequency with which the target network is updated
TRAIN_INTERVAL = 4  # The agent selects 4 actions between successive updates
LEARNING_RATE = 0.00025  # Learning rate used by RMSProp
MOMENTUM = 0.95  # Momentum used by RMSProp
MIN_GRAD = 0.01  # Constant added to the squared gradient in the denominator of the RMSProp update
SAVE_INTERVAL = 3000  # The frequency with which the network is saved
NO_OP_STEPS = 1  # Maximum number of "do nothing" actions to be performed by the agent at the start of an episode
LOAD_NETWORK = False
TRAIN = True
NUM_EPISODES_AT_TEST = 30  # Number of episodes the agent plays at test time

#input specific
NUM_ANALYZER = 4
NUM_FEATURE = 28
NUM_TIME_STAMP = 128
