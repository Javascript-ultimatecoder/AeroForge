# AeroForge+

FastAPI web app that accepts image/PDF uploads, runs simulated paper airplane optimization, and generates a PDF report.

## Run locally

```bash
python3 -m pip install -r requirements.txt
python3 -m uvicorn aeroforge_app:app --reload
```

Open: `http://127.0.0.1:8000`

## Render deploy (Web Service)

Use a **Web Service** (not Static Site) because this app has FastAPI endpoints.

### Render UI values
- **Name**: `aeroforge-plus` (or any unique name you want)
- **Project**: optional (`My project` is fine)
- **Environment**: `Production`
- **Branch**: your deployment branch (for example `main`)
- **Root Directory**: `aeroforge`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python3 -m uvicorn aeroforge_app:app --host 0.0.0.0 --port $PORT`

> If you choose **Static Site** in Render, this backend API will not run.

## Environment variables
Set these in Render:

- `AEROFORGE_ENV=production`
- `AEROFORGE_MAX_ITERATIONS=1000`

You can also copy `.env.example`.

## Health check

`GET /health` returns runtime env + iteration cap.

## Optional infra-as-code

A `render.yaml` is included in this folder for blueprint-based setup.
