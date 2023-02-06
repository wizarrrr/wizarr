# Single-Sign-On (SSO)

#### **Wizarr supports SSO via disabling its inbuilt authentication**

To Disable Wizarr's inbuilt authentication in order to put it behind a Proxy Provider (Authelia, Authentik...), set the following variable:

`DISABLE_BUILTIN_AUTH=True`

#### Whitelist Public Paths (important!)

In order to make the invitation process available for non signed in users, make sure you whitelist the following paths:

```
- /join
- /j/*
- /setup*
- /static/*
```
