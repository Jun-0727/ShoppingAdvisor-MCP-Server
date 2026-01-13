import os
import json

from dotenv import load_dotenv
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ValidationError
from openai import AsyncOpenAI

from ..utils.prompt_template import (
    GET_PRODUCT_SYSTEM_PROMPT,
    GET_PRODUCT_USER_PROMPT,
    RECOMMEND_SHOPPING_MALL_SYSTEM_PROMPT,
    RECOMMEND_SHOPPING_MALL_USER_PROMPT,
    COMPARE_PRODUCTS_SYSTEM_PROMPT,
    COMPARE_PRODUCTS_USER_PROMPT
)

# ============================================================================
# API 클라이언트 초기화
# ============================================================================

# 환경변수에서 API 키 로드
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# AsyncOpenAI 클라이언트 생성
client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

GPT_MODEL = "gpt-4o"

# ============================================================================
# Pydantic Models
# ============================================================================

class ProductInfo(BaseModel):
    """제품 정보 응답 모델"""
    features: list[str] = Field(
        description="제품의 주요 특징"
    )
    pros: list[str] = Field(
        description="제품의 장점"
    )
    cons: list[str] = Field(
        description="제품의 단점 또는 주의사항"
    )
    purchase_notes: list[str] = Field(
        description="구매 전 확인사항"
    )


# ============================================================================
# 메인 함수
# ============================================================================

async def product_info_request(product_name: str) -> Optional[dict]:
    """
    외부 API를 통해 제품 정보를 조회합니다.
    
    Args:
        product_name (str): 제품명 또는 카테고리 이름

    Returns:
        Optional[dict]: 제품 정보 딕셔너리 또는 None if 실패
    """
    
    # API Key 확인
    if not client:
        raise ValueError("API KEY가 조회되지 않습니다.")
        return None
    
    try:
        # 사용자 프롬프트 생성
        user_prompt = GET_PRODUCT_USER_PROMPT.format(product_name=product_name)

        # GPT API 호출
        response = await client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": GET_PRODUCT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,  # 창의성과 일관성 균형
            max_tokens=1000,  # 충분한 응답 길이
            response_format={"type": "json_object"}  # JSON 모드 활성화
        )

        # 응답 추출
        content = response.choices[0].message.content

        # JSON 파싱
        parsed_data = json.loads(content)

        # Pydantic 모델로 검증
        validated_data = ProductInfo(**parsed_data)

        # 검증된 데이터를 딕셔너리로 반환
        return validated_data.model_dump()

    except json.JSONDecodeError as e:
        print(f"Error: JSON 파싱 실패 - {e}")
        print(f"응답 내용: {content}")
        return None
    
    except ValidationError as e:
        print(f"Error: 데이터 검증 실패 - {e}")
        return None

    except Exception as e:
        print(f"Error: API 호출 중 오류 발생 - {type(e).__name__}: {e}")
        return None


async def mall_recommend_request(product_name: str) -> Optional[dict]:
    """
    제품을 어디서 사는 것이 좋은지 쇼핑몰을 추천합니다.

    Args:
        product_name (str): 제품명 또는 카테고리 이름

    Returns:
        Optional[dict]: 쇼핑몰 추천 정보 딕셔너리 또는 None if 실패
    """
    
    # API Key 확인
    if not client:
        raise ValueError("API KEY가 조회되지 않습니다.")
        return None
    
    try:
        # 사용자 프롬프트 생성
        user_prompt = RECOMMEND_SHOPPING_MALL_USER_PROMPT.format(product_name=product_name)

        # GPT API 호출
        response = await client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": RECOMMEND_SHOPPING_MALL_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,  # 창의성과 일관성 균형
            max_tokens=1000,  # 충분한 응답 길이
            response_format={"type": "json_object"}  # JSON 모드 활성화
        )

        # 응답 추출
        content = response.choices[0].message.content

        # JSON 파싱
        parsed_data = json.loads(content)

        return parsed_data

    except json.JSONDecodeError as e:
        print(f"Error: JSON 파싱 실패 - {e}")
        print(f"응답 내용: {content}")
        return None

    except Exception as e:
        print(f"Error: API 호출 중 오류 발생 - {type(e).__name__}: {e}")
        return None


async def compare_products_request(product_names: List[str],comparison_points: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """N개 제품을 GPT API로 비교 분석합니다.

    Args:
        product_names (List[str]): 비교할 제품명 리스트 (최소 2개)
        comparison_points (Optional[List[str]]): 비교하고 싶은 특정 항목들 (선택사항)
            예: ["가격", "성능", "디자인", "배터리"]

    Returns:
        Optional[Dict[str, Any]]: 제품 비교 결과 딕셔너리 또는 None (실패 시)

    Example:
        >>> result = await compare_products_request(
        ...     ["아이폰15", "갤럭시 S24"],
        ...     comparison_points=["카메라", "배터리", "가격"]
        ... )
        >>> print(result['overall_summary'])
    """
    
    # 입력 검증
    if not product_names or len(product_names) < 2:
        print("Error: 최소 2개 이상의 제품이 필요합니다.")
        return None
    
    # API Key 확인
    if not client:
        raise ValueError("API KEY가 조회되지 않습니다.")
    
    try:
        # 제품 목록 포맷팅
        products_list = "\n".join([f"{i+1}. {name}" for i, name in enumerate(product_names)])
        
        # 사용자 프롬프트 생성
        user_prompt = COMPARE_PRODUCTS_USER_PROMPT.format(products_list=products_list)
        
        # 특정 비교 항목이 지정된 경우 추가
        if comparison_points:
            points_text = ", ".join(comparison_points)
            user_prompt += f"\n\n**특히 다음 항목들을 중점적으로 비교해주세요:**\n{points_text}"
        
        # GPT API 호출
        response = await client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": COMPARE_PRODUCTS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,    # 창의성과 일관성 균형
            max_tokens=2500,    # 충분한 응답 길이
            response_format={"type": "json_object"}
        )
        
        # 응답 추출
        content = response.choices[0].message.content
        
        # JSON 파싱
        parsed_data = json.loads(content)
        
        return parsed_data
        
    except json.JSONDecodeError as e:
        print(f"Error: JSON 파싱 실패 - {e}")
        print(f"응답 내용: {content}")
        return None
        
    except Exception as e:
        print(f"Error: API 호출 중 오류 발생 - {type(e).__name__}: {e}")
        return None

