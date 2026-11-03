"""SQLite-serialized Emby join provenance and explicit, retryable revocation.

An interrupted create is not recoverable from a name/email guess. Keep it open;
never infer complete identities from the absence of local users.
"""

from typing import Any, cast
from uuid import uuid4

from app.extensions import db
from app.models import (
    Invitation,
    InvitationAccess,
    InvitationJoinAttempt,
    MediaServer,
    User,
)


class JoinClosed(ValueError):
    pass


def _access_locked(invitation_id):
    # The first write acquires SQLite's writer lock, including against DELETE's
    # tombstone trigger. Reload after acquiring it, not from the identity map.
    exists = Invitation.query.filter_by(id=invitation_id).update(
        {Invitation.id: Invitation.id}
    )
    if not exists:
        raise JoinClosed("Invitation no longer exists")
    db.session.expire_all()
    inv = db.session.get(Invitation, invitation_id)
    if inv is None:
        raise JoinClosed("Invitation no longer exists")
    access = InvitationAccess.query.filter_by(code=inv.code.upper()).first()
    if access is None:
        servers = list(cast(Any, inv.servers)) or ([inv.server] if inv.server else [])
        legacy = bool(
            inv.used
            or inv.used_by_id
            or inv.users
            or User.query.filter_by(code=inv.code).first()
        )
        complete = (
            not legacy
            and not inv.create_ldap_user
            and bool(servers)
            and all(s.server_type == "emby" for s in servers)
        )
        access = InvitationAccess(
            id=uuid4().hex,
            code=inv.code.upper(),
            invitation_id=inv.id,
            baseline_complete=complete,
        )
        db.session.add(access)
        db.session.flush()
    servers = list(cast(Any, inv.servers)) or ([inv.server] if inv.server else [])
    if (
        inv.create_ldap_user
        or not servers
        or any(s.server_type != "emby" for s in servers)
    ):
        access.baseline_complete = False
    if access.invitation_id != inv.id or access.deleted:
        raise JoinClosed("Invitation code has been retired")
    return access


def register_join(code, server_id):
    db.session.commit()
    inv = Invitation.query.filter(
        db.func.upper(Invitation.code) == code.upper()
    ).first()
    if inv is None:
        raise JoinClosed("Invalid invitation")
    iid = inv.id
    db.session.commit()
    try:
        access = _access_locked(iid)
        if access.barrier:
            raise JoinClosed("Invitation revoked")
        # A crashed/lost-response create must not be retried as a new operation.
        if InvitationJoinAttempt.query.filter_by(
            access_id=access.id, server_id=server_id, finished=False
        ).first():
            raise JoinClosed("An earlier join is still unresolved")
        server = db.session.get(MediaServer, server_id)
        if server is None or server.server_type != "emby":
            raise JoinClosed("Unsupported or missing server")
        attempt = InvitationJoinAttempt(
            id=uuid4().hex,
            access_id=access.id,
            server_id=server_id,
            server_ref_id=server_id,
            server_url=server.url,
        )
        db.session.add(attempt)
        db.session.commit()
        return attempt.id
    except Exception:
        db.session.rollback()
        raise


def guarded_post(attempt_id, path, send):
    """Serialize each remote write against the committed cutoff, across workers."""
    db.session.commit()
    attempt = db.session.get(InvitationJoinAttempt, attempt_id)
    if attempt is None:
        raise JoinClosed("Join provenance is missing")
    aid = attempt.access_id
    db.session.commit()
    try:
        admitted = InvitationAccess.query.filter_by(
            id=aid, barrier=False, deleted=False
        ).update({InvitationAccess.barrier: False})
        if not admitted:
            raise JoinClosed("Invitation closed during join")
        attempt = db.session.get(InvitationJoinAttempt, attempt_id)
        if attempt is None:
            raise JoinClosed("Join provenance is missing")
        if path == "/Users/New":
            # Commit uncertainty BEFORE the request; the following writer lock
            # still checks the cutoff again before performing the side effect.
            if not attempt.create_started:
                attempt.create_started = True
                db.session.commit()
                return guarded_post(attempt_id, path, send)
            if attempt.remote_user_id:
                raise JoinClosed("Create already returned an identity")
        response = send()
        if path == "/Users/New":
            remote_id = response.json().get("Id")
            if not isinstance(remote_id, str) or not remote_id:
                raise ValueError("Emby create returned no identity")
            attempt.remote_user_id = remote_id
        db.session.commit()
        return response
    except BaseException:
        db.session.rollback()
        raise


def finish_join(attempt_id):
    db.session.rollback()
    attempt = db.session.get(InvitationJoinAttempt, attempt_id)
    if attempt is None:
        raise JoinClosed("Join provenance is missing")
    if attempt.remote_user_id or not attempt.create_started:
        attempt.finished = True
        # Link only the exact returned backend ID, never a username/email match.
        user = (
            User.query.filter_by(
                server_id=attempt.server_id, token=attempt.remote_user_id
            ).first()
            if attempt.remote_user_id
            else None
        )
        attempt.user_id = user.id if user else None
    aid = attempt.access_id
    db.session.commit()
    access = db.session.get(InvitationAccess, aid)
    if access is None:
        raise JoinClosed("Invitation provenance is missing")
    closed = access.barrier or access.deleted
    if access.barrier:
        reconcile(aid)
    return closed


def commit_barrier(invitation_id):
    db.session.commit()
    try:
        access = _access_locked(invitation_id)
        access.barrier = True
        aid = access.id
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    reconcile(aid)
    result = status(aid)
    if result is None:
        raise JoinClosed("Invitation provenance is missing")
    return result


def reconcile(access_id):
    """Retry known identities only; no delete fallback, no implicit create retry."""
    from app.services.media.emby import EmbyClient
    from app.services.media.service import get_client_for_media_server

    access = db.session.get(InvitationAccess, access_id)
    if not access or not access.barrier:
        return
    attempts = InvitationJoinAttempt.query.filter_by(access_id=access_id).all()
    for attempt in attempts:
        if not attempt.remote_user_id:
            continue
        server = db.session.get(MediaServer, attempt.server_id)
        confirmed = "unconfirmed"
        if (
            server
            and server.server_type == "emby"
            and attempt.server_ref_id == server.id
            and attempt.server_url == server.url
        ):
            client = cast(EmbyClient, get_client_for_media_server(server))
            try:
                # get_user_details() is local-only; use the authoritative endpoint.
                data = client.get(f"/Users/{attempt.remote_user_id}").json()
                if data.get("Id") == attempt.remote_user_id and isinstance(
                    data.get("Policy"), dict
                ):
                    policy = data["Policy"]
                    if policy.get("IsDisabled") is not True:
                        policy["IsDisabled"] = True
                        client.set_policy(attempt.remote_user_id, policy)
                    readback = client.get(f"/Users/{attempt.remote_user_id}").json()
                    if (
                        readback.get("Id") == attempt.remote_user_id
                        and readback.get("Policy", {}).get("IsDisabled") is True
                    ):
                        confirmed = "disabled"
            except Exception:
                # A 404 may mean unavailable/unauthorized routing in Emby's
                # documented contract; it is not proof of authoritative absence.
                confirmed = "unconfirmed"
        attempt.remote_state = confirmed
        db.session.commit()


def status(access_id):
    access = db.session.get(InvitationAccess, access_id)
    if not access:
        return None
    attempts = (
        InvitationJoinAttempt.query.filter_by(access_id=access_id)
        .order_by(InvitationJoinAttempt.id)
        .all()
    )
    inflight = sum(not a.finished for a in attempts)
    complete = access.baseline_complete and all(
        a.finished and (a.remote_user_id is not None or not a.create_started)
        for a in attempts
    )
    accounts = [
        {
            "join_attempt_id": a.id,
            "server_id": a.server_id,
            "remote_user_id": a.remote_user_id,
            "user_id": a.user_id,
            "remote_state": a.remote_state,
        }
        for a in attempts
        if a.remote_user_id
    ]
    revoked = (
        access.barrier
        and not inflight
        and complete
        and all(a["remote_state"] == "disabled" for a in accounts)
    )
    return {
        "operation_id": access.id,
        "barrier_committed": access.barrier,
        "in_flight_joins": inflight,
        "account_ids_complete": bool(complete),
        "state": "revoked" if revoked else "pending",
        "accounts": accounts,
    }
