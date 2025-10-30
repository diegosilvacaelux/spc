import pandas as pd
import numpy as np

def _calculate_sigma(ucl: float, lcl: float) -> float:
    """
    Calculates the standard deviation (sigma) of the plotted statistic
    based on the 3-sigma control limits. Assumes CL is (UCL + LCL) / 2.
    """
    cl = (ucl + lcl) / 2

    return (ucl - cl) / 3

def nelson_1(df: pd.DataFrame, column: str, ul: float, ll: float, new_column='Rule 1') -> pd.DataFrame:
    """
    Rule 1: One point is more than 3 standard deviations from the mean (outside UCL/LCL).
    """
    df_copy = df.copy()
    df_copy[new_column] = False
    ooc_mask = (df_copy[column] > ul) | (df_copy[column] < ll)
    df_copy.loc[ooc_mask, new_column] = True
    return df_copy

def nelson_2(df: pd.DataFrame, column: str, cl: float, new_column='Rule 2') -> pd.DataFrame:
    """
    Rule 2: Nine or more points in a row are on the same side of the mean.
    """
    df_copy = df.copy()
    df_copy[new_column] = False
    above_avg = (df_copy[column] > cl)
    # Compute run lengths
    groups = (above_avg != above_avg.shift()).cumsum()
    # For each run: count how many in that run up to each position
    run_length = above_avg.groupby(groups).cumcount() + 1
    # Only flag at or after the 9th point of a run
    df_copy.loc[run_length >= 9, new_column] = True
    return df_copy

def nelson_3(df: pd.DataFrame, column: str, new_column='Rule 3') -> pd.DataFrame:
    """
    Rule 3: Six or more points in a row are monotonically increasing or decreasing (a trend).
    """
    df_copy = df.copy()
    df_copy[new_column] = False
    diff_sign = np.sign(df_copy[column].diff().fillna(0))
    # Exclude zero changes to break a run (plateaus)
    diff_sign = diff_sign.replace({0: np.nan})
    groups = (diff_sign != diff_sign.shift()).cumsum()
    run_length = diff_sign.groupby(groups).cumcount() + 1
    df_copy.loc[run_length >= 6, new_column] = True
    return df_copy

def nelson_4(df: pd.DataFrame, column: str, new_column='Rule 4') -> pd.DataFrame:
    """
    Rule 4: Fourteen or more points in a row alternate in direction, increasing then decreasing.
    """
    df_copy = df.copy()
    df_copy[new_column] = False
    direction = np.sign(df_copy[column].diff().fillna(0))
    # Avoid zero diffs to maintain alternation logic
    direction = direction.replace({0: np.nan})
    alternating = (direction * direction.shift(1) == -1).fillna(False)
    # Compute rolling sum of alternations (True=1). 14 points = 13 alternations.
    alt_sum = alternating.rolling(window=13, min_periods=13).sum()
    # Flag the 14th point (i.e., when alt_sum == 13 prior alternations)
    df_copy.loc[alt_sum == 13, new_column] = True
    return df_copy

def nelson_5(df: pd.DataFrame, column: str, cl: float, ucl: float, lcl: float, new_column='Rule 5') -> pd.DataFrame:
    """
    Rule 5: Two out of three points in a row are more than 2 standard deviations from the mean 
    in the same direction (in Zone A or beyond).
    """
    df_copy = df.copy()
    df_copy[new_column] = False
    sigma = _calculate_sigma(ucl, lcl)

    two_sigma_u = cl + 2 * sigma
    two_sigma_l = cl - 2 * sigma

    above_2sigma = (df_copy[column] > two_sigma_u)
    below_2sigma = (df_copy[column] < two_sigma_l)

    # Rolling window of size 3; True if count is 2 or 3. Mask is True at the 3rd point.
    check_above = above_2sigma.rolling(window=3, min_periods=3).sum().isin([2, 3])
    check_below = below_2sigma.rolling(window=3, min_periods=3).sum().isin([2, 3])

    mask = check_above | check_below
    
    # Flag all 3 points involved in the violation (3rd, 2nd, and 1st)
    df_copy.loc[mask, new_column] = True             # Flag 3rd point
    df_copy.loc[mask.shift(1).fillna(False), new_column] = True # Flag 2nd point
    df_copy.loc[mask.shift(2).fillna(False), new_column] = True # Flag 1st point

    return df_copy

def nelson_6(df: pd.DataFrame, column: str, cl: float, ucl: float, lcl: float, new_column='Rule 6') -> pd.DataFrame:
    """
    Rule 6: Four out of five points in a row are more than one standard deviation from the mean 
    in the same direction (in Zone B, A, or beyond).
    """
    df_copy = df.copy()
    df_copy[new_column] = False
    sigma = _calculate_sigma(ucl, lcl)

    one_sigma_u = cl + sigma
    one_sigma_l = cl - sigma

    above_1sigma = (df_copy[column] > one_sigma_u)
    below_1sigma = (df_copy[column] < one_sigma_l)

    # Rolling window of size 5; True if count is 4 or 5. Mask is True at the 5th point.
    check_above = above_1sigma.rolling(window=5, min_periods=5).sum().isin([4, 5])
    check_below = below_1sigma.rolling(window=5, min_periods=5).sum().isin([4, 5])

    mask = check_above | check_below
    
    # Flag all 5 points
    df_copy.loc[mask, new_column] = True             
    df_copy.loc[mask.shift(1).fillna(False), new_column] = True 
    df_copy.loc[mask.shift(2).fillna(False), new_column] = True 
    df_copy.loc[mask.shift(3).fillna(False), new_column] = True 
    df_copy.loc[mask.shift(4).fillna(False), new_column] = True 

    return df_copy

def nelson_7(df: pd.DataFrame, column: str, cl: float, ucl: float, lcl: float, new_column='Rule 7') -> pd.DataFrame:
    """
    Rule 7: Fifteen points in a row are all within one standard deviation of the mean on either side 
    of the mean (in Zone C only). This indicates stratification.
    """
    df_copy = df.copy()
    df_copy[new_column] = False
    sigma = _calculate_sigma(ucl, lcl)

    one_sigma_u = cl + sigma
    one_sigma_l = cl - sigma

    in_zone_c = (df_copy[column] <= one_sigma_u) & (df_copy[column] >= one_sigma_l)
    mask = in_zone_c.rolling(window=15, min_periods=15).apply(lambda x: x.all(), raw=True).astype(bool).fillna(False)

    df_copy.loc[mask, new_column] = True

    return df_copy

def nelson_8(df: pd.DataFrame, column: str, cl: float, ucl: float, lcl: float, new_column='Rule 8') -> pd.DataFrame:
    """
    Rule 8: Eight points in a row exist but none within one standard deviation of the mean 
    and the points are in both directions of the mean (in Zone A or B only). This indicates a mixture.
    """
    df_copy = df.copy()
    df_copy[new_column] = False
    sigma = _calculate_sigma(ucl, lcl)

    one_sigma_u = cl + sigma
    one_sigma_l = cl - sigma

    above = (df_copy[column] > one_sigma_u)
    below = (df_copy[column] < one_sigma_l)
    outside_zone_c = above | below

    
    all_outside = outside_zone_c.rolling(window=8, min_periods=8).apply(lambda x: x.all(), raw=True).astype(bool).fillna(False)
    
    any_above = above.rolling(window=8, min_periods=8).max().astype(bool).fillna(False)
    
    any_below = below.rolling(window=8, min_periods=8).max().astype(bool).fillna(False)
    
    mask = all_outside & any_above & any_below
    
    for k in range(8):
        df_copy.loc[mask.shift(k).fillna(False), new_column] = True

    return df_copy