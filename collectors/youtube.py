"""YouTube 트렌딩 수집 — yt-dlp 검색 기반, API 키 불필요"""
import yt_dlp
import time

# 모드별 검색 쿼리
SEARCHES = {
    "fashion": {
        "KR": "패션 트렌드 2026 코디 룩북",
        "US": "fashion trend 2026 outfit lookbook",
        "JP": "ファッション トレンド 2026 コーデ",
    },
    "general": {
        "KR": "trending korea today",
        "US": "trending today",
        "JP": "trending japan today",
    },
}


def _search_trending(query, limit=20):
    """yt-dlp 검색으로 트렌딩 영상 수집"""
    url = f"ytsearch{limit}:{query}"
    opts = {
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "skip_download": True,
        "extract_flat": False,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            entries = info.get("entries", []) or []
            videos = []
            for v in entries:
                if not v or not v.get("id"):
                    continue
                videos.append({
                    "rank": len(videos) + 1,
                    "title": v.get("title", ""),
                    "video_id": v.get("id", ""),
                    "url": f"https://www.youtube.com/watch?v={v.get('id')}",
                    "channel": v.get("uploader", v.get("channel", "")),
                    "views": v.get("view_count", 0),
                    "duration": v.get("duration", 0),
                })
                if len(videos) >= limit:
                    break
            return videos
    except Exception as e:
        return [{"error": str(e)}]


def collect(mode="fashion"):
    queries = SEARCHES.get(mode, SEARCHES["fashion"])
    results = {}
    for code, query in queries.items():
        results[code] = _search_trending(query)
        time.sleep(2)

    return {"platform": "youtube", "mode": mode, "regions": results}
