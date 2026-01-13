import asyncio
import logging

from dotenv import load_dotenv
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ValidationError

from .logging_config import setup_logging

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

ERROR_MESSAGE = "잠시 후 다시 시도해주세요."

# 로깅 설정
setup_logging(log_level="INFO")
logger = logging.getLogger(__name__)

# FastMCP 서버 초기화
mcp = FastMCP("shopping-advisor")


# ============================================================================
# MCP Tools (주요 기능)
# ============================================================================

@mcp.tool(name="get_product")
async def get_product(product_name: str) -> Optional[dict]:
    """제품명 또는 카테고리를 기반으로 제품의 특징, 장점, 단점, 구매 시 확인사항을 제공합니다."""
    
    logger.info(f"제품 정보 조회 시작: {product_name}")
    
    try:
        product_info = await product_info_request(product_name)
        
        # API 레이트 리밋 방지
        await asyncio.sleep(1)

        result = format_product_info_response(product_data=product_info)
        
        if result:
            logger.info(f"제품 정보 조회 성공: {product_name}")
            return result
        else:
            logger.warning(f"제품 정보 조회 실패: {product_name}")
            return None
    
    except Exception as e:
        logger.error(f"제품 정보 조회 중 오류 발생: {product_name}", exc_info=True)
        return ERROR_MESSAGE



@mcp.tool(name="create_shopping_guide")
async def create_shopping_guide(product_name: str) -> Optional[dict]:
    """제품명을 기반으로 제품 구매 가이드를 제공합니다."""
    
    logger.info(f"쇼핑 가이드 생성 시작: {product_name}")

    try:
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
            logger.info(f"쇼핑 가이드 생성 성공: {product_name}")
            return result
        else:
            logger.warning(f"쇼핑 가이드 생성 실패: {product_name}")
            return None
            
    except Exception as e:
        logger.error(f"쇼핑 가이드 생성 중 오류 발생: {product_name}", exc_info=True)
        return ERROR_MESSAGE


@mcp.tool(name="compare_products")
async def compare_products(product_names: List[str],comparison_points: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """제품명을 기반으로 N개의 제품을 비교 및 요약 정보를 제공합니다. """
    
    logger.info(f"제품 비교 시작: {', '.join(product_names)}")

    try:
        comparison_data = await compare_products_request(product_names, comparison_points)

        # API 레이트 리밋 방지
        await asyncio.sleep(1)

        result = format_comparison_response(comparison_data=comparison_data)

        if result:
            logger.info(f"제품 비교 성공: {', '.join(product_names)}")
            return result
        else:
            logger.warning(f"제품 비교 실패: {', '.join(product_names)}")
            return None
            
    except Exception as e:
        logger.error(f"제품 비교 중 오류 발생: {', '.join(product_names)}", exc_info=True)
        return ERROR_MESSAGE



def main():
    """MCP 서버 실행"""
    logger.info("Smart Shopping Advisor MCP Server 시작")
    try:
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("서버 종료 (사용자 인터럽트)")
    except Exception as e:
        logger.error("서버 실행 중 오류 발생", exc_info=True)
        raise


if __name__ == "__main__":
    main()

