# Public access requests

Public access requests let visitors request an invitation without already having
an invite link. The feature is **disabled by default**. A request never creates a
media-server account. An administrator must approve it first, and the recipient
must then complete the existing Wizarr invitation flow.

## Enable requests

1. Add and verify your media server in Wizarr. Check its default library and
   download permissions: approved invitations use those defaults.
2. Configure email and the public URL with the environment variables below.
3. Open **Access requests** in the admin dashboard, enable **Allow public access
   requests**, and save.
4. Share `/signup` on your public Wizarr instance. With requests enabled, the
   public root page also redirects visitors to the form. Administrators still
   sign in through `/login`.

Visitors submit their name, email, and an optional message. Their password is
never collected or stored in the request. Duplicate email submissions receive
the same generic response and do not generate more notifications.

## Review requests

Open `/admin/signups`, select a verified media server, and choose **Approve and
email setup link** or **Reject request**. Approval creates one single-use
invitation that expires after seven days. The recipient chooses their own
username and password through the existing onboarding wizard.

Repeated approval cannot create additional invitations. If email delivery
fails, the approval and invitation remain saved; use **Resend setup email**
after fixing email configuration. Used or expired invitations cannot be resent.
Rejected requests create no invitation and cannot be approved afterward.

For Jellyfin and Seerr, enable new Jellyfin sign-in in Seerr. The approved user
can then sign in to Seerr with the Jellyfin account they created. Movie/show
request auto-approval is a separate Seerr permission.

## Email configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `SIGNUP_PUBLIC_URL` | Public Wizarr base URL used in email links | Empty |
| `SIGNUP_ADMIN_EMAIL` | Owner address for new-request notifications | Empty |
| `SIGNUP_SMTP_HOST` | SMTP server | Empty |
| `SIGNUP_SMTP_PORT` | SMTP port | `587` |
| `SIGNUP_SMTP_SSL` | Implicit TLS, typically port 465 | `false` |
| `SIGNUP_SMTP_FROM` | Sender address | Empty |
| `SIGNUP_SMTP_USERNAME` | SMTP login, if required | Empty |
| `SIGNUP_SMTP_PASSWORD` | SMTP password | Empty |

When implicit TLS is disabled, SMTP uses STARTTLS with certificate validation.
Keep credentials outside source control. Email links use the configured public
URL, not a visitor-supplied Host header. A notification failure does not lose
the request; it remains visible in the approval queue.

## Abuse prevention and privacy

Forms and all review actions validate CSRF tokens. Requests are opt-in, validated,
HTML-escaped, deduplicated by email, and bounded to 500 pending requests. The
database limits new addresses from the same source to five requests per hour,
including across multiple application workers. A honeypot rejects basic bots.
Source addresses are stored as a keyed hash, not in plaintext. If deploying
behind a proxy, configure trusted proxy headers only for your trusted proxy so
the request limits use the visitor's address. Request and approval pages are
marked `no-store` and `noindex`.

Reviewers see names, email addresses, and submitted messages. No public endpoint
lists requests, reveals approval state, or exposes invitation codes. The admin
queue is paginated. Take normal care with database backups because they contain
personal information and unused invitation codes.
