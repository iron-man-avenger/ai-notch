import requests
import time
from typing import List, Dict, Any, Optional

CACHED_NEWS: List[Dict[str, Any]] = []
LAST_FETCH_TIME: float = 0.0
LAST_QUERY: str = ""

TECH_KEYWORDS = [
    "python", "react", "typescript", "fastapi", "azure", "docker", 
    "gemini", "ai", "tailwind", "devops", "kubernetes", "sqlite",
    "javascript", "vite", "pyside", "antigravity"
]

def extract_tech_query(current_title: str, app_name: str) -> str:
    combined = f"{app_name} {current_title}".lower()
    found = []
    for kw in TECH_KEYWORDS:
        if kw in combined:
            found.append(kw)
            
    if found:
        return " ".join(found[:2])
    
    # Defaults based on common tooling
    if "code" in app_name.lower() or "antigravity" in app_name.lower():
        return "python ai"
    return "technology"

def fetch_relevant_news(current_title: str = "", app_name: str = "") -> List[Dict[str, Any]]:
    global CACHED_NEWS, LAST_FETCH_TIME, LAST_QUERY
    
    query = extract_tech_query(current_title, app_name)
    now = time.time()
    
    # Return cache if query is the same and fetched within 5 minutes
    if CACHED_NEWS and query == LAST_QUERY and (now - LAST_FETCH_TIME) < 300:
        return CACHED_NEWS

    articles = []
    
    # 1. Try Dev.to API (developer-focused)
    try:
        tag = query.split()[0] if query else "python"
        devto_url = f"https://dev.to/api/articles?tag={tag}&per_page=4"
        resp = requests.get(devto_url, timeout=4, verify=False)
        if resp.status_code == 200:
            for item in resp.json():
                articles.append({
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "source": "Dev.to",
                    "description": item.get("description", ""),
                    "published_at": item.get("readable_publish_date", ""),
                    "tag": tag
                })
    except Exception:
        pass

    # 2. Try Algolia Hacker News Search API
    try:
        hn_url = f"https://hn.algolia.com/api/v1/search?query={query}&tags=story&hitsPerPage=3"
        resp = requests.get(hn_url, timeout=4, verify=False)
        if resp.status_code == 200:
            hits = resp.json().get("hits", [])
            for hit in hits:
                story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                articles.append({
                    "title": hit.get("title"),
                    "url": story_url,
                    "source": "Hacker News",
                    "description": f"{hit.get('points', 0)} points | {hit.get('num_comments', 0)} comments",
                    "published_at": "Recent",
                    "tag": query
                })
    except Exception:
        pass

    # Fallback default items if external fetch failed
    if not articles:
        articles = [
            {
                "title": f"Latest best practices and tooling updates for {query.title()}",
                "url": "https://dev.to",
                "source": "Tech Radar",
                "description": f"Curated updates relevant to your active work in {app_name}.",
                "published_at": "Today",
                "tag": query
            }
        ]

    CACHED_NEWS = articles
    LAST_FETCH_TIME = now
    LAST_QUERY = query
    return CACHED_NEWS
