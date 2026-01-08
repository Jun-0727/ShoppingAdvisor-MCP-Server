import os
import json
import asyncio

from dotenv import load_dotenv
from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ValidationError

from .utils.product_api import product_info_request

# ============================================================================
# FastMCP 서버 초기화
# ============================================================================

mcp = FastMCP("shopping-advisor")


# ============================================================================
# MCP Tools (주요 기능)
# ============================================================================

@mcp.tool(name="get_product", description="제품명 또는 카테고리를 기반으로 제품의 특징, 장점, 단점, 구매 시 확인사항을 제공합니다.")
async def get_product(product_name: str) -> Optional[dict]:
    
    result = await product_info_request(product_name)

    # API 레이트 리밋 방지
    await asyncio.sleep(1)

    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    else:
        print("정보 조회 실패")
        return None
    

def main():
    """MCP 서버 실행"""
    mcp.run()