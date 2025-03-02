import scrapy
import re
from datetime import datetime
from urllib.parse import urlencode
from shop_scraper.items import ProductItem


class AmazonSpider(scrapy.Spider):
    name = "amazon"
    allowed_domains = ["amazon.com"]
    
    def __init__(self, product=None, output_file=None, *args, **kwargs):
        super(AmazonSpider, self).__init__(*args, **kwargs)
        self.product = product
        self.output_file = output_file
        
        if not self.product:
            raise ValueError("Please provide a product name using -a product='product name'")
    
    def start_requests(self):
        # Construct the search URL
        params = {
            'k': self.product,
            'ref': 'nb_sb_noss'
        }
        search_url = f"https://www.amazon.com/s?{urlencode(params)}"
        
        yield scrapy.Request(
            url=search_url,
            callback=self.parse_search_results,
            meta={'search_term': self.product}
        )
    
    def parse_search_results(self, response):
        # Extract product listings
        products = response.css('div[data-component-type="s-search-result"]')
        
        for product in products:
            # Extract product URL
            product_url = product.css('a.a-link-normal.s-no-outline::attr(href)').get()
            if product_url:
                full_url = response.urljoin(product_url)
                
                yield scrapy.Request(
                    url=full_url,
                    callback=self.parse_product,
                    meta={'search_term': response.meta.get('search_term')}
                )
        
        # Follow pagination if available
        next_page = response.css('a.s-pagination-item.s-pagination-next::attr(href)').get()
        if next_page:
            yield scrapy.Request(
                url=response.urljoin(next_page),
                callback=self.parse_search_results,
                meta={'search_term': response.meta.get('search_term')}
            )
    
    def parse_product(self, response):
        # Extract product information
        product_name = response.css('#productTitle::text').get()
        if product_name:
            product_name = product_name.strip()
        
        # Extract price
        price_whole = response.css('span.a-price-whole::text').get()
        price_fraction = response.css('span.a-price-fraction::text').get()
        
        price = None
        if price_whole and price_fraction:
            price = float(f"{price_whole.strip().replace(',', '')}{price_fraction.strip()}")
        elif price_whole:
            price = float(price_whole.strip().replace(',', ''))
        else:
            # Try alternative price selectors
            price_text = response.css('.a-offscreen::text').get()
            if price_text:
                price_match = re.search(r'[\d,]+\.\d+', price_text)
                if price_match:
                    price = float(price_match.group().replace(',', ''))
        
        # Skip if no product name or price found
        if not product_name or not price:
            return
        
        # Extract other product information
        product_id = response.css('input#ASIN::attr(value)').get()
        
        # Extract availability
        availability = response.css('#availability span::text').get()
        if availability:
            availability = availability.strip()
        
        # Extract rating
        rating_text = response.css('span.a-icon-alt::text').get()
        rating = None
        if rating_text:
            rating_match = re.search(r'(\d+(\.\d+)?)', rating_text)
            if rating_match:
                rating = float(rating_match.group(1))
        
        # Extract reviews count
        reviews_count_text = response.css('#acrCustomerReviewText::text').get()
        reviews_count = None
        if reviews_count_text:
            reviews_match = re.search(r'([\d,]+)', reviews_count_text)
            if reviews_match:
                reviews_count = int(reviews_match.group(1).replace(',', ''))
        
        # Extract image URL
        image_url = response.css('#landingImage::attr(src)').get()
        
        # Extract description
        description = ' '.join(response.css('#feature-bullets .a-list-item::text').getall())
        if description:
            description = description.strip()
        
        # Create product item
        item = ProductItem(
            product_name=product_name,
            price=price,
            currency='USD',
            url=response.url,
            website='Amazon',
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