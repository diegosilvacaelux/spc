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
# SPC Configuration Loader
# ======================================================================
#
# Purpose:
# This module is responsible for loading Statistical Process Control (SPC) 
# configuration files (JSON) and validating them. It handles loading single 
# files or iterating over a directory to set up multiple analysis runs. 
# It converts raw configuration dictionaries into structured DataConfig, 
# TimeConfig, and ChartConfig objects for use by the SpcDataProcessor.
#
# Note: It automatically prepends the CONFIG_DIR path to the Excel 
# filename defined within the DataConfig section.

# Imported modules
import json
import os
from typing import Dict, List

# Developed modules
from spc import DataConfig, TimeConfig, ChartConfig

# Define the relative path to the configuration and data directory here
CONFIG_DIR = 'setup' 

def load_json_config(filepath: str) -> Dict:
    """Loads and validates a single configuration from a JSON file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Configuration file '{filepath}' not found.")
        
    try:
        with open(filepath, 'r') as f:
            config = json.load(f)
            # Simple validation to ensure top-level keys exist
            for key in ['DataConfig', 'TimeConfig', 'ChartConfig']:
                if key not in config:
                    raise ValueError(f"Missing required key '{key}' in config file: {filepath}")
            return config
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON in '{filepath}': {e}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred while loading config '{filepath}': {e}")

def load_multiple_configs(directory_path: str, file_prefix: str = 'spc_setup', file_suffix: str = '.json') -> List[Dict]:
    """
    Finds all matching configuration JSON files in a directory and loads them.
    
    Returns a list of dictionaries, where each dict is {'config': Dict, 'filename': str}.
    """
    if not os.path.isdir(directory_path):
        print(f"WARNING: Configuration directory '{directory_path}' not found. Skipping config loading.")
        return []

    config_files = []
    for filename in sorted(os.listdir(directory_path)):
        if filename.startswith(file_prefix) and filename.endswith(file_suffix):
            filepath = os.path.join(directory_path, filename)
            try:
                config_data = load_json_config(filepath)
                
                # --- CRITICAL MODIFICATION HERE ---
                # Prepend the CONFIG_DIR to the Excel filename before creating DataConfig
                excel_filename = config_data['DataConfig']['filename']
                full_excel_path = os.path.join(CONFIG_DIR, excel_filename)
                
                # Update the dictionary used to create the DataConfig dataclass
                config_data['DataConfig']['filename'] = full_excel_path
                # --- END MODIFICATION ---

                # Instantiate dataclasses to enforce type validation right away
                data_cfg = DataConfig(**config_data['DataConfig'])
                chart_cfg = ChartConfig(**config_data['ChartConfig'])
                time_cfg = TimeConfig(**config_data['TimeConfig'])
                
                config_files.append({
                    'data_cfg': data_cfg,
                    'chart_cfg': chart_cfg,
                    'time_cfg': time_cfg,
                    'filename': filename
                })
                print(f"Successfully loaded and validated config: {filename}")
            except Exception as e:
                print(f"ERROR processing config file {filename}: {e}. Skipping.")
                continue
                
    if not config_files:
        print(f"WARNING: No config files found matching '{file_prefix}*.json' in '{directory_path}'.")
        
    return config_files