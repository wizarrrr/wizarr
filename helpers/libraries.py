from models import Libraries

def get_libraries():
    # Get all libraries from the database
    libraries = list(Libraries.select().execute())
    
    # Return all libraries
    return libraries

def get_libraries_id():
    # Get all libraries from the database with only the ID into a list[str]
    libraries = [library.id for library in Libraries.select().execute()]
    
    # Return all libraries
    return libraries

def get_libraries_name():
    # Get all libraries from the database with only the name into a list[str]
    libraries = [library.name for library in Libraries.select().execute()]
    
    # Return all libraries
    return libraries