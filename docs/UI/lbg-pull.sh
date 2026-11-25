#!/usr/bin/env bash
<<<<<<< HEAD
# Usage: bash lbg-pull.sh [LBG_BRANCH] [NEW_PERSONAL_BRANCH]
set -euo pipefail

PERSONAL_URL='git@github.com:Srujan-DiagonalMatrix/rove.git'
COMPANY_URL='git@github-company:lbg-cloud-platform/tactical-innovation-f2b97b.git'
SOURCE_BRANCH="${1:-}"
if [ -z "$SOURCE_BRANCH" ]; then
  read -r -p 'LBG feature branch: ' SOURCE_BRANCH
fi
TARGET_BRANCH="${2:-feature/lbg-import-$(date +%Y%m%d-%H%M%S)}"
git check-ref-format --branch "$SOURCE_BRANCH" >/dev/null
git check-ref-format --branch "$TARGET_BRANCH" >/dev/null
case "$TARGET_BRANCH" in feature/*) ;; *) echo 'Destination must begin with feature/.' >&2; exit 1 ;; esac
REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

# Use dedicated remotes so existing origin/company settings remain intact.
for remote in lbg-pull-personal lbg-pull-company; do
  if [ "$remote" = lbg-pull-personal ]; then url="$PERSONAL_URL"; else url="$COMPANY_URL"; fi
  if git remote get-url "$remote" >/dev/null 2>&1; then
    git remote set-url "$remote" "$url"
  else
    git remote add "$remote" "$url"
  fi
done

git fetch --no-tags lbg-pull-personal refs/heads/main
PERSONAL_COMMIT=$(git rev-parse FETCH_HEAD)
git fetch --no-tags lbg-pull-company "refs/heads/$SOURCE_BRANCH"
SOURCE_COMMIT=$(git rev-parse FETCH_HEAD)
if git show-ref --verify --quiet "refs/heads/$TARGET_BRANCH"; then
  echo "Local branch already exists: $TARGET_BRANCH" >&2; exit 1
fi
if [ -n "$(git ls-remote --heads lbg-pull-personal "refs/heads/$TARGET_BRANCH")" ]; then
  echo "Personal remote branch already exists: $TARGET_BRANCH" >&2; exit 1
fi

# An isolated worktree preserves your current branch and uncommitted files.
WORKTREE_PARENT=$(mktemp -d)
WORKTREE="$WORKTREE_PARENT/worktree"
cleanup() {
  git -C "$REPO_ROOT" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
  rmdir "$WORKTREE_PARENT" 2>/dev/null || true
}
trap cleanup EXIT
git worktree add -b "$TARGET_BRANCH" "$WORKTREE" "$PERSONAL_COMMIT"
cd "$WORKTREE"
git read-tree --reset -u "$SOURCE_COMMIT"

# Retain personal GitHub automation rather than copying bank workflows.
rm -rf -- .github
if git cat-file -e "$PERSONAL_COMMIT:.github" 2>/dev/null; then
  git restore --source="$PERSONAL_COMMIT" --staged --worktree -- .github
fi

# Match the bank-local exclusions used by lbg-push.sh.
rm -f -- Dockerfile.backup Dockerfile.backup.bak Dockerfile.bak \
  Dockerfile.before-ca-fix Dockerfile.web.bak Dockerfile.web.backup.*.bak \
  server/Dockerfile.backup.*.bak server/Dockerfile.bak \
  server/Dockerfile.bank-backup company-ca.pem docker-compose.corporate.yml

git add -A
if ! git diff --cached --quiet; then
  git commit -m "Import LBG branch $SOURCE_BRANCH ($SOURCE_COMMIT)"
fi
# Empty expected remote ref: create only, never replace an existing branch.
git push --force-with-lease="refs/heads/$TARGET_BRANCH:" lbg-pull-personal \
  "HEAD:refs/heads/$TARGET_BRANCH"
printf '\nCreated personal branch: %s\nSource LBG commit: %s\n' "$TARGET_BRANCH" "$SOURCE_COMMIT"
printf 'Review: https://github.com/Srujan-DiagonalMatrix/rove/tree/%s\n' "$TARGET_BRANCH"
=======
# Usage: bash deploy/lbg-pull.sh [LBG_BRANCH] [NEW_PERSONAL_BRANCH]
set -euo pipefail
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
exec bash "$script_dir/lbg-sync.sh" pull "$@"
>>>>>>> 993d97bf571536b43a0512695af13d6e3863ac79
