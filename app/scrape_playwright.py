"""Playwright-based web scraping with CAS number matching."""
import re
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse, urljoin
from typing import Dict, Optional, Set, List


def _extract_emails(text: str) -> Set[str]:
    """Extract email addresses from text using regex."""
    email_pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    return set(re.findall(email_pattern, text))


def _get_domain(url: str) -> str:
    """Extract domain from URL."""
    return urlparse(url).netloc


def _detect_country(url: str, page_text: str) -> str:
    """
    Detect supplier country from URL and page content.
    
    Args:
        url: Website URL
        page_text: Page content text
        
    Returns:
        Country name or "Unknown"
    """
    # TLD to country mapping
    tld_map = {
        '.com': 'United States',
        '.us': 'United States', 
        '.uk': 'United Kingdom',
        '.co.uk': 'United Kingdom',
        '.de': 'Germany',
        '.fr': 'France',
        '.it': 'Italy',
        '.es': 'Spain',
        '.nl': 'Netherlands',
        '.be': 'Belgium',
        '.ch': 'Switzerland',
        '.at': 'Austria',
        '.se': 'Sweden',
        '.dk': 'Denmark',
        '.no': 'Norway',
        '.fi': 'Finland',
        '.ca': 'Canada',
        '.au': 'Australia',
        '.nz': 'New Zealand',
        '.jp': 'Japan',
        '.cn': 'China',
        '.kr': 'South Korea',
        '.in': 'India',
        '.sg': 'Singapore',
        '.hk': 'Hong Kong',
        '.tw': 'Taiwan',
        '.br': 'Brazil',
        '.mx': 'Mexico',
        '.ru': 'Russia'
    }
    
    # Check URL patterns first
    domain = _get_domain(url).lower()
    
    # Check for country-specific subdomains
    if '.com/' in url:
        if '/us/' in url.lower() or 'usa.' in domain:
            return 'United States'
        elif '/uk/' in url.lower() or 'gb.' in domain:
            return 'United Kingdom' 
        elif '/de/' in url.lower():
            return 'Germany'
        elif '/fr/' in url.lower():
            return 'France'
        elif '/ca/' in url.lower():
            return 'Canada'
        elif '/au/' in url.lower():
            return 'Australia'
        elif '/jp/' in url.lower():
            return 'Japan'
        elif '/cn/' in url.lower() or '/china/' in url.lower():
            return 'China'
        elif '/in/' in url.lower() or '/india/' in url.lower():
            return 'India'
        elif '/sg/' in url.lower():
            return 'Singapore'
    
    # Check TLD
    for tld, country in tld_map.items():
        if domain.endswith(tld):
            return country
    
    # Text-based detection (look for country mentions in addresses)
    text_lower = page_text.lower()
    
    # Country patterns in text
    country_patterns = {
        'United States': [r'\busa\b', r'united states', r'\bu\.s\.a\b', r'\bus\b', r'america'],
        'United Kingdom': [r'united kingdom', r'\buk\b', r'britain', r'england', r'scotland', r'wales'],
        'Germany': [r'germany', r'deutschland', r'german'],
        'France': [r'france', r'french', r'français'],
        'China': [r'china', r'chinese', r'中国', r'beijing', r'shanghai'],
        'Japan': [r'japan', r'japanese', r'日本', r'tokyo', r'osaka'],
        'India': [r'india', r'indian', r'mumbai', r'delhi', r'bangalore'],
        'Canada': [r'canada', r'canadian', r'toronto', r'vancouver'],
        'Australia': [r'australia', r'australian', r'sydney', r'melbourne'],
        'Netherlands': [r'netherlands', r'dutch', r'amsterdam'],
        'Switzerland': [r'switzerland', r'swiss', r'zurich'],
        'Singapore': [r'singapore', r'singaporean'],
        'South Korea': [r'south korea', r'korea', r'korean', r'seoul'],
        'Italy': [r'italy', r'italian', r'milano', r'rome'],
        'Spain': [r'spain', r'spanish', r'madrid', r'barcelona'],
        'Belgium': [r'belgium', r'belgian', r'brussels'],
        'Sweden': [r'sweden', r'swedish', r'stockholm'],
        'Denmark': [r'denmark', r'danish', r'copenhagen'],
        'Norway': [r'norway', r'norwegian', r'oslo'],
        'Finland': [r'finland', r'finnish', r'helsinki']
    }
    
    # Look for country mentions in contact/about sections
    for country, patterns in country_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return country
    
    return 'Unknown'


# Keywords that indicate evidence pages (SDS, catalogs, etc.)
KEY_LINK_HINTS = ("sds", "tds", "safety data", "product", "catalog", "datasheet")


def scrape_and_extract(url: str, cas: str) -> Optional[Dict]:
    """
    Scrape a webpage and extract supplier information with CAS evidence.
    
    Args:
        url: URL to scrape
        cas: CAS number to look for as evidence
        
    Returns:
        Dict with supplier info and evidence URL, or None if no evidence found
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Set timeout and load page
            page.goto(url, timeout=30000)
            page.wait_for_load_state("domcontentloaded")
            
            # Extract page content
            html = page.content()
            text = page.inner_text("body")
            emails = _extract_emails(text)
            
            # Look for CAS number on current page first
            evidence_url = None
            if cas in text:
                evidence_url = url
            else:
                # Follow one hop to find evidence pages (SDS, catalogs, etc.)
                links = [a.get_attribute("href") for a in page.locator("a").all()]
                links = links[:150]  # Limit to avoid excessive crawling
                
                # Convert relative URLs to absolute
                absolute_links = []
                for link in links:
                    if link and not link.startswith("mailto:"):
                        try:
                            absolute_links.append(urljoin(url, link))
                        except Exception:
                            continue
                
                # Check promising links for CAS evidence
                for link in absolute_links:
                    if any(hint in link.lower() for hint in KEY_LINK_HINTS):
                        try:
                            page.goto(link, timeout=20000)
                            page.wait_for_load_state("domcontentloaded")
                            linked_text = page.inner_text("body")
                            
                            if cas in linked_text:
                                evidence_url = link
                                # Also collect emails from evidence page
                                emails.update(_extract_emails(linked_text))
                                break
                        except Exception:
                            continue
            
            # Extract supplier name from page title or domain
            try:
                supplier_name = page.title().split("|")[0].strip()[:120]
                if not supplier_name:
                    supplier_name = _get_domain(url)
            except Exception:
                supplier_name = _get_domain(url)
            
            browser.close()
            
            # Only return results if we found CAS evidence
            if evidence_url:
                # Detect country from URL and page content
                country = _detect_country(url, text)
                
                return {
                    "supplier_name": supplier_name,
                    "website": f"https://{_get_domain(url)}",
                    "evidence_url": evidence_url,
                    "emails": list(emails),
                    "country": country
                }
            
        except Exception as e:
            print(f"Scraping error for {url}: {e}")
            browser.close()
    
    return None


def batch_scrape(urls: List[str], cas: str, max_workers: int = 5) -> List[Dict]:
    """
    Scrape multiple URLs in parallel.
    
    Args:
        urls: List of URLs to scrape
        cas: CAS number to look for
        max_workers: Maximum number of concurrent scraping operations
        
    Returns:
        List of extracted supplier data (only those with evidence)
    """
    import concurrent.futures
    
    results = []
    
    def scrape_single(url):
        return scrape_and_extract(url, cas)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(scrape_single, url): url for url in urls}
        
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                url = futures[future]
                print(f"Error processing {url}: {e}")
    
    return results
