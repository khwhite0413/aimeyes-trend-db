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
        data = resp.json()
        if data.get("status") != "ok" or "data" not in data:
            return {"platform": "tiktok", "status": "error", "reason": "Invalid API response"}

        videos = []
        for i, video in enumerate(data["data"].get("list", [])):
            hashtags = list({
                tag["cha_name"]
                for tag in video.get("cha_list", [])
                if tag.get("cha_name")
            })
            hashtags += [
                tag["hashtag_name"]
                for tag in video.get("text_extra", [])
                if tag.get("type") == 1 and tag.get("hashtag_name") and tag["hashtag_name"] not in hashtags
            ]

            stats = video.get("statistics", {})
            plays = stats.get("play_count", 0)
            likes = stats.get("digg_count", 0)
            comments = stats.get("comment_count", 0)
            shares = stats.get("share_count", 0)
            saves = stats.get("collect_count", 0)

            videos.append({
                "rank": i + 1,
                "description": video.get("desc", ""),
                "author": video.get("author", {}).get("unique_id", ""),
                "author_nickname": video.get("author", {}).get("nickname", ""),
                "url": video.get("share_url", ""),
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
