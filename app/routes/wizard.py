from flask import Blueprint, render_template
from jinja2 import TemplateNotFound
from helpers import get_settings

wizard = Blueprint("wizard", __name__, template_folder="../views/client/wizard/")

@wizard.get("/help", defaults={"subpath": "welcome"})
@wizard.get("/help/<path:subpath>")
def help_routes(subpath):

    # Get all settings
    settings = get_settings()
    server_type = settings["server_type"]

    pages = [
        {
            "name": "welcome",
            "template": f"pages/{server_type}/welcome.html"
        },
        {
            "name": "download",
            "template": f"pages/{server_type}/download.html"
        },
        {
            "name": "requests",
            "template": "pages/requests.html",
            "enabled": bool(settings.get("request_type") != "None")
        },
        {
            "name": "discord",
            "template": "pages/" + ("discord-widget.html" if not settings.get("discord_widget") else "discord.html"),
            "enabled": bool(settings.get("discord_id"))
        },
        {
            "name": "custom",
            "template": "pages/custom.html",
            "enabled": settings.get("custom_html")
        },
        {
            "name": "tips",
            "template": f"pages/{server_type}/tips.html"
        }
    ]

    partials = [page["template"] for page in pages if page.get("enabled", True)]
    current = [page["name"] for page in pages if page.get("enabled", True)].index(subpath)


    data = {
        "partials": partials,
        "current": current,
        "server_type": server_type,
        "server_url": settings.get("server_url"),
    }

    data.update(settings)

    return render_template("wizard.html", **data)
