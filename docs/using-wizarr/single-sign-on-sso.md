# Single-Sign-On (SSO)

#### **Wizarr supports SSO via disabling its inbuilt authentication**

To Disable Wizarr's inbuilt authentication in order to put it behind a Proxy Provider (Authelia, Authentik...), set the following variable:

`DISABLE_BUILTIN_AUTH=True`

#### Whitelist Public Paths (important!)

In order to make the invitation process available for non signed in users, make sure you whitelist the following paths:

{% tabs %}
{% tab title="Authelia" %}
Authelia matches each expression against the path and the query string, so every expression also accepts a `?`.

```
    - domain: wizarr.domain.com
      resources:
        - '^/j([/?].*)?$'
        - '^/join([/?].*)?$'
        - '^/invitation/process([/?].*)?$'
        - '^/plex/callback([/?].*)?$'
        - '^/wizard([/?].*)?$'
        - '^/reset/.+$'
        - '^/setup([/?].*)?$'
        - '^/static([/?].*)?$'
        - '^/image-proxy([/?].*)?$'
        - '^/cinema-posters([/?].*)?$'
        - '^/favicon\.ico$'

      policy: bypass
```
{% endtab %}

{% tab title="Authentik/Other" %}
Paste these lines into the **Unauthenticated Paths** field of the Proxy Provider. Put one expression on each line. Do not add quotes or a `-` in front of a line. Authentik reads them as part of the expression, and then no path matches.

```
^/j(/.*)?$
^/join([/?].*)?$
^/invitation/process$
^/plex/callback$
^/wizard(/.*)?$
^/reset/.+$
^/setup(/.*)?$
^/static(/.*)?$
^/image-proxy$
^/cinema-posters$
^/favicon\.ico$
```

In **Forward auth (domain level)** mode, Authentik matches the full URL, not only the path. The full URL includes the query string, for example `/join?code=ABC123` from the invitation code page. For this reason, the `/join` expression also accepts a `?`. Add the scheme and the host to each line, for example `^https://wizarr\.domain\.com/j(/.*)?$`.
{% endtab %}
{% endtabs %}

The PWA manifest (`/static/manifest.json`) and the icons are under `/static`, so the `/static` expression covers them.

Do not whitelist `/login`. When `DISABLE_BUILTIN_AUTH=True`, `/login` signs in every visitor as an admin. The `/api` paths are not necessary for invitations. Whitelist `/api` only if external tools call the Wizarr API. The API endpoints then accept only requests with a valid `X-API-Key` header, but the API documentation at `/api/docs/` becomes public.

#### Cloudflare Access: verify the token

`DISABLE_BUILTIN_AUTH=True` trusts whatever reaches Wizarr. Anything that can reach its port directly, such as another container on the same host or a misconfigured firewall, gets the admin pages without going through your proxy.

If Wizarr sits behind Cloudflare Access, it can check Access's signed token itself instead. Set both of these:

```
CF_ACCESS_TEAM_DOMAIN=yourteam.cloudflareaccess.com
CF_ACCESS_AUD=<the application's AUD tag>
```

The AUD tag is in Zero Trust under Access > Applications > your Wizarr app > Additional settings > Application Audience (AUD) Tag.

With both set, every admin request must carry a valid `Cf-Access-Jwt-Assertion` header: signed by your team's key, for this application, issued by your team domain and not expired. A session cookie on its own grants nothing. This takes precedence over `DISABLE_BUILTIN_AUTH` and the built-in login. The invitation paths above stay public, `/health` needs no token, and API keys work as before.

If the signing keys can't be fetched from `https://<team>/cdn-cgi/access/certs`, admin access is refused rather than allowed. To get back in, unset the two variables and restart.

---

## Native OIDC Sign-In (Admin Panel)

As of this release, Wizarr can also authenticate administrators directly against an OpenID Connect provider (Authentik, Keycloak, Authelia, Okta, Auth0, Azure AD, ...) without putting Wizarr behind a reverse proxy. This is separate from the proxy-based approach above:

- The proxy approach (`DISABLE_BUILTIN_AUTH=True`) authenticates *every* request before it reaches Wizarr, including the public invite pages, and grants admin access to anyone who passes the proxy.
- Native OIDC only replaces the *admin login page*. Invited users still join a media server exactly as before.

### Setup

1. In your identity provider, create an OIDC application/client for Wizarr (confidential client, Authorization Code flow with PKCE).
2. In Wizarr, go to **Settings → OIDC**, enable it, and fill in:
   - **Discovery URL** — your provider's `.well-known/openid-configuration` URL.
   - **Client ID** / **Client Secret** — from the application you created.
   - **Admin Claim** / **Admin Claim Allowed Values** (strongly recommended) — restricts admin access to identities carrying a specific claim value (e.g. a `groups` claim containing `wizarr-admins`). **If left blank, anyone who can authenticate with your identity provider becomes a Wizarr admin.**
3. Register Wizarr's callback URL with your identity provider: `https://<your-wizarr-address>/oidc/callback`. If Wizarr is reachable at more than one address (a LAN IP and a public domain, for example), register one callback URL per address — most providers (Authentik, Keycloak, Auth0, Okta, Azure AD) accept a list of valid redirect URIs per application. The exact URL to register is shown on the Settings → OIDC page.

### Limitations

- Admin-panel login only — end users accepting an invite don't go through OIDC.
- SAML is not yet supported (see the project's SSO feasibility notes for why OIDC was prioritized).
