# This module contains functions that are used in both the main power-monitor code and the calibration code.

from datetime import datetime
from config import ct_phase_correction, ct1_channel, ct2_channel, ct3_channel, ct4_channel, ct5_channel, ct6_channel, board_voltage_channel, v_sensor_channel, logger
import spidev
import subprocess
import sys
from time import sleep
from textwrap import dedent

#Create SPI
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1750000          # Changing this value will require you to adjust the phasecal values above.

def readadc(adcnum):
    # read SPI data from the MCP3008, 8 channels in total
    r = spi.xfer2([1, 8 + adcnum << 4, 0])
    data = ((r[1] & 3) << 8) + r[2]
    return data

def collect_data(numSamples):
    # Get time of reading
    now = datetime.utcnow()
    
    samples = []
    ct1_data = []
    ct2_data = []
    ct3_data = []
    ct4_data = []
    # ct5_data = []
    # ct6_data = []
    v_data = []

    for _ in range(numSamples):
        ct1 = readadc(ct1_channel)
        # ct5 = readadc(ct5_channel)
        ct2 = readadc(ct2_channel)
        v = readadc(v_sensor_channel)
        ct3 = readadc(ct3_channel)
        ct4 = readadc(ct4_channel)
        # ct6 = readadc(ct6_channel)
        ct1_data.append(ct1)
        ct2_data.append(ct2)
        ct3_data.append(ct3)
        ct4_data.append(ct4)
        # ct5_data.append(ct5)
        # ct6_data.append(ct6)
        v_data.append(v)    
    
    samples = {
        'ct1' : ct1_data,
        'ct2' : ct2_data,
        'ct3' : ct3_data,
        'ct4' : ct4_data,
        # 'ct5' : ct5_data,
        # 'ct6' : ct6_data,
        'voltage' : v_data,
        'time' : now,
    }
    return samples

