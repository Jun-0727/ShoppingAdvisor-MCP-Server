"""URL 생성기 수동 테스트"""

import sys
from pathlib import Path

# 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from shopping_advisor.utils.shopping_mall import (
    generate_shopping_url,
    get_mall_all,
    get_mall_detail,
    get_mall_feature,
    get_mall_pros_cons,
    get_mall_best_for
)


def test_generate_url():
    """URL 생성 테스트"""
    print("\n" + "=" * 60)
    print("테스트 1: URL 생성")
    print("=" * 60)
    
    mall = input("쇼핑몰 이름 (예: 쿠팡): ").strip() or "쿠팡"
    product = input("제품명 (예: 오리발): ").strip() or "오리발"
    
    print(f"\n🔍 {mall}에서 '{product}' 검색 URL 생성 중...\n")
    
    url = generate_shopping_url(mall, product)
    
    if url:
        print(f"✅ 성공!")
        print(f"URL: {url}")
    else:
        print(f"❌ 실패")


def test_available_malls():
    """사용 가능한 쇼핑몰 목록 테스트"""
    print("\n" + "=" * 60)
    print("테스트 3: 사용 가능한 쇼핑몰 목록")
    print("=" * 60)

    malls = get_mall_all()

    print(f"\n총 {len(malls)}개의 쇼핑몰 지원:\n")
    
    for i, mall in enumerate(malls, 1):
        info = get_mall_detail(mall)
        description = info.get("description", "") if info else ""
        print(f"{i:2d}. {mall:15s} - {description}")


def test_mall_info():
    """쇼핑몰 정보 조회 테스트"""
    print("\n" + "=" * 60)
    print("테스트 4: 쇼핑몰 정보 조회")
    print("=" * 60)
    
    mall = input("쇼핑몰 이름 (예: 쿠팡): ").strip() or "쿠팡"
    
    info = get_mall_detail(mall)
    
    if info:
        print(f"\n✅ {mall} 정보:")
        print(f"   이름: {info['name']}")
        print(f"   URL 템플릿: {info['url_template']}")
        print(f"   인코딩: {info['encoding']}")
        print(f"   설명: {info['description']}")
    else:
        print(f"\n❌ '{mall}' 쇼핑몰을 찾을 수 없습니다.")


def main():
    """메인 메뉴"""
    while True:
        print("\n" + "=" * 60)
        print("쇼핑몰 URL 생성기 테스트 메뉴")
        print("=" * 60)
        print("1. 단일 URL 생성")
        print("2. 사용 가능한 쇼핑몰 목록")
        print("3. 쇼핑몰 정보 조회")
        print("4. 종료")
        print("=" * 60)
        
        choice = input("\n선택 (1-4): ").strip()
        
        if choice == "1":
            test_generate_url()
        elif choice == "2":
            test_available_malls()
        elif choice == "3":
            test_mall_info()
        elif choice == "4":
            print("\n👋 종료합니다.")
            break
        else:
            print("\n⚠️  잘못된 선택입니다.")


if __name__ == "__main__":
    print("\n🚀 쇼핑몰 URL 생성기 테스트 시작\n")
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 사용자에 의해 종료되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()