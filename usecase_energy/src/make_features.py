from typing import Dict
from czech_holidays import czech_holidays
import pandas as pd
from datetime import date


def compute_time_features(df_in: pd.DataFrame,
                          use_datetimeindex: bool = True) -> pd.DataFrame:
    
    df = df_in.copy()

    holidays = czech_holidays(2021) + czech_holidays(2022) + czech_holidays(2023) + czech_holidays(2024)
    hd = [i[0] for i in holidays]

    if use_datetimeindex:
        time_col = df.index
    else:
        time_col = df["time"].dt
    
    df["year"] = time_col.year
    df["month"] = time_col.month
    df["day"] = time_col.day
    df["hour"] = time_col.hour
    df["day_of_year"] = time_col.day_of_year
    df["week_of_year"] = time_col.isocalendar().week
    df["day_of_week"] = time_col.weekday
    df["is_weekend"] = time_col.weekday >= 5
    df["hour_of_week"] = df["day_of_week"] * 24 + df["hour"]
    df["is_holiday"] = df["time_col"].isin(hd)
    
    return df


def compute_mean_of_dict_of_dfs(dict_of_dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:

    # Step 1: Concatenate all DataFrames along a new axis (axis=0 by default)
    concatenated_df = pd.concat(dict_of_dfs.values(), axis=0)

    # Step 2: Group by the index and calculate the mean for each cell
    mean_df = concatenated_df.groupby(concatenated_df.index).mean()

    return mean_df