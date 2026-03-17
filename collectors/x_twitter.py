"""X(Twitter) 트렌딩 토픽 수집 — trends24.in + getdaytrends.com, API 키 불필요"""
import requests
from bs4 import BeautifulSoup
import re
import time

_UA = {"User-Agent": "AIMEYES-TrendBot/1.0 (trend data collection)"}

COUNTRIES = {
    "korea": "한국",
    "united-states": "미국",
    "canada": "캐나다",
    "japan": "일본",
    "": "글로벌",
}

# 패션 관련 키워드 필터 (CLAUDE.md 지침서 반영)
FASHION_TERMS = [
    # 기본 패션 용어
    "fashion", "패션", "ootd", "outfit", "style", "코디", "룩북", "lookbook",
    "streetwear", "스트릿", "vintage", "빈티지", "y2k", "trend", "트렌드",
    "wear", "dress", "shoes", "sneaker", "aesthetic",
    # 브랜드/마켓플레이스
    "brand", "브랜드", "nike", "adidas", "zara", "uniqlo", "유니클로",
    "gucci", "prada", "chanel", "무신사", "musinsa", "지그재그",
    "h&m", "shein", "temu", "amazon fashion",
    # 트렌드 키워드
    "quiet luxury", "coquette", "mob wife", "capsule wardrobe",
    "미니멀", "minimal", "레이어링", "layering", "하울", "haul",
    "thrift", "데일리룩", "봄코디", "spring outfit",
    # 일본어
    "ファッション", "コーデ", "着回し", "古着", "韓国ファッション",
    "プチプラ", "骨格診断",
    # 뷰티/메이크업 (연관)
    "뷰티", "beauty", "메이크업", "makeup", "헤어", "hair",
]


def _scrape_trends24(slug):
    url = f"https://trends24.in/{slug}/" if slug else "https://trends24.in/"
    r = requests.get(url, headers=_UA, timeout=15)
    r.encoding = 'utf-8'
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    trends = []
    seen = set()
    for ol in soup.select(".trend-card__list"):
        for li in ol.select("li"):
            name_el = li.select_one(".trend-name a")
            if not name_el:
                continue
            name = name_el.get_text(strip=True)
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            volume = ""
            vol_el = li.select_one(".tweet-count")
            if vol_el:
                volume = vol_el.get_text(strip=True)
            trends.append({"rank": len(trends) + 1, "topic": name, "volume": volume})
        if trends:
            break
    return trends


def _scrape_getdaytrends(slug):
    url = f"https://getdaytrends.com/{slug}/" if slug else "https://getdaytrends.com/"
    r = requests.get(url, headers=_UA, timeout=15)
    r.encoding = 'utf-8'
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    trends = []
    for a in soup.select("a[href*='/trend/']"):
        name = a.get_text(strip=True)
        if not name or len(name) < 2:
            continue
        volume = ""
        parent = a.find_parent()
        if parent:
            vol_text = parent.get_text(strip=True).replace(name, "").strip()
            vol_match = re.search(r"([\d,.]+[KkMm]?\+?\s*tweets?)", vol_text, re.IGNORECASE)
            if vol_match:
                volume = vol_match.group(1)
        trends.append({"rank": len(trends) + 1, "topic": name, "volume": volume})
        if len(trends) >= 30:
            break
    return trends


def _filter_fashion(trends):
    """패션 관련 토픽만 필터링"""
    return [t for t in trends if any(
        term in t["topic"].lower() for term in FASHION_TERMS
    )]


# 패션 해시태그 직접 검색 (nitter/검색 대안)
FASHION_HASHTAGS = {
    "korea": ["패션", "OOTD", "데일리룩", "코디", "스트릿패션", "무신사"],
    "united-states": ["fashion", "OOTD", "streetwear", "thrifthaul", "outfitinspo", "quietluxury"],
    "canada": ["fashion", "OOTD", "thriftflip", "canadianfashion"],
    "japan": ["ファッション", "コーデ", "古着", "韓国ファッション", "プチプラ"],
    "": ["fashion", "OOTD", "streetstyle"],
}


def _search_fashion_hashtags(slug):
    """getdaytrends.com에서 패션 해시태그별 트렌딩 여부 확인"""
    hashtags = FASHION_HASHTAGS.get(slug, FASHION_HASHTAGS[""])
    results = []

    for tag in hashtags:
        try:
            # getdaytrends.com에서 특정 해시태그 검색
            url = f"https://getdaytrends.com/trend/%23{tag}/"
            r = requests.get(url, headers=_UA, timeout=10)
            r.encoding = 'utf-8'
            if r.status_code != 200:
                results.append({"hashtag": f"#{tag}", "status": "not_trending", "volume": ""})
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            # 볼륨/트렌딩 정보 추출
            volume = ""
            trend_info = soup.select_one(".trend-detail, .trend-volume, .summary")
            if trend_info:
                vol_text = trend_info.get_text(strip=True)
                vol_match = re.search(r"([\d,.]+[KkMm]?\+?\s*tweets?)", vol_text, re.IGNORECASE)
                if vol_match:
                    volume = vol_match.group(1)

            status = "trending" if volume else "found"
            results.append({
                "hashtag": f"#{tag}",
                "status": status,
                "volume": volume,
                "rank": len(results) + 1,
            })
            time.sleep(1)

        except Exception:
            results.append({"hashtag": f"#{tag}", "status": "error", "volume": ""})

    return results


def collect(mode="fashion"):
    results = {}
    for slug, name in COUNTRIES.items():
        trends = []
        try:
            trends = _scrape_trends24(slug)
        except Exception:
            pass
        if not trends:
            try:
                trends = _scrape_getdaytrends(slug)
            except Exception:
                pass

        if mode == "fashion":
            # 패션 해시태그 직접 검색 추가
            fashion_hashtags = _search_fashion_hashtags(slug)

            results[slug or "global"] = {
                "fashion_related": _filter_fashion(trends),
                "all_trending": trends,
                "fashion_hashtags": fashion_hashtags,
            }
        else:
            results[slug or "global"] = {
                "all_trending": trends,
            }
        time.sleep(2)

    return {"platform": "x_twitter", "mode": mode, "countries": results}
