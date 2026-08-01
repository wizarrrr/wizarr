// Shared state for the Plex OAuth sign-in flow.
//
// Signing in happens on app.plex.tv in a second window, so two contexts can end
// up racing to finish the same join: the invite page that opened it, and the
// /plex/callback page that Plex forwards that window back to. The invite page
// stays the authority for as long as it is alive; the callback page only takes
// over when it is not, which is the normal outcome on mobile where the second
// window is a background tab the OS is free to freeze or discard.
//
// State lives in localStorage rather than sessionStorage because the two
// contexts are separate tabs and sessionStorage is per-tab.

const WIZARR_PLEX_OAUTH_KEY = "wizarr.plexOAuth";

function plexOAuthRead() {
    try {
        return JSON.parse(localStorage.getItem(WIZARR_PLEX_OAUTH_KEY)) || null;
    } catch (e) {
        return null;
    }
}

function plexOAuthWrite(state) {
    try {
        localStorage.setItem(WIZARR_PLEX_OAUTH_KEY, JSON.stringify(state));
    } catch (e) {
        // Storage can be unavailable (private mode, storage disabled). The flow
        // still works in the window that started it, it just is not resumable.
    }
}

function plexOAuthClear() {
    try {
        localStorage.removeItem(WIZARR_PLEX_OAUTH_KEY);
    } catch (e) {
        /* nothing to clean up */
    }
}

// Mark this context as the one finishing the join. Resolves false when the
// other context claimed it first, so only one POST /join is ever sent.
//
// localStorage has no compare-and-swap, so a plain read-modify-write can let
// both contexts pass the "is it claimed?" check and each believe it won. The
// claim is therefore two-phase: write a token unique to this call, wait a
// beat for a concurrent writer to overwrite it, then re-read and proceed only
// if our own token survived. The last write wins, and both contexts agree on
// who that was.
function plexOAuthClaim(who) {
    const state = plexOAuthRead();
    // No stored state means storage is unavailable, so there is no second
    // context to coordinate with and the caller is the only one who can finish.
    if (!state) return Promise.resolve(true);
    if (state.claimedBy && state.claimedBy !== who) {
        return Promise.resolve(false);
    }
    const token = who + ":" + Math.random().toString(36).slice(2);
    state.claimedBy = who;
    state.claimToken = token;
    plexOAuthWrite(state);
    return new Promise((resolve) => {
        setTimeout(function () {
            const confirmed = plexOAuthRead();
            // State gone mid-claim means the other context finished and
            // cleared it; anything but our own token still standing is a loss.
            resolve(!!confirmed && confirmed.claimToken === token);
        }, 75);
    });
}

// Ask plex.tv whether the pin has been linked yet. Resolves to the auth token,
// or null while the user is still signing in.
async function plexOAuthPollToken(state) {
    const resp = await fetch(`https://plex.tv/api/v2/pins/${state.pinId}`, {
        headers: {
            Accept: "application/json",
            "X-Plex-Client-Identifier": state.clientId,
        },
    }).then((r) => r.json());

    if (resp && resp.errors && resp.errors.length) {
        throw new Error(resp.errors[0].message || "Plex rejected the sign-in.");
    }
    return (resp && resp.authToken) || null;
}
