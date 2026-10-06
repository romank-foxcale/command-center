# Control Center Kit

A ready-to-install Control Center template that works on **Windows (via WSL2) and macOS**, and with **Claude Code, Cursor, Codex and OpenCode**.

A Control Center (CC) is a git repo next to your project repos that tells AI agents how the system is built (as Nix code) and why (as linked notes). It also has agent skills that interview you before setting things up or planning work.

**Quick start:**

- Windows: in PowerShell as administrator, run `install/windows/install.ps1`
- macOS: `curl -fsSL https://raw.githubusercontent.com/romank-foxcale/command-center/main/install/install.sh | bash`
- Then: `cc-kit new my-project` and open it in your AI tool

**Full instructions: [GUIDE.md](GUIDE.md).**

What the kit includes:

| Addition | Where |
|---|---|
| Windows installer (WSL2 + Ubuntu, then hands off) | `install/windows/install.ps1` |
| Linux/WSL/macOS installer (Nix with flakes, systemd, kit, optional CLIs) | `install/install.sh` |
| `cc-kit` command: `new`, `list`, `open`, `doctor`, `update` | `install/cc-kit` |
| Skills for every tool: canonical in `.agents/skills` (Codex, Cursor, OpenCode), synced copy in `.claude/skills` (Claude Code), checked by `./cc check` | `scripts/agent-configs.py`, `./cc agents` |
| `CLAUDE.md` importing `AGENTS.md`, safe read-only permissions for Claude Code | `CLAUDE.md`, `.claude/settings.json` |
| LF line endings enforced for Windows clones (CRLF only for `.ps1` and `.cmd`) | `.gitattributes` |
| `./cc settings` panel with a mascot (agents and models, councils, repos, status line), the same in chat via the `cc-settings` skill, and `./cc council status` for live run progress | `scripts/settings/`, `.agents/skills/cc-settings/`, `./cc council set-role`, `./cc council set` |
| `./cc open <feature>`: starts Claude Code or Codex in the CC with the feature's worktrees, so the CC's skills and rules apply; a session started inside a worktree is told to restart | `scripts/worktrees.py` |
| `cc-help` skill: lists the skills by purpose and explains the one you pick | `.agents/skills/cc-help/` |
| `cc.cmd` launcher: run `.\cc check` from PowerShell or cmd; it forwards to `./cc` in WSL | `cc.cmd` |
| All instructions, skills, notes and templates in English | everywhere |
| `bootstrap install` keeps empty `catalog/` folders tracked so the Nix bootstrap check can see them | `scripts/materialize-template.py` |
| Per-repo target platforms with a gate each, including a real Windows host gate | `./cc verify`, `ccLib.mkWindowsHostGate` |
| Per-repo `stack` (languages) and optional `quality.mutation` gates with each stack's own tool; a missing gate warns | `./cc verify --quality`, `docs/rules/quality-gates.md` |
| Coding, testing and debug councils: Claude and GPT propose or diagnose, an anonymous judge decides, a writer implements (debug: failing reproduction test first, enforced) | `./cc council`, `catalog/agents`, `catalog/councils` |
| `lean-code` skill: the least code that works, adapted from [Ponytail](https://github.com/dietrichgebert/ponytail) (MIT) | `.agents/skills/lean-code/` |
| `debug` and `tdd` skills: root cause before fixes, test first and honest tests, adapted from [Superpowers](https://github.com/obra/superpowers) (MIT) | `.agents/skills/debug/`, `.agents/skills/tdd/` |

## Tools and sources it builds on

**Adapted skills.** These skills are rewritten for the CC, not copied. Each keeps the upstream license next to it and an Origin section naming the exact upstream commit and what was changed.

| Source | License | Used for | What we took |
|---|---|---|---|
| [Ponytail](https://github.com/dietrichgebert/ponytail) by DietrichGebert | MIT | `lean-code` | The "laziest senior dev" ladder: read the problem fully, then stop at the first rung that holds (need it at all, already in the codebase, standard library, native platform feature, installed dependency, one line, minimum new code); root-cause bug fixes; no unrequested abstractions. Dropped: modes, intensity levels, commands. |
| [Superpowers](https://github.com/obra/superpowers) by Jesse Vincent | MIT | `debug`, `tdd` | Systematic debugging (no fix without a root cause, four phases, stop after three failed fixes, root-cause tracing, defense in depth, condition-based waiting) and test-driven development with its rules for honest tests (name the break, hand-derived expectations, no assertions on mocks, the mutation check). Changed: reproduction and verification through `./cc` on every target platform, tests-after allowed when each test is shown to fail. |

**Tools the kit runs.** The CC orchestrates these; it does not vendor them.

| Tool | Role in the CC |
|---|---|
| [Nix](https://nixos.org) with flakes, [nixpkgs](https://github.com/NixOS/nixpkgs) | Every build, test, check and app; pinned inputs; `./cc check`, `./cc verify` |
| Git | Repository catalog, feature worktrees, input overrides |
| Python 3 | The `./cc` scripts: catalog, worktrees, plans, validation, councils |
| WSL2 and PowerShell | Windows host gates (`ccLib.mkWindowsHostGate`) run the real Windows toolchain from WSL |
| [Claude Code](https://github.com/anthropics/claude-code) CLI (`claude`) | Interactive work, and the Claude roles in councils, under the user's own subscription |
| [Codex](https://github.com/openai/codex) CLI (`codex`) | Interactive work, and the GPT roles in councils, under the user's own ChatGPT login |
| Cursor, OpenCode | Supported editors and agents; they read the same `.agents/skills` |
| Docker or Podman (optional) | Container end-to-end workflows |

Each project repository brings its own test tools through its Nix adapter; the CC prescribes none of them.

---

# How a Control Center works

The template is a temporary seed for creating or migrating an agent-facing Control Center. The final CC lives in its own folder; the template clone is deleted after acceptance.

A Control Center stores two kinds of knowledge:

- **how to carry out a process**: Nix `packages`, `checks`, `apps` and, where needed, NixOS modules;
- **why the system is built this way**: atomic linked Markdown notes in `docs/`.

Step-by-step build, test and deploy commands are never duplicated in Markdown. If a process changes, an executable declaration must break.

## Creating a CC

The easiest way is `cc-kit new <name>` (see [GUIDE.md](GUIDE.md)). Without the kit installed, the manual way is:

```bash
mkdir project1_CC
cd project1_CC
git clone <template-url> cc_template
opencode   # or claude, codex, cursor .
```

First prompt:

> Create a Control Center here. Read `cc_template/BOOTSTRAP.md`, treat `cc_template` as a read-only source and start grilling. If there is already a CC of another format here, migrate it without losing meaning.

AI tools do not discover project skills inside a child Git repository, so the reference to `BOOTSTRAP.md` in the first prompt is required. After materialization the skill is available from the root of the target CC.

After `./cc bootstrap validate` and `./cc check` pass, delete `cc_template/` and commit the final CC.

## Working with a ready CC

```bash
./cc doctor
./cc show
./cc check
./cc build <package>
./cc run <app>
./cc repo list
./cc worktree status <feature>
./cc feature <feature> check
./cc plan list
```

Requires Nix with flakes. Docker/Podman is only needed for container workflows. On macOS, Linux images need a Linux builder or CI.

## Where to look

- [AGENTS.md](AGENTS.md): the mandatory protocol for agents.
- [BOOTSTRAP.md](BOOTSTRAP.md): creating and migrating a CC.
- [Knowledge map](docs/index.md): the entry point into the Obsidian-compatible `docs/`.
- [Executable processes](docs/rules/executable-processes.md): what counts as the source of truth.
- [Connecting projects](docs/rules/project-adapters.md): the contract for a sibling repository.
- `nix/projects/`: build adapters for individual projects.
- `nix/workflows/`: cross-project pipelines.
- `examples/cpp-docker-e2e/`: two C++ artifacts → HTTP service image → E2E.

## Repository onboarding and feature worktrees

```bash
./cc repo add repo1 --remote <git-url> --role service --clone
./cc worktree create feature1 repo1
./cc feature feature1 check
./cc worktree status feature1
./cc worktree remove feature1
```

`repo add` creates a catalog descriptor; the build contract is added next, as a flake input and `nix/projects/<repo>.nix`. `feature` turns the worktree manifest into Nix `--override-input` arguments.

## Grilling and plans

- `grill-cc-bootstrap`: creating/migrating a CC.
- `grill-task-planning`: preparing an agent-ready plan.
- The shared grilling invariants live in a non-invocable shared core.

```bash
./cc plan create feature1 --title "Change observable behavior"
./cc plan accept feature1
./cc plan complete feature1 --evidence "Acceptance checks passed"
```

A plan exists in exactly one state: `plans/active/`, `plans/archived/` or `plans/completed/`. The alternative transition for cancelled work is `./cc plan archive feature1 --reason "..."`.

The template deliberately contains no UI, no secrets and no production permissions.
