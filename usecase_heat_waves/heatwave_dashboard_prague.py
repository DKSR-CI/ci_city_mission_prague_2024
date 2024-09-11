import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import plotly.express as px
import os
import sys
import geopandas as gpd
from PIL import Image
from glob import glob

sys.path.append("./src")
import analyse_heatwaves as hw_functions
import plots as hw_plots
import maps as hw_maps

st.set_page_config(layout="wide")
divider_color = 'red'

# Data
DATA_DIR = "./data"
REPROJECTED_LST_PATH = "data/processed/Prague_LC08_L1TP_192025_20180817_20200831_02_T1/LC08_L1TP_192025_20180817_20200831_02_T1_LST_reprojected_Prague.TIF"
SENSOR_DIR = "data/processed/microclimate_sensors"

st.session_state.stations, _ = hw_functions.get_stations_from_location(location="Prague", 
                                                                       max_distance=30000)
st.session_state.stations_hw = hw_functions.compute_heat_stats_stations(st.session_state.stations,
                                                                        start=2003,
                                                                        end=2024) 
st.session_state.station_comparison_location = hw_functions.compare_parameter_stations(
    st.session_state.stations,
    start=2003,
    end=2024) #displayed as a carpet plot in col2

st.session_state.lst_gdf = gpd.read_feather("data/processed/Prague_districts_lst.feather")

air_temp_hourly_path = glob(os.path.join(SENSOR_DIR, "air_temp*hourly.csv"))[0]
st.session_state.air_temp_hourly = pd.read_csv(air_temp_hourly_path)
st.dataframe(st.session_state.air_temp_hourly)

## Title
IMG_DIR = "./data/raw"
dksr_logo = Image.open(os.path.join(IMG_DIR, "logo_dksr.png"))

header1, header2 = st.columns([5,1])
with header1:
    st.write("""
    # Looking at Urban Heat in Prague
    Built for the Prague City Mission
    """)    
 
with header2:
    st.image(dksr_logo, width=200)

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

##### Prague Sensors
st.session_state.m = folium.Map()
st.session_state.m = hw_maps.add_lst_to_map(REPROJECTED_LST_PATH, st.session_state.m)
st.session_state.m.fit_bounds(st.session_state.m.get_bounds())
folium.LayerControl().add_to(st.session_state.m)

city_data = st_folium(st.session_state.m, 
                      use_container_width=True, 
                      returned_objects=["last_object_clicked_popup"], 
                      height=600)

# hw_maps.plot_dots_on_districts(districts_gdf=st.session_state.lst_gdf, 
#                                 gdf_color_column="lst_mean",
#                                 points_gdf=points_this_hour, 
#                                 color_col="air_temp200")

# m = hw_maps.map_stations_with_stats(st.session_state.stations_hw, start_zoom=10)



##### Historical Data
st.header("Heatwaves over the last 20 years", divider=divider_color)


col1, col2 = st.columns([1,1])
with col1:
    st.subheader("Number of heatwave days logged by each weather station")
    m = hw_maps.map_stations_with_stats(st.session_state.stations_hw, start_zoom=10)
    city_data = st_folium(m, use_container_width=True, returned_objects=["last_object_clicked_popup"], height=400)

    st.subheader(f"Heatwave statistics for different stations around Prague")
    params = list(st.session_state.station_comparison_location.keys())
    st.selectbox("select a parameter to compare", options=params, index=3, key="station_comparison_parameter")
    station_comparison_to_plot = st.session_state.station_comparison_location[st.session_state.station_comparison_parameter]
    st.plotly_chart(hw_plots.plot_compare_stations(station_comparison_to_plot), height=100, use_container_width=True)

with col2:
    if city_data["last_object_clicked_popup"] is not None:
        ##### Station Scale     
        station_id = city_data["last_object_clicked_popup"].split(
            "Station ID: ")[1].split("Distance")[0].replace(" ", "").replace("\n","")
        station_name = city_data["last_object_clicked_popup"].split("Station ID: ")[0].replace("\n", "")
        
        st.session_state.daily_data = hw_functions.get_daily_station(station_id, start_year=2003, end_year=2024)
        st.session_state.heatwaves = hw_functions.group_heatwaves_station(st.session_state.daily_data)
        st.session_state.long_heatwaves = hw_functions.compute_longer_heatwaves(st.session_state.heatwaves, 5)

        st.subheader(f"{station_name} Weather Station")
        
        # plot heatwave statistics
        title = f"{station_name}: T_max > 30°C"
        st.plotly_chart(
            hw_plots.plot_daily(
                st.session_state.daily_data,
                title= title,
                plot_value="tmax", 
                highlight_column="tmax>30", ),
            use_container_width=True 
        )
        st.plotly_chart(hw_plots.plot_heatwaves(st.session_state.heatwaves))
    else:
        st.subheader("Click on a station for more information")
        
# Footer
st.subheader("", divider=divider_color)

st.write("""
© 2024 DKSR GmbH
""")