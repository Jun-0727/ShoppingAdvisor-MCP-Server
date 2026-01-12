"""GPT API 수동 테스트 스크립트.

직접 실행하여 API 응답을 확인합니다.
"""

import asyncio
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# .env 로드
load_dotenv(project_root / ".env")

from shopping_advisor.utils.gpt_api import product_info_request, mall_recommend_request


async def test_get_product():
    """제품 정보 조회 테스트"""
    print("=" * 60)
    print("제품 정보 조회 테스트")
    print("=" * 60)
    
    product = input("제품명을 입력하세요 (예: 마샬 스피커): ")
    
    print(f"\n🔍 '{product}' 정보 조회 중...")

    result = await product_info_request(product)
    
    if result:
        print("\n✅ 조회 성공!")
        print("\n" + json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\n❌ 조회 실패")


async def test_recommend_mall():
    """단일 제품 테스트"""
    print("=" * 60)
    print("쇼핑몰 추천 테스트")
    print("=" * 60)
    
    product = input("제품명을 입력하세요 (예: 마샬 스피커): ")
    
    print(f"\n🔍 '{product}' 쇼핑몰 추천 중...")
    result = await mall_recommend_request(product)
    
    if result:
        print("\n✅ 조회 성공!")
        print("\n" + json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\n❌ 조회 실패")

async def main():
    """메인 메뉴"""
    while True:
        print("\n" + "=" * 60)
        print("GPT API 테스트 메뉴")
        print("=" * 60)
        print("1. 제품 정보 조회 테스트")
        print("2. 쇼핑몰 추천 테스트")
        print("3. 종료")
        print("=" * 60)
        
        choice = input("\n선택 (1-3): ")
        
        if choice == "1":
            await test_get_product()
        elif choice == "2":
            await test_recommend_mall()
        elif choice == "3":
            print("\n👋 종료합니다.")
            break
        else:
            print("\n⚠️  잘못된 선택입니다.")


if __name__ == "__main__":
    print("\n🚀 GPT-4 API 수동 테스트 시작\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 사용자에 의해 종료되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")