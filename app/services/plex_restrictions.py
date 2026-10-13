"""Plex content restrictions that an invitation applies to the new share.

Plex filters each library type with labels and content ratings. plexapi
takes one dict for each library type and sends it with the share request,
for example ``{"label!": ["private"], "contentRating": ["G", "PG"]}``:

- ``label``: show only the items that have one of these labels
- ``label!``: hide the items that have one of these labels
- ``contentRating``: show only the items that have one of these ratings
- ``contentRating!``: hide the items that have one of these ratings

Plex has no rating filter for music libraries, so music takes labels only.
Plex has no "maximum rating" filter. An admin lists the ratings to allow or
to exclude.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

PlexFilter = dict[str, list[str]]

# Form field suffix -> plexapi filter key
_LABEL_FILTERS = {"allow_labels": "label", "exclude_labels": "label!"}
_ALL_FILTERS = {
    **_LABEL_FILTERS,
    "allow_ratings": "contentRating",
    "exclude_ratings": "contentRating!",
}

# Library type -> the filters that Plex accepts for it
LIBRARY_FILTERS: dict[str, dict[str, str]] = {
    "movies": _ALL_FILTERS,
    "television": _ALL_FILTERS,
    "music": _LABEL_FILTERS,
}


def split_values(raw: Any) -> list[str]:
    """Values of a comma-separated string or a list, without blanks or duplicates.

    plexapi joins the values with an encoded comma, so a value cannot hold one.
    """
    items = raw if isinstance(raw, list | tuple) else [raw]
    values: list[str] = []
    for item in items:
        for part in str(item or "").split(","):
            value = part.strip()
            if value and value not in values:
                values.append(value)
    return values


def _form_name(kind: str, suffix: str) -> str:
    return f"plex_{kind}_{suffix}"


def _form_values(form: Any, name: str) -> list[str]:
    # The invite modal has one set of fields for each Plex server.
    raw = form.getlist(name) if hasattr(form, "getlist") else form.get(name)
    return split_values(raw)


def _filter_from_form(form: Any, kind: str) -> PlexFilter:
    plex_filter: PlexFilter = {}
    for suffix, key in LIBRARY_FILTERS[kind].items():
        values = _form_values(form, _form_name(kind, suffix))
        if values:
            plex_filter[key] = values
    return plex_filter


@dataclass(frozen=True)
class PlexRestrictions:
    """Label and rating filters for each Plex library type."""

    movies: PlexFilter = field(default_factory=dict)
    television: PlexFilter = field(default_factory=dict)
    music: PlexFilter = field(default_factory=dict)

    def __bool__(self) -> bool:
        return bool(self.movies or self.television or self.music)

    @classmethod
    def from_form(cls, form: Any) -> "PlexRestrictions":
        """Read fields such as ``plex_movies_exclude_labels`` from a form."""
        return cls(**{kind: _filter_from_form(form, kind) for kind in LIBRARY_FILTERS})

    @classmethod
    def from_invitation(cls, invitation: Any) -> "PlexRestrictions":
        return cls(
            movies=invitation.plex_filter_movies or {},
            television=invitation.plex_filter_television or {},
            music=invitation.plex_filter_music or {},
        )

    def invitation_columns(self) -> dict[str, PlexFilter | None]:
        """Values for the Invitation columns. None if a type has no filter."""
        return {
            "plex_filter_movies": self.movies or None,
            "plex_filter_television": self.television or None,
            "plex_filter_music": self.music or None,
        }

    def plexapi_kwargs(self) -> dict[str, PlexFilter]:
        """Keyword arguments for plexapi inviteFriend, createExistingUser and updateFriend."""
        return {
            "filterMovies": dict(self.movies),
            "filterTelevision": dict(self.television),
            "filterMusic": dict(self.music),
        }


def form_fields_from_api(payload: Any) -> dict[str, list[str]]:
    """Convert the ``plex_restrictions`` object of the API to form fields.

    The object has the shape ``{"movies": {"exclude_labels": ["private"]}}``.
    Raises ValueError for a library type or a filter that Plex does not have.
    """
    if payload is None:
        return {}
    if not isinstance(payload, Mapping):
        raise ValueError("plex_restrictions must be an object")
    fields: dict[str, list[str]] = {}
    for kind, filters in payload.items():
        if kind not in LIBRARY_FILTERS:
            raise ValueError(f"Unknown Plex library type: {kind}")
        if not isinstance(filters, Mapping):
            raise ValueError(f"plex_restrictions.{kind} must be an object")
        for suffix, values in filters.items():
            if suffix not in LIBRARY_FILTERS[kind]:
                raise ValueError(f"Unknown Plex restriction for {kind}: {suffix}")
            fields[_form_name(kind, suffix)] = split_values(values)
    return fields
