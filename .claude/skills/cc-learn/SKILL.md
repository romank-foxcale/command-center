---
name: cc-learn
description: Turn one non-obvious thing learned in this session - a root cause, a workaround, a constraint, a decision - into an atomic Control Center note (hack, debt, decision or fact) with evidence and relations, linked from its index, after the user confirms the draft. Use when the user asks to remember, record or capture what was learned, after the debug skill offers it, or when a lasting workaround was just put in place.
---

# CC learn

One run records **one** durable piece of knowledge, so the next agent does not rediscover it. The rules are in `docs/rules/knowledge-layout.md`; read it first.

## 1. Pick the one thing

Name the single fact in one sentence. It qualifies only if it is non-obvious, durable and verified:

- **Record:** a root cause that took real investigation; a workaround for a tool or library quirk; a constraint the code does not show; a decision with its reasons.
- **Refuse, and say why:** typos and simple syntax fixes; one-off outages; anything readable from the code in a minute; a hypothesis that was not confirmed; build or test steps (they belong in Nix, never in a note).

If the session taught several things, list them and ask which one; record the others in later runs.

## 2. Look for an existing note

Search `docs/` for the key terms and read what matches. If a note already states it, offer to update that note (refresh `verified_at`, add evidence, correct it) instead of creating a duplicate. If the new fact replaces an old one, the old note becomes `status: superseded` and links to its successor.

## 3. Choose the kind

| Kind | Folder | Template | Index |
| --- | --- | --- | --- |
| Hack: a temporary workaround | `docs/hacks/` | `templates/note.md` | `docs/hacks/index.md` |
| Debt: a known problem left in place | `docs/debt/` | `templates/note.md` | `docs/debt/index.md` |
| Decision with options and reasons | `docs/decisions/NNNN-<name>.md`, next free number | `templates/decision.md` | `docs/index.md` |
| Fact about one project | `docs/projects/` | `templates/note.md` | `docs/projects/index.md` |

A hack must link to a decision or a debt note and state `remove_when`. When neither exists, the debt note is drafted in the same run: that is the only case of two notes at once.

## 4. Draft

Fill the template completely, in English, whatever language the conversation uses:

- `id`: `<kind>.<short-name>`, unique; `status`: `active` for hacks, debt and facts, `accepted` for a decision only when the user made it, otherwise `draft`; `verified_at`: today.
- `evidence`: paths from the CC root that exist, or permanent URLs (a commit or file permalink) for code in project repos. Never a `../worktrees/` path: worktrees are deleted.
- `relations`: the index and the notes it depends on.
- Body: the why, the limits of applicability and the consequences. Do not restate code or transcribe the session.

## 5. Confirm, then write

Show the user the full draft, its path and the index line, and wait for an explicit yes. Then write the note, add the index line, and run `./cc validate`. Fix any error it reports in the note; never weaken the validator.

## Never

- Write a note without the user's yes, or store conversations, reasoning, secrets or personal data.
- Commit, push or open a PR: the user commits.
- Record an executable process as steps: point to the Nix contract instead, or create one.
