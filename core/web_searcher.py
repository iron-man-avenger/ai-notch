import html
import re
from typing import List, Dict, Any, Optional
import requests

def search_web_organic(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Performs a fast, reliable, organic web search via DuckDuckGo without requiring API keys.
    Returns a list of dicts with 'title', 'snippet', and 'url'.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://duckduckgo.com/",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    results: List[Dict[str, str]] = []

    try:
        resp = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": clean_query, "b": ""},
            headers=headers,
            timeout=5.0
        )
        if resp.status_code == 200:
            # Match each result block using div with class containing result__body
            # Example: <div class="web-result ..."> or <div class="... result__body ...">
            body_parts = re.split(r'class="[^"]*result__body[^"]*"', resp.text)
            for part in body_parts[1:max_results + 1]:
                # Extract title and url from result__a
                title_match = re.search(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', part, re.DOTALL)
                link_url = ""
                raw_title = ""
                if title_match:
                    raw_url = title_match.group(1)
                    raw_title = title_match.group(2)
                    # Often DuckDuckGo wraps url in /l/?kh=-1&uddg=<encoded_url>
                    if "uddg=" in raw_url:
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query)
                        if "uddg" in parsed:
                            link_url = parsed["uddg"][0]
                    if not link_url:
                        link_url = raw_url

                # Extract snippet from result__snippet
                snip_match = re.search(r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>', part, re.DOTALL)
                raw_snip = snip_match.group(1) if snip_match else ""

                clean_title = html.unescape(re.sub(r'<[^>]+>', '', raw_title)).strip()
                clean_snip = html.unescape(re.sub(r'<[^>]+>', '', raw_snip)).strip()

                if clean_title or clean_snip:
                    results.append({
                        "title": clean_title or "Search Result",
                        "snippet": clean_snip or "No snippet available",
                        "url": link_url
                    })
    except Exception as e:
        print(f"[Web Searcher Error] {e}")

    # Fallback to lite.duckduckgo.com if primary failed
    if not results:
        try:
            resp_lite = requests.post(
                "https://lite.duckduckgo.com/lite/",
                data={"q": clean_query},
                headers=headers,
                timeout=5.0
            )
            if resp_lite.status_code == 200:
                titles = re.findall(r'<a[^>]+class="result-link"[^>]*>(.*?)</a>', resp_lite.text, re.DOTALL)
                snippets = re.findall(r'<td[^>]+class="result-snippet"[^>]*>(.*?)</td>', resp_lite.text, re.DOTALL)
                for t, s in zip(titles[:max_results], snippets[:max_results]):
                    results.append({
                        "title": html.unescape(re.sub(r'<[^>]+>', '', t)).strip(),
                        "snippet": html.unescape(re.sub(r'<[^>]+>', '', s)).strip(),
                        "url": "https://duckduckgo.com"
                    })
        except Exception as e2:
            print(f"[Web Searcher Lite Error] {e2}")

    return results

def format_search_results_for_llm(results: List[Dict[str, str]]) -> str:
    """Formats search results into clean markdown context for Gemini."""
    if not results:
        return "No relevant search results found on the web."

    lines = []
    for i, res in enumerate(results, 1):
        url_part = f" ({res['url']})" if res.get('url') else ""
        lines.append(f"{i}. **{res['title']}**{url_part}\n   {res['snippet']}")
    return "\n\n".join(lines)
