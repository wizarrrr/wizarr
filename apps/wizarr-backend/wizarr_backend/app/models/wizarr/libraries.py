from schematics.models import Model
from schematics.types import StringType, DateTimeType, BaseType, URLType
from schematics.exceptions import DataError, ValidationError

from json import loads, JSONDecodeError
from app.models.database.libraries import Libraries
from app.models.database.settings import Settings
from logging import info

class SpecificLibrariesType(BaseType):
    """Converts a string to a list if needed"""

    def to_native(self, value, _):
        if isinstance(value, str):
            try:
                return loads(value)
            except JSONDecodeError as e:
                raise ValidationError("Invalid libraries") from e

        return value


class LibraryModel(Model):
    """Libraries List Model"""

    id = StringType(required=True)
    name = StringType(required=True)
    created = DateTimeType(required=False, convert_tz=True)


class ScanLibrariesModel(Model):
    """Scan Libraries Model"""

    server_type = StringType(required=False, choices=["plex", "jellyfin", "emby"])
    server_url = URLType(fqdn=False, required=False)
    server_api_key = StringType(required=False)


class LibrariesModel(Model):
    """Libraries Model"""

    # ANCHOR - Libraries Model
    libraries: list[str] = SpecificLibrariesType(required=False, default=[])


    # ANCHOR - Validate libraries
    def validate_libraries(self, _, value):
        # Check that the value is a list
        if not isinstance(value, list):
            raise ValidationError("Invalid libraries")

        # Check that the libraries are valid
        for library_id in value:

            # Check that the library is a string
            if not isinstance(library_id, str):
                raise ValidationError("Invalid library id")

            # Check that the library exists in the database
            if not Libraries.get_or_none(Libraries.id == library_id):
                raise ValidationError(f"Invalid library {library_id}")


    # ANCHOR - Get Plex Libraries
    def get_plex_libraries(self, server_url: str, server_api_key: str):
        from helpers.plex import scan_plex_libraries
        plex_libraries = scan_plex_libraries(server_api_key, server_url)
        return [{"id": str(library.uuid), "name": library.title} for library in plex_libraries]


    # ANCHOR - Get Jellyfin Libraries
    def get_jellyfin_libraries(self, server_url: str, server_api_key: str):
        from helpers.jellyfin import scan_jellyfin_libraries
        jellyfin_libraries = scan_jellyfin_libraries(server_api_key, server_url)
        return [{"id": library["Id"], "name": library["Name"]} for library in jellyfin_libraries]


    # ANCHOR - Get Emby Libraries
    def get_emby_libraries(self, server_url: str, server_api_key: str):
        from helpers.emby import scan_emby_libraries
        emby_libraries = scan_emby_libraries(server_api_key, server_url)
        return [{"id": library["Guid"], "name": library["Name"]} for library in emby_libraries]


    # ANCHOR - Compare Libraries
    def compare_libraries(self, server_libraries: list[dict]):
        # pylint: disable=unsupported-membership-test
        return [library for library in server_libraries if library["id"] in self.libraries]


    # ANCHOR - Delete Libraries
    def delete_libraries(self, libraries: list[dict]) -> int:
        return Libraries.delete().where(Libraries.id.not_in([library["id"] for library in libraries])).execute()


    # ANCHOR - Update Libraries to Database
    def update_libraries(self):
        # Get server_type, server_url, and server_api_key from the database
        settings = {
            settings.key: settings.value
            for settings in Settings.select().where(
                (Settings.key == "server_type") | (Settings.key == "server_url") | (Settings.key == "server_api_key")
            )
        }

        # Place the settings into variables
        server_type, server_url, server_api_key = settings["server_type"], settings["server_url"], settings["server_api_key"]

        # Check variables are not None
        if server_type is None or server_url is None or server_api_key is None:
            raise DataError("Invalid server settings")


        # Functions to get libraries from the server
        server_libraries_func = {
            "plex": self.get_plex_libraries,
            "jellyfin": self.get_jellyfin_libraries,
            "emby": self.get_emby_libraries
        }

        # Get the libraries from the server
        server_libraries = server_libraries_func[server_type](server_url, server_api_key)

        # Check that the libraries are not None
        if server_libraries is None:
            raise DataError("Invalid Libraries")

        # Compare the libraries from the server to the libraries from the client
        libraries = self.compare_libraries(server_libraries)

        # Delete all libraries THAT ARE NOT in the list of libraries
        deleted_count = self.delete_libraries(libraries)

        # Log the deleted libraries
        info(f"Deleted {deleted_count} libraries")

        # Loop through new libraries
        for library in libraries:

            # Attempt to get the library from the database
            db_library = Libraries.get_or_none(Libraries.id == library["id"])

            # Create the library if it does not exist
            if db_library is None:
                Libraries.create(id=library["id"], name=library["name"])
                info(f"Library {library['name']} created")
                continue

            # Update the library if it exists
            if db_library.name != library["name"]:
                db_library.name = library["name"]
                db_library.save()
                info(f"Library {library['name']} updated")
                continue

            # Log that the library already exists
            info(f"Library {library['name']} already exists")


        # Set libraries to the libraries from the database
        setattr(self, "libraries", [{"id": library.id, "name": library.name} for library in Libraries.select()])
