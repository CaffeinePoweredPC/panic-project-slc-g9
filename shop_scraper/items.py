# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from datetime import datetime


class ProductItem(scrapy.Item):
    # Basic product information
    product_name = scrapy.Field()
    price = scrapy.Field()
    currency = scrapy.Field()
    url = scrapy.Field()
    website = scrapy.Field()
    
    # Additional product information
    product_id = scrapy.Field()
    description = scrapy.Field()
    image_url = scrapy.Field()
    availability = scrapy.Field()
    rating = scrapy.Field()
    reviews_count = scrapy.Field()
    
    # Metadata
    search_term = scrapy.Field()
    timestamp = scrapy.Field(serializer=lambda x: x.isoformat() if isinstance(x, datetime) else x)
