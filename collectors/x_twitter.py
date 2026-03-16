"""X(Twitter) 트렌딩 토픽 수집 — trends24.in + getdaytrends.com, API 키 불필요"""
import requests
from bs4 import BeautifulSoup
import re
import time

_UA = {"User-Agent": "AIMEYES-TrendBot/1.0 (trend data collection)"}

COUNTRIES = {
    "korea": "한국",
    "united-states": "미국",
    "japan": "일본",
    "": "글로벌",
}

# 패션 관련 키워드 필터
FASHION_TERMS = [
    "fashion", "패션", "ootd", "outfit", "style", "코디", "룩북", "lookbook",
    "streetwear", "스트릿", "vintage", "빈티지", "y2k", "trend", "트렌드",
    "brand", "브랜드", "nike", "adidas", "zara", "uniqlo", "유니클로",
    "ファッション", "コーデ", "wear", "dress", "shoes", "sneaker",
    "gucci", "prada", "chanel", "무신사", "musinsa", "aesthetic",
]


def _scrape_trends24(slug):
    url = f"https://trends24.in/{slug}/" if slug else "https://trends24.in/"
    r = requests.get(url, headers=_UA, timeout=15)
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
            results[slug or "global"] = {
                "fashion_related": _filter_fashion(trends),
                "all_trending": trends,
            }
        else:
            results[slug or "global"] = trends
        time.sleep(2)

    return {"platform": "x_twitter", "mode": mode, "countries": results}
