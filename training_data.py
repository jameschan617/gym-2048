"""Manage training data"""

from __future__ import print_function

import copy
import numpy as np
import os

class training_data(object):

    def __init__(self, record_next_action=False):
        self._x = np.empty([0, 4, 4], dtype=np.int)
        self._y_digit = np.zeros([0, 1], dtype=np.int)
        self._reward = np.zeros([0, 1], dtype=np.float)
        self._record_next_action = record_next_action
        if record_next_action:
            self._next_x = np.empty([0, 4, 4], dtype=np.int)

    def copy(self):
        return copy.deepcopy(self)

    def _check_lengths(self):
        assert self._x.shape[0] == self._y_digit.shape[0]
        assert self._x.shape[0] == self._reward.shape[0]
        if self._record_next_action:
            assert self._next_x.shape[0] == self._reward.shape[0]

    def get_x(self):
        return self._x

    def get_y_digit(self):
        return self._y_digit

    def get_reward(self):
        return self._reward

    def get_next_x(self):
        assert self._record_next_action
        return self._next_x

    def add(self, board, action, reward, next_board=None):
        assert reward is not None
        self._x = np.append(self._x, np.reshape(board, (1, 4, 4)), axis=0)

        y_digit = np.zeros([1, 1], dtype=np.int)
        y_digit[0, 0] = action
        self._y_digit = np.append(self._y_digit, y_digit, axis=0)

        r = np.zeros([1, 1], dtype=np.float)
        r[0, 0] = reward
        self._reward = np.append(self._reward, r, axis=0)

        if self._record_next_action:
            self._next_x = np.append(self._next_x, np.reshape(next_board, (1, 4, 4)), axis=0)

        self._check_lengths()

    def get_n(self, n):
        """Get training sample number n"""
        if self._record_next_action:
            return self._x[n,:,:], self._y_digit[n,:], self._reward[n,:], self._next_x[n,:,:]
        else:
            return self._x[n,:,:], self._y_digit[n,:], self._reward[n,:]

    def log2_rewards(self):
        """log2 of reward values to keep them in a small range"""
        items = self._reward.shape[0]
        rewards = np.reshape(self._reward, (items))
        log_rewards = np.ma.log(rewards) / np.ma.log(2)
        self._reward = np.reshape(np.array(log_rewards, np.float), (items, 1))

    def smooth_rewards(self, llambda=0.9):
        """Smooth reward values so that they don't just represent that action.
         Relies on the data being still in game order."""
        items = self._reward.shape[0]
        rewards = list(np.reshape(self._reward, (items)))
        smoothed_rewards = list()
        previous = None
        rewards.reverse()
        for e in rewards:
            smoothed = e
            if previous:
                smoothed += llambda * previous
            smoothed_rewards.append(smoothed)
            previous = smoothed
        smoothed_rewards.reverse()
        self._reward = np.reshape(np.array(smoothed_rewards, np.float), (items, 1))

    def normalize_rewards(self, mean=None, sd=None):
        """Normalize rewards by subtracting mean and dividing by stdandard deviation"""
        items = self._reward.shape[0]
        rewards = np.reshape(self._reward, (items))
        if mean is None:
            mean = np.mean(rewards)
        if sd is None:
            sd = np.std(rewards)
        norm_rewards = (rewards - mean) / sd
        self._reward = np.reshape(np.array(norm_rewards, np.float), (items, 1))

    def merge(self, other):
        assert self._record_next_action == other._record_next_action
        self._x = np.concatenate((self._x, other.get_x()))
        self._y_digit = np.concatenate((self._y_digit, other.get_y_digit()))
        self._reward = np.concatenate((self._reward, other.get_reward()))
        if self._record_next_action:
            self._next_x = np.concatenate((self._next_x, other.get_next_x()))
        self._check_lengths()

    def split(self, split=0.5):
        splitpoint = int(self.size() * split)
        a = training_data(self._record_next_action)
        b = training_data(self._record_next_action)
        a._x = self._x[:splitpoint,:,:]
        b._x = self._x[splitpoint:,:,:]
        a._y_digit = self._y_digit[:splitpoint,:]
        b._y_digit = self._y_digit[splitpoint:,:]
        a._reward = self._reward[:splitpoint,:]
        b._reward = self._reward[splitpoint:,:]
        if self._record_next_action:
            a._next_x = self._next_x[:splitpoint,:,:]
            b._next_x = self._next_x[splitpoint:,:,:]
        a._check_lengths()
        b._check_lengths()
        return a, b

    def sample(self, index_list):
        indexes = np.asarray(index_list)
        sample = training_data(self._record_next_action)
        sample._x = self._x[indexes,:,:]
        sample._y_digit = self._y_digit[indexes,:]
        sample._reward = self._reward[indexes,:]
        sample._next_x = self._next_x[indexes,:,:]
        sample._check_lengths()
        return sample

    def size(self):
        return self._x.shape[0]

    def import_csv(self, filename):
        """Load data as CSV file"""
        # Load board state
        flat_data = np.loadtxt(filename, dtype=np.int, delimiter=',', skiprows=1, usecols=tuple(range(16)))
        self._x = np.reshape(flat_data, (-1, 4, 4))

        # Load actions
        digits = np.loadtxt(filename, dtype=np.int, delimiter=',', skiprows=1, usecols=16)
        self._y_digit = np.reshape(digits, (-1, 1))

        # Load rewards
        reward_data = np.loadtxt(filename, delimiter=',', skiprows=1, usecols=17)
        self._reward = reward_data.reshape(-1, 1)

        # Load next board state if using that
        if self._record_next_action:
            flat_data = np.loadtxt(filename, dtype=np.int, delimiter=',', skiprows=1, usecols=tuple(range(18, 34)))
            self._next_x = np.reshape(flat_data, (-1, 4, 4))

        self._check_lengths()

    def construct_header(self):
        header = list()
        for m in range(1, 5):
            for n in range(1, 5):
                header.append('{}-{}'.format(m, n))
        header.append('action')
        header.append('reward')
        if self._record_next_action:
            for m in range(1, 5):
                for n in range(1, 5):
                    header.append('next {}-{}'.format(m, n))
        return header

    def export_csv(self, filename):
        """Save data as CSV file"""
        items = self.size()
        flat_x = np.reshape(self._x, (items, 16))
        flat_data = np.concatenate((flat_x, self._y_digit), axis=1)
        flat_data = np.concatenate((flat_data, self._reward), axis=1)
        # Should have flat 16 square board, direction and reward
        assert flat_data.shape[1] == 18
        if self._record_next_action:
            flat_next_x = np.reshape(self._next_x, (items, 16))
            flat_data = np.concatenate((flat_data, flat_next_x), axis=1)
            assert flat_data.shape[1] == 34

        header = self.construct_header()

        fformat = '%d,' * 17 + '%f'
        if self._record_next_action:
            fformat += ',%d' * 16
        np.savetxt(filename, flat_data, comments='', fmt=fformat, header=','.join(header))

    def dump(self):
        print(self._x)
        print(self._y_digit)
        print(self._reward)
        if self._record_next_action:
            print(self._next_x)

    def hflip(self):
        """Flip all the data horizontally"""
        # Add horizontal flip of inputs and outputs
        self._x = np.flip(self.get_x(), 2)

        output_digits = self.get_y_digit()
        # Swap directions 1 and 3
        temp = np.copy(output_digits)
        temp[temp == 1] = 33
        temp[temp == 3] = 1
        temp[temp == 33] = 3
        self._y_digit = temp

        if self._record_next_action:
            self._next_x = np.flip(self.get_next_x(), 2)

        self._check_lengths()

    def rotate(self, k):
        """Rotate the board by k * 90 degrees"""
        self._x = np.rot90(self.get_x(), k=k, axes=(2, 1))
        self._y_digit = np.mod(self.get_y_digit() + k, 4)
        if self._record_next_action:
            self._next_x = np.rot90(self.get_next_x(), k=k, axes=(2,1))
        self._check_lengths()

    def augment(self):
        """Flip the board horizontally, then add rotations to other orientations."""
        # Add a horizontal flip of the board
        other = self.copy()
        other.hflip()
        self.merge(other)

        # Add 3 rotations of the previous
        k1 = self.copy()
        k2 = self.copy()
        k3 = self.copy()
        k1.rotate(1)
        k2.rotate(2)
        k3.rotate(3)
        self.merge(k1)
        self.merge(k2)
        self.merge(k3)

        self._check_lengths()
