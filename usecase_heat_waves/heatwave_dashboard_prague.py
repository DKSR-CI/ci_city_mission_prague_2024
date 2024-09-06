import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
import plotly.express as px
import os
import sys
import geopandas as gpd
from PIL import Image

sys.path.append("./src/heat_waves")
import analyse_heatwaves as hw_functions
import plots as plot_lib
import maps as map_lib
from landsat_pipeline import LandsatLoader

st.set_page_config(layout="wide")
divider_color = 'red'

def celcius_to_farenheit(celsius:float):
        return round((celsius * 1.8) + 32, 1)

# Data
DATA_DIR = "./data"
german_cities_data_path = os.path.join(DATA_DIR, "interim", "heatwave_stats_de_10year.csv")
try:
    st.session_state.german_cities = pd.read_csv(german_cities_data_path)
except:
    st.session_state.german_cities = hw_functions.get_heat_stats_german_cities(save_path=german_cities_data_path, additional_cities=["Lindau"])

drop_cols = [c for c in st.session_state.german_cities if "Unnamed" in c]
st.session_state.german_cities.drop(drop_cols, inplace=True, axis=1) 

## Title
IMG_DIR = "./pages/images"
dksr_logo = Image.open(os.path.join(IMG_DIR, "logo_dksr.png"))
utm_logo = Image.open(os.path.join(IMG_DIR, "logo_utm.jpg"))

header1, header2 = st.columns([5,1])
with header1:
    st.write("""
    # Looking at Urban Heat in Prague
    Built for the Prague City Mission
    """)    
 
with header2:
    st.image(dksr_logo, width=200)
    st.image(utm_logo, width=200)


##### City Scale
st.header("Heatwaves at a Regional Level", divider=divider_color)

with st.expander("""### :blue-background[What are heatwaves and why do they matter?]"""):
    st.write("""
    Heatwaves are abnormally hot periods which cause increased rates of morbidity and mortality. Some of these casualties can be avoided
             by improving understanding of heatwaves and strategically increasing heat resilience in certain areas of the city.
             
    The severity of a heatwave depends on several factors: 
    - Peak daytime temperature: Since heat flows from hot to cold areas, at higher temperatures the body is less able to cool itself.
    - Duration: Longer heatwaves result in hotter surfaces and increase fatigue and dehydration risk.
    - Nighttime temperatures: Unconditioned buildings rely on nighttime ventilation for cooling. If night temperatures increase, buildings are more likely to overheat
    - Relative humidity: High RH reduces the cooling effect of sweating. 

    In the plots below, we use the simplified thresholds recommended by the German Meteorological Office (DWD) as follows:  
    - **Heatwave Day**: The third consecutive day where the temperature exceeds 28°C (82.4°C). 
    - **Hot Day**: A day where the maximum temperature exceeds 30°C (86°F).
    - **Hot Night**: A night where the minimum temperature exceeds 20°C (68°F).
    """)


# Get Data
st.text_input(label="Search for any City",
                value="Prague",
                key="location")

st.session_state.stations, _ = hw_functions.get_stations_from_location(location=st.session_state.location, 
                                                                       max_distance=30000,)

st.session_state.stations_hw = hw_functions.compute_heat_stats_stations(st.session_state.stations,
                                                                        start=2003,
                                                                        end=2024) 
st.session_state.station_comparison_location = hw_functions.compare_parameter_stations(
    st.session_state.stations,
    start=2003,
    end=2024) #displayed as a carpet plot in col2

st.session_state.lst_gdf = gpd.read_feather("data/processed/Prague_districts_lst.feather")
st.dataframe(st.session_state.lst_gdf)

col1, col2 = st.columns([1,1])
with col1:
    st.subheader("Number of heatwave days logged by each weather station")
    m = map_lib.map_stations_with_stats(st.session_state.stations_hw, start_zoom=10)
    city_data = st_folium(m, use_container_width=True, returned_objects=["last_object_clicked_popup"], height=400)

with col2:
    st.subheader(f"Heatwave statistics for different stations around {st.session_state.location}")
    params = list(st.session_state.station_comparison_location.keys())
    st.selectbox("select a parameter to compare", options=params, index=3, key="station_comparison_parameter")
    station_comparison_to_plot = st.session_state.station_comparison_location[st.session_state.station_comparison_parameter]
    st.plotly_chart(plot_lib.plot_compare_stations(station_comparison_to_plot), height=100, use_container_width=True)


    
##### Station Scale     
if city_data["last_object_clicked_popup"] is not None:
    station_id = city_data["last_object_clicked_popup"].split(
        "Station ID: ")[1].split("Distance")[0].replace(" ", "").replace("\n","")
    station_name = city_data["last_object_clicked_popup"].split("Station ID: ")[0].replace("\n", "")
    
    st.session_state.daily_data = hw_functions.get_daily_station(station_id, start_year=2003, end_year=2024)
    st.session_state.heatwaves = hw_functions.group_heatwaves_station(st.session_state.daily_data)
    st.session_state.long_heatwaves = hw_functions.compute_longer_heatwaves(st.session_state.heatwaves, 5)
    
    left, right = st.columns([6,1])
    with left:
        st.subheader(f"{station_name} Weather Station")
    with right:
        st.radio(label="", options=["°C", "°F"], index=0, key="t_unit")

    # convert to F
    if st.session_state.t_unit == "°C":
        title = f"{station_name}: T_max > 30°C"
    else: 
        title = f"{station_name}: T_max > {celcius_to_farenheit(30)}°F"
        st.session_state.daily_data["tmax"] = st.session_state.daily_data["tmax"].apply(lambda x: celcius_to_farenheit(x))
        st.session_state.heatwaves["tmax"] = st.session_state.heatwaves["tmax"].apply(lambda x: celcius_to_farenheit(x))

    col1, col2 = st.columns([1, 1])
    with col1: 
            st.plotly_chart(
                plot_lib.plot_daily(
                    st.session_state.daily_data,
                    title= title,
                    plot_value="tmax", 
                    highlight_column="tmax>30", ),
                use_container_width=True
            )

    with col2:
         st.plotly_chart(plot_lib.plot_heatwaves(st.session_state.heatwaves))

    ##### Load Hourly Data
    st.header("Get Satellite Data for a Heatwave")
    st.radio("Hottest or Longest heatwave", options=["longest", "highest peak temperature"], key="hw_month")
    sort_col = {"longest":"duration",
                "highest peak temperature":"tmax"}
    
    st.session_state.long_heatwaves = st.session_state.long_heatwaves.sort_values(by=sort_col[st.session_state.hw_month], ascending=False)
    
    
    # Load temperature
    hourly_data = pd.DataFrame()
    i = 0
    while (i<5) and (len(hourly_data)==0):
        try:
            hourly_year, hourly_start_month, hourly_end_month = st.session_state.long_heatwaves.index[0]
            hourly_data = hw_functions.get_hourly_station(station_id, 
                                                        year=hourly_year, 
                                                        start_month=hourly_start_month, 
                                                        end_month=hourly_end_month)
        except:
            st.markdown(f"Failed to get Hourly Data for {station_name}")
        if len(hourly_data)==0:
            st.markdown("No hourly data found. trying the next highest...")
        i += 1

    if st.session_state.t_unit != "°C":
        hourly_data["temp"] = hourly_data["temp"].apply(lambda x: celcius_to_farenheit(x))

    # Load Landsat
    # this takes a while, might add a switch
    ll = LandsatLoader(data_path=DATA_DIR)
    try:
        landsat_scenes = ll.get_scenes_l1(location=st.session_state.location, 
                                        start_month=hourly_start_month, 
                                        end_month=hourly_end_month, 
                                        year=hourly_year)
    except:
        landsat_scenes = None
        st.markdown("Ran into trouble fetching landsat scene for this location")
    
    fig_temp_ls = plot_lib.plot_temperature_and_landsat(hourly_data, landsat_scenes, unit=st.session_state.t_unit)
    st.plotly_chart(fig_temp_ls, use_container_width=True)

st.subheader("", divider=divider_color)

st.write("""
© 2024 DKSR GmbH
""")