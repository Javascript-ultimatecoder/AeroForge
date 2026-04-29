import os
import io
import json
import math
import random
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from pydantic import BaseModel
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm

# Optional PDF text extraction
try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

# Optional image handling
try:
    from PIL import Image
except Exception:
    Image = None

app = FastAPI(title="AeroForge+", version="1.3")


@app.get("/")
def home():
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/health")
def health():
    return {
        "ok": True,
        "app": "AeroForge+",
        "env": os.getenv("AEROFORGE_ENV", "development"),
        "max_iterations": int(os.getenv("AEROFORGE_MAX_ITERATIONS", "1000")),
    }


@app.get("/config")
def config():
    return {
        "name": "AeroForge+",
        "environment": os.getenv("AEROFORGE_ENV", "development"),
        "max_iterations": int(os.getenv("AEROFORGE_MAX_ITERATIONS", "1000")),
        "modes": ["Distance", "Airtime", "Height", "Hybrid"],
    }


# ---------------------------------------------------------------------
# Core data model
# ---------------------------------------------------------------------

class PlaneDesign(BaseModel):
    name: str = "Unnamed"
    mode: str = "Distance"  # Distance / Airtime / Height / Hybrid
    wingspan_mm: float = 190.0
    dihedral_deg: float = 3.0
    wing_angle_deg: float = 48.0
    center_of_mass_pct: float = 0.35  # fraction from nose
    nose_lock_mm: float = 15.0
    tail_tab_mm: float = 5.0
    camber_mm: float = 0.5
    symmetry_error_mm: float = 0.0
    notes: str = ""

# ---------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def safe_round(v: float, digits: int = 2) -> float:
    return round(float(v), digits)

def now_stamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def to_download_url(pdf_path: str) -> str:
    filename = Path(pdf_path).name
    return f"/download?path={filename}"

def read_pdf_text(file_bytes: bytes) -> str:
    if PdfReader is None:
        return ""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                pass
        return "\n".join(texts).strip()
    except Exception:
        return ""

def inspect_image_bytes(file_bytes: bytes) -> Dict[str, Any]:
    """
    Lightweight image inspection without OCR.
    Returns basic metadata only unless you plug in a real vision model.
    """
    info = {
        "detected": True,
        "format": None,
        "width": None,
        "height": None,
        "aspect_ratio": None,
    }
    if Image is None:
        return info
    try:
        img = Image.open(io.BytesIO(file_bytes))
        info["format"] = img.format
        info["width"], info["height"] = img.size
        info["aspect_ratio"] = safe_round(img.size[0] / img.size[1], 3) if img.size[1] else None
    except Exception:
        pass
    return info

# ---------------------------------------------------------------------
# "AI" analysis layer
# Replace this with a vision LLM call if you connect one later.
# ---------------------------------------------------------------------

def analyze_design(file_bytes: bytes, filename: str, mode: str) -> Dict[str, Any]:
    text = ""
    ext = os.path.splitext(filename.lower())[1]

    if ext == ".pdf":
        text = read_pdf_text(file_bytes)

    image_info = inspect_image_bytes(file_bytes) if ext in [".png", ".jpg", ".jpeg", ".webp"] else {}

    # Heuristic extraction from PDF text if present
    parsed = {
        "source_file": filename,
        "mode": mode,
        "extracted_text_preview": text[:1200],
        "image_info": image_info,
    }

    # Baseline design guess
    design = PlaneDesign(mode=mode)

    # Very simple heuristic tuning from mode
    if mode == "Distance":
        design.wingspan_mm = 188
        design.dihedral_deg = 2.5
        design.wing_angle_deg = 49
        design.center_of_mass_pct = 0.33
        design.nose_lock_mm = 16
        design.tail_tab_mm = 4
        design.camber_mm = 0.2
        design.notes = "Narrow, stiff, low-drag profile."
    elif mode == "Airtime":
        design.wingspan_mm = 202
        design.dihedral_deg = 3.5
        design.wing_angle_deg = 46
        design.center_of_mass_pct = 0.37
        design.nose_lock_mm = 14
        design.tail_tab_mm = 6
        design.camber_mm = 0.8
        design.notes = "Wide, floaty, lift-focused profile."
    elif mode == "Height":
        design.wingspan_mm = 178
        design.dihedral_deg = 5.0
        design.wing_angle_deg = 44
        design.center_of_mass_pct = 0.31
        design.nose_lock_mm = 17
        design.tail_tab_mm = 5
        design.camber_mm = 0.4
        design.notes = "Compact climb-biased profile."
    else:  # Hybrid
        design.wingspan_mm = 194
        design.dihedral_deg = 3.5
        design.wing_angle_deg = 47
        design.center_of_mass_pct = 0.34
        design.nose_lock_mm = 15
        design.tail_tab_mm = 5
        design.camber_mm = 0.5
        design.notes = "Switchable balanced tri-mode profile."

    # If PDF text mentions design cues, lightly adapt
    lower_text = text.lower()
    if "glide" in lower_text:
        design.camber_mm = clamp(design.camber_mm + 0.2, 0.0, 2.0)
    if "speed" in lower_text or "distance" in lower_text:
        design.dihedral_deg = clamp(design.dihedral_deg - 0.5, 1.5, 6.0)
    if "stall" in lower_text or "float" in lower_text:
        design.camber_mm = clamp(design.camber_mm + 0.3, 0.0, 2.0)

    parsed["baseline_design"] = design.model_dump()
    return parsed

# ---------------------------------------------------------------------
# Physics scoring
# ---------------------------------------------------------------------

def simulate_physics(design: Dict[str, Any]) -> Dict[str, Any]:
    span = float(design["wingspan_mm"])
    dihedral = float(design["dihedral_deg"])
    wing_angle = float(design["wing_angle_deg"])
    com = float(design["center_of_mass_pct"])
    nose = float(design["nose_lock_mm"])
    tail = float(design["tail_tab_mm"])
    camber = float(design["camber_mm"])
    sym = float(design.get("symmetry_error_mm", 0.0))

    # Heuristic scoring
    lift = clamp((span / 220.0) * (0.6 + camber * 0.35) * (1.0 + dihedral * 0.03), 0.0, 2.0)
    drag = clamp((1.4 - (wing_angle - 42.0) * 0.015) + sym * 0.03 + (tail * 0.01), 0.1, 2.5)
    stability = clamp(1.25 - abs(com - 0.34) * 2.2 - abs(dihedral - 3.5) * 0.09 - sym * 0.04, 0.0, 1.5)
    stall_risk = clamp(0.65 - camber * 0.22 + abs(com - 0.34) * 1.0 - dihedral * 0.04, 0.0, 1.0)

    mode = design["mode"]
    if mode == "Distance":
        mode_bonus = 0.18 if span < 195 and drag < 1.4 else 0.0
    elif mode == "Airtime":
        mode_bonus = 0.18 if camber > 0.5 and span > 190 else 0.0
    elif mode == "Height":
        mode_bonus = 0.18 if dihedral >= 4.5 and nose >= 15 else 0.0
    else:
        mode_bonus = 0.12

    glide_score = clamp((lift * stability) / drag + mode_bonus, 0.0, 3.0)
    total_score = glide_score * 100.0 - stall_risk * 15.0 - sym * 2.0

    return {
        "lift": safe_round(lift, 3),
        "drag": safe_round(drag, 3),
        "stability": safe_round(stability, 3),
        "stall_risk": safe_round(stall_risk, 3),
        "glide_score": safe_round(glide_score, 3),
        "total_score": safe_round(total_score, 2),
    }

# ---------------------------------------------------------------------
# Optimizer
# ---------------------------------------------------------------------

def mutate_design(d: Dict[str, Any], mode: str, extreme: bool = False) -> Dict[str, Any]:
    nd = dict(d)
    scale = 1.0 if not extreme else 1.8

    nd["wingspan_mm"] = clamp(d["wingspan_mm"] + random.uniform(-8, 8) * scale, 160, 230)
    nd["dihedral_deg"] = clamp(d["dihedral_deg"] + random.uniform(-0.8, 0.8) * scale, 1.0, 7.0)
    nd["wing_angle_deg"] = clamp(d["wing_angle_deg"] + random.uniform(-1.5, 1.5) * scale, 40, 55)
    nd["center_of_mass_pct"] = clamp(d["center_of_mass_pct"] + random.uniform(-0.03, 0.03) * scale, 0.25, 0.42)
    nd["nose_lock_mm"] = clamp(d["nose_lock_mm"] + random.uniform(-1.5, 1.5) * scale, 10, 20)
    nd["tail_tab_mm"] = clamp(d["tail_tab_mm"] + random.uniform(-1.0, 1.0) * scale, 2, 10)
    nd["camber_mm"] = clamp(d["camber_mm"] + random.uniform(-0.25, 0.25) * scale, 0.0, 2.0)

    # Mode-directed nudges
    if mode == "Distance":
        nd["wingspan_mm"] = clamp(nd["wingspan_mm"] - random.uniform(0, 6), 160, 220)
        nd["camber_mm"] = clamp(nd["camber_mm"] - random.uniform(0, 0.15), 0.0, 2.0)
    elif mode == "Airtime":
        nd["camber_mm"] = clamp(nd["camber_mm"] + random.uniform(0, 0.2), 0.0, 2.0)
        nd["dihedral_deg"] = clamp(nd["dihedral_deg"] + random.uniform(0, 0.5), 1.0, 7.0)
    elif mode == "Height":
        nd["dihedral_deg"] = clamp(nd["dihedral_deg"] + random.uniform(0, 0.7), 1.0, 7.0)
        nd["nose_lock_mm"] = clamp(nd["nose_lock_mm"] + random.uniform(0, 1.0), 10, 20)

    return nd

def optimize_design(base_design: Dict[str, Any], extreme: bool = False, iterations: int = 120) -> Dict[str, Any]:
    best = dict(base_design)
    best_metrics = simulate_physics(best)
    best_score = best_metrics["total_score"]

    history: List[Dict[str, Any]] = []

    for _ in range(iterations):
        candidate = mutate_design(best, best["mode"], extreme=extreme)
        metrics = simulate_physics(candidate)
        score = metrics["total_score"]

        history.append({"design": candidate, "metrics": metrics})
        if score > best_score:
            best = candidate
            best_metrics = metrics
            best_score = score

    best["symmetry_error_mm"] = 0.0
    return {
        "best_design": best,
        "best_metrics": best_metrics,
        "history_top": sorted(history, key=lambda x: x["metrics"]["total_score"], reverse=True)[:5],
    }

# ---------------------------------------------------------------------
# Design generation
# ---------------------------------------------------------------------

def generate_30_step_instructions(design: Dict[str, Any]) -> str:
    mode = design["mode"]
    name = {
        "Distance": "Distance Flyer",
        "Airtime": "Airtime Glider",
        "Height": "Height Climber",
        "Hybrid": "Hybrid X",
    }.get(mode, "Custom Plane")

    steps = []
    for i in range(1, 31):
        if mode == "Distance":
            text = f"Step {i}: Refine the narrow-body distance geometry with a precise crease, keeping the center spine straight and the nose lock tight."
        elif mode == "Airtime":
            text = f"Step {i}: Expand lift behavior by tuning camber, preserving a soft nose and a smooth wing arc for hang time."
        elif mode == "Height":
            text = f"Step {i}: Increase climb bias with a compact rigid fold, stronger dihedral, and a disciplined nose-up balance."
        else:
            text = f"Step {i}: Switch and lock the tri-mode structure, preserving D/A/H tab positions while reinforcing the hybrid core."
        steps.append(text)

    tuning = []
    tuning.append(f"Mode: {mode}")
    tuning.append(f"Wingspan: {safe_round(design['wingspan_mm'], 1)} mm")
    tuning.append(f"Dihedral: {safe_round(design['dihedral_deg'], 1)} deg")
    tuning.append(f"Wing angle: {safe_round(design['wing_angle_deg'], 1)} deg")
    tuning.append(f"Center of mass: {safe_round(design['center_of_mass_pct'] * 100, 1)}% from nose")
    tuning.append(f"Nose lock: {safe_round(design['nose_lock_mm'], 1)} mm")
    tuning.append(f"Tail tab: {safe_round(design['tail_tab_mm'], 1)} mm")
    tuning.append(f"Camber: {safe_round(design['camber_mm'], 2)} mm")

    return f"{name}\n\n" + "\n".join(steps) + "\n\nTUNING\n" + "\n".join(tuning)

# ---------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------

def build_pdf(design: Dict[str, Any], metrics: Dict[str, Any], analysis: Dict[str, Any], filepath: str) -> str:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="TitleCenter",
        parent=styles["Title"],
        alignment=1,
        fontSize=18,
        leading=22,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="Small",
        parent=styles["BodyText"],
        fontSize=8.3,
        leading=10.2,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="Tiny",
        parent=styles["BodyText"],
        fontSize=7.2,
        leading=8.8,
        spaceAfter=2,
    ))

    doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=14*mm, rightMargin=14*mm, topMargin=12*mm, bottomMargin=12*mm)
    story = []

    story.append(Paragraph("AeroForge+ / Paper Plane Optimization Report", styles["TitleCenter"]))
    story.append(Paragraph(f"Generated: {datetime.utcnow().isoformat()}Z", styles["Tiny"]))
    story.append(Spacer(1, 4))

    summary_rows = [
        ["Mode", design["mode"]],
        ["Wingspan", f"{safe_round(design['wingspan_mm'],1)} mm"],
        ["Dihedral", f"{safe_round(design['dihedral_deg'],1)} deg"],
        ["Wing angle", f"{safe_round(design['wing_angle_deg'],1)} deg"],
        ["Center of mass", f"{safe_round(design['center_of_mass_pct']*100,1)}% from nose"],
        ["Nose lock", f"{safe_round(design['nose_lock_mm'],1)} mm"],
        ["Tail tab", f"{safe_round(design['tail_tab_mm'],1)} mm"],
        ["Camber", f"{safe_round(design['camber_mm'],2)} mm"],
        ["Lift", str(metrics["lift"])],
        ["Drag", str(metrics["drag"])],
        ["Stability", str(metrics["stability"])],
        ["Stall risk", str(metrics["stall_risk"])],
        ["Glide score", str(metrics["glide_score"])],
        ["Total score", str(metrics["total_score"])],
    ]
    tbl = Table([["Field", "Value"]] + summary_rows, colWidths=[46*mm, 132*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.black),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#888888")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.HexColor("#F7F7F7")]),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 6))

    story.append(Paragraph("Analysis snapshot", styles["Small"]))
    preview = analysis.get("extracted_text_preview", "")
    if preview:
        story.append(Paragraph(preview.replace("\n", "<br/>")[:2200], styles["Tiny"]))
    else:
        story.append(Paragraph("No text extracted from the uploaded file. If this was an image, connect a vision model for full extraction.", styles["Tiny"]))

    story.append(PageBreak())

    story.append(Paragraph("30-Step Build", styles["TitleCenter"]))
    story.append(Spacer(1, 4))

    instructions = generate_30_step_instructions(design).split("\n")
    for line in instructions:
        if not line.strip():
            story.append(Spacer(1, 4))
        elif line.startswith("Step "):
            story.append(Paragraph(f"<b>{line}</b>", styles["Small"]))
        elif line == "TUNING":
            story.append(Spacer(1, 4))
            story.append(Paragraph("<b>Tuning</b>", styles["Small"]))
        else:
            story.append(Paragraph(line, styles["Tiny"]))

    doc.build(story)
    return filepath

# ---------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------

@app.post("/optimize")
async def optimize_plane(
    file: UploadFile = File(...),
    mode: str = Form("Hybrid"),
    extreme_mode: bool = Form(False),
    iterations: int = Form(120),
):
    if mode not in {"Distance", "Airtime", "Height", "Hybrid"}:
        raise HTTPException(status_code=400, detail="Invalid mode. Use Distance, Airtime, Height, or Hybrid.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file upload.")

    analysis = analyze_design(file_bytes, file.filename or "upload", mode)
    baseline = analysis["baseline_design"]
    max_iterations = int(os.getenv("AEROFORGE_MAX_ITERATIONS", "1000"))
    optimization = optimize_design(baseline, extreme=extreme_mode, iterations=max(10, min(iterations, max_iterations)))

    best_design = optimization["best_design"]
    best_metrics = optimization["best_metrics"]

    out_dir = os.path.join(os.getcwd(), "outputs")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"aeroforge_{now_stamp()}.pdf")
    build_pdf(best_design, best_metrics, analysis, pdf_path)

    return JSONResponse({
        "ok": True,
        "filename": file.filename,
        "mode": mode,
        "extreme_mode": extreme_mode,
        "analysis": analysis,
        "best_design": best_design,
        "best_metrics": best_metrics,
        "top_candidates": optimization["history_top"],
        "pdf_path": pdf_path,
        "download_url": to_download_url(pdf_path),
    })

@app.get("/download")
def download(path: str):
    outputs_dir = Path(os.getcwd()) / "outputs"
    requested = Path(path).name
    full_path = outputs_dir / requested
    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(str(full_path), media_type="application/pdf", filename=requested)

# ---------------------------------------------------------------------
# Local run
# ---------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("aeroforge_app:app", host="0.0.0.0", port=8000, reload=True)
