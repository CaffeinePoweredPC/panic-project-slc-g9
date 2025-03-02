
import os
import sys
import warnings
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dcc, callback, Output, Input, State
from dash.exceptions import PreventUpdate
from datetime import datetime, timedelta




try:
    from database.models import Product, db_session, init_db, SQLALCHEMY_AVAILABLE
    # Initialize database
    init_db()
except ImportError:
    warnings.warn("Database module not found. Using CSV files only.")
    SQLALCHEMY_AVAILABLE = False

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
                style={'padding': '10px 20px', 'backgroundColor': '#4CAF50', 'color': 'white', 'border': 'none'}
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px'})
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
    ], style={'padding': '20px', 'backgroundColor': '#f9f9f9', 'borderRadius': '5px'})
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


@callback(
    [Output('search-results-message', 'children'),
     Output('price-comparison-chart', 'figure'),
     Output('price-history-chart', 'figure'),
     Output('product-details-table', 'children')],
    [Input('search-button', 'n_clicks')],
    [State('search-input', 'value')]
)
def update_results(n_clicks, search_term):
    if n_clicks == 0 or not search_term:
        raise PreventUpdate
    
    # Get data based on available sources
    if SQLALCHEMY_AVAILABLE:
        # Get latest prices for the search term from database
        products = Product.get_latest_prices(search_term)
        
        # Create DataFrame for the latest prices
        latest_data = []
        for product in products:
            latest_data.append({
                'product_name': product.product_name,
                'price': product.price,
                'currency': product.currency,
                'website': product.website,
                'url': product.url,
                'availability': product.availability,
                'rating': product.rating,
                'reviews_count': product.reviews_count,
                'timestamp': product.timestamp
            })
        
        # Get price history data
        history_data = []
        for product in products:
            product_history = Product.get_price_history(product.product_name, product.website)
            for item in product_history:
                history_data.append({
                    'product_name': item.product_name,
                    'price': item.price,
                    'website': item.website,
                    'timestamp': item.timestamp
                })
    else:
        # Get data from CSV files
        csv_products = get_data_from_csv(search_term)
        
        if not csv_products:
            return (
                html.P(f"No results found for '{search_term}'. Try a different search term or run the scraper first."),
                go.Figure(),
                go.Figure(),
                html.Div()
            )
        
        # Create DataFrame for the latest prices
        latest_data = []
        history_data = []
        
        # Group by product_name and website to get the latest entry
        product_dict = {}
        for product in csv_products:
            key = (product['product_name'], product['website'])
            if key not in product_dict or product['timestamp'] > product_dict[key]['timestamp']:
                product_dict[key] = product
        
        # Add latest products to the list
        for product in product_dict.values():
            latest_data.append(product)
        
        # All data is history data
        history_data = csv_products
    
    # Convert to DataFrames
    latest_df = pd.DataFrame(latest_data)
    history_df = pd.DataFrame(history_data)
    
    if latest_df.empty:
        return (
            html.P(f"No results found for '{search_term}'. Try a different search term or run the scraper first."),
            go.Figure(),
            go.Figure(),
            html.Div()
        )
    
    # Create price comparison chart
    price_comparison_fig = px.bar(
        latest_df,
        x='website',
        y='price',
        color='website',
        hover_data=['product_name', 'price', 'currency', 'availability'],
        labels={'price': 'Price', 'website': 'Website'},
        title=f'Price Comparison for "{search_term}" across Websites'
    )
    
    # Create price history chart
    if not history_df.empty:
        price_history_fig = px.line(
            history_df,
            x='timestamp',
            y='price',
            color='website',
            hover_data=['product_name', 'price'],
            labels={'price': 'Price', 'timestamp': 'Date', 'website': 'Website'},
            title=f'Price History for "{search_term}" over Time'
        )
    else:
        price_history_fig = go.Figure()
        price_history_fig.update_layout(
            title=f'No price history available for "{search_term}"',
            xaxis_title='Date',
            yaxis_title='Price'
        )
    
    # Create product details table
    table_header = [
        html.Thead(html.Tr([
            html.Th('Product Name'),
            html.Th('Website'),
            html.Th('Price'),
            html.Th('Availability'),
            html.Th('Rating'),
            html.Th('Reviews'),
            html.Th('Link')
        ]))
    ]
    
    table_rows = []
    for _, product in latest_df.iterrows():
        table_rows.append(html.Tr([
            html.Td(product['product_name']),
            html.Td(product['website']),
            html.Td(f"{product['price']} {product['currency']}"),
            html.Td(product['availability'] if not pd.isna(product['availability']) else 'N/A'),
            html.Td(f"{product['rating']}" if not pd.isna(product['rating']) else 'N/A'),
            html.Td(f"{product['reviews_count']}" if not pd.isna(product['reviews_count']) else 'N/A'),
            html.Td(html.A('View', href=product['url'], target='_blank'))
        ]))
    
    table_body = [html.Tbody(table_rows)]
    
    product_table = html.Table(
        table_header + table_body,
        style={'width': '100%', 'border': '1px solid #ddd', 'borderCollapse': 'collapse'}
    )
    
    return (
        html.P(f"Found {len(latest_df)} results for '{search_term}'"),
        price_comparison_fig,
        price_history_fig,
        product_table
    )


if __name__ == '__main__':
    app.run_server(debug=True) 