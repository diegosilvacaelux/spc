#!/usr/bin/python3
#
# Copyright 2025 Diego Tapia Silva 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License
#
# ======================================================================
# Main script for Statistical Process Control (SPC) X-bar Chart Analysis
# ======================================================================
#
# Workflow:
# 1. Configuration Discovery: Scans the 'spc_setup' directory for all
#    JSON configuration files (e.g., spc_setup*.json).
# 2. Batch Processing: Iterates through each discovered configuration.
# 3. Data Processing: For each config, it loads the specified Excel data, 
#    cleans and filters it by time and column criteria, and groups the data 
#    into subgroups (X-bar chart logic).
# 4. Metric Calculation: Computes control limits (UCL/LCL), flags out-of-control 
#    (OOC) points, and calculates process capability indices (Cp/CpK) if specification 
#    limits (USL/LSL) are provided.
# 5. Output Generation: Generates a comprehensive text report and a corresponding 
#    X-bar control chart image (*_report.txt and *_chart.png) for each analysis.
# 6. Time Tracking: Reports the individual execution time for each analysis and the 
#    total duration for the entire batch job.
#
# Usage:
# Run the script directly to execute the batch SPC analysis pipeline for all 
# configuration files found in the 'spc_setup' directory.

# Imported modules
import os
import time  
# Developed modules 
from spc.config import load_multiple_configs
from spc.processor import SpcDataProcessor

def format_duration(seconds):
    """Convert a duration in seconds into H:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours}h {minutes:02}m {seconds:05.2f}s"

def main():
    # Record the start time for the entire batch job
    start_time = time.time()

    # Define the directory where your configuration files live
    CONFIG_DIR = 'setup' 
    
    # Load all configurations
    all_configs = load_multiple_configs(
        directory_path=CONFIG_DIR, 
        file_prefix='spc_setup', 
        file_suffix='.json'
    )
    
    if not all_configs:
        print("No valid configurations found. Exiting.")
        return

    # Process each configuration sequentially
    for config_item in all_configs:
        # Start time for the individual analysis
        analysis_start_time = time.time()

        data_cfg = config_item['data_cfg']
        chart_cfg = config_item['chart_cfg']
        time_cfg = config_item['time_cfg']
        
        # Use the config filename (without extension) as the output prefix
        output_prefix = os.path.splitext(config_item['filename'])[0]
        print("\n" + "="*80)
        print(f"STARTING ANALYSIS for: {output_prefix}")
        print("="*80)
        
        try:
            processor = SpcDataProcessor(data_cfg, chart_cfg, time_cfg, output_prefix)
            processor.run_analysis()
            
            # End time and duration for the individual analysis
            analysis_end_time = time.time()
            duration = analysis_end_time - analysis_start_time
            print(f"Analysis for {output_prefix} finished. Duration: {format_duration(duration)}")
            
        except Exception as e:
            print(f"!!! CRITICAL FAILURE: Analysis for {output_prefix} failed: {e}")
        
    # 3. Finalize and report total time
    end_time = time.time()
    total_duration = end_time - start_time
    
    print("\n" + "#"*80)
    print("All scheduled analyses completed.")
    print(f"Total batch job duration: {format_duration(total_duration)}")
    print("#"*80)

if __name__ == '__main__':
    # Ensure the config directory exists for a cleaner setup experience
    if not os.path.exists('setup'):
        os.makedirs('setup')
        print("Created directory: setup. Please add your JSON configuration files here.")
        
    main()