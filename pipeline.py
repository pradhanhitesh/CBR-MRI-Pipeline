import subprocess
import os
from typing import List, Optional

def dcm_convert(input_folder: str, cmd: Optional[List[str]] = None):
    # Configure output_folder
    subject_id = input_folder.split("/")[-1]
    output_folder = os.path.join(os.getcwd(), 'temp', subject_id)
    os.makedirs(output_folder, exist_ok=True)

    # Configure dcm2niix command
    if cmd is None:
        cmd = ['dcm2niix', '-f', '%i_%p', '-o', output_folder, input_folder]
    
    # Validation checks
    if not isinstance(cmd, list) or not all(isinstance(i, str) for i in cmd):
        raise TypeError("cmd must be a list of strings. For example, ['dcm2niix', '-z', 'y', '-o', 'output/folder/path', 'dicom/folder/path']")

    if not os.path.isdir(input_folder):
        raise FileNotFoundError(f"Input folder '{input_folder}' does not exist.")

    if not os.path.isdir(output_folder):
        os.makedirs(output_folder, exist_ok=True)

    # Execute dcm2niix using subprocess
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = proc.communicate()

    # Save output
    with open(os.path.join(output_folder, "dcm2niix_cmd_output.txt"), "w") as out_file:
        out_file.write(output.decode('utf-8'))

    # Save error, only if error occurs
    if len(error) > 0:
        with open(os.path.join(output_folder, "dcm2niix_cmd_error.txt"), "w") as err_file:
            err_file.write(error.decode('utf-8'))

    return output, error


import json
import glob
import pandas as pd
import shutil

def read_json(json_path):
        """
        Read and parse the JSON file containing modality templates.

        Returns:
        - dict: Parsed JSON data.

        Raises:
        - ValueError: If the file is not found, contains invalid JSON, or another error occurs.
        """
        try:
            with open(json_path, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            raise ValueError(f"File not found: {json_path}")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in file: {json_path}")
        except Exception as e:
            raise ValueError(f"An unexpected error occurred: {str(e)}")

data = read_json("modalities.json")

def compile_modalities(input_filepath: str):
    all_files = sorted(glob.glob(f"{input_filepath}/*.json"))

    modal_files = {}
    modal_data = []

    for key, value in data.items():
        for file in all_files:
            if value[0] in file:
                json_file = read_json(file)
                image_type = json_file.get('ImageType', [])

                if 'ORIGINAL' in image_type:
                    modal_files[key] = file
                    modal_data.append([key, file.replace('.json', '.nii'), 'ORIGINAL', json_file['AcquisitionTime']])
                    break  # Exit loop once ORIGINAL is found for this key

    for key, value in data.items():
        if key in modal_files:  # Skip if ORIGINAL already exists
            continue
        
        for file in all_files:
            if value[0] in file:
                json_file = read_json(file)
                if 'DERIVED' in json_file.get('ImageType', []):
                    modal_files[key] = file
                    modal_data.append([key, file.replace('.json', '.nii'), 'DERIVED', json_file['AcquisitionTime']])
                    break  # Exit loop once DERIVED is found for this key
    
    # Save modal data
    modal_data = pd.DataFrame(modal_data, columns=['Modality', 'Filepath', 'Type', 'AcqTime']).sort_values(by='AcqTime').reset_index(drop=True)
    modal_data.to_csv(os.path.join(input_filepath, 'modal_data.csv'))

    return modal_data

import os
import shutil

def organize_qc_data(session_path, modal_data):
    """
    Organizes and copies QC files for given modalities into structured directories.

    Parameters:
        session_path (str): Path to the session folder (e.g., 'temp/ACP003_V1').
        modal_data (DataFrame): DataFrame containing 'Modality' and 'Filepath' columns.
    """
    qc_modals = {
        'T1': ('anat', 'sub-001_T1w'),
        'fMRI': ('func', 'sub-001_task-rest_bold'),
        'DTI20': ('dwi', 'sub-001_dwi'),
        'DTI64': ('dwi', 'sub-001_dwi'),
    }
    
    qc_folder = os.path.join(session_path, 'qc')
    os.makedirs(qc_folder, exist_ok=True)

    dataset_description = os.path.join(os.getcwd(), 'dataset_description.json')

    for modal, (subdir, file_prefix) in qc_modals.items():
        if modal in modal_data['Modality'].values:
            file_path = modal_data.loc[modal_data['Modality'] == modal, 'Filepath'].values[0]

            target_dir = os.path.join(qc_folder, modal, 'sub-001', subdir)
            os.makedirs(target_dir, exist_ok=True)

            # Copy dataset description
            shutil.copyfile(dataset_description, os.path.join(qc_folder, modal, 'dataset_description.json'))

            # Copy main NIfTI and JSON files
            for ext in ['nii', 'json']:
                src_file = file_path.replace('nii', ext)
                dest_file = os.path.join(target_dir, f'{file_prefix}.{ext}')
                if os.path.exists(src_file):
                    shutil.copyfile(src_file, dest_file)

            # Copy additional files for DTI
            if modal in ['DTI20', 'DTI64']:
                for ext in ['bval', 'bvec']:
                    src_file = file_path.replace('nii', ext)
                    dest_file = os.path.join(target_dir, f'{file_prefix}.{ext}')
                    if os.path.exists(src_file):
                        shutil.copyfile(src_file, dest_file)

# Example usage
o, e = dcm_convert('assets/ACP003_V1')
session_path = 'temp/ACP003_V1'
modal_data = compile_modalities(session_path)
organize_qc_data(session_path, modal_data)

import os
import subprocess

def run_mriqc(session_path):
    qc_modals = ['T1','fMRI', 'DTI20','DTI64']
    
    for modal in qc_modals:
        # Define paths
        bids_dir = os.path.join(session_path, 'qc', modal)
        qc_output = os.path.join(session_path, 'qc', f"{modal}_output")
        os.makedirs(qc_output, exist_ok=True)
        
        # Activate .mriqc environment and run command
        cmd = ['bash', '-c', f"source .mriqc/bin/activate && mriqc {bids_dir} {qc_output} participant --participant-label sub-001 --no-sub"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        output, error = proc.communicate()
        
        if error:
            print(f"Error in {modal} QC:\n", error.decode())
        else:
            print(f"{modal} QC completed successfully.")

        # Activate .mriqc environment and run command
        cmd = ['bash', '-c', f"source .mriqc/bin/activate && mriqc {bids_dir} {qc_output} group --no-sub"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        output, error = proc.communicate()

# Example usage:
run_mriqc(session_path)