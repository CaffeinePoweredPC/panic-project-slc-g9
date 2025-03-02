#!/usr/bin/env python
import argparse
import os
import sys
import warnings
import traceback
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


try:
    import scrapy
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings
    print(f"Scrapy version: {scrapy.__version__}")
    print(f"Scrapy location: {scrapy.__file__}")
except ImportError as e:
    print(f"ERROR: Scrapy import error: {e}")
    print("Please install Scrapy with 'pip install scrapy'")
    print(f"Traceback: {traceback.format_exc()}")
    sys.exit(1)

try:
    from database.models import init_db, SQLALCHEMY_AVAILABLE
    # Initialize database
    init_db()
    print("Database module imported successfully")
except ImportError as e:
    print(f"WARNING: Database module import error: {e}")
    print(f"Traceback: {traceback.format_exc()}")
    warnings.warn("Database module not found. Database functionality will be limited.")
    SQLALCHEMY_AVAILABLE = False

# Import spiders
try:
    from shop_scraper.spiders.amazon import AmazonSpider
    from shop_scraper.spiders.ebay import EbaySpider
    from shop_scraper.spiders.walmart import WalmartSpider
    print("Spiders imported successfully")
except ImportError as e:
    print(f"ERROR: Failed to import spiders: {e}")
    print(f"Traceback: {traceback.format_exc()}")
    print("Make sure the shop_scraper package is properly installed.")
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description='E-Commerce Price Scraper')
    
    parser.add_argument('--product', '-p', type=str, required=True,
                        help='Product name to search for')
    
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Output CSV file name (default: auto-generated based on product name and timestamp)')
    
    parser.add_argument('--websites', '-w', type=str, nargs='+',
                        choices=['amazon', 'ebay', 'walmart', 'all'],
                        default=['all'],
                        help='Websites to scrape (default: all)')
    
    parser.add_argument('--limit', '-l', type=int, default=None,
                        help='Limit the number of products to scrape per website')
    
    return parser.parse_args()


def main():
    # Parse command-line arguments
    args = parse_args()
    
    # Generate output file name if not provided
    if args.output is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        product_slug = args.product.lower().replace(' ', '_')
        args.output = f"{product_slug}_{timestamp}.csv"
    
    # Ensure output directory exists
    os.makedirs('data/exports', exist_ok=True)
    
    # Get Scrapy settings
    settings = get_project_settings()
    
    # Set CLOSESPIDER_ITEMCOUNT if limit is provided
    if args.limit:
        settings.set('CLOSESPIDER_ITEMCOUNT', args.limit)
    
    # Initialize the crawler process
    process = CrawlerProcess(settings)
    
    # Determine which spiders to run
    spiders = []
    if 'all' in args.websites or 'amazon' in args.websites:
        spiders.append(AmazonSpider)
    if 'all' in args.websites or 'ebay' in args.websites:
        spiders.append(EbaySpider)
    if 'all' in args.websites or 'walmart' in args.websites:
        spiders.append(WalmartSpider)
    
    # Configure and start each spider
    for spider_class in spiders:
        process.crawl(
            spider_class,
            product=args.product,
            output_file=args.output
        )
    
    # Start the crawling process
    print(f"Starting to scrape {args.product} from {', '.join(args.websites)}")
    print(f"Results will be saved to data/exports/{args.output}")
    
    if not SQLALCHEMY_AVAILABLE:
        print("WARNING: SQLAlchemy is not available. Data will only be saved to CSV files.")
    
    process.start()
    
    print("Scraping completed!")
    if SQLALCHEMY_AVAILABLE:
        print(f"Data has been saved to data/exports/{args.output} and the database")
    else:
        print(f"Data has been saved to data/exports/{args.output}")


if __name__ == '__main__':
    main() 