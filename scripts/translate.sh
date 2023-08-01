#!/bin/bash

# GET SCRIPT DIRECTORY AND PARENT DIRECTORY
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ROOT_DIR=$SCRIPT_DIR/..

# MAKE SURE WE ARE IN THE ROOT DIRECTORY
cd $ROOT_DIR

pybabel extract -F babel.cfg -k _l -o messages.pot .
pybabel update -i messages.pot -d app/translations
python translate.py
pybabel compile -d app/translations