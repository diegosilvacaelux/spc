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
# SPC Visualization Module (X-bar Chart Plotting)
# ======================================================================
#
# Purpose:
# This module contains functions for generating visual representations 
# of Statistical Process Control (SPC) data, primarily focusing on 
# control charts. The main function, plot_xbar_chart, generates a 
# high-quality X-bar chart using matplotlib, incorporating control limits, 
# specification limits, and annotation for out-of-control points.

# Imported modules
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
from typing import Optional


from spc import DataConfig, ChartConfig 

def plot_xbar_chart(
    df_subgroups: pd.DataFrame, 
    data_cfg: DataConfig, 
    chart_cfg: ChartConfig, 
    grand_avg: float, 
    ucl: float, 
    lcl: float, 
    cpk: Optional[float], 
    out_of_control_points: pd.DataFrame,
    out_of_specification_points: pd.DataFrame,
    output_filename: str = "xbar_chart.png"
):
    """
    Generates the X-bar control chart.
    """
    if df_subgroups is None or df_subgroups.empty:
        print("Cannot plot chart: No valid subgroups found.")
        return

    # FIX: Keep original index as a column for mapping OOC/OOS points
    subgroup_data = df_subgroups.copy().reset_index().rename(columns={'index': 'original_index'})
    x_positions = subgroup_data.index 

    fig, ax = plt.subplots(figsize=(14, 8))
        
    # Center Line
    ax.axhline(grand_avg, 
              color=chart_cfg.color_avg, 
              linestyle='-', 
              linewidth=1.5, 
              label=r'Grand Average ($\bar{\bar{{X}}}$): ' + f"{grand_avg:.3f}",
              zorder=1
    )

    # Plot Subgroup Means
    ax.plot(
        x_positions, 
        subgroup_data['mean'], 
        marker='o', 
        linestyle='-', 
        color=chart_cfg.color_in_control, 
        label=r'Subgroup Average ($\bar{X}$)',
        zorder=2
    )
    
    # Control Limits
    ax.axhline(ucl, color=chart_cfg.color_control_limits, linestyle='-', linewidth=2, 
               label=f'UCL (3' + r'$\sigma$)' + f": {ucl:.3f}", zorder=1)
    ax.axhline(lcl, color=chart_cfg.color_control_limits, linestyle='-', linewidth=2, 
               label=f'LCL (3' + r'$\sigma$)' + f": {ucl:.3f}", zorder=1)
    
     # 1 Sigma
    sigma_chart = (ucl - grand_avg) / 3
    
    one_sigma_upper = grand_avg + sigma_chart
    one_sigma_lower = grand_avg - sigma_chart

    ax.axhline(one_sigma_upper, color=chart_cfg.color_control_limits, linestyle=':', linewidth=2, zorder=1)
    ax.axhline(one_sigma_lower, color=chart_cfg.color_control_limits, linestyle=':', linewidth=2, zorder=1)
    
    two_sigma_upper = grand_avg + 2 * sigma_chart
    two_sigma_lower = grand_avg - 2 * sigma_chart
    
    ax.axhline(two_sigma_upper, color=chart_cfg.color_control_limits, linestyle='--', linewidth=1.5, zorder=1)
    ax.axhline(two_sigma_lower, color=chart_cfg.color_control_limits, linestyle='--', linewidth=1.5, zorder=1)

    # Specification Limits
    if chart_cfg.usl is not None:
         ax.axhline(chart_cfg.usl, color=chart_cfg.color_spec_limits, linestyle='-', linewidth=1.5, 
                    label=f'USL: {chart_cfg.usl:.3f}', zorder=1)
    if chart_cfg.lsl is not None:
         ax.axhline(chart_cfg.lsl, color=chart_cfg.color_spec_limits, linestyle='-', linewidth=1.5, 
                    label=f'LSL: {chart_cfg.lsl:.3f}', zorder=1)
            
    # Plot OOC points
    if not out_of_control_points.empty:
        is_ooc = subgroup_data['original_index'].isin(out_of_control_points.index)
        
        ax.scatter(
            subgroup_data.index[is_ooc], 
            subgroup_data[is_ooc]['mean'], 
            marker='o', 
            color=chart_cfg.color_out_of_control, 
            label='OOC',
            s=70, 
            zorder=3
        )
    # Plot OOS points 
    if not out_of_specification_points.empty:
        is_oos = subgroup_data['original_index'].isin(out_of_specification_points.index)
        
        ax.scatter(
            subgroup_data.index[is_oos], 
            subgroup_data[is_oos]['mean'], 
            marker='x',
            color=chart_cfg.color_out_of_specification, 
            label='OOS',
            s=70, 
            zorder=3
        )

    # Annotations and Labels (Glass ID for each point)
    for index, row in subgroup_data.iterrows():
        subgroup_label = row['Glass ID']
        
        ax.annotate(
            subgroup_label, 
            (index, row['mean']), 
            textcoords="offset points", 
            xytext=(5, 5), 
            ha='left', 
            fontsize=12,
            rotation=45, 
            zorder=4 
        )
    
    # Draw vertical lines and date labels for chronological index
    subgroup_data['Date_str'] = subgroup_data['Date'].dt.strftime('%m-%d-%Y')
    # Use sort=False to maintain original chronological order
    date_boundaries = subgroup_data.groupby('Date_str', sort=False).apply(lambda g: g.index.min()).tolist()

    for i, idx in enumerate(date_boundaries):
        date_label = subgroup_data.loc[idx, 'Date_str']
        ax.axvline(x=idx, color='gray', linestyle='--', linewidth=1, zorder=0)
        ax.text(
            x=idx,
            y=ax.get_ylim()[1], 
            s=date_label,
            rotation=90,
            verticalalignment='top',
            horizontalalignment='center',
            fontsize=12,
            color='black',
            zorder=0
        )

    cpk_str = f"N/A" if cpk is None else f"{cpk:.3f}"
    title = f"X-bar Chart, Cpk: {cpk_str}" 

    ax.set_title(title, fontsize=14)
    ax.set_xlabel(chart_cfg.xlabel, fontsize=14)
    ax.set_ylabel(f"{data_cfg.y_data_name}", fontsize=14)
    ax.legend(loc=chart_cfg.legend_location, fontsize=14)
    
    ax.set_xlim(x_positions.min() - 0.5, x_positions.max() + 0.5)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    
    plt.tight_layout()
    plt.savefig(output_filename, dpi=600)
    print(f"Chart saved: {output_filename}")
    plt.close(fig) 


def plot_r_chart(
    df_subgroups: pd.DataFrame, 
    data_cfg: DataConfig, 
    chart_cfg: ChartConfig, 
    avg: float, 
    ucl: float, 
    lcl: float, 
    out_of_control_points: pd.DataFrame,
    output_filename: str = "r_chart.png"
):
    """
    Generates the R control chart.
    """
    if df_subgroups is None or df_subgroups.empty:
        print("Cannot plot chart: No valid subgroups found.")
        return

    # FIX: Keep original index as a column for mapping OOC points
    subgroup_data = df_subgroups.copy().reset_index().rename(columns={'index': 'original_index'})
    x_positions = subgroup_data.index 

    fig, ax = plt.subplots(figsize=(14, 8))
        
    # Center Line
    ax.axhline(avg, 
              color=chart_cfg.color_avg, 
              linestyle='-', 
              linewidth=1.5, 
              label=r'Average Range ($\bar{{R}}$): '+ f"{avg:.3f}",
              zorder=1
    )

    # Plot Subgroup range
    ax.plot(
        x_positions, 
        subgroup_data['range'], 
        marker='o', 
        linestyle='-', 
        color=chart_cfg.color_in_control, 
        label=r'Subgroup Range (R)',
        zorder=2
    )
    
    # Control Limits
    ax.axhline(ucl, color=chart_cfg.color_control_limits, linestyle='-', linewidth=2, 
               label=f'UCL (3-sigma): {ucl:.3f}', zorder=1)
    ax.axhline(lcl, color=chart_cfg.color_control_limits, linestyle='-', linewidth=2, 
               label=f'LCL (3-sigma): {lcl:.3f}', zorder=1)
    
            
    # Plot OOC points (if any)
    if not out_of_control_points.empty:
        # FIX: Correctly map the original OOC indices to the new positional indices
        is_ooc = subgroup_data['original_index'].isin(out_of_control_points.index)
        
        ax.scatter(
            subgroup_data.index[is_ooc], 
            subgroup_data[is_ooc]['range'], 
            marker='o', 
            color=chart_cfg.color_out_of_control, 
            label='OOC',
            s=70, 
            zorder=3
        )
            
    # Annotations and Labels (Glass ID for each point)
    for index, row in subgroup_data.iterrows():
        subgroup_label = row['Glass ID']
        
        ax.annotate(
            subgroup_label, 
            (index, row['range']), 
            textcoords="offset points", 
            xytext=(5, 5), 
            ha='left', 
            fontsize=12,
            rotation=45, 
            zorder=4 
        )
    
    # Draw vertical lines and date labels for chronological index
    subgroup_data['Date_str'] = subgroup_data['Date'].dt.strftime('%m-%d-%Y')
    date_boundaries = subgroup_data.groupby('Date_str', sort=False).apply(lambda g: g.index.min()).tolist()

    for i, idx in enumerate(date_boundaries):
        date_label = subgroup_data.loc[idx, 'Date_str']
        ax.axvline(x=idx, color='gray', linestyle='--', linewidth=1, zorder=0)
        ax.text(
            x=idx,
            y=ax.get_ylim()[1], 
            s=date_label,
            rotation=90,
            verticalalignment='top',
            horizontalalignment='center',
            fontsize=12,
            color='black',
            zorder=0
        )

    title = f"R Chart" 

    ax.set_title(title, fontsize=14)
    ax.set_xlabel(chart_cfg.xlabel, fontsize=14)
    ax.set_ylabel(f"Range of {data_cfg.y_data_name}", fontsize=14)
    ax.legend(loc=chart_cfg.legend_location, fontsize=14)
    
    ax.set_xlim(x_positions.min() - 0.5, x_positions.max() + 0.5)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    #fig.legend(fontsize=14, loc='outside upper right')

    plt.tight_layout()
    plt.savefig(output_filename, dpi=600)
    print(f"Chart saved: {output_filename}")
    plt.close(fig) 


# S-Chart
def plot_s_chart(
    df_subgroups: pd.DataFrame, 
    data_cfg: DataConfig, 
    chart_cfg: ChartConfig, 
    avg: float, 
    ucl: float, 
    lcl: float, 
    out_of_control_points: pd.DataFrame,
    output_filename: str = "s_chart.png"
):
    """
    Generates the S control chart.
    """
    if df_subgroups is None or df_subgroups.empty:
        print("Cannot plot chart: No valid subgroups found.")
        return

    # FIX: Keep original index as a column for mapping OOC points
    subgroup_data = df_subgroups.copy().reset_index().rename(columns={'index': 'original_index'})
    x_positions = subgroup_data.index 

    fig, ax = plt.subplots(figsize=(14, 8))
        
    # Center Line
    ax.axhline(avg, 
              color=chart_cfg.color_avg, 
              linestyle='-', 
              linewidth=1.5, 
              label=r'Average $\bar{\sigma}$', 
              zorder=1
    )

    # Plot Subgroup std
    ax.plot(
        x_positions, 
        subgroup_data['std'], 
        marker='o', 
        linestyle='-', 
        color=chart_cfg.color_in_control, 
        label=r'Subgroup Std Dev ($\sigma$)', 
        zorder=2
    )
    
    # Control Limits
    ax.axhline(ucl, color=chart_cfg.color_control_limits, linestyle='-', linewidth=2, 
               label=f'UCL (3-sigma): {ucl:.3f}', zorder=1)
    ax.axhline(lcl, color=chart_cfg.color_control_limits, linestyle='-', linewidth=2, 
               label=f'LCL (3-sigma): {lcl:.3f}', zorder=1)
            
    # Plot OOC points (if any)
    if not out_of_control_points.empty:
        # FIX: Correctly map the original OOC indices to the new positional indices
        is_ooc = subgroup_data['original_index'].isin(out_of_control_points.index)
        
        ax.scatter(
            subgroup_data.index[is_ooc], 
            subgroup_data[is_ooc]['std'], # Plotting the std of the OOC points
            marker='o', 
            color=chart_cfg.color_out_of_control, 
            label='OOC',
            s=70, 
            zorder=3
        )
            
    # Annotations and Labels (Glass ID for each point)
    for index, row in subgroup_data.iterrows():
        subgroup_label = row['Glass ID']
        
        ax.annotate(
            subgroup_label, 
            (index, row['std']), 
            textcoords="offset points", 
            xytext=(5, 5), 
            ha='left', 
            fontsize=12,
            rotation=45, 
            zorder=4 
        )
    
    # Draw vertical lines and date labels for chronological index
    subgroup_data['Date_str'] = subgroup_data['Date'].dt.strftime('%m-%d-%Y')
    date_boundaries = subgroup_data.groupby('Date_str', sort=False).apply(lambda g: g.index.min()).tolist()

    for i, idx in enumerate(date_boundaries):
        date_label = subgroup_data.loc[idx, 'Date_str']
        ax.axvline(x=idx, color='gray', linestyle='--', linewidth=1, zorder=0)
        ax.text(
            x=idx,
            y=ax.get_ylim()[1], 
            s=date_label,
            rotation=90,
            verticalalignment='top',
            horizontalalignment='center',
            fontsize=12,
            color='black',
            zorder=0
        )

    title = f"S Chart" 

    ax.set_title(title, fontsize=14)
    ax.set_xlabel(chart_cfg.xlabel, fontsize=14)
    ax.set_ylabel(f"Standard Deviation of {data_cfg.y_data_name}", fontsize=14) # Changed ylabel
    ax.legend(loc=chart_cfg.legend_location, fontsize=14)
    
    ax.set_xlim(x_positions.min() - 0.5, x_positions.max() + 0.5)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    plt.tight_layout()
    plt.savefig(output_filename, dpi=600)
    print(f"Chart saved: {output_filename}")
    plt.close(fig) 


# MR-Chart
def plot_mr_chart(
    df_subgroups: pd.DataFrame, 
    data_cfg: DataConfig, 
    chart_cfg: ChartConfig, 
    avg: float, # Renamed to avg_mr for clarity
    ucl: float, 
    lcl: float, 
    out_of_control_points: pd.DataFrame,
    output_filename: str = "mr_chart.png"
):
    """
    Generates the MR control chart (for I-MR chart setups, monitoring the Moving Range).
    """
    if df_subgroups is None or df_subgroups.empty:
        print("Cannot plot chart: No valid subgroups found.")
        return

    # FIX: Keep original index as a column for mapping OOC points
    subgroup_data = df_subgroups.copy().reset_index().rename(columns={'index': 'original_index'})
    x_positions = subgroup_data.index 

    fig, ax = plt.subplots(figsize=(14, 8))
        
    # Center Line
    ax.axhline(avg, # Use avg_mr variable
              color=chart_cfg.color_avg, 
              linestyle='-', 
              linewidth=1.5, 
              label=r'Average Moving Range ($\bar{MR}}$)', # FIX: Corrected label
              zorder=1
    )

    # Plot moving range
    ax.plot(
        x_positions, 
        subgroup_data['moving_range'], # Corrected column name to 'moving_range'
        marker='o', 
        linestyle='-', 
        color=chart_cfg.color_in_control, 
        label=r'Moving Range (MR)', # FIX: Corrected label
        zorder=2
    )
    
    # Control Limits
    ax.axhline(ucl, color=chart_cfg.color_control_limits, linestyle='-', linewidth=2, 
               label=f'UCL (3-sigma): {ucl:.3f}', zorder=1)
    ax.axhline(lcl, color=chart_cfg.color_control_limits, linestyle='-', linewidth=2, 
               label=f'LCL (3-sigma): {lcl:.3f}', zorder=1)
    
            
    # Plot OOC points 
    if not out_of_control_points.empty:
        is_ooc = subgroup_data['original_index'].isin(out_of_control_points.index)
        
        ax.scatter(
            subgroup_data.index[is_ooc], 
            subgroup_data[is_ooc]['moving_range'], 
            marker='o', 
            color=chart_cfg.color_out_of_control, 
            label='OOC',
            s=70, 
            zorder=3
        )
            
    for index, row in subgroup_data.iterrows():
        subgroup_label = row['Glass ID']
        
        ax.annotate(
            subgroup_label, 
            (index, row['moving_range']), 
            textcoords="offset points", 
            xytext=(5, 5), 
            ha='left', 
            fontsize=12,
            rotation=45, 
            zorder=4 
        )
    
    # Draw vertical lines and date labels for chronological index
    subgroup_data['Date_str'] = subgroup_data['Date'].dt.strftime('%m-%d-%Y')
    date_boundaries = subgroup_data.groupby('Date_str', sort=False).apply(lambda g: g.index.min()).tolist()

    for i, idx in enumerate(date_boundaries):
        date_label = subgroup_data.loc[idx, 'Date_str']
        ax.axvline(x=idx, color='gray', linestyle='--', linewidth=1, zorder=0)
        ax.text(
            x=idx,
            y=ax.get_ylim()[1], 
            s=date_label,
            rotation=90,
            verticalalignment='top',
            horizontalalignment='center',
            fontsize=12,
            color='black',
            zorder=0
        )

    title = f"MR Chart" 

    ax.set_title(title, fontsize=14)
    ax.set_xlabel(chart_cfg.xlabel, fontsize=14)
    ax.set_ylabel(f"Moving Range of {data_cfg.y_data_name}", fontsize=14) 
    ax.legend(loc=chart_cfg.legend_location, fontsize=14)
    
    ax.set_xlim(x_positions.min() - 0.5, x_positions.max() + 0.5)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    plt.tight_layout()
    plt.savefig(output_filename, dpi=600)
    print(f"Chart saved: {output_filename}")
    plt.close(fig) 