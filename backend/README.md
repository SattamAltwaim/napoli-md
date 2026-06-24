# Backend

Flask REST API for the bundled frame-split `8cgk / 6UQ` simulated trajectory.

## Run

From the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m ensurepip --upgrade
python -m pip install -r backend/requirements.txt
python run_backend.py
```

The API runs on `http://localhost:5001`.

## Notes

- Data is read from `frontend/public/data/simulated_trajectory_8cgk_6UQ` by default.
- Override the data folder with `NAPOLI_DATA_ROOT=/path/to/data`.
- Conserved islands are intentionally skipped and return `{"islands": []}`.
- Upload endpoints are present but inert because the processing engine is not bundled.
