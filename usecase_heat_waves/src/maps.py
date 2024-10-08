import os
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import folium
import osmnx as ox 
import plotly.subplots as sp
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

import sys
from dotenv import load_dotenv

sys.path.append("../data")
load_dotenv()
MAPBOX_TOKEN = os.getenv('MAPBOX')
px.set_mapbox_access_token(MAPBOX_TOKEN)

def map_stations_with_stats(heatwave_stats, start_zoom=10):
    
    # set centerpoint for plot
    plot_lat = heatwave_stats["latitude"].mean()
    plot_lon = heatwave_stats["longitude"].mean()

    m = folium.Map(location=[plot_lat, plot_lon], zoom_start=start_zoom)
    place_gdf = ox.geocode_to_gdf(heatwave_stats.loc[0, "location"])   

    # Optionally, plot the boundary of the place if it's an area
    if 'geometry' in place_gdf.columns:
        folium.GeoJson(place_gdf['geometry']).add_to(m)

    # Filter stations by distance and plot them
    for _, station in heatwave_stats.iterrows():
        station["display_text"] = '''
            <b>{station_name}</b> <br>
            <b>Station ID:</b> {station_id}<br>
            <b>Distance:</b> {distance} Km<br>
            <b>Elevation:</b> {elevation}<br>
            <b>Average Heatwave Days:</b> {dwd_heatwave_day_mean}<br>
            <b>Average Tmax>30 Days:</b> {tmax_gt_30_mean}<br>
            <b>Average Tmin>20 Days:</b> {tmin_gt_20_mean}
        '''.format(
            station_name=station['station_name'], 
            station_id=station['station_id'], 
            distance=round(station['distance'] / 1000, 2), 
            elevation=station['elevation'], 
            dwd_heatwave_day_mean=station['dwd_heatwave_day_mean'], 
            tmax_gt_30_mean=station['tmax>30_mean'], 
            tmin_gt_20_mean=station['tmin>20_mean']
        )

        #iframe = folium.IFrame(station["display_text"])
        #popup = folium.Popup(iframe, min_width=500, max_width=500)
    
        # outer circle
        folium.Circle(
                location=[station["latitude"], station["longitude"]],
                radius=np.interp(station["dwd_heatwave_day_mean"],[0,20], [100, 2000]),
                color='red',
                fill=False,
                fill_color='red',
                fill_opacity=0.5,
                hover_data=station["station_name"],
                popup= folium.Popup(station["display_text"], parse_html=False, max_width=200)
            ).add_to(m)
        
    return m

def map_cities_with_stats(heatwave_stats:pd.DataFrame, 
                          country:str="Germany", 
                          display_parameter:str="dwd_heatwave_day_mean", 
                          color:str="red", start_zoom=10):
    """ToDo: This is too similar to map_stations_with_stats. Consolidate"""
    # set centerpoint for plot
    plot_lat = heatwave_stats["latitude"].mean()
    plot_lon = heatwave_stats["longitude"].mean()

    m = folium.Map(location=[plot_lat, plot_lon], zoom_start=start_zoom)
    place_gdf = ox.geocode_to_gdf(country)   

    # Optionally, plot the boundary of the place if it's an area
    if 'geometry' in place_gdf.columns:
        folium.GeoJson(place_gdf['geometry']).add_to(m)

    # Filter stations by distance and plot them
    for _, station in heatwave_stats.iterrows():
        station["display_text"]=f"""{station['location']} \n 
            Station Name: {station['station_name']} \n
            Station ID: {station['station_id']} \n
            Elevation: {station['elevation']}\n 
            {display_parameter}: {station[display_parameter]}"""

        # outer circle
        folium.Circle(
                location=[station["latitude"], station["longitude"]],
                radius=np.interp(station[display_parameter],[0,20], [100, 20000]),
                color=color,
                fill=False,
                fill_color=color,
                fill_opacity=0.5,
                hover_data=station["station_name"],
                popup= station["display_text"]
            ).add_to(m)
        
    return m

def map_scatter_mapbox(data:pd.DataFrame, 
                       title:str="Heatwave Metrics (Days per year, trend) for the last 10 years", 
                       size_parameter:str="dwd_heatwave_day_mean", 
                       color_parameter:str="dwd_heatwave_day_trend", 
                       zoom:int=5):

    if "trend" in color_parameter:
        continuous_color_scale= [[0, "blue"], [0.5, "white"], [1.0, "red"]]
        range_color=[-1, 1]
        color_continuous_midpoint=0
    else:
        #ToDo
        continuous_color_scale = None
        range_color = None
        color_continuous_midpoint = None

    lat_col = [c for c in data.columns if "lat" in c][0]
    lon_col = [c for c in data.columns if "lon" in c][0]
    name_col = [c for c in data.columns if "name" in c][0]

    fig = px.scatter_mapbox(data, 
                            title=title,
                            lat=data[lat_col], 
                            lon=data[lon_col], 
                            color=color_parameter, 
                            color_continuous_scale=continuous_color_scale,
                            color_continuous_midpoint=color_continuous_midpoint,
                            range_color=range_color,
                            hover_name=data[name_col],
                            hover_data={lat_col:False, lon_col:False, "tmax>30_mean":True, size_parameter:True},
                            zoom=zoom,
                            size=size_parameter,
                            height=800,
                            labels={"dwd_heatwave_day_trend": "Trend Hitzewellentage", 
                                    "dwd_heatwave_day_mean":"Durchschnittszahl von Hitzewellentage",
                                    "tmax>30_mean":"Durchschnittszahl von Heisse Tage (Tmax>30°C)"})


    fig.update_layout(margin={"r":10,"t":50,"l":10,"b":10},
                    mapbox_style="open-street-map")
    fig.update_geos(fitbounds="locations")
    return fig

def map_px_scattermap(data:pd.DataFrame, title:str="Heatwave Metrics (Days per year, trend) for the last 10 years", write_path:str=None):
    # Set centerpoint
    plot_lat = data["latitude"].mean()
    plot_lon = data["longitude"].mean()
    
    fig = px.scatter_geo(data, 
                        title="Heatwave Metrics (Days per year, trend) for the last 10 years",
                        lat=data['latitude'], 
                        lon=data['longitude'], 
                        color='dwd_heatwave_day_trend', 
                        color_continuous_scale=[[0, "blue"], [0.5, "white"], [1.0, "red"]],
                        color_continuous_midpoint=0,
                        range_color=[-1, 1],
                        hover_name='station_name',
                        hover_data={"latitude":False, "longitude":False, "tmax>30_mean":True, 'dwd_heatwave_day_mean':True},
                        size='dwd_heatwave_day_mean',
                        projection='natural earth')

    fig.update_layout(
        geo = dict(
            scope = 'europe',
            showland = True,
            landcolor = "rgb(212, 212, 212)",
            subunitcolor = "rgb(255, 255, 255)",
            countrycolor = "rgb(255, 255, 255)",
            showlakes = True,
            lakecolor = "rgb(255, 255, 255)",
            showsubunits = True,
            showcountries = True,
            resolution = 50,
        ),
        margin={'r': 0, 't': 50, 'l': 0, 'b': 20},
    )
    fig.update_geos(projection_scale=7, center=dict(lat=plot_lat, lon=plot_lon))

    if write_path:
        fig.write_html("dwd_heatwave_day.html")
    
    return fig


def map_choropleth_age(source_gdf,
                zoom:int=9, 
                title:str="", 
                conditions:dict={"prozent_0_5":(0,5)}, 
                show_col="prozent_0_5"):

    gdf = source_gdf.copy()
    bounds = gdf.total_bounds
    center = {"lat": (bounds[1] + bounds[3]) / 2, "lon": (bounds[0] + bounds[2]) / 2}
    zoom = zoom
    if title == "":
        title = f"{conditions}".replace("{","").replace("}","").title()

    filter_cols = []
    for column, threshold in conditions.items():
        this_filter_col = f"filter_{column}"
        gdf[this_filter_col] = gdf[column].between(left=threshold[0], right=threshold[1])
        filter_cols.append(this_filter_col)
    
    gdf["opacity"] = gdf.apply(lambda row: 0.1 if not all(row[filter_cols]) else 0.8, axis=1)

    fig = px.choropleth_mapbox(
        gdf,
        geojson=gdf.geometry,
        locations=gdf.index,
        color=show_col,
        color_continuous_scale="Magenta",
        hover_name="stadtteilname",
        hover_data=dict({"stadtteil": False,
            }, **{c:True for c in [c for c in gdf.columns if c.startswith("Population")]}),
        mapbox_style="carto-positron",
        opacity=gdf["opacity"],
        title=title,
        center=center,
        zoom=zoom
    )
    fig.update_layout(margin={"r":0,"t":50,"l":0,"b":0})

    return fig

def plot_dot(this_map, point, color_map, color_col):
    '''input: series that contains a numeric named latitude and a numeric named longitude
    this function creates a CircleMarker and adds it to your this_map'''
    
    # Define a tooltip for the CircleMarker
    point_tooltip = folium.Tooltip(
        text=(
            f"<b>{color_col}:</b> {point[color_col]}<br>"
            f"<b>Point Name:</b> {point['point_name']}<br>"
            f"<b>Point ID:</b> {point['point_id']}<br>"
            f"<b>Location ID:</b> {point['location_id']}<br>"
            f"<b>Orientation:</b> {point['loc_orientation']}<br>"
            f"<b>Surface:</b> {point['loc_surface']}"
        ),
        sticky=False
    )

    # Get the color from the discrete color map
    color = mcolors.to_hex(color_map(point[color_col]))
        
    folium.CircleMarker(location=[point.lat, point.lng],
                        radius=5,
                        fill_color=color,
                        fill_opacity=1,
                        tooltip=point_tooltip,
                        weight=1).add_to(this_map)

def plot_dots_on_districts(districts_gdf, points_gdf=None, color_col=None):
    # Create a map
    this_map = folium.Map(prefer_canvas=True)

    # Add districts tooltip (hover text)
    districts_tooltip = folium.GeoJsonTooltip(
        fields=["id", "name", "slug"],
        aliases=["ID:", "Name:", "Slug:"],
        localize=True,
        sticky=False,
        labels=True,
        style="""
            background-color: #F0EFEF;    """,
        max_width=800,
    )

    # Add districts
    folium.GeoJson(
        data=districts_gdf,
        style_function=lambda x: {'fillColor': 'white', 'color': 'black'},
        tooltip=districts_tooltip
    ).add_to(this_map)

    # Add Points with color based on the specified column
    if points_gdf is not None:
        # Normalize the data for the color map
        norm = plt.Normalize(vmin=points_gdf[color_col].min(), vmax=points_gdf[color_col].max())
        cmap = plt.get_cmap('viridis')  # You can choose another colormap if you prefer
        color_map = plt.cm.ScalarMappable(norm=norm, cmap=cmap).to_rgba
        points_gdf.apply(lambda point: plot_dot(this_map, point, color_map, color_col), axis=1)

    # Set the zoom to the maximum possible
    this_map.fit_bounds(this_map.get_bounds())

    # Save the map to an HTML file (optional)
    # this_map.save(os.path.join('html_map_output/simple_dot_plot.html'))

    return this_map