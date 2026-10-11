# Pre-Invite and Post-Invite Wizard Steps

Wizarr now supports two distinct categories of wizard steps: **Before Invite Acceptance** (pre-invite) and **After Invite Acceptance** (post-invite). This powerful feature allows you to guide users through important information before they even create their account, and then continue their onboarding after they've joined.

***

## Overview

### What Are Pre-Invite Steps?

Pre-invite steps are shown to users **before** they accept an invitation and create their account. These steps are perfect for:

- **Terms of service** or community guidelines
- **Server rules** and expectations
- **Important announcements** or notices
- **Prerequisites** users should know before joining
- **App download instructions** to prepare users

### What Are Post-Invite Steps?

Post-invite steps are shown to users **after** they've accepted the invitation and created their account. These steps are ideal for:

- **Welcome messages** and getting started guides
- **App setup instructions** specific to their account
- **Feature tours** and advanced tips
- **Request system integration** (Overseerr, Ombi)
- **Discord invites** and community links

***

## How It Works

### The Invitation Flow

```
User clicks invite link
    ↓
Pre-Invite Steps (if configured)
    ↓
Join Page (accept invitation)
    ↓
Account Creation
    ↓
Post-Invite Steps (if configured)
    ↓
Completion
```

### Automatic Routing

Wizarr automatically handles the flow:

1. **User clicks invitation link** → Invite code is stored in session
2. **Pre-invite steps exist?** → User is redirected to `/pre-wizard`
3. **No pre-invite steps?** → User goes directly to join page
4. **After accepting invitation** → User is redirected to `/post-wizard` (if steps exist)
5. **No post-invite steps?** → User goes directly to completion page

### Bypass Prevention

Users **cannot skip** pre-invite steps if they're configured. The system enforces completion through server-side validation, ensuring all users see important information before joining.

***

## Creating Pre-Invite and Post-Invite Steps

### Accessing the Wizard Admin

Navigate to **Settings** → **Wizard** in your Wizarr admin panel.

### Side-by-Side Layout

The wizard admin now displays steps in a **two-column layout**:

- **Left column**: Before Invite Acceptance (pre-invite steps)
- **Right column**: After Invite Acceptance (post-invite steps)

Steps are grouped by server type (Plex, Jellyfin, Emby, etc.) within each column.

### Creating a New Step

1. **Click "Create Step"** in the wizard settings
2. **Select the server type**: `plex`, `jellyfin`, `emby`, etc.
3. **Choose the category**:
   - **Before Invite Acceptance** - Shown before user accepts invitation
   - **After Invite Acceptance** - Shown after user creates account
4. **Write your content** using Markdown
5. **Set interaction requirements** (optional)
6. **Save the step**

### Editing Existing Steps

1. **Click the edit icon** on any step
2. **Change the category** if needed (dropdown field)
3. **Update content** as desired
4. **Save changes**

***

## Drag-and-Drop Management

### Reordering Steps

You can reorder steps within the same category by **dragging and dropping**:

1. **Click and hold** the drag handle (⋮⋮) on any step
2. **Drag** the step to its new position
3. **Release** to drop it in place
4. Changes are **saved automatically**

### Moving Between Categories

You can also **move steps between categories** using drag-and-drop:

1. **Drag a step** from one column to the other
2. **Drop it** in the target category
3. The step's category is **updated automatically**

### Restrictions

- Steps can only be moved **within the same server type**
- You cannot drag a Plex step into Jellyfin steps, for example
- Visual feedback indicates valid and invalid drop zones

***

## Use Cases and Examples

### Example 1: Terms of Service (Pre-Invite)

**Category**: Before Invite Acceptance

```markdown
# Terms of Service

Before joining our media server, please read and acknowledge our terms:

## Server Rules

1. **No sharing** - Keep your account credentials private
2. **Respect bandwidth** - Don't download excessively during peak hours
3. **Content requests** - Use Overseerr for new content requests
4. **Be respectful** - This is a community resource

By clicking "Next" and accepting this invitation, you agree to these terms.

[View Full Terms](https://example.com/terms){:target="_blank" .btn}
```

**Tip**: Enable "Require Interaction" to ensure users click the terms link before proceeding.

### Example 2: App Download (Pre-Invite)

**Category**: Before Invite Acceptance

```markdown
# Download the Plex App

To access our media library, you'll need the Plex app installed on your device.

**Choose your platform:**

[📱 iOS](https://apps.apple.com/app/plex/id383457673){:target="_blank" .btn}
[🤖 Android](https://play.google.com/store/apps/details?id=com.plexapp.android){:target="_blank" .btn}
[💻 Windows](https://www.plex.tv/media-server-downloads/){:target="_blank" .btn}
[🍎 macOS](https://www.plex.tv/media-server-downloads/){:target="_blank" .btn}

Click a download button above to continue.
```

**Tip**: Enable "Require Interaction" to ensure users download the app before joining.

### Example 3: Welcome Message (Post-Invite)

**Category**: After Invite Acceptance

```markdown
# Welcome to Our Media Server! 🎉

Congratulations! Your account has been created successfully.

## What's Next?

1. **Open the Plex app** you downloaded earlier
2. **Sign in** with your Plex account
3. **Look for our server** in your server list
4. **Start watching!**

## Need Help?

Join our Discord community for support and updates:

[Join Discord](https://discord.gg/example){:target="_blank" .btn}
```

### Example 4: Request System Integration (Post-Invite)

**Category**: After Invite Acceptance

```markdown
# Request New Content

Want to watch something that's not in our library? Use Overseerr to request it!

## How to Request Content

1. Visit our Overseerr instance
2. Sign in with your Plex account
3. Search for movies or TV shows
4. Click "Request" and we'll add it to the library

[Open Overseerr](https://overseerr.example.com){:target="_blank" .btn}
```

***

## Multi-Server Invitations

### How It Works

For invitations that cover multiple media servers, Wizarr automatically combines steps:

1. **Pre-invite steps** from all servers are shown in sequence
2. **User accepts invitation** and accounts are created
3. **Post-invite steps** from all servers are shown in sequence

### Server Indicators

The wizard clearly indicates which server each step belongs to, helping users understand the context.

***

## Wizard Bundles with Categories

### Mixed Category Bundles

Wizard bundles can now include steps from both categories:

1. **Create a bundle** in the wizard settings
2. **Add steps** from both pre-invite and post-invite categories
3. **Reorder as needed** - bundle order overrides category
4. **Assign to invitations**

### Bundle Behavior

When a bundle is assigned to an invitation:

- **Bundle steps are shown in bundle order** regardless of category
- **Category-based routing still applies** (pre-wizard → join → post-wizard)
- **Steps are filtered** based on the current phase

***

## Migration from Previous Versions

### Automatic Migration

When you upgrade to a version with pre/post-invite support:

1. **All existing wizard steps** are automatically assigned to "After Invite Acceptance" (post-invite)
2. **Existing invitation links** continue to work without changes
3. **Existing wizard bundles** function exactly as before
4. **No manual intervention** is required

### Gradual Adoption

You can adopt the new feature gradually:

1. **Start with post-invite steps** (existing behavior)
2. **Add pre-invite steps** as needed for specific server types
3. **Test the flow** with new invitations
4. **Refine and iterate** based on user feedback

### Backward Compatibility

- The old `/wizard` endpoint redirects to `/post-wizard` automatically
- Invitations without pre-invite steps skip directly to the join page
- All existing features (bundles, multi-server, interaction requirements) work with both categories

***

## Best Practices

### Pre-Invite Steps

- **Keep them brief** - Users haven't committed yet
- **Focus on essentials** - Terms, rules, prerequisites
- **Use interaction requirements** - Ensure users engage with important content
- **Avoid overwhelming** - Too many pre-invite steps may discourage users

### Post-Invite Steps

- **Welcome users warmly** - They've just joined!
- **Provide clear next steps** - How to access content
- **Include helpful resources** - Support links, Discord, request systems
- **End with encouragement** - Make users excited to use the service

### Step Organization

**Good Pre-Invite Flow:**
1. Welcome and introduction
2. Terms of service
3. App download instructions

**Good Post-Invite Flow:**
1. Welcome message
2. Getting started guide
3. Request system integration
4. Community links

***

## Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| Pre-invite steps not showing | Check that steps are assigned to "Before Invite Acceptance" category |
| Users skip pre-invite steps | This shouldn't be possible - check server logs for errors |
| Steps in wrong order | Verify position values and drag-and-drop to reorder |
| Category not saving | Ensure you're using the latest version with migration applied |

### Debug Tips

1. **Check the wizard admin** - Verify steps are in the correct column
2. **Test with a new invitation** - Use a fresh invitation link
3. **Clear browser cache** - Old JavaScript may cause issues
4. **Check server logs** - Look for wizard-related errors

***

## FAQ

| Question | Answer |
|----------|---------|
| Can I have only pre-invite steps? | Yes, post-invite steps are optional |
| Can I have only post-invite steps? | Yes, this is the default behavior |
| Do I need to update existing invitations? | No, they work automatically with the new system |
| Can I move steps between categories? | Yes, use drag-and-drop or edit the step |
| Do bundles support both categories? | Yes, bundles can include steps from both categories |
| What happens if I delete all pre-invite steps? | Users go directly to the join page |

***

That's it! 🎉

The pre-invite and post-invite wizard system gives you complete control over your user onboarding journey. Create compelling pre-invite experiences that set expectations, and welcoming post-invite flows that help users get started quickly.

Start by adding a few pre-invite steps to your most important server type, and watch your user onboarding become even more effective! ✨

