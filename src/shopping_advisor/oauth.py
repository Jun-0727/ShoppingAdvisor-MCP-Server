"""
Google OAuth 2.1 구현
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# OAuth 라우터
router = APIRouter()

# 환경 변수 로드
config = Config('.env')

# OAuth 클라이언트 설정
oauth = OAuth(config)

# Google OAuth 등록
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# 토큰 저장소 (프로덕션에서는 Redis 사용 권장)
tokens: Dict[str, dict] = {}
auth_codes: Dict[str, dict] = {}

# MCP OAuth 메타데이터 엔드포인트
@router.get("/.well-known/oauth-authorization-server")
async def oauth_metadata(request: Request):
    """MCP가 요구하는 OAuth 메타데이터"""
    base_url = os.getenv('BASE_URL', 'http://localhost:8000')
    
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "scopes_supported": ["mcp:use"],
    }

# OAuth 인증 시작
@router.get("/oauth/authorize")
async def authorize(request: Request):
    """
    Claude.ai가 호출하는 인증 시작 엔드포인트
    """
    try:
        # 파라미터 추출
        client_id = request.query_params.get('client_id')
        redirect_uri = request.query_params.get('redirect_uri')
        state = request.query_params.get('state')
        scope = request.query_params.get('scope', 'mcp:use')
        
        logger.info(f"OAuth authorize 요청: client_id={client_id}, state={state}")
        
        # State를 세션에 저장
        request.session['oauth_state'] = state
        request.session['mcp_redirect_uri'] = redirect_uri
        request.session['mcp_client_id'] = client_id
        
        # Google OAuth 인증 시작
        redirect_uri_google = f"{os.getenv('BASE_URL')}/oauth/callback"
        return await oauth.google.authorize_redirect(
            request, 
            redirect_uri_google
        )
        
    except Exception as e:
        logger.error(f"OAuth authorize 에러: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Google OAuth 콜백
@router.get("/oauth/callback")
async def oauth_callback(request: Request):
    """
    Google에서 돌아오는 콜백
    """
    try:
        # Google OAuth 토큰 획득
        token = await oauth.google.authorize_access_token(request)
        
        # 사용자 정보 조회
        user_info = token.get('userinfo')
        
        if not user_info:
            raise HTTPException(status_code=400, detail="사용자 정보를 가져올 수 없습니다")
        
        logger.info(f"사용자 로그인 성공: {user_info.get('email')}")
        
        # Authorization Code 생성 (MCP용)
        auth_code = secrets.token_urlsafe(32)
        
        # Authorization Code 저장
        auth_codes[auth_code] = {
            'user_email': user_info.get('email'),
            'user_name': user_info.get('name'),
            'mcp_client_id': request.session.get('mcp_client_id'),
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(minutes=10)
        }
        
        # Claude.ai로 리다이렉트
        mcp_redirect_uri = request.session.get('mcp_redirect_uri')
        oauth_state = request.session.get('oauth_state')
        
        if not mcp_redirect_uri:
            raise HTTPException(status_code=400, detail="Redirect URI가 없습니다")
        
        # Claude.ai로 Authorization Code 전달
        return RedirectResponse(
            url=f"{mcp_redirect_uri}?code={auth_code}&state={oauth_state}"
        )
        
    except Exception as e:
        logger.error(f"OAuth callback 에러: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# 토큰 발급
@router.post("/oauth/token")
async def token_endpoint(request: Request):
    """
    Claude.ai가 Authorization Code를 Access Token으로 교환하는 엔드포인트
    """
    try:
        form_data = await request.form()
        grant_type = form_data.get('grant_type')
        
        logger.info(f"Token 요청: grant_type={grant_type}")
        
        if grant_type == 'authorization_code':
            code = form_data.get('code')
            
            if not code or code not in auth_codes:
                raise HTTPException(status_code=400, detail="Invalid authorization code")
            
            auth_data = auth_codes[code]
            
            # 만료 확인
            if datetime.utcnow() > auth_data['expires_at']:
                del auth_codes[code]
                raise HTTPException(status_code=400, detail="Authorization code expired")
            
            # Access Token 생성
            access_token = secrets.token_urlsafe(32)
            refresh_token = secrets.token_urlsafe(32)
            
            # 토큰 저장
            tokens[access_token] = {
                'user_email': auth_data['user_email'],
                'user_name': auth_data['user_name'],
                'refresh_token': refresh_token,
                'created_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(hours=1)
            }
            
            # Authorization Code 삭제 (일회용)
            del auth_codes[code]
            
            logger.info(f"Access Token 발급: {auth_data['user_email']}")
            
            return {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": refresh_token
            }
        
        elif grant_type == 'refresh_token':
            refresh_token_value = form_data.get('refresh_token')
            
            # 기존 토큰 찾기
            old_access_token = None
            for token_key, token_data in tokens.items():
                if token_data.get('refresh_token') == refresh_token_value:
                    old_access_token = token_key
                    break
            
            if not old_access_token:
                raise HTTPException(status_code=400, detail="Invalid refresh token")
            
            # 새 Access Token 생성
            new_access_token = secrets.token_urlsafe(32)
            tokens[new_access_token] = tokens[old_access_token].copy()
            tokens[new_access_token]['expires_at'] = datetime.utcnow() + timedelta(hours=1)
            
            logger.info(f"Access Token 갱신: {tokens[new_access_token]['user_email']}")
            
            return {
                "access_token": new_access_token,
                "token_type": "Bearer",
                "expires_in": 3600
            }
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported grant type")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token endpoint 에러: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Access Token 검증 미들웨어
async def verify_token(authorization: str) -> Optional[dict]:
    """Access Token 검증"""
    if not authorization or not authorization.startswith('Bearer '):
        return None
    
    token = authorization.replace('Bearer ', '')
    
    if token not in tokens:
        return None
    
    token_data = tokens[token]
    
    # 만료 확인
    if datetime.utcnow() > token_data['expires_at']:
        del tokens[token]
        return None
    
    return token_data

# OAuth 설정을 앱에 추가하는 함수
def setup_oauth(app):
    """FastAPI 앱에 OAuth 라우터 및 세션 미들웨어 추가"""
    
    # 세션 미들웨어 추가
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv('SESSION_SECRET', secrets.token_urlsafe(32))
    )
    
    # OAuth 라우터 추가
    app.include_router(router)
    
    logger.info("OAuth 설정 완료")