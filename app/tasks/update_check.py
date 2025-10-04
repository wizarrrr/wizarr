"""Background tasks for update checking and manifest fetching."""

import json
import logging
from datetime import UTC, datetime

import requests

from app.extensions import db
from app.models import Settings

MANIFEST_URL = "https://update.wizarr.dev"
TIMEOUT_SECS = 10


def fetch_and_cache_manifest(app=None):
    """Fetch manifest.json from GitHub and cache it in the database.

    Args:
        app: Flask application instance. If None, will try to get from current context.
    """
    if app is None:
        from flask import current_app

        try:
            app = current_app._get_current_object()  # type: ignore
        except RuntimeError:
            logging.error(
                "fetch_and_cache_manifest called outside application context and no app provided"
            )
            return

    with app.app_context():
        try:
            # Get current version for User-Agent
            import os

            current_version = os.getenv("APP_VERSION", "dev")

            # Fetch the manifest from GitHub
            resp = requests.get(
                MANIFEST_URL,
                timeout=TIMEOUT_SECS,
                headers={
                    "Accept": "application/json",
                    "User-Agent": f"Wizarr/{current_version} (https://github.com/wizarrrr/wizarr)",
                },
            )
            resp.raise_for_status()
            manifest_data = resp.json()

            # Store the manifest data in the database
            manifest_setting = Settings.query.filter_by(key="cached_manifest").first()
            if not manifest_setting:
                manifest_setting = Settings(key="cached_manifest")
                db.session.add(manifest_setting)

            manifest_setting.value = json.dumps(manifest_data)

            # Update the last fetch timestamp
            timestamp_setting = Settings.query.filter_by(
                key="manifest_last_fetch"
            ).first()
            if not timestamp_setting:
                timestamp_setting = Settings(key="manifest_last_fetch")
                db.session.add(timestamp_setting)

            timestamp_setting.value = datetime.now(UTC).isoformat()

            db.session.commit()
            logging.info("📦 Manifest cached successfully from %s", MANIFEST_URL)

            # Check if update is available and log/notify it
            try:
                import os

                from app.services.notifications import notify
                from app.services.update_check import check_update_available

                raw_version = os.getenv("APP_VERSION", "dev")
                if raw_version != "dev":
                    latest_version = manifest_data.get("latest_version")
                    if check_update_available(raw_version):
                        logging.info(
                            "🔄 UPDATE AVAILABLE: %s → %s", raw_version, latest_version
                        )

                        # Check if we've already notified about this version
                        last_notified_setting = Settings.query.filter_by(
                            key="last_notified_version"
                        ).first()
                        last_notified_version = (
                            last_notified_setting.value
                            if last_notified_setting
                            else None
                        )

                        # Only send notification if this is a new version we haven't notified about
                        if last_notified_version != latest_version:
                            try:
                                notify(
                                    title="Wizarr Update Available",
                                    message=f"A new version of Wizarr is available: {raw_version} → {latest_version}",
                                    tags="update,wizarr",
                                    event_type="update_available",
                                )

                                # Record that we've notified about this version
                                if not last_notified_setting:
                                    last_notified_setting = Settings(
                                        key="last_notified_version"
                                    )
                                    db.session.add(last_notified_setting)

                                last_notified_setting.value = latest_version
                                db.session.commit()

                                logging.info(
                                    "📢 Update notification sent to configured agents for version %s",
                                    latest_version,
                                )
                            except Exception as notify_error:
                                logging.warning(
                                    "Failed to send update notification: %s",
                                    notify_error,
                                )
                                db.session.rollback()
                        else:
                            logging.debug(
                                "Update %s already notified, skipping notification",
                                latest_version,
                            )
                    else:
                        logging.info("✅ Running latest version: %s", raw_version)
                else:
                    latest_version = manifest_data.get("latest_version", "unknown")
                    logging.info(
                        "🧪 Development version (latest stable: %s)", latest_version
                    )
            except Exception as e:
                logging.debug("Could not check update status: %s", e)

        except requests.RequestException as e:
            logging.warning("❌ Failed to fetch manifest from %s: %s", MANIFEST_URL, e)
            # Keep existing cached data if available

        except Exception as e:
            logging.error("❌ Unexpected error while caching manifest: %s", e)
            db.session.rollback()
