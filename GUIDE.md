# Control Center: setup and usage guide

A **Control Center (CC)** is a git repo that sits next to your project repos and teaches AI coding agents how the whole system fits together:

- **how to build, test and run things**: as Nix code, which fails loudly when something drifts;
- **why things are the way they are**: short, linked Markdown notes in `docs/`;
- **how to plan work**: two built-in agent skills that interview you before anything gets changed;
- **how to code and test with several models**: councils in which Claude and GPT each propose, an anonymous judge decides, you approve, and a writer implements until `./cc verify` passes.

Everyone creates **their own CC** and uses **their own AI tool and account**. The CC holds no credentials. You sign in to your tool as usual and choose any model your subscription includes. Councils call the `claude` and `codex` CLIs with your own logins; which model each council role uses is set in `catalog/agents/*.json` (see [Councils](#councils)).

| You use | Your subscription covers |
|---|---|
| Claude Code (desktop, CLI, VS Code extension) | Claude Pro / Max / Team / Enterprise |
| Cursor | Cursor plan (includes Claude, GPT and other models in Cursor's model picker) |
| Codex (app, CLI, IDE extension) | ChatGPT plan (Plus, Pro, Business, …) or an OpenAI API key |
| OpenCode | Whichever provider you connect. A Claude subscription can't be used here |

---

## 1. Install

### Windows (WSL2)

Everything runs inside **WSL2** (Linux on Windows), because Nix doesn't run on Windows natively.

1. Open **PowerShell as administrator** (right-click → *Run as administrator*).
2. Download and run the installer:

   ```powershell
   irm https://raw.githubusercontent.com/romank-foxcale/command-center/main/install/windows/install.ps1 -OutFile $env:TEMP\cc-install.ps1
   powershell -ExecutionPolicy Bypass -File $env:TEMP\cc-install.ps1 -Tools claude,codex,opencode
   ```

   `-Tools` is optional. It installs those command-line tools inside WSL, so leave out the ones you don't use.
3. If WSL wasn't installed yet, the script installs it and Ubuntu starts in the same window, asking for a Linux username (lowercase, no spaces) and password. The password stays invisible while you type. Type `exit` when you see the green prompt. If Windows asks for a reboot instead, reboot and run `wsl --install -d Ubuntu` once more. Then run the second command again (no admin needed this time).
4. The script then does the rest inside Ubuntu: base packages, systemd, Nix with flakes, the kit in `~/.cc-kit`, and the `cc-kit` command. `sudo` asks for your **Linux** password.

To get a Linux terminal afterwards, run `wsl` in PowerShell (or open **Ubuntu** from the Start menu).

> **Keep your projects inside Linux** (`~/Projects`), never under `/mnt/c/...`. Nix and git are very slow on the Windows drive, and some things break there.

### macOS

In Terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/romank-foxcale/command-center/main/install/install.sh | bash -s -- --tools claude,codex,opencode
```

It installs the Apple command line tools if missing (re-run after the dialog finishes), then Nix with flakes, the kit in `~/.cc-kit`, and `cc-kit`.

### Check it worked

Open a **new** terminal (Ubuntu on Windows) and run:

```bash
cc-kit doctor
```

Everything under *Required* must say `ok`. Everything under *Optional* only matters for the tools you use.

---

## 2. Create your Control Center

```bash
cc-kit new my-project
```

This creates the standard layout:

```
~/Projects/
├── my-project_CC/        ← your Control Center (its own git repo)
├── repos/                ← base clones of your project repos (shared by all CCs)
└── worktrees/<feature>/  ← one folder per task, with a git worktree per changed repo
```

`cc-kit list` shows your CCs. Don't rename or move these folders: the scripts rely on the layout.

---

## 3. Open it in your AI tool

Pick your tool. Every tool reads the same instructions (`AGENTS.md`) and the same two skills.

### Claude Code desktop

- **Windows:** in the Code tab, open the environment picker and choose **WSL → Ubuntu**. Then open the folder `\\wsl.localhost\Ubuntu\home\<your-linux-user>\Projects\my-project_CC`. The whole session (Claude, its tools, git) runs inside Ubuntu.
  In WSL sessions the integrated terminal, file browser pane, connectors and `@` file suggestions aren't available yet. Use an Ubuntu terminal next to it for `./cc` commands.
- **macOS:** open `~/Projects/my-project_CC`.

### VS Code + Claude Code extension, or VS Code + Codex extension

- **Windows:** from an Ubuntu terminal run `cc-kit open my-project code`. VS Code opens *connected to WSL* (bottom-left corner says `WSL: Ubuntu`).
  Install the Claude Code and/or Codex extension **in that WSL window**; VS Code offers "Install in WSL: Ubuntu". Sign in with your own account.
  If Codex still runs on the Windows side, enable the setting `chatgpt.runCodexInWindowsSubsystemForLinux`.
- **macOS:** `cc-kit open my-project code`, or open the folder normally.

### Cursor

- **Windows:** from an Ubuntu terminal run `cc-kit open my-project cursor`. The Cursor window must show `WSL: Ubuntu` in the bottom-left corner. If the new Agent window doesn't connect to WSL, use the classic editor window (`cursor --classic`).
- **macOS:** open the folder normally.
- Pick any model from Cursor's model picker; it's billed to your Cursor plan.

### Codex app or CLI

- **App on Windows:** Settings → switch the agent to **WSL**, restart the app, then open `~/Projects/my-project_CC`.
- **CLI (Windows in Ubuntu, or macOS):** `cd ~/Projects/my-project_CC && codex`. The first time, run `codex login` and sign in with your ChatGPT account.

### OpenCode

`cd ~/Projects/my-project_CC && opencode` (on Windows, in Ubuntu). Connect a provider with `/connect`.

---

## 4. First session: set the CC up

Type this into your tool's chat:

> Set up this Control Center. Use the grill-cc-bootstrap skill.

The agent interviews you about your repos, how they depend on each other and how each is built. It then connects them one at a time:

1. registers the repo (`./cc repo add`),
2. writes a Nix build adapter and a check for it,
3. proves it builds and passes (`./cc check`).

Expect several rounds of questions. The agent asks only what it can't work out from the code and CI. When it's done, `control-center.json` has status `ready`. Commit the CC and push it to your own remote.

You can also call the skill directly: `/grill-cc-bootstrap` in Claude Code and Cursor, `$grill-cc-bootstrap` in Codex.

---

## 5. Everyday work

Not sure which skill fits? Ask "what can the CC do?" or type `/cc-help`: it lists the skills by purpose and explains the one you pick.

To plan a bigger task:

> Plan this with the grill-task-planning skill: <what you want to achieve>

The agent turns it into an agreed plan with work packages and checks, saved in `plans/active/`. It won't write code until you accept the plan. Then:

```bash
./cc worktree create my-feature repo1 repo2   # task folders under ~/Projects/worktrees/my-feature/
./cc feature my-feature verify                # build + test your changed code on every target platform
./cc worktree status my-feature
./cc worktree remove my-feature               # refuses if anything is uncommitted or unpushed
```

**From Windows without opening Ubuntu:** the `cc.cmd` launcher in the CC folder runs the same commands inside WSL for you, with the same output and exit code. In PowerShell type `.\cc check`, in cmd `cc check`, in Git Bash `./cc.cmd check`. It works whether the CC lives on `C:` or inside Ubuntu (`\\wsl.localhost\Ubuntu\home\...`). With several Linux distributions installed, set `CC_WSL_DISTRO` to the one with Nix.

Other commands, run from the CC folder:

| Command | What it does |
|---|---|
| `./cc verify` | Run every check plus each repo's target platform gates (e.g. the real Windows build) |
| `./cc verify --quality` | Also run each repo's mutation gate: do the tests catch injected bugs? Warns for repos without one |
| `./cc check` | Run every pure check: builds, tests, knowledge notes, skill sync |
| `./cc doctor` | Check Nix, Docker and the `claude`/`codex` logins |
| `./cc show` | List everything that can be built, checked or run |
| `./cc build <name>` / `./cc run <name>` | Build or run one thing |
| `./cc repo list` | Connected repos and their status |
| `./cc plan list` | Plans in progress, archived, completed |
| `./cc validate` | Check the `docs/` notes only (works without Nix) |
| `./cc agents sync` | After editing a skill in `.agents/skills/`, copy it to `.claude/skills/` |

### Councils

A council makes Claude and GPT work on the same task. It needs both CLIs installed and logged in inside Ubuntu (`claude auth login`, `codex login`); `./cc doctor` shows their state.

> Run a coding council on my-feature: <what you want>

1. Both models study the worktree and propose an approach, without editing.
2. A judge compares them as "Proposal A" and "Proposal B", without knowing who wrote which, and picks one or a hybrid.
3. The run stops and shows you the verdict and who wrote what. Approve it, pick the other proposal, add a note, or reject it.
4. The writer implements it in the worktree, reusing existing code first; `./cc feature my-feature verify` must pass, with up to 2 retries.
5. A security reviewer reads the diff. You review `changes.diff` and commit it yourself.

A testing council works the same way: both models write tests, the judge merges them, and a failing new test is reported as a suspected bug.

A debug council finds and fixes a bug: `./cc council run debug --feature my-feature --task "<exact symptom>"`. The CC first runs verify and hands its output to both models; each diagnoses the root cause with evidence; the judge picks the best-evidenced one; after your approval the writer adds a reproduction test that must fail, and only then fixes the cause. After three failed fixes it stops and asks you to rethink the design.

Which model plays which role is one field per file in `catalog/agents/` (for example `"model": "opus"` in `writer.json`); `catalog/councils/` sets the roles, the approval pause and the retry limit. Ask your agent to change them, or edit the JSON. Run files are kept in `~/Projects/worktrees/<feature>/.cc-runs/`.

---

## 6. Migrating an existing CC

If you already have a control center, repo catalog or docs in another format:

```bash
mkdir -p ~/Projects/old-thing_CC && cd ~/Projects/old-thing_CC   # or the folder that already has it
git clone ~/.cc-kit cc_template
```

Open that folder in your tool and say:

> Migrate this to the Control Center format. Read `cc_template/BOOTSTRAP.md`, treat `cc_template` as read-only, and use the grill-cc-bootstrap skill.

The agent inventories what exists without changing anything first, then moves it over one piece at a time. When it's done, delete `cc_template/`.

---

## 7. Docker (only for container workflows)

- **Windows:** install Docker Desktop, then Settings → Resources → **WSL Integration** → enable **Ubuntu**. Don't also install Docker inside Ubuntu.
- **macOS:** Docker Desktop or OrbStack works for *running* containers. *Building* Linux images with Nix on a Mac needs a Linux builder (for example nix-darwin's `nix.linux-builder.enable = true;`) or CI. Container checks are skipped on macOS until you set one up.

---

## 8. Updating the kit

```bash
cc-kit update
```

This updates `~/.cc-kit` only. Existing CCs are separate repos and never change behind your back. To pull a kit improvement into a CC, ask your agent to compare the CC with `~/.cc-kit` and bring over the change.

---

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| `Python was not found` / Microsoft Store opens | You're in PowerShell or Git Bash, not Ubuntu. Run commands in Ubuntu. |
| `cc-kit: command not found` | Open a new terminal, or run `source ~/.bashrc`. |
| `$'\r': command not found` | The repo was cloned on the Windows side with Windows line endings. Clone it again from inside Ubuntu. |
| `Nix is not installed` right after installing | Open a new terminal. |
| `Nix flakes are disabled` | Re-run `~/.cc-kit/install/install.sh`. |
| Everything is very slow | Your CC is under `/mnt/c`. Move it to `~/Projects`. |
| Nix can't see a new file | Nix only sees files git knows about: `git add <file>`. |
| Installer stops after "enabling systemd" | Run `wsl --shutdown` in PowerShell, then run the installer again. |
| The tool doesn't list the skills | Run `./cc agents check` in the CC and make sure you opened the CC folder itself, not `~/Projects`. |
