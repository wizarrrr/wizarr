# External account enrollment

Relates to #1290.

Goal: allow an invitation to redirect users to an external identity provider enrollment flow, such as Authentik, and then return to Wizarr to continue the post-invite wizard.

Initial scope:

- Add an external enrollment mode for invitations.
- Redirect to an external enrollment URL instead of showing Wizarr's account creation form.
- Add a callback route that resumes the wizard after successful external authentication.