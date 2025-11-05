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
# SPC Configuration Dataclasses
# ======================================================================
#
# Purpose:
# This module defines the structured configuration objects (dataclasses) 
# used to govern the behavior of the Statistical Process Control (SPC) 
# analysis pipeline. These classes are instantiated by the 'config.py' 
# module from the input JSON files.
#
# Dataclasses:
# 1. DataConfig: Specifies the location and filtering criteria for the 
#    input data (Excel file, columns, filters).
# 2. TimeConfig: Defines the chronological range for the analysis, handling 
#    start/end dates, relative ranges (e.g., "1w"), and date parsing.
# 3. ChartConfig: Contains parameters related to the control chart visuals 
#    and limits (USL/LSL, colors, labels).

# Imported modules
from dataclasses import dataclass, field
from typing import Dict, Literal, Optional, List
from datetime import datetime, timedelta

DateRange = Literal["1d", "2d", "3d", "4d", "5d", "6d","1w", "2w", "3w", "1m", "2m", "3m", "6m", "1y"]
ColumnFilters = Dict[str, str]

@dataclass
class DataConfig:
    """
    Configuration for loading and initial filtering of raw data for SPC analysis.
    """
    filename: str
    sheet_name: str
    
    # 1. Flexible Column Names (Input Fields)
    y_data_col: str         # The column containing the measured variable (e.g., "Max PCE (%)")
    date_col: str           # The column containing the date/time (e.g., "Fab Date" or "Date")
    substrate_col: str      # The column defining the subgroup unit (e.g., "Glass ID" or "Wafer Lot")
    
    skiprows: int
    header: int
    
    # Filtering fields
    column_include_entries: Optional[Dict[str, List[str]]] = field(default_factory=dict)
    column_exclude_entries: Optional[Dict[str, List[str]]] = field(default_factory=dict)

    @property
    def y_data_name(self) -> str:
        """Alias for compatibility with plotting functions."""
        return self.y_data_col

    @property
    def grouping_keys(self) -> List[str]:
        """
        Dynamically defines the columns used to create subgroups, which are the 
        date column and the substrate ID column.
        """
        # The grouping keys are always the date column and the substrate column
        return [self.date_col, self.substrate_col]
    
    @property
    def required_columns(self) -> List[str]:
        """
        Generates a list of all columns that must be present in the DataFrame, 
        ensuring all analysis, grouping, and filtering columns are included.
        """
        # Start with the mandatory columns for analysis
        # Note: We use self.y_data_col here, not self.y_data_name
        cols = self.grouping_keys + [self.y_data_col]
        
        # Include columns from inclusion filters
        if self.column_include_entries:
            # Get the keys (column names) from the dictionary
            cols.extend(list(self.column_include_entries.keys()))
            
        # Include columns from exclusion masks
        if self.column_exclude_entries:
            # Get the keys (column names) from the dictionary
            cols.extend(list(self.column_exclude_entries.keys()))
            
        # Use dict.fromkeys to maintain order and deduplicate
        return list(dict.fromkeys(cols))

@dataclass
class TimeConfig:
    reference_date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    date_range: DateRange = "1w"
    date_format: str = "%m-%d-%Y" 
    
    start_dt: datetime = field(init=False)
    end_dt: datetime = field(init=False)

    def _apply_range(self, dt: datetime, rng: DateRange, backward: bool = False) -> datetime:
        delta_map = {
            "1d": timedelta(days=1), "2d": timedelta(days=2), "3d": timedelta(days=3),
            "4d": timedelta(days=4), "5d": timedelta(days=5), "6d": timedelta(days=6),
            "1w": timedelta(weeks=1), "2w": timedelta(weeks=2),"3w": timedelta(weeks=3),
            "1m": timedelta(days=30), "2m": timedelta(weeks=9), "3m": timedelta(weeks=12),
            "6m": timedelta(weeks=24), "1y": timedelta(days=365)
        }
        if rng not in delta_map:
            raise ValueError(f"Invalid date_range: {rng}")
            
        delta = delta_map[rng]
        return dt - delta if backward else dt + delta

    def __post_init__(self):
        import pandas as pd
        
        def parse_opt(dt_str: Optional[str]) -> Optional[datetime]:
            if dt_str is None or (isinstance(dt_str, str) and dt_str.lower() in ('none', 'null', '')):
                return None
            
            try:
                return datetime.strptime(dt_str, self.date_format)
            except ValueError:
                try:
                    return pd.to_datetime(dt_str).to_pydatetime()
                except:
                    raise ValueError(f"Date '{dt_str}' does not match format {self.date_format} or common formats.")

        for attr in ['start_date', 'end_date', 'reference_date']:
            val = getattr(self, attr)
            if isinstance(val, str) and val.lower() == 'null':
                setattr(self, attr, None)
        
        ref_dt = parse_opt(self.reference_date) or datetime.today()
        start_dt = parse_opt(self.start_date)
        end_dt = parse_opt(self.end_date)
        
        if start_dt is not None and end_dt is not None:
            self.start_dt = start_dt
            self.end_dt = end_dt
        elif start_dt is not None:
            self.start_dt = start_dt
            self.end_dt = self._apply_range(start_dt, self.date_range)
        elif end_dt is not None:
            self.end_dt = end_dt
            self.start_dt = self._apply_range(end_dt, self.date_range, backward=True)
        else:
            self.end_dt = ref_dt
            self.start_dt = self._apply_range(ref_dt, self.date_range, backward=True)

@dataclass
class ChartConfig:
    usl: Optional[float] = None
    lsl: Optional[float] = None
    xlabel: Optional[str] = "Index (Chronological)"
    ylabel: Optional[str] = field(init=False, default=None) 
    color_out_of_control: str = 'red'
    color_out_of_specification: str = 'red'
    color_in_control: str = 'blue'
    color_avg: str = 'black'
    color_control_limits: str = 'darkorange'
    color_spec_limits: str = 'green'
    events_vlines: Optional[Dict[str, str]] = field(default_factory=dict)
