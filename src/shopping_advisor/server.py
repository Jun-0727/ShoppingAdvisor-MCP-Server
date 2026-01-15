"""
HTTP 전송을 지원하는 MCP 서버
"""
from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from .utils.tool import get_product, create_shopping_guide, compare_products

import uvicorn
import os
import logging
import json
from typing import Any, Dict
from .utils.formatter import (
    format_product_info_response, 
    format_shopping_guide_response, 
    format_comparison_response,
    format_error_response
)

# 로깅 설정
from .logging_config import setup_logging
setup_logging(log_level="INFO")
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="Shopping Advisor MCP Server",
    description="Smart shopping decision support MCP server",
    version="0.1.0"
)

# CORS 설정
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

MCP_TOOLS = {
    "get_product": get_product,
    "create_shopping_guide": create_shopping_guide,
    "compare_products": compare_products,
}

TOOLS_INFO = [
            {
                "name": "get_product",
                "description": "제품명을 기반으로 제품의 특징, 장점, 단점, 구매 시 확인사항을 제공합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_name": {
                            "type": "string",
                            "description": "조회할 제품의 이름 또는 카테고리 (예: 'iPhone 15', '노트북', '무선 이어폰')"
                        }
                    },
                    "required": ["product_name"]
                }
            },
            {
                "name": "create_shopping_guide",
                "description": "제품 구매 가이드를 생성하여 선택 기준, 주의사항, 추천 쇼핑몰 등을 제공합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_name": {
                            "type": "string",
                            "description": "구매 가이드를 생성할 제품명 (예: '4K 모니터', '공기청정기', '커피머신')"
                        }
                    },
                    "required": ["product_name"]
                }
            },
            {
                "name": "compare_products",
                "description": "2개 이상의 제품을 비교하여 각 제품의 장단점, 사양 비교, 사용 사례별 추천을 제공합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_list": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "비교할 제품명 리스트 (최소 2개, 권장 2-5개, 예: ['iPhone 15', 'Galaxy S24'])"
                        },
                        "comparison_points": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "(선택사항) 비교할 특정 항목 리스트 (예: ['카메라 성능', '배터리 수명', '가격'])"
                        }
                    },
                    "required": ["product_list"]
                }
            }
        ]

@app.get("/.well-known/mcp.json")
async def mcp_info():
    return {
        "name": "Smart Shopping Advisor MCP Server",
        "description": "온라인 쇼핑 의사결정을 돕는 MCP 서버",
        "version": "1.0.0",
        "tools": TOOLS_INFO
    }

@app.get("/tools")
def list_tools():
    return {
        "tools": [
            {
                "name": "get_product",
                "description": "제품 정보 조회",
                "input_schema": {
                    "product_name": "string"
                }
            },
            {
                "name": "create_shopping_guide",
                "description": "구매 가이드 생성",
                "input_schema": {
                    "product_name": "string"
                }
            },
            {
                "name": "compare_products",
                "description": "제품 비교",
                "input_schema": {
                    "product_names": ["string"],
                    "comparison_points": ["string"]
                }
            }
        ]
    }

@app.post("/tools/{tool_name}")
async def run_tool(tool_name: str, payload: Dict[str, Any]):
    """MCP Tool을 실행하기 위한 엔드포인트"""

    # 1. Tool 존재 여부 확인
    tool = MCP_TOOLS.get(tool_name)
    if not tool:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found"
        )

    try:
        # 2. Tool별 인자 처리
        if tool_name == "get_product":
            product_name = payload.get("product_name")
            if not product_name:
                raise HTTPException(
                    status_code=400,
                    detail="제품명을 입력해주세요."
                )

            product_info = await tool(product_name=product_name)
            
            result = format_product_info_response(product_data=product_info)


        elif tool_name == "create_shopping_guide":
            product_name = payload.get("product_name")
            if not product_name:
                raise HTTPException(
                    status_code=400,
                    detail="제품명을 입력해주세요."
                )

            guide_data = await tool(product_name=product_name)
            
            result = format_shopping_guide_response(guide_data=guide_data)

        elif tool_name == "compare_products":
            product_list = payload.get("product_list")
            comparison_points = payload.get("comparison_points")

            if not product_list or not isinstance(product_list, list):
                raise HTTPException(
                    status_code=400,
                    detail="제품명을 입력해주세요."
                )

            comparison_data = await tool(product_list=product_list, comparison_points=comparison_points)

            result = format_comparison_response(comparison_data=comparison_data)


        else:
            raise HTTPException(
                status_code=400,
                detail="지원하지 않는 Tool 입니다."
            )

        # 3. 결과 검증
        if result is None:
            return format_error_response(error_message="잠시 후 다시 시도해주세요.")

        return result

    except Exception as e:
        logger.error(f"Error in {tool_name}: {e}", exc_info=True)
        return format_error_response(str(e))


# Health check
@app.get("/health")
async def health():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "shopping-advisor-mcp",
        "version": "0.1.0"
    }

# MCP 메시지 처리 함수
async def process_mcp_message(body: dict) -> dict:
    """MCP 메시지 처리 로직"""
    method = body.get('method')
    params = body.get('params', {})
    
    logger.debug(f"Processing method: {method}")
    logger.debug(f"Params: {json.dumps(params, indent=2)}")
    
    # initialize 메서드
    if method == 'initialize':
        client_protocol = params.get('protocolVersion', '2025-11-25')

        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "protocolVersion": "0.1.0",
                "capabilities": {
                    "tools": {},
                    "prompts": {}
                },
                "serverInfo": {
                    "name": "shopping-advisor",
                    "version": "0.1.0"
                }
            }
        }
    
    # tools/list 메서드
    elif method == 'tools/list':
        tools = TOOLS_INFO
        
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "tools": tools
            }
        }
    
    # tools/call 메서드
    elif method == 'tools/call':
        tool_name = params.get('name')
        arguments = params.get('arguments', {})
        
        result_text = f"도구 '{tool_name}' 실행 완료: {json.dumps(arguments, ensure_ascii=False)}"
        
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": result_text
                    }
                ]
            }
        }
    
    # 알 수 없는 메서드
    else:
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }

# 루트 POST 엔드포인트 - JSON-RPC 메시지 처리
@app.post("/")
async def handle_messages(request: Request):
    """
    MCP JSON-RPC 메시지 처리
    """
    try:
        # Request 정보 로깅
        logger.debug(f"Headers: {dict(request.headers)}")
        
        # Body 읽기
        body_bytes = await request.body()
        logger.debug(f"Raw body: {body_bytes.decode('utf-8')}")
        
        # JSON 파싱
        body = json.loads(body_bytes)
        logger.info(f"Received: {json.dumps(body, indent=2)}")
        
        # 메시지 처리
        response = await process_mcp_message(body)
        logger.info(f"Response: {json.dumps(response, indent=2)}")
        
        return JSONResponse(
            content=response,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "no-cache"
            }
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            }
        )
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
        )

# OPTIONS 요청 처리
@app.options("/")
async def options_root():
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

# Streamable HTTP specific endpoints
@app.post("/message")  # 단수형도 추가
async def handle_message(request: Request):
    return await handle_messages(request)

@app.get("/")
async def root():
    """루트 GET 요청 - 서버 정보 반환"""
    return {
        "name": "shopping-advisor-mcp-server",
        "version": "0.1.0",
        "protocol": "streamable-http",
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv('SERVER_PORT', 8000)),
        log_level="info",
        reload=False
    )