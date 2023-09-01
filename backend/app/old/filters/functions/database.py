def database_get(table: str, column: str = None, value: str = None):
    # Find the table in app.models.database
    try:
        for model in dir(__import__("app.models.database", fromlist=[table])):
            if model.lower() == table.lower():
                # Get the table from app.models.database
                table = getattr(__import__("app.models.database", fromlist=[table]), model)

                # If column is None, return the entire table
                if column is None:
                    return table.select().dicts()

                # Find the column in the table
                for column_name in dir(table):
                    if column_name.lower() == column.lower():
                        # Get the column from the table
                        column = getattr(table, column_name)

                        # If value is None, return the entire table with only the column
                        if value is None:
                            return table.select(column).dicts()

                        # Find the value in the column
                        for row in table.select():
                            if getattr(row, column_name) == value:
                                return row.to_dict()
    except Exception:
        pass
