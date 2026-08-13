#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/Users/srujan.kumar/Documents/git/rove"
GCP_PROJECT="tactical-innovation-f2b97b"
REGION="europe-west1"
REPOSITORY="cloud-run-source-deploy"
SERVICE_NAME="rove-web"
IMAGE_NAME="rove-web"

cd "$PROJECT_DIR"

echo "ROVE deployment started"

command -v npm >/dev/null 2>&1 || { echo "ERROR: npm is not installed."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker is not installed."; exit 1; }
command -v gcloud >/dev/null 2>&1 || { echo "ERROR: gcloud CLI is not installed."; exit 1; }

docker info >/dev/null 2>&1 || { echo "ERROR: Docker Desktop is not running."; exit 1; }

if ! gcloud auth print-access-token >/dev/null 2>&1; then
  gcloud auth login
fi

gcloud config set project "$GCP_PROJECT" >/dev/null

echo "[1/6] Installing dependencies..."
NODE_USE_SYSTEM_CA=1 npm ci

echo "[2/6] Building React app..."
NODE_USE_SYSTEM_CA=1 npm run build

if [ ! -d "dist" ]; then
  echo "ERROR: dist/ was not created."
  exit 1
fi

if [ -f ".dockerignore" ]; then
  sed -i '' '/^dist\/?$/d' .dockerignore
fi

echo "[3/6] Preparing Docker runtime..."

cat > Dockerfile <<'EOF'
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY dist /usr/share/nginx/html
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
EOF

cat > nginx.conf <<'EOF'
server {
    listen 8080;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet >/dev/null

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
VERSION_IMAGE="${REGION}-docker.pkg.dev/${GCP_PROJECT}/${REPOSITORY}/${IMAGE_NAME}:${TIMESTAMP}"
LATEST_IMAGE="${REGION}-docker.pkg.dev/${GCP_PROJECT}/${REPOSITORY}/${IMAGE_NAME}:latest"

echo "[4/6] Building and pushing linux/amd64 image..."
docker buildx build \
  --platform linux/amd64 \
  -t "$VERSION_IMAGE" \
  -t "$LATEST_IMAGE" \
  --push \
  .

echo "[5/6] Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image "$VERSION_IMAGE" \
  --region "$REGION" \
  --platform managed \
  --port 8080 \
  --no-invoker-iam-check \
  --quiet

echo "[6/6] Getting service URL..."
SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" \
  --region "$REGION" \
  --format='value(status.url)')"

echo ""
echo "ROVE DEPLOYMENT SUCCESSFUL"
echo "Image tag: $TIMESTAMP"
echo "Website: $SERVICE_URL"

open "$SERVICE_URL" 2>/dev/null || true
