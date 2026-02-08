import yfinance as yf
import requests
import pandas as pd

def get_ticker_info(ticker):
    try: return yf.Ticker(ticker).info
    except: return None

def get_ticker_history(ticker, period="2d"):
    try: return yf.Ticker(ticker).history(period=period)
    except: return pd.DataFrame()

def trouver_ticker(nom):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={nom}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers).json()
        return response['quotes'][0]['symbol'] if response.get('quotes') else nom
    except: return nom

def get_crypto_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        return float(requests.get(url).json()['price'])
    except: return None
