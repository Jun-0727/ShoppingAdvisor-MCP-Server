"""GPT-4 API 수동 테스트 스크립트

직접 실행하여 API 응답을 확인할 수 있습니다.
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


from shopping_advisor.server import product_info_request

async def test_single_product():
    """단일 제품 테스트"""
    print("=" * 60)
    print("단일 제품 테스트")
    print("=" * 60)
    
    product = input("제품명을 입력하세요 (예: 마샬 스피커): ")
    
    print(f"\n🔍 '{product}' 정보 조회 중...")

    result = await product_info_request(product)
    
    if result:
        print("\n✅ 조회 성공!")
        print("\n" + json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\n❌ 조회 실패")


async def test_multiple_products():
    """여러 제품 테스트"""
    print("=" * 60)
    print("여러 제품 배치 테스트")
    print("=" * 60)
    
    test_products = [
        "마샬 블루투스 스피커",
        "아이폰17",
        "노트북",
        "에어프라이어"
    ]
    
    for product in test_products:
        print(f"\n{'='*60}")
        print(f"테스트: {product}")
        print('='*60)
        
        result = await product_info_request(product)
        
        if result:
            print("\n✅ 성공")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("\n❌ 실패")
        
        # API 레이트 리밋 방지
        await asyncio.sleep(2)


async def test_custom_products():
    """사용자 정의 제품 리스트 테스트"""
    print("=" * 60)
    print("사용자 정의 제품 테스트")
    print("=" * 60)
    
    products_input = input("테스트할 제품들을 쉼표로 구분하여 입력: ")
    products = [p.strip() for p in products_input.split(",")]
    
    for product in products:
        print(f"\n🔍 {product} 조회 중...")
        result = await product_info_request(product)
        
        if result:
            print(f"✅ {product}: 성공")
            print(f"  특징: {len(result['features'])}개")
            print(f"  장점: {len(result['pros'])}개")
            print(f"  단점: {len(result['cons'])}개")
        else:
            print(f"❌ {product}: 실패")
        
        await asyncio.sleep(1)


async def main():
    """메인 메뉴"""
    while True:
        print("\n" + "=" * 60)
        print("GPT-4 API 테스트 메뉴")
        print("=" * 60)
        print("1. 단일 제품 테스트")
        print("2. 여러 제품 배치 테스트")
        print("3. 사용자 정의 제품 테스트")
        print("4. 종료")
        print("=" * 60)
        
        choice = input("\n선택 (1-4): ")
        
        if choice == "1":
            await test_single_product()
        elif choice == "2":
            await test_multiple_products()
        elif choice == "3":
            await test_custom_products()
        elif choice == "4":
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