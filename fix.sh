#!/bin/bash
#
# Fix a Git repository that pulls from a personal GitHub repo but pushes using
# the wrong GitHub SSH identity (for example: srujan-lbg-dev).
#
# Run this INSIDE the affected repository.
#
# Examples:
#   ./fix-personal-github-repo.sh
#   ./fix-personal-github-repo.sh git@github.com:Srujan-DiagonalMatrix/comm.git
#   PERSONAL_KEY="$HOME/.ssh/id_ed25519_github_personal" ./fix-personal-github-repo.sh
#
# This script changes only the CURRENT repository's local Git configuration.
# It does not change global Git settings and does not modify company repos.

set -euo pipefail

EXPECTED_GITHUB_USER="${EXPECTED_GITHUB_USER:-Srujan-DiagonalMatrix}"
TARGET_REMOTE="${1:-}"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

info() {
  echo "==> $*"
}

# -----------------------------------------------------------------------------
# 1. Make sure we are inside a Git repository
# -----------------------------------------------------------------------------
git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || fail "Run this script from inside the affected Git repository."

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

info "Repository: $REPO_ROOT"

# -----------------------------------------------------------------------------
# 2. Determine the personal GitHub remote
# -----------------------------------------------------------------------------
if [[ -z "$TARGET_REMOTE" ]]; then
  TARGET_REMOTE="$(git remote get-url origin 2>/dev/null || true)"
fi

[[ -n "$TARGET_REMOTE" ]] || fail "No origin remote found. Pass the personal repo URL as argument 1."

# Normalize common GitHub URL formats to SSH.
case "$TARGET_REMOTE" in
  git@github.com:*)
    ;;
  https://github.com/*)
    TARGET_REMOTE="git@github.com:${TARGET_REMOTE#https://github.com/}"
    ;;
  ssh://git@github.com/*)
    TARGET_REMOTE="git@github.com:${TARGET_REMOTE#ssh://git@github.com/}"
    ;;
  *)
    fail "Unsupported remote format: $TARGET_REMOTE"
    ;;
esac

# Remove trailing slash, ensure .git for consistency.
TARGET_REMOTE="${TARGET_REMOTE%/}"
[[ "$TARGET_REMOTE" == *.git ]] || TARGET_REMOTE="${TARGET_REMOTE}.git"

info "Personal GitHub remote: $TARGET_REMOTE"

# -----------------------------------------------------------------------------
# 3. Find the SSH key that authenticates as the PERSONAL GitHub account
# -----------------------------------------------------------------------------
find_personal_key() {
  local candidates=()

  if [[ -n "${PERSONAL_KEY:-}" ]]; then
    candidates+=("$PERSONAL_KEY")
  fi

  candidates+=(
    "$HOME/.ssh/id_ed25519_github_personal"
    "$HOME/.ssh/id_rsa_github_personal"
    "$HOME/.ssh/id_ed25519_personal"
    "$HOME/.ssh/id_rsa_personal"
    "$HOME/.ssh/id_ed25519"
    "$HOME/.ssh/id_rsa"
  )

  # Add any other private-looking files from ~/.ssh as last-resort candidates.
  if [[ -d "$HOME/.ssh" ]]; then
    while IFS= read -r f; do
      [[ "$f" == *.pub ]] && continue
      [[ "$(basename "$f")" == "config" ]] && continue
      [[ "$(basename "$f")" == "known_hosts"* ]] && continue
      candidates+=("$f")
    done < <(find "$HOME/.ssh" -maxdepth 1 -type f 2>/dev/null | sort)
  fi

  local seen="|"
  local key output
  for key in "${candidates[@]}"; do
    [[ -f "$key" ]] || continue
    [[ "$seen" == *"|$key|"* ]] && continue
    seen+="$key|"

    output="$(ssh -T \
      -o BatchMode=yes \
      -o ConnectTimeout=8 \
      -o ConnectionAttempts=1 \
      -o IdentitiesOnly=yes \
      -i "$key" \
      git@github.com 2>&1 || true)"

    if printf '%s\n' "$output" | grep -Fqi "Hi ${EXPECTED_GITHUB_USER}!"; then
      printf '%s\n' "$key"
      return 0
    fi
  done

  return 1
}

info "Finding the SSH key for GitHub account '${EXPECTED_GITHUB_USER}'..."
PERSONAL_KEY_RESOLVED="$(find_personal_key || true)"

if [[ -z "$PERSONAL_KEY_RESOLVED" ]]; then
  cat >&2 <<EOF2

Could not automatically find an SSH key that authenticates as:
  ${EXPECTED_GITHUB_USER}

Your current problem is almost certainly SSH identity selection.

If you already know the personal key, rerun like this:

  PERSONAL_KEY="$HOME/.ssh/id_ed25519_github_personal" $0 "$TARGET_REMOTE"

To see which GitHub account your default SSH key is using:

  ssh -T git@github.com

The expected response should start with:
  Hi ${EXPECTED_GITHUB_USER}!
EOF2
  exit 2
fi

info "Personal SSH key found: $PERSONAL_KEY_RESOLVED"

# -----------------------------------------------------------------------------
# 4. Fix BOTH fetch and push URLs to the same personal repository
# -----------------------------------------------------------------------------
info "Making origin fetch and push use the SAME personal repository..."

git config --local remote.origin.url "$TARGET_REMOTE"
git config --local --unset-all remote.origin.pushurl 2>/dev/null || true
git config --local remote.origin.pushurl "$TARGET_REMOTE"

# -----------------------------------------------------------------------------
# 5. Force this repository ONLY to use the personal SSH key
# -----------------------------------------------------------------------------
# This is the key fix. It prevents ssh-agent / company keys from being selected
# for this repository while leaving other repositories untouched.
SSH_COMMAND="ssh -i '$PERSONAL_KEY_RESOLVED' -o IdentitiesOnly=yes"
git config --local core.sshCommand "$SSH_COMMAND"

# -----------------------------------------------------------------------------
# 6. Clear any branch-specific pushRemote that might redirect pushes elsewhere
# -----------------------------------------------------------------------------
CURRENT_BRANCH="$(git branch --show-current 2>/dev/null || true)"
if [[ -n "$CURRENT_BRANCH" ]]; then
  git config --local --unset-all "branch.${CURRENT_BRANCH}.pushRemote" 2>/dev/null || true
  git config --local "branch.${CURRENT_BRANCH}.remote" origin
fi

# Remove repository-local default pushRemote if someone previously configured it.
git config --local --unset-all remote.pushDefault 2>/dev/null || true

# Use normal/simple push behavior.
git config --local push.default simple

# -----------------------------------------------------------------------------
# 7. Verify identity and repository access
# -----------------------------------------------------------------------------
info "Verifying GitHub identity with the forced personal key..."
AUTH_OUTPUT="$(ssh -T \
  -o BatchMode=yes \
  -o ConnectTimeout=8 \
  -o IdentitiesOnly=yes \
  -i "$PERSONAL_KEY_RESOLVED" \
  git@github.com 2>&1 || true)"
echo "$AUTH_OUTPUT"

printf '%s\n' "$AUTH_OUTPUT" | grep -Fqi "Hi ${EXPECTED_GITHUB_USER}!" \
  || fail "The selected key did not authenticate as ${EXPECTED_GITHUB_USER}."

info "Testing repository read access..."
git ls-remote origin HEAD >/dev/null

# -----------------------------------------------------------------------------
# 8. Show final configuration
# -----------------------------------------------------------------------------
echo
echo "============================================================"
echo "FIX COMPLETE"
echo "============================================================"
echo "Repository : $REPO_ROOT"
echo "Branch     : ${CURRENT_BRANCH:-<detached HEAD>}"
echo "SSH user   : $EXPECTED_GITHUB_USER"
echo "SSH key    : $PERSONAL_KEY_RESOLVED"
echo
echo "Remotes:"
git remote -v

echo
echo "Repo-specific SSH command:"
git config --local --get core.sshCommand

echo
echo "You can now use normal commands:"
echo "  git pull"
echo "  git push"
echo
echo "Both pull and push will use:"
echo "  $TARGET_REMOTE"
echo
echo "Company GitHub repositories are NOT changed because this fix is local"
echo "to this repository only."
