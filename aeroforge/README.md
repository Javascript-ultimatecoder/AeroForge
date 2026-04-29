# AeroForge+

FastAPI web app that accepts image/PDF uploads, runs simulated paper airplane optimization, and generates a PDF report.

## Run locally

```bash
python3 -m pip install -r requirements.txt
python3 -m uvicorn aeroforge_app:app --reload
```

Open: `http://127.0.0.1:8000`

## Render deployment

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
python3 -m uvicorn aeroforge_app:app --host 0.0.0.0 --port $PORT
```
