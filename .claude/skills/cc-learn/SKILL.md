---
name: cc-learn
description: Record one non-obvious, durable thing learned - a root cause, workaround, constraint or decision - as an atomic CC note in docs/, after the user confirms the draft. Use when the user asks to remember or record something, or a lasting workaround was just put in place.
---

# CC learn

One run records **one** durable piece of knowledge, so the next agent does not rediscover it. The rules are in `docs/kit/rules/knowledge-layout.md`; read it first.

## 1. Pick the one thing

Name the single fact in one sentence. It qualifies only if it is non-obvious, durable and verified:

- **Record:** a root cause that took real investigation; a workaround for a tool or library quirk; a constraint the code does not show; a decision with its reasons.
- **Refuse, and say why:** typos and simple syntax fixes; one-off outages; anything readable from the code in a minute; a hypothesis that was not confirmed; build or test steps (they belong in Nix, never in a note).

If the session taught several things, list them and ask which one; record the others in later runs.

## 2. Look for an existing note

Search `docs/` for the key terms and read what matches. If a note already states it, offer to update that note (refresh `verified_at`, add evidence, correct it) instead of creating a duplicate. If the new fact replaces an old one, the old note becomes `status: superseded` and links to its successor. A note that `./cc validate` warns about (evidence changed after `verified_at`) is refreshed only after reading the change: confirm it still holds, then bump `verified_at`, or correct it.

## 3. Choose the kind

| Kind | Folder | Template | Index |
| --- | --- | --- | --- |
| Hack: a temporary workaround | `docs/hacks/` | `templates/note.md` | `docs/hacks/index.md` |
| Debt: a known problem left in place | `docs/debt/` | `templates/note.md` | `docs/debt/index.md` |
| Decision with options and reasons | `docs/decisions/NNNN-<name>.md`, next free number from 0001 | `templates/decision.md` | `docs/decisions/index.md` |
| Fact about one project | `docs/projects/` | `templates/note.md` | `docs/projects/index.md` |
| Recurring shortcoming reviewers keep raising | `docs/lessons/` | `templates/lesson.md` | `docs/lessons/index.md` |

Everything here is this CC's own knowledge. Never write into `docs/kit/`: it belongs to the kit and is replaced on a kit update. A decision that changes kit behaviour for this CC names the kit decision it overrides in its text and `relations`.

A hack must link to a decision or a debt note and state `remove_when`. When neither exists, the debt note is drafted in the same run: that is the only case of two notes at once.

## 4. Draft

Fill the template completely, in English, whatever language the conversation uses:

- `id`: `<kind>.<short-name>`, unique; `status`: `active` for hacks, debt and facts, `accepted` for a decision only when the user made it, otherwise `draft`; `verified_at`: today.
- `evidence`: paths from the CC root that exist, or permanent URLs (a commit or file permalink) for code in project repos. Never a `worktrees/` path: worktrees are deleted.
- `relations`: the index and the notes it depends on.
- Body: the why, the limits of applicability and the consequences. Do not restate code or transcribe the session.

## 5. Confirm, then write

Show the user the full draft, its path and the index line, and wait for an explicit yes. Then write the note, add the index line, and run `./cc validate`. Fix any error it reports in the note; never weaken the validator.

## Never

- Write a note without the user's yes, or store conversations, reasoning, secrets or personal data.
- Commit, push or open a PR: the user commits.
- Record an executable process as steps: point to the Nix contract instead, or create one.
