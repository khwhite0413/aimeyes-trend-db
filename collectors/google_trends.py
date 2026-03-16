"""Google Trends 수집 — RSS 피드 + 패션 키워드 트렌드, API 키 불필요"""
import requests
from bs4 import BeautifulSoup
import time

COUNTRIES = {
    "KR": "한국",
    "US": "미국",
    "JP": "일본",
}

# 패션 모니터링 키워드 (Google Trends URL로 관심도 추적)
FASHION_KEYWORDS = {
    "KR": ["Y2K패션", "미니멀코어", "레이어링", "스트릿패션", "빈티지코디"],
    "US": ["quiet luxury", "mob wife aesthetic", "coquette", "streetwear", "vintage fashion"],
    "JP": ["韓国ファッション", "ストリート系", "古着コーデ", "ミニマル", "Y2Kファッション"],
}


def _fetch_trending_rss(geo):
    """Google Trends RSS 피드에서 실시간 인기 검색어 수집"""
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    r = requests.get(url, timeout=15)
    if r.status_code != 200:
        return []

    soup = BeautifulSoup(r.text, "xml")
    items = soup.find_all("item")
    results = []
    for i, item in enumerate(items):
        title = item.find("title")
        traffic = item.find("ht:approx_traffic")
        news_items = item.find_all("ht:news_item")

        news = []
        for ni in news_items[:3]:
            news_title = ni.find("ht:news_item_title")
            news_url = ni.find("ht:news_item_url")
            if news_title:
                news.append({
                    "title": news_title.text,
                    "url": news_url.text if news_url else "",
                })

        results.append({
            "rank": i + 1,
            "keyword": title.text if title else "",
            "traffic": traffic.text if traffic else "",
            "related_news": news,
        })

    return results


def _fetch_fashion_rss(geo):
    """Google Trends RSS에서 패션 관련 검색어만 필터링"""
    all_results = _fetch_trending_rss(geo)
    fashion_terms = ["패션", "fashion", "코디", "outfit", "style", "wear", "룩", "look",
                     "ファッション", "コーデ", "브랜드", "brand", "옷", "dress", "shoes",
                     "트렌드", "trend", "뷰티", "beauty", "메이크업", "makeup"]

    fashion_results = []
    for item in all_results:
        keyword_lower = item["keyword"].lower()
        if any(term in keyword_lower for term in fashion_terms):
            fashion_results.append(item)

    return fashion_results


def collect(mode="fashion"):
    results = {}
    for geo, name in COUNTRIES.items():
        try:
            if mode == "fashion":
                # 패션 필터링된 인기 검색어 + 모니터링 키워드 목록
                results[geo] = {
                    "trending_fashion": _fetch_fashion_rss(geo),
                    "all_trending": _fetch_trending_rss(geo),
                    "monitoring_keywords": FASHION_KEYWORDS.get(geo, []),
                }
            else:
                results[geo] = _fetch_trending_rss(geo)
        except Exception as e:
            results[geo] = {"error": str(e)}
        time.sleep(2)

    return {"platform": "google_trends", "mode": mode, "countries": results}
