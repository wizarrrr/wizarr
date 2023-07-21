@echo off

REM Get the current date and time in YYYY-MM-DD_HH-MM-SS format
for /f "tokens=1-6 delims=:-/ " %%a in ("%date% %time%") do set "DATE=%%c-%%b-%%a_%%d-%%e-%%f"

REM Get current directory of the script
set "DIR=%~dp0"

REM Create the filename with the current date in the current directory
set "FILENAME=%DIR%%DATE%.py"

REM Create the file with the filename and add the import statements
echo from logging import error, migrations, warning > "%FILENAME%"

echo. >> "%FILENAME%"

echo from peewee import * >> "%FILENAME%"
echo from playhouse.migrate import * >> "%FILENAME%"
echo from logging import migrations >> "%FILENAME%"

echo. >> "%FILENAME%"

echo from app import db >> "%FILENAME%"
echo from app.exceptions import MigrationError >> "%FILENAME%"

echo. >> "%FILENAME%"

echo # Do not change the name of this file, >> "%FILENAME%"
echo # migrations are run in order of their filenames date and time >> "%FILENAME%"

echo. >> "%FILENAME%"

echo # PLEASE USE migrations('MESSAGE HERE') FOR ANY INFO LOGGING >> "%FILENAME%"
echo # Example: migrations('Creating table users') >> "%FILENAME%"
echo # Feel free to use error and warning for any errors or warnings >> "%FILENAME%"

echo. >> "%FILENAME%"

echo def run^(\^): >> "%FILENAME%"
echo     migrator = SqliteMigrator(db^) >> "%FILENAME%"
echo. >> "%FILENAME%"
echo     # Add your migrations here >> "%FILENAME%"

echo MIGRATION: %FILENAME% created

pause