import scrapy
import re
import json
from datetime import datetime
from urllib.parse import urlencode
from shop_scraper.items import ProductItem


class WalmartSpider(scrapy.Spider):
    name = "walmart"
    allowed_domains = ["walmart.com"]
    
    def __init__(self, product=None, output_file=None, *args, **kwargs):
        super(WalmartSpider, self).__init__(*args, **kwargs)
        self.product = product
        self.output_file = output_file
        
        if not self.product:
            raise ValueError("Please provide a product name using -a product='product name'")
    
    def start_requests(self):
        # Construct the search URL
        params = {
            'q': self.product,
            'sort': 'best_match'
        }
        search_url = f"https://www.walmart.com/search?{urlencode(params)}"
        
        yield scrapy.Request(
            url=search_url,
            callback=self.parse_search_results,
            meta={'search_term': self.product}
        )
    
    def parse_search_results(self, response):
        # Extract product listings
        products = response.css('div[data-item-id]')
        
        for product in products:
            # Extract product URL
            product_url = product.css('a.absolute::attr(href)').get()
            if product_url:
                full_url = response.urljoin(product_url)
                
                yield scrapy.Request(
                    url=full_url,
                    callback=self.parse_product,
                    meta={'search_term': response.meta.get('search_term')}
                )
        
        # Follow pagination if available
        next_page = response.css('a[aria-label="Next Page"]::attr(href)').get()
        if next_page:
            yield scrapy.Request(
                url=response.urljoin(next_page),
                callback=self.parse_search_results,
                meta={'search_term': response.meta.get('search_term')}
            )
    
    def parse_product(self, response):
        # Try to extract product data from JSON-LD
        json_ld = response.css('script[type="application/ld+json"]::text').getall()
        product_data = None
        
        for json_text in json_ld:
            try:
                data = json.loads(json_text)
                if '@type' in data and data['@type'] == 'Product':
                    product_data = data
                    break
            except json.JSONDecodeError:
                continue
        
        # Extract product information from JSON-LD if available
        if product_data:
            product_name = product_data.get('name')
            
            # Extract price
            price = None
            if 'offers' in product_data and 'price' in product_data['offers']:
                price = float(product_data['offers']['price'])
            
            # Extract currency
            currency = 'USD'
            if 'offers' in product_data and 'priceCurrency' in product_data['offers']:
                currency = product_data['offers']['priceCurrency']
            
            # Extract availability
            availability = None
            if 'offers' in product_data and 'availability' in product_data['offers']:
                availability = product_data['offers']['availability'].replace('http://schema.org/', '')
            
            # Extract rating
            rating = None
            if 'aggregateRating' in product_data and 'ratingValue' in product_data['aggregateRating']:
                rating = float(product_data['aggregateRating']['ratingValue'])
            
            # Extract reviews count
            reviews_count = None
            if 'aggregateRating' in product_data and 'reviewCount' in product_data['aggregateRating']:
                reviews_count = int(product_data['aggregateRating']['reviewCount'])
            
            # Extract image URL
            image_url = None
            if 'image' in product_data:
                if isinstance(product_data['image'], list):
                    image_url = product_data['image'][0]
                else:
                    image_url = product_data['image']
            
            # Extract description
            description = product_data.get('description')
            
            # Extract product ID
            product_id = None
            if 'sku' in product_data:
                product_id = product_data['sku']
            
        else:
            # Fallback to CSS selectors if JSON-LD is not available
            product_name = response.css('h1.f3.b.lh-copy.dark-gray.mt1.mb2::text').get()
            if product_name:
                product_name = product_name.strip()
            
            # Extract price
            price_text = response.css('span.b.black.f1.mr1::text').get()
            price = None
            if price_text:
                price_match = re.search(r'([\d,]+\.\d+)', price_text)
                if price_match:
                    price = float(price_match.group(1).replace(',', ''))
            
            # Default values
            currency = 'USD'
            product_id = response.css('div[data-testid="product-details"] span:contains("Item #")::text').get()
            if product_id:
                product_id = product_id.replace('Item #', '').strip()
            
            availability = response.css('div[data-testid="fulfillment-shipping-text"]::text').get()
            if availability:
                availability = availability.strip()
            
            rating_text = response.css('span.f7.rating-number::text').get()
            rating = None
            if rating_text:
                rating_match = re.search(r'(\d+(\.\d+)?)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
            
            reviews_count_text = response.css('a[data-testid="product-reviews-link"] span::text').get()
            reviews_count = None
            if reviews_count_text:
                reviews_match = re.search(r'([\d,]+)', reviews_count_text)
                if reviews_match:
                    reviews_count = int(reviews_match.group(1).replace(',', ''))
            
            image_url = response.css('img.db.center.mw100.mh100::attr(src)').get()
            
            description = response.css('div[data-testid="product-description"] div::text').get()
            if description:
                description = description.strip()
        
        # Skip if no product name or price found
        if not product_name or not price:
            return
        
        # Create product item
        item = ProductItem(
            product_name=product_name,
            price=price,
            currency=currency,
            url=response.url,
            website='Walmart',
            product_id=product_id,
            description=description,
            image_url=image_url,
            availability=availability,
            rating=rating,
            reviews_count=reviews_count,
            search_term=response.meta.get('search_term'),
            timestamp=datetime.now()
        )
        
        yield item 