from dataclasses import dataclass
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.models import Invitation


@dataclass(frozen=True)
class ExternalEnrollmentContext:
    invite_code: str
    state: str
    callback_url: str


class ExternalEnrollmentProvider(Protocol):
    def build_url(
        self,
        invitation: Invitation,
        context: ExternalEnrollmentContext,
    ) -> str: ...


class StaticUrlEnrollmentProvider:
    def build_url(
        self,
        invitation: Invitation,
        context: ExternalEnrollmentContext,
    ) -> str:
        if not invitation.external_enrollment_url:
            raise ValueError("External enrollment URL is required")

        if not invitation.external_enrollment_append_context:
            return invitation.external_enrollment_url

        return append_query_params(
            invitation.external_enrollment_url,
            {
                "source": "wizarr",
                "invite_code": context.invite_code,
                "state": context.state,
                "callback_url": context.callback_url,
            },
        )


def get_external_enrollment_provider(provider_name: str) -> ExternalEnrollmentProvider:
    if provider_name == "static_url":
        return StaticUrlEnrollmentProvider()

    raise ValueError(f"Unsupported external enrollment provider: {provider_name}")


def build_external_enrollment_url(
    invitation: Invitation,
    context: ExternalEnrollmentContext,
) -> str:
    provider = get_external_enrollment_provider(
        invitation.external_enrollment_provider or "static_url"
    )
    return provider.build_url(invitation, context)


def append_query_params(url: str, params: dict[str, str]) -> str:
    parts = urlsplit(url)
    query_params = dict(parse_qsl(parts.query, keep_blank_values=True))
    query_params.update(params)

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query_params),
            parts.fragment,
        )
    )
