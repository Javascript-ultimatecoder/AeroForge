import os
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse

from core.analysis import analyze_design
from core.instructions import build_instructions
from core.optimizer import optimize_design
from utils.graph import generate_graph
from utils.pdf import build_pdf
from services.leaderboard import add_score

router = APIRouter()

@router.post('/optimize')
async def optimize(file: UploadFile = File(...), user: str = 'guest'):
    data = await file.read()
    analysis = analyze_design(data, file.filename or 'upload', 'Hybrid')
    result = optimize_design(analysis['baseline_design'])
    graph = generate_graph(result['history'])
    pdf = build_pdf(result['best_design'], result['best_metrics'], graph)
    add_score(user, result['best_metrics']['total_score'])
    return {
        'score': result['best_metrics']['total_score'],
        'design': result['best_design'],
        'instructions': build_instructions(result['best_design']),
        'download': f"/download/{os.path.basename(pdf)}",
    }

@router.get('/download/{file}')
def download(file: str):
    path = os.path.join('aeroforge', 'outputs', os.path.basename(file))
    if not os.path.exists(path):
        return {'error': 'file not found'}
    return FileResponse(path)
