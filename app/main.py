"""Command-line interface for the chemical supplier agent."""
import argparse
import json
import os
import sys
from dotenv import load_dotenv

from .agent import run_agent


def main():
    """Main CLI entry point."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Check required environment variables
    required_keys = ["SERPAPI_KEY"]
    missing_keys = [key for key in required_keys if not os.environ.get(key)]
    
    if missing_keys:
        print(f"❌ Missing required environment variables: {', '.join(missing_keys)}")
        print("Please create a .env file based on env.example")
        sys.exit(1)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Find chemical suppliers using autonomous web search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app.main --name "N-Methyl-2-pyrrolidone" --cas "872-50-4"
  python -m app.main --name "Polysorbate 80" --cas "9005-65-6" --limit 5
        """
    )
    
    parser.add_argument(
        "--name", 
        required=True,
        help="Chemical name (e.g., 'N-Methyl-2-pyrrolidone')"
    )
    
    parser.add_argument(
        "--cas", 
        required=True,
        help="CAS number (e.g., '872-50-4')"
    )
    
    parser.add_argument(
        "--limit", 
        type=int, 
        default=10,
        help="Number of suppliers to return (default: 10)"
    )
    
    parser.add_argument(
        "--output", 
        choices=["json", "table"],
        default="json",
        help="Output format (default: json)"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    try:
        # Run the agent
        result = run_agent(
            chemical_name=args.name,
            cas=args.cas,
            limit=args.limit
        )
        
        # Output results
        if args.output == "json":
            print(result.model_dump_json(indent=2))
        elif args.output == "table":
            print_table_output(result, args.verbose)
            
    except KeyboardInterrupt:
        print("\n⚠️ Search interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def print_table_output(result, verbose=False):
    """Print results in a human-readable table format."""
    print(f"\n🧪 Chemical: {result.chemical_name}")
    print(f"🔢 CAS: {result.cas}")
    print(f"📊 Found {len(result.suppliers)} suppliers\n")
    
    if not result.suppliers:
        print("No suppliers found.")
        return
    
    # Print table header
    print("=" * 100)
    print(f"{'#':<3} {'Supplier':<30} {'Confidence':<10} {'Email Status':<12} {'Website':<30}")
    print("=" * 100)
    
    # Print suppliers
    for i, supplier in enumerate(result.suppliers, 1):
        # Truncate long names
        name = supplier.supplier_name[:29] + "…" if len(supplier.supplier_name) > 30 else supplier.supplier_name
        website = str(supplier.website)[:29] + "…" if len(str(supplier.website)) > 30 else str(supplier.website)
        email_status = supplier.email_status or "unknown"
        
        print(f"{i:<3} {name:<30} {supplier.confidence_score:<10} {email_status:<12} {website:<30}")
        
        if verbose:
            if supplier.contact_email:
                print(f"    📧 Email: {supplier.contact_email}")
            print(f"    🔗 Evidence: {supplier.evidence_url}")
            print()


if __name__ == "__main__":
    main()
