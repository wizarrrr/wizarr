import logging
import requests
from app.extensions import db
from app.models import Settings

class JellyfinClient:
    """Minimal wrapper around the Jellyfin REST API."""
    def __init__(self):
        # pull server_url and api_key via SQLAlchemy scalar queries
        self.url = (
            db.session
              .query(Settings.value)
              .filter_by(key="server_url")
              .scalar()
        )
        self.key = (
            db.session
              .query(Settings.value)
              .filter_by(key="api_key")
              .scalar()
        )
        self.hdrs = {"X-Emby-Token": self.key}

    # ─── raw helpers ───────────────────────────────────────────────
    def get(self, path: str):
        r = requests.get(f"{self.url}{path}", headers=self.hdrs, timeout=10)
        logging.info("GET  %s%s → %s", self.url, path, r.status_code)
        r.raise_for_status()
        return r

    def post(self, path: str, payload: dict):
        r = requests.post(
            f"{self.url}{path}",
            json=payload,
            headers=self.hdrs,
            timeout=10
        )
        logging.info("POST %s%s → %s", self.url, path, r.status_code)
        r.raise_for_status()
        return r

    def delete(self, path: str):
        r = requests.delete(f"{self.url}{path}", headers=self.hdrs, timeout=10)
        logging.info("DEL  %s%s → %s", self.url, path, r.status_code)
        r.raise_for_status()
        return r

    # ─── convenience wrappers ────────────────────────────────────
    def libraries(self) -> dict[str, str]:
        return {
            item["Name"]: item["Id"]
            for item in self.get("/Library/MediaFolders").json()["Items"]
        }

    def create_user(self, username: str, password: str) -> str:
        return self.post(
            "/Users/New",
            {"Name": username, "Password": password}
        ).json()["Id"]

    def set_policy(self, user_id: str, policy: dict) -> None:
        self.post(f"/Users/{user_id}/Policy", policy)

    def delete_user(self, user_id: str) -> None:
        self.delete(f"/Users/{user_id}")

    def get_user(self, jf_id: str) -> dict:
        return self.get(f"/Users/{jf_id}").json()

    def update_user(self, jf_id: str, form: dict) -> dict | None:
        """Return updated user JSON (Jellyfin echoes it back)."""
        current = self.get_user(jf_id)

        # coerce incoming strings into correct types
        for key, val in form.items():
            for section in ("Policy", "Configuration"):
                if key in current[section]:
                    target = current[section][key]
                    if isinstance(target, bool):
                        val = (val == "True")
                    elif isinstance(target, int):
                        val = int(val)
                    elif isinstance(target, list):
                        val = [] if val == "" else val.split(", ")
                    current[section][key] = val

        return self.post(f"/Users/{jf_id}", current).json()


def scan_libraries(url: str, token: str) -> dict[str, str]:
    """
    Return a mapping of {name: id} for every media folder on the server.
    """
    resp = requests.get(
        f"{url}/Library/MediaFolders",
        headers={"X-Emby-Token": token},
        timeout=5
    )
    resp.raise_for_status()
    return {
        item["Name"]: item["Id"]
        for item in resp.json()["Items"]
    }
