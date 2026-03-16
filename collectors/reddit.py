"""Reddit 인기 게시물 수집 — 공개 JSON API, 키 불필요"""
import requests
import time

_UA = {"User-Agent": "AIMEYES-TrendBot/1.0 (trend data collection)"}

SUBREDDITS = {
    "fashion": {
        "fashion": "패션",
        "streetwear": "스트리트웨어",
        "malefashionadvice": "남성 패션",
        "femalefashionadvice": "여성 패션",
        "womensstreetwear": "여성 스트릿",
    },
    "general": {
        "popular": "전체 인기",
        "trending": "트렌딩",
    },
}


def _fetch_subreddit(name, limit=25):
    url = f"https://www.reddit.com/r/{name}/hot.json?limit={limit}"
    r = requests.get(url, headers=_UA, timeout=15)
    if r.status_code != 200:
        return []

    data = r.json()
    posts = []
    for i, child in enumerate(data.get("data", {}).get("children", [])):
        post = child.get("data", {})
        if post.get("stickied"):
            continue
        posts.append({
            "rank": len(posts) + 1,
            "title": post.get("title", ""),
            "subreddit": post.get("subreddit", name),
            "url": f"https://reddit.com{post.get('permalink', '')}",
            "score": post.get("score", 0),
            "num_comments": post.get("num_comments", 0),
            "author": post.get("author", ""),
            "created_utc": post.get("created_utc", 0),
        })
    return posts


def collect(mode="fashion"):
    subs = SUBREDDITS.get(mode, SUBREDDITS["fashion"])
    results = {}
    for sub, label in subs.items():
        try:
            results[sub] = _fetch_subreddit(sub)
        except Exception as e:
            results[sub] = {"error": str(e)}
        time.sleep(6)  # Reddit rate limit: ~10 req/min for unauthenticated

    return {"platform": "reddit", "mode": mode, "subreddits": results}
