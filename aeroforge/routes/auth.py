from fastapi import APIRouter
from services.auth import oauth_login

router = APIRouter(prefix='/auth', tags=['auth'])

@router.get('/login/{provider}')
def login(provider: str):
    if provider.lower() not in {'google', 'microsoft'}:
        return {'error': 'provider must be google or microsoft'}
    return oauth_login(provider.lower())
