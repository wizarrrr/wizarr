from plexapi.myplex import PlexServer
from pydantic import HttpUrl


def scan_plex_libraries(server_api_key: str, server_url: HttpUrl):
    # Get Plex URL as string
    api_url = str(server_url)
    
    # Get the libraries
    plex = PlexServer(api_url, server_api_key)
            
    # Get the raw libraries
    response: list[dict] = plex.library.sections()
    
    # Raise exception if raw_libraries is not a list
    if not isinstance(response, list):
        raise TypeError("Plex API returned invalid data.")
    
    return response