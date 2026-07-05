# External account enrollment

External enrollment lets a Wizarr invitation redirect the invitee to another signup or onboarding system before continuing the post-invite wizard.

Flow:

1. Invitee opens `/j/<invite-code>`.
2. Wizarr shows any pre-invite wizard steps.
3. Wizarr redirects to the configured external enrollment URL.
4. The external system handles account creation or login.
5. The external system redirects back to `/invitation/external/callback?state=...`.
6. Wizarr verifies the pending session state and a trusted authentication header.
7. Wizarr grants access to the post-invite wizard.

## Required trusted header

The callback does not trust query parameters alone. Configure a trusted reverse proxy or identity provider to protect the callback route and send an authentication header.

Example:

```env
EXTERNAL_ENROLLMENT_AUTH_HEADER=X-authentik-username
```

## Authentik setup example

External enrollment can be used with Authentik by redirecting Wizarr invitees to an Authentik enrollment flow and returning them to Wizarr after signup/login.

A typical flow looks like this:

1. The invitee opens a Wizarr invite link, for example `/j/ABC123`.
2. Wizarr shows any configured pre-invite wizard steps.
3. Wizarr redirects the invitee to the configured Authentik enrollment flow.
4. Authentik creates or authenticates the user.
5. Authentik redirects the user back to `/invitation/external/callback?state=...`.
6. Wizarr verifies the pending session state and a trusted Authentik proxy header.
7. Wizarr resumes the post-invite wizard.

### Wizarr configuration

Configure Wizarr to trust one Authentik header from your reverse proxy:

```env
EXTERNAL_ENROLLMENT_AUTH_HEADER=X-authentik-uid
```

`X-authentik-uid` is preferred because it is more stable than a username or email address. `X-authentik-username` can also be used if preferred.

When creating an invitation in Wizarr, use:

- Account creation mode: `Use external enrollment`
- External enrollment URL: your Authentik enrollment flow URL, for example:

```text
https://auth.example.com/if/flow/wizarr-enrollment/
```

- Enrollment URL context: `Append invite code, state, and callback URL`

When context appending is enabled, Wizarr appends parameters such as:

```text
source=wizarr
invite_code=ABC123
state=<random-state>
callback_url=https://wizarr.example.com/invitation/external/callback
```

### Authentik enrollment flow

Create an Authentik enrollment flow, for example:

```text
Name: Wizarr enrollment
Slug: wizarr-enrollment
Designation: Enrollment
```

A minimal stage order is:

1. Prompt stage  
   Collect the desired signup fields, such as username, email, name, and password.

2. User Write stage  
   Create the Authentik user. Optionally assign the user to a group used for Wizarr or your media services.

3. User Login stage  
   Log the newly created user into Authentik.

4. Redirect stage  
   Redirect back to Wizarr.

### Redirecting back to Wizarr

The redirect must include the original Wizarr `state` value. A static redirect to the callback URL is not enough.

Use an Authentik Expression Policy on the redirect stage to build the final callback URL from the query parameters Wizarr supplied:

```python
callback_url = request.http_request.GET.get("callback_url")
state = request.http_request.GET.get("state")

if not callback_url or not state:
    ak_message("Missing Wizarr callback_url or state")
    return False

allowed_callback = "https://wizarr.example.com/invitation/external/callback"
if callback_url != allowed_callback:
    ak_message("Invalid Wizarr callback URL")
    return False

context["flow_plan"].context["redirect_stage_target"] = f"{callback_url}?state={state}"

return True
```

Replace `https://wizarr.example.com` with your own Wizarr URL.

### Proxy protection

The callback route should be protected by Authentik forward auth or an Authentik proxy provider. Do not allow unauthenticated access to:

```text
/invitation/external/callback
```

The public invite entry points may remain unauthenticated, for example:

```text
/j/<invite-code>
/invitation/external/start/<invite-code>
```

Make sure your reverse proxy forwards the trusted Authentik header to Wizarr. For example, with Traefik forward auth:

```yaml
authResponseHeaders:
  - X-authentik-uid
  - X-authentik-username
  - X-authentik-email
  - X-authentik-groups
```

The header configured in `EXTERNAL_ENROLLMENT_AUTH_HEADER` must be present on the callback request. If it is missing, Wizarr will reject the callback and will not grant wizard access.
