# LDAP Authentication

Wizarr supports LDAP authentication for both administrators and regular users. This guide covers setup with LLDAP (Light LDAP), but the configuration applies to any LDAP server.

## Table of Contents

- [Overview](#overview)
- [LLDAP Setup](#lldap-setup)
- [Wizarr LDAP Configuration](#wizarr-ldap-configuration)
- [Admin Authentication](#admin-authentication)
- [User Invitations with LDAP](#user-invitations-with-ldap)
- [Group Management](#group-management)
- [Troubleshooting](#troubleshooting)

## Overview

LDAP authentication in Wizarr provides:

- **Admin Login via LDAP**: Administrators can log in using their LDAP credentials
- **Automatic User Creation**: Users created in LDAP when accepting invitations
- **Group-based Authorization**: Control admin access via LDAP group membership
- **Dual Authentication**: Admin accounts can use both local passwords and LDAP authentication

## LLDAP Setup

### Installation

LLDAP is a lightweight LDAP server perfect for home labs and small deployments.

**Docker Compose:**

```yaml
version: '3'
services:
  lldap:
    image: lldap/lldap:stable
    ports:
      - "3890:3890"  # LDAP port
      - "17170:17170"  # Web UI
    environment:
      - LLDAP_JWT_SECRET=CHANGE_ME_TO_RANDOM_STRING
      - LLDAP_LDAP_USER_PASS=CHANGE_ME_ADMIN_PASSWORD
      - LLDAP_LDAP_BASE_DN=dc=example,dc=com
    volumes:
      - lldap_data:/data

volumes:
  lldap_data:
```

### Initial Configuration

1. Access LLDAP web UI at `http://localhost:17170`
2. Log in with username `admin` and the password set in `LLDAP_LDAP_USER_PASS`
3. Create a service account for Wizarr:
   - Go to **Users** → **Create User**
   - Username: `wizarr-service`
   - Email: `wizarr@example.com`
   - Set a strong password
   - Click **Create**

4. **CRITICAL**: Add service account to password manager group:
   - Go to **Groups**
   - Click on **lldap_password_manager** group
   - Add `wizarr-service` user to this group
   - Click **Save**

   > **⚠️ REQUIRED FOR USER CREATION**: LLDAP requires the service account to be in the `lldap_password_manager` group to:
   > - Create new users
   > - Set user passwords
   >
   > Without this group membership, Wizarr cannot create LDAP users when invitations are accepted.

5. Create admin group (optional but recommended):
   - Go to **Groups** → **Create Group**
   - Name: `wizarr_admins`
   - Description: `Wizarr Administrator Access`
   - Click **Create**

### LLDAP Directory Structure

```
dc=example,dc=com
├── ou=people
│   ├── uid=admin
│   ├── uid=wizarr-service
│   └── uid=john (created by Wizarr)
└── ou=groups
    ├── cn=lldap_admin
    ├── cn=lldap_password_manager
    └── cn=wizarr_admins
```

## Wizarr LDAP Configuration

### Access LDAP Settings

1. Log in to Wizarr as admin
2. Go to **Settings** → **LDAP**

### Basic Configuration

| Setting | Value | Example |
|---------|-------|---------|
| **Enable LDAP** | ✓ Checked | - |
| **Server URL** | `ldap://hostname:port` | `ldap://lldap:3890` |
| **Use TLS** | ☐ Unchecked (for local) | ✓ for production |
| **Base DN** | Your LDAP base | `dc=example,dc=com` |

### Service Account

| Setting | Value |
|---------|-------|
| **Service Account DN** | `uid=wizarr-service,ou=people,dc=example,dc=com` |
| **Service Account Password** | Password you set for wizarr-service |

> **Test Connection** button will verify these settings

### User Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| **User Base DN** | `ou=people,dc=example,dc=com` | Where users are stored |
| **User Search Filter** | `(uid={username})` | LLDAP uses `uid` |
| **Username Attribute** | `uid` | LLDAP standard |
| **Email Attribute** | `mail` | LLDAP standard |
| **User Object Class** | `person` | LLDAP default |

### Group Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| **Group Base DN** | `ou=groups,dc=example,dc=com` | Where groups are stored (required for admin group check) |
| **Group Object Class** | `groupOfUniqueNames` | LLDAP default |
| **Group Member Attribute** | `uniqueMember` | LLDAP default |

> **⚠️ LLDAP Limitation**: LLDAP does not support automatic group assignment via LDAP protocol. Group membership must be managed manually through the LLDAP web UI or via its GraphQL API. Wizarr cannot automatically add users to groups during invitation acceptance.

### Admin Authentication

| Setting | Value |
|---------|-------|
| **Allow Admin LDAP Bind** | ✓ Checked |
| **Admin Group DN** | `cn=wizarr_admins,ou=groups,dc=example,dc=com` |

> Leave **Admin Group DN** empty to allow any LDAP user to be admin (not recommended)

### Save Configuration

Click **Save Settings** and use **Test Connection** to verify everything works.

## Admin Authentication

### How It Works

When an admin logs in with LDAP:

1. Wizarr searches for the username in LDAP
2. Attempts to bind (authenticate) with the provided password
3. Checks if user is in the Admin Group (if configured)
4. Creates/updates local admin account with LDAP DN stored in `external_id`

### Dual Authentication Support

Admin accounts support **both** authentication methods:

- **LDAP Authentication**: Uses LDAP credentials
- **Local Authentication**: Uses local password (if set)

This allows admins to:
- Log in with LDAP when available
- Fall back to local password if LDAP is down
- Use passkeys for 2FA with either method

### Login Flow

**Login Page:**
```
Authentication Method: [LDAP ▼]
Username: [admin]
Password: [••••••]
```

Select "LDAP" from the dropdown and use your LDAP credentials.

## User Invitations with LDAP

### Automatic User Creation

When LDAP is enabled, Wizarr automatically creates LDAP users when invitations are accepted.

### Creating an Invitation

1. Go to **Invitations** → **Create Invitation**
2. Select media servers
3. Expand **Advanced Options**
4. **LDAP Integration** section appears:
   - ✓ **Create LDAP User** (checked by default)

### Invitation Acceptance Flow

When a user accepts an invitation with LDAP enabled:

1. User fills in registration form (username, email, password)
2. **LDAP user created** in `ou=people,dc=example,dc=com`
3. Media server accounts created (Plex/Jellyfin/Emby)
4. User proceeds to setup wizard

> **⚠️ IMPORTANT - Password Management**: After creating LDAP users, you must manually add them to the `lldap_password_manager` group in LLDAP's web UI if you want them to be able to change their own passwords. Without this group membership, users cannot update their passwords.
>
> **To enable password changes for a user:**
> 1. Log in to LLDAP web UI
> 2. Go to **Groups** → **lldap_password_manager**
> 3. Add the user to this group
> 4. Click **Save**

### Example LDAP User

After invitation acceptance:

```
dn: uid=john,ou=people,dc=example,dc=com
objectClass: person
uid: john
mail: john@example.com
```

> **Note**: Users are not automatically added to any groups. You must manually add them to the `lldap_password_manager` group (and any other groups) via LLDAP's web UI.

## Group Management

### Creating LDAP Groups

In LLDAP web UI:

1. Go to **Groups** → **Create Group**
2. Name: `plex_users` (example)
3. Description: `Plex Media Server Users`
4. Click **Create**

### Syncing Groups to Wizarr

You need to sync groups from LDAP to Wizarr so you can select an admin group for authorization.

**To sync groups:**
1. Go to **Settings** → **LDAP**
2. Scroll to **User & Group Settings** section
3. Click **Sync Groups** button
4. Groups will be imported and available for admin group selection

> **Note**: LLDAP groups don't have a `description` attribute. Group descriptions set in LLDAP's web UI are stored in LLDAP's internal database but not exposed via LDAP protocol.

### Group-based Admin Authorization

Set **Admin Group DN** to restrict admin access:

```
cn=wizarr_admins,ou=groups,dc=example,dc=com
```

Only users in this group can log in as administrators.

## Troubleshooting

### Test Connection Fails

**Error**: "Cannot connect to LDAP server"

**Solutions**:
- Verify server URL and port
- Check firewall rules
- For Docker: ensure containers can communicate
- Try `ldapsearch` from Wizarr container:

```bash
docker exec wizarr ldapsearch -x -H ldap://lldap:3890 -b "dc=example,dc=com"
```

### Authentication Failed

**Error**: "Invalid LDAP credentials"

**Solutions**:
- Verify service account DN is correct
- Check service account password
- Ensure user exists in LDAP
- Check User Search Filter matches username

### Password Setting Fails

**Error**: "Failed to create LDAP user: invalid attribute type userPassword"

**Solution**: Add service account to `lldap_password_manager` group in LLDAP

**Error**: "User created but password not set"

**Solution**: Service account needs `lldap_password_manager` group membership

### Group Membership Not Working

**Error**: "User not in admin group"

**Check**:
1. User exists in LDAP
2. Group exists in LDAP
3. User is member of the group
4. Group Base DN is correct
5. Group Member Attribute is `uniqueMember` (for LLDAP)

### Testing LDAP Configuration

Use `ldapsearch` to verify configuration:

```bash
# Test service account bind
ldapsearch -x -H ldap://lldap:3890 \
  -D "uid=wizarr-service,ou=people,dc=example,dc=com" \
  -w "SERVICE_ACCOUNT_PASSWORD" \
  -b "dc=example,dc=com"

# Search for users
ldapsearch -x -H ldap://lldap:3890 \
  -D "uid=wizarr-service,ou=people,dc=example,dc=com" \
  -w "SERVICE_ACCOUNT_PASSWORD" \
  -b "ou=people,dc=example,dc=com" \
  "(uid=john)"

# Search for groups
ldapsearch -x -H ldap://lldap:3890 \
  -D "uid=wizarr-service,ou=people,dc=example,dc=com" \
  -w "SERVICE_ACCOUNT_PASSWORD" \
  -b "ou=groups,dc=example,dc=com" \
  "(objectClass=groupOfUniqueNames)"
```

### Migrating Existing Users

TODO

## See Also

- [Single Sign-On (SSO)](single-sign-on-sso.md)
- [Password & Passkey Recovery](password-passkey-recovery.md)
- [LLDAP GitHub Repository](https://github.com/lldap/lldap)
- [LLDAP Documentation](https://github.com/lldap/lldap/blob/main/docs/README.md)
