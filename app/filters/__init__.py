from flask import Flask

def register_filters(app: Flask):
    # Find all function filters in app/filters/functions and register them, do not register filters that start with _
    # and only go one level deep, do not import submodules, or imports that are inside module files
    for filter_name in dir(__import__("app.filters.functions", fromlist=["*"])):
        if not filter_name.startswith("_"):
            filter_func = getattr(__import__("app.filters.functions", fromlist=[filter_name]), filter_name)
            if callable(filter_func):
                app.add_template_filter(filter_func, filter_name)
