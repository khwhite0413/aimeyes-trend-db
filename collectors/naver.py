"""네이버 데이터랩 쇼핑 인기 검색어 수집 — 웹 스크래핑, API 키 불필요"""
import requests
from bs4 import BeautifulSoup
import re

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}

FASHION_SHOPPING_TERMS = [
    "자켓", "원피스", "가디건", "니트", "코트", "바지", "청바지", "데님",
    "스커트", "블라우스", "셔츠", "티셔츠", "맨투맨", "후드", "패딩",
    "슬랙스", "트렌치", "가방", "신발", "스니커즈", "부츠", "샌들",
    "액세서리", "목걸이", "귀걸이", "반지", "시계", "모자", "벨트",
    "선글라스", "화장품", "립스틱", "파운데이션", "향수",
]


def collect(mode="fashion"):
    """네이버 데이터랩 메인에서 쇼핑 분야별 인기 검색어 스크래핑"""
    url = "https://datalab.naver.com/"
    try:
        r = requests.get(url, headers=_UA, timeout=15)
        if r.status_code != 200:
            return {"platform": "naver", "status": "error", "reason": f"HTTP {r.status_code}"}

        soup = BeautifulSoup(r.text, "html.parser")
        daily_rankings = []

        # 날짜별 인기 검색어 블록 추출
        for rank_block in soup.select(".keyword_rank"):
            title_el = rank_block.select_one(".rank_title")
            date_text = title_el.get_text(strip=True) if title_el else ""

            keywords = []
            rank_list = rank_block.select_one(".rank_list")
            if rank_list:
                for li in rank_list.select("li"):
                    text = li.get_text(strip=True)
                    # "1트위드자켓" → rank=1, keyword="트위드자켓"
                    m = re.match(r"^(\d+)(.+)", text)
                    if m:
                        keywords.append({
                            "rank": int(m.group(1)),
                            "keyword": m.group(2).strip(),
                        })

            if keywords:
                daily_rankings.append({
                    "date": date_text,
                    "keywords": keywords,
                })

        result = {
            "platform": "naver",
            "source": "datalab.naver.com",
            "category": "쇼핑 인기 검색어",
            "daily_rankings": daily_rankings,
            "mode": mode,
        }

        if mode == "fashion" and daily_rankings:
            fashion_filtered = []
            for ranking in daily_rankings:
                filtered_kws = [kw for kw in ranking.get("keywords", [])
                              if any(term in kw["keyword"] for term in FASHION_SHOPPING_TERMS)]
                if filtered_kws:
                    fashion_filtered.append({"date": ranking["date"], "keywords": filtered_kws})
            result["fashion_filtered"] = fashion_filtered

        return result

    except Exception as e:
        return {"platform": "naver", "status": "error", "reason": str(e)}
