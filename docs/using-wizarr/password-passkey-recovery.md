# Password and Passkey Recovery

This guide helps administrators recover access to their Wizarr instance when locked out due to forgotten passwords or lost passkeys.

## Recovery Tool Overview

The recovery tool is a command-line utility designed to help administrators regain access when locked out. It provides emergency recovery options for common authentication issues.

### Key Features

* **Password Reset**: Reset passwords for admin accounts
* **Passkey Management**: Remove all passkeys for specific admin accounts
* **Emergency Admin**: Create emergency admin accounts
* **Account Listing**: View all admin accounts and their passkey status
* **Container-Friendly**: Designed to work seamlessly in Docker containers

## When to Use the Recovery Tool

Use the recovery tool in these situations:

* **Forgotten Password**: You cannot remember your admin password
* **Lost Passkey**: Your passkey device is lost or broken
* **2FA Lockout**: You're locked out due to passkey 2FA requirements
* **Complete Lockout**: All admin accounts are inaccessible

## Running the Recovery Tool

### Docker Container

For Docker installations:

```bash
# Find your container name
docker ps

# Run it directly
docker exec -it <container_name> uv run recovery_tool.py
```

## Recovery Options

The recovery tool provides five main options:

### 1. List All Admin Accounts

View all administrators and their current status:

* Username and ID
* Number of registered passkeys
* Account creation date
* Legacy admin status

### 2. Reset Admin Password

Change the password for any admin account:

1. Select the admin account from the list
2. Enter a new password (minimum 6 characters)
3. Confirm the password
4. The password is immediately updated

### 3. Remove All Passkeys

Delete all passkeys for a specific admin account:

1. Select the admin account
2. Confirm the operation (this cannot be undone)
3. All passkeys are removed
4. 2FA requirement is disabled for that account

### 4. Create Emergency Admin

Create a new admin account with password authentication:

1. Enter a username (must be unique)
2. Set a password (minimum 6 characters)
3. Confirm the password
4. New admin account is created immediately

### 5. Exit

Close the recovery tool safely.

## Common Recovery Scenarios

### Scenario 1: Forgotten Admin Password

**Problem**: You remember your username but forgot your password.

**Solution**:
1. Run the recovery tool
2. Select option 2 (Reset admin password)
3. Choose your admin account
4. Enter a new password
5. Log in with the new password

### Scenario 2: Lost Passkey Device

**Problem**: Your passkey device is lost, broken, or unavailable.

**Solution**:
1. Run the recovery tool
2. Select option 3 (Remove all passkeys for admin)
3. Choose your admin account
4. Confirm the removal
5. Log in with username/password (2FA disabled)

### Scenario 3: Complete Lockout

**Problem**: All admin accounts are inaccessible.

**Solution**:
1. Run the recovery tool
2. Select option 4 (Create emergency admin account)
3. Create a new admin account
4. Log in with the emergency account
5. Manage other accounts through the web interface
6. Delete the emergency account when no longer needed

### Scenario 4: 2FA Lockout

**Problem**: You're locked out due to passkey 2FA requirements.

**Solution**:
1. Run the recovery tool
2. Select option 3 (Remove all passkeys for admin)
3. Choose your admin account
4. Confirm passkey removal
5. Log in with username/password only

## Security Considerations

{% hint style="warning" %}
**Important Security Notes**

* Only run this tool when you have direct access to the server/container
* The tool requires database access and should only be used by system administrators
* Anyone with server access can use this tool to gain admin privileges
{% endhint %}

### After Recovery

Once you regain access, consider these security steps:

1. **Update Passwords**: Change passwords for all admin accounts
2. **Re-register Passkeys**: Set up new passkeys for 2FA
3. **Review Admin Access**: Audit who has admin privileges
4. **Delete Emergency Accounts**: Remove temporary accounts when no longer needed
5. **Secure Server Access**: Ensure only authorized personnel can access the server

## System Requirements

The recovery tool requires:

* Access to the server or container running Wizarr
* Read/write access to the database
* Proper Flask environment configuration
* Python execution privileges

## Environment Configuration

The tool automatically uses your existing Wizarr configuration. Ensure these environment variables are set if needed:

* `DATABASE_URL` - Database connection string
* `FLASK_ENV` - Flask environment (development/production)
* `SECRET_KEY` - Flask secret key

## Troubleshooting

### Common Issues

**Import Error**
* Ensure you're running the tool from the Wizarr root directory
* Check that all dependencies are installed

**Database Connection Error**
* Verify the database is accessible
* Check that the Flask environment is properly configured

**Permission Error**
* Ensure you have write access to the database
* Check file permissions on the database file

### Tool Output

The recovery tool provides clear feedback:

* ✅ Success messages for completed operations
* ❌ Error messages for failed operations
* ⚠️ Warning messages for destructive operations
* ℹ️ Information messages for status updates

## Best Practices

1. **Regular Backups**: Keep database backups before making changes
2. **Test Access**: Verify you can log in after making changes
3. **Document Changes**: Keep records of recovery actions taken
4. **Secure Storage**: Store recovery procedures in a secure location
5. **Regular Reviews**: Periodically review admin account access

## Support

If you encounter issues with the recovery tool:

1. Check the troubleshooting section above
2. Verify database connectivity
3. Ensure proper permissions
4. Review Flask application logs for additional details
5. Contact support through the official channels

{% hint style="info" %}
**Remember**: This tool is for emergency recovery only. Regular admin management should be done through the web interface.
{% endhint %}