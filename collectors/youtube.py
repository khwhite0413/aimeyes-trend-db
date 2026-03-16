"""YouTube 트렌딩 수집 — YouTube Data API v3 (무료 일 10,000 쿼터)"""
import os
import requests
import time

API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# 모드별 검색 쿼리
SEARCHES = {
    "fashion": {
        "KR": ["패션 트렌드 2026", "코디 룩북", "패션 하울"],
        "US": ["fashion trend 2026", "outfit lookbook", "fashion haul"],
        "JP": ["ファッション トレンド 2026", "コーデ ルックブック"],
    },
    "general": {
        "KR": ["트렌드 2026", "요즘 유행"],
        "US": ["trending today", "viral 2026"],
        "JP": ["トレンド 2026", "話題"],
    },
}

REGION_MAP = {"KR": "KR", "US": "US", "JP": "JP"}


def _get_trending(region_code, max_results=15):
    """YouTube 인기 급상승 동영상 (mostPopular)"""
    if not API_KEY:
        return []
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": max_results,
        "key": API_KEY,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return [{"error": f"HTTP {resp.status_code}", "detail": resp.text[:200]}]
        data = resp.json()
        videos = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            videos.append({
                "rank": len(videos) + 1,
                "title": snippet.get("title", ""),
                "video_id": item.get("id", ""),
                "url": f"https://www.youtube.com/watch?v={item.get('id', '')}",
                "channel": snippet.get("channelTitle", ""),
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "published": snippet.get("publishedAt", ""),
                "category": snippet.get("categoryId", ""),
            })
        return videos
    except Exception as e:
        return [{"error": str(e)}]


def _search_videos(query, region_code="KR", max_results=10):
    """YouTube 키워드 검색"""
    if not API_KEY:
        return []
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "order": "viewCount",
        "regionCode": region_code,
        "maxResults": max_results,
        "publishedAfter": "",  # 아래에서 설정
        "key": API_KEY,
    }
    # 최근 7일 영상만
    from datetime import datetime, timezone, timedelta
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00Z")
    params["publishedAfter"] = week_ago

    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return [{"error": f"HTTP {resp.status_code}"}]
        data = resp.json()
        videos = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId", "")
            videos.append({
                "rank": len(videos) + 1,
                "title": snippet.get("title", ""),
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "channel": snippet.get("channelTitle", ""),
                "published": snippet.get("publishedAt", ""),
            })
        return videos
    except Exception as e:
        return [{"error": str(e)}]


def collect(mode="fashion"):
    if not API_KEY:
        return {"platform": "youtube", "status": "skipped", "reason": "YOUTUBE_API_KEY not set"}

    queries = SEARCHES.get(mode, SEARCHES["fashion"])
    results = {}

    # 1. 각 국가별 인기 급상승
    for code in REGION_MAP:
        trending = _get_trending(code)
        if trending:
            results[f"{code}_trending"] = trending
        time.sleep(0.5)

    # 2. 키워드 검색
    for code, keyword_list in queries.items():
        search_results = []
        seen = set()
        for keyword in keyword_list:
            videos = _search_videos(keyword, code)
            for v in videos:
                vid = v.get("video_id", "")
                if vid and vid not in seen:
                    seen.add(vid)
                    v["rank"] = len(search_results) + 1
                    search_results.append(v)
            time.sleep(0.5)
        results[f"{code}_search"] = search_results[:20]

    return {"platform": "youtube", "mode": mode, "regions": results}
