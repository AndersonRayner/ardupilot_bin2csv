from pymavlink import DFReader
import os

def bin2csv(log_filename):

    # Import Log
    print(f"Importing {log_filename}")
    if log_filename.endswith('.log'):
        log = DFReader.DFReader_text(log_filename)
    else:
        log = DFReader.DFReader_binary(log_filename)

    # File was opened, create directory for saving data
    output_path = os.path.join(os.path.splitext(log_filename)[0])
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Save each data stream
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
            print(f"\tFound {channel_name}")
            fid[channel_name] = open(os.path.join(output_path,channel_name+'.csv'), 'w')

            # Write the header
            print(*line._fieldnames, sep=', ',file=fid[channel_name])

        # Write the data
        print(*line._elements, sep=', ',file=fid[channel_name])

    # Close open files
    for files in fid :
        fid[files].close

    # Save the parameters
    print(f"\nSaving parameter file (not yet implemented)")

    # All done
    return

if __name__ == "__main__":

    # Import the file
    bin2csv('input_file/ardupilot.bin')

    # All done
    print("Done!")
    exit (0)