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
# SPC Data Processing and Analysis Orchestrator
# ======================================================================
#
# Purpose:
# The SpcDataProcessor class manages the entire workflow for a single 
# X-bar control chart analysis defined by a set of configuration objects. 
# It orchestrates loading, cleaning, filtering, metric calculation, 
# reporting, and visualization.
#
# Workflow Handled by Methods:
# 1. Data Loading and Cleaning (from Excel).
# 2. Filtering by time range and categorical columns.
# 3. Grouping data into consistent subgroups (subgroup size 'n').
# 4. Calculating control limits (UCL/LCL) and process capability (Cp/CpK).
# 5. Flagging and reporting out-of-control (OOC) points.
# 6. Generating a final text report and plot image.

# Imported modules
import pandas as pd
from datetime import datetime
import os
from typing import Optional

# Developed modules
from spc import DataConfig, TimeConfig, ChartConfig
from spc.visualization import plot_mr_chart, plot_r_chart, plot_s_chart, plot_xbar_chart
from spc.metrics import (
    calculate_control_limits_x_s, 
    calculate_control_limits_r, 
    calculate_control_limits_s,
    calculate_control_limits_i,
    calculate_control_limits_mr,
    check_ooc, 
    calculate_cpk
)

from spc.nelson_rules import (
    nelson_1,
    nelson_2,
    nelson_3,
    nelson_4,
    nelson_5,
    nelson_6,
    nelson_7,
    nelson_8
)

class SpcDataProcessor:
    """
    Processes raw data for Statistical Process Control (SPC) analysis,
    calculates control limits, detects OOC/OOS points, and generates reports.
    Supports X-bar/R, X-bar/S, and I/MR control charts.
    """
    def __init__(self, dataconfig: DataConfig, chartconfig: ChartConfig, timeconfig: TimeConfig, output_prefix: str):
        self.dataconfig = dataconfig
        self.chartconfig = chartconfig
        self.timeconfig = timeconfig
        self.output_prefix = output_prefix
        
        # Processed DataFrames
        self.df_raw: Optional[pd.DataFrame] = None
        self.df_processed: Optional[pd.DataFrame] = None
        self.df_subgroups: Optional[pd.DataFrame] = None
        self.invalid_groups: Optional[pd.DataFrame] = None
        
        # Results/Metrics
        self.process_sigma: float = 0.0
        self.highest_frequnecy_subgroup_size: int = 0
        self.cp: Optional[float] = None
        self.cpk: Optional[float] = None
        
        # Control Limits (Central Tendency - X-bar or I)
        self.cl_x: Optional[float] = None
        self.ucl_x: Optional[float] = None
        self.lcl_x: Optional[float] = None
        self.ooc_points_x: Optional[pd.DataFrame] = None
        self.oos_points_x: Optional[pd.DataFrame] = None
        
        # Control Limits (Variability - R, S, or MR)
        self.cl_v: Optional[float] = None
        self.ucl_v: Optional[float] = None
        self.lcl_v: Optional[float] = None
        self.ooc_points_v: Optional[pd.DataFrame] = None
        
        # Chart Type tracking
        self.variability_chart_type: str = "" # R, S, or MR
        self.central_tendency_chart_type: str = "" # X or I


    def run_analysis(self):
        """Orchestrates the entire data processing and analysis pipeline."""
        print(f"Starting SPC Analysis for {self.output_prefix}...")
        
        self._load_data()
        if self.df_raw is None: return
        
        self._clean_and_convert_columns()
        self._filter_by_date()
        self._filter_by_column_entry()
        
        self._group_data()
        if self.df_subgroups is None: return

        self._calculate_metrics()
        self._check_nelson()
        self._generate_report()
        self._plot_charts()

        print(f"Analysis complete for {self.output_prefix}. Charts generated.")

    # --- Data Loading and Cleaning Methods ---

    def _load_data(self) -> None:
        """Loads raw data from the configured Excel file."""
        try:
            self.df_raw = pd.read_excel(
                self.dataconfig.filename,
                sheet_name=self.dataconfig.sheet_name,
                skiprows=self.dataconfig.skiprows if self.dataconfig.skiprows is not None else 0,
                header=self.dataconfig.header,
            )
            # Clean column names
            self.df_raw.columns = self.df_raw.columns.astype(str).str.strip()
        except FileNotFoundError:
            print(f"Error: File not found at {self.dataconfig.filename}")
            self.df_raw = None
        except Exception as e:
            print(f"Error loading data for {self.output_prefix}: {e}")
            self.df_raw = None

    def _clean_and_convert_columns(self) -> None:
        """Selects required columns and converts them to appropriate types."""
        if self.df_raw is None: return
        
        cols_to_keep = self.dataconfig.required_columns
        xcol = self.dataconfig.y_data_name
        
        existing_cols = [c for c in cols_to_keep if c in self.df_raw.columns]
        
        if len(existing_cols) < len(cols_to_keep):
            missing_cols = set(cols_to_keep) - set(existing_cols)
            raise ValueError(f"Required columns missing from data for {self.output_prefix}: {missing_cols}")

        self.df_processed = self.df_raw.loc[:, existing_cols].copy()
        
        # Convert types (Date to datetime, Y data to numeric)
        self.df_processed['Date'] = pd.to_datetime(self.df_processed['Date'].astype(str).str.strip(), errors="coerce")
        self.df_processed[xcol] = pd.to_numeric(self.df_processed[xcol].astype(str).str.strip(), errors="coerce")
        
        # Drop rows where Date is NaT or Y data is NaN
        self.df_processed.dropna(subset=['Date', xcol], inplace=True)

        
    def _filter_by_date(self) -> None:
        """Filters the processed data by the configured date range."""
        if self.df_processed is None or self.df_processed.empty: return
        
        start = self.timeconfig.start_dt
        end = self.timeconfig.end_dt
        print(f"Filtering DataFrame for date range: {start} to {end}")
        mask = (self.df_processed['Date'] >= start) & (self.df_processed['Date'] <= end)
        self.df_processed = self.df_processed.loc[mask].copy()

    def _filter_by_column_entry(self) -> None:
        """Filters the processed data based on specific column values."""
        if self.df_processed is None or self.df_processed.empty: return
        
        filters = self.dataconfig.column_filters
        active_filters = {k: v for k, v in filters.items() if v is not None}
        
        if not active_filters: return
        
        combined_mask = pd.Series(True, index=self.df_processed.index)
        
        for column_name, value in active_filters.items():
            if column_name not in self.df_processed.columns: continue
                
            self.df_processed[column_name] = self.df_processed[column_name].astype(str).str.strip()
            current_mask = (self.df_processed[column_name].str.casefold() == str(value).strip().casefold())
            combined_mask = combined_mask & current_mask
            
        self.df_processed = self.df_processed.loc[combined_mask].copy()

    def _group_data(self) -> None:
        """Groups data by keys and calculates subgroup statistics, handling $n=1$ case."""
        if self.df_processed is None or self.df_processed.empty:
            print(f"Cannot group data. Processed DataFrame is empty.")
            return

        y_col = self.dataconfig.y_data_name
        grouping_keys = self.dataconfig.grouping_keys
        
        if not grouping_keys:
            # If no grouping keys are provided, each row is a subgroup of size n=1
            self.df_subgroups = self.df_processed.rename(columns={y_col: 'mean'}).copy()
            self.df_subgroups['std'] = None
            self.df_subgroups['min'] = self.df_subgroups['mean']
            self.df_subgroups['max'] = self.df_subgroups['mean']
            self.df_subgroups['size'] = 1
        else:
            # Standard subgrouping
            agg = self.df_processed.groupby(grouping_keys, sort=False) 
            self.df_subgroups = agg[y_col].agg(['mean', 'std', 'min', 'max', 'size']).reset_index()

        self.df_subgroups['range'] = self.df_subgroups['max'] - self.df_subgroups['min']
        
        # Calculate Moving Range for all cases (used for I-MR when n=1)
        self.df_subgroups['moving_range'] = self.df_subgroups['mean'].diff().abs()

        if self.df_subgroups.empty:
            print(f"Cannot group data for {self.output_prefix}: no subgroups generated.")
            self.df_subgroups = None
            return

        # Handle inconsistent group sizes
        if self.df_subgroups['size'].empty: return
        
        # Determine the highest frequency subgroup size
        size_counts = self.df_subgroups['size'].value_counts()
        self.highest_frequnecy_subgroup_size = size_counts.index[0]
        
        # Filter down to the mode size (only relevant for n > 1)
        if self.highest_frequnecy_subgroup_size > 1:
            valid_groups = self.df_subgroups[self.df_subgroups['size'] == self.highest_frequnecy_subgroup_size]
            self.invalid_groups = self.df_subgroups[self.df_subgroups['size'] != self.highest_frequnecy_subgroup_size]
        
            total_subgroups = len(self.df_subgroups)
            total_valid_subgroups = len(valid_groups)
            total_invalid_subgroups = len(self.invalid_groups)

            if not self.invalid_groups.empty:
                print(f"Inconsistent group sizes detected. Using {total_valid_subgroups}/{total_subgroups} valid subgroups (n={self.highest_frequnecy_subgroup_size}).")
            
            self.df_subgroups = valid_groups.reset_index(drop=True)
        else:
            # For n=1, all are valid, and invalid_groups remains empty
            self.invalid_groups = pd.DataFrame()


    # --- Metrics Calculation and OOC Check ---
    
    def _calculate_metrics(self) -> None:
        """Calculates control limits, OOC points, and CpK based on subgroup size."""
        if self.df_subgroups is None or self.df_subgroups.empty: return

        n = self.highest_frequnecy_subgroup_size
        
        try:
            # 1. Calculate Control Limits (Central Tendency & Variability)
            if n == 1:
                # --- I-MR Charts ---
                self.central_tendency_chart_type = 'I'
                self.variability_chart_type = 'MR'
                
                self.cl_x, mr_bar, self.ucl_x, self.lcl_x, E2, self.process_sigma = \
                    calculate_control_limits_i(self.df_subgroups)
                
                self.cl_v, self.ucl_v, self.lcl_v, D3, D4 = \
                    calculate_control_limits_mr(self.df_subgroups)
                
                central_data_col = 'mean'
                variability_data_col = 'moving_range'

            elif n >= 2 and n < 10:
                # --- X-bar / R-bar Charts (Traditional choice for n < 10) ---
                self.central_tendency_chart_type = 'X'
                self.variability_chart_type = 'R'
                
                # Use X-bar/S-bar constants for X-bar limits as per user's original A3 table
                self.cl_x, s_bar, self.ucl_x, self.lcl_x, A3 = \
                    calculate_control_limits_x_s(self.df_subgroups, n)
                
                self.cl_v, self.ucl_v, self.lcl_v, D3, D4 = \
                    calculate_control_limits_r(self.df_subgroups, n)
                    
                # The process sigma is estimated by S-bar (which is used for CpK later)
                self.process_sigma = s_bar
                central_data_col = 'mean'
                variability_data_col = 'range'

            elif n >= 10 and n <= 15:
                # --- X-bar / S-bar Charts (Standard for n >= 10) ---
                self.central_tendency_chart_type = 'X'
                self.variability_chart_type = 'S'
                
                self.cl_x, s_bar, self.ucl_x, self.lcl_x, A3 = \
                    calculate_control_limits_x_s(self.df_subgroups, n)
                
                self.cl_v, self.ucl_v, self.lcl_v, B3, B4 = \
                    calculate_control_limits_s(self.df_subgroups, n)
                    
                self.process_sigma = s_bar
                central_data_col = 'mean'
                variability_data_col = 'std'
            else:
                raise ValueError(f"Subgroup size n={n} is not supported (Max n=15).")
        
        except ValueError as e:
            print(f"Error calculating control limits: {e}")
            return # Stop if limits can't be calculated
        except ZeroDivisionError as e:
            print(f"Calculation Error: {e}")
            return
        
        self.ooc_points_v = check_ooc(
            self.df_subgroups, 
            variability_data_col,
            self.ucl_v, 
            self.lcl_v,
        )
        
        # 5. CpK Calculation (Requires USL/LSL and process_sigma estimate)
        self.cp, self.cpk = calculate_cpk(self.chartconfig, self.cl_x, self.process_sigma)

    def _check_nelson(self) -> None:        
        self.test_ooc = nelson_1(
            df=self.df_subgroups.copy(), 
            column='mean',
            ul=self.ucl_x,
            ll=self.lcl_x
            )
        
        self.test_ooc = nelson_2(
            df=self.test_ooc,
            column='mean',
            cl=self.cl_x
        )

        self.test_ooc = nelson_3(
            df=self.test_ooc,
            column='mean',
        )

        self.test_ooc = nelson_4(
            df=self.test_ooc,
            column='mean',
        )

        self.test_ooc = nelson_5(
            df=self.test_ooc,
            column='mean',
            cl=self.cl_x,
            ucl=self.ucl_x,
            lcl=self.lcl_x
        )

        self.test_ooc = nelson_6(
            df=self.test_ooc,
            column='mean',
            cl=self.cl_x,
            ucl=self.ucl_x,
            lcl=self.lcl_x
        )

        self.test_ooc = nelson_7(
            df=self.test_ooc,
            column='mean',
            cl=self.cl_x,
            ucl=self.ucl_x,
            lcl=self.lcl_x
        )

        self.test_ooc = nelson_8(
            df=self.test_ooc,
            column='mean',
            cl=self.cl_x,
            ucl=self.ucl_x,
            lcl=self.lcl_x
        )
        usl = self.chartconfig.usl
        lsl = self.chartconfig.lsl
        self.test_ooc = nelson_1(
            df=self.test_ooc,
            column='mean',
            ul=usl,
            ll=lsl,
            new_column='OOS'
        )

    # --- Reporting and Plotting Methods ---
    
    def _generate_report(self) -> None:
        """Generates a comprehensive text report summarizing the analysis, 
        with detailed breakdown for each control rule violation."""
        
        if self.test_ooc is None:
            print("Error: OOC/OOS analysis data (self.test_ooc) not initialized.")
            return

        # 1. Define the standard descriptive columns
        STANDARD_COLS = [
            col for col in ['Date'] + self.dataconfig.grouping_keys + ['mean', 'std', 'min', 'max', 
            'size', 'range', 'moving_range'] if col in self.test_ooc.columns
        ]
        
        # 2. Define the columns containing the boolean Rule flags
        NELSON_RULES_COLS = [f'Rule {i}' for i in range(1, 9)]
        
        report_filename = f"spc_report.txt"
        
        usl_active = self.chartconfig.usl is not None
        lsl_active = self.chartconfig.lsl is not None
        
        total_subgroups = len(self.df_subgroups) if self.df_subgroups is not None else 0
        
        with open(report_filename, 'w') as f:
            # --- Header ---
            f.write("=" * 60 + "\n")
            f.write(f" SPC REPORT: {self.central_tendency_chart_type}-CHART / {self.variability_chart_type}-CHART \n")
            f.write("=" * 60 + "\n")
            f.write(f"Date Generated: {datetime.now().strftime('%m-%d-%Y %H:%M:%S')}\n\n")

            # --- Input Summary ---
            f.write("--- INPUT AND DATA SUMMARY ---\n")
            f.write(f"Measured Variable: {self.dataconfig.y_data_name}\n")
            f.write(f"Chart Type Used: {self.central_tendency_chart_type}/{self.variability_chart_type}\n")
            f.write(f"Subgroup Size (n): {self.highest_frequnecy_subgroup_size}\n")
            f.write(f"Total Valid Subgroups Analyzed: {total_subgroups}\n")
            f.write(f"Invalid Subgroups Ignored: {len(self.invalid_groups) if self.invalid_groups is not None else 0}\n\n")

            # --- Invalid subgroup details ---
            f.write("--- INVALID SUBGROUP DETAILS ---\n")
            if self.invalid_groups is not None and not self.invalid_groups.empty:
                # Select key columns for invalid groups report
                invalid_cols = [c for c in ['Date'] + self.dataconfig.grouping_keys + ['size'] if c in self.invalid_groups.columns]
                f.write(self.invalid_groups[invalid_cols].to_string(index=False))
                f.write("\n\n")
            else:
                f.write("No inconsistent subgroup sizes identified.\n\n")

            # --- Central Tendency Chart Report (I or X-bar) ---
            f.write(f"--- {self.central_tendency_chart_type}-CHART CONTROL LIMITS ---\n")
            f.write(f"Center Line (CL): {self.cl_x:.6f}\n")
            f.write(f"UCL: {self.ucl_x:.6f}\n")
            f.write(f"LCL: {self.lcl_x:.6f}\n")
            f.write(f"Process Sigma Estimate: {self.process_sigma:.6f}\n\n")

            # --- DETAILED OOC BREAKDOWN (X-Chart) ---
            f.write("--- DETAILED OOC (Out-of-Control) VIOLATIONS ---\n")
            
            # Calculate Total Unique OOC Points
            rule_cols_in_df = [col for col in NELSON_RULES_COLS if col in self.test_ooc.columns]
            
            if rule_cols_in_df:
                unique_ooc_violations = self.test_ooc[self.test_ooc[rule_cols_in_df].any(axis=1)]
                ooc_total_count = len(unique_ooc_violations)
            else:
                 ooc_total_count = 0
            
            f.write(f"Total Unique OOC Points Identified: {ooc_total_count}\n")
            
            for rule_col in NELSON_RULES_COLS:
                # **CRITICAL CHANGE**: Use self.test_ooc for all rule violation checks
                if rule_col in self.test_ooc.columns:
                    
                    # Filter for rows where the current rule is True
                    rule_violations = self.test_ooc[self.test_ooc[rule_col] == True]
                    
                    # Define the columns for the report section: Standard columns + the specific Rule column
                    output_cols = STANDARD_COLS + [rule_col]
                    
                    f.write(f"\n--- VIOLATIONS OF {rule_col} ---\n")
                    f.write(f"Count: {len(rule_violations)}\n")
                    
                    if not rule_violations.empty:
                        # Select only the necessary columns for display
                        f.write(rule_violations[output_cols].to_string(index=False, float_format='%.6f'))
                        f.write("\n")
                    else:
                        f.write(f"No points violated {rule_col}.\n")

            
            # --- Variability Chart Report (MR, R, or S) ---
            f.write(f"\n--- {self.variability_chart_type}-CHART CONTROL LIMITS ---\n")
            f.write(f"Center Line (CL): {self.cl_v:.6f}\n")
            f.write(f"UCL: {self.ucl_v:.6f}\n")
            f.write(f"LCL: {self.lcl_v:.6f}\n\n")
            
            f.write("--- VARIABILITY CHART OOC POINTS (Rule 1 Only) ---\n") 
            if self.ooc_points_v is not None and not self.ooc_points_v.empty:
                 f.write(f"Count: {len(self.ooc_points_v)}\n")
                 var_data_col = {'R': 'range', 'S': 'std', 'MR': 'moving_range'}.get(self.variability_chart_type, 'range')
                 output_cols = [c for c in STANDARD_COLS if c not in ['std', 'range', 'moving_range']] + [var_data_col]
                 f.write(self.ooc_points_v[output_cols].to_string(index=False, float_format='%.6f'))
                 f.write("\n")
            else:
                f.write("No Out-of-Control points identified in the variability chart.\n")
            
            # --- Specification and Capability Report ---
            f.write("\n--- SPECIFICATION AND CAPABILITY ---\n")
            f.write(f"USL: {self.chartconfig.usl if usl_active else 'N/A'}\n")
            f.write(f"LSL: {self.chartconfig.lsl if lsl_active else 'N/A'}\n")
            f.write(f"Limits Status: {'ACTIVE' if (usl_active or lsl_active) else 'INACTIVE'}\n")
            
            cp_str= f"{self.cp:.3f}" if self.cp is not None else 'N/A'
            cpk_str = f"{self.cpk:.3f}" if self.cpk is not None else 'N/A'
            f.write(f"Cp: {cp_str}\n")
            f.write(f"Cpk: {cpk_str}\n")
            
            # --- DETAILED OOS BREAKDOWN ---
            OOS_COL = 'OOS'
            f.write("\n--- OOS (Out-of-Specification) POINTS ---\n")
            
            # **CRITICAL CHANGE**: Use self.test_ooc for OOS violation check
            if OOS_COL in self.test_ooc.columns:
                oos_violations = self.test_ooc[self.test_ooc[OOS_COL] == True]
                
                f.write(f"Count: {len(oos_violations)}\n")
                
                if not oos_violations.empty:
                    # Define the columns for the OOS report: Standard columns + OOS column
                    output_cols = STANDARD_COLS + [OOS_COL]
                    
                    # Select and write the data
                    f.write(oos_violations[output_cols].to_string(index=False, float_format='%.6f'))
                    f.write("\n")
                else:
                    f.write("No Out-of-Specification points identified.\n")
            else:
                f.write("OOS analysis not performed (Specification Limits not provided or 'OOS' column missing).\n")

            f.write("=" * 60 + "\n")

        print(f"Report generated: {os.path.abspath(report_filename)}")


    def _plot_charts(self):
        """Generates plots for the Central Tendency and Variability charts."""
        # Central Tendency Plot
        print(self.test_ooc.head())

        plot_func_x = plot_xbar_chart if self.central_tendency_chart_type == 'X' else None # Assuming plot_xbar_chart also handles 'I'
        if self.central_tendency_chart_type == 'I': 
            # Placeholder: In a real environment, you'd likely use a dedicated plot_i_chart
            plot_func_x = plot_xbar_chart 
        
        rule_ls = ['Rule 1', 'Rule 2', 'Rule 3', 'Rule 4', 
                   'Rule 5', 'Rule 6', 'Rule 7', 'Rule 8']
        
        if plot_func_x:
            df_oos = self.test_ooc[self.test_ooc['OOS']== True]
            for rule in rule_ls:
                df_ooc = self.test_ooc[self.test_ooc[rule]== True]
                plot_func_x(
                    df_subgroups=self.test_ooc,
                    data_cfg=self.dataconfig,
                    chart_cfg=self.chartconfig,
                    grand_avg=self.cl_x,
                    ucl=self.ucl_x,
                    lcl=self.lcl_x,
                    cpk=self.cpk,
                    out_of_control_points=df_ooc,
                    out_of_specification_points=df_oos,
                    output_filename=f"{rule.replace(' ', '')}_{self.central_tendency_chart_type}chart.png",
                )

        # Variability Plot
        plot_func_v = None
        if self.variability_chart_type == 'R':
            plot_func_v = plot_r_chart

        elif self.variability_chart_type == 'S':
            plot_func_v = plot_s_chart

        elif self.variability_chart_type == 'MR':
            plot_func_v = plot_mr_chart

        if plot_func_v:
            print(f"{self.output_prefix}_{self.variability_chart_type}chart.png")
            plot_func_v(
                df_subgroups=self.test_ooc,
                data_cfg=self.dataconfig,
                chart_cfg=self.chartconfig, # Re-using chart config for labels
                avg=self.cl_v,
                ucl=self.ucl_v,
                lcl=self.lcl_v,
                out_of_control_points=self.ooc_points_v,
                output_filename=f"{self.variability_chart_type}chart.png",
            )
            print(f"{self.variability_chart_type}chart.png")
