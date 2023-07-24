#!/bin/bash

# GET SCRIPT DIRECTORY AND PARENT DIRECTORY
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ROOT_DIR=$SCRIPT_DIR/..

# MAKE SURE WE ARE IN THE ROOT DIRECTORY
cd $ROOT_DIR

# CHECK PYTHON 3 IS INSTALLED
if ! command -v python3 &> /dev/null
then
    echo "Python 3 could not be found"
    exit
fi

# CHECK PIP 3 IS INSTALLED
if ! command -v pip &> /dev/null
then
    echo "Pip could not be found"
    exit
fi

# CHECK NPM IS INSTALLED
if ! command -v npm &> /dev/null
then
    echo "NPM could not be found"
    exit
fi

# CHECK NODE IS INSTALLED
if ! command -v node &> /dev/null
then
    echo "Node could not be found"
    exit
fi

# CREATE PYTHON VIRTUAL ENVIRONMENT
python3 -m venv venv

# ACTIVATE PYTHON VIRTUAL ENVIRONMENT
source venv/bin/activate

# INSTALL PYTHON DEPENDENCIES
pip install -r requirements.txt

# CREATE DATABASE DIRECTORY
mkdir $ROOT_DIR/database

# MOVE TO STATIC DIRECTORY
cd $ROOT_DIR/app/static

# INSTALL NPM DEPENDENCIES
npm install

# MOVE BACK TO ROOT DIRECTORY
cd $ROOT_DIR

# DEFINE COLORS
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# CLEAR THE SCREEN
clear

# TELL USER TO ACTIVATE VIRTUAL ENVIRONMENT BEFORE RUNNING SERVER WITH FANCY COLORS
printf "======================================================================================\n"
printf "| ${GREEN}Build environment setup complete!                                                  ${NC}|\n"
printf "| ${RED}Make sure to activate the virtual environment before running the server!           ${NC}|\n"
printf "| source venv/bin/activate                                                           ${NC}|\n"
printf "| ${RED}To deactivate the virtual environment, run:                                        ${NC}|\n"
printf "| deactivate                                                                         ${NC}|\n"
printf "======================================================================================\n"
