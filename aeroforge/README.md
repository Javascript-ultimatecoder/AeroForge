# AeroForge+

FastAPI web app that accepts image/PDF uploads, runs simulated paper airplane optimization, and generates a PDF report.

## Run locally

```bash
python3 -m pip install -r requirements.txt
python3 -m uvicorn aeroforge_app:app --reload
```

Open: `http://127.0.0.1:8000`

## Render deployment settings

### Recommended (Web Service)
Use **Web Service** because this app has backend API routes.

- **Name**: `aeroforge-plus` (must be unique)
- **Project**: `My project` (optional)
- **Environment**: `Production`
- **Branch**: `main` (or your deploy branch)
- **Root Directory**: `aeroforge`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python3 -m uvicorn aeroforge_app:app --host 0.0.0.0 --port $PORT`
- **Environment Variables**:
  - `AEROFORGE_ENV=production`
  - `AEROFORGE_MAX_ITERATIONS=1000`

### If you still choose Static Site in Render UI
This backend will not run there, but for your form fields:

- **Name**: `aeroforge-plus-ui` (unique)
- **Project**: `My project` (optional)
- **Environment**: `Production`
- **Branch**: `main`
- **Root Directory**: `aeroforge`
- **Build Command**: `echo "Static export not configured"`
- **Publish Directory**: `./`
- **Environment Variables**: optional for static assets only

## API
- `GET /` UI
- `GET /health` runtime health
- `GET /config` runtime config for frontend
- `POST /optimize` optimize and generate report PDF
- `GET /download?path=<filename>` download generated report

## Notes
- `POST /optimize` now returns `download_url` so the frontend can avoid path handling conflicts.
- A `render.yaml` file is included for blueprint deploys.
