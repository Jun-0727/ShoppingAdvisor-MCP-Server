"""쇼핑몰 URL 생성 유틸리티"""

import json
from pathlib import Path
from typing import Optional, Dict, List
from urllib.parse import quote


# ============================================================================
# 데이터 로드
# ============================================================================

def load_shopping_malls() -> Dict:
    """쇼핑몰 데이터 로드"""
    data_path = Path(__file__).parent.parent / "data" / "shopping_malls.json"
    
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {data_path} 파일을 찾을 수 없습니다.")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error: JSON 파싱 실패 - {e}")
        return {}


# 쇼핑몰 데이터 로드
SHOPPING_MALLS = load_shopping_malls()


# ============================================================================
# 메인 함수
# ============================================================================

def get_mall_all() -> List[str]:
    """쇼핑몰 목록 반환
    
    Returns:
        List[str]: 쇼핑몰 이름 리스트
    """
    return list(SHOPPING_MALLS.keys())


def get_mall_detail(mall_name: str) -> Optional[Dict]:
    """쇼핑몰 정보 조회
    
    Args:
        mall_name (str): 쇼핑몰 이름
        
    Returns:
        Optional[Dict]: 쇼핑몰 정보 또는 None
    """
    return SHOPPING_MALLS.get(mall_name)


def get_mall_pros_cons(mall_name: str) -> Optional[Dict[str, List[str]]]:
    """쇼핑몰 장단점 조회
    
    Args:
        mall_name (str): 쇼핑몰 이름
        
    Returns:
        Optional[Dict[str, List[str]]]: 장단점 딕셔너리 또는 None
    """
    mall_data = SHOPPING_MALLS.get(mall_name)
    
    if not mall_data:
        return None
    
    return {
        "pros": mall_data.get("pros", []),
        "cons": mall_data.get("cons", [])
    }


def get_mall_best_for(mall_name: str) -> Optional[List[str]]:
    """쇼핑몰 추천 카테고리 조회
    
    Args:
        mall_name (str): 쇼핑몰 이름
        
    Returns:
        Optional[List[str]]: 추천 카테고리 리스트 또는 None
    """
    mall_data = SHOPPING_MALLS.get(mall_name)
    
    if not mall_data:
        return None
    
    return mall_data.get("best_for", [])


def get_mall_feature(mall_name: str) -> Optional[str]:
    """쇼핑몰 설명 조회
    
    Args:
        mall_name (str): 쇼핑몰 이름
        
    Returns:
        Optional[str]: 쇼핑몰 설명 또는 None
    """
    mall_data = SHOPPING_MALLS.get(mall_name)
    
    if not mall_data:
        return None
    
    return mall_data.get("description")



def generate_shopping_url(mall_name: str, product_name: str) -> Optional[str]:
    """쇼핑몰 URL 생성
    
    Args:
        mall_name (str): 쇼핑몰 이름 (예: "쿠팡", "네이버쇼핑")
        product_name (str): 검색할 제품명 (예: "오리발")
        
    Returns:
        Optional[str]: 생성된 URL 또는 None (실패 시)
        
    Examples:
        >>> generate_shopping_url("쿠팡", "iPhone 17")
        'https://www.coupang.com/np/search?q=iPhone+17'
    """
    if not mall_name or not product_name:
        return None
    
    # 쇼핑몰 데이터 조회
    mall_data = SHOPPING_MALLS.get(mall_name)
    
    if not mall_data:
        print(f"Error: '{mall_name}' 쇼핑몰을 찾을 수 없습니다.")
        print(f"사용 가능한 쇼핑몰: {', '.join(SHOPPING_MALLS.keys())}")
        return None
    
    # URL 인코딩
    encoding = mall_data.get("encoding", "utf-8")
    try:
        encoded_product = quote(product_name, encoding=encoding)
    except Exception as e:
        print(f"Error: URL 인코딩 실패 - {e}")
        return None
    
    # URL 생성
    url_template = mall_data["url_template"]
    url = url_template.format(encoded_product)
    
    return url
