from arcgis.gis import GIS
import os
from dotenv import load_dotenv
load_dotenv()

ARCGIS_USER = os.getenv("ARCGIS_USER")
ARCGIS_PASSWORD = os.getenv("ARCGIS_PASSWORD")

def get_survey(arcgis_user:str, arcgis_password:str, title: str="Thermal Comfort Survey"):
    # Sign in to ArcGIS Online
    gis = GIS("https://www.arcgis.com", arcgis_user, arcgis_password)
    # Access the Survey123 feature layer
    surveys = gis.content.search(query=f"title:{title}, owner:Jonas_DKSR", item_type="Feature Layer", )
    survey_layer = surveys[0].layers[0]
    survey_data = survey_layer.query(where="1=1", as_df=True)
    return survey_data