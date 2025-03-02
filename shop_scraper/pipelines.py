# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import csv
import os
import warnings
from datetime import datetime
from itemadapter import ItemAdapter

try:
    from database.models import Product, db_session, SQLALCHEMY_AVAILABLE
except ImportError:
    warnings.warn("Database module not found. Database functionality will be limited.")
    SQLALCHEMY_AVAILABLE = False


class DatabasePipeline:
    """
    Pipeline for storing scraped items in the database
    """
    def process_item(self, item, spider):
        if not SQLALCHEMY_AVAILABLE:
            spider.logger.warning("SQLAlchemy is not available. Skipping database storage.")
            return item
            
        adapter = ItemAdapter(item)
        
        # Create a new Product instance
        product = Product(
            product_name=adapter.get('product_name'),
            price=float(adapter.get('price', 0.0)),
            website=adapter.get('website'),
            currency=adapter.get('currency', 'USD'),
            url=adapter.get('url'),
            product_id=adapter.get('product_id'),
            description=adapter.get('description'),
            image_url=adapter.get('image_url'),
            availability=adapter.get('availability'),
            rating=adapter.get('rating'),
            reviews_count=adapter.get('reviews_count'),
            search_term=adapter.get('search_term'),
            timestamp=adapter.get('timestamp', datetime.now())
        )
        
        # Add to database session
        db_session.add(product)
        db_session.commit()
        
        return item


class CSVExportPipeline:
    """
    Pipeline for exporting items to CSV
    """
    def __init__(self):
        self.file_handles = {}
        self.csv_writers = {}
        self.output_dir = 'data/exports'
        os.makedirs(self.output_dir, exist_ok=True)
    
    def open_spider(self, spider):
        if hasattr(spider, 'output_file'):
            output_file = spider.output_file
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"{spider.name}_{timestamp}.csv"
        
        file_path = os.path.join(self.output_dir, output_file)
        self.file_handles[spider.name] = open(file_path, 'w', newline='', encoding='utf-8')
        
        # Initialize CSV writer
        self.csv_writers[spider.name] = csv.writer(self.file_handles[spider.name])
        
        # Write header row
        self.csv_writers[spider.name].writerow([
            'Product Name', 'Price', 'Currency', 'Website', 'URL', 
            'Product ID', 'Availability', 'Rating', 'Reviews Count',
            'Search Term', 'Timestamp'
        ])
    
    def close_spider(self, spider):
        if spider.name in self.file_handles:
            self.file_handles[spider.name].close()
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        if spider.name in self.csv_writers:
            self.csv_writers[spider.name].writerow([
                adapter.get('product_name', ''),
                adapter.get('price', ''),
                adapter.get('currency', 'USD'),
                adapter.get('website', ''),
                adapter.get('url', ''),
                adapter.get('product_id', ''),
                adapter.get('availability', ''),
                adapter.get('rating', ''),
                adapter.get('reviews_count', ''),
                adapter.get('search_term', ''),
                adapter.get('timestamp', datetime.now()).isoformat() if isinstance(adapter.get('timestamp'), datetime) else adapter.get('timestamp', '')
            ])
        
        return item
