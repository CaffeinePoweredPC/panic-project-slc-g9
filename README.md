# E-Commerce Price Tracker

A web scraping application that tracks product prices across multiple e-commerce websites. The application allows users to search for specific products and compare prices between different retailers, as well as track price changes over time.

## Features

- Scrape product prices from multiple e-commerce websites
- Search for specific products by name
- Store historical price data in a database
- Generate interactive visualizations to compare prices between websites
- Track price changes over time with trend analysis
- Export data to CSV files

## Installation

1. Clone this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Running the Price Scraper

```
python run.py --product "product name" --output output_filename.csv
```

### Running the Dashboard

```
python dashboard.py
```

Then open your browser and navigate to http://127.0.0.1:8050/

## Project Structure

- `shop_scraper/` - Main Scrapy project directory
  - `spiders/` - Contains spider implementations for different e-commerce websites
  - `items.py` - Defines the data structure for scraped items
  - `pipelines.py` - Processes scraped data and stores it in the database
- `database/` - Database models and utilities
- `dashboard/` - Interactive dashboard for data visualization
- `run.py` - Command-line interface for running the scraper

## Supported Websites

- Amazon
- eBay
- Walmart
- Best Buy
- Target

## License

MIT 