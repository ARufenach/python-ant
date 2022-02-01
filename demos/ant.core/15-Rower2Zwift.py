#!/usr/bin/python
#
'''
Data processed
     Data Page 16
          Instantaneous speed 0.001 m/s
     Data Page 22
          Instantaneous Cadence spm
          Instantaneous power watts
'''

import time
import os
import fcntl
import sys, hashlib

from ant.core import driver
from ant.core.node import Node, Network, ChannelID
from ant.core.constants import NETWORK_KEY_ANT_PLUS, NETWORK_NUMBER_PUBLIC
from ant.plus.rower import *
from ant.plus.bikeTrainer import *
from ant.core.resetUSB import reset_USB_Device
from config import *

from ant.plus.PowerMeterTx import PowerMeterTx
from ant.plus.SpeedTx import SpeedTx


########################   Get the serial number of Raspberry Pi

def getserial():
    # Extract serial from cpuinfo file
    cpuserial = "0000000000000000"
    try:
        f = open('/proc/cpuinfo', 'r')
        for line in f:
            if line[0:6] == 'Serial':
                cpuserial = line[10:26]
        f.close()
    except:
        cpuserial = "ERROR000000000"
    return cpuserial

####################################################################

C2 = False
myWheel = 2200000

#
# ok I own a C2 rover but it's now 450 km away, I'm at winter residence
# btw I got to level 50 on Zwift with that python assembly
#

if (C2):
    POWER_ADJUST = 1.25
    SPEED_ADJUST = 2.5
    RPM_ADJUST = 3.0
else:
    print("C2 Rower simulated via Simulant bike trainer for debug")
    POWER_ADJUST = 1.0
    SPEED_ADJUST = 1.0
    RPM_ADJUST = 1.0

POWER_SENSOR_ID = int(int(hashlib.md5(getserial().encode()).hexdigest(), 16) & 0xfffe) + 1
SPEED_SENSOR_ID = int(int(hashlib.md5(getserial().encode()).hexdigest(), 16) & 0xfffe) + 2

#-------------------------------------------------#
#  ANT Callbacks                                  #
#-------------------------------------------------#
def device_paired(device_profile, channel_id):
    print(f'Connected to {device_profile.name} ({channel_id.deviceNumber})')

def search_timed_out(device_profile):
    print(f'Could not connect to {device_profile.name}')

def channel_closed(device_profile):
    print(f'Channel closed for {device_profile.name}')

def Rower(elapsedTime, distanceTraveled, msSecSpeed, kmhSpeed, cadence, power):
    print("INPUT --- Speed Km/h {} Cadence {} Power {}".format(str(kmhSpeed), str(cadence), str(power)))
    speed_meter.update(myWheel, (1+(msSecSpeed*SPEED_ADJUST)))
    power_meter.update(int(power*POWER_ADJUST), int(cadence*RPM_ADJUST))

#-------------------------------------------------#
#  Initialization                                 #
#-------------------------------------------------#

try:
    reset_USB_Device()
except Exception as ex:
   print(ex)


antnode = Node(driver.USB2Driver(log=LOG, debug=DEBUG, idProduct=0x1008))
try:
    antnode.start()
    network = Network(key=NETWORK_KEY_ANT_PLUS, name='N:ANT+')
    antnode.setNetworkKey(NETWORK_NUMBER_PUBLIC, network)

    speed_meter = SpeedTx(antnode, SPEED_SENSOR_ID)
    speed_meter.open()
    print("SUCCESFULLY STARTED speed meter with ANT+ ID " + repr(SPEED_SENSOR_ID))
    power_meter = PowerMeterTx(antnode, POWER_SENSOR_ID)
    power_meter.open()
    print("SUCCESFULLY STARTED power meter with ANT+ ID " + repr(POWER_SENSOR_ID))

    if (C2):
        myTrainer = rower(antnode, network,
             {'onDevicePaired' : device_paired,
              'onSearchTimeout': search_timed_out,
              'onChannelClosed': channel_closed,
              'onRower'  : Rower})
    else:
        myTrainer = bikeTrainer(antnode, network,
             {'onDevicePaired' : device_paired,
              'onSearchTimeout': search_timed_out,
              'onChannelClosed': channel_closed,
              'onBikeTrainer'  : Rower})


    # Unpaired, search:
    myTrainer.open()
    print('ANT started. Connecting to devices...')
except ANTException as err:
    print(f'Could not start ANT.\n{err}')

#######################################################################################

while True:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        break

myTrainer.close()
antnode.stop()
