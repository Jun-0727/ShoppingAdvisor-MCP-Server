import os
import json
import asyncio

from dotenv import load_dotenv
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ValidationError

from .utils.gpt_api import (
    product_info_request, 
    mall_recommend_request, 
    compare_products_request
)

from .utils.formatter import (
    format_product_info_response, 
    format_shopping_guide_response, 
    format_comparison_response
)

# FastMCP 서버 초기화
mcp = FastMCP("shopping-advisor")


# ============================================================================
# MCP Tools (주요 기능)
# ============================================================================

@mcp.tool(name="get_product")
async def get_product(product_name: str) -> Optional[dict]:
    
    product_info = await product_info_request(product_name)
    
    # API 레이트 리밋 방지
    await asyncio.sleep(1)

    result = format_product_info_response(product_data=product_info)
    
    if result:
        # print(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    else:
        # print("정보 조회 실패")
        return None


@mcp.tool(name="create_shopping_guide")
async def create_shopping_guide(product_name: str) -> Optional[dict]:
    """제품에 대한 쇼핑 가이드를 생성합니다."""
    
    # 제품 정보 조회
    product_info = await product_info_request(product_name)
    
    # 추천 쇼핑몰
    recommend_mall = await mall_recommend_request(product_name)

    # LLM을 사용하여 최종 가이드 생성 (예시 구현)
    guide = {
        "product_info": product_info,
        "mall_info": recommend_mall,
    }

    result = format_shopping_guide_response(guide_data=guide)

    if result:
        # print(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    else:
        # print("정보 조회 실패")
        return None


@mcp.tool(name="compare_products")
async def compare_products(product_names: List[str],comparison_points: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    
    comparison_data = await compare_products_request(product_names, comparison_points)

    result = format_comparison_response(comparison_data=comparison_data)

    # API 레이트 리밋 방지
    await asyncio.sleep(1)

    if result:
        # print(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    else:
        # print("정보 조회 실패")
        return None


def main():
    """MCP 서버 실행"""
    print("Smart Shopping Advisor MCP Server 실행중...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

