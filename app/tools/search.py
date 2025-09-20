"""Web search tool with multiple providers."""

import hashlib
import json
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from diskcache import Cache

from app.config import settings


class SearchResult:
    """A single search result."""

    def __init__(self, title: str, url: str, snippet: str) -> None:
        self.title = title
        self.url = url
        self.snippet = snippet

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return {"title": self.title, "url": self.url, "snippet": self.snippet}


class SearchTool:
    """Web search tool with caching and multiple providers."""

    def __init__(self) -> None:
        self.cache = Cache(str(settings.data_dir / "cache" / "search"))
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def _cache_key(self, query: str, num_results: int) -> str:
        """Generate cache key for query."""
        key_data = f"{query}:{num_results}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _is_robots_allowed(self, url: str) -> bool:
        """Basic robots.txt check."""
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            response = self.session.get(robots_url, timeout=5)
            if response.status_code == 200:
                # Simple check - in production would use robotparser
                return "User-agent: *" in response.text and "Disallow: /" not in response.text
            return True
        except Exception:
            return True  # Allow if can't check

    def _search_serpapi(self, query: str, num_results: int) -> List[SearchResult]:
        """Search using SerpAPI."""
        if not settings.serpapi_api_key:
            raise ValueError("SerpAPI key not configured")

        url = "https://serpapi.com/search"
        params = {
            "engine": "google",
            "q": query,
            "api_key": settings.serpapi_api_key,
            "num": num_results,
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        print("data")
        print(data)

        results = []
        for item in data.get("organic_results", [])[:num_results]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                )
            )
        return results

    def _search_tavily(self, query: str, num_results: int) -> List[SearchResult]:
        """Search using Tavily."""
        if not settings.tavily_api_key:
            raise ValueError("Tavily API key not configured")

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": settings.tavily_api_key,
            "query": query,
            "max_results": num_results,
            "search_depth": "basic",
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("results", [])[:num_results]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                )
            )
        return results

    def _search_fallback(self, query: str, num_results: int) -> List[SearchResult]:
        """Fallback search using direct scraping (basic implementation)."""
        # This is a basic implementation - in production would need more robust scraping
        search_url = f"https://www.google.com/search?q={query}"
        
        try:
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            
            # Basic Google results parsing - very simplified
            for div in soup.find_all('div', class_='g')[:num_results]:
                title_elem = div.find('h3')
                link_elem = div.find('a')
                snippet_elem = div.find('span')
                
                if title_elem and link_elem:
                    title = title_elem.get_text()
                    url = link_elem.get('href', '')
                    snippet = snippet_elem.get_text() if snippet_elem else ""
                    
                    if url.startswith('/url?q='):
                        url = url.split('/url?q=')[1].split('&')[0]
                    
                    if url and self._is_robots_allowed(url):
                        results.append(SearchResult(title, url, snippet))
            
            return results
        except Exception as e:
            print(f"Fallback search failed: {e}")
            return []

    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Perform web search with caching."""
        # cache_key = self._cache_key(query, num_results)
        
        # # Check cache first
        # cached = self.cache.get(cache_key)
        # if cached:
        #     return [SearchResult(**item) for item in cached]

        # results = []
        
        # Try providers in order of preference
        try:
            if settings.tavily_api_key:
                results = self._search_tavily(query, num_results)
            elif settings.serpapi_api_key:
                results = self._search_serpapi(query, num_results)
            else:
                results = self._search_fallback(query, num_results)
        except Exception as e:
            print(f"Primary search failed: {e}")
            if not results:  # Try fallback if primary failed
                results = self._search_fallback(query, num_results)

        # # Cache results
        # if results:
        #     cache_data = [result.to_dict() for result in results]
        #     self.cache.set(cache_key, cache_data, expire=settings.cache_ttl_hours * 3600)

        return results

    def scrape_content(self, url: str, max_chars: int = 2000) -> Optional[str]:
        """Scrape content from a URL."""
        if not self._is_robots_allowed(url):
            return None

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text[:max_chars]
        except Exception as e:
            print(f"Failed to scrape {url}: {e}")
            return None
