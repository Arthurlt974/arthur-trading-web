import streamlit as st

def apply_terminal_style():
    st.markdown("""
        <style>
            header[data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; }
            .stApp [data-testid="stDecoration"] { display: none; }
            .stApp { background-color: #0d0d0d; color: #ff9800 !important; }
            
            /* Données et Chiffres en VERT */
            [data-testid="stMetricValue"], 
            [data-testid="stMetricDelta"] > div,
            td, input { 
                color: #00ff00 !important; 
                font-family: 'Courier New', monospace !important;
                text-shadow: 0 0 5px rgba(0, 255, 0, 0.3);
            }
            
            /* Titres et Labels en ORANGE */
            h1, h2, h3, p, span, label, [data-testid="stMetricLabel"] { 
                color: #ff9800 !important; 
                text-transform: uppercase; 
            }
            
            .stButton>button { background-color: #1a1a1a; color: #ff9800; border: 1px solid #ff9800; }
        </style>
    """, unsafe_allow_html=True)
