import os
import pandas as pd
import geopandas as gpd
import numpy as np
import osmnx as ox
from tqdm import tqdm

# Import Meteostat library and dependencies
from datetime import datetime
from shapely import wkt
from meteostat import Point, Daily, Hourly, Stations
import folium
import warnings


def get_geometry(name:str):
    """Returns just the geometry for a location name.

    Args:
        name (str): name of a location (city, street, etc.)

    Returns:
        a shapely geometry object (point or polygon)
    """
    try:
        gdf = ox.geocode_to_gdf(name).to_crs("epsg:3857")
        return gdf["geometry"]
    except:
        return None

def get_stations_from_location(location: str, 
                        max_distance: int=20000, 
                        return_map: bool=False)->tuple:
    """Get the stations around a location

    Args:
        location (str): Name of a location
        max_distance (int, optional): Search radius. Defaults to 20000.
        return_map (bool, optional): If true, this will return a folium map showing the stations. Defaults to True.

    Returns:
        tuple (gpd.GeoDataFrame, folium.map): Returns a geodataframe of weather stations within the search radius and a map showing them
    """
    # Geocode the location to get a GeoDataFrame
    location_gdf = ox.geocode_to_gdf(location)
    
    # Get latitude and longitude from the GeoDataFrame
    lat = location_gdf.loc[0, "lat"]
    lon = location_gdf.loc[0, "lon"]
        
    # Get nearby stations
    stations = Stations()
    nearby_stations = stations.nearby(lat, lon).fetch(20)
    columns_to_drop = [c for c in nearby_stations if ("start" in c) or (
        "end" in c) or any([a in c for a in ["timezone", "wmo", "icao"]])]
    nearby_stations.drop(columns_to_drop, axis=1, inplace=True)
    nearby_stations["location"] = location
    nearby_stations.reset_index(inplace=True)
    nearby_stations.rename(columns={"name":"station_name", "id":"station_id"}, inplace=True)
    # Filter stations by distance and plot them
    nearby_stations = nearby_stations.loc[nearby_stations["distance"] < max_distance, :]

    if not return_map:
        return nearby_stations, None
    else:
        # Initialize a Folium map centered at the location
        m = folium.Map(location=[lat, lon], zoom_start=10)
        
        # Optionally, plot the boundary of the location if it's an area
        if 'geometry' in location_gdf.columns:
            folium.GeoJson(location_gdf['geometry']).add_to(m)
        for _, station in nearby_stations.iterrows():
            folium.Marker(
                location=[station["latitude"], station["longitude"]],
                popup=f"{station['station_name']} \n Distance: {round(station['distance']/1000,2)} Km \n Elevation: {station['elevation']}",
                icon=folium.Icon(icon="train", color="blue")
            ).add_to(m)
        
        # Return the map instead of DataFrame
        return nearby_stations, m

def compute_dwd_heatwave(data:pd.DataFrame):
    """ Calculate heatwave days according to the DWD
    Der Deutsche Wetterdienst (DWD) spricht von 
    einer Hitzewelle, sobald die Temperatur an 
    mindestens drei aufeinanderfolgenden Tagen über 28°C liegt.
    
    Args: data (pd.DataFrame): a weather dataframe returned by 
    """
    data["tmax>28"] = data["tmax"].apply(lambda x: 1 if x > 28 else 0)
    data["rolling_28_3"] = data["tmax>28"].rolling(3).sum().fillna(0)
    data["dwd_heatwave_day"] = data["rolling_28_3"] >= 3    
    data.drop(["tmax>28"], axis=1, inplace=True)
    return data
 
def compute_simple_stats(df):
    hot_days = df.copy()
    hot_days["year"] = hot_days.index.year
    hot_days['month_of_year'] = hot_days.index.month
    hot_days['day_of_year'] = hot_days.index.dayofyear
    hot_days[f'tmax>30'] = hot_days["tmax"].apply(lambda x: True if x > 30 else False)
    hot_days[f'tmin>20'] = hot_days["tmin"].apply(lambda x: True if x > 20 else False)
    return hot_days

def get_daily_station(station_id:str,  
                    start_year:int=2013, 
                    end_year:int=2023,
                    heatwave_definition:str="dwd", 
                    parameter:str="", 
                    threshold:int=100) -> pd.DataFrame:
    """Get daily data from a station and add some new columns

    Args:
        station_id (str): the meteostat station id
        start_year (int, optional): start year. Defaults to 2013.
        end_year (int, optional): end year. Defaults to 2023.
        heatwave_definition (str, optional): maybe in the future we will have other functions to determine a heatwave day. Defaults to "dwd".
        parameter (str, optional): optional parameter (eg. humidity) to test a condition. Defaults to "".
        threshold (int, optional): optional threshold to test the parameter. Defaults to 100.

    Returns:
        pd.DataFrame: _description_
    """
    # Set time period
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)

    # Get daily data for 2018
    data = Daily(station_id, start, end)
    data = data.fetch()

    # Create a DataFrame with a datetime index from start to end
    date_range = pd.date_range(start, end, freq='D')
    all_days = pd.DataFrame(index=date_range)

    if len(data) > 0:
        data = all_days.merge(data, how='left', left_index=True, right_index=True)
        hot_days = compute_simple_stats(data)
        
        if (parameter != "") and (threshold != 100):
            print(parameter, threshold)
            hot_days[f'{parameter}>{threshold}'] = hot_days[parameter].apply(lambda x: 1 if x > threshold else 0)

        if heatwave_definition == "dwd":
            hot_days = compute_dwd_heatwave(hot_days)
            # Assign a unique id to each heatwave event
            heatwaves = pd.DataFrame(hot_days.loc[hot_days["dwd_heatwave_day"]==True, "day_of_year"].diff().fillna(hot_days["day_of_year"])).rename(columns={"day_of_year":"days_elapsed"})
            heatwaves["year"] = heatwaves.index.year
            heatwaves["annual_index"] = heatwaves["year"].astype(str) + '_' + heatwaves.groupby('year')['days_elapsed'].apply(lambda x: (x > 1).cumsum()).values.astype(str)
            heatwaves.drop("year", inplace=True, axis=1)
            hot_days = pd.merge(hot_days, heatwaves, how='outer', left_index=True, right_index=True)

        return hot_days
    else:
        warnings.warn(f"Failed to load data for {station_id}")
        return pd.DataFrame()

def get_hourly_station(station_id:str,  
                            year:int=2018, 
                            start_month:int=7,
                            end_month:int=8) -> pd.DataFrame:
    """Get hourly weather from a station using the meteostat api

    Args:
        station_id (str): station id which can be obtained from the "id" column produced by get_stations_from_location (ie. Meteostat's Station object)
        year (int, optional): the year for which to fetch data. Defaults to 2018.
        start_month (int, optional): Defaults to 7.
        end_month (int, optional): Defaults to 8.

    Returns:
        pd.DataFrame: an hourly weather timeseries
    """
    # Set time period
    start = datetime(year, start_month, 1)
    end = datetime(year, end_month, 31)

    # Get daily data for 2018
    data = Hourly(station_id, start, end)
    data = data.fetch()

    # Create a DataFrame with a datetime index from start to end
    date_range = pd.date_range(start, end, freq='H')
    all_days = pd.DataFrame(index=date_range)

    if len(data) > 0:
        data = all_days.merge(data, how='left', left_index=True, right_index=True)
        hot_days = data.copy()

        hot_days["year"] = hot_days.index.year
        hot_days['month_of_year'] = hot_days.index.month
        hot_days['day_of_year'] = hot_days.index.dayofyear

        return hot_days
    else:
        warnings.warn(f"Failed to load data for {station_id}")
        return pd.DataFrame()

def get_daily_temperature_location(location:str, 
                            start_year:int=2013, 
                            end_year:int=2023, 
                            heatwave_definition:str="dwd", 
                            parameter:str="", 
                            threshold:int=100) -> pd.DataFrame:
    """Given a location, this function searches for stations within a radius and returns daily data for the first station it finds.

    Args:
        location (str): Location to get annual temperature for
        start_year (int, optional): First year to fetch temperatures. Defaults to 2013.
        end_year (int, optional): Year to fetch. Defaults to 2013.
        heatwave_definition(str, optional): refers to the heatwave methodololgy.
        parameter (str, optional): which column of the dataframe to use as a condition. eg. "tmax", "tmin". Defaults to "tmax".
        threshold (int, optional): Use this value to create a new boolean column if the temperature is above this value. Defaults to 30.

    Returns:
        pd.DataFrame: _description_
    """
    nearby_stations, _ = get_stations_from_location(location, return_map=False)
    
    # Set time period
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)

    # Loop through nearby_stations until some data is found
    data = pd.DataFrame()
    i = 0
    while (len(data) == 0) and (i<10) and (i<len(nearby_stations)):
        if i>0:
            print(f"No results for {location}")

        metadata = nearby_stations.reset_index().iloc[i, :]
        location_name = metadata["station_name"]
        print(f"Fetching daily weather for {location_name}")
        data = Daily(metadata["station_id"], start, end)
        data = data.fetch()

        daily_df = get_daily_station(station_id = metadata["station_id"],  
                              start_year=start_year, 
                              end_year=end_year,
                              heatwave_definition=heatwave_definition, 
                              parameter=parameter, 
                              threshold=threshold)
        
        i += 1

    if len(data) > 0:
        return daily_df
    else:
        return pd.DataFrame()
    
def group_heatwaves_station(station_daily_data:pd.DataFrame)->pd.DataFrame:
    """The DWD definition returns a boolean for whether a single day is a heatwave day. This function 
    returns a dataframe of heatwave events, where each event is a consecutive number of heatwave days.
    The returned dataframe contains the maximum temperature reached, the duration, start month and end month.

    Args:
        station_daily_data (pd.DataFrame): the output of get_daily_station

    Returns:
        pd.DataFrame: a dataframe where each row is an individual heatwave event for the weather station
    """
    heatwaves = station_daily_data.copy().reset_index().rename(columns={"index":"start_date"})
    heatwaves["end_date"] = heatwaves["start_date"]
    heatwaves = heatwaves.loc[:, ["year", "annual_index", "tavg", "tmax", "start_date", "end_date"]].groupby(["year", "annual_index"]).agg({"tavg":"count", "tmax":"max", "start_date":"min", "end_date":"max"}).rename(columns={"tavg":"duration"})
    heatwaves.reset_index(inplace=True)
    return heatwaves

def compute_hot_days_per_year(daily_df:pd.DataFrame) -> pd.DataFrame:
    """A wrapper around group_heatwaves_station which returns a dataframe where every row is a year.
    This is useful to show the number of heatwaves per year, longest heatwave, total number of heatwave days,
    hot days (T>30°C) and hot nights (T>20°C)

    Args:
        daily_df (pd.DataFrame): the output of get_station_daily

    Returns:
        pd.DataFrame: _description_
    """
    annual_hot_days = daily_df.loc[:, ["year", "tmax>30", "tmin>20", "dwd_heatwave_day"]].groupby("year").sum()
    
    heatwaves = group_heatwaves_station(daily_df)
    longest_heatwave_per_year = heatwaves.loc[:, ["year", "duration"]].groupby("year").agg("max").rename(columns={"duration":"longest_heatwave"})
    n_heatwaves_per_year = heatwaves.loc[:, ["year", "duration"]].groupby("year").agg("count").rename(columns={"duration":"n_heatwaves"})

    heatwaves_per_year = pd.concat([annual_hot_days, longest_heatwave_per_year, n_heatwaves_per_year], axis=1)
    return heatwaves_per_year

def compute_heat_stats(daily_df:pd.DataFrame, metadata:dict, additional_columns:list[str]=[])->dict:
    """Returns a dictionary representing a single weather station. The dictionary can be used to populate 
    a geodataframe and show heatwave trends on a map. The trends are assumed to be linear and calculated on 
    the output of compute_hot_days_per_year

    Args:
        daily_df (pd.DataFrame): the output of get_daily_station
        metadata (dict): a single row of the dataframe created by compute_heat_stats_stations 
        additional_columns (list[str], optional): _description_. Defaults to [].

    Returns:
        dict: 24 key value pairs with heat indicator trends for each station
    """
    # Sum and trend of hot days, hot nights, and DWD heatwave days
    hot_days = compute_hot_days_per_year(daily_df)
    totals_dict = hot_days.sum().to_dict()
    totals_dict = ({f"{k}_total":v for k, v in totals_dict.items()})

    trends = np.polyfit(hot_days.index, hot_days.to_numpy(), deg=1)[0]
    trends_dict = dict(zip([f"{t}_trend" for t in hot_days.columns], trends))
    trends_dict = {k:round(v, 3) for k,v in trends_dict.items()}

    metadata = {("station_name" if k == "name" else k): v for k, v in metadata.items()}
    keep_keys = list(metadata.keys())[:10]
    metadata = {k:v for k,v in metadata.items() if k in keep_keys}
    
    return {**metadata, **{"n_years":len(hot_days)}, **totals_dict, **trends_dict}

def compute_heat_stats_stations(stations:pd.DataFrame, save_path:str="", start:int=2013, end:int=2023) -> pd.DataFrame: 
    """Loops through a dataframe of stations containing a column called "station_id" and runs compute_heat_stats for
    each station. Once the loop is complete, mean metrics for some heatwave parameters are calculated in this function.

    Args:
        stations (pd.DataFrame): output of get_stations_from_location
        save_path (str, optional): path to save the dataframe. Defaults to "".
        start (int, optional): Analysis start year. Defaults to 2013.
        end (int, optional): Analysis end year. Defaults to 2023.

    Returns:
        pd.DataFrame: a dataframe where each row represents a weather station
    """
    stations_heat_stats = None
    for idx in range(0, len(stations)):
        row = stations.iloc[idx, :].to_dict()
        daily = get_daily_station(station_id=row["station_id"], start_year = start, end_year = end)
        if len(daily) > 0:
            s_stats = compute_heat_stats(daily, row)
            if stations_heat_stats is not None:
                stations_heat_stats = pd.concat([stations_heat_stats, pd.DataFrame(s_stats, index=[0])], ignore_index=True)
            else:
                stations_heat_stats = pd.DataFrame(s_stats, index=[0])

    if stations_heat_stats is not None:
        for metric in ["tmax>30", "tmin>20", "dwd_heatwave_day", "n_heatwaves"]:
            stations_heat_stats[f"{metric}_mean"] = round(stations_heat_stats[f"{metric}_total"] / stations_heat_stats["n_years"], 1)
        
        if save_path != "":
            stations_heat_stats.to_csv(save_path)

    return stations_heat_stats

def compute_longer_heatwaves(heatwaves:pd.DataFrame, min_length:int)->pd.DataFrame:
    """Return a list of months containing heat waves longer than a certain threshold. [MM.YYYY, ] 

    Args:
        heatwaves (pd.DataFrame): _description_
        min_length (int): _description_

    Returns:
        pd.DataFrame: a dataframe of duration and max temperature and a multiindex of (year, start_month, end_month)
    """

    hw = heatwaves.copy()
    hw["start_month"] = hw["start_date"].dt.month
    hw["end_month"] = hw["end_date"].dt.month

    long_heatwaves = hw.loc[:,["year", "start_month", "end_month", "duration", "tmax"]].groupby(["year", "start_month", "end_month"]).max()
    long_heatwaves = long_heatwaves.loc[long_heatwaves["duration"]>min_length,:]
    return long_heatwaves

def compare_parameter_stations(stations:pd.DataFrame, start:int=2013, end:int=2024)->dict:
    """Returns a dictionary of dataframes where the keys are metrics 
    produced by compute_hot_days_per_year and the values are dataframes for 
    that metric with stations as columns and year as rows

    Args:
        stations (pd.DataFrame): pd.DataFrame

    Returns:
        dict: a dictionary of dataframes corresponding to each column of compute_hot_days_per_year.
    """
    dict_of_dfs = {}
    for i, row in stations.iterrows():
        daily_data = get_daily_station(row["station_id"], start_year=start, end_year=end)
        if len(daily_data)>0:
            dict_of_dfs[row["station_name"]] = compute_hot_days_per_year(daily_data)

    parameter_dicts = {}
    columns = list(dict_of_dfs.values())[0].columns
    for parameter in columns:
        param_df = pd.DataFrame({k:v.loc[:, parameter] for k, v in dict_of_dfs.items()}).T
        param_df["total"] = param_df.sum(axis=1)
        param_df = param_df.sort_values(by="total", ascending=False)
        parameter_dicts[parameter] = param_df
    return parameter_dicts


def get_heat_stats_german_cities(save_path:str="", additional_cities:list[str]=[], start:int=2013, end:int=2023):
    """Loop through a list of cities, identify heatwave indicators and summarize the statistics. 
    Loops through German cities with population > 1,000,000 by default. Takes a while to run so it is recommended to 
    save the result

    Args:
        save_path (str, optional): Path to save the resulting dataframe as csv. Defaults to "".
        additional_cities (list[str], optional): optional list of cities to add to the dataframe. Defaults to [].
        start (int, optional): year to start the analysis. Defaults to 2013.
        end (int, optional): year to end the analysis. Defaults to 2023.

    Returns:
        _type_: _description_
    """
    GROSSSTAEDTE = ['Berlin', 'Hamburg', 'Muenchen', 'Koeln', 
        'Frankfurt am Main', 'Stuttgart', 'Duesseldorf', 'Leipzig', 
        'Dortmund', 'Essen', 'Bremen', 'Dresden', 'Hannover', 'Nuernberg', 
        'Duisburg', 'Bochum', 'Wuppertal', 'Bielefeld', 'Bonn', 'Muenster, Deutschland', 
        'Mannheim', 'Karlsruhe', 'Augsburg', 'Wiesbaden', 'Moenchengladbach', 
        'Gelsenkirchen', 'Aachen', 'Braunschweig', 'Chemnitz', 'Kiel', 'Halle', 
        'Magdeburg', 'Freiburg im Breisgau', 'Krefeld', 'Mainz', 'Luebeck', 'Erfurt',
        'Oberhausen', 'Rostock', 'Kassel', 'Hagen', 'Potsdam', 'Saarbruecken', 
        'Hamm', 'Ludwigshafen am Rhein', 'Oldenburg', 'Muelheim an der Ruhr', 
        'Osnabrueck', 'Leverkusen', 'Heidelberg', 'Darmstadt', 'Solingen', 
        'Regensburg', 'Herne', 'Paderborn', 'Neuss', 'Ingolstadt',
        'Offenbach am Main', 'Fuerth', 'Ulm', 'Heilbronn', 'Pforzheim', 
        'Wuerzburg', 'Wolfsburg', 'Goettingen', 'Bottrop', 'Reutlingen', 
        'Erlangen', 'Bremerhaven', 'Koblenz', 'Bergisch Gladbach', 'Remscheid', 
        'Trier', 'Recklinghausen', 'Jena', 'Moers', 'Salzgitter', 'Siegen', 
        'Guetersloh', 'Hildesheim', 'Hanau']

    if os.path.exists(save_path):
        hw_stats_gs = pd.read_csv(save_path)
    else:
        hw_stats_gs = None

    for gs in (pbar := tqdm(GROSSSTAEDTE+additional_cities)):
        pbar.set_description(f"Fetching data for {gs}")
        
        if (hw_stats_gs is not None) and (gs in hw_stats_gs.columns):
            continue
        else:
            stations, _ = get_stations_from_location(gs, max_distance=20000)

            # Expand the search if no stations are found within 20km
            if len(stations)<2:
                stations, _ = get_stations_from_location(gs, max_distance=40000)

            stations_stats = compute_heat_stats_stations(stations)
            if hw_stats_gs is not None:
                    hw_stats_gs = pd.concat([hw_stats_gs, stations_stats], ignore_index=True)
            else:
                hw_stats_gs = stations_stats

    if save_path!="":
        hw_stats_gs.to_csv(save_path) # will overwrite existing

    return hw_stats_gs

