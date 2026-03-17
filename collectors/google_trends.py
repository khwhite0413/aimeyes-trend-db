"""Google Trends 수집 — RSS 피드 + 패션 키워드 트렌드, API 키 불필요"""
import requests
from bs4 import BeautifulSoup
import time

COUNTRIES = {
    "KR": "한국",
    "US": "미국",
    "JP": "일본",
}

# 패션 모니터링 키워드 (CLAUDE.md 지침서 반영)
FASHION_KEYWORDS = {
    "KR": [
        "Y2K패션", "미니멀코어", "레이어링", "스트릿패션", "빈티지코디",
        "OOTD", "무신사", "지그재그", "데일리룩", "봄코디",
        "패션하울", "코디룩북", "뉴트럴톤", "콜라주레이어링",
    ],
    "US": [
        "quiet luxury", "mob wife aesthetic", "coquette", "streetwear", "vintage fashion",
        "capsule wardrobe", "thrift fashion", "OOTD", "spring outfits",
        "Amazon fashion", "Y2K fashion", "outfit lookbook",
    ],
    "JP": [
        "韓国ファッション", "ストリート系", "古着コーデ", "ミニマル", "Y2Kファッション",
        "着回しコーデ", "GUコーデ", "ユニクロコーデ", "春コーデ",
        "プチプラコーデ", "骨格診断",
    ],
}

# 범용 모니터링 키워드
GENERAL_KEYWORDS = {
    "KR": ["밈 트렌드", "틱톡 챌린지", "생활꿀팁", "인테리어DIY", "먹방레시피", "자기계발"],
    "US": ["TikTok trends", "viral memes", "life hacks", "home DIY", "food trends", "self care"],
    "JP": ["バズった", "TikTokトレンド", "ライフハック", "100均DIY", "バズレシピ"],
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
    fashion_terms = [
        "패션", "fashion", "코디", "outfit", "style", "wear", "룩", "look",
        "ファッション", "コーデ", "着回し", "古着", "프치프라",
        "브랜드", "brand", "옷", "dress", "shoes", "sneaker",
        "트렌드", "trend", "뷰티", "beauty", "메이크업", "makeup",
        "ootd", "haul", "하울", "thrift", "빈티지", "vintage",
        "streetwear", "스트릿", "y2k", "aesthetic", "minimal", "미니멀",
        "무신사", "지그재그", "zara", "uniqlo", "유니클로", "h&m", "shein",
        "quiet luxury", "coquette", "capsule", "레이어링", "layering",
    ]

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
                results[geo] = {
                    "trending_fashion": _fetch_fashion_rss(geo),
                    "all_trending": _fetch_trending_rss(geo),
                    "monitoring_keywords": FASHION_KEYWORDS.get(geo, []),
                }
            else:
                results[geo] = {
                    "all_trending": _fetch_trending_rss(geo),
                    "monitoring_keywords": GENERAL_KEYWORDS.get(geo, []),
                }
        except Exception as e:
            results[geo] = {"error": str(e)}
        time.sleep(2)

    return {"platform": "google_trends", "mode": mode, "countries": results}
