# Local Environment Notes

Operational notes for developers running OnePilot AI on this machine. No secrets.

## Repository path

Canonical local checkout:

```text
/Users/hallo/Developer/OnePilot-AI
```

If an older checkout lived under `Desktop/AI Projects/OnePilot-AI`, do **not** point tools or shells at that path — it may be missing or stale.

## Backend virtual environment

The backend uses a **uv**-managed `.venv` under `backend/.venv`.

### Symptom of a stale environment

Shell sessions sometimes export:

```bash
VIRTUAL_ENV=/Users/hallo/Desktop/AI Projects/OnePilot-AI/backend/.venv
```

That path does not match the Developer checkout. `uv` then warns and ignores the active environment:

```text
warning: VIRTUAL_ENV=.../Desktop/AI Projects/OnePilot-AI/backend/.venv
does not match the project environment path `.venv` and will be ignored
```

### Safe repair (do not commit `.venv`)

```bash
cd /Users/hallo/Developer/OnePilot-AI
unset VIRTUAL_ENV
cd backend
uv sync --extra dev   # only if dependencies are missing
uv run python -m pytest -q
```

Notes:

- Prefer `uv run …` so the project `.venv` is selected explicitly.
- Do **not** commit `backend/.venv`.
- Do not change application dependencies unless a package is actually broken.
- If `backend/.venv` itself still contains Desktop shebang paths, recreate with `uv venv` + `uv sync --extra dev` from `backend/` after `unset VIRTUAL_ENV`.

### Verified healthy shape

A healthy `backend/.venv/pyvenv.cfg` points at a uv-managed CPython under `~/.local/share/uv/python/…` and does **not** reference the Desktop path.

## Frontend tooling

```bash
cd frontend
pnpm install
pnpm lint && pnpm typecheck && pnpm test && pnpm build
```

If `pnpm` is missing: `npm install -g pnpm@9` (or enable Corepack on Node distributions that ship it).

## Public demo smoke (against live backend)

```bash
unset VIRTUAL_ENV
python scripts/smoke_test_public_demo.py \
  --base-url https://onepilot-ai-production.up.railway.app
```

Do not modify host environment variables from local sessions unless explicitly asked.
