#!/bin/bash
# ROVE GitHub diagnostic for a secured macOS laptop.
# Read-only/non-destructive: does not change remotes, keys, Git config, or repositories.
# It creates a temporary test clone and removes it automatically.
#
# Usage:
#   chmod +x diagnose-rove-github.sh
#   ./diagnose-rove-github.sh
#
# Optional comparison with a known-good personal repo:
#   ./diagnose-rove-github.sh git@github.com:YOUR-USER/KNOWN-GOOD-REPO.git

set +e

ROVE_SSH="git@github.com:Srujan-DiagonalMatrix/rove.git"
ROVE_HTTPS="https://github.com/Srujan-DiagonalMatrix/rove.git"
KNOWN_GOOD_REPO="${1:-}"
REPORT="${PWD}/rove_git_diagnostic_report_$(date +%Y%m%d_%H%M%S).txt"
TMPDIR_TEST="$(mktemp -d -t rove-git-diag.XXXXXX 2>/dev/null || mktemp -d)"
CLONE_DIR="${TMPDIR_TEST}/rove-test"

cleanup() {
  rm -rf "$TMPDIR_TEST" >/dev/null 2>&1
}
trap cleanup EXIT INT TERM

section() {
  printf "\n============================================================\n" | tee -a "$REPORT"
  printf "%s\n" "$1" | tee -a "$REPORT"
  printf "============================================================\n" | tee -a "$REPORT"
}

run_capture() {
  local label="$1"
  shift
  printf "\n--- %s ---\n" "$label" >> "$REPORT"
  "$@" >> "$REPORT" 2>&1
  local rc=$?
  printf "[exit_code=%s]\n" "$rc" >> "$REPORT"
  return $rc
}

redact_url() {
  sed -E 's#https://[^/@:]+:[^/@]+@#https://***:***@#g'
}

echo "ROVE GitHub Diagnostic Report" > "$REPORT"
echo "Generated: $(date)" >> "$REPORT"
echo "Target repo: $ROVE_SSH" >> "$REPORT"
echo "Host: $(hostname 2>/dev/null)" >> "$REPORT"
echo "User: $(whoami 2>/dev/null)" >> "$REPORT"

section "1. SYSTEM / GIT INFORMATION"
{
  echo "macOS:"
  sw_vers 2>/dev/null || uname -a
  echo
  echo "Git:"
  git --version 2>&1
  echo
  echo "Git executable:"
  command -v git 2>&1
  echo
  echo "SSH:"
  ssh -V 2>&1
  echo
  echo "Git LFS:"
  git lfs version 2>&1 || echo "Git LFS not installed / not available"
} >> "$REPORT"

section "2. SAFE GIT CONFIG CHECKS"
{
  echo "Global SSH command:"
  git config --global --get core.sshCommand 2>/dev/null || echo "<not set>"
  echo
  echo "Global proxy settings:"
  git config --global --get http.proxy 2>/dev/null || echo "http.proxy: <not set>"
  git config --global --get https.proxy 2>/dev/null || echo "https.proxy: <not set>"
  echo
  echo "URL rewrite rules:"
  git config --global --get-regexp '^url\..*\.insteadof$' 2>/dev/null | redact_url || echo "<none>"
} >> "$REPORT"

section "3. SSH AGENT / KEY VISIBILITY"
{
  echo "SSH_AUTH_SOCK=${SSH_AUTH_SOCK:-<not set>}"
  echo
  echo "Keys currently loaded in ssh-agent (fingerprints only):"
  ssh-add -l 2>&1 || true
  echo
  echo "Relevant ~/.ssh/config entries (safe fields only):"
  if [ -f "$HOME/.ssh/config" ]; then
    awk '
      BEGIN {IGNORECASE=1}
      /^[[:space:]]*Host[[:space:]]/ ||
      /^[[:space:]]*HostName[[:space:]]/ ||
      /^[[:space:]]*User[[:space:]]/ ||
      /^[[:space:]]*Port[[:space:]]/ ||
      /^[[:space:]]*IdentityFile[[:space:]]/ ||
      /^[[:space:]]*IdentitiesOnly[[:space:]]/ {
        print
      }
    ' "$HOME/.ssh/config"
  else
    echo "~/.ssh/config does not exist"
  fi
} >> "$REPORT"

section "4. BASIC GITHUB NETWORK TESTS"
run_capture "DNS lookup: github.com" dscacheutil -q host -a name github.com
DNS_RC=$?

run_capture "HTTPS reachability: https://github.com" \
  curl -I -L --max-time 12 --connect-timeout 8 -sS https://github.com
HTTPS_RC=$?

run_capture "TCP port 22 to github.com" nc -G 8 -vz github.com 22
PORT22_RC=$?

run_capture "TCP port 443 to ssh.github.com" nc -G 8 -vz ssh.github.com 443
PORT443_RC=$?

section "5. GITHUB SSH AUTHENTICATION"
SSH22_OUT="${TMPDIR_TEST}/ssh22.txt"
ssh -T \
  -o BatchMode=yes \
  -o ConnectTimeout=10 \
  -o ConnectionAttempts=1 \
  git@github.com >"$SSH22_OUT" 2>&1
SSH22_RC=$?
{
  echo "--- SSH authentication via github.com:22 ---"
  cat "$SSH22_OUT"
  echo "[exit_code=$SSH22_RC]"
} >> "$REPORT"

SSH443_OUT="${TMPDIR_TEST}/ssh443.txt"
ssh -T \
  -p 443 \
  -o BatchMode=yes \
  -o ConnectTimeout=10 \
  -o ConnectionAttempts=1 \
  -o UserKnownHostsFile=/dev/null \
  -o StrictHostKeyChecking=no \
  git@ssh.github.com >"$SSH443_OUT" 2>&1
SSH443_RC=$?
{
  echo
  echo "--- SSH authentication via ssh.github.com:443 ---"
  cat "$SSH443_OUT"
  echo "[exit_code=$SSH443_RC]"
} >> "$REPORT"

SSH22_OK=0
SSH443_OK=0
grep -qi "successfully authenticated" "$SSH22_OUT" && SSH22_OK=1
grep -qi "successfully authenticated" "$SSH443_OUT" && SSH443_OK=1

section "6. ROVE REPOSITORY ACCESS TEST"
LSREMOTE_OUT="${TMPDIR_TEST}/lsremote.txt"
GIT_TERMINAL_PROMPT=0 \
GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1" \
git ls-remote "$ROVE_SSH" >"$LSREMOTE_OUT" 2>&1
LSREMOTE_RC=$?
{
  echo "--- git ls-remote over SSH ---"
  head -80 "$LSREMOTE_OUT"
  echo "[exit_code=$LSREMOTE_RC]"
} >> "$REPORT"

HTTPS_REMOTE_OUT="${TMPDIR_TEST}/httpsremote.txt"
GIT_TERMINAL_PROMPT=0 \
git ls-remote "$ROVE_HTTPS" >"$HTTPS_REMOTE_OUT" 2>&1
HTTPS_REMOTE_RC=$?
{
  echo
  echo "--- git ls-remote over HTTPS (non-interactive; private repo may require credentials) ---"
  redact_url < "$HTTPS_REMOTE_OUT" | head -80
  echo "[exit_code=$HTTPS_REMOTE_RC]"
} >> "$REPORT"

if [ -n "$KNOWN_GOOD_REPO" ]; then
  section "7. KNOWN-GOOD PERSONAL REPO COMPARISON"
  GOOD_OUT="${TMPDIR_TEST}/goodrepo.txt"
  GIT_TERMINAL_PROMPT=0 \
  GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1" \
  git ls-remote "$KNOWN_GOOD_REPO" >"$GOOD_OUT" 2>&1
  GOOD_RC=$?
  {
    echo "Known-good repo: $KNOWN_GOOD_REPO"
    head -80 "$GOOD_OUT"
    echo "[exit_code=$GOOD_RC]"
  } >> "$REPORT"
else
  GOOD_RC=99
  section "7. KNOWN-GOOD PERSONAL REPO COMPARISON"
  echo "Skipped. Optional usage:" >> "$REPORT"
  echo "./diagnose-rove-github.sh git@github.com:YOUR-USER/KNOWN-GOOD-REPO.git" >> "$REPORT"
fi

section "8. LIGHTWEIGHT CLEAN CLONE TEST"
CLONE_OUT="${TMPDIR_TEST}/clone.txt"
GIT_TERMINAL_PROMPT=0 \
GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1" \
git clone \
  --no-checkout \
  --filter=blob:none \
  --depth 1 \
  --single-branch \
  --branch main \
  "$ROVE_SSH" \
  "$CLONE_DIR" >"$CLONE_OUT" 2>&1
CLONE_RC=$?
{
  echo "--- partial shallow clone output ---"
  head -150 "$CLONE_OUT"
  echo "[exit_code=$CLONE_RC]"
} >> "$REPORT"

if [ "$CLONE_RC" -eq 0 ]; then
  {
    echo
    echo "Clone succeeded."
    echo "HEAD:"
    git -C "$CLONE_DIR" rev-parse HEAD 2>&1
    echo
    echo "Remote:"
    git -C "$CLONE_DIR" remote -v 2>&1
    echo
    echo "Repository object summary:"
    git -C "$CLONE_DIR" count-objects -vH 2>&1
    echo
    echo ".gitattributes at HEAD (if present):"
    git -C "$CLONE_DIR" show HEAD:.gitattributes 2>&1 || echo "<none>"
  } >> "$REPORT"
fi

section "9. EXISTING LOCAL ROVE CHECK"
FOUND_LOCAL=0
for candidate in \
  "$PWD" \
  "$PWD/rove" \
  "$HOME/rove" \
  "$HOME/dev/rove" \
  "$HOME/Developer/rove" \
  "$HOME/projects/rove" \
  "$HOME/workspace/rove"
do
  if [ -d "$candidate/.git" ]; then
    FOUND_LOCAL=1
    {
      echo
      echo "Existing Git checkout found: $candidate"
      echo "Top-level: $(git -C "$candidate" rev-parse --show-toplevel 2>/dev/null)"
      echo "Current branch: $(git -C "$candidate" branch --show-current 2>/dev/null)"
      echo "HEAD: $(git -C "$candidate" rev-parse --short HEAD 2>/dev/null)"
      echo "Status:"
      git -C "$candidate" status --short --branch 2>&1 | head -50
      echo "Remotes:"
      git -C "$candidate" remote -v 2>&1 | redact_url
      echo "Repo-specific core.sshCommand:"
      git -C "$candidate" config --local --get core.sshCommand 2>/dev/null || echo "<not set>"
    } >> "$REPORT"
  fi
done

if [ "$FOUND_LOCAL" -eq 0 ]; then
  echo "No existing rove checkout found in the common locations checked." >> "$REPORT"
fi

section "10. AUTOMATIC DIAGNOSIS"
{
  if [ "$HTTPS_RC" -ne 0 ] && [ "$PORT22_RC" -ne 0 ] && [ "$PORT443_RC" -ne 0 ]; then
    echo "LIKELY LOCATION: Company network / DNS / proxy / endpoint security."
    echo "Reason: GitHub HTTPS and both SSH routes are unreachable."
  elif [ "$SSH22_OK" -eq 0 ] && [ "$SSH443_OK" -eq 0 ]; then
    echo "LIKELY LOCATION: SSH authentication/key selection."
    echo "Reason: GitHub network is reachable, but neither SSH route authenticated."
    echo "Check which key is loaded and which GitHub account that key belongs to."
  elif [ "$LSREMOTE_RC" -ne 0 ]; then
    echo "LIKELY LOCATION: ROVE-specific repository access or wrong SSH identity."
    echo "Reason: GitHub SSH authentication works, but git ls-remote for ROVE failed."
    if [ "$GOOD_RC" -eq 0 ]; then
      echo "Strong evidence: the supplied known-good personal repository works from the same laptop."
    fi
  elif [ "$CLONE_RC" -ne 0 ]; then
    echo "LIKELY LOCATION: Git object transfer / repository-size / proxy / endpoint-security issue."
    echo "Reason: ROVE refs are accessible, but even a lightweight depth-1 partial clone failed."
  else
    echo "REMOTE ACCESS IS HEALTHY."
    echo "Reason: GitHub SSH, ROVE ls-remote, and a fresh lightweight clone all succeeded."
    echo "Most likely problem is the existing local ROVE checkout, its local Git config, or a stale remote."
  fi

  echo
  echo "Result codes:"
  echo "  DNS lookup               : $DNS_RC"
  echo "  GitHub HTTPS             : $HTTPS_RC"
  echo "  github.com port 22       : $PORT22_RC"
  echo "  ssh.github.com port 443  : $PORT443_RC"
  echo "  SSH auth port 22         : $SSH22_OK"
  echo "  SSH auth port 443        : $SSH443_OK"
  echo "  ROVE ls-remote           : $LSREMOTE_RC"
  echo "  ROVE lightweight clone   : $CLONE_RC"
  if [ "$GOOD_RC" -ne 99 ]; then
    echo "  Known-good repo ls-remote: $GOOD_RC"
  fi
} >> "$REPORT"

section "11. PRIVACY NOTE"
cat >> "$REPORT" <<'PRIVACY'
This report intentionally does NOT print:
- private SSH key contents
- GitHub tokens/passwords
- credential-helper stored credentials
- full Git environment variables

Before sharing, you may still skim the report for company-specific hostnames,
usernames, file paths, or policy information you do not want to disclose.
PRIVACY

printf "\nDiagnostic complete.\n"
printf "Report created at:\n%s\n\n" "$REPORT"
printf "Send me the generated report file (or paste its contents), and I can locate the failing layer.\n"
