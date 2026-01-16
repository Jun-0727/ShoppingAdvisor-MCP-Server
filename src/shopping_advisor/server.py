"""
Streamable HTTP 전송을 지원하는 MCP 서버
- 단일 엔드포인트 (/mcp)에서 GET/POST 모두 처리
- GET: SSE 스트림 (서버 → 클라이언트)
- POST: JSON-RPC 메시지 (클라이언트 → 서버)
"""
import os
import asyncio
import uuid
import uvicorn
import logging
import json

from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from .utils.tool import TOOLS_INFO
from .utils.formatter import JsonRpcFormat, ResponseFormat, MarkdownFormat
from .logging_config import setup_logging
from .utils.tool import (
    get_product, 
    create_shopping_guide, 
    compare_products
)

# 로깅 설정
setup_logging(log_level="INFO")
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="Shopping Advisor MCP Server",
    description="Streamable HTTP MCP Server",
    version="0.1.0"
)

# CORS 설정
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"]
)

# ============================================================
# 세션 관리
# ============================================================
class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(self) -> str:
        """새 세션 생성"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "queue": asyncio.Queue(),
            "created_at": asyncio.get_event_loop().time(),
            "initialized": False
        }
        logger.info(f"Session created: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 조회"""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Session deleted: {session_id}")
            return True
        return False
    
    def get_queue(self, session_id: str) -> Optional[asyncio.Queue]:
        """세션의 메시지 큐 조회"""
        session = self.get_session(session_id)
        return session["queue"] if session else None

session_manager = SessionManager()

# ============================================================
# Tool 실행 함수 (실제 구현은 import 해서 사용)
# ============================================================
async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Tool 실행 로직"""
    # tool 유효성 검사
    if not tool_name:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    try:
        if tool_name == "get_product":
            product_name = arguments.get("product_name", "")

            # 제품명 유효성 검사
            if not product_name:
                raise HTTPException(status_code=400, detail="제품명을 입력해주세요.")
            
            # 제품 정보 조회
            product_json = await get_product(product_name=product_name)
            result = MarkdownFormat.product_info(product_json)
            
        elif tool_name == "create_shopping_guide":
            product_name = arguments.get("product_name", "")

            # 제품명 유효성 검사
            if not product_name:
                raise HTTPException(status_code=400, detail="제품명을 입력해주세요.")
            
            shopping_guide_json = await create_shopping_guide(product_name=product_name)
            result = MarkdownFormat.shopping_guide(shopping_guide_json)
        
        elif tool_name == "compare_products":
            product_list = arguments.get("product_list", [])
            comparison_points = arguments.get("comparison_points", [])

            # 제품 리스트 유효성 검사
            if not product_list or not isinstance(product_list, list):
                raise HTTPException(status_code=400, detail="제품명을 입력해주세요.")
            
            comparison_data_json = await compare_products(product_list=product_list, comparison_points=comparison_points)
            result = MarkdownFormat.comparison_data(comparison_data_json)
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        return ResponseFormat.success(result)
    
    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error in {tool_name}: {e}", exc_info=True)
        return ResponseFormat.error("잠시 후 다시 시도해주세요.")
    
# ============================================================
# MCP 메시지 처리
# ============================================================
async def process_mcp_message(body: dict, session_id: Optional[str] = None) -> dict:
    """MCP JSON-RPC 메시지 처리"""
    method = body.get("method")
    params = body.get("params", {})
    msg_id = body.get("id")
    
    logger.info(f"Processing method: {method}, id: {msg_id}")
    
    # ---- initialize ----
    if method == "initialize":
        initialize_info = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True}
                },
                "serverInfo": {
                    "name": "shopping-advisor",
                    "version": "0.1.0"
                }
            }
        return JsonRpcFormat.success(msg_id=msg_id, result=initialize_info)
    
    # ---- notifications/initialized ----
    elif method == "notifications/initialized":
        # 알림이므로 응답 없음 (202 Accepted)
        return None
    
    # ---- tools/list ----
    elif method == "tools/list":
        return JsonRpcFormat.success(msg_id=msg_id, result={"tools": TOOLS_INFO})
    
    # ---- tools/call ----
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        logger.info(f"Tool call: {tool_name}, args: {arguments}")
        
        try:
            tool_output = await execute_tool(tool_name, arguments)
            tool_output_json = json.dumps(tool_output, ensure_ascii=False, indent=2)
            result = ResponseFormat.success(content=tool_output_json)
            
            return JsonRpcFormat.success(msg_id=msg_id, result=result)
            
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            
            return JsonRpcFormat.error(msg_id=msg_id, error=str(e))
    
    # ---- ping ----
    elif method == "ping":
        return JsonRpcFormat.success(msg_id=msg_id, result={})
    
    # ---- Unknown method ----
    else:
        return JsonRpcFormat.error(msg_id=msg_id, error=f"Method not found: {method}")
        

# ============================================================
# Streamable HTTP 엔드포인트 - /mcp
# ============================================================

@app.post("/mcp")
async def mcp_post(request: Request):
    """
    POST /mcp - 클라이언트가 서버로 메시지 전송
    
    - JSON-RPC request → JSON 또는 SSE 응답
    - JSON-RPC notification/response → 202 Accepted
    """
    # Accept 헤더 확인
    accept_header = request.headers.get("accept", "")
    session_id = request.headers.get("mcp-session-id")
    
    try:
        body = await request.json()
        logger.info(f"POST /mcp - Body: {json.dumps(body, indent=2)}")
        
        # 배치 요청 처리
        if isinstance(body, list):
            responses = []
            for msg in body:
                response = await process_mcp_message(msg, session_id)
                if response:  # notification은 None 반환
                    responses.append(response)
            
            if not responses:
                return Response(status_code=202)
            
            return JSONResponse(
                content=responses if len(responses) > 1 else responses[0],
                headers={"Content-Type": "application/json"}
            )
        
        # 단일 메시지 처리
        method = body.get("method")
        
        # notification 또는 response인 경우
        if body.get("id") is None or method in ["notifications/initialized", "notifications/cancelled"]:
            await process_mcp_message(body, session_id)
            return Response(status_code=202)
        
        # request인 경우 - 응답 생성
        response = await process_mcp_message(body, session_id)
        
        # initialize 요청인 경우 세션 ID 생성
        response_headers = {"Content-Type": "application/json"}
        if method == "initialize":
            new_session_id = session_manager.create_session()
            response_headers["Mcp-Session-Id"] = new_session_id
        
        # SSE 스트림 응답 지원 (Accept 헤더에 text/event-stream 포함 시)
        """
        if "text/event-stream" in accept_header:
            async def generate_sse():
                # 응답 전송
                yield {
                    "event": "message",
                    "data": json.dumps(response)
                }
                
                # 서버에서 추가 메시지가 있다면 여기서 전송
                # (예: 진행 상황 업데이트 등)
            
            return EventSourceResponse(
                generate_sse(),
                headers=response_headers
            )
        """
        
        # 일반 JSON 응답
        return JSONResponse(content=response, headers=response_headers)
    
    except json.JSONDecodeError:
        return JSONResponse(
            content=JsonRpcFormat.error(msg_id=None, error="Parse error"),
            status_code=400
        )
            
    except Exception as e:
        logger.error(f"POST /mcp error: {e}", exc_info=True)
        return JSONResponse(
            content=JsonRpcFormat.error(msg_id=None, error=str(e)),
            status_code=500
            )

@app.get("/mcp")
async def mcp_get(request: Request):
    """
    GET /mcp - 서버가 클라이언트로 메시지 푸시 (SSE 스트림)
    
    - 서버 주도 알림/요청 전송용
    - 클라이언트는 이 스트림을 열어두고 서버 메시지 수신
    """
    accept_header = request.headers.get("accept", "")
    session_id = request.headers.get("mcp-session-id")
    
    # Accept 헤더 검증
    if "text/event-stream" not in accept_header:
        return Response(
            status_code=405,
            headers={"Allow": "POST"}
        )
    
    # 세션 검증 (선택적)
    if session_id and not session_manager.get_session(session_id):
        return Response(status_code=404)
    
    async def event_generator():
        """SSE 이벤트 생성기"""
        event_id = 0
        queue = session_manager.get_queue(session_id) if session_id else asyncio.Queue()
        
        try:
            while True:
                # 연결 확인
                if await request.is_disconnected():
                    logger.info(f"SSE disconnected: {session_id}")
                    break
                
                try:
                    # 큐에서 메시지 대기 (30초 타임아웃)
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    event_id += 1
                    
                    yield {
                        "event": "message",
                        "id": str(event_id),
                        "data": json.dumps(message)
                    }
                    
                except asyncio.TimeoutError:
                    # Keep-alive (주석 형태로 전송)
                    yield {"comment": "keep-alive"}
                    
        except asyncio.CancelledError:
            logger.info(f"SSE cancelled: {session_id}")
    
    return EventSourceResponse(
        event_generator(),
        headers={"Cache-Control": "no-cache"}
    )

@app.delete("/mcp")
async def mcp_delete(request: Request):
    """
    DELETE /mcp - 세션 종료
    
    클라이언트가 세션을 명시적으로 종료할 때 사용
    """
    session_id = request.headers.get("mcp-session-id")
    
    if not session_id:
        return Response(status_code=400)
    
    if session_manager.delete_session(session_id):
        return Response(status_code=204)
    else:
        return Response(status_code=404)

@app.options("/mcp")
async def mcp_options():
    """OPTIONS /mcp - CORS preflight"""
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Accept, Mcp-Session-Id",
            "Access-Control-Expose-Headers": "Mcp-Session-Id"
        }
    )


# ============================================================
# 보조 엔드포인트 (선택적)
# ============================================================

@app.get("/")
async def root():
    """루트 - 서버 정보"""
    return {
        "name": "shopping-advisor-mcp-server",
        "version": "0.1.0",
        "protocol": "streamable-http",
        "mcp_endpoint": "/mcp"
    }


@app.get("/health")
async def health():
    """헬스 체크"""
    return {"status": "healthy"}


@app.get("/.well-known/mcp.json")
async def mcp_manifest():
    """MCP 서버 매니페스트"""
    return {
        "name": "Shopping Advisor MCP Server",
        "description": "온라인 쇼핑 의사결정을 돕는 MCP 서버",
        "version": "0.1.0",
        "protocol": "streamable-http",
        "endpoint": "/mcp",
        "tools": TOOLS_INFO
    }


# ============================================================
# 메인 실행
# ============================================================
if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("SERVER_PORT", 8000)),
        log_level="info"
    )