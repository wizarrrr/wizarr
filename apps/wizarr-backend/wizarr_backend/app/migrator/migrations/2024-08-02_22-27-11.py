#
# CREATED ON VERSION: V4.1.1
# MIGRATION: 2024-08-02_22-27-11
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

    # update onboarding table with columns (needs to be recreated)
    with db.transaction():
        # Step 1: Create a new table with the desired structure
        db.execute_sql("""
        CREATE TABLE "onboarding_temp" (
            "id" INTEGER NOT NULL UNIQUE,
            "value" TEXT,
            "order" INTEGER NOT NULL,
            "enabled" INTEGER NOT NULL DEFAULT 1,
            "template" INTEGER,
            "editable" INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY("id")
        )
        """)

        # Step 2: Copy data from the existing table to the new table
        db.execute_sql("""
        INSERT INTO onboarding_temp ("id", "value", "order", "enabled")
        SELECT "id", "value", "order", "enabled" FROM onboarding;
        """)

        # Step 3: Drop the old table
        db.execute_sql("DROP TABLE onboarding;")

        # Step 4: Rename the new table to match the old table's name
        db.execute_sql("ALTER TABLE onboarding_temp RENAME TO onboarding;")


    # populate onboarding with default values
    with db.transaction():

        # Check if the onboarding table is empty
        if not db.execute_sql("SELECT EXISTS(SELECT 1 FROM onboarding)").fetchone()[0]:
            # Check if server_type is set in the settings table
            if db.execute_sql("SELECT key FROM settings WHERE key = 'server_type'").fetchone():
                # Get the server_type
                server_type = db.execute_sql("SELECT value FROM settings WHERE key = 'server_type'").fetchone()[0]
                if(server_type == "plex"):
                    db.execute_sql("""
                    INSERT INTO onboarding ("id", "order", "value") VALUES
                        (1, 0, '## ℹ️ Eh, So, What is Plex exactly?

Great question! Plex is a software that allows individuals to share their media collections with others. If you''ve received this invitation, it means someone wants to share their library with you.

With Plex, you''ll have access to all of the movies, TV shows, music, and photos that are stored on their server!

So let''s see how to get started!'),
                        (2, 1, '## Join & Download Plex

So you now have access to our server''s media collection. Let''s make sure you know how to use it with Plex.

Planning on watching movies on this device? [Download Plex](https://www.plex.tv/en-gb/media-server-downloads/#plex-app) for this device.

[Open Plex in browser ↗]({{server_url}})')
                    """)
                if(server_type == "jellyfin"):
                    db.execute_sql("""
                    INSERT INTO onboarding ("id", "order", "value") VALUES
                        (3, 0, '## ℹ️ Eh, So, What is Jellyfin exactly?

Jellyfin is a platform that lets you stream all your favorite movies, TV shows, and music in one place. It''s like having your own personal movie theater right at your fingertips! Think of it as a digital library of your favorite content that you can access from anywhere, on any device - your phone, tablet, laptop, smart TV, you name it.?

## 🍿 Right, so how do I watch stuff?

It couldn''t be simpler! Jellyfin is available on a wide variety of devices including laptops, tablets, smartphones, and TVs. All you need to do is download the Jellyfin app on your device, sign in with your account, and you''re ready to start streaming your media. It''s that easy!'),
                        (4, 1, '## Join & Download Jellyfin

So you now have access to our server''s media collection. Let''s make sure you know how to use it with Jellyfin.

Planning on watching movies on this device? [Download Jellyfin](https://jellyfin.org/downloads) for this device.

[Open Jellyfin in browser ↗]({{server_url}})')
                    """)
                if(server_type == "emby"):
                    db.execute_sql("""
                    INSERT INTO onboarding ("id", "order", "value") VALUES
                        (5, 0, '## ℹ️ Eh, So, What is Emby exactly?

Emby is a platform that lets you stream all your favorite movies, TV shows, and music in one place. It''s like having your own personal movie theater right at your fingertips! Think of it as a digital library of your favorite content that you can access from anywhere, on any device - your phone, tablet, laptop, smart TV, you name it.

## 🍿 Right, so how do I watch stuff?

It couldn''t be simpler! Emby is available on a wide variety of devices including laptops, tablets, smartphones, and TVs. All you need to do is download the Emby app on your device, sign in with your account, and you''re ready to start streaming your media. It''s that easy!'),
                        (6, 1, '## Join & Download Emby

Great news! You now have access to our server''s media collection. Let''s make sure you know how to use it with Emby.

Planning on watching movies on this device? [Download Emby](https://emby.media/download.html) for this device.

[Open Emby in browser ↗]({{server_url}})')
                    """)

            add_requests = db.execute_sql("SELECT EXISTS(SELECT 1 FROM requests)").fetchone()[0]

            if db.execute_sql("""SELECT key FROM settings WHERE key = 'server_discord_id' AND value IS NOT NULL""").fetchone():
                db.execute_sql("""INSERT INTO onboarding ("id", "order", "template", "editable") VALUES (7, 2, 1, 0)""")
                if add_requests:
                    db.execute_sql("""INSERT INTO onboarding ("id", "order", "template", "editable") VALUES (8, 3, 2, 0)""")

            elif add_requests:
                db.execute_sql("""INSERT INTO onboarding ("id", "order", "template", "editable") VALUES (8, 2, 2, 0)""")
