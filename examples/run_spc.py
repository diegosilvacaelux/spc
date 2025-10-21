# run_spc.py

import os
import time  
from spc.config import load_multiple_configs
from spc.spc_processor import SpcDataProcessor

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
    CONFIG_DIR = 'spc_setup' 
    
    # 1. Load all configurations
    all_configs = load_multiple_configs(
        directory_path=CONFIG_DIR, 
        file_prefix='spc_setup', 
        file_suffix='.json'
    )
    
    if not all_configs:
        print("No valid configurations found. Exiting.")
        return

    # 2. Process each configuration sequentially
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
    if not os.path.exists('spc_setup'):
        os.makedirs('spc_setup')
        print("Created directory: spc_setup. Please add your JSON configuration files here.")
        
    main()