import os
from pathlib import Path
from typing import List

from tqdm import tqdm
import pandas as pd


#######################################################################################
#### BUILDING DATA

def get_building_name_list(data_folder: Path):
    
    building_name_list = [b.name for b in Path(data_folder).glob("*") if not b.name.endswith("xlsx")]
    
    return building_name_list


def get_building_metadata_df(data_folder: Path,
                             building_list: List[str] = None):
    
    df = pd.read_excel(data_folder.joinpath("Potential objects.xlsx"))
    
    if building_list is not None:
        building_ids = [b.split("-")[0] for b in building_list]
        pat = '|'.join(r"\b{}\b".format(x) for x in building_ids)
        
        df = df.loc[df["Addr meter"].str.contains(pat), :]
        df
    
    return df


def get_building_data_raw_files(data_folder: Path,
                                building_name: str):
    
    data_files = data_folder.joinpath(building_name).glob("*")
    
    dfs = []
    for file in data_files:
        
        if file.name.endswith("json"):
            temp_df = pd.read_json(file,
                                   convert_dates=["time"])
            temp_df.set_index("time", inplace=True)
        elif file.name.endswith("xls"):
            temp_df = pd.read_excel(file,
                                    skiprows=11,
                                    header=1)
            temp_df.rename(columns={"Čas": "time",
                                    "Stav provozní": "value"},
                           inplace=True)
            temp_df = temp_df[["time", "value"]]
            
            temp_df = temp_df.iloc[:temp_df[(temp_df["time"] == "Celkem") == True].index.tolist()[0]]
            
            temp_df["time"] = pd.to_datetime(temp_df["time"], format="mixed")
            temp_df["time"] = temp_df["time"].dt.tz_localize("CET", ambiguous="NaT", nonexistent="shift_forward")
            
            temp_df.dropna(axis=0, inplace=True)
            
            temp_df.set_index("time", inplace=True)
            
        else:
            raise RuntimeError("Unexpected file ending")
        
        dfs.append(temp_df)
        
    return dfs


def get_building_data_df(data_folder: Path,
                         building_name: str):
    
    dfs = get_building_data_raw_files(data_folder,
                                      building_name)
        
    df = pd.concat(dfs)
    df = df[~df.index.duplicated()]
    df.sort_index(inplace=True)
    
    return df


def get_all_buildings_data_df(data_folder: Path):
    
    building_names = get_building_name_list(data_folder)

    dfs = []
    column_names = []
    for building_name in tqdm(building_names, desc="Loading single building data"):
        temp_df = get_building_data_df(data_folder, building_name)
        
        dfs.append(temp_df["value"])
        column_names.append(building_name)
        
    temp_df = pd.concat(dfs, axis=1)
    temp_df.columns = column_names
    temp_df.index = pd.to_datetime(temp_df.index, utc=True)
    temp_df.sort_index(inplace=True)
        
    return temp_df


#######################################################################################
#### WEATHER DATA

def get_weather_data_dict_of_dfs(data_folder: Path):
    
    weather_data = {}

    for file in data_folder.glob("*"):
        
        station_id = file.name.split("_")[-1].split(".")[0]
        
        weather_data[station_id] = pd.read_parquet(file)
    
    return weather_data