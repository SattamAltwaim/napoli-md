# Backend

Flask REST API for frame-split NAPOLI trajectory jobs.

## Run

From the repository root:

```bash
uv sync
uv run python run_backend.py
```

Or with `pip`:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m ensurepip --upgrade
python -m pip install -r backend/requirements.txt
python run_backend.py
```

The API runs on `http://localhost:5001`.

## Notes

- Jobs are discovered from `systems/` by default. Each child folder with `frame_*` directories is treated as one job.
- Override the jobs folder with `NAPOLI_SYSTEMS_ROOT=/path/to/systems`.
- Conserved islands are intentionally skipped and return `{"islands": []}`.
- Upload endpoints are present but inert because the processing engine is not bundled.
