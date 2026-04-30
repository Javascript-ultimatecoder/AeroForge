from fastapi import APIRouter
from services.leaderboard import get_top

router = APIRouter(prefix='/leaderboard', tags=['leaderboard'])

@router.get('')
def leaderboard():
    return {'top': get_top()}
