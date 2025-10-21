# spc_analysis/metrics.py

from typing import Optional, Tuple
import pandas as pd
from spc import ChartConfig

# A3 constants for X-bar chart using subgroup standard deviation (S-bar)
A3_TABLE = {
    2: 2.659, 3: 1.954, 4: 1.628, 5: 1.427, 6: 1.287, 7: 1.182, 8: 0.373,
}

def calculate_control_limits(df_subgroups: pd.DataFrame, max_subgroup_size: int) -> Tuple[float, float, float, float]:
    """
    Calculates the Grand Average, Average Subgroup Std, UCL, and LCL.
    
    Returns: (grand_avg, grand_std, ucl, lcl)
    """
    if max_subgroup_size not in A3_TABLE:
        raise ValueError(f"No A3 constant defined for subgroup size n={max_subgroup_size}. Max supported is 8.")
        
    A3 = A3_TABLE[max_subgroup_size]
    
    grand_avg = df_subgroups['mean'].mean()
    grand_std = df_subgroups['std'].mean()

    ucl = grand_avg + A3 * grand_std
    lcl = grand_avg - A3 * grand_std
    
    return grand_avg, grand_std, ucl, lcl, A3

def check_ooc(df_subgroups: pd.DataFrame, chart_cfg: ChartConfig, grand_avg: float, ucl: float, lcl: float) -> pd.DataFrame:
    """Applies control and spec limits to flag out-of-control (OOC) points."""
    ooc_mask = pd.Series(False, index=df_subgroups.index)

    # Criteria Using Control Limits (UCL/LCL)
    if chart_cfg.use_control_limits_ooc:
        ucl_lcl_ooc = (df_subgroups['mean'] > ucl) | (df_subgroups['mean'] < lcl)
        ooc_mask = ooc_mask | ucl_lcl_ooc

    # Criteria Using Specification Limits (USL/LSL)
    usl_set = chart_cfg.usl is not None
    lsl_set = chart_cfg.lsl is not None
    
    if usl_set or lsl_set:
        usl = chart_cfg.usl if usl_set else float('inf')
        lsl = chart_cfg.lsl if lsl_set else float('-inf')
        
        usl_lsl_ooc = (df_subgroups['mean'] > usl) | (df_subgroups['mean'] < lsl)
        ooc_mask = ooc_mask | usl_lsl_ooc
        
    df_subgroups['OOC_Flag'] = ooc_mask
    return df_subgroups[ooc_mask].copy()

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