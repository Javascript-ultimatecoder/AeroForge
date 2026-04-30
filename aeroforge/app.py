from fastapi import FastAPI
from routes import optimize, auth, leaderboard

app = FastAPI(title='AeroForge v4')
app.include_router(optimize.router)
app.include_router(auth.router)
app.include_router(leaderboard.router)
