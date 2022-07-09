import logging
import sys

# Create basic logger
logger = logging.getLogger('power_monitor')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s : %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
ch.setFormatter(formatter)
logger.addHandler(ch)


# Using a multimeter, measure the voltage of the receptacle where your 9V AC transformer will plug into. Enter the measured value below.
GRID_VOLTAGE = 121.7
# Using a multimeter, measure the output voltage of your AC transformer. Using the value on the label is not ideal and will lead to greater accuracy in the calculations.
AC_TRANSFORMER_OUTPUT_VOLTAGE = 8.64




# Define Variables
ct1_channel = 6            # 3.5mm Input #1  

ct2_channel = 7             # 3.5mm Input #2           
ct3_channel = 2             # Blue Pair             
ct4_channel = 3             # Brown Pair           
ct5_channel = 4              # Orange Pair 
board_voltage_channel =  0  # Board voltage ~3.3V
v_sensor_channel = 5        # 9V AC Voltage channel
ct6_channel = 1              # Green Pair       

# The values from running the software in "phase" mode should go below!
ct_phase_correction = {
    'ct1' : 1.04564589,
    'ct2' : 1.13240952,
    'ct3' : 1,
    'ct4' : 1,
    'ct5' : 1,
    'ct6' : 1,
}

# AFTER phase correction is completed, these values are used in the final calibration for accuracy. See the documentation for more information.
accuracy_calibration = {
    'ct1' : .97,
    'ct2' : .97,
    'ct3' : 1,
    'ct4' : 1,
    'ct5' : 1,
    'ct6' : 1,
    'AC'  : 1,
}