import json
import os
import pandas as pd

def load_portfolio_data(file_path='data/portfolio.json'):
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=["ticker", "lot", "avg_price"])
    with open(file_path, 'r') as f:
        return pd.DataFrame(json.load(f))
