from datetime import datetime
import pytz
import json

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