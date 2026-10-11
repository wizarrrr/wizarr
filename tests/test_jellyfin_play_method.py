"""Jellyfin and Emby put PlayMethod in PlayState (#815).

Wizarr read session["PlayMethod"], which is not there. Thus every session
with a TranscodingInfo block showed as a transcode. A browser often gets a
remux: the server copies the video and the audio into a new container. A
remux is a direct stream, not a transcode. The Jellyfin dashboard uses the
same rules.

No test uses the network.
"""

import pytest

from app.services.media.emby import EmbyClient
from app.services.media.jellyfin import JellyfinClient

REMUX = {
    "IsVideoDirect": True,
    "IsAudioDirect": True,
    "VideoCodec": "h264",
    "AudioCodec": "aac",
    "Container": "ts",
}
VIDEO_TRANSCODE = {**REMUX, "IsVideoDirect": False, "Framerate": 48}


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _client(cls):
    client = cls.__new__(cls)
    client.url = "http://media.local"
    client.token = "admin-key"
    client.server_id = None
    return client


def _session(play_method, transcoding=None):
    session = {
        "Id": "s1",
        "UserName": "sam",
        "NowPlayingItem": {
            "Id": "i1",
            "Name": "Heat",
            "Type": "Movie",
            "RunTimeTicks": 100,
        },
        "PlayState": {
            "PositionTicks": 50,
            "IsPaused": False,
            "PlayMethod": play_method,
        },
    }
    if transcoding:
        session["TranscodingInfo"] = transcoding
    return session


@pytest.mark.parametrize("cls", [JellyfinClient, EmbyClient])
@pytest.mark.parametrize(
    ("play_method", "transcoding", "expected"),
    [
        pytest.param("DirectPlay", VIDEO_TRANSCODE, (False, True), id="direct-play"),
        pytest.param("DirectStream", None, (False, False), id="direct-stream"),
        pytest.param("Transcode", REMUX, (False, False), id="remux"),
        pytest.param("Transcode", VIDEO_TRANSCODE, (True, False), id="transcode"),
    ],
)
def test_play_method_comes_from_play_state(cls, play_method, transcoding, expected):
    entry = _client(cls)._now_playing_entry(_session(play_method, transcoding))

    info = entry["transcoding_info"]
    assert (info["is_transcoding"], info["direct_play"]) == expected
    assert entry["metadata"]["play_method"] == play_method


def test_emby_statistics_do_not_count_a_remux_as_a_transcode():
    client = _client(EmbyClient)
    payloads = {
        "/Sessions": [_session("Transcode", REMUX)],
        "/Users": [],
        "/System/Info": {"Version": "4.8"},
    }
    client.get = lambda path, **_kw: _Resp(payloads[path])

    stats = client.statistics()

    assert stats["server_stats"]["transcoding_sessions"] == 0
