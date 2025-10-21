# spc_analysis/core.py

import pandas as pd
from datetime import datetime
import os
from spc import DataConfig, TimeConfig, ChartConfig
from spc.metrics import calculate_control_limits, check_ooc, calculate_cpk
from spc.visualization import plot_xbar_chart

class SpcDataProcessor:
    def __init__(self, dataconfig: DataConfig, chartconfig: ChartConfig, timeconfig: TimeConfig, output_prefix: str):
        self.dataconfig = dataconfig
        self.chartconfig = chartconfig
        self.timeconfig = timeconfig
        self.output_prefix = output_prefix
        
        # Initialize internal state
        self.df_raw: pd.DataFrame = None
        self.df_processed: pd.DataFrame = None
        self.df_subgroups: pd.DataFrame = None
        self.invalid_groups: pd.DataFrame = None
        self.out_of_control_points: pd.DataFrame = None
        
        self.total_subgroups = 0
        self.total_valid_subgroups = 0
        self.total_invalid_subgroups = 0
        self.max_subgroup_size = 0
        
        self.grand_avg, self.grand_std, self.ucl, self.lcl, self.A3 = None, None, None, None, None
        self.cp, self.cpk = None, None

    def run_analysis(self):
        """Orchestrates the entire data processing and analysis pipeline."""
        self._load_data()
        if self.df_raw is None: return
        
        self._clean_and_convert_columns()
        self._filter_by_date()
        self._filter_by_column_entry()
        
        self._group_data()
        if self.df_subgroups is None: return

        self._calculate_metrics()
        self._generate_report()
        self._plot_xbar_chart()
        
        print(f"Analysis complete for {self.output_prefix}")

    # --- Data Loading and Cleaning Methods (Simplified/Refactored) ---

    def _load_data(self) -> None:
        # ... (Your existing _load_data logic remains, adjust imports if necessary)
        # Using a single method to load raw data
        try:
             self.df_raw = pd.read_excel(
                 self.dataconfig.filename,
                 sheet_name=self.dataconfig.sheet_name,
                 skiprows=self.dataconfig.skiprows,
                 header=self.dataconfig.header,
             )
             self.df_raw.columns = self.df_raw.columns.astype(str).str.strip()
        except Exception as e:
            print(f"Error loading data for {self.output_prefix}: {e}")
            self.df_raw = None

    def _clean_and_convert_columns(self) -> None:
        # ... (Your existing _clean_and_convert_columns logic)
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
        # ... (Your existing _filter_by_date logic)
        if self.df_processed is None or self.df_processed.empty: return
        
        start = self.timeconfig.start_dt
        end = self.timeconfig.end_dt
        
        mask = (self.df_processed['Date'] >= start) & (self.df_processed['Date'] <= end)
        self.df_processed = self.df_processed.loc[mask].copy()

    def _filter_by_column_entry(self) -> None:
        # ... (Your existing _filter_by_column_entry logic)
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
        """Groups data and handles inconsistent subgroup sizes."""
        if self.df_processed is None or self.df_processed.empty:
            print(f"Cannot group data for {self.output_prefix}: processed DataFrame is empty.")
            return

        y_col = self.dataconfig.y_data_name
        grouping_keys = self.dataconfig.grouping_keys
        
        agg = self.df_processed.groupby(grouping_keys, sort=True) # Sort=True for chronological order
        
        self.df_subgroups = agg[y_col].agg(['mean', 'std', 'size']).reset_index()
        
        if self.df_subgroups.empty:
            print(f"Cannot group data for {self.output_prefix}: no subgroups generated.")
            self.df_subgroups = None
            return

        # Handle inconsistent group sizes
        if self.df_subgroups['size'].empty: return
        self.max_subgroup_size = self.df_subgroups['size'].mode().iloc[0]
        
        valid_groups = self.df_subgroups[self.df_subgroups['size'] == self.max_subgroup_size]
        self.invalid_groups = self.df_subgroups[self.df_subgroups['size'] < self.max_subgroup_size]
        
        self.total_subgroups = len(self.df_subgroups)
        self.total_valid_subgroups = len(valid_groups)
        self.total_invalid_subgroups = len(self.invalid_groups)

        if not self.invalid_groups.empty:
            print(f"Inconsistent group sizes detected for {self.output_prefix}. Using {self.total_valid_subgroups}/{self.total_subgroups} valid subgroups (n={self.max_subgroup_size}).")
            
        self.df_subgroups = valid_groups.reset_index(drop=True)
        
    # --- Metrics and Reporting Methods ---
    
    def _calculate_metrics(self) -> None:
        """Calculates control limits, OOC points, and CpK."""
        if self.df_subgroups.empty: return

        # 1. Control Limits
        try:
             self.grand_avg, self.grand_std, self.ucl, self.lcl, self.A3 = \
                 calculate_control_limits(self.df_subgroups, self.max_subgroup_size)
        except ValueError as e:
            print(f"Error calculating control limits for {self.output_prefix}: {e}")
            return # Stop if limits can't be calculated

        # 2. OOC Check
        self.out_of_control_points = check_ooc(
            self.df_subgroups, 
            self.chartconfig, 
            self.grand_avg, 
            self.ucl, 
            self.lcl
        )
        
        # 3. CpK
        self.cp, self.cpk = calculate_cpk(self.chartconfig, self.grand_avg, self.grand_std)

    def _generate_report(self) -> None:
        """Generates a text report summarizing the analysis."""
        # ... (Your existing _generate_report logic, but use self.output_prefix)
        # Using a dedicated report generation function or moving the logic from here
        
        report_filename = f"spc_report.txt"
        
        usl_active = self.chartconfig.usl is not None
        lsl_active = self.chartconfig.lsl is not None
        
        with open(report_filename, 'w') as f:
             # --- (Write Report Content - using all self attributes) ---
             f.write("========================================================\n")
             f.write(f"           SPC REPORT           \n")
             f.write("========================================================\n")
             f.write(f"Date Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
             
             f.write("--- INPUT PARAMS AND FILTERS ---\n")
             f.write(f"Measured Variable (Y): {self.dataconfig.y_data_name}\n")
             f.write(f"Date Range: {self.timeconfig.start_dt.strftime('%m-%d-%Y')} to {self.timeconfig.end_dt.strftime('%m-%d-%Y')} \n")
             f.write(f"Column filters: {self.dataconfig.column_filters} \n\n")
             
             f.write("--- INCONSISTENT GROUP SIZE REPORT ---\n")
             f.write(f"Maximum Subgroup Size (n): {self.max_subgroup_size}\n")
             f.write(f"Total Subgroups: {self.total_subgroups}\n")
             f.write(f"Valid Subgroups: {self.total_valid_subgroups}\n")
             f.write(f"Invalid Subgroups: {self.total_invalid_subgroups}\n\n")
             
             f.write("--- Invalid Subgroup Details ---\n")
             if not self.invalid_groups.empty:
                 f.write(self.invalid_groups.to_string(index=False, float_format='%.3f'))
             else:
                 f.write("No inconsistent subgroup sizes identified.\n")
             f.write("\n")
             
             f.write("--- OOC POINTS REPORT ---\n")
             f.write(f"Out-of-Control Points Count: {len(self.out_of_control_points)}\n\n")
             
             f.write("--- Process Metrics ---\n")
             f.write(f"Grand Average (X-double-bar): {self.grand_avg:.6f}\n")
             f.write(f"Average Subgroup Std (S-bar): {self.grand_std:.6f}\n")
             f.write(f"A3 Constant Used: {self.A3:.4f}\n\n")
             
             f.write("--- Control Limits (Calculated) ---\n")
             f.write(f"UCL: {self.ucl:.6f}\n")
             f.write(f"LCL: {self.lcl:.6f}\n")
             f.write(f"OOC Check/Plotting Status: {'ACTIVE' if self.chartconfig.use_control_limits_ooc else 'INACTIVE'}\n\n")
             
             f.write("--- Specification Limits (Given) ---\n")
             f.write(f"USL: {self.chartconfig.usl if usl_active else 'N/A'}\n")
             f.write(f"LSL: {self.chartconfig.lsl if lsl_active else 'N/A'}\n")
             f.write(f"Limits Status: {'ACTIVE' if (usl_active or lsl_active) else 'INACTIVE'}\n\n")
             
             f.write("--- Process Capability (Cp/CpK) ---\n")
             cp_str = f"{self.cp:.3f}" if self.cp is not None else 'N/A'
             cpk_str = f"{self.cpk:.3f}" if self.cpk is not None else 'N/A'
             f.write(f"Cp: {cp_str}\n")
             f.write(f"CpK: {cpk_str}\n\n")

             f.write("--- Out-of-Control Points Details ---\n")
             if not self.out_of_control_points.empty:
                 f.write(self.out_of_control_points.to_string(index=False))
             else:
                 f.write("No Out-of-Control points identified. \n")
                 
             f.write("\n========================================================\n")
        
        print(f"Report generated: {os.path.abspath(report_filename)}")

    def _plot_xbar_chart(self):
        """Generates the X-bar chart using the visualization module."""
        # The visualization logic is now external, making this clean
        plot_xbar_chart(
            df_subgroups=self.df_subgroups,
            data_cfg=self.dataconfig,
            chart_cfg=self.chartconfig,
            grand_avg=self.grand_avg,
            ucl=self.ucl,
            lcl=self.lcl,
            cpk=self.cpk,
            out_of_control_points=self.out_of_control_points,
            output_filename=f"xbar_chart.png"
        )