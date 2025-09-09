"""Main agent orchestration for chemical supplier discovery."""
import concurrent.futures
from urllib.parse import urlparse
from typing import Dict

from .search_serpapi import search_candidates
from .scrape_playwright import scrape_and_extract
from .rerank import rerank_score
from .schema import SupplierHit, AgentResult


def calculate_confidence_score(
    search_result: Dict,
    scraped_data: Dict,
    rerank_score_val: float,
    cas: str
) -> float:
    """
    Calculate confidence score based on multiple signals.
    
    Args:
        search_result: Original search result with title/snippet
        scraped_data: Scraped page data
        rerank_score_val: Relevance score from reranker
        cas: CAS number being searched
        
    Returns:
        Confidence score between 0 and 10
    """
    score = 0.0
    
    # CAS exact match signals (high value)
    search_text = (search_result.get("title", "") + " " + 
                   search_result.get("snippet", "")).lower()
    
    if cas in search_text:
        score += 3.0  # CAS in search results
    
    # Evidence page type signals
    evidence_url = scraped_data.get("evidence_url", "").lower()
    if any(keyword in evidence_url for keyword in ["sds", "tds", "datasheet"]):
        score += 2.0  # Safety data sheet or technical data sheet
    elif any(keyword in evidence_url for keyword in ["catalog", "product"]):
        score += 1.5  # Product catalog or product page
    
    # Marketplace/directory signals
    if any(domain in evidence_url for domain in [
        "buyersguidechem.com", "chemondis.com", "thomasnet.com", 
        "chemspider.com", "molport.com"
    ]):
        score += 1.0  # Known chemical supplier directory
    
    # Reranker score (0-1 range, scale to 0-4 points)
    score += 4.0 * rerank_score_val
    
    # Bonus for having contact emails
    if scraped_data.get("emails"):
        score += 0.5
    
    # Cap at 10
    return min(10.0, round(score, 2))


def process_single_candidate(args) -> Dict:
    """Process a single search candidate. Used for parallel processing."""
    search_result, cas, query = args
    
    url = search_result["link"]
    
    # Scrape the page for CAS evidence
    scraped_data = scrape_and_extract(url, cas)
    if not scraped_data:
        return None
    
    # Calculate rerank score
    text_for_rerank = (search_result.get("title", "") + " " + 
                       search_result.get("snippet", ""))
    rerank_score_val = rerank_score(query, text_for_rerank)
    
    # Calculate confidence score
    confidence = calculate_confidence_score(
        search_result, scraped_data, rerank_score_val, cas
    )
    
    # Use scraped emails or generate common patterns
    emails = scraped_data.get("emails", [])
    if emails:
        email = emails[0]  # Use first found email
        email_status = "found"
    else:
        # Generate common email pattern
        domain = urlparse(scraped_data["website"]).netloc
        email = f"info@{domain}"
        email_status = "generated"
    
    return {
        "supplier_name": scraped_data["supplier_name"],
        "website": scraped_data["website"],
        "contact_email": email,
        "email_status": email_status,
        "evidence_url": scraped_data["evidence_url"],
        "confidence_score": confidence,
        "domain": urlparse(scraped_data["website"]).netloc,
        "country": scraped_data.get("country", "Unknown")
    }


def run_agent(
    chemical_name: str, 
    cas: str, 
    limit: int = 10,
    max_candidates: int = 40,
    max_workers: int = 5,
    excluded_countries: set = None,
    allowed_countries: set = None
) -> AgentResult:
    """
    Main agent function to find chemical suppliers.
    
    Args:
        chemical_name: Name of the chemical (e.g., "N-Methyl-2-pyrrolidone")
        cas: CAS number (e.g., "872-50-4")
        limit: Number of suppliers to return
        max_candidates: Maximum search candidates to process
        max_workers: Maximum parallel workers for scraping
        excluded_countries: Set of country names to exclude from results
        allowed_countries: Set of country names to include ONLY (takes precedence over excluded_countries)
        
    Returns:
        AgentResult with top suppliers found
    """
    if excluded_countries is None:
        excluded_countries = set()
    if allowed_countries is None:
        allowed_countries = set()
    query = f"{chemical_name} {cas}"
    print(f"Searching for: {query}")
    
    # Step 1: Search for candidates
    print("Searching for supplier candidates...")
    candidates = search_candidates(chemical_name, cas, num_pages=2)
    candidates = candidates[:max_candidates]  # Limit candidates to process
    print(f"Found {len(candidates)} search candidates")
    
    if not candidates:
        return AgentResult(
            chemical_name=chemical_name,
            cas=cas,
            suppliers=[]
        )
    
    # Step 2: Process candidates in parallel
    print("Scraping candidates for evidence...")
    results = []
    
    # Prepare arguments for parallel processing
    candidate_args = [(candidate, cas, query) for candidate in candidates]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_candidate = {
            executor.submit(process_single_candidate, args): args[0] 
            for args in candidate_args
        }
        
        for future in concurrent.futures.as_completed(future_to_candidate):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                candidate = future_to_candidate[future]
                print(f"Error processing {candidate.get('link', 'unknown')}: {e}")
    
    print(f"Successfully processed {len(results)} suppliers with evidence")
    
    # Step 3: Filter by country preferences
    if allowed_countries:
        # Only include suppliers from allowed countries
        before_filter = len(results)
        results = [r for r in results if r.get("country", "Unknown") in allowed_countries]
        filtered_count = before_filter - len(results)
        if filtered_count > 0:
            print(f"Filtered to only suppliers from allowed countries ({filtered_count} excluded)")
    elif excluded_countries:
        # Exclude suppliers from specific countries
        before_filter = len(results)
        results = [r for r in results if r.get("country", "Unknown") not in excluded_countries]
        filtered_count = before_filter - len(results)
        if filtered_count > 0:
            print(f"Filtered out {filtered_count} suppliers from excluded countries")
    
    # Step 4: Deduplicate by domain and sort by confidence
    seen_domains = set()
    unique_results = []
    
    # Sort by confidence score first
    results.sort(key=lambda x: x["confidence_score"], reverse=True)
    
    for result in results:
        domain = result["domain"]
        if domain not in seen_domains:
            seen_domains.add(domain)
            unique_results.append(result)
            
            if len(unique_results) >= limit:
                break
    
    # Step 5: Convert to Pydantic models
    suppliers = []
    for result in unique_results:
        try:
            supplier = SupplierHit(
                supplier_name=result["supplier_name"],
                website=result["website"],
                contact_email=result["contact_email"],
                email_status=result["email_status"],
                evidence_url=result["evidence_url"],
                confidence_score=result["confidence_score"],
                country=result.get("country", "Unknown")
            )
            suppliers.append(supplier)
        except Exception as e:
            print(f"Error creating SupplierHit: {e}")
            continue
    
    print(f"Returning {len(suppliers)} unique suppliers")
    
    return AgentResult(
        chemical_name=chemical_name,
        cas=cas,
        suppliers=suppliers
    )
