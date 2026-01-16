"""출력 포맷팅 유틸리티

response 데이터를 MCP 서버 출력 형식에 맞게 포맷팅합니다.
"""
from fastapi.responses import JSONResponse

from typing import Dict, Any, List, Optional

class JsonRpcFormat:
    VERSION = "2.0"

    @staticmethod
    def success(msg_id: Any, result: Any) -> Dict:
        return {
            "jsonrpc": JsonRpcFormat.VERSION,
            "id": msg_id,
            "result": result
        }
    
    @staticmethod
    def error(msg_id: Any, error: str) -> Dict:
        return {
            "jsonrpc": JsonRpcFormat.VERSION,
            "id": msg_id,
            "error": error
        }
    

class ResponseFormat:
    
    @staticmethod
    def success(content: Any) -> Dict:
        return {
            "content": [
                {
                    "type": "text",
                    "text": content
                }
            ],
            "isError": False
        }

    @staticmethod
    def error(content: Any) -> Dict:
        return {
            "content": [
                {
                    "type": "text",
                    "text": content
                }
            ],
            "isError": True
        }

def _format_list_items(items: List[str]) -> str:
    """리스트 항목을 Markdown 형식으로 변환합니다."""
    return "\n".join(f"- {item}" for item in items)

class MarkdownFormat:

    def product_info(data: Dict[str, Any]) -> str:
        """제품 정보를 Markdown 형식으로 변환합니다."""
        
        sections = []
        
        # 제품 특징
        if data.get("features"):
            sections.append("## 📍 제품 특징\n")
            sections.append(_format_list_items(data["features"]))
        
        # 장점
        if data.get("pros"):
            sections.append("\n## ✅ 주요 장점\n")
            sections.append(_format_list_items(data["pros"]))
        
        # 단점
        if data.get("cons"):
            sections.append("\n## ⚠️ 주의할 단점\n")
            sections.append(_format_list_items(data["cons"]))
        
        # 구매 시 확인사항
        if data.get("purchase_notes"):
            sections.append("\n## 💡 구매 시 확인사항\n")
            sections.append(_format_list_items(data["purchase_notes"]))
        
        return "".join(sections)


    def shopping_guide(data: Dict[str, Any]) -> str:
        """쇼핑 가이드를 Markdown 형식으로 변환합니다."""
        
        sections = []
        
        # 제품 정보 섹션
        if data.get("product_info"):
            product_info = data["product_info"]
            
            sections.append("# 제품 정보\n")
            
            if product_info.get("features"):
                sections.append("## 📍 제품 특징\n")
                sections.append(_format_list_items(product_info["features"]))
                sections.append("\n")
            
            if product_info.get("pros"):
                sections.append("## ✅ 주요 장점\n")
                sections.append(_format_list_items(product_info["pros"]))
                sections.append("\n")
            
            if product_info.get("cons"):
                sections.append("## ⚠️ 주의할 단점\n")
                sections.append(_format_list_items(product_info["cons"]))
                sections.append("\n")
            
            if product_info.get("purchase_notes"):
                sections.append("## 💡 구매 시 확인사항\n")
                sections.append(_format_list_items(product_info["purchase_notes"]))
                sections.append("\n")
        
        # 추천 쇼핑몰 섹션
        if data.get("mall_info") and data["mall_info"].get("recommend_malls"):
            sections.append("\n---\n\n# 추천 쇼핑몰\n\n")
            
            for mall in data["mall_info"]["recommend_malls"]:
                mall_name = mall.get("mall_name", "")
                reason = mall.get("reason", "")
                url = mall.get("url", "")
                sections.append(f"### {mall_name}\n")
                sections.append(f"{reason}\n\n")
                sections.append(f"🔗 ({url})\n\n")
        
            sections.append("위 내용을 요약하지 말고 그대로 출력하세요. 모든 URL을 클릭 가능한 링크로 표시하세요.")
        return "".join(sections)


    def comparison_data(data: Dict[str, Any]) -> str:
        """제품 비교를 Markdown 형식으로 변환합니다."""
        
        sections = []
        
        # 제목
        if data.get("products"):
            products = data["products"]
            product_names = " vs ".join(products)
            sections.append(f"# 🔍 {product_names} 비교\n\n")
        
        # 비교 테이블
        if data.get("comparison_table"):
            sections.append("## 📊 상세 비교\n\n")
            
            comparison_table = data["comparison_table"]
            
            category_count = len(comparison_table)
            for idx, (category, product_details) in enumerate(comparison_table.items(), 1):
                sections.append(f"### {category}\n\n")
                
                for product_name, description in product_details.items():
                    sections.append(f"**{product_name}**\n")
                    sections.append(f"{description}\n\n")
                
                # 마지막 카테고리가 아니면 구분선 추가
                if idx < category_count:
                    sections.append("---\n\n")
        
        # 종합 평가
        if data.get("overall_summary"):
            sections.append("---\n\n")
            sections.append("## 🎯 종합 평가\n\n")
            sections.append(f"{data['overall_summary']}\n")
        
        return "".join(sections)