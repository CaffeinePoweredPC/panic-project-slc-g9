from setuptools import setup, find_packages

setup(
    name="shop_scraper",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "scrapy>=2.5.0",
        "sqlalchemy>=1.4.0",
        "pandas>=1.3.0",
        "plotly>=5.3.0",
        "dash>=2.0.0",
    ],
) 