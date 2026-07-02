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
