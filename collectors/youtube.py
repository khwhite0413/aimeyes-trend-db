"""YouTube 트렌딩 수집 — YouTube Data API v3 (무료 일 10,000 쿼터)"""
import os
import requests
import time

API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# 모드별 검색 쿼리 (CLAUDE.md 지침서 키워드 반영)
# YouTube API 쿼터 관리: 일 10,000 units, search=100 units/req
# 하루 2회 실행 → 1회당 ~4,800 units 이하로 유지 (검색 48개 이하)
SEARCHES = {
    "fashion": {
        "KR": [
            "패션 트렌드 2026", "코디 룩북", "패션 하울",
            "OOTD 데일리룩", "스트릿 패션 코디",
            "무신사 인기 아이템", "빈티지 Y2K 패션",
            "계절별 코디 추천",
        ],
        "US": [
            "fashion trend 2026", "outfit lookbook", "fashion haul",
            "OOTD street style", "thrift haul capsule wardrobe",
            "quiet luxury outfit", "seasonal outfits ideas",
            "Amazon fashion finds",
        ],
        "JP": [
            "ファッション トレンド 2026", "コーデ ルックブック",
            "着回し 古着コーデ", "韓国ファッション",
            "季節コーデ", "GU ユニクロ コーデ",
        ],
    },
    "general": {
        "KR": [
            "트렌드 2026", "요즘 유행",
            "틱톡 챌린지 바이럴", "생활 꿀팁 라이프핵",
            "인테리어 DIY 자취", "맛집 레시피 먹방",
        ],
        "US": [
            "trending today viral", "TikTok trends 2026",
            "life hacks tips DIY", "viral recipe food",
            "home makeover", "self improvement",
        ],
        "JP": [
            "トレンド 2026 話題", "バズった TikTok トレンド",
            "ライフハック 100均 DIY", "バズ レシピ",
        ],
    },
}

FASHION_FILTER_TERMS = [
    "패션", "fashion", "코디", "outfit", "style", "wear", "룩", "look",
    "ファッション", "コーデ", "着回し", "古着",
    "브랜드", "brand", "옷", "dress", "shoes", "sneaker",
    "트렌드", "trend", "뷰티", "beauty", "메이크업", "makeup",
    "ootd", "haul", "하울", "thrift", "빈티지", "vintage",
    "streetwear", "스트릿", "y2k", "aesthetic", "minimal", "미니멀",
    "무신사", "지그재그", "zara", "uniqlo", "유니클로",
    "quiet luxury", "coquette", "capsule", "레이어링", "layering",
]

# 패션 검색 결과에서 제외할 블랙리스트 (비관련 콘텐츠)
BLACKLIST_TERMS = [
    "saree", "sari", "lehenga", "kurti", "salwar", "anarkali", "mehndi", "henna",
    "bridal wear", "wedding wear", "mangalsutra", "bindi",
    "ramadan", "ramadhan", "hijab tutorial", "abaya",
    "necklace design", "gold jewellery", "prime jeweller",
    "rangoli", "mehendi", "dupatta",
]

REGION_MAP = {"KR": "KR", "US": "US", "JP": "JP"}


def _filter_fashion_videos(videos):
    """패션 관련 영상만 필터링 (제목+채널명 기반)"""
    filtered = []
    for v in videos:
        title_lower = (v.get("title", "") + " " + v.get("channel", "")).lower()
        if any(term in title_lower for term in FASHION_FILTER_TERMS):
            filtered.append(v)
    return filtered


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


def _get_video_stats(video_ids):
    """video ID 목록으로 조회수/좋아요 등 통계 일괄 조회 (videos.list: 1 unit per request, 최대 50개)"""
    if not API_KEY or not video_ids:
        return {}
    stats_map = {}
    # 50개씩 배치 (API 최대)
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "statistics",
            "id": ",".join(batch),
            "key": API_KEY,
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                for item in resp.json().get("items", []):
                    vid = item.get("id", "")
                    s = item.get("statistics", {})
                    stats_map[vid] = {
                        "views": int(s.get("viewCount", 0)),
                        "likes": int(s.get("likeCount", 0)),
                        "comments": int(s.get("commentCount", 0)),
                    }
        except Exception as e:
            # stats 조회 실패 시 에러 기록
            for vid in batch:
                if vid not in stats_map:
                    stats_map[vid] = {"views": 0, "likes": 0, "comments": 0, "error": str(e)[:100]}
        time.sleep(0.3)
    return stats_map


def _search_videos(query, region_code="KR", max_results=5):
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
        if mode == "fashion":
            trending = _filter_fashion_videos(trending)
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
        search_results = search_results[:20]

        # 블랙리스트 필터링 (비관련 콘텐츠 제거)
        if mode == "fashion":
            search_results = [v for v in search_results
                              if not any(term in (v.get("title", "") + " " + v.get("channel", "")).lower()
                                         for term in BLACKLIST_TERMS)]

        # 3. 검색 결과에 조회수 추가 (videos.list API, 1 unit per 50 videos)
        video_ids = [v["video_id"] for v in search_results if v.get("video_id")]
        if video_ids:
            stats = _get_video_stats(video_ids)
            for v in search_results:
                vid = v.get("video_id", "")
                if vid in stats:
                    v["views"] = stats[vid]["views"]
                    v["likes"] = stats[vid]["likes"]
                    v["comments"] = stats[vid]["comments"]

        results[f"{code}_search"] = search_results

    return {"platform": "youtube", "mode": mode, "regions": results}
