---
name: cc-settings
description: Open the Control Center's settings panel (./cc settings) in a terminal - agents and their models, councils, repos (add by link, remove, main branch, kind, platforms, stack) and the Trello board - or, where no terminal can be opened, show and change the same settings in the chat with pick lists. Use when the user asks for the settings, wants to see or change a role's model, a council setting, the repo list or a repo's branch, platforms or stack, or types /cc-settings.
---

# CC settings

First read `../_shared/cc-cli.md` and follow it. Every change goes through `./cc`, in the panel and in the chat.

## 1. Open the panel

The settings are an interactive panel, not a chat. Open it where the user can use it:

| Where this session runs | How |
|---|---|
| Claude Code desktop app | Run the panel in a new Terminal panel tab titled `CC settings`, in the CC root: `.\cc settings` on Windows (PowerShell, via `cc.cmd`), `./cc settings` elsewhere. Link the tab for the user. |
| A terminal Claude Code or Codex session | Tell the user to run `./cc settings` (or `.\cc settings` on Windows) in another terminal; a session's own shell cannot host the panel. |

Then say in one line what the panel offers: arrows switch tabs, `e` edits the selected row, `a` adds a repo by pasting its link, `d` removes one, `q` quits. Do not also print the settings in the chat.

## 2. In the chat, when the panel cannot be opened

Or when the user asks for one change by name ("make the judge use sonnet"). Run `./cc settings show`, present it compactly, then offer every choice as a pick list: in Claude Code with the question tool; in Codex and other tools as a numbered list. Never ask the user to type a model or provider name.

| Setting | Choices | Command |
|---|---|---|
| A role's model | `./cc council models`: one group per logged-in provider | `./cc council set-role <role> --provider <p> --model <m>` |
| A council's approval pause | on, off | `./cc council set <council> --approval on\|off` |
| A council's retry limit | 0 to 5 | `./cc council set <council> --max-retries <n>` |
| Add a repo | the pasted link; project or reference | `./cc repo add <url> [--branch <b>] (--targets ... --stack ... \| --kind reference)` |
| Remove a repo | the catalog's repos | `./cc repo remove <id>` |
| A repo's main branch | the remote's branches | `./cc repo set-branch <id> <branch>` |
| A repo's link or kind | project, reference | `./cc repo set-remote <id> <url>`, `./cc repo set-kind <id> <kind>` |
| A repo's target platforms | windows, linux, macos | `./cc repo set-targets <id> <platform>...` |
| A repo's stack | the languages found in its code, plus other | `./cc repo set-stack <id> <language>...` |
| Trello board | `./cc trello boards`, then its lists | `./cc trello connect --board <id> --active-list <name> --completed-list <name>` |

- With more choices than the question tool allows, ask for the group first (provider, repo), then the item.
- Changing a verified repo's platforms resets it to adapted; turning a council's approval pause off lets the writer start without the user's decision; removing a repo drops it from this CC: confirm each before applying.
- After each change, show the command's output. A rejected change leaves the setting unchanged: show the reason.

## Related

- Repo details beyond settings (status, onboarding): `cc-repo`. Open PRs of the repos: `cc-prs`.
- Posting to or moving Trello cards is not a setting: `cc-trello`, on demand only.
- Run progress is not a setting: `cc-council` (`./cc council status <run>`).
