# spc/test_config.py

import json
import os
from typing import Dict, Any


def load_json_config(filepath: str) -> Dict[str, Any]:
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
            # IMPORTANT: DO NOT modify config['DataConfig']['filename'] here.
            return config
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON in '{filepath}': {e}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred while loading config '{filepath}': {e}")

