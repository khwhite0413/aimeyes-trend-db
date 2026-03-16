"""네이버 데이터랩 쇼핑 인기 검색어 수집 — 웹 스크래핑, API 키 불필요"""
import requests
from bs4 import BeautifulSoup
import re

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}


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

        return {
            "platform": "naver",
            "source": "datalab.naver.com",
            "category": "쇼핑 인기 검색어",
            "daily_rankings": daily_rankings,
        }

    except Exception as e:
        return {"platform": "naver", "status": "error", "reason": str(e)}
