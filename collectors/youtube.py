"""YouTube 트렌딩 수집 — RSS 피드 기반, API 키 불필요"""
import requests
from bs4 import BeautifulSoup
import time

# 모드별 검색 쿼리
SEARCHES = {
    "fashion": {
        "KR": ["패션 트렌드", "코디 룩북", "패션 하울"],
        "US": ["fashion trend", "outfit lookbook", "fashion haul"],
        "JP": ["ファッション トレンド", "コーデ", "ファッション"],
    },
    "general": {
        "KR": ["트렌드", "인기"],
        "US": ["trending"],
        "JP": ["トレンド"],
    },
}

# YouTube 인기 채널 RSS (트렌딩 대안)
TRENDING_FEEDS = {
    "KR": "https://www.youtube.com/feeds/videos.xml?chart=most_popular&gl=KR",
    "US": "https://www.youtube.com/feeds/videos.xml?chart=most_popular&gl=US",
    "JP": "https://www.youtube.com/feeds/videos.xml?chart=most_popular&gl=JP",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AIMEYES-TrendBot/1.0)",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


def _fetch_rss_feed(url):
    """YouTube RSS 피드에서 영상 목록 수집"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "lxml-xml")
        entries = soup.find_all("entry")
        videos = []
        for entry in entries:
            video_id = ""
            yt_id = entry.find("yt:videoId")
            if yt_id:
                video_id = yt_id.text
            elif entry.find("id"):
                id_text = entry.find("id").text
                if "video:" in id_text:
                    video_id = id_text.split("video:")[-1]

            title = entry.find("title").text if entry.find("title") else ""
            author = entry.find("author")
            channel = author.find("name").text if author and author.find("name") else ""
            published = entry.find("published").text if entry.find("published") else ""

            # 조회수 (media:statistics)
            views = 0
            stats = entry.find("media:statistics")
            if stats and stats.get("views"):
                views = int(stats["views"])

            videos.append({
                "rank": len(videos) + 1,
                "title": title,
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
                "channel": channel,
                "views": views,
                "published": published,
            })
        return videos
    except Exception:
        return []


def _search_rss(query):
    """YouTube 검색 RSS로 키워드 검색"""
    url = f"https://www.youtube.com/feeds/videos.xml?search_query={requests.utils.quote(query)}"
    return _fetch_rss_feed(url)


def collect(mode="fashion"):
    queries = SEARCHES.get(mode, SEARCHES["fashion"])
    results = {}

    # 1. 각 국가별 트렌딩 피드
    for code, feed_url in TRENDING_FEEDS.items():
        trending = _fetch_rss_feed(feed_url)
        if trending:
            results[f"{code}_trending"] = trending[:15]
        time.sleep(1)

    # 2. 키워드 검색
    for code, keyword_list in queries.items():
        search_results = []
        for keyword in keyword_list:
            videos = _search_rss(keyword)
            for v in videos:
                if v not in search_results:
                    search_results.append(v)
            time.sleep(1)
        # 중복 제거 후 상위 20개
        seen = set()
        unique = []
        for v in search_results:
            vid = v.get("video_id", "")
            if vid and vid not in seen:
                seen.add(vid)
                v["rank"] = len(unique) + 1
                unique.append(v)
        results[f"{code}_search"] = unique[:20]

    return {"platform": "youtube", "mode": mode, "regions": results}
