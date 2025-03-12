import os
import glob
import pandas as pd
from utils import read_json

def compile_modalities(input_filepath: str, modalities_json: str):
    """Extracts and compiles modalities from JSON files."""
    data = read_json(modalities_json)
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
    
    modal_df = pd.DataFrame(modal_data, columns=['Modality', 'Filepath', 'Type', 'AcqTime'])
    modal_df = modal_df.sort_values(by='AcqTime').reset_index(drop=True)
    modal_df.to_csv(os.path.join(input_filepath, 'modal_data.csv'))
    
    return modal_df

def compile_qc_data(session_path: str, modal_data: pd.DataFrame):
    """
    Compile data into structured directories for QC.
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

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        output, error = proc.communicate()

def compile_subject_folder(sessions_path: str, bids_id: str, modal_data):
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

