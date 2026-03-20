"""Google Trends 수집 — RSS 피드 + pytrends 패션 키워드 관심도, API 키 불필요"""
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
        "OOTD", "무신사", "지그재그", "데일리룩", "계절코디",
        "패션하울", "코디룩북", "뉴트럴톤", "콜라주레이어링",
    ],
    "US": [
        "quiet luxury", "mob wife aesthetic", "coquette", "streetwear", "vintage fashion",
        "capsule wardrobe", "thrift fashion", "OOTD", "seasonal outfits",
        "Amazon fashion", "Y2K fashion", "outfit lookbook",
    ],
    "JP": [
        "韓国ファッション", "ストリート系", "古着コーデ", "ミニマル", "Y2Kファッション",
        "着回しコーデ", "GUコーデ", "ユニクロコーデ", "季節コーデ",
        "プチプラコーデ", "骨格診断",
    ],
}

# 범용 모니터링 키워드
GENERAL_KEYWORDS = {
    "KR": ["밈 트렌드", "틱톡 챌린지", "생활꿀팁", "인테리어DIY", "먹방레시피", "자기계발"],
    "US": ["TikTok trends", "viral memes", "life hacks", "home DIY", "food trends", "self care"],
    "JP": ["バズった", "TikTokトレンド", "ライフハック", "100均DIY", "バズレシピ"],
}

# pytrends 지역 코드
GEO_MAP = {"KR": "KR", "US": "US", "JP": "JP"}

# 패션 필터 용어
FASHION_FILTER_TERMS = [
    "패션", "fashion", "코디", "outfit", "style", "wear", "룩", "look",
    "ファッション", "コーデ", "着回し", "古着", "プチプラ",
    "브랜드", "brand", "옷", "dress", "shoes", "sneaker",
    "트렌드", "trend", "뷰티", "beauty", "메이크업", "makeup",
    "ootd", "haul", "하울", "thrift", "빈티지", "vintage",
    "streetwear", "스트릿", "y2k", "aesthetic", "minimal", "미니멀",
    "무신사", "지그재그", "zara", "uniqlo", "유니클로", "h&m", "shein",
    "quiet luxury", "coquette", "capsule", "레이어링", "layering",
]


def _fetch_trending_rss(geo):
    """Google Trends RSS 피드에서 실시간 인기 검색어 수집"""
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    r = requests.get(url, timeout=15)
    r.encoding = 'utf-8'
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
    fashion_results = []
    for item in all_results:
        keyword_lower = item["keyword"].lower()
        if any(term in keyword_lower for term in FASHION_FILTER_TERMS):
            fashion_results.append(item)
    return fashion_results


def _fetch_keyword_interest(keywords, geo):
    """pytrends로 패션 키워드별 관심도 점수(0~100) 수집"""
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return []

    results = []
    # pytrends는 한번에 최대 5개 키워드 비교 가능
    # 5개씩 묶어서 조회
    for i in range(0, len(keywords), 5):
        batch = keywords[i:i+5]
        try:
            pytrends = TrendReq(hl='ko', tz=540, timeout=(10, 25),
                                retries=2, backoff_factor=2)
            pytrends.build_payload(batch, cat=0, timeframe='now 7-d', geo=geo)
            interest = pytrends.interest_over_time()

            if not interest.empty:
                for kw in batch:
                    if kw in interest.columns:
                        avg_score = int(interest[kw].mean())
                        max_score = int(interest[kw].max())
                        latest_score = int(interest[kw].iloc[-1])
                        results.append({
                            "keyword": kw,
                            "interest_avg": avg_score,
                            "interest_max": max_score,
                            "interest_latest": latest_score,
                        })

            time.sleep(2)  # 429 방지

        except Exception as e:
            # 429 등 에러 시 해당 배치 건너뛰기
            for kw in batch:
                results.append({
                    "keyword": kw,
                    "interest_avg": 0,
                    "interest_max": 0,
                    "interest_latest": 0,
                    "error": str(e)[:100],
                })
            time.sleep(5)

    # 관심도 순으로 정렬
    results.sort(key=lambda x: x.get("interest_avg", 0), reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    return results


def _fetch_related_queries(keywords, geo):
    """pytrends로 패션 키워드의 연관 검색어 수집"""
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return []

    related = []
    # 상위 3개 키워드만 연관 검색어 조회 (Rate limiting 대응 + 쿼터 절약)
    for kw in keywords[:3]:
        try:
            pytrends = TrendReq(hl='ko', tz=540, timeout=(10, 25),
                                retries=3, backoff_factor=3)
            pytrends.build_payload([kw], cat=0, timeframe='now 7-d', geo=geo)
            queries = pytrends.related_queries()

            if kw in queries and queries[kw].get("rising") is not None:
                rising_df = queries[kw]["rising"]
                if not rising_df.empty:
                    for _, row in rising_df.head(5).iterrows():
                        related.append({
                            "parent_keyword": kw,
                            "query": row.get("query", ""),
                            "value": str(row.get("value", "")),
                        })

            time.sleep(5)  # 429 방지 강화

        except Exception as e:
            print(f"    [related_queries] {kw}: {str(e)[:60]}")
            time.sleep(10)  # 에러 시 더 긴 대기

    return related


def collect(mode="fashion"):
    results = {}
    keywords_map = FASHION_KEYWORDS if mode == "fashion" else GENERAL_KEYWORDS

    for geo, name in COUNTRIES.items():
        try:
            if mode == "fashion":
                # 1. RSS 트렌딩 (전체 + 패션 필터)
                all_trending = _fetch_trending_rss(geo)
                trending_fashion = _fetch_fashion_rss(geo)

                # 2. pytrends 패션 키워드 관심도
                kw_list = keywords_map.get(geo, [])
                keyword_interest = _fetch_keyword_interest(kw_list, GEO_MAP.get(geo, geo))

                # 3. pytrends 연관 검색어
                related = _fetch_related_queries(kw_list, GEO_MAP.get(geo, geo))

                results[geo] = {
                    "trending_fashion": trending_fashion,
                    "all_trending": all_trending,
                    "keyword_interest": keyword_interest,
                    "related_queries": related,
                    "monitoring_keywords": kw_list,
                }
            else:
                all_trending = _fetch_trending_rss(geo)
                kw_list = keywords_map.get(geo, [])
                keyword_interest = _fetch_keyword_interest(kw_list, GEO_MAP.get(geo, geo))

                results[geo] = {
                    "all_trending": all_trending,
                    "keyword_interest": keyword_interest,
                    "monitoring_keywords": kw_list,
                }
        except Exception as e:
            results[geo] = {"error": str(e)}
        time.sleep(2)

    return {"platform": "google_trends", "mode": mode, "countries": results}
