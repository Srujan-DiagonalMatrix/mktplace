# mktplace

Lloyds Market Place — an AI-assisted car buying MVP with a FastAPI backend and Streamlit frontend.

## Current application entrypoints

- Main backend entrypoint: `src.backend.main:app` (FastAPI app for Uvicorn).
- Main frontend entrypoint: `src/frontend/app.py` (Streamlit app).

## Service URLs

When running the full Docker stack:

- Frontend UI: http://localhost:8501
- Backend API: http://localhost:8000
- Backend API docs: http://localhost:8000/docs
- ChromaDB host port: http://localhost:8001
- Portainer: https://localhost:9443
- Postgres host port: `localhost:5433` mapped to container port `5432`

## Docker-first quickstart

Docker Compose is the recommended local runtime because it starts the combined app container (FastAPI backend + Streamlit frontend), Postgres, ChromaDB, and Portainer with the same service names the containers expect.

1. Create `.env.docker`:

   ```bash
   cat > .env.docker <<'ENV'
   OPENAI_API_KEY=
   DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/mktplace
   POSTGRES_DB=mktplace
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   # The combined Docker app binds FastAPI to 0.0.0.0 internally and
   # sets FASTAPI_HOST=127.0.0.1 for frontend-to-backend calls.
   FASTAPI_HOST=127.0.0.1
   FASTAPI_PORT=8000
   STREAMLIT_HOST=0.0.0.0
   STREAMLIT_PORT=8501
   INVENTORY_CSV_PATH=data/dataset.csv
   PLACEHOLDER_IMAGE_PATH=assets/placeholder.svg
   CHROMA_ENABLED=false
   CHROMA_DB_PATH=/app/vector_db
   ADMIN_TOKEN=
   ENV
   ```

   `OPENAI_API_KEY` is optional for the current deterministic demo flow, but can be filled in for future AI-backed behaviour.

2. Build and start the stack:

   ```bash
   docker compose up -d --build
   ```

3. Check containers and logs:

   ```bash
   docker compose ps
   docker compose logs -f app
   docker compose logs -f postgres
   ```

4. Open the frontend at http://localhost:8501 and the backend docs at http://localhost:8000/docs.

5. Stop the stack when finished:

   ```bash
   docker compose down
   # Optional destructive cleanup of DB/vector/Portainer volumes:
   docker compose down -v
   ```


### Automatic Docker Compose refresh on code changes

If you want the whole Docker stack to restart whenever project code or configuration changes, run this watcher in a separate terminal:

```bash
scripts/auto-refresh-compose.sh
```

The watcher polls `src`, `app`, `docker`, `scripts`, `requirements.txt`, Compose files, `.env.example`, `README.md`, and `docs` by default. On a change it runs:

```bash
docker compose down
docker compose up -d --build
```

You can tune it with environment variables, for example:

```bash
POLL_INTERVAL=5 WATCH_PATHS="src docker docker-compose.yml" scripts/auto-refresh-compose.sh
```

## Local quick test commands

For a fast non-Docker feedback loop, install dependencies and run the test suite from the repository root:

```bash
python -m pip install -r requirements.txt
python -m pytest tests/unit
python -m pytest tests/integration
python -m pytest tests/e2e
```

Useful direct run commands, if you already have dependencies and required services available locally:

```bash
uvicorn src.backend.main:app --reload --host 127.0.0.1 --port 8000
streamlit run src/frontend/app.py --server.address=127.0.0.1 --server.port=8501
```

## Full Docker validation commands

Run this sequence to validate the application in its recommended Docker environment:

```bash
docker compose up -d --build
docker compose ps
docker compose exec app python -m pytest tests/unit tests/integration tests/e2e
curl -f http://localhost:8000/health
curl -f http://localhost:8000/catalog/
curl -f -X POST http://localhost:8000/chat/message \
  -H 'Content-Type: application/json' \
  -d '{"message":"I am looking to buy with a budget of £450 per month"}'
```

If you need to validate the frontend process is reachable from the host, also run:

```bash
curl -f http://localhost:8501
```

## Frontend UI overview

The frontend is a three-column Streamlit experience:

- Left navigation rail: static visual navigation for Chat, Recommendations, Finance, Shortlist, and Settings.
- Middle chat region: header, New Session control, assistant messages, quick replies, free-text input, and send button.
- Right recommendations region: finance summary cards, recommendation cards, and a compact finance summary.
- Detail/enquiry region: rendered below the main columns when a vehicle is selected.

Current UI behaviour to be aware of:

- The sidebar navigation is display-only; it does not switch pages yet.
- Recommendation card action buttons are rendered for View Details, Shortlist, and Enquire, but the cards currently present the visual shell rather than a full click-through workflow.
- The Finance Summary `View Finance Options` control is display-only.
- The chat area is the main interactive flow: messages are sent to `POST /chat/message`, returned preferences are stored in session state, and recommendations refresh from `GET /recommendations/from_session`.

See `docs/frontend-ui.md` for a fuller UI map and `docs/testing.md` for test strategy and Docker/offline-queue notes.

### Operational notes

- Source code, data, and assets are mounted into the app container via volumes, so local edits are reflected in the running container.
- FastAPI and Streamlit are packaged together in `docker/Dockerfile` and run in the single `app` Compose service while still exposing host ports `8000` and `8501`.
- Backend uses `uvicorn --reload`; frontend Streamlit reloads on source changes. Use `scripts/auto-refresh-compose.sh` if you want code/configuration changes to trigger a full `docker compose down` followed by `docker compose up -d --build`.
- Inventory CSV defaults to `data/dataset.csv`; car images are served from `assets/` where available.
- If Postgres is unavailable during enquiry submission, the API queues the enquiry in `data/offline_enquiries.jsonl` and returns HTTP `202`. Flush queued enquiries after Postgres is restored with `docker compose exec app python -m src.backend.scripts.flush_offline_enquiries` or `POST /admin/flush_offline`.


### docker commands ###
clear
git pull
docker compose -f "docker-compose-ubuntu.yml" down
docker compose -f "docker-compose-ubuntu.yml" build
docker compose -f "docker-compose-ubuntu.yml" up -d
clear

clear
git pull
docker compose -f "docker-compose-ubuntu.yml" down
docker compose -f "docker-compose-ubuntu.yml" up -d
clear