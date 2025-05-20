from app.models import Settings


def inject_server_name():
    # Option A: load the full Settings object
    setting = Settings.query.filter_by(key="server_name").first()
    server_name = setting.value if setting else "Wizarr"

    # Option B: load just the value column
    # server_name = (
    #     db.session
    #       .query(Settings.value)
    #       .filter_by(key="server_name")
    #       .scalar()
    # ) or "Wizarr"

    return {"server_name": server_name}
