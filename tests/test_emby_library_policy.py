from app.services.media.emby import EmbyClient

EMBY_LIBRARIES = [
    {
        "Id": "3",
        "Guid": "2a97f52972644bc2b7b52b0c9c0e9053",
        "Name": "Movies",
    },
    {
        "Id": "5",
        "Guid": "9f14df642ca947db933576babc24f36b",
        "Name": "Music",
    },
]


class _Response:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


def _emby_client():
    client = object.__new__(EmbyClient)
    client.policy_updates = []

    def get(endpoint):
        if endpoint == "/Library/MediaFolders":
            return _Response({"Items": EMBY_LIBRARIES})
        if endpoint == "/Users/emby-user-1":
            return _Response({"Policy": {"EnableAllFolders": True}})
        raise AssertionError(f"Unexpected endpoint: {endpoint}")

    def set_policy(user_id, policy):
        client.policy_updates.append((user_id, policy))

    client.get = get
    client.set_policy = set_policy
    return client


def test_emby_libraries_use_guid_for_external_id():
    assert _emby_client().libraries() == {
        "2a97f52972644bc2b7b52b0c9c0e9053": "Movies",
        "9f14df642ca947db933576babc24f36b": "Music",
    }


def test_emby_scan_libraries_uses_guid_for_external_id(monkeypatch):
    captured = {}

    def fake_get(url, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _Response({"Items": EMBY_LIBRARIES})

    monkeypatch.setattr("app.services.media.emby.requests.get", fake_get)

    assert EmbyClient().scan_libraries("http://emby.local", "test-token") == {
        "Movies": "2a97f52972644bc2b7b52b0c9c0e9053",
        "Music": "9f14df642ca947db933576babc24f36b",
    }
    assert captured["url"] == "http://emby.local/Library/MediaFolders"
    assert captured["headers"]["Authorization"] == 'MediaBrowser Token="test-token"'


def test_emby_set_specific_folders_maps_legacy_id_to_guid():
    client = _emby_client()

    client._set_specific_folders("emby-user-1", ["3"])

    assert client.policy_updates == [
        (
            "emby-user-1",
            {
                "EnableAllFolders": False,
                "EnabledFolders": ["2a97f52972644bc2b7b52b0c9c0e9053"],
                "EnableMediaPlayback": True,
                "EnableAudioPlaybackTranscoding": True,
                "EnableVideoPlaybackTranscoding": True,
                "EnablePlaybackRemuxing": True,
                "EnableRemoteAccess": True,
            },
        )
    ]


def test_emby_set_specific_folders_maps_name_to_guid():
    client = _emby_client()

    client._set_specific_folders("emby-user-1", ["Movies"])

    assert client.policy_updates[0][1]["EnabledFolders"] == [
        "2a97f52972644bc2b7b52b0c9c0e9053"
    ]
