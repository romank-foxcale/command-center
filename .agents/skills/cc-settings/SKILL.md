---
name: cc-settings
description: Show and change the Control Center's settings inside the chat - which provider and model each agent role uses (picked from the models of the logged-in subscriptions), each council's approval pause and retry limit, and each repo's target platforms and stack. Use when the user asks for the settings, wants to see or change a role's model, a council setting, or a repo's platforms or stack, or types /cc-settings.
---

# CC settings

First read `../_shared/cc-cli.md` and follow it. This is the in-chat version of `./cc settings`, the terminal panel; both change things only through `./cc`.

## 1. Show

Run `./cc settings show` and present it compactly: the status line, then agents (role → provider model), councils (approval, retries, roles) and repos (status, targets, stack). Then ask what to change.

## 2. Change, with choices instead of typing

Offer every choice as a pick list: in Claude Code with the question tool (clickable options); in Codex and other tools as a numbered list the user answers with a number. Never ask the user to type a model or provider name.

| Setting | Choices | Command |
|---|---|---|
| A role's model | `./cc council models`: one group per logged-in provider, the role's current model marked | `./cc council set-role <role> --provider <p> --model <m>` |
| A council's approval pause | on, off | `./cc council set <council> --approval on\|off` |
| A council's retry limit | 0 to 5 | `./cc council set <council> --max-retries <n>` |
| A repo's target platforms | windows, linux, macos (several allowed) | `./cc repo set-targets <repo> <platform>...` |
| A repo's stack | the languages found in the repo's code, plus other | `./cc repo set-stack <repo> <language>...` |

- When a choice list would exceed the question tool's option limit, ask for the provider first, then the model.
- Choosing a model sets its provider; never mix a model with another provider.
- Changing a verified repo's platforms resets it to adapted: say so before applying, and point to `./cc verify <repo>`.
- Turning a council's approval pause off lets the writer start without the user's decision: confirm explicitly before applying.
- After each change, show the command's output. A rejected change leaves the setting unchanged: show the reason.

## Related

- Run progress is not a setting: "how is the run going?" belongs to `cc-council` (`./cc council status <run>`).
- In a terminal, `./cc settings` opens the same settings as a panel.
