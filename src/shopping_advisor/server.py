""" Streamable HTTP 전송을 지원하는 MCP 서버

- 단일 엔드포인트 (/mcp)에서 GET/POST 모두 처리
- 세션 없이 요청-응답 패턴으로 동작
- POST: JSON-RPC 메시지 (클라이언트 → 서버)
- GET: SSE 스트림 (서버 → 클라이언트)
"""

import os
import uvicorn
import logging
import asyncio
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
    allow_headers=["*"]
)


# ============================================================
# Tool 실행 함수
# ============================================================

async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """ Tool 실행 로직 """
    
    # tool 유효성 검사
    if not tool_name:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    try:
        if tool_name == "get_product":
            product_name = arguments.get("product_name", "")

            # 제품명 유효성 검사
            if not product_name:
                raise HTTPException(status_code=400, detail="제품명을 입력해주세요.")
            
            # 제품 정보
            product_json = await get_product(product_name=product_name)
            result = MarkdownFormat.product_info(product_json)
            
        elif tool_name == "create_shopping_guide":
            product_name = arguments.get("product_name", "")

            # 제품명 유효성 검사
            if not product_name:
                raise HTTPException(status_code=400, detail="제품명을 입력해주세요.")
            
            # 쇼핑 가이드
            shopping_guide_json = await create_shopping_guide(product_name=product_name)
            result = MarkdownFormat.shopping_guide(shopping_guide_json)
        
        elif tool_name == "compare_products":
            product_list = arguments.get("product_list", [])
            comparison_points = arguments.get("comparison_points", [])

            # 제품 리스트 유효성 검사
            if not product_list or not isinstance(product_list, list):
                raise HTTPException(status_code=400, detail="제품명을 입력해주세요.")
            
            # 제품 비교
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

async def process_mcp_message(body: dict) -> dict:
    """ MCP JSON-RPC 메시지 처리 """
    method = body.get("method")
    params = body.get("params", {})
    msg_id = body.get("id")
    
    logger.info(f"Processing method: {method}, id: {msg_id}")
    
    # ---- initialize ----
    if method == "initialize":
        initialize_info = {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {}
                },
                "serverInfo": {
                    "name": "shopping-advisor",
                    "version": "0.1.0"
                }
            }
        return JsonRpcFormat.success(msg_id=msg_id, result=initialize_info)
    
    # ---- notifications/initialized ----
    elif method == "notifications/initialized":
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
    """ POST /mcp - 클라이언트가 서버로 메시지 전송 (Stateless) """
    try:
        body = await request.json()
        logger.info(f"POST /mcp - Body: {json.dumps(body, indent=2)}")
        
        # 배치 요청 처리
        if isinstance(body, list):
            responses = []
            for msg in body:
                response = await process_mcp_message(msg)
                if response:
                    responses.append(response)
            
            if not responses:
                return Response(status_code=202)
            
            return JSONResponse(
                content=responses if len(responses) > 1 else responses[0],
                headers={"Content-Type": "application/json"}
            )
        
        # 단일 메시지 처리
        method = body.get("method")
        
        # notification인 경우
        if body.get("id") is None or method in ["notifications/initialized", "notifications/cancelled"]:
            await process_mcp_message(body)
            return Response(status_code=202)
        
        # request인 경우 - 응답 생성
        response = await process_mcp_message(body)
        
        # 일반 JSON 응답
        return JSONResponse(
            content=response, 
            headers={"Content-Type": "application/json"}
        )
    
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
    """ GET /mcp - Streamable HTTP (SSE)
    
    - Stateless
    - 서버는 상태를 저장하지 않음
    - 연결 유지 + keep-alive만 제공
    """
    accept_header = request.headers.get("accept", "")

    if "text/event-stream" not in accept_header:
        return Response(
            status_code=406,
            headers={"Allow": "POST"}
        )

    async def event_generator():
        try:
            while not await request.is_disconnected():
                await asyncio.sleep(30)
                yield {"comment": "keep-alive"}

        except asyncio.CancelledError:
            logger.info("SSE connection cancelled")

    return EventSourceResponse(
        event_generator(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.options("/mcp")
async def mcp_options():
    """ OPTIONS /mcp - CORS preflight """
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Accept",
        }
    )


# ============================================================
# 보조 엔드포인트
# ============================================================

@app.get("/")
async def root():
    """ 루트 - 서버 정보 """
    return {
        "name": "shopping-advisor-mcp-server",
        "version": "0.1.0",
        "protocol": "streamable-http",
        "mcp_endpoint": "/mcp"
    }

@app.get("/health")
async def health():
    """ 헬스 체크 """
    return {"status": "healthy"}

@app.get("/.well-known/mcp.json")
async def mcp_manifest():
    """ MCP 서버 매니페스트 """
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