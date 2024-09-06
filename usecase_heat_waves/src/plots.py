import os
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import folium
import osmnx as ox 
import plotly.subplots as sp
import sys

sys.path.append("../data")
from dotenv import load_dotenv
load_dotenv()

MAPBOX_TOKEN = os.getenv('MAPBOX')
px.set_mapbox_access_token(MAPBOX_TOKEN)

def plot_temperature_trends(daily_data, station_name=""):
    annual_hot_days = daily_data.loc[:, ["year", "tmax>30", "tmin>20", "dwd_heatwave_day"]].groupby("year").sum()
    if station_name != "":
        station_name = " for " + station_name        
    fig = px.line(annual_hot_days, 
            #template="plotly_dark",
            title=f"Temperature trends{station_name}",
            )

    #fig.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
    fig.update_yaxes(title="Tage im Jahr", range=(0,40))
    fig.update_xaxes(title="Jahr")
    return fig

def plot_daily(daily, title, plot_value:str="tavg", highlight_column:str="dwd_heatwave_day"):

    if plot_value not in daily.columns:
        return f"{plot_value} not found in Dataframe"
    if highlight_column not in daily.columns:
        return f"{highlight_column} not found in DataFrame"
        
    # Dummy day counter to correctly display y-axis
    daily["dummy_day"] = 1

    # Plotting
    fig = px.bar(daily.reset_index(), x="year", y="dummy_day",
                 color=plot_value,
                 title=title,
                 template="plotly_dark",
                 #hover_name={'station_name'},
                 hover_data={"dummy_day":False,
                             "day_of_year": True, 
                             "month_of_year":True,
                             "index": True,
                             "year": False, 
                             "tmin>20": True, 
                             "tmax>30":True, 
                             "dwd_heatwave_day": True},
                 )
    
    # Extract the default colors assigned by Plotly
    default_colors = [trace.marker.color for trace in fig.data]

    # Set border and fill colors based on 'dwd_heatwave_day'
    daily['border_color'] = daily[highlight_column].apply(lambda x: 'red' if x > 0 else "rgba(0,0,0,0)")
    daily['fill_color'] = daily[highlight_column].apply(lambda x: 'red' if x > 0 else None)

    # Ensure that fill_color is properly assigned
    fill_colors = daily['fill_color'].tolist()

    # Update traces for border and fill color
    for i, trace in enumerate(fig.data):
        trace.marker.line.width = 1
        trace.marker.line.color = daily['border_color'].tolist()
        # Use fill_color if it's set, otherwise use the default color
        updated_colors = [fill_colors[j] if fill_colors[j] is not None else default_colors[i][j] for j in range(len(fill_colors))]
        trace.marker.color = updated_colors
    

    # Update y-axis to show months
    fig.update_yaxes(title="Month", 
                     tickmode='array', 
                     tickvals=[0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335], 
                     ticktext=[pd.to_datetime(f'2020-{i}-01').strftime('%B') for i in range(1, 13)], 
                     showgrid=True)

    # Update x-axis to show years
    years = daily['year'].unique()
    fig.update_xaxes(title="Year", tickmode='array', tickvals=years, ticktext=years)
    
    # update colour scheme to a specific range
    return fig


def plot_daily_go(daily, title, plot_value="tavg", highlight_column="dwd_heatwave_day", color_range=None, color_scale='Turbo'):
    if plot_value not in daily.columns:
        return f"{plot_value} not found in DataFrame"
    if highlight_column not in daily.columns:
        return f"{highlight_column} not found in DataFrame"
        
    # Dummy day counter to correctly display y-axis
    daily["dummy_day"] = 1

    # Calculate opacity based on the condition in 'tmin>20'
    daily['opacity'] = daily['tmin>20'].apply(lambda x: 0.2 if x else 1)
    
    # Set border colors based on 'dwd_heatwave_day'
    daily['border_color'] = daily[highlight_column].apply(lambda x: 'yellow' if x > 0 else "rgba(0,0,0,0)")

    # Define color range for the color scale
    cmin, cmax = color_range if color_range else (daily[plot_value].min(), daily[plot_value].max())

    # Create a bar trace
    trace = go.Bar(
        x=daily["year"],
        y=daily["dummy_day"],
        marker=dict(
            color=daily[plot_value],
            colorscale=color_scale,
            cmin=cmin,
            cmax=cmax,
            colorbar=dict(title=plot_value),
            line=dict(width=1, color=daily['border_color'])
        ),
        hoverinfo='skip'
    )

    # Create the figure
    fig = go.Figure(data=[trace])

    # Update layout
    fig.update_layout(
        title=title,
        template="plotly_dark",
        yaxis=dict(
            title="Month",
            tickmode='array',
            tickvals=[0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335],
            ticktext=[pd.to_datetime(f'2020-{i}-01').strftime('%B') for i in range(1, 13)],
            showgrid=True
        ),
        xaxis=dict(
            title="Year",
            tickmode='array',
            tickvals=daily['year'].unique(),
            ticktext=daily['year'].unique()
        )
    )

    return fig

def plot_compare_stations(df:pd.DataFrame, title:str=""):
    station_comparison_df = df.copy().drop("total", axis=1)
    fig = px.imshow(station_comparison_df,
                    #template="plotly_light",
                    color_continuous_scale="temps",
                    aspect="auto",
                    text_auto=True,
                    title=title,
                    )

    return fig

def plot_monthly_heatwave_days(daily_data):
    monthly_heatwave_days = pd.pivot_table(data=daily_data, columns="year", index="month_of_year", 
                               values="dwd_heatwave_day", aggfunc="sum")
    sub_monthly_heatwave_days = monthly_heatwave_days.loc[monthly_heatwave_days.sum(axis=1)>0, :]

    fig = px.imshow(sub_monthly_heatwave_days, 
                    y=[pd.to_datetime(f'2020-{i}-01').strftime('%B') for i in sub_monthly_heatwave_days.index.to_list()],
                    x=monthly_heatwave_days.columns,
                    #template="plotly_light",
                    color_continuous_scale="temps",
                    aspect="auto",
                    text_auto=True,
                    title="Number of Heatwave Days per Month"
                    )

    return fig

def plot_heatwaves(heatwaves_df:pd.DataFrame):
    """A stacked bar plot showing individual heatwave events by length and maximum temperature

    Args:
        heatwaves_df (pd.DataFrame): a dataframe summarizing heatwaves created using data_tools.group_heatwaves_station(daily_data)

    Returns:
        px.fig: a figure to show in streamlit
    """
    hw = heatwaves_df.copy()
    hw['start_date'] = hw['start_date'].dt.strftime('%d.%m.%Y')
    hw['end_date'] = hw['end_date'].dt.strftime('%d.%m.%Y')

    fig = px.bar(data_frame=hw,
            x="year", 
            y="duration", 
            color="tmax",
            title="Heatwave Length and Max. Temperature",
            color_continuous_scale="YlOrRd",
            template="plotly_white",
            text="tmax",
            hover_name='annual_index',
            hover_data={"year":False,
                        "duration":True,
                        "tmax":True,
                    "start_date":True,
                    "end_date": True, 
                        }) 

    fig.update_yaxes(title="Heatwave Days")
    fig.update_xaxes(title="year")
    return fig


def plot_temperature_and_landsat(hourly_df:pd.DataFrame, landsat_df:pd.DataFrame, unit:str="°C"):
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    if landsat_df is not None:
        fig.add_trace(go.Scatter(
            x=landsat_df["stop_time"], 
            y=landsat_df["cloud_cover"], 
            name="Landsat Captures",
            mode='markers',
            marker=dict(color='blue'),
            hovertemplate=
                '<b>Display ID</b>: %{customdata[0]}<br>' +
                '<b>Capture Time</b>: %{x}<br>' +
                '<b>Cloud Cover</b>: %{y}<br>',
            customdata=landsat_df[['display_id']]
            ), secondary_y=True)
    
    if (hourly_df is not None) and (len(hourly_df)>0):
        fig.add_trace(go.Scatter(x=hourly_df.index, 
                                y=hourly_df["temp"], 
                                name=f"Temperature {unit}",
                                mode='lines',
                                line=dict(color='red')), 
                                secondary_y=False)
    
    title = 'Air Temperature and available Landsat scenes (with cloudcover)'
        
    fig.update_layout(
        title=title,
        hovermode="x unified",
        xaxis_title='Date',
        template='plotly_white'
    )

    # Set y-axes titles
    fig.update_yaxes(title_text="Temperature", secondary_y=False)
    fig.update_yaxes(title_text="Cloud Cover", secondary_y=True)

    return fig

def plot_hourly_carpet(df:pd.DataFrame, 
                metadata:pd.DataFrame=pd.DataFrame(), 
                unit:str="", 
                title:str="",
                col:str="",
                diff:bool=False):
    
    if col == "":
        return "Please specify a column"
    else:
        long_df = pd.DataFrame(df.loc[:, col])
        long_df.index = pd.to_datetime(long_df.index)
        long_df.columns = ["value"]
        long_df["date"] = long_df.index.normalize()
        long_df["daytime"] = long_df.index - long_df["date"]

        short_df = long_df.pivot_table(columns="date", index="daytime", values="value")
        short_df.index = short_df.index / pd.Timedelta('1 hour')

        if (unit == "") and len(metadata)>0:
            unit = metadata.loc[metadata['measure']==col, 'unit'].values[0]
        if (title == "") and len(metadata)>0:
            title = metadata.loc[metadata['measure']==col, 'point_id'].values[0]
            title = f"Point {title} <br>{col}"
        
        if diff:
            fig = px.imshow(short_df, 
                            title=title, 
                            color_continuous_scale=px.colors.diverging.RdBu_r, 
                            color_continuous_midpoint=0)
        else:
            fig = px.imshow(short_df, 
                            title=title, 
                            color_continuous_scale="Turbo")

        # Update the color axis to change the colorbar title
        fig.update_layout(
            coloraxis_colorbar=dict(
                title=unit  # This changes the legend title to your desired unit
            )
        )
        return fig