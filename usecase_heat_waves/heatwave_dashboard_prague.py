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
from load_arcgis import get_survey
import analyse_heatwaves as hw_functions
import plots as hw_plots
import maps as hw_maps

st.set_page_config(layout="wide")
divider_color = 'red'

# Data
DATA_DIR = "./data"
REPROJECTED_LST_PATH = "data/processed/Prague_LC08_L1TP_192025_20180817_20200831_02_T1/LC08_L1TP_192025_20180817_20200831_02_T1_LST_reprojected_Prague.TIF"
SENSOR_DIR = "data/processed/microclimate_sensors"

# Meteostat
st.session_state.stations, _ = hw_functions.get_stations_from_location(location="Prague", 
                                                                       max_distance=30000)
st.session_state.stations_hw = hw_functions.compute_heat_stats_stations(st.session_state.stations,
                                                                        start=2003,
                                                                        end=2024) 
st.session_state.station_comparison_location = hw_functions.compare_parameter_stations(
    st.session_state.stations,
    start=2003,
    end=2024) #displayed as a carpet plot in col2

# Land Surface Temperature
st.session_state.lst_gdf = gpd.read_feather("data/processed/Prague_districts_lst.feather")
# Prauge Sensors
air_temp_hourly_paths = glob(os.path.join(SENSOR_DIR, "air_temp*hourly.csv"))
####DEBUG
#st.markdown([p[-21:-11] for p in air_temp_hourly_paths])
air_temp_hourly_path = air_temp_hourly_paths[1]

## Hourly Air Temperature
st.session_state.air_temp_hourly = pd.read_csv(air_temp_hourly_path, index_col="measured_at")
st.session_state.air_temp_hourly.index = pd.to_datetime(st.session_state.air_temp_hourly.index)
### Calculate difference from mean
mean = st.session_state.air_temp_hourly.mean(axis=1)
st.session_state.air_temp_hourly = st.session_state.air_temp_hourly.assign(mean=mean)
df_delta = st.session_state.air_temp_hourly.drop(columns="mean").subtract(mean, axis=0)

## Sensor Info 
st.session_state.sensor_info = gpd.read_file(os.path.join(SENSOR_DIR, "microclimate_sensorspoints_en.csv"), crs="epsg:4326")
if st.session_state.sensor_info.crs is None:
    st.session_state.sensor_info = st.session_state.sensor_info.set_crs("EPSG:4326")

## Title
IMG_DIR = "./data/raw"
dksr_logo = Image.open(os.path.join(IMG_DIR, "logo_dksr.png"))

header1, header2 = st.columns([5,1])
with header1:
    st.write("""
    # Heatwave Risk in Prague
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

# Add coloured districts 
districts_layer, _ = hw_maps.districts_gdf_to_folium_layer(
    districts_gdf=st.session_state.lst_gdf, 
    gdf_color_column="lst_mean") 
districts_layer.add_to(st.session_state.m)

# Add Microclimate sensors
hw_maps.add_gdf_points_to_map(points_gdf=st.session_state.sensor_info, 
                              color_col="",
                              this_map=st.session_state.m)

left, right = st.columns([2, 1])
with left:
    # Display Map
    folium.LayerControl().add_to(st.session_state.m) 
    city_data = st_folium(st.session_state.m, 
                        use_container_width=True, 
                        returned_objects=["last_object_clicked_tooltip"], 
                        height=600)
with right:
    lst_df = st.session_state.lst_gdf.drop(["geometry", "id", "district_id", "slug", "pixel_count", "updated_at", "band"], axis=1).set_index("name").sort_values("lst_mean")
    # Statistics
    district_lst_scatter = px.scatter(lst_df.iloc[:, :3], 
                                      template="plotly_white", 
                                      orientation="h",
                                      title="Aggregate Land Surface Temperature per District")
    # Proportion of area in certain temperature bands
    district_lst_stacked_bar = px.bar(
        lst_df.iloc[:, 4:], 
        barmode="stack", 
        orientation="h", 
        template="plotly_white",
        title="Proportion of area within certain temperature bands")
    
    st.plotly_chart(district_lst_scatter)
    st.plotly_chart(district_lst_stacked_bar)

left, right = st.columns([1, 1])
with left:
    # Temperature charts
    hourly_temperature_plot = px.line(st.session_state.air_temp_hourly, 
              color_discrete_sequence=px.colors.qualitative.Plotly,
              title="Hourly Mean Temperature ")
    hourly_temperature_plot.update_layout(
        legend_title="Sensor"
    )
    # Delta charts
    hourly_temperature_delta = px.line(df_delta, 
              y=df_delta.columns, 
              color_discrete_sequence=px.colors.qualitative.Plotly,
              title="T_mean - T_sensor"
              )
              
    hourly_temperature_delta.update_layout(
        legend_title="Sensor"
    )

    # Plot
    st.plotly_chart(hourly_temperature_plot)
    st.plotly_chart(hourly_temperature_delta)


with right:
    # Select sensor to plot
    sensors_with_data = st.session_state.air_temp_hourly.columns

    sensor_id = st.radio(label="Select a sensor to plot", 
                    horizontal=True,
                    options=st.session_state.air_temp_hourly.columns)

    if city_data["last_object_clicked_tooltip"]:
        selected_sensor_on_map = city_data["last_object_clicked_tooltip"].split("Point ID: ")[1][:3]
        if selected_sensor_on_map in sensors_with_data:
            sensor_id = selected_sensor_on_map

    st.table(st.session_state.sensor_info.set_index("point_id").loc[sensor_id,["loc_description", "sensor_position_detail"]]) 

    # Temperature Scatter Plot
    temperature_carpet = hw_plots.plot_hourly_carpet(
        df=st.session_state.air_temp_hourly, 
        unit="°C", 
        title=f"Air Temperature <br>Point {sensor_id}", 
        col=sensor_id)
    st.plotly_chart(temperature_carpet)

    temperature_diff_carpet = hw_plots.plot_hourly_carpet(
        df=df_delta, 
        unit="°C", 
        title=f"Air Temperature <br>Mean - Point {sensor_id}", 
        col=sensor_id)
    st.plotly_chart(temperature_diff_carpet)    


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