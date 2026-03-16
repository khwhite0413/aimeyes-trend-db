"""TikTok 트렌딩 수집 — RapidAPI (키 필요, 없으면 건너뜀)"""
import os
import requests


def collect(mode="fashion"):
    api_key = os.getenv("TIKTOK_RAPIDAPI_KEY", "")
    if not api_key:
        return {"platform": "tiktok", "status": "skipped", "reason": "TIKTOK_RAPIDAPI_KEY not set"}

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "tiktok-best-experience.p.rapidapi.com",
    }
    try:
        resp = requests.get(
            "https://tiktok-best-experience.p.rapidapi.com/trending",
            headers=headers,
            timeout=15,
        )

        # 응답 디버깅: 상태 코드와 구조 확인
        if resp.status_code != 200:
            return {
                "platform": "tiktok",
                "status": "error",
                "reason": f"HTTP {resp.status_code}",
                "detail": resp.text[:500],
            }

        data = resp.json()

        # 유연한 응답 파싱: 다양한 API 응답 구조 대응
        video_list = []
        if isinstance(data, dict):
            # 구조 1: {"status": "ok", "data": {"list": [...]}}
            if "data" in data and isinstance(data["data"], dict):
                video_list = data["data"].get("list", [])
            # 구조 2: {"data": [...]}
            elif "data" in data and isinstance(data["data"], list):
                video_list = data["data"]
            # 구조 3: {"list": [...]}
            elif "list" in data:
                video_list = data["list"]
            # 구조 4: {"items": [...]}
            elif "items" in data:
                video_list = data["items"]
        elif isinstance(data, list):
            # 구조 5: 직접 리스트
            video_list = data

        if not video_list:
            return {
                "platform": "tiktok",
                "status": "error",
                "reason": "No video data in response",
                "response_keys": list(data.keys()) if isinstance(data, dict) else str(type(data)),
                "sample": str(data)[:300],
            }

        videos = []
        for i, video in enumerate(video_list):
            if not isinstance(video, dict):
                continue

            hashtags = list({
                tag["cha_name"]
                for tag in video.get("cha_list", [])
                if isinstance(tag, dict) and tag.get("cha_name")
            })
            hashtags += [
                tag["hashtag_name"]
                for tag in video.get("text_extra", [])
                if isinstance(tag, dict) and tag.get("type") == 1 and tag.get("hashtag_name") and tag["hashtag_name"] not in hashtags
            ]

            stats = video.get("statistics", video.get("stats", {}))
            plays = stats.get("play_count", stats.get("playCount", 0))
            likes = stats.get("digg_count", stats.get("diggCount", stats.get("likes", 0)))
            comments = stats.get("comment_count", stats.get("commentCount", stats.get("comments", 0)))
            shares = stats.get("share_count", stats.get("shareCount", stats.get("shares", 0)))
            saves = stats.get("collect_count", stats.get("collectCount", stats.get("saves", 0)))

            videos.append({
                "rank": i + 1,
                "description": video.get("desc", video.get("description", "")),
                "author": video.get("author", {}).get("unique_id", video.get("author", {}).get("uniqueId", "")) if isinstance(video.get("author"), dict) else str(video.get("author", "")),
                "url": video.get("share_url", video.get("shareUrl", "")),
                "hashtags": hashtags,
                "stats": {
                    "plays": plays,
                    "likes": likes,
                    "comments": comments,
                    "shares": shares,
                    "saves": saves,
                },
                "engagement_rate": round(((likes + comments + shares) / plays) * 100, 2) if plays > 0 else 0,
            })

        return {"platform": "tiktok", "videos": videos}

    except Exception as e:
        return {"platform": "tiktok", "status": "error", "reason": str(e)}
