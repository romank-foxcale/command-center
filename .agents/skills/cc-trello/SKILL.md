---
name: cc-trello
description: Connect the Control Center to a Trello board and, only when the user asks, link cards to plans or features, show a card, post a comment (a verdict, a verify result, a summary) or move a card between lists, through ./cc trello. Use when the user mentions Trello, a card, or asks to post, comment, update or move something on the board.
---

# CC Trello

First read `../_shared/cc-cli.md` and follow it.

## On demand only

Trello is visible to the whole team, so nothing goes there unless the user asked for this specific update in this conversation. Never post or move as a side effect of another task, and never on a guess. `./cc trello comment` and `move` only preview without `--yes`.

For every comment or move:

1. Run the command **without** `--yes` and show the user the exact preview: the card, and the full comment text or the target list.
2. Wait for an explicit yes to that preview. A yes to an earlier preview does not cover a new one.
3. Only then run the same command with `--yes`, and show the result.

## Commands

| Request | Command |
|---|---|
| Is Trello set up? | `./cc trello status` |
| Which boards do I have? | `./cc trello boards` |
| Connect this CC to a board | `./cc trello connect --board <board url> [--active-list "In progress"] [--completed-list "Done"]` |
| Link a plan or a feature to a card | `./cc trello link --plan <id> <card url>` or `--feature <name> <card url>`; a new feature can link at creation: `./cc worktree create <feature> <repo>... --card <card url>` |
| Show the linked card | `./cc trello show --plan <id>` or `--feature <name>` |
| Comment | `./cc trello comment --plan <id>\|--feature <name> --text "<text>"` (or `--file <path>` for longer text), then `--yes` |
| Move | `./cc trello move --plan <id>\|--feature <name> active\|completed\|"<list name>"`, then `--yes` |

## Writing comments

- Write what a teammate needs: the outcome, the evidence (verify result, PR link, council verdict in two or three lines), and what is next. No internal reasoning, no transcript, no AI attribution.
- Match the language the card and team use; ask when unsure.
- Never include secrets, tokens, credentials, connection strings or personal data, even when they appear in logs.

## Setup

Credentials are the user's: they put `TRELLO_API_KEY` and `TRELLO_TOKEN` in `~/.config/cc/trello.env`, outside every repository. Never ask for the token in chat, never write or print it, and never put it in the catalog; `./cc check` rejects credential-like fields there. If `status` reports missing credentials, tell the user where to create the key and token (the Trello Power-Up admin page and its token link) and which file to put them in.
