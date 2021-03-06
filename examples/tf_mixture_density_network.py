#!/usr/bin/env python
"""
Mixture density network using maximum likelihood.

Probability model:
  Prior: None ("flat prior")
  Likelihood: Mixture sum of normals parameterized by a NN
Inference: Maximum a posteriori
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import edward as ed
import numpy as np
import tensorflow as tf

from edward.stats import norm
from keras import backend as K
from keras.layers import Dense
from sklearn.cross_validation import train_test_split


class MixtureDensityNetwork:
  """
  Mixture density network for outputs y on inputs x.

  p((x,y), (z,theta))
  = sum_{k=1}^K pi_k(x; theta) Normal(y; mu_k(x; theta), sigma_k(x; theta))

  where pi, mu, sigma are the output of a neural network taking x
  as input and with parameters theta. There are no latent variables
  z, which are hidden variables we aim to be Bayesian about.
  """
  def __init__(self, K):
    self.K = K

  def neural_network(self, X):
    """pi, mu, sigma = NN(x; theta)"""
    # fully-connected layer with 25 hidden units
    hidden1 = Dense(25, activation=K.relu)(X)
    hidden2 = Dense(25, activation=K.relu)(hidden1)
    self.mus = Dense(self.K)(hidden2)
    self.sigmas = Dense(self.K, activation=K.exp)(hidden2)
    self.pi = Dense(self.K, activation=K.softmax)(hidden2)

  def log_prob(self, xs, zs):
    """Return scalar, the log joint density log p(xs, zs)."""
    # Note there are no parameters we're being Bayesian about. The
    # parameters are baked into how we specify the neural networks.
    X, y = xs['X'], xs['y']
    self.neural_network(X)
    result = self.pi * tf.exp(norm.logpdf(y, self.mus, self.sigmas))
    result = tf.log(tf.reduce_sum(result, 1))
    return tf.reduce_sum(result)


def build_toy_dataset(N):
  y_data = np.float32(np.random.uniform(-10.5, 10.5, (1, N))).T
  r_data = np.float32(np.random.normal(size=(N, 1)))  # random noise
  x_data = np.float32(np.sin(0.75 * y_data) * 7.0 + y_data * 0.5 + r_data * 1.0)
  return train_test_split(x_data, y_data, random_state=42)


ed.set_seed(42)
model = MixtureDensityNetwork(10)

X_train, X_test, y_train, y_test = build_toy_dataset(N=6000)
print("Size of features in training data: {:s}".format(X_train.shape))
print("Size of output in training data: {:s}".format(y_train.shape))
print("Size of features in test data: {:s}".format(X_test.shape))
print("Size of output in test data: {:s}".format(y_test.shape))

X = ed.placeholder(tf.float32, shape=(None, 1))
y = ed.placeholder(tf.float32, shape=(None, 1))
data = {'X': X, 'y': y}

inference = ed.MAP([], data, model)
sess = ed.get_session()
K.set_session(sess)
inference.initialize()

init = tf.initialize_all_variables()
init.run()

NEPOCH = 20
train_loss = np.zeros(NEPOCH)
test_loss = np.zeros(NEPOCH)
for i in range(NEPOCH):
  info_dict = inference.update(feed_dict={X: X_train, y: y_train})
  train_loss[i] = info_dict['loss']
  test_loss[i] = sess.run(inference.loss, feed_dict={X: X_test, y: y_test})
  print("Train Loss: {:0.3f}, Test Loss: {:0.3f}".format(train_loss[i],
                                                         test_loss[i]))

pred_weights, pred_means, pred_std = sess.run(
    [model.pi, model.mus, model.sigmas], feed_dict={X: X_test})
