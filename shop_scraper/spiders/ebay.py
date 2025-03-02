import scrapy
import re
from datetime import datetime
from urllib.parse import urlencode
from shop_scraper.items import ProductItem


class EbaySpider(scrapy.Spider):
    name = "ebay"
    allowed_domains = ["ebay.com"]
    
    def __init__(self, product=None, output_file=None, *args, **kwargs):
        super(EbaySpider, self).__init__(*args, **kwargs)
        self.product = product
        self.output_file = output_file
        
        if not self.product:
            raise ValueError("Please provide a product name using -a product='product name'")
    
    def start_requests(self):
        # Construct the search URL
        params = {
            '_nkw': self.product,
            '_sacat': '0',
            'LH_TitleDesc': '0'
        }
        search_url = f"https://www.ebay.com/sch/i.html?{urlencode(params)}"
        
        yield scrapy.Request(
            url=search_url,
            callback=self.parse_search_results,
            meta={'search_term': self.product}
        )
    
    def parse_search_results(self, response):
        # Extract product listings
        products = response.css('li.s-item')
        
        for product in products:
            # Skip "More items like this" entry
            if product.css('.s-item__title--tagblock'):
                continue
                
            # Extract product URL
            product_url = product.css('a.s-item__link::attr(href)').get()
            if product_url:
                yield scrapy.Request(
                    url=product_url,
                    callback=self.parse_product,
                    meta={'search_term': response.meta.get('search_term')}
                )
        
        # Follow pagination if available
        next_page = response.css('a.pagination__next::attr(href)').get()
        if next_page:
            yield scrapy.Request(
                url=next_page,
                callback=self.parse_search_results,
                meta={'search_term': response.meta.get('search_term')}
            )
    
    def parse_product(self, response):
        # Extract product information
        product_name = response.css('h1.x-item-title__mainTitle span::text').get()
        if not product_name:
            # Try alternative selector
            product_name = response.css('h1.it-ttl::text').get()
        
        if product_name:
            product_name = product_name.strip()
        
        # Extract price
        price_text = response.css('div.x-price-primary span::text').get()
        if not price_text:
            # Try alternative selector
            price_text = response.css('span#prcIsum::text').get()
        
        price = None
        currency = 'USD'
        
        if price_text:
            # Extract currency and price
            currency_match = re.search(r'([A-Z]{3})', price_text)
            if currency_match:
                currency = currency_match.group(1)
            
            price_match = re.search(r'([\d,]+\.\d+)', price_text)
            if price_match:
                price = float(price_match.group(1).replace(',', ''))
        
        # Skip if no product name or price found
        if not product_name or not price:
            return
        
        # Extract product ID
        product_id = response.css('div.x-item-number span::text').get()
        if product_id:
            product_id = product_id.strip().replace('Item number: ', '')
        
        # Extract availability
        availability = "Available"  # Default for eBay listings
        
        # Extract quantity available
        quantity_text = response.css('span.qtyTxt span::text').get()
        if quantity_text and "available" in quantity_text.lower():
            availability = quantity_text.strip()
        
        # Extract sold count
        sold_text = response.css('span.vi-qtyS-hot-red::text').get()
        if sold_text and "sold" in sold_text.lower():
            availability = f"{availability} ({sold_text.strip()})"
        
        # Extract rating
        rating = None
        rating_text = response.css('div.ebay-review-start-rating::text').get()
        if rating_text:
            rating_match = re.search(r'(\d+(\.\d+)?)', rating_text)
            if rating_match:
                rating = float(rating_match.group(1))
        
        # Extract reviews count
        reviews_count = None
        reviews_text = response.css('div.reviews-right span::text').get()
        if reviews_text:
            reviews_match = re.search(r'([\d,]+)', reviews_text)
            if reviews_match:
                reviews_count = int(reviews_match.group(1).replace(',', ''))
        
        # Extract image URL
        image_url = response.css('img#icImg::attr(src)').get()
        if not image_url:
            # Try alternative selector
            image_url = response.css('div.ux-image-carousel-item img::attr(src)').get()
        
        # Extract description
        description = response.css('div.x-item-description div.d-item-description-text::text').get()
        if not description:
            # Try to get from iframe
            description_iframe = response.css('iframe#desc_ifr::attr(src)').get()
            if description_iframe:
                # We could follow this iframe, but for simplicity we'll skip it
                description = "See full description on eBay"
        
        if description:
            description = description.strip()
        
        # Create product item
        item = ProductItem(
            product_name=product_name,
            price=price,
            currency=currency,
            url=response.url,
            website='eBay',
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