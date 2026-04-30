# AeroForge+ v3+

Advanced FastAPI AI app for paper-airplane optimization.

## Features
- Image upload + OpenCV contour/bounding-box geometry extraction
- Aerodynamic-style physics with lift, drag, and Reynolds scaling
- Hybrid genetic optimization (elite + crossover + mutation)
- Two generated graphs (distance + stability)
- Structured PDF report
- In-memory leaderboard
- Modern mobile UI
- Render free-tier compatible

## Local run
```bash
cd aeroforge-v3-plus
python3 -m pip install -r requirements.txt
python3 -m uvicorn aeroforge_app:app --reload
```

## Render deploy
- Root Directory: `aeroforge-v3-plus`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn aeroforge_app:app --host 0.0.0.0 --port $PORT`
