import os

def run_mriqc(session_path: str):
    """
    Runs MRIQC on QC data.
    """
    qc_modals = ['T1', 'fMRI', 'DTI20', 'DTI64']
    
    for modal in qc_modals:
        bids_dir = os.path.join(session_path, 'qc', modal)
        qc_output = os.path.join(session_path, 'qc', f"{modal}_output")
        os.makedirs(qc_output, exist_ok=True)
        
        # Run participant level analysis
        cmd = ['bash', '-c', f"source .mriqc/bin/activate && mriqc {bids_dir} {qc_output} participant --participant-label sub-001 --no-sub"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = proc.communicate()
        
        if error:
            print(f"Error in {modal} QC:\n", error.decode())
        else:
            print(f"{modal} QC completed successfully.")

        # Run group level analysis
        cmd = ['bash', '-c', f"source .mriqc/bin/activate && mriqc {bids_dir} {qc_output} group --no-sub"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        output, error = proc.communicate()