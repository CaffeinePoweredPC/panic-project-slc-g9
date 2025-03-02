import os
import sys
import warnings
from datetime import datetime

try:
    from sqlalchemy import Column, Integer, String, Float, DateTime, create_engine, ForeignKey, func
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import scoped_session, sessionmaker
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    warnings.warn("SQLAlchemy is not available. Database functionality will be limited.")
    SQLALCHEMY_AVAILABLE = False

# Create database directory if it doesn't exist
os.makedirs('data', exist_ok=True)

if SQLALCHEMY_AVAILABLE:
    # Database setup
    engine = create_engine('sqlite:///data/products.db')
    db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

    Base = declarative_base()
    Base.query = db_session.query_property()

    class Product(Base):
        __tablename__ = 'products'
        
        id = Column(Integer, primary_key=True)
        product_name = Column(String(255), nullable=False)
        price = Column(Float, nullable=False)
        currency = Column(String(10), default='USD')
        url = Column(String(1024))
        website = Column(String(100), nullable=False)
        product_id = Column(String(100))
        description = Column(String(2048))
        image_url = Column(String(1024))
        availability = Column(String(50))
        rating = Column(Float)
        reviews_count = Column(Integer)
        search_term = Column(String(255))
        timestamp = Column(DateTime, default=datetime.now)
        
        def __init__(self, product_name, price, website, **kwargs):
            self.product_name = product_name
            self.price = price
            self.website = website
            
            # Set optional fields from kwargs
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
        
        def __repr__(self):
            return f'<Product {self.product_name} ({self.website}) - {self.price} {self.currency}>'
        
        @classmethod
        def get_products_by_search_term(cls, search_term):
            return cls.query.filter(cls.search_term.like(f'%{search_term}%')).all()
        
        @classmethod
        def get_price_history(cls, product_name, website):
            return cls.query.filter_by(product_name=product_name, website=website).order_by(cls.timestamp).all()
        
        @classmethod
        def get_latest_prices(cls, search_term):
            # Get the latest price for each product from each website
            subquery = db_session.query(
                cls.product_name,
                cls.website,
                func.max(cls.timestamp).label('max_timestamp')
            ).filter(cls.search_term.like(f'%{search_term}%')).group_by(cls.product_name, cls.website).subquery()
            
            return db_session.query(cls).join(
                subquery,
                (cls.product_name == subquery.c.product_name) &
                (cls.website == subquery.c.website) &
                (cls.timestamp == subquery.c.max_timestamp)
            ).all()
else:
    # Dummy implementations for when SQLAlchemy is not available
    Base = None
    db_session = None
    
    class Product:
        def __init__(self, product_name, price, website, **kwargs):
            self.product_name = product_name
            self.price = price
            self.website = website
            self.currency = kwargs.get('currency', 'USD')
            self.url = kwargs.get('url')
            self.product_id = kwargs.get('product_id')
            self.description = kwargs.get('description')
            self.image_url = kwargs.get('image_url')
            self.availability = kwargs.get('availability')
            self.rating = kwargs.get('rating')
            self.reviews_count = kwargs.get('reviews_count')
            self.search_term = kwargs.get('search_term')
            self.timestamp = kwargs.get('timestamp', datetime.now())
        
        def __repr__(self):
            return f'<Product {self.product_name} ({self.website}) - {self.price} {self.currency}>'
        
        @classmethod
        def get_products_by_search_term(cls, search_term):
            return []
        
        @classmethod
        def get_price_history(cls, product_name, website):
            return []
        
        @classmethod
        def get_latest_prices(cls, search_term):
            return []

def init_db():
    if SQLALCHEMY_AVAILABLE:
        Base.metadata.create_all(bind=engine)
    else:
        print("SQLAlchemy is not available. Database initialization skipped.")
        print("Data will be exported to CSV files only.") 