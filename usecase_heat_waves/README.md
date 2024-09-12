# usecase_heat_waves

Heatwaves are abnormally hot periods which cause increased rates of morbidity and mortality. Some of these casualties can be avoided by improving understanding of heatwaves and strategically increasing heat resilience in certain areas of the city.

The severity of a heatwave depends on several factors:

- Peak daytime temperature: Since heat flows from hot to cold areas, at higher temperatures the body is less able to cool itself.
- Duration: Longer heatwaves result in hotter surfaces and increase fatigue and dehydration risk.
- Nighttime temperatures: Unconditioned buildings rely on nighttime ventilation for cooling. If night temperatures increase, buildings are more likely to overheat
- Relative humidity: High RH reduces the cooling effect of sweating.
In the plots below, we use the simplified thresholds recommended by the German Meteorological Office (DWD) as follows:

- Heatwave Day: The third consecutive day where the temperature exceeds 28°C (82.4°C).
- Hot Day: A day where the maximum temperature exceeds 30°C (86°F).
- Hot Night: A night where the minimum temperature exceeds 20°C (68°F).

## Data
In this repo we analyse several datasets to help us better understand heatwaves. We want to use these data to identify the district with the highest heat risk and plan a walking route to do some site measurements.

### Land Surface Temperature
Taken from satellites at a 30m resolution, this is useful to understand spatial heat distribution, but cannot be used alone to describe thermal comfort. 
#ToDo:
- Look at the LST distribution in each district
- Identify the sources of extreme outliers
- Separate ground and building temperatures
### Meteostat data
There are a handful of weather stations around prague which provide weather records from the past decades.
#ToDo:
- Combine temperature, humidity and radiation to get a better estimate of thermal comfort (at least in an open field)
### Prague's Microclimate measurement campaign
Running between January 2023 and September 2024, we can use these sensors to better understand the impact of urban context on microclimate.
#ToDo:
- Cluster the temperatures based on their deviation from the mean at different times of the day. 
- Add features which describe the sensor surroundings
- Try to generalize how landscape impacts the microclimate
### Handheld weather stations:
We will take these with us for a walk around the city and map the results
#ToDo:
- Load the data
- Find creative ways to plot the readings on the map and along a time axis
### Personal thermal comfort surveys:
It is unlikely to be hot during the trip, but we should still be able to observe variations in comfort.
#ToDo:
- Load the data
- Map it to the handheald weather station data
### Population data for Prague:
Helps us understand distribution of different risk groups
#ToDo:
- Load the data
- Add it to the dashboard map
### Open Street Map, Local data:
We can use this to get more contextual information, such as the number of trees, schools, etc. in each neighborhood
#ToDo:
- decide which points of interest we find interesting and load them
- Add them to the map
- Split them by district and count them
## Dashboard
Everything comes together in the streamlit dashboard. For the dashboard to run locally you first need to run the notebooks.

## Project Organization

```
├── README.md          <- The top-level README for developers using this project.
├── data
│   ├── external       <- Data from third party sources.
│   ├── interim        <- Intermediate data that has been transformed.
│   ├── processed      <- The final, canonical data sets for modeling.
│   └── raw            <- The original, immutable data dump.
│
├── models             <- Trained and serialized models, model predictions, or model summaries
│
├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering),
│                         the creator's initials, and a short `-` delimited description, e.g.
│                         `1.0-jqp-initial-data-exploration`.
│
├── references         <- Data dictionaries, manuals, and all other explanatory materials.
│
├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
│   └── figures        <- Generated graphics and figures to be used in reporting
│
├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
│                         generated with `pip freeze > requirements.txt`
│
├── setup.cfg          <- Configuration file for flake8
│
└── usecase_mobility   <- Source code for use in this project.
    │
    ├── __init__.py             <- Makes usecase_mobility a Python module
    │
    ├── config.py               <- Store useful variables and configuration
    │
    ├── dataset.py              <- Scripts to download or generate data
    │
    ├── features.py             <- Code to create features for modeling
    │
    ├── modeling                
    │   ├── __init__.py 
    │   ├── predict.py          <- Code to run model inference with trained models          
    │   └── train.py            <- Code to train models
    │
    └── plots.py                <- Code to create visualizations
```

--------
