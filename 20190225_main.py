from proc import preprocess
from train import test_train
from model import test
import tensorflow as tf
import h5py
import os
import multiprocessing as mp
import matplotlib.pyplot as plt

preproc = {
    'dir': './raw',
    'stride': 15,
    'patch_size': 40,  # should be multiple of 8
    'batch_size': 1000,
    'mode': 'h5',
    'shuffle': True
}

preprocess(**preproc)
