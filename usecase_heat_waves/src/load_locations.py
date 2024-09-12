import os
import sys
import streamlit as st
import requests
import folium
import pandas as pd
import geopandas as gpd
import plotly.express as px
import numpy as np
from shapely import wkt
from folium.plugins import MarkerCluster
from datetime import datetime
from streamlit_folium import st_folium, folium_static
from PIL import Image
from typing import List

DATA_PATH = "../data"
SRC_PATH = "./src"
GOLEMIO_KEY = os.environ.get("GOLEMIO_KEY")

sys.path.append(os.path.join(SRC_PATH, "heat_waves"))
import analyse_heatwaves as analyse_heatwaves
import plots as plot_lib



def get_golemio(data:str, golemio_key:str) -> dict:
    url = 'https://api.golemio.cz/' + data
    headers = {"X-Access-Token": golemio_key,
            'Accept': 'application/json'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Failed to retrieve data (status code {response.status_code})")
        return {response.text}

def get_measurement(id:int=None, measure:str="", start_date:str="", end_date:str=""):
    if id:
        if (int(id%10) == 0):
            id_str = f"locationId={id}"
        else:
            id_str = f"pointId={id}"
    else:
        id_str = ""
    if measure != "":
        measure_str = f"&measure={measure}"
    else:
        measure_str = ""
    if start_date != "":
        start_str = f"&from={start_date}"
    else:
        start_str = ""
    if end_date != "":
        end_str = f"&to={end_date}"
    else:
        end_str = ""

    query = f'/v2/microclimate/measurements?{id_str}{measure_str}{start_str}{end_str}'
    print(query)
    measurements = get_golemio(query, GOLEMIO_KEY)
    
    measurements_df = pd.DataFrame.from_dict(measurements)
    # Set datetime index
    if "measured_at" in measurements_df.columns:
        measurements_df["measured_at"] = pd.to_datetime(measurements_df.measured_at)
        measurements_df["measured_at"] = measurements_df["measured_at"].dt.round(freq="min")
        measurements_df.set_index("measured_at", inplace=True)
    return measurements_df

def compute_hourly(df):
    df_raw = df.copy()
    metadata = df_raw.iloc[0,:].drop("value")

    data = pd.DataFrame(df_raw.loc[:, "value"]).rename(columns={'value':metadata['measure']})
    hourly = data.resample("1h").agg("mean").round(1)
    return hourly, metadata

def compute_daily(df):
    df_raw = df.copy()
    metadata = df_raw.iloc[0,:].drop("value")

    data = pd.DataFrame(df_raw.loc[:, "value"]).rename(columns={'value':metadata['measure']})
    daily = data.resample("1D").agg(["max", "mean", "min"]).round(1)
    return daily, metadata

def get_id_hourly_daily(id:int, measures: List[str], 
                        start_date: str="", 
                        end_date: str="", 
                        save_path:str="") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    id_hourly_df = pd.DataFrame()
    id_daily_df = pd.DataFrame()
    metadata_df = pd.DataFrame()

    for m in measures:
        this_measure = get_measurement(id=id, measure=m, start_date=start_date, end_date=end_date)
        try:
            this_measure_hourly, metadata = compute_hourly(this_measure)
            # append metadata
            if len(metadata_df) == 0:
                metadata_df = pd.DataFrame(metadata).T
            else:
                metadata_df.loc[len(metadata_df)] = metadata
            # append hourly
            if len(id_hourly_df) == 0:
                id_hourly_df = this_measure_hourly
            else: 
                id_hourly_df = id_hourly_df.join(this_measure_hourly, how="outer")
            
            this_measure_daily, _ = compute_daily(this_measure)
            # append daily
            if len(id_daily_df) == 0:
                id_daily_df = this_measure_daily
            else: 
                id_daily_df = id_daily_df.join(this_measure_daily, how="outer")
            
        except:
            print(f"{m} has length {len(this_measure)}")
    
    # Write to csv
    date_str = ""
    if start_date != "":
        date_str += start_date.split("T")[0]
    if end_date != "":
        date_str += f"-{end_date.split('T')[0]}"
    else:
        date_str += f"-{datetime.today().strftime('%Y-%m-%d')}"
    # Flatten multilayer columns
    id_daily_df.columns = id_daily_df.columns.map('_'.join)

    if save_path != "":
        if not os.path.exists(save_path):
            os.mkdir(save_path)
        id_hourly_df.to_csv(os.path.join(save_path, f"{id}_{date_str}_hourly.csv"))
        id_daily_df.to_csv(os.path.join(save_path, f"{id}_{date_str}_daily.csv"))
        print("wrote hourly and daily files to ../data/interim")
    
    return id_hourly_df, id_daily_df, metadata_df

def get_measure(ids:list[int], measure: str, 
                        start_date: str="", 
                        end_date: str="", 
                        save_path:str="") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df_hourly = pd.DataFrame()
    df_daily = pd.DataFrame()
    metadata_df = pd.DataFrame()

    for id in ids:
        this_measure = get_measurement(id=id, measure=measure, start_date=start_date, end_date=end_date)
        try:
            this_measure_hourly, metadata = compute_hourly(this_measure)
            this_measure_hourly.rename(columns={measure:id}, inplace=True)
            # append metadata
            if len(metadata_df) == 0:
                metadata_df = pd.DataFrame(metadata).T
            else:
                metadata_df.loc[len(metadata_df)] = metadata

            # append hourly
            if len(df_hourly) == 0:
                df_hourly = this_measure_hourly
            else: 
                df_hourly = df_hourly.join(this_measure_hourly, how="outer")
            
            this_measure_daily, _ = compute_daily(this_measure)
            this_measure_daily.rename(columns={measure:id}, inplace=True)

            # append daily
            if len(df_daily) == 0:
                df_daily = this_measure_daily
            else: 
                df_daily = df_daily.join(this_measure_daily, how="outer")
            
        except:
            print(f"Sensor_{id}-{measure} has length {len(this_measure)}")
    
    # Flatten multilayer columns
    df_daily.columns = df_daily.columns.to_series().apply(lambda x: "{0}_{1}".format(*x)).values
    
    date_str = ""
    if start_date != "":
        date_str += start_date.split("T")[0]
    if end_date != "":
        date_str += f"-{end_date.split('T')[0]}"
    else:
        date_str += f"-{datetime.today().strftime('%Y-%m-%d')}"
    
    # Write to csv
    if save_path != "":
        if not os.path.exists(save_path):
            os.mkdir(save_path)
        df_hourly.to_csv(os.path.join(save_path, f"{measure}_{date_str}_hourly.csv"))
        df_daily.to_csv(os.path.join(save_path, f"{measure}_{date_str}_daily.csv"))
        print(f"wrote hourly and daily files to {save_path}")
    
    return df_hourly, df_daily, metadata_df
    
