#!/usr/bin/env bash
set -Eeuo pipefail
set +x

GCP_PROJECT="${GCP_PROJECT:-tactical-innovation-f2b97b}"
REGION="${REGION:-europe-west1}"
REPOSITORY="${REPOSITORY:-cloud-run-source-deploy}"
API_SERVICE="${API_SERVICE:-rove-api}"
WEB_SERVICE="${WEB_SERVICE:-rove-web}"
BRANCH="${BRANCH:-fix/frontend-build-source-cleanup}"
REMOTE="${REMOTE:-origin}"

fail() { echo "ERROR: $*" >&2; exit 1; }
gc() { gcloud --project="$GCP_PROJECT" "$@"; }

command -v gcloud >/dev/null || fail 'Install Google Cloud CLI first.'

# Default mode makes no changes.
if [[ "${1:---check}" == --check ]]; then
  echo "Checking resources in $GCP_PROJECT"
  gc run services list --region="$REGION" \
    --format='table(metadata.name,status.url)'
  gc sql instances list \
    --format='table(name,region,databaseVersion,state,connectionName)'
  gc artifacts repositories list --location="$REGION" \
    --format='table(name,format)'
  gc secrets list --format='table(name)'
  echo 'Only secret names were listed; no secret values were read.'
  echo 'If Cloud SQL is missing, investigate backups/recovery before deploying.'
  exit 0
fi

[[ "${1:-}" == --deploy ]] || fail 'Use --check or --deploy.'

: "${CLOUD_SQL_CONNECTION:?Set CLOUD_SQL_CONNECTION=PROJECT:REGION:INSTANCE}"
: "${DATABASE_URL_SECRET:?Set DATABASE_URL_SECRET=SECRET_NAME:VERSION}"
: "${ADMIN_USERNAME_SECRET:?Set ADMIN_USERNAME_SECRET=SECRET_NAME:VERSION}"
: "${ADMIN_PASSWORD_SECRET:?Set ADMIN_PASSWORD_SECRET=SECRET_NAME:VERSION}"

for tool in git node npm docker python3 curl tar; do
  command -v "$tool" >/dev/null || fail "Missing command: $tool"
done
docker info >/dev/null
docker buildx version >/dev/null

repo_root=$(git -C "${REPO_DIR:-$PWD}" rev-parse --show-toplevel)
work=$(mktemp -d)
chmod 700 "$work"
trap 'rm -rf "$work"' EXIT
trap 'echo "Stopped at line $LINENO. Earlier cloud changes may remain. No database reset or automatic rollback was attempted." >&2' ERR

export CLOUD_SQL_CONNECTION DATABASE_URL_SECRET
export ADMIN_USERNAME_SECRET ADMIN_PASSWORD_SECRET
export EXTRA_SECRETS="${EXTRA_SECRETS:-}"

# Validate configuration without reading secret values.
python3 - "$GCP_PROJECT" "$work" <<'PY'
import os, re, sys
from pathlib import Path

parts = os.environ["CLOUD_SQL_CONNECTION"].split(":")
if (len(parts) != 3 or parts[0] != sys.argv[1]
    or not all(re.fullmatch(r"[a-z][a-z0-9-]*", p) for p in parts)):
    raise SystemExit("Use an existing Cloud SQL instance in GCP_PROJECT.")

refs = {
    k: os.environ[k + "_SECRET"]
    for k in ("DATABASE_URL", "ADMIN_USERNAME", "ADMIN_PASSWORD")
}
for item in filter(None, os.environ["EXTRA_SECRETS"].split(",")):
    key, sep, value = item.partition("=")
    if not sep or key in refs:
        raise SystemExit("Invalid or duplicate EXTRA_SECRETS entry.")
    refs[key] = value

for key, value in refs.items():
    if (not re.fullmatch(r"[A-Z][A-Z0-9_]*", key)
        or not re.fullmatch(r"[A-Za-z0-9_-]+:(latest|[0-9]+)", value)):
        raise SystemExit("Use ENV=SECRET_NAME:VERSION references.")

w = Path(sys.argv[2])
(w / "secret-refs").write_text(
    "".join(v + "\n" for v in sorted(set(refs.values())))
)
(w / "secret-args").write_text(
    ",".join(k + "=" + v for k, v in refs.items())
)
PY

sql_instance=${CLOUD_SQL_CONNECTION##*:}
gc sql instances describe "$sql_instance" --format=json > "$work/sql.json"

python3 - "$work/sql.json" "$CLOUD_SQL_CONNECTION" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
if (s.get("connectionName") != sys.argv[2]
    or s.get("state") != "RUNNABLE"
    or not s.get("databaseVersion", "").startswith("POSTGRES")):
    raise SystemExit("Existing Cloud SQL must be runnable PostgreSQL.")
if not any(i.get("type") == "PRIMARY" for i in s.get("ipAddresses", [])):
    raise SystemExit(
        "Private-IP-only SQL requires your original VPC settings. Stopped."
    )
PY

while IFS=: read -r secret version; do
  state=$(gc secrets versions describe "$version" \
    --secret="$secret" --format='value(state)')
  [[ "$state" == ENABLED ]] || fail "Secret version unavailable: $secret:$version"
done < "$work/secret-refs"

# Optional API_ENV_FILE contains JSON environment settings.
python3 - "${API_ENV_FILE:-}" "$work/env.json" "$work/secret-args" <<'PY'
import json, sys
values = json.load(open(sys.argv[1])) if sys.argv[1] else {}
if not isinstance(values, dict) or any(
    not isinstance(v, str) for v in values.values()
):
    raise SystemExit("API_ENV_FILE must be a JSON object with string values.")
secrets = {
    item.split("=", 1)[0] for item in open(sys.argv[3]).read().split(",")
}
if secrets.intersection(values):
    raise SystemExit("Do not duplicate secret names in API_ENV_FILE.")
values.update(
    APP_ENV="production",
    AUTH_COOKIE_SECURE="true",
    SESSION_COOKIE_SECURE="true",
)
json.dump(values, open(sys.argv[2], "w"))
PY

echo "=== Fetch and build remote source in isolation ==="
git -C "$repo_root" check-ref-format --branch "$BRANCH" >/dev/null
git -C "$repo_root" fetch "$REMOTE" "refs/heads/$BRANCH"
commit=$(git -C "$repo_root" rev-parse FETCH_HEAD)
mkdir "$work/source"
git -C "$repo_root" archive "$commit" | tar -x -C "$work/source"
cd "$work/source"

[[ -f package-lock.json && -f server/Dockerfile ]] \
  || fail 'Expected ROVE source files are missing.'

NODE_USE_SYSTEM_CA=1 npm ci --include=dev
mkdir -p "$work/web/dist"
NODE_USE_SYSTEM_CA=1 VITE_API_URL='' npm run build \
  -- --outDir "$work/web/dist" --emptyOutDir
test -s "$work/web/dist/index.html"

echo "=== Create required cloud resources ==="
gc services enable \
  run.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com sqladmin.googleapis.com \
  iam.googleapis.com --quiet

if ! gc artifacts repositories describe "$REPOSITORY" \
  --location="$REGION" >/dev/null 2>&1; then
  gc artifacts repositories create "$REPOSITORY" \
    --location="$REGION" --repository-format=docker --quiet
fi

[[ "$(gc artifacts repositories describe "$REPOSITORY" \
  --location="$REGION" --format='value(format)')" == DOCKER ]] \
  || fail 'Artifact repository must use Docker format.'

api_account="rove-api-runtime@$GCP_PROJECT.iam.gserviceaccount.com"
web_account="rove-web-runtime@$GCP_PROJECT.iam.gserviceaccount.com"

for name in rove-api-runtime rove-web-runtime; do
  if ! gc iam service-accounts describe \
    "$name@$GCP_PROJECT.iam.gserviceaccount.com" >/dev/null 2>&1; then
    gc iam service-accounts create "$name" \
      --display-name="$name" --quiet
  fi
done

gc projects add-iam-policy-binding "$GCP_PROJECT" \
  --member="serviceAccount:$api_account" \
  --role=roles/cloudsql.client --condition=None --quiet >/dev/null

while IFS=: read -r secret version; do
  gc secrets add-iam-policy-binding "$secret" \
    --member="serviceAccount:$api_account" \
    --role=roles/secretmanager.secretAccessor \
    --condition=None --quiet >/dev/null
done < "$work/secret-refs"

gc auth configure-docker "${REGION}-docker.pkg.dev" --quiet

tag="recovery-$(date -u +%Y%m%d%H%M%S)-${commit:0:12}"
registry="${REGION}-docker.pkg.dev/$GCP_PROJECT/$REPOSITORY"
api_image="$registry/rove-api:$tag"
web_image="$registry/rove-web:$tag"

ca_args=()
if [[ -n "${CORPORATE_CA_FILE:-}" ]]; then
  test -s "$CORPORATE_CA_FILE"
  ca_args=(--secret "id=corporate_ca,src=$CORPORATE_CA_FILE")
fi

echo "=== Build and push API image ==="
docker buildx build --platform linux/amd64 --pull \
  "${ca_args[@]}" --load -t "$api_image" \
  -f server/Dockerfile server

docker run --rm --entrypoint python "$api_image" -c \
  'from alembic.config import Config; from alembic.script import ScriptDirectory; s=ScriptDirectory.from_config(Config("alembic.ini")); assert len(s.get_heads())==1, "Resolve migration heads before deployment"'

docker push "$api_image"

echo "=== Create or update API service ==="
# Public API access is required by the existing Nginx proxy architecture.
# Normal Alembic migrations run before the API starts.
gc run deploy "$API_SERVICE" --region="$REGION" --image="$api_image" \
  --service-account="$api_account" --port=8000 \
  --ingress=all --allow-unauthenticated \
  --add-cloudsql-instances="$CLOUD_SQL_CONNECTION" \
  --env-vars-file="$work/env.json" \
  --update-secrets="$(cat "$work/secret-args")" \
  --max-instances=1 \
  --command=sh \
  --args='-c,alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000' \
  --quiet

gc run services update-traffic "$API_SERVICE" \
  --region="$REGION" --to-latest --quiet

api_url=$(gc run services describe "$API_SERVICE" \
  --region="$REGION" --format='value(status.url)')

curl --fail --silent --show-error --retry 5 --retry-all-errors \
  --max-time 60 "$api_url/api/health" >/dev/null

cat > "$work/web/nginx.conf" <<EOF
server {
  listen 8080;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;
  location /api/ {
    proxy_pass ${api_url};
    proxy_ssl_server_name on;
    proxy_set_header Host ${api_url#https://};
    proxy_set_header X-Forwarded-Proto https;
    proxy_http_version 1.1;
    proxy_read_timeout 120s;
  }
  location = /index.html {
    add_header Cache-Control "no-cache, no-store, must-revalidate" always;
  }
  location / { try_files \$uri \$uri/ /index.html; }
}
EOF

cat > "$work/web/Dockerfile" <<'EOF'
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY dist /usr/share/nginx/html
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
EOF

echo "=== Build and push frontend image ==="
docker buildx build --platform linux/amd64 --pull \
  --push -t "$web_image" "$work/web"

echo "=== Create or update frontend service ==="
gc run deploy "$WEB_SERVICE" --region="$REGION" --image="$web_image" \
  --service-account="$web_account" --port=8080 \
  --ingress=all --allow-unauthenticated --quiet

web_url=$(gc run services describe "$WEB_SERVICE" \
  --region="$REGION" --format='value(status.url)')

gc run services update "$API_SERVICE" --region="$REGION" \
  --update-env-vars="CORS_ORIGIN=$web_url" --quiet

gc run services update-traffic "$API_SERVICE" \
  --region="$REGION" --to-latest --quiet
gc run services update-traffic "$WEB_SERVICE" \
  --region="$REGION" --to-latest --quiet

curl --fail --silent --show-error --retry 5 --retry-all-errors \
  --max-time 60 "$web_url/" >/dev/null
curl --fail --silent --show-error --retry 5 --retry-all-errors \
  --max-time 60 "$web_url/api/health" >/dev/null
curl --fail --silent --show-error --max-time 60 \
  "$web_url/api/catalogue/vehicles" > "$work/catalogue.json"

python3 - "$work/catalogue.json" <<'PY'
import json, sys
vehicles = json.load(open(sys.argv[1]))
if not isinstance(vehicles, list):
    raise SystemExit("Unexpected catalogue response.")
print("Public catalogue vehicle count:", len(vehicles))
if not vehicles:
    print("WARNING: Inventory is empty; dropdowns have no values.")
PY

echo "Deployment complete: $web_url"
echo "API: $api_url"
echo "Source: $BRANCH at $commit"
echo 'Existing database retained. Test login, reservations and dropdowns.'
