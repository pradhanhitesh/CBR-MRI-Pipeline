import os
import subprocess
from typing import List, Optional

def dcm2nifti(input_folder: str, cmd: Optional[List[str]] = None):
    """
    Converts DICOM files to NIfTI format using dcm2niix.
    Source: https://github.com/rordenlab/dcm2niix
    """

    subject_id = os.path.basename(input_folder)
    output_folder = os.path.join(os.getcwd(), 'temp', subject_id)
    os.makedirs(output_folder, exist_ok=True)

    # Validation Checks
    if cmd is None:
        cmd = ['dcm2niix', '-f', '%i_%p', '-o', output_folder, input_folder]
    
    if not os.path.isdir(input_folder):
        raise FileNotFoundError(f"Input folder '{input_folder}' does not exist.")
    
    # Execute dcm2niix
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = proc.communicate()
    
    # Save command output
    with open(os.path.join(output_folder, "dcm2niix_cmd_output.txt"), "w") as out_file:
        out_file.write(output.decode('utf-8'))
    
    # Save command errors
    if error:
        with open(os.path.join(output_folder, "dcm2niix_cmd_error.txt"), "w") as err_file:
            err_file.write(error.decode('utf-8'))
    
    return output, error