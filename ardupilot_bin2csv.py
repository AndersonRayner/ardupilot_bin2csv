from pymavlink import DFReader
import os
import glob
import datetime

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
import csv

# Import Folder
root_directory = '/data'
root_directory = '/media/matt/OS/Users/matt/Downloads/for_aerospaceCorp/'
root_directory = '/home/matt/Documents/aerospace_corp/2024-07-25_NorthField/data/uav'

def bin2csv(log_filename):

    # Import Log
    print(f"Processing {log_filename}")
    if log_filename.endswith('.log'):
        log = DFReader.DFReader_text(log_filename)
    else:
        log = DFReader.DFReader_binary(log_filename)

    # File was opened, create directory for saving data
    output_path = os.path.join(os.path.splitext(log_filename)[0])
    if not os.path.exists(os.path.join(output_path,'csv')):
        os.makedirs(os.path.join(output_path,'csv'))

    # Save parameter files
    print(f"\tSaving parameter file")
    fid = open(os.path.join(output_path,'params.txt'), 'w')
    timestamp = datetime.datetime.fromtimestamp(log.clock.timebase).strftime("%Y-%m-%d-%H-%M-%S")
    print(f"# Parameters exported from {log_filename}\n# {timestamp}\n#",file=fid)
    for param, value in sorted(log.params.items()) :
        print(f"{param}={value}",file=fid)
    fid.close()
    print(f"\t\t{len(log.params)} parameters written")

    # Save each data stream
    print('\tImporting data streams')
    skip_fmt_name = ['FMT','PARM','UNIT','MULT','FMTU']
    fid = {}
    line = []

    while line is not None :

        # Read the line
        line = log._parse_next()

        # Check for empty lines (assume end of file)
        if line is None :
            continue

        # Check for non-data lines
        if line.fmt.name in skip_fmt_name :
            continue

        # Handle multiple instances of sensors
        if line.fmt.instance_field is None :
            channel_name = line.fmt.name
        else :
            channel_name = line.fmt.name + '_' + str(line._elements[line.fmt.colhash[line.fmt.instance_field]])

        # Handle multipliers
        if line._apply_multiplier :
            for idx, multi in enumerate(line.fmt.msg_mults):
                if multi is not None :
                    line._elements[idx] = line._elements[idx]*multi

        # Open a text file if not already open
        if channel_name not in fid :

            # Open the file
            fid[channel_name] = open(os.path.join(output_path,'csv',channel_name+'.csv'), 'w')

            # Write the header
            print(*line._fieldnames, sep=', ',file=fid[channel_name])

        # Write the data
        print(*line._elements, sep=', ',file=fid[channel_name])

        # Update the user
        if log.remaining % 10000 == 0 :
            print(f"\033[K\t\t{log.remaining} lines remaining",end='\r')

    # Close open files
    for files in fid :
        fid[files].close

    # All done
    print(f"\033[K\t\tDone")
    return

# Helper functions
def lla2enu(lla, lla0=None):
    
    # Latitude / Longitude / Altitude to East / North / Up

    if lla0 is None :
        lla0 = [lla[0][0],lla[1][0],lla[2][0]]

    # Convert lat/lon to NE
    LOCATION_SCALING_FACTOR = 111318.84502145034  # deg to m
    DEG_TO_RAD = math.pi / 180.0

    enu = lla.copy()

    enu[1] = (lla[0] - lla0[0]) * LOCATION_SCALING_FACTOR
    enu[0] = (lla[1] - lla0[1]) * LOCATION_SCALING_FACTOR * max(math.cos(lla0[0] * DEG_TO_RAD), 0.01)
    enu[2] = (lla[2] - lla0[2])

    return enu

from datetime import datetime, timedelta, timezone

def gps_to_unix(gps_week, gps_seconds):
    # Check at https://www.unixtimestamp.com/

    # Define the GPS epoch
    secs_unix2gps = 315964800
    secs_leapSeconds = 18

    # Calculate the total number of seconds since the GPS epoch
    unix = secs_unix2gps + secs_leapSeconds + \
           gps_week * 7 * 24 * 60 * 60 + gps_seconds

    return unix

# Make plots
def plot_data(log_filename) :

    # Create paths
    data_path = os.path.join(os.path.splitext(log_filename)[0],'csv')
    output_path = os.path.join(os.path.splitext(log_filename)[0],'images')
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Load data
    data = pd.read_csv(os.path.join(data_path,'ATT.csv'))
    print(data.head())

    # Plot the data
    t_offset = data['TimeUS'].iloc[0]
    data['TimeUS'] = data['TimeUS'] - t_offset

    fig, ax = plt.subplots(nrows=2,ncols=2, figsize=(18, 8))

    # Roll / Pitch
    ax[0,0].plot(data['TimeUS'].values/1e6, data[' Roll'].values, linestyle='-', color='b', label='Roll')
    ax[0,0].plot(data['TimeUS'].values/1e6, data[' DesRoll'].values, linestyle='--', linewidth=0.5, color='k', label='Desired Roll')
    ax[0,0].plot(data['TimeUS'].values/1e6, data[' Pitch'].values, linestyle='-', color='r', label='Pitch')
    ax[0,0].plot(data['TimeUS'].values/1e6, data[' DesPitch'].values, linestyle='--', linewidth=0.5, color='k', label='Desired Pitch')
    ax[0,0].set_xlabel('Time [ s ]')
    ax[0,0].set_ylabel('Roll/Pitch [ deg ]')
    ax[0,0].set_title('Attitude Tracking')
    ax[0,0].legend()
    ax[0,0].grid(True)

    # Yaw
    ax[1,0].plot(data['TimeUS'].values/1e6, data[' Yaw'].values, linestyle='-', color='r', label='Yaw')
    ax[1,0].plot(data['TimeUS'].values/1e6, data[' DesYaw'].values, linestyle='--', linewidth=0.5, color='k', label='Desired Yaw')
    ax[1,0].set_xlabel('Yaw [ s ]')
    ax[1,0].set_ylabel('Yaw [ deg ]')
    ax[1,0].legend()
    ax[1,0].grid(True)

    # Altitude
    data = pd.read_csv(os.path.join(data_path,'CTUN.csv'))
    data['TimeUS'] = data['TimeUS'] - t_offset

    print(data.head())
    ax[0,1].plot(data['TimeUS'].values/1e6, data[' Alt'].values, linestyle='-', color='r', label='Altitude')
    ax[0,1].plot(data['TimeUS'].values/1e6, data[' DAlt'].values, linestyle='--', linewidth=0.5, color='k', label='Desired Altitude')
    ax[0,1].set_xlabel('Time [ s ]')
    ax[0,1].set_ylabel('Altitude [ m ]')
    ax[0,1].legend()
    ax[0,1].grid(True)

    # Position
    data = pd.read_csv(os.path.join(data_path,'POS.csv'))
    data['TimeUS'] = data['TimeUS'] - t_offset
    data['Time'] = data['TimeUS']/1e6

    print(data.head())

    lla0 = [data[' Lat'].values[0], data[' Lng'].values[0], data[' Alt'].values[0]]

    enu = lla2enu([data[' Lat'].values, data[' Lng'].values, data[' Alt'].values],lla0=lla0)
    ax[1,1].plot(enu[0], enu[1], linestyle='-', color='k', label='Position')
    ax[1,1].plot(enu[0][0], enu[1][0], marker='x', color='r', label='Launch')
    ax[1,1].plot(enu[0][-1], enu[1][-1], marker='o', color='g', label='Land')

    # Sensors
    radar_lla = [34.13438310, -118.12710082, data[' Alt'].values[0]]
    lidar_lla = [34.13439824, -118.12710594, data[' Alt'].values[0]]
    radar_enu =  lla2enu(radar_lla,lla0=lla0)
    lidar_enu =  lla2enu(lidar_lla,lla0=lla0)
    ax[1,1].plot(radar_enu[0], radar_enu[1], marker='^', color='b', linestyle='None', label='RaDAR')
    ax[1,1].plot(lidar_enu[0], lidar_enu[1], marker='v', color='b', linestyle='None', label='LiDAR')
    ax[1,1].set_xlabel('East [ m ]')
    ax[1,1].set_ylabel('North [ m ]')
    ax[1,1].grid(True)
    ax[1,1].legend()

    # Align the time vector to UTC
    gps_data = pd.read_csv(os.path.join(data_path,'GPS_0.csv'))
    gps_data['TimeUS'] = gps_data['TimeUS'] - t_offset
    gps_data['Time'] = gps_data['TimeUS']/1e6
    gps_data['unix'] = gps_to_unix(gps_data[' GWk'].values, gps_data[' GMS'].values/1000)
    data['unix'] = np.interp(x=data['Time'].values, xp=gps_data['Time'].values, fp=gps_data['unix'].values)

    # Adjust layout to prevent overlap
    plt.tight_layout()
    ax[1,1].set_aspect('equal', 'box')

    # Create output data
    headers = ['unix [ s ]','Time [ s ]',
               'Lat [ dd.dd ]', 'Lon [ dd.dd ]', 'Alt [ m ]',
               'E [ m ]', 'N [ m ]', 'U [ m ]']
    
    info = f'lat0: {lla0[0]}, lon0: {lla0[1]}, alt0: {lla0[2]}\n'
    info = info + f'radar_lat: {radar_lla[0]}, radar_lon: {radar_lla[1]}, radar_alt: {radar_lla[2]}\n'
    info = info + f'lidar_lat: {lidar_lla[0]}, lidar_lon: {lidar_lla[1]}, lidar_alt: {lidar_lla[2]}\n'
    info = info + f'radar_E: {radar_enu[0]}, radar_N: {radar_enu[1]}, radar_U: {radar_enu[2]}\n'
    info = info + f'lidar_E: {lidar_enu[0]}, lidar_N: {lidar_enu[1]}, lidar_U: {lidar_enu[2]}\n'
    info = info + '#--------------\n'
    output = [
        data['unix'].values,
        data['Time'].values,
        data[' Lat'].values,
        data[' Lng'].values,
        data[' Alt'].values,
        enu[0],
        enu[1],
        enu[2],
    ]
    output = list(zip(*output))

    # File path where the CSV file will be saved
    csv_file = os.path.join(os.path.splitext(log_filename)[0],os.path.splitext(os.path.basename(log_filename))[0]+'.csv')

    # Writing to the CSV file
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)

        # Header
        file.write(info)

        # Column labels
        writer.writerow(headers)

        # Data
        writer.writerows(output)


    exit (0)
    # Show the plot
    # plt.show()
    # exit (0)

    # Save the plot to a PNG file
    plt.savefig(os.path.join(output_path,'ATT.png'))

if __name__ == "__main__":

    # Find all *.bin files
    log_files = sorted(
        glob.glob(os.path.join(root_directory, "**/*.bin"), recursive=True) +
        glob.glob(os.path.join(root_directory, "**/*.BIN"), recursive=True)
    )

    # Import the file
    for ii in range(len(log_files)):
        print(f'{ii+1:2d}/{len(log_files):2d} | ', end='')
        # bin2csv(log_files[ii])
        plot_data(log_files[ii]) 

    # All done
    print("All log files imported!")
    exit (0)