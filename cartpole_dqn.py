"""
This module contains the deep reinforcement learning model which can
learn the OpenAI Cartpole Gym using reinforcement learning or imitation
learning
"""

import random
import numpy as np
from collections import deque
from keras.models import Sequential
from keras.layers import Dense
from keras.optimizers import Adam
import os
from keras.callbacks import ModelCheckpoint
from keras.models import load_model
import keras
from datetime import datetime


class CartpoleDQN:
    """
    Contains the deep neural network agent which can be reinforced with
    game experience or through an expert human player
    """

    ENV_NAME = "CartPole-v1"

    GAMMA = 0.95
    LEARNING_RATE = 0.001

    MEMORY_SIZE = 1000000
    BATCH_SIZE = 20

    EXPLORATION_MAX = 1
    EXPLORATION_MIN = 0.01
    EXPLORATION_DECAY = 0.7

    def __init__(self, observation_space, action_space, model_name):

        """
        Constructor
        """

        # The name under which to save the model
        self.model_name = model_name

        # The chance of choosing a random action vs using output of the neural network (or lookup table)
        self.exploration_rate = self.EXPLORATION_MAX

        # The action space of the agent
        self.action_space = action_space

        # Replay buffer
        self.memory = deque(maxlen=self.MEMORY_SIZE)

        # Initialize the model if it does not exist
        if not os.path.exists(os.path.join(".", "models", "{}.h5".format(self.model_name))):
            self.model = Sequential()
            self.model.add(Dense(24, input_shape=(observation_space,), activation="relu"))
            self.model.add(Dense(24, activation="relu"))
            self.model.add(Dense(self.action_space, activation="linear"))
            self.model.compile(loss="mse", optimizer=Adam(lr=self.LEARNING_RATE))
        # Otherwise load the model
        else:
            print('Loading model...')
            self.model = load_model(os.path.join(".", "models", "{}.h5".format(self.model_name)))

        # Model save configuration
        self.save_path = os.path.join(".", "models", "{}.h5".format(self.model_name))
        self.checkpoint = ModelCheckpoint(self.save_path, monitor='loss', verbose=0, save_best_only=False, mode='min')
        self.callbacks_list = [self.checkpoint]
        self.callbacks_save_disabled = []

        # Previous reward initialization
        self.prev_highest_reward = 0

    def remember(self, state, action, reward, next_state, done):

        """
        Saves the current step for experience replay

        :param state: The current environement state
        :param action: The action taken by the machine
        :param reward: The reward from this state given the current action
        :param next_state: The next state given this action
        :param done: Whether or not the episode has ended
        :return:
        """

        self.memory.append((state, action, reward, next_state, done))

    def act(self, state):

        """
        Computing the action given the state
        Choosing whether to take the optimal action or a random action

        :param state: The environment state
        :return: The optimal action
        """

        # Random action
        if np.random.rand() < self.exploration_rate:
            return random.randrange(self.action_space)
        # Optimal action
        else:
            q_values = self.model.predict(state)
            # print("q_values: {}".format(q_values))
            # print(q_values.shape)
            # print("action_space: {}".format(self.action_space))
            # print("np.argmax(q_values[0]): {}".format(np.argmax(q_values[0])))
            return np.argmax(q_values[0])

    def experience_replay(self, save=True):

        """
        Training the deep neural network using the replay memory

        :param save: Whether or not to save the model
        """

        # If there are not enough steps across all episodes to accommodate the
        # minimum batch size then do not train
        if len(self.memory) < self.BATCH_SIZE:
            return -1, -1

        # If there are enough steps then train
        else:

            # Randomly sample some steps
            batch = random.sample(self.memory, self.BATCH_SIZE)

            # The loss values across the entire batch
            loss = []
            rewards = []

            # Iterating through each step in the batch
            for state, action, reward, state_next, terminal in batch:

                # Non-terminal reward
                if not terminal:
                    # Bellman equation
                    q_update = (reward + self.GAMMA * np.amax(self.model.predict(state_next)[0]))

                # Terminal reward (reward at end of episode)
                else:
                    q_update = reward

                # Output of the neural network (q values) given the state
                q_values = self.model.predict(state)

                # Action is the action which was taken in the state within the episode
                # This action is/was thought to be the optimal action before training
                # This action gets updated with the new reward.
                q_values[0][action] = q_update

                # Backpropagation based on the current experience
                # Note: at this point your q_value are your labels
                # Saves on last step of batch only
                if save:
                    history = self.model.fit(state, q_values, verbose=0, callbacks=self.callbacks_list)
                else:
                    history = self.model.fit(state, q_values, verbose=0, callbacks=self.callbacks_save_disabled)

                loss = loss + history.history['loss']
                rewards = rewards + [reward]

            # if np.mean(rewards) > self.prev_highest_reward:
            #
            #     # Updating the mean reward
            #     self.prev_highest_reward = np.mean(rewards)
            #
            #     # Changing exploration rate after training
            #     # This is equivalent to modifying your learning rate in supervised learning
            #     old_exploration_rate = self.exploration_rate
            #     self.exploration_rate *= self.EXPLORATION_DECAY
            #     self.exploration_rate = max(self.EXPLORATION_MIN, self.exploration_rate)
            #     print("Exploration rate is updated from {} to {}".format(old_exploration_rate, self.exploration_rate))
            # else:
            #     print("Exploration rate is currently {}".format(self.exploration_rate))

            # Changing exploration rate after training
            # This is equivalent to modifying your learning rate in supervised learning
            self.exploration_rate *= self.EXPLORATION_DECAY
            self.exploration_rate = max(self.EXPLORATION_MIN, self.exploration_rate)
            print("Exploration rate is currently {}".format(self.exploration_rate))

            # Returning average training loss and average training reward of current step
            return np.mean(loss), np.mean(rewards)
