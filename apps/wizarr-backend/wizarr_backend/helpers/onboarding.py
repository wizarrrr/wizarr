from enum import Enum
from peewee import fn
from app.models.database.settings import Settings
from app.models.database.onboarding import Onboarding

class TemplateType(Enum):
    Discord = 1
    Request = 2
    Download = 3

def getNextOrder():
    return (Onboarding.select(fn.MAX(Onboarding.order)).scalar() or -1) + 1

def populateForServerType(server_type: str):
    next_order = getNextOrder()
    if(server_type == "plex"):
        Onboarding.create(id=1, order=next_order, value="## ℹ️ Eh, So, What is Plex exactly?\n\nGreat question! Plex is a software that allows individuals to share their media collections with others. If you've received this invitation, it means someone wants to share their library with you.\n\nWith Plex, you'll have access to all of the movies, TV shows, music, and photos that are stored on their server!\n\nSo let's see how to get started!")
        Onboarding.create(id=2, order=next_order + 1, template=TemplateType.Download.value, value="## Join & Download Plex\n\nSo you now have access to our server's media collection. Let's make sure you know how to use it with Plex.\n\nPlanning on watching movies on this device?")
    elif(server_type == "jellyfin"):
        Onboarding.create(id=3, order=next_order, value="## ℹ️ Eh, So, What is Jellyfin exactly?\n\nJellyfin is a platform that lets you stream all your favorite movies, TV shows, and music in one place. It's like having your own personal movie theater right at your fingertips! Think of it as a digital library of your favorite content that you can access from anywhere, on any device - your phone, tablet, laptop, smart TV, you name it.?\n\n## 🍿 Right, so how do I watch stuff??\n\nIt couldn't be simpler! Jellyfin is available on a wide variety of devices including laptops, tablets, smartphones, and TVs. All you need to do is download the Jellyfin app on your device, sign in with your account, and you're ready to start streaming your media. It's that easy!")
        Onboarding.create(id=4, order=next_order + 1, template=TemplateType.Download.value, value="## Join & Download Jellyfin\n\nSo you now have access to our server's media collection. Let's make sure you know how to use it with Jellyfin.\n\nPlanning on watching movies on this device?")
    elif(server_type == "emby"):
        Onboarding.create(id=5, order=next_order, value="## ℹ️ Eh, So, What is Emby exactly?\n\nEmby is a platform that lets you stream all your favorite movies, TV shows, and music in one place. It's like having your own personal movie theater right at your fingertips! Think of it as a digital library of your favorite content that you can access from anywhere, on any device - your phone, tablet, laptop, smart TV, you name it.\n\n## 🍿 Right, so how do I watch stuff?\n\nIt couldn't be simpler! Emby is available on a wide variety of devices including laptops, tablets, smartphones, and TVs. All you need to do is download the Emby app on your device, sign in with your account, and you're ready to start streaming your media. It's that easy!")
        Onboarding.create(id=6, order=next_order + 1, template=TemplateType.Download.value, value="## Join & Download Emby\n\nGreat news! You now have access to our server's media collection. Let's make sure you know how to use it with Emby.\n\nPlanning on watching movies on this device?")

def showStatic(template: int, show: bool):
    static_row = Onboarding.get_or_none(template=template)
    if show:
        if not static_row:
            Onboarding.create(order=getNextOrder(), template=template, editable=False)
        elif static_row.enabled == False:
            static_row.enabled = True
            static_row.save()
    else:
        if static_row and static_row.enabled == True:
            static_row.enabled = False
            static_row.save()


def showRequest(show: bool):
    showStatic(TemplateType.Request.value, show)

def showDiscord(show: bool):
    showStatic(TemplateType.Discord.value, show)

