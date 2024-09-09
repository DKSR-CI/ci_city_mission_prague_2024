
import os
from pathlib import Path
from typing import List

from tqdm import tqdm
import pandas as pd


def get_building_name_list(data_folder: Path):
    
    building_name_list = [b.name for b in Path(data_folder).glob("*") if not b.name.endswith("xlsx")]
    
    return building_name_list


def get_building_metadata_df(data_folder: Path,
                             building_list: List[str] = None):
    
    df = pd.read_excel(data_folder.joinpath("Potential objects.xlsx"))
    
    if building_list is not None:
        building_ids = [b.split("-")[0] for b in building_list]
        pat = '|'.join(r"\b{}\b".format(x) for x in building_ids)
        
        df = df.loc[df["Měřidlo"].str.contains(pat), :]
        df
    
    return df


def get_building_data_raw_files(data_folder: Path,
                                building_name: str):
    
    json_files = data_folder.joinpath(building_name).glob("*.json")
    
    dfs = []
    for file in json_files:
        temp_df = pd.read_json(file,
                               convert_dates=["time"])
        temp_df.set_index("time", inplace=True)
        
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

    df = pd.DataFrame()
    for building_name in tqdm(building_names, desc="Loading single building data"):
        temp_df = get_building_data_df(data_folder, building_name)
        df[building_name] = temp_df["value"]
        
    return df
