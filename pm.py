#!/usr/bin/python
from concurrent.futures import thread
from time import sleep
import timeit
import csv
from math import sqrt
import sys
from datetime import datetime
from plotting import plot_data
import pickle
import os
from socket import socket, AF_INET, SOCK_DGRAM
import fcntl
from prettytable import PrettyTable
import logging
from config import logger, ct_phase_correction, ct2_channel, ct3_channel, ct4_channel, ct5_channel, ct6_channel, ct6_channel, board_voltage_channel, v_sensor_channel, GRID_VOLTAGE, AC_TRANSFORMER_OUTPUT_VOLTAGE, accuracy_calibration
from calibration import check_phasecal, rebuild_wave, find_phasecal
from textwrap import dedent
from common import collect_data, readadc
from shutil import copyfile

from api_client import ApiClient
import time

# Tuning Variables


# Static Variables - these should not be changed by the end user
AC_voltage_ratio            = (GRID_VOLTAGE / AC_TRANSFORMER_OUTPUT_VOLTAGE) * 11   # This is a rough approximation of the ratio
# Phase Calibration - note that these items are listed in the order they are sampled.
# Changes to these values are made in config.py, in the ct_phase_correction dictionary.
ct1_phasecal = ct_phase_correction['ct1']
ct2_phasecal = ct_phase_correction['ct2']
ct3_phasecal = ct_phase_correction['ct3']
ct4_phasecal = ct_phase_correction['ct4']
# ct5_phasecal = ct_phase_correction['ct5']
# ct6_phasecal = ct_phase_correction['ct6']
ct1_accuracy_factor         = accuracy_calibration['ct1']
ct2_accuracy_factor         = accuracy_calibration['ct2']
ct3_accuracy_factor         = accuracy_calibration['ct3']
ct4_accuracy_factor         = accuracy_calibration['ct4']
# ct5_accuracy_factor         = accuracy_calibration['ct5']
# ct6_accuracy_factor         = accuracy_calibration['ct6']
AC_voltage_accuracy_factor  = accuracy_calibration['AC']



def dump_data(dump_type, samples):
    speed_kHz = spi.max_speed_hz / 1000
    now = datetime.now().stfrtime('%m-%d-%Y-%H-%M')
    filename = f'data-dump-{now}.csv'
    with open(filename, 'w') as f:
        headers = ["Sample#", "ct1", "ct2", "ct3", "ct4"]#, "ct5", "ct6", "voltage"]
        writer = csv.writer(f)
        writer.writerow(headers)
        # samples contains lists for each data sample. 
        for i in range(0, len(samples[0])):
            ct1_data = samples[0]
            ct2_data = samples[1]
            ct3_data = samples[2]
            ct4_data = samples[3]
            # ct5_data = samples[4]
            # ct6_data = samples[5]
            v_data = samples[-1]
            writer.writerow([i, ct1_data[i], ct2_data[i], v_data[i]], ct3_data[i], ct4_data[i])#, ct5_data[i], ct6_data[i]
    logger.info(f"CSV written to {filename}.")

def get_board_voltage():
    # Take 10 sample readings and return the average board voltage from the +3.3V rail. 
    samples = []
    while len(samples) <= 10:
        data = readadc(board_voltage_channel)
        samples.append(data)

    avg_reading = sum(samples) / len(samples)
    board_voltage = (avg_reading / 1024) * 3.31 * 2    
    return board_voltage

# Phase corrected power calculation
def calculate_power(samples, board_voltage):
    ct1_samples = samples['ct1']        # current samples for ct1
    ct2_samples = samples['ct2']        # current samples for ct2
    ct3_samples = samples['ct3']        # current samples for ct3
    ct4_samples = samples['ct4']        # current samples for ct4
    # ct5_samples = samples['ct5']        # current samples for ct5
    # ct6_samples = samples['ct6']        # current samples for ct6
    v_samples_1 = samples['v_ct1']      # phase-corrected voltage wave specifically for ct1
    v_samples_2 = samples['v_ct2']      # phase-corrected voltage wave specifically for ct2
    v_samples_3 = samples['v_ct3']      # phase-corrected voltage wave specifically for ct3
    v_samples_4 = samples['v_ct4']      # phase-corrected voltage wave specifically for ct4
    # v_samples_5 = samples['v_ct5']      # phase-corrected voltage wave specifically for ct5   
    # v_samples_6 = samples['v_ct6']      # phase-corrected voltage wave specifically for ct6   

    # Variable Initialization    
    sum_inst_power_ct1 = 0
    sum_inst_power_ct2 = 0
    sum_inst_power_ct3 = 0
    sum_inst_power_ct4 = 0
    # sum_inst_power_ct5 = 0
    # sum_inst_power_ct6 = 0
    sum_squared_current_ct1 = 0 
    sum_squared_current_ct2 = 0
    sum_squared_current_ct3 = 0
    sum_squared_current_ct4 = 0
    # sum_squared_current_ct5 = 0
    # sum_squared_current_ct6 = 0
    sum_raw_current_ct1 = 0
    sum_raw_current_ct2 = 0
    sum_raw_current_ct3 = 0
    sum_raw_current_ct4 = 0
    # sum_raw_current_ct5 = 0
    # sum_raw_current_ct6 = 0
    sum_squared_voltage_1 = 0
    sum_squared_voltage_2 = 0
    sum_squared_voltage_3 = 0
    sum_squared_voltage_4 = 0
    # sum_squared_voltage_5 = 0
    # sum_squared_voltage_6 = 0
    sum_raw_voltage_1 = 0
    sum_raw_voltage_2 = 0
    sum_raw_voltage_3 = 0
    sum_raw_voltage_4 = 0
    # sum_raw_voltage_5 = 0
    # sum_raw_voltage_6 = 0

    # Scaling factors
    vref = board_voltage / 1024
    ct1_scaling_factor = vref * 100 * ct1_accuracy_factor
    ct2_scaling_factor = vref * 100 * ct2_accuracy_factor
    ct3_scaling_factor = vref * 100 * ct3_accuracy_factor
    ct4_scaling_factor = vref * 100 * ct4_accuracy_factor
    # ct5_scaling_factor = vref * 100 * ct5_accuracy_factor
    # ct6_scaling_factor = vref * 100 * ct6_accuracy_factor
    voltage_scaling_factor = vref * AC_voltage_ratio * AC_voltage_accuracy_factor
    

    num_samples = len(v_samples_1)
    
    for i in range(0, num_samples):
        ct1 = (int(ct1_samples[i]))
        ct2 = (int(ct2_samples[i]))
        ct3 = (int(ct3_samples[i]))
        ct4 = (int(ct4_samples[i]))
        # ct5 = (int(ct5_samples[i]))
        # ct6 = (int(ct6_samples[i]))
        voltage_1 = (int(v_samples_1[i]))
        voltage_2 = (int(v_samples_2[i]))
        voltage_3 = (int(v_samples_3[i]))
        voltage_4 = (int(v_samples_4[i]))
        # voltage_5 = (int(v_samples_5[i]))
        # voltage_6 = (int(v_samples_6[i]))

        # Process all data in a single function to reduce runtime complexity
        # Get the sum of all current samples individually
        sum_raw_current_ct1 += ct1
        sum_raw_current_ct2 += ct2
        sum_raw_current_ct3 += ct3
        sum_raw_current_ct4 += ct4
        # sum_raw_current_ct5 += ct5
        # sum_raw_current_ct6 += ct6
        sum_raw_voltage_1 += voltage_1
        sum_raw_voltage_2 += voltage_2
        sum_raw_voltage_3 += voltage_3
        sum_raw_voltage_4 += voltage_4
        # sum_raw_voltage_5 += voltage_5
        # sum_raw_voltage_6 += voltage_6


        # Calculate instant power for each ct sensor
        inst_power_ct1 = ct1 * voltage_1
        inst_power_ct2 = ct2 * voltage_2
        inst_power_ct3 = ct3 * voltage_3
        inst_power_ct4 = ct4 * voltage_4
        # inst_power_ct5 = ct5 * voltage_5
        # inst_power_ct6 = ct6 * voltage_6
        sum_inst_power_ct1 += inst_power_ct1
        sum_inst_power_ct2 += inst_power_ct2
        sum_inst_power_ct3 += inst_power_ct3
        sum_inst_power_ct4 += inst_power_ct4
        # sum_inst_power_ct5 += inst_power_ct5
        # sum_inst_power_ct6 += inst_power_ct6

        # Squared voltage
        squared_voltage_1 = voltage_1 * voltage_1
        squared_voltage_2 = voltage_2 * voltage_2
        squared_voltage_3 = voltage_3 * voltage_3
        squared_voltage_4 = voltage_4 * voltage_4
        # squared_voltage_5 = voltage_5 * voltage_5
        # squared_voltage_6 = voltage_6 * voltage_6
        sum_squared_voltage_1 += squared_voltage_1
        sum_squared_voltage_2 += squared_voltage_2
        sum_squared_voltage_3 += squared_voltage_3
        sum_squared_voltage_4 += squared_voltage_4
        # sum_squared_voltage_5 += squared_voltage_5
        # sum_squared_voltage_6 += squared_voltage_6

        # Squared current
        sq_ct1 = ct1 * ct1
        sq_ct2 = ct2 * ct2
        sq_ct3 = ct3 * ct3
        sq_ct4 = ct4 * ct4
        # sq_ct5 = ct5 * ct5
        # sq_ct6 = ct6 * ct6
        
        sum_squared_current_ct1 += sq_ct1
        sum_squared_current_ct2 += sq_ct2
        sum_squared_current_ct3 += sq_ct3
        sum_squared_current_ct4 += sq_ct4
        # sum_squared_current_ct5 += sq_ct5
        # sum_squared_current_ct6 += sq_ct6

    avg_raw_current_ct1 = sum_raw_current_ct1 / num_samples
    avg_raw_current_ct2 = sum_raw_current_ct2 / num_samples
    avg_raw_current_ct3 = sum_raw_current_ct3 / num_samples
    avg_raw_current_ct4 = sum_raw_current_ct4 / num_samples
    # avg_raw_current_ct5 = sum_raw_current_ct5 / num_samples
    # avg_raw_current_ct6 = sum_raw_current_ct6 / num_samples
    avg_raw_voltage_1 = sum_raw_voltage_1 / num_samples
    avg_raw_voltage_2 = sum_raw_voltage_2 / num_samples
    avg_raw_voltage_3 = sum_raw_voltage_3 / num_samples
    avg_raw_voltage_4 = sum_raw_voltage_4 / num_samples
    # avg_raw_voltage_5 = sum_raw_voltage_5 / num_samples
    # avg_raw_voltage_6 = sum_raw_voltage_6 / num_samples
    
    real_power_1 = ((sum_inst_power_ct1 / num_samples) - (avg_raw_current_ct1 * avg_raw_voltage_1))  * ct1_scaling_factor * voltage_scaling_factor
    real_power_2 = ((sum_inst_power_ct2 / num_samples) - (avg_raw_current_ct2 * avg_raw_voltage_2))  * ct2_scaling_factor * voltage_scaling_factor 
    real_power_3 = ((sum_inst_power_ct3 / num_samples) - (avg_raw_current_ct3 * avg_raw_voltage_3))  * ct3_scaling_factor * voltage_scaling_factor 
    real_power_4 = ((sum_inst_power_ct4 / num_samples) - (avg_raw_current_ct4 * avg_raw_voltage_4))  * ct4_scaling_factor * voltage_scaling_factor 
    # real_power_5 = ((sum_inst_power_ct5 / num_samples) - (avg_raw_current_ct5 * avg_raw_voltage_5))  * ct5_scaling_factor * voltage_scaling_factor 
    # real_power_6 = ((sum_inst_power_ct6 / num_samples) - (avg_raw_current_ct6 * avg_raw_voltage_6))  * ct6_scaling_factor * voltage_scaling_factor 

    mean_square_current_ct1 = sum_squared_current_ct1 / num_samples 
    mean_square_current_ct2 = sum_squared_current_ct2 / num_samples 
    mean_square_current_ct3 = sum_squared_current_ct3 / num_samples 
    mean_square_current_ct4 = sum_squared_current_ct4 / num_samples 
    # mean_square_current_ct5 = sum_squared_current_ct5 / num_samples 
    # mean_square_current_ct6 = sum_squared_current_ct6 / num_samples 
    mean_square_voltage_1 = sum_squared_voltage_1 / num_samples
    mean_square_voltage_2 = sum_squared_voltage_2 / num_samples
    mean_square_voltage_3 = sum_squared_voltage_3 / num_samples
    mean_square_voltage_4 = sum_squared_voltage_4 / num_samples
    # mean_square_voltage_5 = sum_squared_voltage_5 / num_samples
    # mean_square_voltage_6 = sum_squared_voltage_6 / num_samples

    rms_current_ct1 = sqrt(mean_square_current_ct1 - (avg_raw_current_ct1 * avg_raw_current_ct1)) * ct1_scaling_factor
    rms_current_ct2 = sqrt(mean_square_current_ct2 - (avg_raw_current_ct2 * avg_raw_current_ct2)) * ct2_scaling_factor
    rms_current_ct3 = sqrt(mean_square_current_ct3 - (avg_raw_current_ct3 * avg_raw_current_ct3)) * ct3_scaling_factor
    rms_current_ct4 = sqrt(mean_square_current_ct4 - (avg_raw_current_ct4 * avg_raw_current_ct4)) * ct4_scaling_factor
    # rms_current_ct5 = sqrt(mean_square_current_ct5 - (avg_raw_current_ct5 * avg_raw_current_ct5)) * ct5_scaling_factor
    # rms_current_ct6 = sqrt(mean_square_current_ct6 - (avg_raw_current_ct6 * avg_raw_current_ct6)) * ct6_scaling_factor
    rms_voltage_1     = sqrt(mean_square_voltage_1 - (avg_raw_voltage_1 * avg_raw_voltage_1)) * voltage_scaling_factor
    rms_voltage_2     = sqrt(mean_square_voltage_2 - (avg_raw_voltage_2 * avg_raw_voltage_2)) * voltage_scaling_factor
    rms_voltage_3     = sqrt(mean_square_voltage_3 - (avg_raw_voltage_3 * avg_raw_voltage_3)) * voltage_scaling_factor
    rms_voltage_4     = sqrt(mean_square_voltage_4 - (avg_raw_voltage_4 * avg_raw_voltage_4)) * voltage_scaling_factor
    # rms_voltage_5     = sqrt(mean_square_voltage_5 - (avg_raw_voltage_5 * avg_raw_voltage_5)) * voltage_scaling_factor
    # rms_voltage_6     = sqrt(mean_square_voltage_6 - (avg_raw_voltage_6 * avg_raw_voltage_6)) * voltage_scaling_factor

    # Power Factor
    apparent_power_1 = rms_voltage_1 * rms_current_ct1
    apparent_power_2 = rms_voltage_2 * rms_current_ct2
    apparent_power_3 = rms_voltage_3 * rms_current_ct3
    apparent_power_4 = rms_voltage_4 * rms_current_ct4
    # apparent_power_5 = rms_voltage_5 * rms_current_ct5
    # apparent_power_6 = rms_voltage_6 * rms_current_ct6
    
    try:
        power_factor_1 = real_power_1 / apparent_power_1
    except ZeroDivisionError:
        power_factor_1 = 0
    try:
        power_factor_2 = real_power_2 / apparent_power_2
    except ZeroDivisionError:
        power_factor_2 = 0
    try:
        power_factor_3 = real_power_3 / apparent_power_3
    except ZeroDivisionError:
        power_factor_3 = 0
    try:
        power_factor_4 = real_power_4 / apparent_power_4
    except ZeroDivisionError:
        power_factor_4 = 0
    # try:
    #     power_factor_5 = real_power_5 / apparent_power_5
    # except ZeroDivisionError:
    #     power_factor_5 = 0
    # try:
    #     power_factor_6 = real_power_6 / apparent_power_6
    # except ZeroDivisionError:
    #     power_factor_6 = 0
    

    
    results = {
        'ct1' : {
            'type'      : 'consumption',
            'power'     : real_power_1,
            'current'   : rms_current_ct1,
            'voltage'   : rms_voltage_1,
            'pf'        : power_factor_1
        },
        'ct2' : {
            'type'      : 'consumption',
            'power'     : real_power_2,
            'current'   : rms_current_ct2,
            'voltage'   : rms_voltage_2,
            'pf'        : power_factor_2 
         }
         ,
        'ct3' : {
            'type'      : 'consumption', 
            'power'     : real_power_3,
            'current'   : rms_current_ct3,
            'voltage'   : rms_voltage_3,
            'pf'        : power_factor_3
        },
        'ct4' : {
            'type'      : 'consumption',
            'power'     : real_power_4,         
            'current'   : rms_current_ct4,
            'voltage'   : rms_voltage_4,            
            'pf'        : power_factor_4            
        }
        # ,                                          
        # 'ct5' : {                                   
        #     'type'      : 'consumption',
        #     'power'     : real_power_5,
        #     'current'   : rms_current_ct5,
        #     'voltage'   : rms_voltage_5,
        #     'pf'        : power_factor_5
        # },
        # 'ct6' : {                                   
        #     'type'      : 'consumption',
        #     'power'     : real_power_6,
        #     'current'   : rms_current_ct6,
        #     'voltage'   : rms_voltage_6,
        #     'pf'        : power_factor_6
        #}
        ,
        'voltage' : rms_voltage_1,
    }

    return results

def rebuild_waves(samples, PHASECAL_1, PHASECAL_2, PHASECAL_3, PHASECAL_4):#, PHASECAL_5, PHASECAL_6

    # The following empty lists will hold the phase corrected voltage wave that corresponds to each individual CT sensor.
    wave_1 = []
    wave_2 = []
    wave_3 = []
    wave_4 = []
    # wave_5 = []
    # wave_6 = []

    voltage_samples = samples['voltage']

    wave_1.append(voltage_samples[0])
    wave_2.append(voltage_samples[0])
    wave_3.append(voltage_samples[0])
    wave_4.append(voltage_samples[0])
    # wave_5.append(voltage_samples[0])
    # wave_6.append(voltage_samples[0])
    previous_point = voltage_samples[0]
    
    for current_point in voltage_samples[1:]:
        new_point_1 = previous_point + PHASECAL_1 * (current_point - previous_point)
        new_point_2 = previous_point + PHASECAL_2 * (current_point - previous_point)
        new_point_3 = previous_point + PHASECAL_3 * (current_point - previous_point)
        new_point_4 = previous_point + PHASECAL_4 * (current_point - previous_point)
        # new_point_5 = previous_point + PHASECAL_5 * (current_point - previous_point)
        # new_point_6 = previous_point + PHASECAL_6 * (current_point - previous_point)

        wave_1.append(new_point_1)
        wave_2.append(new_point_2)
        wave_3.append(new_point_3)
        wave_4.append(new_point_4)
        # wave_5.append(new_point_5)
        # wave_6.append(new_point_6)

        previous_point = current_point

    rebuilt_waves = {
        'v_ct1' : wave_1,
        'v_ct2' : wave_2,
        'v_ct3' : wave_3,
        'v_ct4' : wave_4,
        # 'v_ct5' : wave_5,
        # 'v_ct6' : wave_6,
        'voltage' : voltage_samples,
        'ct1' : samples['ct1'],
        'ct2' : samples['ct2'],
        'ct3' : samples['ct3'],
        'ct4' : samples['ct4'],
        # 'ct5' : samples['ct5'],
        # 'ct6' : samples['ct6'],
    }

    return rebuilt_waves


def run_main(print_output=False):
    
    logger.info("... Starting Raspberry Pi Power Monitor")
    logger.info("Press Ctrl-c to quit...")

    api=ApiClient()

    # The following empty dictionaries will hold the respective calculated values at the end of each polling cycle, which are then averaged prior to storing the value to the DB.
    solar_power_values = dict(power=[], pf=[], current=[])
    home_load_values = dict(power=[], pf=[], current=[])
    net_power_values = dict(power=[], current=[])
    ct1_dict = dict(power=[], pf=[], current=[])
    ct2_dict = dict(power=[], pf=[], current=[])
    ct3_dict = dict(power=[], pf=[], current=[])
    ct4_dict = dict(power=[], pf=[], current=[])
    # ct5_dict = dict(power=[], pf=[], current=[])
    # ct6_dict = dict(power=[], pf=[], current=[])
    rms_voltages = []
    i = 0   # Counter for aggregate function
    
    while True:        
        try:

            board_voltage = get_board_voltage()    
            samples = collect_data(2000)
            poll_time = samples['time']            
            ct1_samples = samples['ct1']
            ct2_samples = samples['ct2']
            ct3_samples = samples['ct3']
            ct4_samples = samples['ct4']
            # ct5_samples = samples['ct5']
            # ct6_samples = samples['ct6']
            v_samples = samples['voltage']
            rebuilt_waves = rebuild_waves(samples, ct1_phasecal, ct2_phasecal, ct3_phasecal, ct4_phasecal)#, ct5_phasecal, ct6_phasecal)
            results = calculate_power(rebuilt_waves, board_voltage) 

            # # RMS calculation for phase correction only - this is not needed after everything is tuned. The following code is used to compare the RMS power to the calculated real power. 
            # # Ideally, you want the RMS power to equal the real power when you are measuring a purely resistive load.
            # rms_power_1 = round(results['ct1']['current'] * results['ct1']['voltage'], 2)  # AKA apparent power
            # rms_power_2 = round(results['ct2']['current'] * results['ct2']['voltage'], 2)  # AKA apparent power
            # rms_power_3 = round(results['ct3']['current'] * results['ct3']['voltage'], 2)  # AKA apparent power
            # rms_power_4 = round(results['ct4']['current'] * results['ct4']['voltage'], 2)  # AKA apparent power
            # rms_power_5 = round(results['ct5']['current'] * results['ct5']['voltage'], 2)  # AKA apparent power
            # rms_power_6 = round(results['ct6']['current'] * results['ct6']['voltage'], 2)  # AKA apparent power

            # Prepare values for database storage 
            grid_1_power = results['ct1']['power']    # ct1 Real Power
            grid_2_power = results['ct2']['power']    # ct2 Real Power
            grid_3_power = results['ct3']['power']    # ct3 Real Power
            grid_4_power = results['ct4']['power']    # ct4 Real Power
            # grid_5_power = results['ct5']['power']    # ct5 Real Power
            # grid_6_power = results['ct6']['power']    # ct6 Real Power

            grid_1_current = results['ct1']['current']  # ct1 Current
            grid_2_current = results['ct2']['current']  # ct2 Current
            grid_3_current = results['ct3']['current']  # ct3 Current
            grid_4_current = results['ct4']['current']  # ct4 Current
            # grid_5_current = results['ct5']['current']  # ct5 Current
            # grid_6_current = results['ct6']['current']  # ct6 Current

            # If you are monitoring solar/generator inputs to your panel, specify which CT number(s) you are using, and uncomment the commented lines.
            solar_power = 0
            solar_current = 0
            solar_pf = 0
            # solar_power = results['ct4']['power']
            # solar_current = results['ct4']['current']
            # solar_pf = results['ct4']['pf']
            voltage = results['voltage']

            # Set solar power and current to zero if the solar power is under 20W.
            if solar_power < 20:
                solar_power = 0
                solar_current = 0
                solar_pf = 0
            
            # Determine if the system is net producing or net consuming right now by looking at the two panel mains.
            # Since the current measured is always positive, we need to add a negative sign to the amperage value if we're exporting power.
            if grid_1_power < 0:
                grid_1_current = grid_1_current * -1
            if grid_2_power < 0:
                grid_2_current = grid_2_current * -1
            if solar_power > 0:
                solar_current = solar_current * -1

            # Unless your specific panel setup matches mine exactly, the following four lines will likely need to be re-written:
            home_consumption_power = grid_1_power + grid_2_power + solar_power#+ grid_3_power + grid_4_power + grid_5_power + grid_6_power 
            net_power = home_consumption_power - solar_power
            home_consumption_current = grid_1_current + grid_2_current # + grid_3_current + grid_4_current + grid_5_current + grid_6_current
            net_current = grid_1_current + grid_2_current #+ grid_3_current + grid_4_current + grid_5_current + grid_6_current 

            if net_power < 0:
                current_status = "Producing"                                
            else:
                current_status = "Consuming"                

            # Average 2 readings before sending to db
            if i < 2:
                solar_power_values['power'].append(solar_power)
                solar_power_values['current'].append(solar_current)
                solar_power_values['pf'].append(solar_pf)

                home_load_values['power'].append(home_consumption_power)
                home_load_values['current'].append(home_consumption_current)
                net_power_values['power'].append(net_power)
                net_power_values['current'].append(net_current)
                
                ct1_dict['power'].append(results['ct1']['power'])
                ct1_dict['current'].append(results['ct1']['current'])
                ct1_dict['pf'].append(results['ct1']['pf'])
                ct2_dict['power'].append(results['ct2']['power'])
                ct2_dict['current'].append(results['ct2']['current'])
                ct2_dict['pf'].append(results['ct2']['pf'])
                ct3_dict['power'].append(results['ct3']['power'])
                ct3_dict['current'].append(results['ct3']['current'])
                ct3_dict['pf'].append(results['ct3']['pf'])
                ct4_dict['power'].append(results['ct4']['power'])
                ct4_dict['current'].append(results['ct4']['current'])
                ct4_dict['pf'].append(results['ct4']['pf'])
                # ct5_dict['power'].append(results['ct5']['power'])
                # ct5_dict['current'].append(results['ct5']['current'])
                # ct5_dict['pf'].append(results['ct5']['pf'])
                # ct6_dict['power'].append(results['ct6']['power'])
                # ct6_dict['current'].append(results['ct6']['current'])
                # ct6_dict['pf'].append(results['ct6']['pf'])
                rms_voltages.append(voltage)
                i += 1
            
            
            else:   # Calculate the average, send the result to InfluxDB, and reset the dictionaries for the next 2 sets of data.
                data={'ct1':ct1_dict,
                'ct2':ct2_dict,
                'ct3':ct2_dict,
                'ct4':ct2_dict,
                # 'ct5':ct2_dict,
                # 'ct6':ct2_dict
                }

                
                if(print_output):
                    print_results(results)
                else:
                    api.AddBatch(results)

                solar_power_values = dict(power=[], pf=[], current=[])
                home_load_values = dict(power=[], pf=[], current=[])
                net_power_values = dict(power=[], current=[])
                ct1_dict = dict(power=[], pf=[], current=[])
                ct2_dict = dict(power=[], pf=[], current=[])
                ct3_dict = dict(power=[], pf=[], current=[])
                ct4_dict = dict(power=[], pf=[], current=[])
                # ct5_dict = dict(power=[], pf=[], current=[])
                # ct6_dict = dict(power=[], pf=[], current=[])
                rms_voltages = []
                i = 0

                # if logger.handlers[0].level == 10:
                #     t = PrettyTable(['', 'ct1', 'ct2'])#, 'ct3', 'ct4', 'ct5', 'ct6'])
                #     t.add_row(['Watts', round(results['ct1']['power'], 3), round(results['ct2']['power'], 3))#, round(results['ct3']['power'], 3), round(results['ct4']['power'], 3), round(results['ct5']['power'], 3), round(results['ct6']['power'], 3)])
                #     t.add_row(['Current', round(results['ct1']['current'], 3), round(results['ct2']['current'], 3))#, round(results['ct3']['current'], 3), round(results['ct4']['current'], 3), round(results['ct5']['current'], 3), round(results['ct6']['current'], 3)])
                #     t.add_row(['P.F.', round(results['ct1']['pf'], 3), round(results['ct2']['pf'], 3))#, round(results['ct3']['pf'], 3), round(results['ct4']['pf'], 3), round(results['ct5']['pf'], 3), round(results['ct6']['pf'], 3)])
                #     t.add_row(['Voltage', round(results['voltage'], 3), ''])#, '', '', '', ''])
                #     s = t.get_string()
                #     logger.debug('\n' + s)
                if(print_output):
                    sleep(5)
                else:
                    sleep(60)

        except KeyboardInterrupt:
            
            sys.exit()

def print_results(results):
    t = PrettyTable(['', 'ct1', 'ct2', 'ct3', 'ct4'])#, 'ct5', 'ct6'])
    t.add_row(['Watts', round(results['ct1']['power'], 3), round(results['ct2']['power'], 3), round(results['ct3']['power'], 3), round(results['ct4']['power'], 3)])#, round(results['ct5']['power'], 3), round(results['ct6']['power'], 3)])
    t.add_row(['Current', round(results['ct1']['current'], 3), round(results['ct2']['current'], 3), round(results['ct3']['current'], 3), round(results['ct4']['current'], 3)])#, round(results['ct5']['current'], 3), round(results['ct6']['current'], 3)])
    t.add_row(['P.F.', round(results['ct1']['pf'], 3), round(results['ct2']['pf'], 3), round(results['ct3']['pf'], 3), round(results['ct4']['pf'], 3)])#, round(results['ct5']['pf'], 3), round(results['ct6']['pf'], 3)])
    t.add_row(['Voltage', round(results['voltage'], 3), '', '', ''])#])
    s = t.get_string()

    print(t)
    logger.debug(s)


def get_ip():
    # This function acquires your Pi's local IP address for use in providing the user with a copy-able link to view the charts.
    # It does so by trying to connect to a non-existent private IP address, but in doing so, it is able to detect the IP address associated with the default route.
    s = socket(AF_INET, SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = None
    finally:
        s.close()
    return IP


if __name__ == '__main__':
    print("Entered Main")

    # Backup config.py file
    try:
        copyfile('config.py', 'config.py.backup')
    except FileNotFoundError:
        logger.info("Could not create a backup of config.py file.")
    
    if len(sys.argv) > 1:
        MODE = sys.argv[1]
        if MODE == 'debug' or MODE == 'phase':
            try:
                title = sys.argv[2]
            except IndexError:
                title = None
        # Create the data/samples directory:
        try:
            os.makedirs('data/samples/')
        except FileExistsError:
            pass
    else:
        MODE = None

    if not MODE or MODE=="print":
        # Try to establish a connection to the DB for 5 seconds:
        if(MODE=="print"):
            run_main(True)
        else:
            run_main()

    else:
        # Program launched in one of the non-main modes. Increase logging level.
        logger.setLevel(logging.DEBUG)
        logger.handlers[0].setLevel(logging.DEBUG)      
        if 'help' in MODE.lower() or '-h' in MODE.lower():

            logger.info("See the project Wiki for more detailed usage instructions: https://github.com/David00/rpi-power-monitor/wiki")
            logger.info(dedent("""Usage:
                Start the program:                                  python3 power-monitor.py

                Collect raw data and build an interactive plot:     python3 power-monitor.py debug "chart title here" 

                Launch interactive phase correction mode:           python3 power-monitor.py phase

                Start the program like normal, but print all        python3 power-monitor.py terminal
                readings to the terminal window
                """))

        if MODE.lower() == 'debug':
            # This mode is intended to take a look at the raw CT sensor data.  It will take 2000 samples from each CT sensor, plot them to a single chart, write the chart to an HTML file located in /var/www/html/, and then terminate.
            # It also stores the samples to a file located in ./data/samples/last-debug.pkl so that the sample data can be read when this program is started in 'phase' mode.

            # Time sample collection
            start = timeit.default_timer()
            samples = collect_data(2000)
            stop = timeit.default_timer()
            duration = stop - start

            # Calculate Sample Rate in Kilo-Samples Per Second.
            sample_count = sum([ len(samples[x]) for x in samples.keys() if type(samples[x]) == list ])
            
            sample_rate = round((sample_count / duration) / 1000, 2)

            logger.debug(f"Finished Collecting Samples. Sample Rate: {sample_rate} KSPS")
            ct1_samples = samples['ct1']
            ct2_samples = samples['ct2']
            ct3_samples = samples['ct3']
            ct4_samples = samples['ct4']
            # ct5_samples = samples['ct5']
            # ct6_samples = samples['ct6']
            v_samples = samples['voltage']

            # Save samples to disk
            with open('data/samples/last-debug.pkl', 'wb') as f:
                pickle.dump(samples, f)

            if not title:
                title = input("Enter the title for this chart: ")
            
            title = title.replace(" ","_")
            logger.debug("Building plot.")
            plot_data(samples, title, sample_rate=sample_rate)
            ip = get_ip()
            if ip:
                logger.info(f"Chart created! Visit http://{ip}/{title}.html to view the chart. Or, simply visit http://{ip} to view all the charts created using 'debug' and/or 'phase' mode.")
            else:
                logger.info("Chart created! I could not determine the IP address of this machine. Visit your device's IP address in a webrowser to view the list of charts you've created using 'debug' and/or 'phase' mode.")

        if MODE.lower() == 'phase':
            # This mode is intended to be used for correcting the phase error in your CT sensors. Please ensure that you have a purely resistive load running through your CT sensors - that means no electric fans and no digital circuitry!

            PF_ROUNDING_DIGITS = 3      # This variable controls how many decimal places the PF will be rounded

            while True:
                try:    
                    ct_num = int(input("\nWhich CT number are you calibrating? Enter the number of the CT label [1 - 6]: "))
                    if ct_num not in range(1, 7):
                        logger.error("Please choose from CT numbers 1, 2, 3, 4, 5, or 6.")
                    else:
                        ct_selection = f'ct{ct_num}'
                        break
                except ValueError:
                    logger.error("Please enter an integer! Acceptable choices are: 1, 2, 3, 4, 5, 6.")

            
            cont = input(dedent(f"""
                #------------------------------------------------------------------------------#
                # IMPORTANT: Make sure that current transformer {ct_selection} is installed over          #
                #            a purely resistive load and that the load is turned on            #
                #            before continuing with the calibration!                           #
                #------------------------------------------------------------------------------#

                Continue? [y/yes/n/no]: """))
                

            if cont.lower() in ['n', 'no']:
                logger.info("\nCalibration Aborted.\n")
                sys.exit()

            samples = collect_data(2000)
            rebuilt_wave = rebuild_wave(samples[ct_selection], samples['voltage'], ct_phase_correction[ct_selection])
            board_voltage = get_board_voltage()
            results = check_phasecal(rebuilt_wave['ct'], rebuilt_wave['new_v'], board_voltage)

            # Get the current power factor and check to make sure it is not negative. If it is, the CT is installed opposite to how it should be.
            pf = results['pf']
            initial_pf = pf  
            if pf < 0:
                logger.info(dedent('''
                    Current transformer is installed backwards. Please reverse the direction that it is attached to your load. \n
                    (Unclip it from your conductor, and clip it on so that the current flows the opposite direction from the CT's perspective) \n
                    Press ENTER to continue when you've reversed your CT.'''))
                input("[ENTER]")
                # Check to make sure the CT was reversed properly by taking another batch of samples/calculations:
                samples = collect_data(2000)
                rebuilt_wave = rebuild_wave(samples[ct_selection], samples['voltage'], 1)
                board_voltage = get_board_voltage()
                results = check_phasecal(rebuilt_wave['ct'], rebuilt_wave['new_v'], board_voltage)
                pf = results['pf']
                if pf < 0:
                    logger.info(dedent("""It still looks like the current transformer is installed backwards.  Are you sure this is a resistive load?\n
                        Please consult the project documentation on https://github.com/david00/rpi-power-monitor/wiki and try again."""))
                    sys.exit()

            # Initialize phasecal values
            new_phasecal = ct_phase_correction[ct_selection]
            previous_pf = 0
            new_pf = pf

            samples = collect_data(2000)
            board_voltage = get_board_voltage()
            best_pfs = find_phasecal(samples, ct_selection, PF_ROUNDING_DIGITS, board_voltage)
            avg_phasecal = sum([x['cal'] for x in best_pfs]) / len([x['cal'] for x in best_pfs])
            logger.info(f"Please update the value for {ct_selection} in ct_phase_correction in config.py with the following value: {round(avg_phasecal, 8)}")
            logger.info("Please wait... building HTML plot...")
            # Get new set of samples using recommended phasecal value
            samples = collect_data(2000)
            rebuilt_wave = rebuild_wave(samples[ct_selection], samples['voltage'], avg_phasecal)

            report_title = f'CT{ct_num}-phase-correction-result'
            plot_data(rebuilt_wave, report_title, ct_selection)
            logger.info(f"file written to {report_title}.html")

        if MODE.lower() == "terminal":
            # This mode will read the sensors, perform the calculations, and print the wattage, current, power factor, and voltage to the terminal.
            # Data is stored to the database in this mode!
            logger.debug("... Starting program in terminal mode")
            
            
            run_main()

