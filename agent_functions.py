import geopandas as gpd
from shapely.geometry import Point
from db import update_location
from db import update_emergency_description


def location_verifier(streamsid: str, address: str):
    error = None
    point = None
    normalized_address = address

    try:
        coord = gpd.tools.geocode(address)

        if not coord.empty and not coord.geometry.iloc[0].is_empty:
            point = coord.geometry.iloc[0]
            normalized_address = coord.address.iloc[0]
        else:
            error = "No location found"

    except Exception as e:
        error = e

    if error is None and point is not None:
        update_location(streamsid, point.y, point.x, normalized_address)
        return {
            "gps": {
                "lat": point.y,
                "lon": point.x
            },
            "address": normalized_address
        }
    else:
        update_location(streamsid, 0, 0, address)
        return {
            "gps": {
                "lat": None,
                "lon": None
            },
            "address": f"Not found due to error: {error}"
        }

def note_emergency_description(streamsid: str, emergency_description: str):
    """
    Updates the specific database record that belongs to the streamsid. 
    It adds the emergency_descrpition attribute of this function to the existing emergency description of the record
    

    Args:
        emergency_description (str): String of the emergency description or of new information regarding the emergency description
        streamsid (str): unique identifier of the session call 
        
    Result: Confirmation that the emergency description has been either 
            - added,
            - updated,
            - not entered update due to an error
    """
    try:
        existing_emergency_description = update_emergency_description(streamsid, emergency_description)
        if existing_emergency_description is None:
            return f"The emergency description has been succesfully added"
        else: 
            return f"The emergency description has been successfully updated"
    except Exception as e:
        return f"The emergency description has not been added or updated, due to the following error: {e}"
    
