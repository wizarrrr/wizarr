#
# CREATED ON VERSION: V4.1.1
# MIGRATION: 2024-08-02_17-30-11
# CREATED: Fri Aug 02 2024
#

from peewee import *
from playhouse.migrate import *

from app import db

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

def run():
    # Use migrator to perform actions on the database
    migrator = SqliteMigrator(db)

    # Create new table 'fixedonboarding' and populate it with default values
    with db.transaction():
        # Check if the table exists
        cursor = db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fixedonboarding';")
        table_exists = cursor.fetchone()

        if not table_exists:
            db.execute_sql("""
                CREATE TABLE "fixedonboarding" (
                    "id" INTEGER NOT NULL UNIQUE,
                    "value"	TEXT NOT NULL,
                    PRIMARY KEY("id")
                )
            """)
            print("Table 'fixedonboarding' created successfully")
            db.execute_sql("""
                INSERT INTO fixedonboarding (id, value) VALUES
                    (1, '## ℹ️ Eh, So, What is Plex exactly?

Great question! Plex is a software that allows individuals to share their media collections with others. If you''ve received this invitation, it means someone wants to share their library with you.

With Plex, you''ll have access to all of the movies, TV shows, music, and photos that are stored on their server!

So let''s see how to get started!'),
                    (2, '## Join & Download Plex

So you now have access to our server''s media collection. Let''s make sure you know how to use it with Plex.

Planning on watching movies on this device? [Download Plex](https://www.plex.tv/en-gb/media-server-downloads/#plex-app) for this device.

[Open Plex in browser ↗]({{server_url}})'),
                    (3, '## ℹ️ Eh, So, What is Jellyfin exactly?

Jellyfin is a platform that lets you stream all your favorite movies, TV shows, and music in one place. It''s like having your own personal movie theater right at your fingertips! Think of it as a digital library of your favorite content that you can access from anywhere, on any device - your phone, tablet, laptop, smart TV, you name it.?

## 🍿 Right, so how do I watch stuff??

It couldn''t be simpler! Jellyfin is available on a wide variety of devices including laptops, tablets, smartphones, and TVs. All you need to do is download the Jellyfin app on your device, sign in with your account, and you''re ready to start streaming your media. It''s that easy!'),
                    (4, '## Join & Download Jellyfin

So you now have access to our server''s media collection. Let''s make sure you know how to use it with Jellyfin.

Planning on watching movies on this device? [Download Jellyfin](https://jellyfin.org/downloads) for this device.

[Open Jellyfin in browser ↗]({{server_url}})'),
                    (5, '## ℹ️ Eh, So, What is Emby exactly?

Emby is a platform that lets you stream all your favorite movies, TV shows, and music in one place. It''s like having your own personal movie theater right at your fingertips! Think of it as a digital library of your favorite content that you can access from anywhere, on any device - your phone, tablet, laptop, smart TV, you name it.

## 🍿 Right, so how do I watch stuff?

It couldn''t be simpler! Emby is available on a wide variety of devices including laptops, tablets, smartphones, and TVs. All you need to do is download the Emby app on your device, sign in with your account, and you''re ready to start streaming your media. It''s that easy!'),
                    (6, '## Join & Download Emby

Great news! You now have access to our server''s media collection. Let''s make sure you know how to use it with Emby.

Planning on watching movies on this device? [Download Emby](https://emby.media/download.html) for this device.

[Open Emby in browser ↗]({{server_url}})')
            """)
            print("Table 'fixedonboarding' populated successfully")
        else:
            print("Table 'fixedonboarding' already exists")

    print("Migration 2024-07-30_11-02-04 complete")
