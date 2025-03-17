from MRI.qc import run_mriqc
from MRI.dicom import dcm2nifti
from MRI.compile import compile_modalities, compile_qc_folder, compile_sub_folder
from MRI.utils import get_time, read_json, extract_acq_times, compute_session_duration

def main():
    # CHANGE THE SUBJECT DIRECTORY HERE
    input_folder, bids_id = 'assets/BGH004_V2', 'sub-002'
    modalities_json = 'utils/modalities.json'
    
    print(f"{get_time()} Starting DICOM conversion...")
    dcm2nifti(input_folder)
    
    print(f"{get_time()} Compiling modalities...")
    modal_data = compile_modalities(input_folder, modalities_json)
    
    print(f"{get_time()} Organizing QC data...")
    compile_qc_folder(input_folder, modal_data)
    
    print(f"{get_time()} Running MRIQC...")
    run_mriqc(input_folder)
    
    print(f"{get_time()} Running BIDS organisation...")
    compile_sub_folder(input_folder, bids_id, modal_data)

    print("Processing complete.")

if __name__ == "__main__":
    main()