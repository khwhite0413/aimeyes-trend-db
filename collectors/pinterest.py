"""Pinterest Predicts 트렌드 수집 — 웹 스크래핑, API 키 불필요"""
import requests
from bs4 import BeautifulSoup
import re
import datetime

_UA = {"User-Agent": "AIMEYES-TrendBot/1.0 (trend data collection)"}

FASHION_TREND_TERMS = [
    "fashion", "style", "outfit", "wear", "beauty", "makeup", "hair",
    "dress", "jewelry", "accessory", "aesthetic", "decor", "design",
    "nail", "skin", "glow", "vintage", "retro", "boho", "minimal",
    "luxury", "chic", "elegant", "bold", "color", "pattern", "texture",
]


def collect(mode="fashion"):
    year = str(datetime.date.today().year)
    url = f"https://business.pinterest.com/pinterest-predicts/{year}/"

    try:
        r = requests.get(url, headers=_UA, timeout=15)
        if r.status_code != 200:
            return {"platform": "pinterest", "status": "error", "reason": f"HTTP {r.status_code}"}

        soup = BeautifulSoup(r.text, "html.parser")
        trends = []

        # 스크립트 태그에서 트렌드 데이터 추출
        for script in soup.select("script"):
            text = script.string or ""
            names = re.findall(r'"trend_name"\s*:\s*"([^"]+)"', text)
            descs = re.findall(r'"trend_description"\s*:\s*"([^"]*)"', text)
            for i, name in enumerate(names):
                desc = descs[i] if i < len(descs) else ""
                desc = re.sub(r"<[^>]+>", "", desc)
                desc = desc.replace("\\u0026", "&").replace("\\n", " ").strip()
                if name and name not in [t.get("name") for t in trends]:
                    trends.append({"name": name, "description": desc[:300]})

        # 폴백: h2/h3 텍스트 추출
        if not trends:
            for heading in soup.select("h2, h3"):
                text = heading.get_text(strip=True)
                if 3 < len(text) < 100:
                    ps = heading.find_next_siblings("p", limit=2)
                    desc = " ".join(p.get_text(strip=True) for p in ps) if ps else ""
                    trends.append({"name": text, "description": desc[:300]})

        result = {
            "platform": "pinterest",
            "year": year,
            "source_url": url,
            "trends": trends,
            "mode": mode,
        }

        if mode == "fashion":
            fashion_trends = [t for t in trends if any(
                term in (t.get("name", "") + " " + t.get("description", "")).lower()
                for term in FASHION_TREND_TERMS
            )]
            result["fashion_trends"] = fashion_trends

        return result

    except Exception as e:
        return {"platform": "pinterest", "status": "error", "reason": str(e)}
