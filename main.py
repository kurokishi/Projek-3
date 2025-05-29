import streamlit as st
import sys
import os
import json
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import requests
from datetime import datetime, timedelta

# ======== Konfigurasi Awal ========
st.set_page_config(layout="wide", page_title="Analisis Portofolio Saham")

# ======== System Check ========
python_version = sys.version.split()[0]
st.sidebar.write(f"Python version: {python_version}")

# ======== Setup Session dengan Timeout ========
session = requests.Session()
session.timeout = 10  # 10 detik timeout

# ======== Dependency Fallbacks ========
class DummyModule:
    def __call__(self, *args, **kwargs):
        st.error("Fitur dinonaktifkan: Dependency tidak tersedia")
        return None
    def __getattr__(self, name):
        return self

# Setup fallbacks dengan error handling lebih baik
try:
    import yfinance as yf
    import requests
    session = requests.Session()
    session.timeout = 10  # 10 detik timeout
    YFINANCE_ENABLED = True
except ImportError:
    yf = DummyModule()
    YFINANCE_ENABLED = False
    st.sidebar.error("⚠️ yfinance tidak terinstall (pip install yfinance)")

try:
    from ta.momentum import RSIIndicator
    from ta.trend import MACD, SMAIndicator
    TA_ENABLED = True
except ImportError:
    RSIIndicator = MACD = SMAIndicator = DummyModule()
    TA_ENABLED = False
    st.sidebar.error("⚠️ Library TA tidak terinstall (pip install ta)")

[... bagian kode lainnya tetap sama ...]
