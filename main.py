import os
import subprocess
import json
import glob
import pandas as pd
import shutil
from typing import List, Optional
from datetime import datetime
import pytz

def dcm_convert(input_folder: str, cmd: Optional[List[str]] = None):
    """
    Converts DICOM files to NIfTI format using dcm2niix.
    """
    subject_id = os.path.basename(input_folder)
    output_folder = os.path.join(os.getcwd(), 'temp', subject_id)
    os.makedirs(output_folder, exist_ok=True)

    if cmd is None:
        cmd = ['dcm2niix', '-f', '%i_%p', '-o', output_folder, input_folder]
    
    if not os.path.isdir(input_folder):
        raise FileNotFoundError(f"Input folder '{input_folder}' does not exist.")
    
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = proc.communicate()
    
    with open(os.path.join(output_folder, "dcm2niix_cmd_output.txt"), "w") as out_file:
        out_file.write(output.decode('utf-8'))
    
    if error:
        with open(os.path.join(output_folder, "dcm2niix_cmd_error.txt"), "w") as err_file:
            err_file.write(error.decode('utf-8'))
    
    return output, error

def read_json(json_path: str):
    """Reads and parses a JSON file."""
    try:
        with open(json_path, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise ValueError(f"Error reading JSON file {json_path}: {str(e)}")

def compile_modalities(input_filepath: str, modalities_json: str):
    """Extracts and compiles modalities from JSON files."""
    data = read_json(modalities_json)
    all_files = sorted(glob.glob(f"{input_filepath}/*.json"))
    modal_data = []
    
    for key, value in data.items():
        for file in all_files:
            if value[0] in file:
                json_file = read_json(file)
                image_type = json_file.get('ImageType', [])
                
                if 'ORIGINAL' in image_type:
                    modal_data.append([key, file.replace('.json', '.nii'), 'ORIGINAL', json_file['AcquisitionTime']])
                    break
    
    modal_df = pd.DataFrame(modal_data, columns=['Modality', 'Filepath', 'Type', 'AcqTime'])
    modal_df = modal_df.sort_values(by='AcqTime').reset_index(drop=True)
    modal_df.to_csv(os.path.join(input_filepath, 'modal_data.csv'))
    
    return modal_df

def organize_qc_data(session_path: str, modal_data: pd.DataFrame):
    """
    Organizes QC data into structured directories.
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
            
            shutil.copyfile(dataset_description, os.path.join(qc_folder, modal, 'dataset_description.json'))
            
            for ext in ['nii', 'json']:
                src_file = file_path.replace('nii', ext)
                dest_file = os.path.join(target_dir, f'{file_prefix}.{ext}')
                if os.path.exists(src_file):
                    shutil.copyfile(src_file, dest_file)
            
            if modal in ['DTI20', 'DTI64']:
                for ext in ['bval', 'bvec']:
                    src_file = file_path.replace('nii', ext)
                    dest_file = os.path.join(target_dir, f'{file_prefix}.{ext}')
                    if os.path.exists(src_file):
                        shutil.copyfile(src_file, dest_file)

def run_mriqc(session_path: str):
    """
    Runs MRIQC on QC data.
    """
    qc_modals = ['T1', 'fMRI', 'DTI20', 'DTI64']
    
    for modal in qc_modals:
        bids_dir = os.path.join(session_path, 'qc', modal)
        qc_output = os.path.join(session_path, 'qc', f"{modal}_output")
        os.makedirs(qc_output, exist_ok=True)
        
        cmd = ['bash', '-c', f"source .mriqc/bin/activate && mriqc {bids_dir} {qc_output} participant --participant-label sub-001 --no-sub"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = proc.communicate()
        
        if error:
            print(f"Error in {modal} QC:\n", error.decode())
        else:
            print(f"{modal} QC completed successfully.")

        # Activate .mriqc environment and run command
        cmd = ['bash', '-c', f"source .mriqc/bin/activate && mriqc {bids_dir} {qc_output} group --no-sub"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        output, error = proc.communicate()

def final_folder(sessions_path: str, bids_id: str, modal_data):
    qc_modals = {
        'T1'    : ('anat', f'{bids_id}_T1w'),
        'T2S'   : ('anat', f'{bids_id}_T2star'),
        'T2F'   : ('anat', f'{bids_id}_FLAIR'),
        'HRH'   : ('anat', f'{bids_id}_acq-HRH_T1w'),
        'fMRI'  : ('func', f'{bids_id}_task-rest_bold'),
        'DTI20' : ('dwi', f'{bids_id}_dti20_dwi'),
        'DTI64' : ('dwi', f'{bids_id}_dti64_dwi'),
    }

    rename_qc = {
    'DTI20' : f'{bids_id}_mriqc_DTI20.tsv',
    'DTI64' : f'{bids_id}_mriqc_DTI64.tsv',
    'fMRI' : f'{bids_id}_mriqc_fMRI.tsv',
    'T1' : f'{bids_id}_mriqc_T1.tsv'
    }

    sub_folder = os.path.join('output', sessions_path.split("/")[-1])
    os.makedirs(sub_folder, exist_ok=True)

    qc_folder = os.path.join('output', sessions_path.split("/")[-1], 'qc')
    os.makedirs(qc_folder, exist_ok=True)

    for modal, (subdir, file_prefix) in qc_modals.items():
        if modal in modal_data['Modality'].values:
            file_path = modal_data.loc[modal_data['Modality'] == modal, 'Filepath'].values[0]
            target_dir = os.path.join(sub_folder, bids_id, subdir)
            os.makedirs(target_dir, exist_ok=True)
                    
            for ext in ['nii', 'json']:
                src_file = file_path.replace('nii', ext)
                dest_file = os.path.join(target_dir, f'{file_prefix}.{ext}')
                if os.path.exists(src_file):
                    shutil.copyfile(src_file, dest_file)
            
            if modal in ['DTI20', 'DTI64']:
                for ext in ['bval', 'bvec']:
                    src_file = file_path.replace('nii', ext)
                    dest_file = os.path.join(target_dir, f'{file_prefix}.{ext}')
                    if os.path.exists(src_file):
                        shutil.copyfile(src_file, dest_file)

    mriqc_tsv = glob.glob(sessions_path + "/**/group_*.tsv", recursive=True)
    for file in mriqc_tsv:
        modal = file.split("_output")[0].split("/")[-1]
        filename = rename_qc.get(modal)
        src = file
        dst = os.path.join(qc_folder, filename)
        shutil.copyfile(src, dst)


def main():
    # CHANGE THE SUBJECT DIRECTORY HERE
    input_folder = 'assets/ALK002_V2'
    session_path = 'temp/ALK002_V2'
    bids_id = 'sub-001'
    modalities_json = 'modalities.json'
    
    print(f"{datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S')} Starting DICOM conversion...")
    dcm_convert(input_folder)
    
    print(f"{datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S')} Compiling modalities...")
    modal_data = compile_modalities(session_path, modalities_json)
    
    print(f"{datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S')} Organizing QC data...")
    organize_qc_data(session_path, modal_data)
    
    print(f"{datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S')} Running MRIQC...")
    run_mriqc(session_path)
    
    print(f"{datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S')} Running BIDS organisation...")
    final_folder(session_path, bids_id, modal_data)

    print("Processing complete.")

if __name__ == "__main__":
    main()
