import asyncio
import logging

from dotenv import load_dotenv
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP
from fastapi import FastAPI

from ..logging_config import setup_logging

from .gpt_api import (
    product_info_request, 
    mall_recommend_request, 
    compare_products_request
)

ERROR_MESSAGE = "잠시 후 다시 시도해주세요."

TOOLS_INFO = [
    {
        "name": "get_product",
        "description": "제품명을 기반으로 제품의 특징, 장점, 단점, 구매 시 확인사항을 제공합니다.",
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
        "description": "제품 구매 가이드를 생성하여 선택 기준, 주의사항, 추천 쇼핑몰 등을 제공합니다.",
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
        "description": "2개 이상의 제품을 비교하여 각 제품의 장단점, 사양 비교, 사용 사례별 추천을 제공합니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "비교할 제품명 리스트 (최소 2개)"
                },
                "comparison_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "(선택사항) 비교할 특정 항목 리스트"
                }
            },
            "required": ["product_list"]
        }
    }
]

# 로깅 설정
setup_logging(log_level="INFO")
logger = logging.getLogger(__name__)

# FastMCP 서버 초기화
mcp = FastMCP("shopping-advisor")


# ============================================================================
# MCP Tools (주요 기능)
# ============================================================================

@mcp.tool(name="get_product", description="제품명을 기반으로 제품의 특징, 장점, 단점, 구매 시 확인사항을 제공합니다.")
async def get_product(product_name: str) -> Optional[dict]:
    """
    제품 정보를 조회하여 구매 결정에 필요한 핵심 정보를 제공합니다.
    
    - 제품의 주요 특징 및 사양
    - 장점 (Pros): 제품의 강점과 우수한 점
    - 단점 (Cons): 제품의 약점과 개선이 필요한 점
    - 구매 시 확인사항: 구매 전 반드시 체크해야 할 항목들
    
    Args:
        product_name: 조회할 제품의 이름 또는 카테고리 (예: "iPhone 15", "노트북", "무선 이어폰")
    
    Returns:
        제품 정보를 포함한 딕셔너리 또는 제품을 찾을 수 없는 경우 None

    """
    
    logger.info(f"제품 정보 조회 시작: {product_name}")
    
    try:
        product = await product_info_request(product_name)
        
        # API 레이트 리밋 방지
        await asyncio.sleep(1)
        
        if product:
            logger.info(f"제품 정보 조회 성공: {product_name}")
            return product
        else:
            logger.warning(f"제품 정보 조회 실패: {product_name}")
            return None
    
    except Exception as e:
        logger.error(f"제품 정보 조회 중 오류 발생: {product_name}", exc_info=True)
        return ERROR_MESSAGE


@mcp.tool(name="create_shopping_guide", description="제품명을 기반으로 구매 가이드를 생성하여 선택 기준, 주의사항, 추천 쇼핑몰 등을 제공합니다.")
async def create_shopping_guide(product_name: str) -> Optional[dict]:
    """
    제품명을 기반으로 제품 구매 가이드를 제공합니다.
    
    Args:
        product_name: 구매 가이드를 생성할 제품명 (예: "4K 모니터", "공기청정기", "커피머신")
    
    Returns:
        구매 가이드 정보를 포함한 딕셔너리 또는 가이드 생성 실패 시 None
        
    """
    
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

        if guide:
            logger.info(f"쇼핑 가이드 생성 성공: {product_name}")
            return guide
        else:
            logger.warning(f"쇼핑 가이드 생성 실패: {product_name}")
            return None
            
    except Exception as e:
        logger.error(f"쇼핑 가이드 생성 중 오류 발생: {product_name}", exc_info=True)
        return ERROR_MESSAGE


@mcp.tool(name="compare_products", description="2개 이상의 제품을 비교하여 각 제품의 장단점, 사양 비교, 사용 사례별 추천, 가성비 분석을 제공합니다.")
async def compare_products(product_list: List[str],comparison_points: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """
    여러 제품을 비교 분석하여 각 제품의 상대적 장단점과 추천 사항을 제공합니다.
    
    Args:
        product_names: 비교할 제품명 리스트 (최소 2개, 권장 2-5개)
            예: ["iPhone 15", "Galaxy S24"]
        
        comparison_points: (선택사항) 비교할 특정 항목 리스트
            예: ["카메라 성능", "배터리 수명", "가격"]
            None인 경우 제품 카테고리에 적합한 기본 비교 항목 사용
    
    Returns:
        비교 분석 결과를 포함한 딕셔너리 또는 비교 실패 시 None
        
    Notes:
        - 너무 많은 제품(5개 초과)을 비교하면 결과가 복잡할 수 있습니다
        - 서로 다른 카테고리의 제품 비교는 의미 있는 결과를 제공하지 못할 수 있습니다
    """
    
    logger.info(f"제품 비교 시작: {', '.join(product_list)}")

    try:
        comparison_data = await compare_products_request(product_list, comparison_points)

        # API 레이트 리밋 방지
        await asyncio.sleep(1)

        if comparison_data:
            logger.info(f"제품 비교 성공: {', '.join(product_list)}")
            return comparison_data
        else:
            logger.warning(f"제품 비교 실패: {', '.join(product_list)}")
            return None
            
    except Exception as e:
        logger.error(f"제품 비교 중 오류 발생: {', '.join(product_list)}", exc_info=True)
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

