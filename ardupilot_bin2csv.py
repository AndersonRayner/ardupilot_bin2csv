from pymavlink import DFReader
import os
import glob
import datetime

import pandas as pd
import matplotlib.pyplot as plt

# Import Folder
root_directory = '/data'
# root_directory = '/media/matt/OS/Users/matt/Downloads/for_aerospaceCorp/'

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
    ax[0,0].plot(data['TimeUS'].values/1e6, data[' DesRoll'].values, linestyle='-', color='b', label='Desired Roll')
    ax[0,0].plot(data['TimeUS'].values/1e6, data[' Roll'].values, linestyle='--', color='b', label='Roll')
    ax[0,0].plot(data['TimeUS'].values/1e6, data[' DesPitch'].values, linestyle='-', color='r', label='Desired Pitch')
    ax[0,0].plot(data['TimeUS'].values/1e6, data[' Pitch'].values, linestyle='--', color='r', label='Pitch')
    ax[0,0].set_xlabel('Time [ s ]')
    ax[0,0].set_ylabel('Attitude [ deg ]')
    ax[0,0].set_title('Attitude Tracking')
    ax[0,0].legend()
    ax[0,0].grid(True)

    # Yaw
    ax[1,0].plot(data['TimeUS'].values/1e6, data[' DesYaw'].values, linestyle='-', color='r', label='Desired Yaw')
    ax[1,0].plot(data['TimeUS'].values/1e6, data[' Yaw'].values, linestyle='--', color='r', label='Yaw')
    ax[1,0].set_xlabel('Time [ s ]')
    ax[1,0].set_ylabel('Attitude [ deg ]')
    ax[1,0].legend()
    ax[1,0].grid(True)

    # Altitude
    data = pd.read_csv(os.path.join(data_path,'CTUN.csv'))
    data['TimeUS'] = data['TimeUS'] - t_offset

    print(data.head())
    ax[0,1].plot(data['TimeUS'].values/1e6, data[' DAlt'].values, linestyle='-', color='r', label='Desired Altitude')
    ax[0,1].plot(data['TimeUS'].values/1e6, data[' Alt'].values, linestyle='--', color='r', label='Altitude')
    ax[0,1].set_xlabel('Time [ s ]')
    ax[0,1].set_ylabel('Altitude [ m ]')
    ax[0,1].legend()
    ax[0,1].grid(True)

    # Position
    data = pd.read_csv(os.path.join(data_path,'POS.csv'))
    data['TimeUS'] = data['TimeUS'] - t_offset

    print(data.head())
    ax[1,1].plot(data[' Lat'].values/1e6, data[' Lng'].values, linestyle='-', color='r', label='Position')
    ax[1,1].set_xlabel('Longitude [ dd.dd ]')
    ax[1,1].set_ylabel('Latitude [ dd.dd ]')
    ax[1,1].grid(True)


    # Adjust layout to prevent overlap
    plt.tight_layout()

    # Save the plot to a PNG file
    plt.savefig(os.path.join(output_path,'ATT.png'))

    # exit (0)


if __name__ == "__main__":

    # Find all *.bin files
    log_files = sorted(
        glob.glob(os.path.join(root_directory, "**/*.bin"), recursive=True) +
        glob.glob(os.path.join(root_directory, "**/*.BIN"), recursive=True)
    )

    # Import the file
    for ii in range(len(log_files)):
        print(f'{ii+1:2d}/{len(log_files):2d} | ', end='')
        bin2csv(log_files[ii])
        plot_data(log_files[ii]) 

    # All done
    print("All log files imported!")
    exit (0)