#
# Some settings to force TensorFlow to behave nicely
#
# (c) 2021 Jean-Olivier Irisson, GNU General Public License v3
#

import os

# disable tensorflow messages
#os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
# NB: does not work when run on the command line apparently...

# store models downloaded from TFHub in the user's home to avoid permission problems
import sys

os.environ['TFHUB_CACHE_DIR'] = os.path.expanduser('~/.tfhub_modules/')

# Set a memory limit on tensorflow, which otherwise takes all the GPU memory by default
# which would be fine except that other GPU-related modules (CUBLAS) have 0 byte left for them.
import tensorflow as configured_tf
gpus = configured_tf.config.experimental.list_physical_devices('GPU')

if len(gpus) == 0:
    print(""" NO GPU FOUND. If it worked before, you can try:
root:~# rmmod nvidia_uvm
root:~# nvidia-modprobe 
    """, file=sys.stderr)

# # either allow memory to grow as needed (less efficient -- and seems broken)
# tf.config.experimental.set_memory_growth(gpus[0], True)

# or set a predefined memory limit
# TODO: A parameter.
if len(gpus) > 0:
    configured_tf.config.experimental.set_virtual_device_configuration(gpus[0],
        [configured_tf.config.experimental.VirtualDeviceConfiguration(memory_limit=2300)])

