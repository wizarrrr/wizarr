# IMPORTANT INFORMATION
##### IT IS IMPORTANT THAT YOU DO NOT MODIFY OTHER PEOPLES MIGRATION SCRIPTS UNLESS YOU KNOW WHAT YOU ARE DOING, THESE SCRIPTS ARE TO PREVENT DATA LOSS WHEN PEOPLE UPDATE WIZARR.

##### IN MOST CASES YOUR BEST OPTION IF YOU ENCOUNTER SOMETHING YOU NEED TO CHANGE IS TO CREATE A NEW MIGRATION SCRIPT THAT WILL RUN AFTER THE SCRIPT YOU NEED TO CHANGE.


# Migrations Folder

The migrations folder is a directory that contains scripts for managing changes to a database schema. These scripts are used to create, modify, and delete database tables, columns, indexes, and other objects.

This task is performed automatically at first runtime of the application. The migration scripts are executed in the order they are found in the migrations folder. In this case by order of date and time.

## Getting Started

To get started with migrations, you'll need to follow these steps:

1. Create a new migration script in the migrations folder. You can do this by running the create-migration.sh or .bat file in the root of the project. This will create a new file with a timestamp in the name and template code for the migration.

2. Write the migration code in the script. This code should define the changes you want to make to the database schema. For example, you might add a new column to a table, or modify an existing column.

4. YOU ARE IN CHARGE OF MAKING SURE YOUR MIGRATION SCRIPT ONLY RUNS ONCE, MAKE SURE TO CHECK THE DATABASE AT THE BEGINNING OF YOUR SCRIPT TO SEE IF THE MIGRATION HAS ALREADY BEEN APPLIED.

5. Run the migration script using an old version of the database, one from before you made any changes.

4. Verify that the migration was successful by checking the database. You should see the changes you made in the migration script.

## Conclusion

The migrations folder is an essential part of managing changes to a database schema. By following the steps outlined above, you can get started with migrations and ensure that Wizarr users have a smooth experience when updating their software.