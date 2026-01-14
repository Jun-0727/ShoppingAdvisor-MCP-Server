"""
HTTP/SSE 전송을 지원하는 MCP 서버
"""
from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import logging
from typing import Optional

from .oauth import setup_oauth, verify_token
from .server import mcp  # 기존 MCP 인스턴스

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="Shopping Advisor MCP Server",
    description="Smart shopping decision support MCP server",
    version="0.1.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth 설정
setup_oauth(app)

# Health check
@app.get("/health")
async def health():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "shopping-advisor-mcp",
        "version": "0.1.0"
    }

# 인증된 사용자 정보 가져오기
async def get_current_user(authorization: str = Header(None)) -> dict:
    """Access Token으로 현재 사용자 정보 조회"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    user_data = await verify_token(authorization)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user_data

# MCP 메시지 처리 엔드포인트
@app.post("/messages")
async def handle_messages(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    MCP 메시지 처리 (인증 필요)
    """
    try:
        body = await request.json()
        
        logger.info(f"MCP 요청: user={user['user_email']}, method={body.get('method')}")
        
        # MCP 프로토콜 처리
        method = body.get('method')
        
        if method == 'tools/list':
            # 도구 목록 반환
            tools = [
                {
                    "name": "get_product",
                    "description": "제품명 또는 카테고리를 기반으로 제품의 특징, 장점, 단점, 구매 시 확인사항을 제공합니다.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "product_name": {
                                "type": "string",
                                "description": "조회할 제품의 이름 또는 카테고리"
                            }
                        },
                        "required": ["product_name"]
                    }
                },
                {
                    "name": "create_shopping_guide",
                    "description": "제품명을 기반으로 구매 가이드를 생성하여 선택 기준, 예산별 추천, 구매 시기/장소, 주의사항을 제공합니다.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "product_name": {
                                "type": "string",
                                "description": "구매 가이드를 생성할 제품명"
                            }
                        },
                        "required": ["product_name"]
                    }
                },
                {
                    "name": "compare_products",
                    "description": "2개 이상의 제품을 비교하여 각 제품의 장단점, 사양 비교, 사용 사례별 추천, 가성비 분석을 제공합니다.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "product_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "비교할 제품명 리스트 (최소 2개)"
                            },
                            "comparison_points": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "비교할 특정 항목 리스트 (선택사항)"
                            }
                        },
                        "required": ["product_names"]
                    }
                }
            ]
            
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "tools": tools
                }
            }
        
        elif method == 'tools/call':
            # 도구 실행
            tool_name = body.get('params', {}).get('name')
            arguments = body.get('params', {}).get('arguments', {})
            
            # 실제 MCP 도구 호출 (기존 server.py의 함수 사용)
            # TODO: 여기에 실제 도구 호출 로직 연결
            
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"도구 '{tool_name}' 실행 완료"
                        }
                    ]
                }
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"메시지 처리 에러: {e}")
        return {
            "jsonrpc": "2.0",
            "id": body.get("id") if body else None,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }

if __name__ == "__main__":
    uvicorn.run(
        "shopping_advisor.http_server:app",
        host="0.0.0.0",
        port=int(os.getenv('SERVER_PORT', 8000)),
        reload=True
    )