import os
import sys
import warnings
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dcc, callback, Output, Input, State
from dash.exceptions import PreventUpdate
from datetime import datetime, timedelta
import threading
import time

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    import scrapy
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings
    SCRAPY_AVAILABLE = True
except ImportError:
    warnings.warn("Scrapy is not available. Scraping functionality will be disabled.")
    SCRAPY_AVAILABLE = False

try:
    from database.models import Product, db_session, init_db, SQLALCHEMY_AVAILABLE
    # Initialize database
    init_db()
except ImportError:
    warnings.warn("Database module not found. Using CSV files only.")
    SQLALCHEMY_AVAILABLE = False

# Import spiders if Scrapy is available
if SCRAPY_AVAILABLE:
    try:
        from shop_scraper.spiders.amazon import AmazonSpider
        from shop_scraper.spiders.ebay import EbaySpider
        from shop_scraper.spiders.walmart import WalmartSpider
        SPIDERS_AVAILABLE = True
    except ImportError:
        warnings.warn("Failed to import spiders. Scraping functionality will be disabled.")
        SPIDERS_AVAILABLE = False
else:
    SPIDERS_AVAILABLE = False

# Create Dash app
app = Dash(__name__, title="E-Commerce Price Tracker")

# Define app layout
app.layout = html.Div([
    html.H1("E-Commerce Price Tracker", style={'textAlign': 'center', 'marginBottom': '30px', 'marginTop': '20px'}),
    
    # Search section
    html.Div([
        html.H3("Search for Products", style={'marginBottom': '15px'}),
        html.Div([
            dcc.Input(
                id='search-input',
                type='text',
                placeholder='Enter product name...',
                style={'width': '70%', 'padding': '10px', 'marginRight': '10px'}
            ),
            html.Button(
                'Search',
                id='search-button',
                n_clicks=0,
                style={'padding': '10px 20px', 'backgroundColor': '#4CAF50', 'color': 'white', 'border': 'none', 'marginRight': '10px'}
            ),
            html.Button(
                'Scrape Now',
                id='scrape-button',
                n_clicks=0,
                style={'padding': '10px 20px', 'backgroundColor': '#2196F3', 'color': 'white', 'border': 'none', 'display': 'inline-block' if SPIDERS_AVAILABLE else 'none'}
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px'}),
        
        # Scraping options
        html.Div([
            html.H4("Scraping Options", style={'marginBottom': '10px'}),
            html.Div([
                html.Label("Select Websites:", style={'marginRight': '10px'}),
                dcc.Checklist(
                    id='website-checklist',
                    options=[
                        {'label': 'Amazon', 'value': 'amazon'},
                        {'label': 'eBay', 'value': 'ebay'},
                        {'label': 'Walmart', 'value': 'walmart'}
                    ],
                    value=['amazon'],
                    inline=True
                )
            ], style={'marginBottom': '10px'}),
            html.Div([
                html.Label("Product Limit:", style={'marginRight': '10px'}),
                dcc.Input(
                    id='limit-input',
                    type='number',
                    min=1,
                    max=50,
                    value=5,
                    style={'width': '60px'}
                )
            ])
        ], style={'marginTop': '20px', 'display': 'block' if SPIDERS_AVAILABLE else 'none'}),
        
        # Scraping status
        html.Div(id='scraping-status', style={'marginTop': '10px', 'color': '#FF5722'}),
        
        # Auto-refresh toggle
        html.Div([
            html.Label("Auto-refresh results after scraping: ", style={'marginRight': '10px'}),
            dcc.Checklist(
                id='auto-refresh',
                options=[{'label': '', 'value': 'yes'}],
                value=['yes'],
                inline=True
            )
        ], style={'marginTop': '10px', 'display': 'block' if SPIDERS_AVAILABLE else 'none'})
    ], style={'padding': '20px', 'backgroundColor': '#f9f9f9', 'borderRadius': '5px', 'marginBottom': '30px'}),
    
    # Results section
    html.Div([
        html.H3("Search Results", style={'marginBottom': '15px'}),
        html.Div(id='search-results-message'),
        
        # Price comparison chart
        html.Div([
            html.H4("Price Comparison by Website", style={'marginTop': '20px', 'marginBottom': '10px'}),
            dcc.Graph(id='price-comparison-chart')
        ], style={'marginBottom': '30px'}),
        
        # Price history chart
        html.Div([
            html.H4("Price History Over Time", style={'marginTop': '20px', 'marginBottom': '10px'}),
            dcc.Graph(id='price-history-chart')
        ], style={'marginBottom': '30px'}),
        
        # Product details table
        html.Div([
            html.H4("Product Details", style={'marginTop': '20px', 'marginBottom': '10px'}),
            html.Div(id='product-details-table')
        ])
    ], style={'padding': '20px', 'backgroundColor': '#f9f9f9', 'borderRadius': '5px'}),
    
    # Hidden div for storing scraping completion status
    html.Div(id='scraping-completed', style={'display': 'none'}),
    
    # Interval component for auto-refresh
    dcc.Interval(
        id='interval-component',
        interval=2000,  # in milliseconds (2 seconds)
        n_intervals=0,
        disabled=True
    )
])


def get_data_from_csv(search_term):
    """
    Get data from CSV files when database is not available
    """
    products = []
    exports_dir = 'data/exports'
    
    if not os.path.exists(exports_dir):
        return []
    
    for filename in os.listdir(exports_dir):
        if not filename.endswith('.csv'):
            continue
        
        file_path = os.path.join(exports_dir, filename)
        try:
            df = pd.read_csv(file_path)
            # Filter by search term
            if 'Search Term' in df.columns and 'Product Name' in df.columns:
                filtered_df = df[df['Search Term'].str.contains(search_term, case=False, na=False) | 
                                df['Product Name'].str.contains(search_term, case=False, na=False)]
                
                for _, row in filtered_df.iterrows():
                    product = {
                        'product_name': row.get('Product Name', ''),
                        'price': float(row.get('Price', 0)),
                        'currency': row.get('Currency', 'USD'),
                        'website': row.get('Website', ''),
                        'url': row.get('URL', ''),
                        'availability': row.get('Availability', ''),
                        'rating': float(row.get('Rating', 0)) if not pd.isna(row.get('Rating', 0)) else None,
                        'reviews_count': int(row.get('Reviews Count', 0)) if not pd.isna(row.get('Reviews Count', 0)) else None,
                        'timestamp': pd.to_datetime(row.get('Timestamp', datetime.now()))
                    }
                    products.append(product)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    return products


# Global variable to track scraping status
scraping_in_progress = False
scraping_completed_timestamp = None

def run_spider(product, websites, limit):
    """
    Run the spiders in a separate thread
    """
    global scraping_in_progress, scraping_completed_timestamp
    
    try:
        # Generate output file name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        product_slug = product.lower().replace(' ', '_')
        output_file = f"{product_slug}_{timestamp}.csv"
        
        # Ensure output directory exists
        os.makedirs('data/exports', exist_ok=True)
        
        # Get Scrapy settings
        settings = get_project_settings()
        
        # Set CLOSESPIDER_ITEMCOUNT if limit is provided
        if limit:
            settings.set('CLOSESPIDER_ITEMCOUNT', limit)
        
        # Initialize the crawler process
        process = CrawlerProcess(settings)
        
        # Determine which spiders to run
        spiders = []
        if 'amazon' in websites:
            spiders.append(AmazonSpider)
        if 'ebay' in websites:
            spiders.append(EbaySpider)
        if 'walmart' in websites:
            spiders.append(WalmartSpider)
        
        # Configure and start each spider
        for spider_class in spiders:
            process.crawl(
                spider_class,
                product=product,
                output_file=output_file
            )
        
        # Start the crawling process
        print(f"Starting to scrape {product} from {', '.join(websites)}")
        print(f"Results will be saved to data/exports/{output_file}")
        
        process.start()
        
        print("Scraping completed!")
        scraping_completed_timestamp = datetime.now()
    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        scraping_in_progress = False


@callback(
    [Output('scraping-status', 'children'),
     Output('interval-component', 'disabled'),
     Output('scraping-completed', 'children')],
    Input('scrape-button', 'n_clicks'),
    [State('search-input', 'value'),
     State('website-checklist', 'value'),
     State('limit-input', 'value'),
     State('auto-refresh', 'value')]
)
def start_scraping(n_clicks, product, websites, limit, auto_refresh):
    global scraping_in_progress
    
    if n_clicks == 0 or not product:
        return "", True, ""
    
    if not SCRAPY_AVAILABLE or not SPIDERS_AVAILABLE:
        return "Scraping functionality is not available. Please install Scrapy and make sure the spiders are properly configured.", True, ""
    
    if scraping_in_progress:
        return "Scraping is already in progress. Please wait...", True, ""
    
    # Set scraping flag
    scraping_in_progress = True
    
    # Start scraping in a separate thread
    threading.Thread(target=run_spider, args=(product, websites, limit)).start()
    
    # Enable auto-refresh if selected
    auto_refresh_enabled = 'yes' in auto_refresh if auto_refresh else False
    
    return f"Scraping '{product}' from {', '.join(websites)} with a limit of {limit} products per website. This may take a few minutes...", not auto_refresh_enabled, ""


@callback(
    [Output('search-results-message', 'children'),
     Output('price-comparison-chart', 'figure'),
     Output('price-history-chart', 'figure'),
     Output('product-details-table', 'children')],
    [Input('search-button', 'n_clicks'),
     Input('interval-component', 'n_intervals')],
    [State('search-input', 'value')]
)
def update_results(n_clicks, n_intervals, search_term):
    global scraping_completed_timestamp
    
    # Check if this is triggered by the interval and if scraping just completed
    if n_clicks == 0 and n_intervals > 0:
        if not scraping_completed_timestamp or (datetime.now() - scraping_completed_timestamp).total_seconds() > 10:
            raise PreventUpdate
    
    if not search_term:
        raise PreventUpdate
    
    # Get products from database or CSV
    if SQLALCHEMY_AVAILABLE:
        products = Product.get_latest_prices(search_term)
    else:
        products = get_data_from_csv(search_term)
    
    if not products:
        return (
            html.P(f"No results found for '{search_term}'. Try scraping data first."),
            px.bar(title="No data available"),
            px.line(title="No data available"),
            html.P("No product details available")
        )
    
    # Create DataFrame for visualization
    data = []
    for product in products:
        if hasattr(product, '__dict__'):
            # SQLAlchemy model instance
            product_dict = {
                'product_name': product.product_name,
                'price': product.price,
                'currency': product.currency,
                'website': product.website,
                'url': product.url,
                'availability': product.availability,
                'rating': product.rating,
                'reviews_count': product.reviews_count,
                'timestamp': product.timestamp
            }
            data.append(product_dict)
        else:
            # Dictionary from CSV
            data.append(product)
    
    df = pd.DataFrame(data)
    
    # Price comparison chart
    fig_comparison = px.bar(
        df, 
        x='product_name', 
        y='price', 
        color='website',
        title=f"Price Comparison for '{search_term}'",
        labels={'product_name': 'Product', 'price': 'Price', 'website': 'Website'},
        hover_data=['rating', 'reviews_count', 'availability']
    )
    
    # Price history chart (if we have historical data)
    if SQLALCHEMY_AVAILABLE:
        history_data = []
        for product in products:
            history = Product.get_price_history(product.product_name, product.website)
            for hist_item in history:
                history_data.append({
                    'product_name': hist_item.product_name,
                    'price': hist_item.price,
                    'website': hist_item.website,
                    'timestamp': hist_item.timestamp
                })
        
        if history_data:
            history_df = pd.DataFrame(history_data)
            fig_history = px.line(
                history_df, 
                x='timestamp', 
                y='price', 
                color='product_name',
                line_dash='website',
                title=f"Price History for '{search_term}'",
                labels={'timestamp': 'Date', 'price': 'Price', 'product_name': 'Product', 'website': 'Website'}
            )
        else:
            fig_history = px.line(title="No historical data available")
    else:
        fig_history = px.line(title="Historical data requires database functionality")
    
    # Product details table
    table_rows = []
    for product in sorted(data, key=lambda x: x['price']):
        price_str = f"{product['price']:.2f} {product['currency']}"
        rating_str = f"{product['rating']:.1f} ({product['reviews_count']} reviews)" if product['rating'] and product['reviews_count'] else "No ratings"
        
        row = html.Tr([
            html.Td(product['product_name']),
            html.Td(price_str),
            html.Td(product['website']),
            html.Td(product['availability'] if product['availability'] else "Unknown"),
            html.Td(rating_str),
            html.Td(html.A("View", href=product['url'], target="_blank") if product['url'] else "No link")
        ])
        table_rows.append(row)
    
    table = html.Table([
        html.Thead(
            html.Tr([
                html.Th("Product Name"),
                html.Th("Price"),
                html.Th("Website"),
                html.Th("Availability"),
                html.Th("Rating"),
                html.Th("Link")
            ])
        ),
        html.Tbody(table_rows)
    ], style={'width': '100%', 'border-collapse': 'collapse'})
    
    # Reset scraping completion timestamp
    if scraping_completed_timestamp:
        scraping_completed_timestamp = None
    
    return (
        html.P(f"Found {len(products)} results for '{search_term}'"),
        fig_comparison,
        fig_history,
        table
    )


@callback(
    [Output('scraping-status', 'children', allow_duplicate=True),
     Output('interval-component', 'disabled', allow_duplicate=True)],
    Input('interval-component', 'n_intervals'),
    prevent_initial_call=True
)
def check_scraping_status(n_intervals):
    global scraping_in_progress, scraping_completed_timestamp
    
    if not scraping_in_progress and scraping_completed_timestamp:
        # Scraping just completed
        if (datetime.now() - scraping_completed_timestamp).total_seconds() < 5:
            return "Scraping completed! Refreshing results...", True
    
    if not scraping_in_progress:
        # Disable interval once we've shown the completion message
        return "", True
    
    return "Scraping in progress...", False


if __name__ == '__main__':
    app.run_server(debug=True) 