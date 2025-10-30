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
# Statistical Process Control (SPC) Metrics and Limits Calculation
# ======================================================================
#
# Purpose:
# This module provides core functions for calculating key statistical metrics 
# essential for X-bar control charts and process capability analysis.
#
# Functions include:
# 1. Control Limits: Calculates the Grand Average, Average Subgroup Standard 
#    Deviation (S-bar), and the 3-sigma Upper and Lower Control Limits (UCL/LCL) 
#    using the A3 constant for the X-bar chart.
# 2. Out-of-Control (OOC) Check: Flags subgroups that violate control or 
#    specification limits.
# 3. Process Capability: Calculates the Process Potential Index (Cp) and 
#    Process Capability Index (CpK) based on specification limits (USL/LSL).

# Imported modules
from typing import Optional, Tuple
import pandas as pd
from spc import ChartConfig
from spc.chart_constants import (
    A3_TABLE, D3_TABLE, D4_TABLE, B3_TABLE, B4_TABLE, D2_TABLE, E2_TABLE
)

# --- Subgroup Mean Chart Calculations (X-bar / S-bar) ---

def calculate_control_limits_x_s(df_subgroups: pd.DataFrame, subgroup_size: int) -> Tuple[float, float, float, float, float]:
    """
    Calculates the X-bar chart control limits using the A3 constant (based on S-bar).
    
    Returns: (grand_avg_x, grand_std_s, ucl_x, lcl_x, A3)
    """
    if subgroup_size not in A3_TABLE:
        raise ValueError(f"No A3 constant defined for subgroup size n={subgroup_size}. Max supported is 15.")
    
    A3 = A3_TABLE[subgroup_size]
    
    # Center Line (CL) is the Grand Average of the means
    grand_avg_x = df_subgroups['mean'].mean()
    # Process Sigma is estimated using the Average Subgroup Standard Deviation (S-bar)
    grand_std_s = df_subgroups['std'].mean()

    ucl_x = grand_avg_x + A3 * grand_std_s
    lcl_x = grand_avg_x - A3 * grand_std_s
    
    return grand_avg_x, grand_std_s, ucl_x, lcl_x, A3

# --- Subgroup Range Chart Calculations (R-chart) ---

def calculate_control_limits_r(df_subgroups: pd.DataFrame, subgroup_size: int) -> Tuple[float, float, float, float, float]:
    """
    Calculates the R-chart control limits using D3 and D4 constants.
    
    Returns: (avg_r, ucl_r, lcl_r, D3, D4)
    """
    if subgroup_size not in D3_TABLE or subgroup_size not in D4_TABLE:
        raise ValueError(f"No D3/D4 constants defined for subgroup size n={subgroup_size}. Max supported is 15.")
    
    D3 = D3_TABLE[subgroup_size]
    D4 = D4_TABLE[subgroup_size]
    
    # Center Line (CL) is the Average Range (R-bar)
    avg_r = df_subgroups['range'].mean()

    ucl_r = D4 * avg_r
    lcl_r = D3 * avg_r
    
    return avg_r, ucl_r, lcl_r, D3, D4

# --- Subgroup Standard Deviation Chart Calculations (S-chart) ---

def calculate_control_limits_s(df_subgroups: pd.DataFrame, subgroup_size: int) -> Tuple[float, float, float, float, float]:
    """
    Calculates the S-chart control limits using B3 and B4 constants.
    
    Returns: (avg_std_s, ucl_s, lcl_s, B3, B4)
    """
    if subgroup_size not in B3_TABLE or subgroup_size not in B4_TABLE:
        raise ValueError(f"No B3/B4 constants defined for subgroup size n={subgroup_size}. Max supported is 15.")
    
    B3 = B3_TABLE[subgroup_size]
    B4 = B4_TABLE[subgroup_size]
    
    # Center Line (CL) is the Average Standard Deviation (S-bar)
    avg_std_s = df_subgroups['std'].mean()

    ucl_s = B4 * avg_std_s
    lcl_s = B3 * avg_std_s
    
    return avg_std_s, ucl_s, lcl_s, B3, B4

# --- Individual Observations Chart Calculations (I-chart) ---

def calculate_control_limits_i(df_subgroups: pd.DataFrame) -> Tuple[float, float, float, float, float]:
    """
    Calculates the Individual (I) chart control limits.
    
    Uses the Average Moving Range (MR-bar) and d2 (for n=2) to estimate process sigma.
    Returns: (grand_avg_x, mr_bar, ucl_i, lcl_i, E2)
    """
    # d2 constant for n=2 (used for MR calculation)
    D2_n2 = D2_TABLE[2]
    # E2 constant (3 / d2)
    E2_n2 = E2_TABLE[2]
    
    # Center Line (CL) is the Grand Average of the individual observations
    grand_avg_i = df_subgroups['mean'].mean()
    
    # Average Moving Range (MR-bar). Exclude the first NaN value.
    mr_bar = df_subgroups['moving_range'].mean()
    
    # Calculate process sigma estimate: sigma_hat = mr_bar / d2(n=2)
    if D2_n2 == 0:
        raise ZeroDivisionError("d2 constant is zero, cannot calculate I-chart limits.")
    process_sigma = mr_bar / D2_n2
    
    # Control Limits: CL +/- 3 * sigma_hat
    ucl_i = grand_avg_i + 3 * process_sigma
    lcl_i = grand_avg_i - 3 * process_sigma
    
    return grand_avg_i, mr_bar, ucl_i, lcl_i, E2_n2, process_sigma

# --- Moving Range Chart Calculations (MR-chart) ---

def calculate_control_limits_mr(df_subgroups: pd.DataFrame) -> Tuple[float, float, float, float, float]:
    """
    Calculates the Moving Range (MR) chart control limits.
    
    Uses D3 and D4 constants for n=2 (MR is the range of 2 points).
    Returns: (mr_bar, ucl_mr, lcl_mr, D3_mr, D4_mr)
    """
    D3_mr = 0 # D3 for n=2
    D4_mr = 3.268 # D4 for n=2
    
    # Center Line (CL) is the Average Moving Range (MR-bar). Exclude the first NaN value.
    mr_bar = df_subgroups['moving_range'].mean()

    ucl_mr = D4_mr * mr_bar
    lcl_mr = D3_mr * mr_bar
    
    return mr_bar, ucl_mr, lcl_mr, D3_mr, D4_mr

# --- Process Capability and OOC/OOS Checks ---

def calculate_cpk(chart_cfg: ChartConfig, grand_avg: float, process_sigma: float) -> Tuple[Optional[float], Optional[float]]:
    """Calculates Process Capability (Cp and CpK) if USL and LSL are set."""
    usl = chart_cfg.usl
    lsl = chart_cfg.lsl
    
    if usl is None or lsl is None:
        return None, None
        
    if process_sigma <= 0:
        print("WARNING: Cannot calculate Cp/CpK, process standard deviation is zero or negative.")
        return None, None
            
    # Cp (Process Potential Index)
    process_spread = usl - lsl
    cp = process_spread / (6 * process_sigma)
    
    # CpK (Process Capability Index)
    cpl = (grand_avg - lsl) / (3 * process_sigma)
    cpu = (usl - grand_avg) / (3 * process_sigma)
    cpk = min(cpl, cpu)
    
    return cp, cpk

def check_ooc(df_subgroups: pd.DataFrame, data_column_name: str, ucl: float, lcl: float) -> pd.DataFrame:
    """Applies control limits to flag out-of-control (OOC) points."""
    
    # Ensure moving_range has no NaNs for the OOC check (only relevant for MR chart)
    df_temp = df_subgroups.dropna(subset=[data_column_name]).copy()
    
    # Criteria: Above UCL or Below LCL
    ooc_mask = (df_temp[data_column_name] > ucl) | (df_temp[data_column_name] < lcl)

    # Note: df_subgroups is modified in SpcDataProcessor, but this returns the OOC points
    # We add the OOC_Flag to the returned DataFrame of OOC points for confirmation
    df_ooc = df_temp[ooc_mask].copy()
    df_ooc['OOC_Flag'] = True
    
    return df_ooc


def check_oos(df: pd.DataFrame, column: str, usl: float, lsl: float) -> pd.DataFrame:
    """
    Applies specification limits (USL and LSL) to flag out-of-specification (OOS) points.
    Returns the full DataFrame with a boolean 'OOS' column.
    """
    # 1. Create a copy of the input DataFrame to ensure the original is not modified.
    df_copy = df.copy()
    
    # 2. Initialize the new flag column to False for all rows.
    df_copy['OOS'] = False

    # 3. Calculate the OOS mask (True if point is above USL OR below LSL).
    # The mask must be calculated on the column of interest in the copy.
    oos_mask = (df_copy[column] > usl) | (df_copy[column] < lsl)
    
    # 4. Apply the mask to set the 'OOS' flag to True for violating rows.
    # We use .loc to modify values based on the mask.
    df_copy.loc[oos_mask, 'OOS'] = True
    
    # 5. Return the full DataFrame with the new flag column.
    return df_copy


def compute_sigmas(avg, ucl):
    sigma = (ucl - avg) / 3
    two_sigma = 2 * sigma
    three_sigma = 3 * sigma

    return sigma, two_sigma, three_sigma