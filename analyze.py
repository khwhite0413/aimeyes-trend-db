"""수집 데이터 자동 분석 — Daily Digest, Keyword Tracker, Weekly Summary 생성

collect_all.py 실행 후 자동으로 호출됨.
AI 불필요, Python만으로 시계열 비교 분석.
"""
import os
import json
import glob
import datetime
import re
from collections import Counter, defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DIGEST_DIR = os.path.join(BASE_DIR, "digest")

# 블랙리스트 (youtube.py와 동일)
BLACKLIST = [
    "saree", "sari", "lehenga", "kurti", "salwar", "anarkali", "mehndi", "henna",
    "bridal wear", "wedding wear", "mangalsutra", "bindi",
    "ramadan", "ramadhan", "hijab tutorial", "abaya",
    "necklace design", "gold jewellery", "prime jeweller",
    "rangoli", "mehendi", "dupatta",
]

# 불용어
STOP_WORDS = {
    "the", "a", "an", "and", "or", "is", "in", "at", "to", "for", "of", "on",
    "it", "my", "me", "i", "you", "this", "that", "with", "from", "by", "as",
    "be", "was", "are", "do", "does", "did", "have", "has", "had", "will",
    "would", "could", "should", "not", "no", "but", "if", "so", "up", "out",
    "about", "just", "also", "how", "what", "when", "where", "which", "who",
    "why", "very", "only", "now", "new", "one", "two", "more", "some", "any",
    "|", "-", "&", "", "–", "—", "...", "2026", "2025", "new", "best", "top",
    "most", "latest", "video", "official", "music",
}


def _get_available_dates(mode):
    """사용 가능한 날짜 목록 (최신순)"""
    mode_dir = os.path.join(DATA_DIR, mode)
    if not os.path.isdir(mode_dir):
        return []
    dates = []
    for d in sorted(os.listdir(mode_dir), reverse=True):
        if os.path.isdir(os.path.join(mode_dir, d)) and re.match(r"\d{4}-\d{2}-\d{2}", d):
            dates.append(d)
    return dates


def _load_json(mode, date, platform):
    """특정 날짜/플랫폼의 JSON 로드"""
    path = os.path.join(DATA_DIR, mode, date, f"{platform}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _extract_keywords_from_youtube(yt_data, country="KR"):
    """YouTube 데이터에서 키워드 추출 (search 결과만)"""
    keywords = Counter()
    if not yt_data or "regions" not in yt_data:
        return keywords

    search_key = f"{country}_search"
    videos = yt_data.get("regions", {}).get(search_key, [])
    if not isinstance(videos, list):
        return keywords

    for v in videos:
        title = v.get("title", "")
        # 해시태그 추출
        hashtags = re.findall(r"#[^\s#]+", title)
        for tag in hashtags:
            tag_lower = tag.lower()
            if len(tag_lower) > 2 and not any(bl in tag_lower for bl in BLACKLIST):
                keywords[tag_lower] += 1

        # 단어 추출
        words = re.sub(r"[^\w\s가-힣ぁ-ヿ㐀-䶵一-鿋]", " ", title).split()
        for w in words:
            w_lower = w.lower()
            if len(w_lower) >= 2 and w_lower not in STOP_WORDS and not w_lower.isdigit():
                if not any(bl in w_lower for bl in BLACKLIST):
                    keywords[w_lower] += 1

    return keywords


def _extract_keywords_from_google_trends(gt_data, country="KR"):
    """Google Trends 데이터에서 키워드 추출"""
    keywords = Counter()
    if not gt_data or "countries" not in gt_data:
        return keywords

    country_data = gt_data.get("countries", {}).get(country, {})
    if isinstance(country_data, list):
        trending = country_data
    elif isinstance(country_data, dict):
        trending = country_data.get("all_trending", country_data.get("trending_fashion", []))
    else:
        trending = []
    if isinstance(trending, list):
        for item in trending:
            kw = item.get("keyword", "").strip()
            if kw and len(kw) >= 2:
                keywords[kw.lower()] += 1

    return keywords


def _extract_keywords_from_x_twitter(xt_data, country_key="korea"):
    """X/Twitter 데이터에서 키워드 추출"""
    keywords = Counter()
    if not xt_data or "countries" not in xt_data:
        return keywords

    country_data = xt_data.get("countries", {}).get(country_key, {})
    if isinstance(country_data, list):
        trending = country_data
    elif isinstance(country_data, dict):
        trending = country_data.get("all_trending", country_data.get("fashion_related", []))
    else:
        trending = []
    if isinstance(trending, list):
        for item in trending:
            topic = item.get("topic", "").strip()
            if topic and len(topic) >= 2:
                keywords[topic.lower()] += 1

    return keywords


def _extract_keywords_from_naver(nv_data):
    """Naver 데이터에서 키워드 추출"""
    keywords = Counter()
    if not nv_data:
        return keywords

    for ranking in nv_data.get("daily_rankings", []):
        for item in ranking.get("keywords", []):
            kw = item.get("keyword", "").strip()
            if kw and len(kw) >= 2:
                keywords[kw.lower()] += 1

    return keywords


def _extract_keywords_from_pinterest(pt_data):
    """Pinterest 데이터에서 키워드 추출"""
    keywords = Counter()
    if not pt_data:
        return keywords

    trends = pt_data.get("fashion_trends", pt_data.get("trends", []))
    if isinstance(trends, list):
        for item in trends:
            name = item.get("name", "").strip()
            if name and len(name) >= 2:
                keywords[name.lower()] += 1

    return keywords


def _get_all_keywords_for_date(mode, date):
    """특정 날짜의 모든 플랫폼에서 키워드 추출"""
    all_keywords = Counter()
    platform_keywords = {}

    yt = _load_json(mode, date, "youtube")
    gt = _load_json(mode, date, "google_trends")
    xt = _load_json(mode, date, "x_twitter")
    nv = _load_json(mode, date, "naver")
    pt = _load_json(mode, date, "pinterest")

    for country in ["KR", "US", "JP"]:
        yt_kw = _extract_keywords_from_youtube(yt, country)
        all_keywords.update(yt_kw)
        for kw in yt_kw:
            if kw not in platform_keywords:
                platform_keywords[kw] = set()
            platform_keywords[kw].add("youtube")

    gt_kw = _extract_keywords_from_google_trends(gt, "KR")
    all_keywords.update(gt_kw)
    for kw in gt_kw:
        if kw not in platform_keywords:
            platform_keywords[kw] = set()
        platform_keywords[kw].add("google_trends")

    xt_kw = _extract_keywords_from_x_twitter(xt, "korea")
    all_keywords.update(xt_kw)
    for kw in xt_kw:
        if kw not in platform_keywords:
            platform_keywords[kw] = set()
        platform_keywords[kw].add("x_twitter")

    nv_kw = _extract_keywords_from_naver(nv)
    all_keywords.update(nv_kw)
    for kw in nv_kw:
        if kw not in platform_keywords:
            platform_keywords[kw] = set()
        platform_keywords[kw].add("naver")

    pt_kw = _extract_keywords_from_pinterest(pt)
    all_keywords.update(pt_kw)
    for kw in pt_kw:
        if kw not in platform_keywords:
            platform_keywords[kw] = set()
        platform_keywords[kw].add("pinterest")

    return all_keywords, platform_keywords


def _confidence_level(sample_today, sample_yesterday, days_of_data):
    """신뢰도 등급 계산"""
    if days_of_data >= 14 and sample_today >= 10 and sample_yesterday >= 10:
        return "high"
    elif days_of_data >= 7 and sample_today >= 5:
        return "medium"
    else:
        return "low"


def generate_daily_digest(mode="fashion"):
    """Daily Digest 생성 — 어제 대비 변화 분석"""
    dates = _get_available_dates(mode)
    if len(dates) < 1:
        return None

    today = dates[0]
    yesterday = dates[1] if len(dates) > 1 else None

    today_kw, today_platforms = _get_all_keywords_for_date(mode, today)

    if yesterday:
        yesterday_kw, _ = _get_all_keywords_for_date(mode, yesterday)
    else:
        yesterday_kw = Counter()

    # Rising 키워드 (오늘 > 어제)
    rising = []
    for kw, count in today_kw.most_common(100):
        prev = yesterday_kw.get(kw, 0)
        if count > prev and count >= 2:
            if prev > 0:
                change_pct = round((count - prev) / prev * 100)
                change_str = f"+{change_pct}%"
            else:
                change_str = "NEW"

            platforms = sorted(today_platforms.get(kw, set()))
            confidence = _confidence_level(count, prev, len(dates))

            rising.append({
                "keyword": kw,
                "change": change_str,
                "today_count": count,
                "yesterday_count": prev,
                "confidence": confidence,
                "platforms": platforms,
                "sample_note": f"오늘 {count}건, 어제 {prev}건 기준" if prev > 0 else f"오늘 {count}건 (신규)",
            })

    rising.sort(key=lambda x: x["today_count"], reverse=True)
    rising = rising[:20]

    # Declining 키워드 (어제 > 오늘)
    declining = []
    for kw, prev_count in yesterday_kw.most_common(50):
        curr = today_kw.get(kw, 0)
        if prev_count > curr and prev_count >= 3:
            change_pct = round((curr - prev_count) / prev_count * 100)
            declining.append({
                "keyword": kw,
                "change": f"{change_pct}%",
                "today_count": curr,
                "yesterday_count": prev_count,
                "confidence": _confidence_level(curr, prev_count, len(dates)),
            })

    declining.sort(key=lambda x: x["yesterday_count"], reverse=True)
    declining = declining[:10]

    # 신규 등장 키워드
    new_entries = []
    for kw, count in today_kw.most_common(50):
        if kw not in yesterday_kw and count >= 2:
            new_entries.append(kw)
    new_entries = new_entries[:10]

    # 크로스 플랫폼 (2개 이상 플랫폼에서 동시 등장)
    cross_platform = []
    for kw, platforms in today_platforms.items():
        if len(platforms) >= 2:
            cross_platform.append({
                "keyword": kw,
                "platform_count": len(platforms),
                "platforms": sorted(platforms),
                "total_count": today_kw[kw],
            })
    cross_platform.sort(key=lambda x: x["platform_count"], reverse=True)
    cross_platform = cross_platform[:10]

    digest = {
        "date": today,
        "mode": mode,
        "compared_to": yesterday,
        "total_keywords_today": len(today_kw),
        "total_keywords_yesterday": len(yesterday_kw) if yesterday else 0,
        "data_days_available": len(dates),
        "overall_confidence": _confidence_level(
            sum(today_kw.values()), sum(yesterday_kw.values()), len(dates)
        ),
        "rising": rising,
        "declining": declining,
        "new_entries": new_entries,
        "cross_platform_hot": cross_platform,
    }

    return digest


def generate_keyword_tracker(mode="fashion"):
    """Keyword Tracker — 주요 키워드의 날짜별 추이"""
    dates = _get_available_dates(mode)
    if not dates:
        return None

    # 모든 날짜의 키워드 수집
    all_date_keywords = {}
    for date in dates[:30]:  # 최대 30일
        kw, _ = _get_all_keywords_for_date(mode, date)
        all_date_keywords[date] = kw

    # 전체 기간에서 가장 많이 등장한 키워드 Top 30
    total = Counter()
    for date_kw in all_date_keywords.values():
        total.update(date_kw)

    top_keywords = [kw for kw, _ in total.most_common(30)]

    # 키워드별 날짜 추이
    tracker = {}
    for kw in top_keywords:
        tracker[kw] = {}
        for date in sorted(dates[:30]):
            tracker[kw][date] = all_date_keywords.get(date, {}).get(kw, 0)

    return {
        "mode": mode,
        "tracked_keywords": len(top_keywords),
        "date_range": {"from": sorted(dates[:30])[0], "to": dates[0]} if dates else {},
        "data_days": len(dates[:30]),
        "keywords": tracker,
    }


def generate_weekly_summary(mode="fashion"):
    """Weekly Summary — 이번 주 핵심 요약"""
    dates = _get_available_dates(mode)
    if not dates:
        return None

    week_dates = dates[:7]

    # 주간 키워드 집계
    weekly_total = Counter()
    weekly_platforms = {}
    first_day_kw = Counter()
    last_day_kw = Counter()

    for i, date in enumerate(week_dates):
        kw, plat = _get_all_keywords_for_date(mode, date)
        weekly_total.update(kw)
        for k, p in plat.items():
            if k not in weekly_platforms:
                weekly_platforms[k] = set()
            weekly_platforms[k].update(p)

        if i == 0:  # 최신
            last_day_kw = kw
        if i == len(week_dates) - 1:  # 가장 오래된
            first_day_kw = kw

    # 주간 Top rising
    top_rising = []
    for kw, total in weekly_total.most_common(20):
        first = first_day_kw.get(kw, 0)
        last = last_day_kw.get(kw, 0)
        if last > first:
            growth = f"+{round((last - first) / max(first, 1) * 100)}%"
            top_rising.append({"keyword": kw, "growth": growth, "total_mentions": total})

    top_rising.sort(key=lambda x: x["total_mentions"], reverse=True)

    # 크로스 플랫폼 Hot
    most_cross = []
    for kw, plats in weekly_platforms.items():
        if len(plats) >= 2:
            most_cross.append({
                "keyword": kw,
                "platforms": sorted(plats),
                "count": len(plats),
            })
    most_cross.sort(key=lambda x: x["count"], reverse=True)

    # Naver 쇼핑 인기
    naver_hot = []
    for date in week_dates[:1]:
        nv = _load_json(mode, date, "naver")
        if nv:
            nv_kw = _extract_keywords_from_naver(nv)
            naver_hot = [kw for kw, _ in nv_kw.most_common(5)]

    summary = {
        "mode": mode,
        "week_range": {"from": week_dates[-1], "to": week_dates[0]} if len(week_dates) > 1 else {},
        "days_analyzed": len(week_dates),
        "confidence": _confidence_level(
            sum(last_day_kw.values()), sum(first_day_kw.values()), len(dates)
        ),
        "top_rising": top_rising[:5],
        "most_cross_platform": most_cross[:5],
        "naver_shopping_hot": naver_hot,
        "top_keywords_overall": [kw for kw, _ in weekly_total.most_common(10)],
    }

    return summary


def run_analysis():
    """전체 분석 실행"""
    os.makedirs(DIGEST_DIR, exist_ok=True)

    for mode in ["fashion", "general"]:
        mode_digest_dir = os.path.join(DIGEST_DIR, mode)
        os.makedirs(mode_digest_dir, exist_ok=True)

        print(f"\n  === {mode.upper()} 분석 ===")

        # Daily Digest
        digest = generate_daily_digest(mode)
        if digest:
            path = os.path.join(mode_digest_dir, "daily_digest.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(digest, f, ensure_ascii=False, indent=2)
            rising_count = len(digest.get("rising", []))
            cross_count = len(digest.get("cross_platform_hot", []))
            conf = digest.get("overall_confidence", "?")
            print(f"  Daily Digest: {rising_count} rising, {cross_count} cross-platform (신뢰도: {conf})")

        # Keyword Tracker
        tracker = generate_keyword_tracker(mode)
        if tracker:
            path = os.path.join(mode_digest_dir, "keyword_tracker.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(tracker, f, ensure_ascii=False, indent=2)
            print(f"  Keyword Tracker: {tracker['tracked_keywords']}개 키워드, {tracker['data_days']}일")

        # Weekly Summary
        summary = generate_weekly_summary(mode)
        if summary:
            path = os.path.join(mode_digest_dir, "weekly_summary.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            print(f"  Weekly Summary: {summary['days_analyzed']}일 분석 (신뢰도: {summary['confidence']})")


if __name__ == "__main__":
    run_analysis()
