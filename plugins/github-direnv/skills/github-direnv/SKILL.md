---
name: github-direnv
description: Set up direnv-based folder-scoped GitHub authentication so `gh` CLI and `git push/pull` automatically use a specific GitHub account when working in that folder. Use this skill when the user wants to scope a particular GitHub account (e.g., personal vs work) to a directory, asks to auto-switch `gh auth` per folder, hits "Repository not found" errors on push because the wrong gh account is active, has multiple `gh auth` accounts and wants them isolated by directory, or wants to stop running `gh auth switch --user X` manually. Also use when the user mentions `.envrc`, direnv, `GH_TOKEN`, or per-folder GitHub credentials. Prefer this over global `gh auth switch` whenever the user's intent is folder-scoped, even if they don't say "direnv" explicitly.
---

# github-direnv

Configure folder-scoped GitHub authentication using direnv. When the user `cd`s into the configured directory, `GH_TOKEN` is exported from a specific `gh`-stored account's token. `gh` CLI and `git push/pull` (which uses gh's credential helper) then operate as that account — automatically, without changing the global `gh auth` active account or affecting other terminals/IDEs.

## Why this approach

`gh auth` keeps an *active account* as global state. If the user has multiple accounts and uses `gh auth switch` to change it for one folder, every other terminal/IDE session sees that change too. The result: `git push` fails with "Repository not found" when the active account doesn't have access to the target repo.

direnv solves this by exporting environment variables only inside a directory. `gh` respects `GH_TOKEN` over its keyring's active account, so setting `GH_TOKEN` per-directory cleanly scopes the auth — no global mutation, no cross-talk between terminals.

The token isn't hardcoded into `.envrc` — it's fetched at load time via `gh auth token --user <account>`, which reads from the OS keyring. So the file is safe to commit, and token rotations are picked up on the next direnv load.

## Workflow

Run these phases in order. Skip a phase if its check already passes.

### 1. Verify direnv is installed

Run `command -v direnv`. If missing:
- macOS: `brew install direnv`
- Debian/Ubuntu: `sudo apt install direnv`
- Other: point the user to https://direnv.net/docs/installation.html

If install requires sudo or interactive consent, ask before running.

### 2. Verify the shell hook exists

The hook is what makes direnv auto-load `.envrc` on `cd`. Detect the user's shell from `$SHELL` (or `echo $0` if unclear).

For zsh, check `~/.zshrc` for `direnv hook zsh`:
```bash
grep -q 'direnv hook zsh' ~/.zshrc || printf '\n# direnv\neval "$(direnv hook zsh)"\n' >> ~/.zshrc
```

For bash, do the same against `~/.bashrc` with `direnv hook bash`.

After adding, tell the user the hook only activates in **new shells**. They should `source ~/.zshrc` (or open a new terminal). The current session can still use `direnv exec . <cmd>` as a workaround.

### 3. Identify the target gh account

If the user named one ("skarl86 계정으로", "work account"), use it.

Otherwise, list available accounts:
```bash
gh auth status 2>&1 | grep -E 'Logged in to.* account' | awk '{print $NF}'
```

If only one account exists, confirm with the user before assuming. If multiple, ask which.

Verify the token is retrievable: `gh auth token --user <account>` must print a non-empty token. If it errors, the user needs to `gh auth login --user <account>` first.

### 4. Write `.envrc`

Create `.envrc` in the target directory (default: cwd; confirm if uncertain). Substitute `<account>` with the chosen GitHub username:

```bash
# Auto-switch GitHub auth to <account> when in this directory.
# Used by gh CLI and git (via gh credential helper).
# Loaded by direnv (https://direnv.net) — install via `brew install direnv`.

if command -v gh >/dev/null 2>&1; then
  TOKEN=$(gh auth token --user <account> 2>/dev/null)
  if [ -n "$TOKEN" ]; then
    export GH_TOKEN="$TOKEN"
  else
    log_error "<account> not logged in to gh. Run: gh auth login --user <account>"
  fi
fi
```

The `command -v gh` guard means the file is harmless on machines without `gh` installed (clones to other machines won't break). The `log_error` prints a clear remediation when the account is missing.

### 5. Allow and verify

```bash
direnv allow .
```

Then verify the env loads correctly without relying on the not-yet-active hook:

```bash
direnv exec . sh -c 'echo "GH_TOKEN length: ${#GH_TOKEN}"; gh api user --jq .login'
```

The output should print a non-zero token length and the target account's login.

### 6. Optional: scope git author identity too

`.envrc` only changes auth. Commits will still use the user's *global* `git config user.name/user.email`. If the user wants commits in this folder to be authored as the scoped account too:

```bash
ID=$(gh api user --jq .id)
LOGIN=$(gh api user --jq .login)
git config user.name "$LOGIN"
git config user.email "${ID}+${LOGIN}@users.noreply.github.com"
```

Run with the scoped env active (use `direnv exec .` if the hook isn't reloaded yet). This sets *local* git config, leaving global identity untouched.

Only do this step if the user asks or it's clearly implied — don't silently overwrite their git author identity.

## Common pitfalls

- **Hook not active yet.** After adding the hook to `.zshrc`/`.bashrc`, the *current* shell still doesn't have it. The fix: `source ~/.zshrc` or new terminal. If they need to push *right now* before reloading, suggest `direnv exec . git push`.
- **Tool ignores `GH_TOKEN`.** Almost everything respects it (`gh`, `git` via gh credential helper, GitHub Actions runners). But VSCode's GitHub integration sometimes uses its own auth. The `.envrc` won't fix that.
- **Token rotation.** Tokens stored by `gh auth login` rotate transparently — `gh auth token --user X` always returns the current one. So `.envrc` doesn't need updating.
- **Multiple accounts in one folder.** Out of scope. `.envrc` exports a single `GH_TOKEN`; it can't multiplex by remote URL. Use submodules or split repos if you really need this.
- **CI/server contexts.** This is for interactive dev. CI should use `secrets.GH_TOKEN` (or equivalent) injected by the runner.

## Example session

```
User: "이 폴더에서는 항상 skarl86 계정으로 push 되게 해줘"

Claude:
  → command -v direnv          ✓ installed
  → grep direnv ~/.zshrc       ✓ hook present
  → gh auth status             accounts: tide-namgee, skarl86, Dev-Expertise-TS
  → gh auth token --user skarl86  ✓ 40-char token retrieved
  → write .envrc with skarl86
  → direnv allow .
  → direnv exec . gh api user --jq .login  → "skarl86" ✓

  Reply: "Done. .envrc committed-safe (token fetched at load time, not stored).
         To activate in this terminal, run: source ~/.zshrc
         New terminals get it automatically."
```
