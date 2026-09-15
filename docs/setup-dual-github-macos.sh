#!/usr/bin/env bash
set -Eeuo pipefail

# ============================================================
# Dual GitHub setup for a secured macOS development machine
#
# Personal GitHub = source of new ROVE code
# Company GitHub  = destination used for company/GCP deployment
#
# Safe behaviour:
# - creates separate SSH keys for personal/company GitHub accounts
# - does NOT overwrite existing keys
# - preserves existing ~/.ssh/config (and makes a backup)
# - clones/pulls only from the personal repository
# - configures company repository as a second remote
# - does NOT perform a real push; only optional --dry-run checks
# ============================================================

PERSONAL_REPO_PATH="Srujan-DiagonalMatrix/rove.git"
COMPANY_REPO_PATH="lbg-cloud-platform/tactical-innovation-f2b97b.git"

# Override when running, e.g.:
#   ROVE_DIR="$HOME/work/rove" ./setup-dual-github-macos.sh
ROVE_DIR="${ROVE_DIR:-$HOME/dev/rove}"

SSH_DIR="$HOME/.ssh"
PERSONAL_KEY="$SSH_DIR/id_ed25519_github_personal"
COMPANY_KEY="$SSH_DIR/id_ed25519_github_company"
SSH_CONFIG="$SSH_DIR/config"

PERSONAL_HOST="github-personal"
COMPANY_HOST="github-company"

# GitHub supports SSH over port 443 at ssh.github.com. This is often more
# compatible with secured corporate networks than SSH port 22.
GITHUB_SSH_HOST="ssh.github.com"
GITHUB_SSH_PORT="443"

PERSONAL_REMOTE="git@${PERSONAL_HOST}:${PERSONAL_REPO_PATH}"
COMPANY_REMOTE="git@${COMPANY_HOST}:${COMPANY_REPO_PATH}"

START_MARKER="# >>> dual-github-rove setup >>>"
END_MARKER="# <<< dual-github-rove setup <<<"

info() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m[OK]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[WARN]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[ERROR]\033[0m %s\n' "$*" >&2; exit 1; }

command -v git >/dev/null 2>&1 || die "git is not installed or is blocked by company policy."
command -v ssh >/dev/null 2>&1 || die "ssh is not installed or is blocked by company policy."
command -v ssh-keygen >/dev/null 2>&1 || die "ssh-keygen is unavailable."

if [[ "$(uname -s)" != "Darwin" ]]; then
  die "This script is intended for macOS."
fi

info "1/7 - Preparing SSH directory"
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"
touch "$SSH_CONFIG"
chmod 600 "$SSH_CONFIG"

make_key() {
  local key_file="$1"
  local label="$2"

  if [[ -f "$key_file" && -f "${key_file}.pub" ]]; then
    ok "Existing $label SSH key retained: $key_file"
    return 0
  fi

  if [[ -e "$key_file" || -e "${key_file}.pub" ]]; then
    die "Only one half of the key pair exists for $key_file. Fix/remove it manually, then rerun."
  fi

  info "Creating $label SSH key"
  printf '%s\n' "You will be asked for a passphrase. Using one is recommended on a company laptop."
  ssh-keygen -t ed25519 \
    -C "${label}-github-$(whoami)@$(hostname -s)" \
    -f "$key_file"
  chmod 600 "$key_file"
  chmod 644 "${key_file}.pub"
}

info "2/7 - Creating/reusing separate GitHub SSH keys"
make_key "$PERSONAL_KEY" "personal"
make_key "$COMPANY_KEY" "company"

info "3/7 - Configuring two GitHub SSH identities"
cp "$SSH_CONFIG" "${SSH_CONFIG}.backup.$(date +%Y%m%d%H%M%S)"

tmp_config="$(mktemp)"
awk -v start="$START_MARKER" -v end="$END_MARKER" '
  $0 == start { skip=1; next }
  $0 == end   { skip=0; next }
  !skip       { print }
' "$SSH_CONFIG" > "$tmp_config"

{
  cat <<EOF_CONFIG
$START_MARKER
Host $PERSONAL_HOST
    HostName $GITHUB_SSH_HOST
    Port $GITHUB_SSH_PORT
    User git
    IdentityFile $PERSONAL_KEY
    IdentitiesOnly yes
    AddKeysToAgent yes
    UseKeychain yes

Host $COMPANY_HOST
    HostName $GITHUB_SSH_HOST
    Port $GITHUB_SSH_PORT
    User git
    IdentityFile $COMPANY_KEY
    IdentitiesOnly yes
    AddKeysToAgent yes
    UseKeychain yes
$END_MARKER

EOF_CONFIG
  cat "$tmp_config"
} > "$SSH_CONFIG"
rm -f "$tmp_config"
chmod 600 "$SSH_CONFIG"
ok "SSH aliases configured: $PERSONAL_HOST and $COMPANY_HOST"

info "4/7 - Loading keys into macOS SSH agent / Keychain"
# macOS normally provides an SSH agent. Start one only if none is available.
if ! ssh-add -l >/dev/null 2>&1; then
  eval "$(ssh-agent -s)" >/dev/null
fi

add_key() {
  local key_file="$1"
  if ssh-add --apple-use-keychain "$key_file" 2>/dev/null; then
    return 0
  fi
  ssh-add "$key_file"
}

add_key "$PERSONAL_KEY"
add_key "$COMPANY_KEY"
ok "SSH keys loaded"

show_and_register_key() {
  local label="$1"
  local key_file="$2"

  info "Register the $label public key in the correct GitHub account"
  printf '\n%s public key:\n\n' "$label"
  cat "${key_file}.pub"
  printf '\n\n'

  if command -v pbcopy >/dev/null 2>&1; then
    pbcopy < "${key_file}.pub"
    printf '%s\n' "The key has also been copied to your clipboard."
  fi

  if command -v open >/dev/null 2>&1; then
    open "https://github.com/settings/ssh/new" >/dev/null 2>&1 || true
  fi

  printf '%s\n' "In GitHub: Settings -> SSH and GPG keys -> New SSH key -> Authentication key."
  if [[ "$label" == "company" ]]; then
    printf '%s\n' "If your company organisation enforces SAML SSO, authorize this key for the organisation after adding it."
  fi
  read -r -p "After adding this key to the $label GitHub account, press Enter to continue... " _
}

show_and_register_key "personal" "$PERSONAL_KEY"
show_and_register_key "company" "$COMPANY_KEY"

info "5/7 - Testing both GitHub identities"
test_github_ssh() {
  local label="$1"
  local host_alias="$2"
  local out

  # GitHub intentionally returns exit status 1 even after successful SSH authentication.
  out="$(ssh -T -o ConnectTimeout=15 "git@${host_alias}" 2>&1 || true)"
  printf '%s\n' "$out"

  if grep -qi "successfully authenticated" <<< "$out"; then
    ok "$label GitHub SSH authentication works"
  else
    die "$label GitHub SSH authentication failed. Verify that the correct public key was added to the correct GitHub account and, for company GitHub, that SSO access is authorized."
  fi
}

test_github_ssh "Personal" "$PERSONAL_HOST"
test_github_ssh "Company" "$COMPANY_HOST"

info "6/7 - Preparing the ROVE working copy"
mkdir -p "$(dirname "$ROVE_DIR")"

if [[ -d "$ROVE_DIR/.git" ]]; then
  ok "Existing Git repository found: $ROVE_DIR"
else
  if [[ -e "$ROVE_DIR" && -n "$(ls -A "$ROVE_DIR" 2>/dev/null || true)" ]]; then
    die "$ROVE_DIR exists and is not an empty Git repository. Choose another location with ROVE_DIR=/path/to/rove"
  fi
  git clone "$PERSONAL_REMOTE" "$ROVE_DIR"
fi

if git -C "$ROVE_DIR" remote get-url origin >/dev/null 2>&1; then
  git -C "$ROVE_DIR" remote set-url origin "$PERSONAL_REMOTE"
else
  git -C "$ROVE_DIR" remote add origin "$PERSONAL_REMOTE"
fi

if git -C "$ROVE_DIR" remote get-url company >/dev/null 2>&1; then
  git -C "$ROVE_DIR" remote set-url company "$COMPANY_REMOTE"
else
  git -C "$ROVE_DIR" remote add company "$COMPANY_REMOTE"
fi

# Personal GitHub is authoritative for incoming code.
git -C "$ROVE_DIR" fetch origin --prune

# Verify that company repository can at least be reached/read.
git -C "$ROVE_DIR" ls-remote company >/dev/null
ok "Both Git remotes are reachable"

info "7/7 - Performing non-destructive push permission checks"
TEST_BRANCH="access-check-$(whoami)-$(date +%Y%m%d%H%M%S)"

check_push_dry_run() {
  local remote="$1"
  local label="$2"
  local output

  output="$(git -C "$ROVE_DIR" push --dry-run "$remote" "HEAD:refs/heads/$TEST_BRANCH" 2>&1 || true)"
  printf '%s\n' "$output"

  if grep -Eqi "denied|permission|not found|403|authentication failed|could not read|repository access" <<< "$output"; then
    warn "$label dry-run indicates push access may be blocked. Check repository permissions/SSO/branch policy."
  else
    ok "$label push dry-run completed without an obvious authentication/permission error"
  fi
}

check_push_dry_run origin "Personal GitHub"
check_push_dry_run company "Company GitHub"

CURRENT_BRANCH="$(git -C "$ROVE_DIR" branch --show-current)"
[[ -n "$CURRENT_BRANCH" ]] || CURRENT_BRANCH="main"

printf '\n\033[1;32m============================================================\033[0m\n'
printf '\033[1;32mSETUP COMPLETE\033[0m\n'
printf '\033[1;32m============================================================\033[0m\n\n'
printf 'Working directory: %s\n' "$ROVE_DIR"
printf 'Current branch:     %s\n\n' "$CURRENT_BRANCH"

git -C "$ROVE_DIR" remote -v

cat <<EOF_USAGE

Normal workflow on the COMPANY MacBook:

  cd "$ROVE_DIR"

  # 1. Get the newest code from your PERSONAL GitHub
  git checkout "$CURRENT_BRANCH"
  git pull --ff-only origin "$CURRENT_BRANCH"

  # 2. Push that exact code to the COMPANY GitHub
  git push company "$CURRENT_BRANCH:$CURRENT_BRANCH"

Explicit remotes:
  origin  = personal GitHub (source)
  company = company GitHub  (deployment destination)

The script did NOT make a real push to either repository.
EOF_USAGE
