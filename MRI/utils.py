from datetime import datetime
from pydicom import dcmread
import pytz
import json
import os
import pandas as pd
import magic


def get_time():
    # Set timezone as GMT+05:30 IST
    time_zone = pytz.timezone('Asia/Kolkata')

    # Get current time
    current_time = datetime.now(time_zone)

    # Format the time as YEAR-MM-DD HH:MM:SS
    formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S')

    return formatted_time

def read_json(json_path: str):
    """Reads and parses a JSON file."""
    try:
        with open(json_path, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise ValueError(f"Error reading JSON file {json_path}: {str(e)}")

def extract_acquisition_times(files):
    """
    Extracts acquisition times from a list of DICOM files.

    Parameters:
        files (list): List of file paths.

    Returns:
        pd.DataFrame: DataFrame containing file paths and acquisition times.
    """
    dcm_time = []

    for file in files:
        if os.path.isdir(file):
            continue

        if magic.from_file(file, mime=True) == 'application/dicom':
            try:
                ds = dcmread(file)
                acq_time = ds.get('AcquisitionTime', None)

                if acq_time:
                    dcm_time.append([file, acq_time])

            except Exception as e:
                print(f"Error reading {file}: {e}")

    return pd.DataFrame(dcm_time, columns=['File', 'Time']).sort_values(by='Time')

def compute_time_difference(time1: str, time2: str):
    """
    Computes the difference between two times given in HHMMSS.SSSSSS format.

    Parameters:
        time1 (str): Start time in the format 'HHMMSS.SSSSSS'
        time2 (str): End time in the format 'HHMMSS.SSSSSS'

    Returns:
        str: Time difference in HH:MM:SS.SSSSSS format
    """
    time_format = "%H%M%S.%f"
    t1 = datetime.strptime(time1, time_format)
    t2 = datetime.strptime(time2, time_format)

    return str(t2 - t1)