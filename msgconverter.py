

'''
    Simple encode/decode Ethernet Frames library 
    
    Author: Michal Stobierski
'''

import binascii
import bitarray as ba
import numpy as np
import sys
import re

'''
Defines
'''

codes4B5B = {
'0000': '11110',
'0001': '01001',
'0010': '10100',
'0011': '10101',
'0100': '01010',
'0101': '01011',
'0110': '01110',
'0111': '01111',
'1000': '10010',
'1001': '10011',
'1010': '10110',
'1011': '10111',
'1100': '11010',
'1101': '11011',
'1110': '11100',
'1111': '11101'
}

codes5B4B = {
'11110': '0000',
'01001': '0001',
'10100': '0010',
'10101': '0011',
'01010': '0100',
'01011': '0101',
'01110': '0110',
'01111': '0111',
'10010': '1000',
'10011': '1001',
'10110': '1010',
'10111': '1011',
'11010': '1100',
'11011': '1101',
'11100': '1110',
'11101': '1111'
}


MAC_OCTETS = 6
LEN_OCTETS = 2
CHAR_OCTETS = 1
PRE_OCTETS = 8
CRC_OCTETS = 4

'''
Utils
'''

def to_bitarray(data, bytes):
    return ba.bitarray( bin(data)[2:].zfill(bytes*8) )


def make_preamble():
    result = ba.bitarray(0)
    
    for i in range(7):
        result.extend("10101010")
    result.extend("10101011")
    
    return result

    
def change_coding(data, coding, jump):
    result = ba.bitarray(0)
    
    for i in range(0, len(data), jump):
        if (data[i:i+jump].to01() not in coding.keys()):
            return None
        result.extend(coding[data[i:i+jump].to01()])
        
    return result
    
    
def to_NRZ(data, prev):
    
    result = data
    
    if (prev == True):
        result[0] = False if result[0] == True else True
    else:
        result[0] = prev
        
    for i in range(1, len(result)):
    
        if(result[i] == True):
            result[i] = False if result[i-1] == True else True
        else:
            result[i] = result[i-1]
            
    return result


def from_NRZ(data, prev):
    
    result = ba.bitarray(0)
    
    if (data[0] == prev):
        result.append(False)
    else:
        result.append(True)
    
    for i in range(1, len(data)):
    
        if(data[i] != data[i-1]):
            result.append(True)
        else:
            result.append(False)
            
    return result

'''
Encode message to correct ethernet frame
'''

def encode(mac_source, mac_target, message):
    #Create storage for result
    result = ba.bitarray(0)

    #Convert data from input
    message_bin = ba.bitarray(0)
    for i in range(len(message)):
        message_bin.extend(to_bitarray(ord(message[i]), 1))
    
    #Append converted data to result
    result.extend(to_bitarray(mac_target, 6))
    result.extend(to_bitarray(mac_source, 6))
    result.extend(to_bitarray(len(message), 2))
    result.extend(message_bin)
    
    #Count checksum and append to res
    result.extend(to_bitarray(binascii.crc32(result) % (1<<32), 4))
    
    #Convert to 4B5B and NRZ
    result = to_NRZ(change_coding(result, codes4B5B, 4), True)
    
    #Add preamble
    pre = make_preamble()
    pre.extend(result)
    result = pre
    
    #Ret
    #print("{0}".format(result.to01()))
    return result 
    
'''
Decode message from ehternet frame (if correct)
'''

def decode(frame):
    #Create copy of input to analyse
    data = frame
    
    #Check correct length
    if (len(data) < 8*(2*MAC_OCTETS+LEN_OCTETS+CRC_OCTETS)):
        return
        
    #Check if preamble is correct
    if (re.search('^(10101010){7}(10101011){1}', data) is None):
        return None
    
    #Decode from NRZ and 4B5B
    data = change_coding(from_NRZ(data[8*PRE_OCTETS:], True), codes5B4B, 5)
    if (data is None):
        return None
    
    #Decode frame infos
    mac_bits = 8*MAC_OCTETS
    len_bits = 8*LEN_OCTETS
    crc_bits = 8*CRC_OCTETS
    
    #Check if CRC32 is correct
    my_crc32 = to_bitarray( binascii.crc32( data[:len(data)-crc_bits] ) % (1<<32), 4 )
    if(data[-crc_bits:] != my_crc32):
        return None

    #Decode message
    mac_target = int(data[:mac_bits].to01(), 2)
    mac_source = int(data[mac_bits:2*mac_bits].to01(), 2)
    message_len = int(data[2*mac_bits:2*mac_bits+len_bits].to01(), 2)
    
    message_bin = data[2*mac_bits+len_bits:len(data)-crc_bits]
    
    #Check if info about msg is correct
    if(len(message_bin)%8 != 0 or len(message_bin)/8 != message_len):
        return None
    
    message = ""
    for i in range(0, len(message_bin), 8):
        message += chr(int(message_bin[i:i+8].to01(), 2))
    
    #Ret
    #print("{0} {1} {2}".format(mac_source, mac_target, message))
    return (mac_source, mac_target, message)

'''
Example usage:
E 1 2 abc def - encode message 'abc def' from 1 to 2
D 101010... - decode ethernet frame

for line in sys.stdin:

    spaces = []
    for i in range(len(line)):
        if(line[i] == " "):
            spaces.append(i)
    
    if(line[0] == 'E'):
        encode(int(line[spaces[0]+1:spaces[1]]), int(line[spaces[1]+1:spaces[2]]), line[spaces[2]+1:-1])
    elif(line[0] == 'D'):
        decode(line[spaces[0]+1:-1])
'''
