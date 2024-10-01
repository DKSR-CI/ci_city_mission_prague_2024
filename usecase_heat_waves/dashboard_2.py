import streamlit as st
from streamlit_folium import st_folium, folium_static
import folium
from folium.plugins import FastMarkerCluster, HeatMap
import json
import pandas as pd
import geopandas as gpd
import rioxarray as rxr
import plotly.express as px
from shapely.geometry import Polygon, Point
import os
import sys
import numpy as np
from PIL import Image

sys.path.append("./src")
from load_arcgis import get_survey
import analyse_heatwaves as hw_functions
import plots as hw_plots
import maps as hw_maps
import pickle

st.set_page_config(layout="wide")
divider_color = 'red'

# Data
IMG_DIR = "./data/raw"
DATA_DIR = "./data"
FULL_LST_PATH = "data/processed/Prague_LC08_L1TP_192025_20180817_20200831_02_T1/LC08_L1TP_192025_20180817_20200831_02_T1_LST_reprojected_Prague.TIF"
LST_DICT_PATH = "data/processed/lst_dict.pkl"
POPULATION_PATH = "data/processed/prague_population_districts_meta2020.feather"

#st.session_state.lst = rxr.open_rasterio(FULL_LST_PATH, masked=True)#
with open(LST_DICT_PATH, 'rb') as file:
    st.session_state.lst_dict = pickle.load(file)

st.session_state.population = gpd.read_feather(POPULATION_PATH)

# Get population figures (for bar plot and filtering)
keep_columns = [c for c in st.session_state.population.columns if c.startswith("cze")]+["name", "area (km²)"]
total_pop = st.session_state.population.loc[:, keep_columns]
pop_density = (total_pop.drop("name", axis=1).T / total_pop["area (km²)"]).T

# Load Logo
dksr_logo = Image.open(os.path.join(IMG_DIR, "logo_dksr.png"))

header1, header2 = st.columns([5,1])
with header1:
    st.write("""
    # Vulnerable Groups under Heat Stress
    ## Explore Heat Risk
    """)
    
with header2:
    st.image(dksr_logo)

left_col, middle_col, right_col = st.columns([1, 3, 2])

with left_col:
    # adjust population
    st.markdown("### Vulnerable Groups")
    slider_max = round(pop_density.max()["cze_elderly_60_plus_2020"])
    st.slider(label="Population density aged 60 plus [p/km²]", min_value=0, max_value=slider_max, value=round(slider_max/2), key="population_slider")

    total_pop_filtered = total_pop[pop_density["cze_elderly_60_plus_2020"] > st.session_state.population_slider]
    district_indices = total_pop_filtered.index

    # adjust lst
    st.markdown("### Heat Stress")
    st.slider(label="LST_min Hot Spots [°C]", min_value=20, max_value=50, value=28, key="lst_min")
    st.slider(label="LST_max Cool Spots [°C]", min_value=0, max_value=28, value=28, key="lst_max")

with middle_col:
    m = folium.Map(tiles='CartoDB positron', width=800)

    for key in district_indices:
        this_lst = st.session_state.lst_dict[key]
        # filter range
        this_lst = this_lst.where((this_lst > st.session_state.lst_min) | (this_lst < st.session_state.lst_max))
        img_bytes = hw_maps.array_to_colored_png(this_lst, vmin=10, vmax=60)
        left, bottom, right, top = this_lst.rio.bounds()

        # Create an image overlay
        img_overlay = folium.raster_layers.ImageOverlay(
            img_bytes,
            bounds=[[bottom, left], [top, right]],
            opacity=0.6,
            interactive=True,
            cross_origin=False,
            zindex=1,
            #name=f"D{key}_LST 17.08.2018 10:00"
        )
        img_overlay.add_to(m)

    colorbar = hw_maps.generate_colorbar(vmin=0, vmax=60,)
    position=(55, 5)
    colorbar.add_to(m)

    # load population map
    layer, cmap = hw_maps.districts_gdf_to_folium_layer(st.session_state.population.loc[district_indices], 
                                                        gdf_color_column="cze_general_2020",
                                                        fields=["name", 
                                                                "cze_general_2020", 
                                                                "cze_elderly_60_plus_2020",
                                                                "cze_children_under_five_2020"],
                                                        aliases=["District: ", 
                                                                 "Total Population: ",
                                                                 "Population >60: ",
                                                                 "Population <5:"],
                                                        opacity=0.01
                                                        )
     
    layer.add_to(m)
    #cmap.add_to(m)
    #folium.LayerControl().add_to(m) 
    m.fit_bounds(m.get_bounds())
    folium_static(m)

with right_col:
    # plot population
    total_pop_filtered.set_index("name", inplace=True)
    total_pop_filtered.sort_values(by="cze_general_2020", ascending=True, inplace=True)
    
    percentage_reached = total_pop_filtered.sum() / total_pop.sum() * 100
    st.markdown(f"### {round(percentage_reached['cze_general_2020'])}% of total population")
    total_pop_filtered.drop(["area (km²)", "cze_general_2020"], axis=1, inplace=True)

    total_pop_bar = px.bar(total_pop_filtered, 
             template="plotly_white",
             title="Total Population (p)",
             )
    
    total_pop_bar.update_layout(yaxis_title="District",
                  xaxis_title="Total Population")
    
    st.plotly_chart(total_pop_bar)
    
