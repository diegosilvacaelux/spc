from typing import Dict

# ----------------------------------------------------------------------
# A3, D3, D4, B3, B4 Constants for Subgroup Charts (n > 1)
# Max supported subgroup size is n=15 based on the provided table.
# ----------------------------------------------------------------------

# A3 constants for X-bar chart using subgroup standard deviation (S-bar)
A3_TABLE: Dict[int, float] = {
    2: 2.659, 3: 1.954, 4: 1.628, 5: 1.427, 6: 1.287, 7: 1.182, 8: 1.099, 9: 1.032, 10: 0.975, 11: 0.927, 12: 0.886, 13: 0.850, 14: 0.817, 15: 0.789
}

# D3 constants for R-chart (Lower Control Limit factor)
D3_TABLE: Dict[int, float] = {
    2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0.076, 8: 0.136, 9: 0.184, 10: 0.223, 11: 0.256, 12: 0.283, 13: 0.307, 14: 0.328, 15: 0.347
}

# D4 constants for R-chart (Upper Control Limit factor)
D4_TABLE: Dict[int, float] = {
    2: 3.268, 3: 2.574, 4: 2.282, 5: 2.114, 6: 2.004, 7: 1.924, 8: 1.864, 9: 1.816, 10: 1.777, 11: 1.744, 12: 1.717, 13: 1.693, 14: 1.672, 15: 1.653
}

# B3 constants for S-chart (Lower Control Limit factor)
B3_TABLE: Dict[int, float] = {
    2: 0, 3: 0, 4: 0, 5: 0, 6: 0.030, 7: 0.118, 8: 0.185, 9: 0.239, 10: 0.284, 11: 0.321, 12: 0.354, 13: 0.382, 14: 0.406, 15: 0.428
}

# B4 constants for S-chart (Upper Control Limit factor)
B4_TABLE: Dict[int, float] = {
    2: 3.267, 3: 2.568, 4: 2.266, 5: 2.089, 6: 1.970, 7: 1.882, 8: 1.815, 9: 1.761, 10: 1.716, 11: 1.679, 12: 1.646, 13: 1.618, 14: 1.594, 15: 1.572
}

# ----------------------------------------------------------------------
# Constants for Individual and Moving Range Charts (n = 1)
# ----------------------------------------------------------------------

# d2 constant for estimating process sigma from the average moving range (n=2 for MR)
# sigma_hat = MR_bar / d2(n=2)
# d2(n=2) = 1.128
D2_TABLE: Dict[int, float] = {
    2: 1.128 
}

# E2 constant can also be used for I-charts (UCL = X_bar +/- E2 * MR_bar),
# but using 3/d2 is more direct for process sigma calculation.
# E2 = 3 / d2(n=2) = 3 / 1.128 = 2.6595
E2_TABLE: Dict[int, float] = {
    2: 2.659  # For I-chart based on MR (Subgroup size n=2 for MR calculation)
}

# D4 constant for Moving Range chart (MR-chart)
# The MR chart is essentially an R-chart with n=2. D4(n=2) = 3.268.
# D3(n=2) = 0.
MR_D3_D4_TABLE: Dict[int, float] = {
    2: 0,
    4: 3.268 # D4 value for n=2 (used for MR chart)
}