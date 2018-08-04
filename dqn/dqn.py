#!/usr/bin/env python3
from collections import deque
import gym
import numpy as np
import os
import tensorflow as tf
import sys
#import matplotlib
#matplotlib.use('Agg')
#import matplotlib.pyplot as plt
import seaborn as sns
sns.set()
from config import *


'''
use vr gum environment 
'''
import gym_foo
env = gym.make("foo-v0")


def q_network(net, name, reuse=False):
    '''
    Deep Q Learning Network
    current architecture:
    =input
    LSTM layer
    fully connected relu
    fully connected layer
    =output action space
    
    '''
    with tf.variable_scope(name, reuse=reuse) as scope:
        initializer = tf.contrib.layers.variance_scaling_initializer()
        lstm_cell = tf.contrib.rnn.BasicLSTMCell(num_time_step,state_is_tuple=True)
        lstm_state_in = lstm_cell.zero_state(1, tf.float32)
        net,lstm_state_out = tf.nn.dynamic_rnn(inputs = net, cell = lstm_cell, dtype=tf.float32, initial_state = lstm_state_in, scope = "lstm_cell")

        net = tf.layers.dense(net, 256, activation=tf.nn.relu, kernel_initializer=initializer)
        net = tf.contrib.layers.flatten(net)
        net = tf.layers.dense(net, env.action_space.n, kernel_initializer=initializer)

    trainable_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope=scope.name)
    return net, trainable_vars


'''
training step
'''

with tf.variable_scope("train"):
    X_state = tf.placeholder(tf.float32, shape=[None, num_analyzer * num_feature, num_time_step])
    X_next_state = tf.placeholder(tf.float32, shape=[None, num_analyzer * num_feature, num_time_step])
    X_action = tf.placeholder(tf.int32, shape=[None])
    X_done = tf.placeholder(tf.float32, shape=[None])
    X_rewards = tf.placeholder(tf.float32, shape=[None])
    online_q_values, online_vars = q_network(X_state, name="q_networks/online")
    target_q_values, target_vars = q_network(X_next_state, name="q_networks/online", reuse=True)
    max_target_q_values = tf.reduce_max(target_q_values, axis=1)
    target = X_rewards + (1. - X_done) * discount_rate * max_target_q_values
    q_value = tf.reduce_sum(online_q_values * tf.one_hot(X_action, env.action_space.n), axis=1)
    error = tf.abs(q_value - tf.stop_gradient(target))
    clipped_error = tf.clip_by_value(error, 0.0, 1.0)
    linear_error = 2 * (error - clipped_error)
    loss = tf.reduce_mean(tf.square(clipped_error) + linear_error)

    global_step = tf.Variable(0, trainable=False, name='global_step')
    optimizer = tf.train.AdamOptimizer(learning_rate)
    training_op = optimizer.minimize(loss, global_step=global_step)

    #writing everything into tensorboard
    tf.summary.scalar("loss", loss)
    tf.summary.histogram("action space", X_action)
    merged = tf.summary.merge_all()
    
# copy the online DQN to the target DQN
copy_ops = [target_var.assign(online_var)
            for target_var, online_var in zip(target_vars, online_vars)]
copy_online_to_target = tf.group(*copy_ops)

# Let's implement a simple replay memory
replay_memory = deque([], maxlen=10000)
import numpy as np
def sample_memories(batch_size):
    indices = np.random.permutation(len(replay_memory))[:batch_size]
    cols = [[], [], [], [], []] # state, action, reward, next_state, continue
    for idx in indices:
        memory = replay_memory[idx]
        for col, value in zip(cols, memory):
            col.append(value)
    cols = [np.array(col) for col in cols]
    return cols


def epsilon_greedy(q_values, step, bound = None):
    epsilon = max(eps_min, eps_max - (eps_max-eps_min) * step / explore_steps)
    rand_action_within_bound = np.random.randint(env.action_space.n)
    while(rand_action_within_bound in bound):
        rand_action_within_bound = np.random.randint(env.action_space.n)

    #print(rand_action_within_bound)
    if np.random.rand() < epsilon:
        return rand_action_within_bound
    else:
        potential_q_values =  np.argmax(q_values) # optimal action
        print(potential_q_values)
        if potential_q_values in bound:
            return rand_action_within_bound
        else:
            return potential_q_values

# initialize training variables 
done = True 
loss_val = np.infty
game_length = 0
total_max_q = 0
mean_max_q = 0.0
returnn = 0.0
returns = []
steps = []
init = tf.global_variables_initializer()
saver = tf.train.Saver()
state, reward, done, info = env.step(env.action_space.sample())

with tf.Session() as sess:
    train_writer = tf.summary.FileWriter(path, sess.graph)
    if os.path.isfile(path + ".index"):
        saver.restore(sess, path)
    else:
        init.run()
        copy_online_to_target.run()
    for step in range(num_steps):
        training_iter = global_step.eval() 
        if step % 50 == 3: # game over, start again
            print(reward, info)
            if verbosity > 0:
                print("Step {}/{} ({:.1f})% Training iters {}   "
                      "Loss {:5f}    Mean Max-Q {:5f}   Return: {:5f}".format(
                step, num_steps, step * 100 / num_steps,
                training_iter, loss_val, mean_max_q, returnn))
                sys.stdout.flush()
        if done:
            state = env.reset()

        state = state.reshape((num_analyzer * num_feature, num_time_step))
        # Online DQN evaluates what to do
        q_values = online_q_values.eval(feed_dict={X_state: [state]})
        action = epsilon_greedy(q_values, step, info["bound"])

        # Online DQN plays
        next_state, reward, done, info = env.step(action)
        returnn += reward
        next_state = next_state.reshape((num_analyzer * num_feature, num_time_step))

        # memorization 
        replay_memory.append((state, action, reward, next_state, done))
        state = next_state

        if istest:
            continue

        # Compute statistics for tracking progress (not shown in the book)
        total_max_q += q_values.max()
        game_length += 1
        if done:
            steps.append(step)
            returns.append(returnn)
            returnn = 0.
            mean_max_q = total_max_q / game_length
            total_max_q = 0.0
            game_length = 0

        if step < training_start or step % learn_freq != 0:
            continue # only train after warmup period and at regular intervals
        
        # Sample memories and train the online DQN
        X_state_val, X_action_val, X_rewards_val, X_next_state_val, X_done_val = sample_memories(batch_size)
        
        _, loss_val,summary = sess.run([training_op, loss, merged],
        {X_state: X_state_val, 
        X_action: X_action_val, 
        X_rewards: X_rewards_val,
        X_done: X_done_val,
        X_next_state: X_next_state_val})
        
        train_writer.add_summary(summary, step)
        
        # Regularly copy the online DQN to the target DQN
        if step % copy_step == 0:
            copy_online_to_target.run()

        # And save regularly
        if step % save_steps == 0:
            saver.save(sess, path)
            np.save(os.path.join(jobid, "{}.npy".format(jobid)), np.array((steps, returns)))


