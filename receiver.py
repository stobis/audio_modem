#!/usr/bin/env python2.7

'''
    Ethernet Frames audio receiver
    
    Author: Michal Stobierski
'''

import sys
import wave

import pulseaudio as pa
import numpy as np
import bitarray as ba
import msgconverter as mc


'''
Global variables
'''

#Sound device settings
sample_map = {
    1 : pa.SAMPLE_U8,
    2 : pa.SAMPLE_S16LE,
    4 : pa.SAMPLE_S32LE,
}

BASE_FREQ = 44100
SAMPWIDTH = 2
NCHANNELS = 1

#Program arguments
t = int(sys.argv[1])    # Signals per second
f0 = int(sys.argv[2])   # Freq of bit 0
f1 = int(sys.argv[3])   # Freq of bit 1

#Other stuff 

preamble = mc.make_preamble()    # Preamble
msg = ba.bitarray(0)    # Result - the ethernet frame
candidates = [] # With this array we will try to find preamble

signal_len = BASE_FREQ/t    # Num of frames per one bit
interval_len = 6    # Len of candidates[]; break between bits = siggnal_len/interval_len
tolerance = 0   # Acceptable difference between f0/f1 and actual bit freq

'''
Dominant frequency check
'''

def dom_freq(frames):
    # Using FFT to find best match of frequency and value in it
    res = np.fft.fft(frames)
    
    max_val = abs(res[0])
    max_it = 0

    res = res[0:len(res)/2]
    for i in range(len(res)):
        if(abs(res[i]) > max_val):
            max_val = abs(res[i])
            max_it = i 
    
    return (max_it*t, max_val)
    
            
'''
Main loop
'''

with pa.simple.open(direction=pa.STREAM_RECORD, format=sample_map[SAMPWIDTH], rate=BASE_FREQ, channels=NCHANNELS) as sound_source:
    
    ready_to_listen = False # True if we recognized preamble
    listen = False  # Listen message bits? - True after preamble end
    last_bit = -1   # Previous heard bit
    bits_left = sys.maxint   # How many bits (at least) we still need
    
    while True:
        #Read next frames
        data = sound_source.read(signal_len)
        if (len(data) == 0):
            break
        
        #Get info about actual data
        (act_freq, act_fft) = dom_freq(data)
        
        #Setup for listen 
        if(ready_to_listen is False):
            
            #Ignore noise
            if(abs(act_freq-f0) > tolerance and abs(act_freq-f1) > tolerance):
                continue
        
            #print(act_freq, act_fft)
            candidates.append(data)
            data = sound_source.read(signal_len/interval_len)   # Ignore some frames
        
            if(len(candidates) != interval_len):
                continue
            
            # We have enough candidates to try
            
            max_val = -1
            max_val_it = -1
            it = 1
            
            for x in candidates:
                (fq, fqval) = dom_freq(x)
                if(abs(fq-f1) <= tolerance):
                    if(max_val < fqval):
                        max_val = fqval
                        max_val_it = it
                it += 1
            
            
            if(max_val_it > 0):
                # We found good setting of bit 1. Now we will can listen without breaks    
                ready_to_listen = True
                for i in range(max_val_it-1):
                    data = sound_source.read(signal_len + signal_len/interval_len)
                continue
                
            # Every time we are looking at last 'interval_len' candidates
            candidates.pop(0)
        
        #Determine actual bit
        if(abs(act_freq-f0) <= tolerance):
            act_bit = 0
        elif(abs(act_freq-f1) <= tolerance):
            act_bit = 1
        else:
            act_bit = -1
        
        #Append bit to message if correct
        if(listen is True and act_bit >= 0):
            msg.append(act_bit)
            
            bits_left -= 1
            if(bits_left == 0):
                break
            
            #If we heard length of msg we can know how many bits we still need:
            if(len(msg) == 10*(2*mc.MAC_OCTETS + mc.LEN_OCTETS)):
                
                try:
                    bits_left = int(mc.change_coding(mc.from_NRZ(msg[-10*mc.LEN_OCTETS:], msg[-10*mc.LEN_OCTETS-1]), mc.codes5B4B, 5).to01(), 2)
                    #print(bits_left)
                    bits_left = 10*(bits_left+mc.CRC_OCTETS)
                except Exception:
                    print("Error: invalid or broken data.")
                    exit()
        
        #Check if preamble has ended just now
        if(listen is False and ready_to_listen is True and act_bit == last_bit and act_bit == 1):
            listen = True
        
        #Remember previous bit
        last_bit = act_bit
        
'''
Get result (decoded message)
'''

msg_str = preamble.to01() + msg.to01()
#print(msg_str)
try:
    decoded_message = mc.decode(msg_str)
    print("{0} {1} {2}".format(decoded_message[0], decoded_message[1], decoded_message[2]))
    
except Exception:
    print("Error: decoding message unsuccessful.")
    exit()
