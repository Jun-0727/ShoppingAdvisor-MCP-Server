import os
import json
import asyncio

from dotenv import load_dotenv
from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ValidationError
from openai import AsyncOpenAI

from utils.prompt_template import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

# ============================================================================
# API 클라이언트 초기화
# ============================================================================

# 환경변수에서 API 키 로드
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# AsyncOpenAI 클라이언트 생성
client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


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
    """외부 API를 통해 제품 정보를 조회합니다."""
    
    # API Key 확인
    if not client:
        raise ValueError("API KEY가 조회되지 않습니다.")
        return None
    
    try:
        # 사용자 프롬프트 생성
        user_prompt = USER_PROMPT_TEMPLATE.format(product_name=product_name)

        # GPT API 호출
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
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



# ============================================================================
# FastMCP 서버 초기화
# ============================================================================

mcp = FastMCP("shopping-advisor")


# ============================================================================
# 메인 함수 MCP Tools (주요 기능)
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
    
    
# 실행
#if __name__ == "__main__":
#    
#    # 테스트 실행
#    asyncio.run(get_product("무선 이어폰"))

