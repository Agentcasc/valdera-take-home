"""SerpAPI-based search functionality for chemical suppliers."""
import os
from typing import List, Dict

try:
    from serpapi.google_search import GoogleSearch
except ImportError:
    # Alternative import approach
    from serpapi import GoogleSearch

# Target high-signal supplier directories and marketplaces
DEFAULT_QUERIES = [
    '"{name}" "{cas}" supplier',
    '"{name}" "{cas}" SDS',
    '"{cas}" catalog',
    '"{cas}" site:buyersguidechem.com',
    '"{cas}" site:chemondis.com',
    '"{cas}" site:thomasnet.com',
    '"{cas}" site:chemspider.com vendor',
    '"{name}" CAS "{cas}" buy OR purchase',
]


def search_candidates(name: str, cas: str, num_pages: int = 2) -> List[Dict[str, str]]:
    """
    Search for chemical suppliers using multiple query patterns.
    
    Args:
        name: Chemical name (e.g., "N-Methyl-2-pyrrolidone")
        cas: CAS number (e.g., "872-50-4")
        num_pages: Number of search result pages per query
        
    Returns:
        List of candidate results with title, link, snippet
    """
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        raise ValueError("SERPAPI_KEY environment variable is required")
        
    queries = [q.format(name=name, cas=cas) for q in DEFAULT_QUERIES]
    results = []
    
    for query in queries:
        for start in range(0, num_pages * 10, 10):
            params = {
                "engine": "google",
                "q": query,
                "num": 10,
                "start": start,
                "api_key": api_key
            }
            
            try:
                search = GoogleSearch(params)
                data = search.get_dict()
                
                for item in data.get("organic_results", []):
                    results.append({
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "query": query
                    })
            except Exception as e:
                print(f"Search error for query '{query}': {e}")
                continue
    
    # Deduplicate by URL while preserving order
    seen = set()
    unique_results = []
    for result in results:
        url = result["link"]
        if url and url not in seen:
            seen.add(url)
            unique_results.append(result)
    
    return unique_results
