from app.models.database import Libraries
from app.models.wizarr.libraries import LibraryModel
from playhouse.shortcuts import model_to_dict

# INDEX OF FUNCTIONS
# - Get Libraries
# - Get Library by ID
# - Get Library by Name
# - Get Libraries IDs
# - Get Libraries Names

# ANCHOR - Get Libraries
def get_libraries() -> list[Libraries]:
    """Get all libraries from the database

    :return: A list of libraries
    """

    # Get all libraries from the database
    libraries: list[Libraries] = Libraries.select()

    # Convert the libraries to a list of dictionaries
    libraries = [LibraryModel(model_to_dict(library)).to_primitive() for library in libraries]

    # Return a list of libraries
    return libraries


# ANCHOR - Get Library by ID
def get_library_by_id(library_id: int, verify: bool = True) -> Libraries or None:
    """Get a library by id
    :param library_id: The id of the library
    :type library_id: int

    :param verify: Whether or not to verify the library exists
    :type verify: bool

    :return: A library
    """

    # Get the library by id
    library = Libraries.get_or_none(Libraries.id == library_id)

    # Check if the library exists
    if library is None and verify:
        raise ValueError("Library does not exist")

    # Return the library
    return library


# ANCHOR - Get Library by Name
def get_library_by_name(library_name: str, verify: bool = True) -> Libraries or None:
    """Get a library by name

    :param library_name: The name of the library
    :type library_name: str

    :param verify: Whether or not to verify the library exists
    :type verify: bool

    :return: A library
    """

    # Get the library by name
    library = Libraries.get_or_none(Libraries.name == library_name)

    # Check if the library exists
    if library is None and verify:
        raise ValueError("Library does not exist")

    # Return the library
    return library


# ANCHOR - Get Libraries IDs
def get_libraries_ids() -> list[str]:
    """Get all libraries from the database with only the ID

    :return: A list of str of libraries IDs
    """

    # Get all libraries from the database with only the ID into a list[str]
    libraries = Libraries.select()

    # Convert the libraries to a list of dictionaries with only the ID
    libraries = [model_to_dict(library, only=[Libraries.id]) for library in libraries]

    # Return all libraries
    return libraries


# ANCHOR - Get Libraries Names
def get_libraries_name():
    """Get all libraries from the database with only the name

    :return: A list of str of libraries names
    """

    # Get all libraries from the database with only the name into a list[str]
    libraries = Libraries.select()

    # Convert the libraries to a list of dictionaries with only the name
    libraries = [model_to_dict(library, only=[Libraries.name]) for library in libraries]

    # Return all libraries
    return libraries


# ANCHOR - Create Library
# TODO: Create Create Library

# ANCHOR - Update Library
# TODO: Create Update Library

# ANCHOR - Delete Library
def delete_library(library_id: int) -> None:
    """Delete a library by id
    :param library_id: The id of the library
    :type library_id: int

    :return: None
    """

    # Get the library by id
    library = get_library_by_id(library_id, False)

    # Check if the library exists
    if library is None:
        raise ValueError("Library does not exist")

    # Delete the library
    library.delete_instance()
