from __future__ import annotations

import random
import uuid
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer

app = FastAPI(title="AeroForge+ v3+", version="3.2.0")
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
LEADERBOARD: list[dict] = []


@app.get("/")
def home() -> HTMLResponse:
    return HTMLResponse((BASE_DIR / "index.html").read_text(encoding="utf-8"))


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def extract_geometry(file_bytes: bytes) -> dict[str, float]:
    nparr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image upload.")

    blur = cv2.GaussianBlur(img, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return {"span": 180.0, "angle": 3.0, "balance": 0.33}

    cnt = max(contours, key=cv2.contourArea)
    _, _, w, h = cv2.boundingRect(cnt)
    area_ratio = cv2.contourArea(cnt) / max(1, w * h)

    span = clamp(float(w), 80, 380)
    angle = clamp((h / (w + 1)) * 10, 0.5, 10)
    balance = clamp(0.28 + area_ratio * 0.2 + (np.mean(edges) / 255) * 0.05, 0.1, 0.5)
    return {"span": span, "angle": angle, "balance": balance}


def simulate(d: dict[str, float]) -> float:
    rho = 1.225
    v = 8.0
    area = d["span"] * 0.0001
    reynolds = (rho * v * (d["span"] * 0.001)) / 1.81e-5

    lift_coeff = 0.1 * d["angle"]
    drag_coeff = 0.02 + (d["angle"] ** 2) * 0.01
    lift = 0.5 * rho * v**2 * area * lift_coeff
    drag = 0.5 * rho * v**2 * area * drag_coeff

    stability = 1 - abs(d["balance"] - 0.33)
    glide = lift / (drag + 1e-5)
    reynolds_factor = np.log(reynolds + 1) / 10
    return max(0.0, glide * max(0.2, stability) * reynolds_factor)


def mutate(d: dict[str, float]) -> dict[str, float]:
    return {
        "span": clamp(d["span"] + random.uniform(-15, 15), 50, 400),
        "angle": clamp(d["angle"] + random.uniform(-1, 1), 0.5, 11),
        "balance": clamp(d["balance"] + random.uniform(-0.05, 0.05), 0.1, 0.5),
    }


def crossover(a: dict[str, float], b: dict[str, float]) -> dict[str, float]:
    return {"span": (a["span"] + b["span"]) / 2, "angle": (a["angle"] + b["angle"]) / 2, "balance": (a["balance"] + b["balance"]) / 2}


def optimize(initial: dict[str, float]) -> tuple[dict[str, float], float]:
    population = [initial] + [mutate(initial) for _ in range(17)]
    for _ in range(25):
        scored = sorted(((simulate(d), d) for d in population), reverse=True, key=lambda x: x[0])
        elites = [d for _, d in scored[:6]]
        next_gen = elites[:]
        while len(next_gen) < 24:
            p1, p2 = random.sample(elites, 2)
            next_gen.append(mutate(crossover(p1, p2)))
        population = next_gen

    best = max(population, key=simulate)
    return best, simulate(best)


def generate_graphs(best: dict[str, float]) -> tuple[Path, Path]:
    angles = list(range(5, 60, 5))
    dist = []
    stability_curve = []
    for a in angles:
        d = best.copy()
        d["angle"] = a / 10
        dist.append(simulate(d) * 10)
        stability_curve.append(1 - abs(d["balance"] - 0.33))

    p1 = OUTPUT_DIR / f"dist_{uuid.uuid4().hex[:8]}.png"
    p2 = OUTPUT_DIR / f"stab_{uuid.uuid4().hex[:8]}.png"

    plt.figure(figsize=(6, 3.3)); plt.plot(angles, dist, marker="o"); plt.title("Distance Curve"); plt.xlabel("Throw Angle"); plt.ylabel("Distance Index"); plt.grid(alpha=0.3); plt.tight_layout(); plt.savefig(p1); plt.close()
    plt.figure(figsize=(6, 3.3)); plt.plot(angles, stability_curve, marker="o"); plt.title("Stability Curve"); plt.xlabel("Throw Angle"); plt.ylabel("Stability"); plt.grid(alpha=0.3); plt.tight_layout(); plt.savefig(p2); plt.close()
    return p1, p2


def create_pdf(text: str, g1: Path, g2: Path) -> Path:
    path = OUTPUT_DIR / f"report_{uuid.uuid4().hex[:8]}.pdf"
    doc = SimpleDocTemplate(str(path))
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("AeroForge+ v3+ Report", styles["Title"]), Spacer(1, 15),
        Paragraph("Section 1: Analysis Summary", styles["Heading2"]), Paragraph(text.replace("\n", "<br/>"), styles["BodyText"]), Spacer(1, 16),
        Paragraph("Section 2: Distance Curve", styles["Heading2"]), Image(str(g1), width=420, height=230), Spacer(1, 16),
        Paragraph("Section 3: Stability Curve", styles["Heading2"]), Image(str(g2), width=420, height=230),
    ]
    doc.build(elements)
    return path


@app.post("/optimize")
async def optimize_plane(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file upload.")

    initial = extract_geometry(data)
    best, score = optimize(initial)
    g1, g2 = generate_graphs(best)

    text = f"Initial:\nSpan {initial['span']:.2f}\nAngle {initial['angle']:.2f}\nBalance {initial['balance']:.2f}\n\nOptimized:\nSpan {best['span']:.2f}\nAngle {best['angle']:.2f}\nBalance {best['balance']:.2f}\n\nScore: {score:.4f}"
    pdf = create_pdf(text, g1, g2)

    LEADERBOARD.append({"score": score, "design": best})
    LEADERBOARD.sort(reverse=True, key=lambda x: x["score"])

    return {
        "initial": initial,
        "optimized": best,
        "score": score,
        "graphs": [f"/file?name={g1.name}", f"/file?name={g2.name}"],
        "pdf": f"/file?name={pdf.name}",
        "leaderboard": LEADERBOARD[:5],
    }


@app.get("/leaderboard")
def leaderboard():
    return {"entries": LEADERBOARD[:10]}


@app.get("/file")
def get_file(name: str):
    path = OUTPUT_DIR / Path(name).name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(path))
