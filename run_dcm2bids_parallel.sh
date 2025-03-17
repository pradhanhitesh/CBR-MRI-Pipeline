#!/bin/bash

# Check if the user provided the number of parallel jobs
if [ -z "$1" ]; then
    echo "Usage: $0 <num_parallel_jobs>"
    exit 1
fi

NUM_JOBS=$1  # Number of parallel jobs specified by the user
BASE_DIR="."

# Find all folders (excluding hidden ones)
folders=($(find "$BASE_DIR" -mindepth 1 -maxdepth 1 -type d | sort))

# Run dcm2bids using GNU parallel with sequential numbering
parallel --jobs "$NUM_JOBS" --eta \
    '~/dcm2bids -d {} -p $(printf "%03d" {#}) -c config.json' ::: "${folders[@]}"