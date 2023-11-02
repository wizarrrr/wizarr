#!/usr/bin/env python
from datetime import datetime
from os import path
from packaging.version import parse

def get_current_version():
    # File path to the version file
    version_file = path.abspath(path.join(path.dirname(path.realpath(__file__)), "../", "../", "../", "../", "../", "latest"))

    # Read the current version
    with open(version_file, "r") as f:
        current_version = parse(f.read())

    return current_version

# Get the current script's directory
script_dir = path.dirname(path.abspath(__file__ if '__file__' in locals() else path.abspath(path.realpath(__file__))))

# Define the path to the template file relative to the script's directory
template_file = path.join(script_dir, "template.py")

# Get the current date and time in YYYY-MM-DD_HH-MM-SS format
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Create the filename with the current date in the current directory
filename = path.join(script_dir, "migrations", f"{current_time}.py")

# Read the content of the template file
with open(template_file, "r") as template:
    template_content = template.read()

# Replace {data} with Tue Oct 10 2023 date format and replace {name} with the filename
template_content = template_content.replace("{date}", datetime.now().strftime("%a %b %d %Y"))
template_content = template_content.replace("{name}", current_time)
template_content = template_content.replace("{version}", str(get_current_version()))

# Write the modified content to the new file
with open(filename, "w") as new_file:
    new_file.write(template_content)

print(f"MIGRATION: {filename} created")
