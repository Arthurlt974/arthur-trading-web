import streamlit as st
import streamlit.components.v1 as components

def show_multi_charts():
    st.title("🖥️ WORKSPACE MULTI-FENÊTRES")
    
    col_input, col_add, col_clear = st.columns([3, 1, 1])
    with col_input:
        new_ticker = st.text_input("SYMBOLE", key="add_chart_input").upper()
    with col_add:
        if st.button("AJOUTER +") and new_ticker:
            if new_ticker not in st.session_state.multi_charts:
                st.session_state.multi_charts.append(new_ticker)
                st.rerun()
    with col_clear:
        if st.button("TOUT FERMER"):
            st.session_state.multi_charts = []
            st.rerun()

    if st.session_state.multi_charts:
        all_windows = ""
        for i, tk in enumerate(st.session_state.multi_charts):
            all_windows += f"""
            <div id="win_{i}" class="floating-window" style="width:450px; height:350px; position:absolute; top:{50+(i*40)}px; left:{50+(i*40)}px; background:#0d0d0d; border:2px solid #ff9800; z-index:{100+i}; display:flex; flex-direction:column;">
                <div class="window-header" style="background:#1a1a1a; color:#ff9800; padding:10px; cursor:move; border-bottom:1px solid #ff9800;">
                    <span>📟 TERMINAL: {tk}</span>
                </div>
                <div id="tv_{i}" style="flex-grow:1;"></div>
            </div>
            <script>new TradingView.widget({{"autosize":true,"symbol":"{tk}","theme":"dark","container_id":"tv_{i}"}});</script>
            """
        
        components.html(f"""
            <script src="https://code.jquery.com/jquery-3.6.0.js"></script>
            <script src="https://code.jquery.com/ui/1.13.2/jquery-ui.js"></script>
            <script src="https://s3.tradingview.com/tv.js"></script>
            <div id="desktop" style="width:100%; height:800px; position:relative;">{all_windows}</div>
            <script>
                $(function() {{ 
                    $(".floating-window").draggable({{ handle:".window-header", containment:"#desktop", stack:".floating-window" }});
                    $(".floating-window").resizable({{ handles:"se", minWidth:300, minHeight:200 }});
                }});
            </script>
        """, height=850)

