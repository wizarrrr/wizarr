from ipaddress import ip_interface
from logging import error
from socket import gethostbyname
from typing import Optional

from nmap import PortScanner
from requests import get
from schematics.exceptions import ValidationError
from schematics.types import URLType

def get_host_ip_from_container():
    """
    Get the IP address of the Docker host from inside the container
    :return: str | None
    """

    # Retrieve the IP address of the Docker host from inside the container
    try:
        return gethostbyname("host-gateway")
    except Exception:
        return None

def get_internal_ip_from_container():
    """
    Get the internal IP address of the container
    :return: str | None
    """

    # Retrieve the IP address of the Docker host from inside the container
    try:
        return gethostbyname("host.docker.internal")
    except Exception:
        return None

def get_subnet_from_ip(host_ip: str):
    """
    Get the subnet of the given IP address
    :return: str
    """

    # Calculate the subnet of the container"s host IP address
    subnet_ip = ip_interface(f"{host_ip}/24")
    subnet = subnet_ip.network

    # Return the subnet
    return subnet

def detect_server(server_url: str):
    """
    Detect what type of media server is running at the given url

    :param server_url: The url of the media server
    :type server_url: str

    :return: object
    """

    # Create URLType object
    url_validator = URLType(fqdn=False)

    # Create a url object
    url = url_validator.valid_url(server_url)

    # Check if the url is valid
    if not url:
        raise ValidationError("Invalid url, malformed input")

    # If the url has path, query, or fragment, raise an exception
    if url["query"] or url["frag"]:
        raise ValidationError("Invalid url, must be a base url")

    # Get host from url
    host = url["hostn"] or url["host4"] or url["host6"]

    # Construct the url from the server url
    server_url = f"{url['scheme']}://{host}"

    # Add the port if it exists
    if url["port"]:
        server_url += f":{url['port']}"

    # Add the path if it exists
    if url["path"] and url["path"] != "/":
        server_url += url["path"]

    # Map endpoints to server types
    endpoints = {
        "plex": "/identity",
        "jellyfin": "/System/Info/Public",
        "emby": "/System/Info/Public"
    }

    # Loop through the endpoints to find the server type
    for server_type, endpoint in endpoints.items():
        # Make the request, don't allow redirects, and set the timeout to 30 seconds
        try:
            response = get(f"{server_url}{endpoint}", allow_redirects=False, timeout=30)
        except Exception as e:
            error(e)
            continue

        if response.status_code == 200:
            # This is to handle Emby and Jellyfin servers having the same endpoint
            if server_type == "jellyfin":
                # ProductName is only available in Jellyfin
                if "ProductName" not in response.json():
                    continue

            return {
                "server_type": server_type,
                "server_url": server_url
            }

    # Raise an exception if the server type is not found
    raise ConnectionError("Media Server could not be contacted")

def verify_server(server_url: str, server_api_key: str):
    """
    Verify that the api credentials are valid for the media server

    :param server_url: The url of the media server
    :type server_url: str

    :param server_api_key: The api key of the media server
    :type server_api_key: str

    :return: object
    """

    # Get the server type
    server = detect_server(server_url)
    server_type = server["server_type"]
    server_url = server["server_url"]

    # Map endpoints for verifying the server
    endpoints = {
        "plex": f"/connections?X-Plex-Token={server_api_key}",
        "jellyfin": f"/System/Info?api_key={server_api_key}",
        "emby": f"/System/Info?api_key={server_api_key}"
    }

    # Build the url for the server
    server_url += endpoints[server_type]

    # Make the request, don't allow redirects, and set the timeout to 30 seconds
    try:
        response = get(server_url, allow_redirects=False, timeout=30)
    except ConnectionError as e:
        raise ConnectionError("Unable to connect to server") from e

    # Check if the response is valid
    if response.status_code == 200:
        return {
            "server_type": server_type,
            "server_url": server["server_url"]
        }

    # Raise an exception if the server type is not found
    raise ConnectionError("Unable to verify server")

def scan_network(ports: Optional[int | str | list[int | str]] = None, target: Optional[str | list[str]] = None):
    """
    Scan the network for media servers
    :param ports: The ports to scan
    :param target: The target to scan

    :return: list
    """

    # Create a PortScanner object
    nmap = PortScanner()
    media_servers = []

    # Set default ports if not provided
    if ports is None:
        ports = [8096, 32400]

    # Set default target if not provided
    if target is None:
        # Get the dockers internal and external IP addresses
        external_address = get_host_ip_from_container()
        internal_address = get_internal_ip_from_container()

        # Create a list of targets
        targets = []

        # Add the external ip address to the list of targets if it exists
        if external_address:
            targets.append(f"{get_subnet_from_ip(external_address)}")

        # Add the internal ip address to the list of targets if it exists
        if internal_address:
            targets.append(f"{get_subnet_from_ip(internal_address)}")

        # Convert the list of targets to a string
        target = f"{' '.join(targets)}"

    # If target is a list, convert it to a string
    if isinstance(target, list):
        target = " ".join(target)

    # Ensure ports is a list
    if isinstance(ports, (int, str)):
        ports = [str(ports)]

    # Convert ports to strings
    ports = [str(port) for port in ports]

    # Convert ports list to a string
    port_str = ",".join(ports)

    # Scan the network
    nmap.scan(hosts=target, arguments=f"-p {port_str} --open")

    # Iterate through each host
    for host in nmap.all_hosts():
        # Check open ports and determine server type
        for port in nmap[host]["tcp"].keys():
            # Check if the port is open
            if nmap[host]["tcp"][port]["state"] == "open":
                try:
                    # Attempt to detect the server type
                    server_info = detect_server(f"http://{host}:{port}")
                    server_type = server_info.get("server_type", None)

                    # If the server type is None, skip it
                    if server_type is None:
                        continue

                    # Add server information to the list
                    media_servers.append({"host": host, "port": port, "server_type": server_type })

                except Exception:
                    # If an exception occurs, pass to the next port
                    pass

    # Return the list of media servers
    return media_servers
