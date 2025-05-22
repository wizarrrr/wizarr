
# Customising the Welcome Wizard 🪄
Give your new users a quick tour that *you* control — all through simple Markdown
files. No coding required.

---

## 1 · Where do I put my pages?

```
wizard\_steps/
│
├─ plex/        ← steps that appear when your server type is Plex
│   ├─ 01\_download.md
│   ├─ 02\_intro.md
│   └─ 99\_tips.md
│
└─ jellyfin/    ← steps for Jellyfin
├─ 01\_download.md
└─ 99\_tips.md

````

* **Pick the folder** (`plex` or `jellyfin`).  
* **Create a new `.md` file** for every step.  
* The files are shown in *alphabetical* order, so a handy trick is to start
  filenames with numbers: `01_`, `02_`, `03_` …

---

### 2 · Writing a step (now with **title** and **require**)

Each Markdown file may start with an **optional** YAML front-matter block:

```yaml
---
title: Download the Plex app      # overrides the first heading if you prefer
require: true                     # user must click a button or link on this
---
```

* **`title`**
  – If present, this value is used as the card heading.
  – If omitted, the wizard falls back to the first `# Heading` it finds.

* **`require`**
  – When set to `true`, the *Next* button stays disabled until the user clicks
  **any** link or button inside that card.
  – Perfect for slides that say “Please download the app before continuing”.

After the front-matter you write normal Markdown as before:

```markdown
We recommend installing the **native Plex app** for the best picture quality.

[Download for my device](https://www.plex.tv/media-server-downloads/#plex-app){:target="_blank" .btn}
```

Everything else about ordering, previewing, dark-mode support, etc. stays
exactly the same.


```markdown
# Download the Plex app

You’ll get the best experience by installing the **native Plex app** on the
device you’re using right now.

[Download for my device](https://www.plex.tv/media-server-downloads/#plex-app){:target="_blank" .btn}
````

* **Headings** (`#`, `##`, `###`, …) automatically get nice sizes & colours.
* **Links / buttons** – add Tailwind classes with the `{:.btn}` notation
  and `{:target="_blank"}` if you want it to open in a new tab.
* **Images** – just use normal Markdown:
  `![Alt text](<link>){.mx-auto .max-w-xs}`
  (classes after the brace are optional).

> **Tip:** dark-mode is handled automatically; you don’t have to style anything.

---

## 3 · Previewing your changes

1. Save the file in *wizard\_steps/…*
2. Restart the app (or refresh if you’re running with live-reload).
3. Navigate to /wizard ➜ the wizard shows your new page in sequence.

Nothing to compile, nothing to rebuild — it “just works”.

---

## 4 · Removing or re-ordering pages

* **Re-order** — rename the files so they sort the way you want
  (`01_hello.md`, `02_getting-started.md`, …).
* **Remove** — simply delete the file.
  The wizard skips anything that isn’t there.

---

## 5 · FAQ

| Question                             | Answer                                                                                                                                                            |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| *Can I disable the wizard entirely?* | Delete every file in `wizard_steps/plex/` and `wizard_steps/jellyfin/`.                                                                                           |
| *Do I need to know Tailwind?*        | No — plain Markdown is enough. Add classes only if you want fancy buttons or centred images.                                                                      |
| *Will my slides be translated?*      | Wrap any text that should be translatable in `{{ _("Like this") }}`. If you don’t know what that means, you can ignore it — English text will still display fine. |

---

That’s it!
Add a Markdown file, hit save, and your users get a personalised, theme-aware
welcome tour. Enjoy ✨

