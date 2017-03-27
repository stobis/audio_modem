#!/usr/bin/env python2.7

'''
    Ethernet Frames audio sender
    
    Author: Michal Stobierski
'''

import sys
import wave
import pulseaudio as pa
import numpy as np
import math

import msgconverter as mc

#Sound device settings
sample_map = {
    1 : pa.SAMPLE_U8,
    2 : pa.SAMPLE_S16LE,
    4 : pa.SAMPLE_S32LE,
}

dtype_map = {
    1 : np.int16,
    2 : np.int16,
    4 : np.int32,
}

BASE_FREQ = 44100
SAMPWIDTH = 2
NCHANNELS = 1
MULTIPLIER = 23000

#Program arguments
t = int(sys.argv[1])
f0 = int(sys.argv[2])
f1 = int(sys.argv[3])
source = int(sys.argv[4])
target = int(sys.argv[5])
msg = sys.argv[6]

#Encode message from argv
encoded_message = mc.encode(source, target, msg)

'''
Main loop
'''

with pa.simple.open(direction=pa.STREAM_PLAYBACK, format=sample_map[SAMPWIDTH], rate=BASE_FREQ, channels=NCHANNELS) as player:

    time = float((1.0)/t)   # time of one bit
    arg_f1 = 2*math.pi*f1   
    arg_f0 = 2*math.pi*f0
    
    for bit in encoded_message:
        
        act_samples = np.arange(BASE_FREQ*time)/float(BASE_FREQ)
        
        if (bit is True):
            frames = np.sin(act_samples*arg_f1)*MULTIPLIER
        else:
            frames = np.sin(act_samples*arg_f0)*MULTIPLIER
            
        player.write(frames)
        
    player.drain()

