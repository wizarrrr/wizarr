# Customise The Wizard

Give your new users a personalized onboarding experience with Wizarr's powerful wizard system. Create custom welcome flows that guide users through setting up their media apps, understanding your server, and more.

***

## Overview

Wizarr's wizard system supports multiple approaches for creating and managing onboarding steps:

1. **Database-backed steps** (recommended) - Create and manage steps through the admin interface
2. **Wizard bundles** - Custom sequences of steps for specific invitation types
3. **Multi-server wizards** - Automatic flows for invitations covering multiple servers
4. **Legacy file-based steps** - Markdown files as fallback (still supported)

***

## 1 · Managing Wizard Steps Through the Admin Interface

### Accessing the Wizard Admin

Navigate to **Settings** → **Wizard** in your Wizarr admin panel to manage wizard steps and bundles.

### Creating Default Steps

Default steps are server-type specific and will be shown to all users invited to that server type.

1. **Click "Default Steps"** in the wizard settings
2. **Click "Create Step"** to add a new step
3. **Select the server type**: `plex`, `jellyfin`, `emby`, `audiobookshelf`, `romm`, or `komga`
4. **Write your content** using Markdown
5. **Set conditional display** (optional) using the `requires` field

### Step Fields

- **Server Type**: Which media server this step applies to
- **Title**: Optional override for the step heading
- **Markdown**: The main content of your step
- **Requires**: Comma-separated setting keys that must be truthy for the step to display

### Conditional Step Display

Use the `requires` field to show steps only when certain conditions are met:

```
discord_url,enable_notifications
```

This step will only show if both `discord_url` and `enable_notifications` settings have truthy values.

***

## 2 · Wizard Bundles (Custom Flows)

Wizard bundles allow you to create completely custom onboarding sequences that can be assigned to specific invitations.

### Creating a Bundle

1. **Click "Custom Bundles"** in the wizard settings
2. **Click "Create Bundle"** 
3. **Name your bundle** (e.g., "VIP Onboarding", "Family Setup")
4. **Add a description** (optional)
5. **Create and assign steps** to your bundle

### Bundle Steps

Bundle steps are different from default steps:
- **No server type** - they're not tied to a specific media server
- **Flexible ordering** - drag and drop to reorder steps within the bundle
- **Custom content** - can include any markdown content you want

### Assigning Bundles to Invitations

When creating an invitation, you can:
1. **Select a wizard bundle** from the dropdown
2. **Leave it as "Automatic"** to use the default server-type steps

***

## 3 · Multi-Server Wizard Flows

For invitations that cover multiple media servers, Wizarr automatically creates a combined wizard flow.

### How It Works

1. **User accepts invitation** for multiple servers
2. **Wizard automatically combines** steps from each server type
3. **Steps are shown in order** based on server type (alphabetical)
4. **User progresses through** all relevant steps

### Server Types Supported

- **Plex** - Media streaming server
- **Jellyfin** - Open-source media server
- **Emby** - Media server platform
- **Audiobookshelf** - Audiobook and podcast server
- **Romm** - ROM and game library manager
- **Komga** - Comic and manga library server

***

## 4 · Writing Effective Wizard Steps

### Markdown Syntax

Wizarr supports standard Markdown with some enhancements:

```markdown
# Step Title

Welcome to our **media server**! Here's what you need to know:

## Getting Started

1. Download the app using the button below
2. Sign in with your username and password
3. Start enjoying your content!

[Download App](https://example.com/download){:target="_blank" .btn}
```

### Styling Options

- **Links as buttons**: Add `{.btn}` to make links look like buttons
- **External links**: Add `{:target="_blank"}` to open in new tab
- **Images**: Use standard Markdown syntax with optional classes
- **Tailwind classes**: Add `{.class-name}` for custom styling

### Interactive Elements

Make your steps interactive by requiring user engagement:

```markdown
---
title: Download Required
require: true
---

# Download the App

Please download our app before continuing.

[Download Now](https://example.com/download){:target="_blank" .btn}
```

When `require: true` is set, the Next button stays disabled until the user clicks a link or button.

***

## 5 · Legacy File-Based Steps (Fallback)

While the database-backed approach is recommended, Wizarr still supports file-based steps as a fallback.

### File Structure

```
wizard_steps/
├── plex/
│   ├── 01_download.md
│   ├── 02_setup.md
│   └── 99_tips.md
├── jellyfin/
│   ├── 01_download.md
│   └── 02_about.md
├── emby/
│   ├── 01_download.md
│   └── 02_about.md
├── audiobookshelf/
│   └── 01_intro.md
├── romm/
│   └── 01_intro.md
└── komga/
    ├── 01_intro.md
    ├── 02_access.md
    ├── 03_features.md
    └── 04_tips.md
```

### File-Based Front Matter

```yaml
---
title: Download the App
require: true
---

# Your content here
```

### When Files Are Used

- **No database steps exist** for the server type
- **Database is unavailable** (during migrations, etc.)
- **Fallback behavior** ensures the wizard always works

***

## 6 · Access Control

### Wizard Access Control

By default, wizard access is restricted to:
- **Authenticated users** (logged-in admins)
- **Users with valid invitation codes** (stored in session)

### Disabling Access Control

Set the `wizard_acl_enabled` setting to `false` to allow unrestricted access to the wizard.

***

## 7 · Previewing and Testing

### Preview Options

1. **Click "Preview"** button when editing steps
2. **Visit `/wizard`** while logged in to test the full flow
3. **Use invitation links** to test the user experience

### Testing Multi-Server Flows

1. **Create an invitation** for multiple servers
2. **Use the invitation link** to test the combined flow
3. **Verify step order** and content display

***

## 8 · Advanced Features

### Step Ordering

- **Database steps**: Automatically ordered by position
- **File-based steps**: Ordered alphabetically (use `01_`, `02_` prefixes)
- **Bundle steps**: Drag and drop to reorder

### Dynamic Content

Steps can reference server settings and configuration:

```markdown
Welcome to **{{ server_name }}**!

Your server is available at: {{ server_url }}
```

### Conditional Logic

Use the `requires` field to show steps conditionally:

```markdown
# Discord Integration

Join our Discord community for support and updates!

[Join Discord]({{ discord_url }}){:target="_blank" .btn}
```

Only shows if `discord_url` is set in the `requires` field.

***

## 9 · Best Practices

### Content Guidelines

- **Keep steps concise** - users want to get started quickly
- **Use clear calls-to-action** - make buttons and links obvious
- **Test on mobile** - many users will access on phones
- **Include screenshots** - visual aids help understanding

### Step Organization

- **Start with essentials** - app download, account setup
- **End with optional content** - advanced features, tips
- **Use logical progression** - each step builds on the previous
- **Consider user journey** - think about what they need when

### Bundle Strategy

- **Create specific bundles** for different user types
- **VIP users** might get extended onboarding
- **Family members** might need simpler instructions
- **Power users** might want advanced configuration steps

***

## 10 · Migration from File-Based Steps

If you're upgrading from an older version with file-based steps:

1. **Database steps take precedence** - they'll be used if they exist
2. **File-based steps remain** as fallback
3. **Import existing files** through the admin interface
4. **Gradually migrate** to database-backed approach
5. **Test thoroughly** before removing file-based steps

***

## 11 · Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| Steps not showing | Check server type matches invitation |
| Wrong step order | Verify position values in database |
| Missing steps | Check `requires` field conditions |
| Bundle not working | Verify bundle assignment on invitation |

### Debug Tips

1. **Check admin logs** for wizard-related errors
2. **Verify database connectivity** for step loading
3. **Test with different server types** to isolate issues
4. **Use browser dev tools** to inspect step loading

***

## 12 · FAQ

| Question | Answer |
|----------|---------|
| Can I disable the wizard entirely? | Yes, don't create any steps and remove existing ones |
| Do I need to know HTML/CSS? | No, Markdown is sufficient for most use cases |
| Can I use custom JavaScript? | Not directly, but you can use interactive Markdown elements |
| How do I backup my wizard steps? | Export through the admin interface or backup your database |
| Can I preview changes before publishing? | Yes, use the preview button in the step editor |

***

That's it! 🎉

Wizarr's wizard system gives you complete control over your user onboarding experience. Whether you use simple default steps or create elaborate custom bundles, your users will have a smooth, guided introduction to your media server.

Start with the admin interface, create your first step, and watch your users get set up faster than ever before! ✨
