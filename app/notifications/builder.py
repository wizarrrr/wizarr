from inspect import getmembers, isclass

from app.notifications import providers
from app.notifications.model import Model


def build_web_resource(resource: type(providers)):
    # Store metadata for each field in the resource
    metadata = []

    # Loop through each field in the resource
    for field in resource.items():
        # Get the metadata for the field in the resource class
        field_metadata = resource.fields[field[0]].metadata

        # Get the default value for the field in the resource class
        field_default = resource.fields[field[0]].default

        # Get if the field is required in the resource class
        field_required = resource.fields[field[0]].required

        # Get the field name in the resource class
        field_name = field[0]

        # Get the type of the field in the resource class
        field_type = resource.fields[field[0]].primitive_type.__name__

        # Create a dictionary for the fields metadata
        data = {}

        # Add the field name to the data dictionary
        if field_metadata:
            data["name"] = field_metadata["name"]
            data["metadata"] = field_metadata

        # Add the field default value to the data dictionary
        if field_default:
            data["default"] = field_default

        # Add the field required value to the data dictionary
        if field_required:
            data["required"] = field_required

        # Add the field name to the data dictionary
        if field_name:
            data["field_name"] = field_name

        # Add the field type to the data dictionary
        if field_type:
            data["type"] = field_type

        # Add to the metadata dictionary
        metadata.append(data)

    # Return the metadata dictionary
    return metadata


def get_web_resources():
    # Store all resources
    resources = []

    # Get all classes from app.notifications.providers
    classes = getmembers(providers, isclass)

    # Filter the classes based on their name
    resource_classes = [cls for cls in classes if cls[0].endswith('Resource')]

    # Loop through each resource class and build the web resource
    for cls in resource_classes:
        web_resource = build_web_resource(cls[1]())
        resource_name = web_resource[0]["name"]

        resources.append({
            "name": resource_name,
            "class": cls[1].__name__,
            "resource": web_resource,
        })

    return resources


def validate_resource(resource: str, data: dict or str) -> Model:
    # Make sure the resource name is valid and ends with Resource
    if not resource.endswith("Resource"):
        raise ValueError("Invalid resource name")

    # Get the resource class from the providers module by name
    resource_class = getattr(providers, resource)

    try:
        # Validate the data against the resource class
        resource_model: Model = resource_class(validate=True, strict=False)

        # Load the data into the model
        if isinstance(data, str):
            resource_model.from_json(data)
        elif isinstance(data, dict):
            resource_model.import_data(data)
        else:
            raise ValueError("Invalid data passed to resource")

    except Exception as e:
        raise ValueError(f"Invalid data passed to {resource}") from e

    # Add the resource name to the model
    resource_model.resource = resource
    resource_model.resource_class = resource_class

    # Add metadata to the model, but only run build_web_resource if access is attempted
    resource_model.metadata = lambda: build_web_resource(resource_model)

    # Return the validated data
    return resource_model
