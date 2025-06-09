# AGENTS

This repository contains **Wizarr**, a Flask based invitation system for Plex, Jellyfin and Emby servers.

## Key Features
- Automatic invitations for Plex, Jellyfin, and Emby
- Secure, user-friendly invitation process
- Plug-and-play SSO support
- Multi-tiered invitation access
- Time-limited membership options
- Setup guides for media apps
- Request system integration (Overseerr, Ombi, etc.)
- Discord invite support
- Fully customisable with your own HTML snippets

## Development
1. Install dependencies with `uv sync --locked`.
2. Start the development server with `uv run flask run`.
3. Run tests using `uv run pytest`.

## Customising the Welcome Wizard
Markdown files inside `wizard_steps/plex/` or `wizard_steps/jellyfin/` define the onboarding slides. Filenames are shown alphabetically, so prefix them with `01_`, `02_` etc. Each file can have optional YAML front matter with `title` and `require` keys. The `require` field disables the *Next* button until a link or button is clicked. Preview your changes by refreshing the app and visiting `/wizard`.

## Single Sign‑On
Set the environment variable `DISABLE_BUILTIN_AUTH=True` to disable Wizarr's built-in login when using an external provider (Authelia, Authentik, ...). Ensure `/join`, `/j`, `/setup` and `/static` paths remain publicly accessible in your proxy configuration.

## Translations
Translations are managed through [Weblate](https://hosted.weblate.org/engage/wizarr/). You can test specific languages by setting the `FORCE_LANGUAGE` environment variable.

## License
Wizarr is distributed under the MIT License.
