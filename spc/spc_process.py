import os
import time
import sys 
import glob 

# Developed modules 
from spc.config import load_json_config 
from spc import DataConfig, TimeConfig, ChartConfig
from spc.processor import SpcDataProcessor

def format_duration(seconds):

    """Convert a duration in seconds into H:MM:SS format."""

    hours = int(seconds // 3600)

    minutes = int((seconds % 3600) // 60)

    seconds = seconds % 60

    return f"{hours}h {minutes:02}m {seconds:05.2f}s"


def main():
    start_time = time.time()
    
    config_files_to_process = []
    input_file_paths = []

    # --- NEW ARGUMENT HANDLING LOGIC ---
    if len(sys.argv) > 1:
        # Check if a wildcard was passed (e.g., python spc_process.py *.json)
        # We only check the first argument, assuming the shell didn't expand it.
        if '*' in sys.argv[1]:
            # Python handles the wildcard expansion here
            input_file_paths = glob.glob(sys.argv[1])
            if not input_file_paths:
                print(f"Warning: No files found matching '{sys.argv[1]}'.")
        else:
            # If no wildcard, assume the arguments are explicit file names
            input_file_paths = sys.argv[1:]
    
    if not input_file_paths:
        print("Error: Please provide one or more JSON configuration files as command-line arguments.")
        print("Usage: python spc_process.py *.json  OR  python spc_process.py spc_setup01.json")
        return

    print(f"Found {len(input_file_paths)} configuration file(s) to process.")
    
    # --- Loop over the resolved list of file paths ---
    for file_path in input_file_paths:
        try:
            # Get the directory where the JSON config file resides
            config_dir = os.path.dirname(os.path.abspath(file_path)) or os.getcwd() # Use os.getcwd() for safety
            
            config_data = load_json_config(file_path) 
            
            # Instantiate dataclasses
            data_cfg = DataConfig(**config_data['DataConfig'])
            chart_cfg = ChartConfig(**config_data['ChartConfig'])
            time_cfg = TimeConfig(**config_data['TimeConfig'])
            
            config_filename = os.path.basename(file_path) 

            config_files_to_process.append({
                'data_cfg': data_cfg,
                'chart_cfg': chart_cfg,
                'time_cfg': time_cfg,
                'filename': config_filename, 
            })
            print(f"Loaded: {config_filename}")
            
        except Exception as e:
            print(f"!!! CRITICAL FAILURE: Could not load or validate file {file_path}: {e}. Skipping.")
            
    # ... (rest of the processing logic remains the same) ...
    if not config_files_to_process:
        print("No valid configurations found to process. Exiting.")
        return

    print("\n" + "~"*80)
    print(f"Starting batch process for {len(config_files_to_process)} analysis run(s).")
    print("~"*80)

    for config_item in config_files_to_process:
        analysis_start_time = time.time()
        data_cfg = config_item['data_cfg']
        chart_cfg = config_item['chart_cfg']
        time_cfg = config_item['time_cfg']
        config_filename = config_item['filename']

        prefix_base = os.path.splitext(config_filename)[0] 
        output_dir_name = prefix_base.replace('spc_setup', 'spc_output')
        
        if not os.path.exists(output_dir_name):
            os.makedirs(output_dir_name, exist_ok=True)
            print(f"Created output directory: {output_dir_name}")
            
        output_prefix = os.path.join(output_dir_name, prefix_base)
        
        print("\n" + "="*80)
        print(f"STARTING ANALYSIS for: {config_filename} -> Output in: {output_dir_name}")
                     
        print("="*80)
        
        try:
            processor = SpcDataProcessor(
                dataconfig=data_cfg, 
                chartconfig=chart_cfg, 
                timeconfig=time_cfg, 
                output_dir=output_dir_name
            )
            processor.run_analysis()
            
            analysis_end_time = time.time()
            duration = analysis_end_time - analysis_start_time
            print(f"Analysis for {config_filename} finished. Duration: {format_duration(duration)}")
            
        except Exception as e:
            print(f"!!! CRITICAL FAILURE: Analysis for {config_filename} failed: {e}")
            
    # ... (Finalize and report total time) ...
    end_time = time.time()
    total_duration = end_time - start_time
    
    print("\n" + "#"*80)
    print("All scheduled analyses completed.")
    print(f"Total batch job duration: {format_duration(total_duration)}")
    print("#"*80)

if __name__ == '__main__':
    main()