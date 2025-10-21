# spc_analysis/visualization.py

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
    output_filename: str = "xbar_chart.png"
):
    """
    Generates the X-bar control chart.
    """
    if df_subgroups is None or df_subgroups.empty:
        print("Cannot plot chart: No valid subgroups found.")
        return

    subgroup_data = df_subgroups.copy().reset_index(drop=True)
    x_positions = subgroup_data.index 

    fig, ax = plt.subplots(figsize=(14, 8))
        
    # Center Line
    ax.axhline(grand_avg, 
               color=chart_cfg.color_grand_avg, 
               linestyle='-', 
               linewidth=1.5, 
               label=r'Grand Average ($\bar{\bar{{X}}}$)',
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
    if chart_cfg.use_control_limits_ooc:
        ax.axhline(ucl, color=chart_cfg.color_control_limits, linestyle='-', linewidth=2, 
                   label=f'UCL (3-sigma): {ucl:.3f}', zorder=1)
        ax.axhline(lcl, color=chart_cfg.color_control_limits, linestyle='-', linewidth=2, 
                   label=f'LCL (3-sigma): {lcl:.3f}', zorder=1)
    
    # Specification Limits
    if chart_cfg.usl is not None:
         ax.axhline(chart_cfg.usl, color=chart_cfg.color_spec_limits, linestyle='--', linewidth=1.5, 
                    label=f'USL: {chart_cfg.usl:.3f}', zorder=1)
    if chart_cfg.lsl is not None:
         ax.axhline(chart_cfg.lsl, color=chart_cfg.color_spec_limits, linestyle='--', linewidth=1.5, 
                    label=f'LSL: {chart_cfg.lsl:.3f}', zorder=1)
            
    # Plot OOC points (if any)
    if not out_of_control_points.empty:
        # Map the original index of OOC points to the new, 0-based sequential index
        ooc_indices = out_of_control_points.index.map(lambda x: subgroup_data.index[subgroup_data.index == x][0])
        ax.scatter(
            ooc_indices, 
            out_of_control_points['mean'], 
            marker='o', 
            color=chart_cfg.color_out_of_control, 
            label='Out of Control Point',
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
            fontsize=8,
            rotation=45, 
            zorder=4 
        )
    
    # Draw vertical lines and date labels for chronological index
    # Note: df_subgroups should already be ordered chronologically by your grouping logic
    subgroup_data['Date_str'] = subgroup_data['Date'].dt.strftime('%m-%d-%Y')
    date_boundaries = subgroup_data.groupby('Date_str').apply(lambda g: g.index.min()).tolist()

    for i, idx in enumerate(date_boundaries):
        date_label = subgroup_data.loc[idx, 'Date_str']
        ax.axvline(x=idx, color='gray', linestyle='--', linewidth=1, zorder=0)
        ax.text(
            x=idx,
            y=ax.get_ylim()[0], 
            s=date_label,
            rotation=90,
            verticalalignment='bottom',
            horizontalalignment='center',
            fontsize=8,
            color='black',
            zorder=0
        )

    cpk_str = f"N/A" if cpk is None else f"{cpk:.3f}"
    title = f"X-bar Chart: {data_cfg.y_data_name}, Cpk: {cpk_str}" 

    ax.set_title(title)
    ax.set_xlabel(chart_cfg.xlabel)
    ax.set_ylabel(f"{data_cfg.y_data_name} (units)")
    ax.legend(loc=chart_cfg.legend_location)
    
    ax.set_xlim(x_positions.min() - 0.5, x_positions.max() + 0.5)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    plt.tight_layout()
    plt.savefig(output_filename, dpi=600)
    print(f"Chart saved: {output_filename}")
    plt.close(fig) # Use plt.close(fig) to prevent excessive memory usage with multiple plots