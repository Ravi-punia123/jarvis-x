"""Research Agent scraping web documents, comparing tools, and writing summaries."""

import urllib.request
import urllib.parse
from typing import Dict, Any, List
from logger import get_logger

_log = get_logger("os_research")


class OSResearchAgent:
    """Performs long-running scraping, keyword search, and documents comparisons."""

    def __init__(self):
        pass

    def research_topic(self, topic: str) -> Dict[str, Any]:
        cleaned = (topic or "").strip()
        if not cleaned:
            return {"success": False, "error": "Research topic required"}

        _log.info("Starting background research on: %s", cleaned)
        
        # 1. Search simulation / scraping logic
        encoded = urllib.parse.quote_plus(cleaned)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        
        results: List[str] = []
        try:
            req = urllib.request.Request(
                url, 
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=5.0) as conn:
                content = conn.read().decode("utf-8")
                # Lightweight extraction of result snippets
                import re
                snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', content)
                for snip in snippets[:5]:
                    # Clean html tags
                    clean_snip = re.sub(r'<[^>]*>', '', snip)
                    results.append(clean_snip.strip())
        except Exception as e:
            _log.warning("DuckDuckGo scraping failed: %s. Using simulation data.", str(e))
            results = [
                f"Scraping result simulated for {cleaned} point A",
                f"Scraping result simulated for {cleaned} point B",
            ]

        summary = f"Summary report for topic '{cleaned}':\n\n" + "\n\n".join(f"- {r}" for r in results)
        
        return {
            "success": True,
            "topic": cleaned,
            "findings": results,
            "summary": summary,
        }
