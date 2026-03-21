import geopandas as gpd
from shapely.geometry import Point
from db import update_location
from db import update_emergency_description




def location_verifier(streamsid: str, address: str):
    error = None

    for attempt in range(3):
        try:
            coord = gpd.tools.geocode(address)

            if not coord.empty and not coord.geometry.iloc[0].is_empty:
                point = coord.geometry.iloc[0]
                normalized_address = coord.address.iloc[0]

                update_location(streamsid, point.y, point.x, normalized_address)

                return {
                    "gps": {
                        "lat": point.y,
                        "lon": point.x
                    },
                    "address": normalized_address
                }

        except Exception as e:
            error = e

    update_location(streamsid, None, None, address)

    if error is not None:
        message = f"Not found after retries due to error: {error}"
    else:
        message = "Not found after retries: geocoder returned no match"

    return {
        "gps": {
            "lat": None,
            "lon": None
        },
        "address": message
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
    
