#!/usr/bin/env python3
"""
Simple terminal interface for the Chemical Supplier Agent

Usage:
    python3 search.py "Chemical Name" "CAS-Number" [--exclude COUNTRIES | --only COUNTRIES]
    
Examples:
    python3 search.py "N-Methyl-2-pyrrolidone" "872-50-4"
    python3 search.py "Eucalyptol" "470-82-6" --exclude cn,de
    python3 search.py "Potassium methoxide" "865-33-8" --exclude="China,Germany"
    python3 search.py "Acetone" "67-64-1" --only us,ca
    python3 search.py "Ethanol" "64-17-5" --only="United States,United Kingdom"
"""

import sys
import argparse
from dotenv import load_dotenv
from app.agent import run_agent

# Load environment variables
load_dotenv()

# Country code mapping for convenience
COUNTRY_CODES = {
    'us': 'United States',
    'usa': 'United States',
    'uk': 'United Kingdom',
    'gb': 'United Kingdom',
    'de': 'Germany',
    'fr': 'France',
    'it': 'Italy',
    'es': 'Spain',
    'nl': 'Netherlands',
    'be': 'Belgium',
    'ch': 'Switzerland',
    'at': 'Austria',
    'se': 'Sweden',
    'dk': 'Denmark',
    'no': 'Norway',
    'fi': 'Finland',
    'ca': 'Canada',
    'au': 'Australia',
    'nz': 'New Zealand',
    'jp': 'Japan',
    'cn': 'China',
    'kr': 'South Korea',
    'in': 'India',
    'sg': 'Singapore',
    'hk': 'Hong Kong',
    'tw': 'Taiwan',
    'br': 'Brazil',
    'mx': 'Mexico',
    'ru': 'Russia'
}


def main():
    parser = argparse.ArgumentParser(
        description="Find chemical suppliers with evidence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 search.py "Eucalyptol" "470-82-6"
  python3 search.py "N-Methyl-2-pyrrolidone" "872-50-4" --exclude cn,de
  python3 search.py "Potassium methoxide" "865-33-8" --exclude="China,Germany"
  python3 search.py "Acetone" "67-64-1" --only us,ca
  python3 search.py "Ethanol" "64-17-5" --only="United States,United Kingdom"
        """
    )
    
    parser.add_argument("chemical_name", help="Name of the chemical to search for")
    parser.add_argument("cas", help="CAS number of the chemical")
    parser.add_argument(
        "--exclude", 
        type=str, 
        help="Comma-separated list of countries to exclude (codes or names). Examples: 'cn,de' or 'China,Germany'"
    )
    parser.add_argument(
        "--only", 
        type=str, 
        help="Comma-separated list of countries to include ONLY (codes or names). Examples: 'us,ca' or 'United States,Canada'"
    )
    
    args = parser.parse_args()
    
    chemical_name = args.chemical_name
    cas = args.cas
    
    # Validate that both --exclude and --only are not used together
    if args.exclude and args.only:
        print("Error: Cannot use both --exclude and --only flags together. Please choose one.")
        sys.exit(1)
    
    # Process exclude list
    excluded_countries = set()
    allowed_countries = set()
    
    if args.exclude:
        exclude_items = [item.strip().lower() for item in args.exclude.split(',')]
        for item in exclude_items:
            # Check if it's a country code
            if item in COUNTRY_CODES:
                excluded_countries.add(COUNTRY_CODES[item])
            else:
                # Treat as full country name (case insensitive)
                excluded_countries.add(item.title())
        
        if excluded_countries:
            print(f"Excluding suppliers from: {', '.join(sorted(excluded_countries))}")
            print()
    
    elif args.only:
        only_items = [item.strip().lower() for item in args.only.split(',')]
        for item in only_items:
            # Check if it's a country code
            if item in COUNTRY_CODES:
                allowed_countries.add(COUNTRY_CODES[item])
            else:
                # Treat as full country name (case insensitive)
                allowed_countries.add(item.title())
        
        if allowed_countries:
            print(f"Only including suppliers from: {', '.join(sorted(allowed_countries))}")
            print()
    
    print(f"Searching for: {chemical_name}")
    print(f"CAS Number: {cas}")
    print("This may take 1-2 minutes...")
    print()
    
    try:
        result = run_agent(chemical_name, cas, limit=10, excluded_countries=excluded_countries, allowed_countries=allowed_countries)
        
        # Print summary
        print(f"Found {len(result.suppliers)} suppliers")
        print("=" * 80)
        
        # Print each supplier
        for i, supplier in enumerate(result.suppliers, 1):
            print(f"\n{i}. {supplier.supplier_name}")
            print(f"   Website: {supplier.website}")
            print(f"   Country: {supplier.country or 'Unknown'}")
            
            if supplier.contact_email:
                status_indicator = {
                    "found": "[FOUND]",
                    "generated": "[PATTERN]"
                }.get(supplier.email_status, "[UNKNOWN]")
                print(f"   Email: {supplier.contact_email} {status_indicator}")
            else:
                print("   Email: Not found")
            
            print(f"   Evidence: {supplier.evidence_url}")
            print(f"   Confidence: {supplier.confidence_score}/10")
        
        # Save JSON output
        output_file = f"{chemical_name.replace(' ', '_')}_{cas.replace('-', '_')}.json"
        with open(output_file, 'w') as f:
            f.write(result.model_dump_json(indent=2))
        
        print(f"\nFull results saved to: {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
