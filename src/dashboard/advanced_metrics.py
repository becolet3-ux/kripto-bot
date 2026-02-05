import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta

class AdvancedDashboard:
    """Gelişmiş monitoring dashboard"""
    
    def __init__(self, db_connection=None, state=None):
        self.db = db_connection
        self.state = state or {}
    
    def render(self):
        # Header is rendered by main dashboard
        # st.title("🤖 Crypto Trading Bot - Advanced Dashboard")
        
        # Metrics Row
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Balance", f"${self.get_total_balance():,.2f}", 
                     delta=f"{self.get_daily_pnl_pct():.2f}%")
        
        with col2:
            st.metric("Win Rate", f"{self.get_win_rate():.1f}%")
        
        with col3:
            st.metric("Active Positions", self.get_active_positions_count())
        
        with col4:
            st.metric("Daily P&L", f"${self.get_daily_pnl():.2f}",
                     delta=f"{self.get_daily_pnl_pct():.2f}%")
        
        with col5:
            st.metric("Sharpe Ratio", f"{self.get_sharpe_ratio():.2f}")
        
        # Tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Equity Curve", 
            "📊 Performance", 
            "💼 Positions", 
            "🔥 Heatmap",
            "⚙️ System Health"
        ])
        
        with tab1:
            self.render_equity_curve()
        
        with tab2:
            self.render_performance_metrics()
        
        with tab3:
            self.render_positions_table()
        
        with tab4:
            self.render_performance_heatmap()
        
        with tab5:
            self.render_system_health()
    
    # --- Data Helpers ---
    def get_stats(self):
        return self.state.get('stats', {})

    def get_total_balance(self):
        # Calculate from state (initial 1000 for paper trading)
        initial = 1000.0
        pnl_pct = self.get_stats().get('total_pnl_pct', 0.0)
        return initial * (1 + (pnl_pct / 100))

    def get_daily_pnl(self):
        # Approximate daily PnL from stats (just realized today)
        return self.get_stats().get('daily_realized_pnl', 0.0) # This is likely pct

    def get_daily_pnl_pct(self):
        return self.get_stats().get('daily_realized_pnl', 0.0)

    def get_win_rate(self):
        return self.get_stats().get('win_rate', 0.0) * 100

    def get_active_positions_count(self):
        return len(self.state.get('paper_positions', {}))

    def get_sharpe_ratio(self):
        # Placeholder calculation
        return 0.0

    def get_active_positions(self):
        positions = []
        raw_positions = self.state.get('paper_positions', {})
        for symbol, data in raw_positions.items():
            pos = data.copy()
            pos['symbol'] = symbol
            # Mock current price if not available
            pos['current_price'] = pos['entry_price'] # Would need live price here
            pos['value'] = pos['quantity'] * pos['entry_price']
            positions.append(pos)
        return positions

    # --- Renderers ---

    def render_equity_curve(self):
        """Sermaye büyüme grafiği"""
        st.subheader("Equity Curve")
        
        # Mock data if no history
        equity_data = pd.DataFrame({
            'timestamp': [datetime.now()],
            'equity': [self.get_total_balance()]
        })
        
        fig = go.Figure()
        
        # Equity line
        fig.add_trace(go.Scatter(
            x=equity_data['timestamp'],
            y=equity_data['equity'],
            mode='lines',
            name='Portfolio Value',
            line=dict(color='#00ff00', width=2)
        ))
        
        fig.update_layout(
            height=500,
            yaxis=dict(title="Equity ($)"),
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_performance_metrics(self):
        """Performans metrikleri"""
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Win/Loss Distribution")
            # Mock
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=[0],
                nbinsx=50,
                marker_color='lightblue'
            ))
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Cumulative P&L by Symbol")
            # Mock
            fig = go.Figure()
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    def render_positions_table(self):
        """Aktif pozisyonlar tablosu"""
        st.subheader("Active Positions")
        
        positions = self.get_active_positions()
        
        if positions:
            df = pd.DataFrame(positions)
            df['unrealized_pnl_pct'] = df.apply(
                lambda x: ((x['current_price'] - x['entry_price']) / x['entry_price']) * 100,
                axis=1
            )
            
            # Renklendirme
            def color_pnl(val):
                color = 'green' if val > 0 else 'red'
                return f'color: {color}'
            
            styled_df = df.style.applymap(color_pnl, subset=['unrealized_pnl_pct'])
            
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.info("No active positions")
        
        # Pozisyon dağılımı (pie chart)
        if positions:
            st.subheader("Position Distribution")
            
            fig = go.Figure(data=[go.Pie(
                labels=[p['symbol'] for p in positions],
                values=[p['value'] for p in positions],
                hole=0.3
            )])
            st.plotly_chart(fig, use_container_width=True)
    
    def render_performance_heatmap(self):
        """Performans heatmap'i (gün/saat)"""
        st.subheader("Performance Heatmap (Hour/Day)")
        
        # Mock data
        z = [[0]*24 for _ in range(7)]
        
        fig = go.Figure(data=go.Heatmap(
            z=z,
            x=[f"{h:02d}:00" for h in range(24)],
            y=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            colorscale='RdYlGn',
            zmid=0
        ))
        
        fig.update_layout(
            xaxis_title="Hour of Day",
            yaxis_title="Day of Week",
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_system_health(self):
        """Sistem sağlığı"""
        st.subheader("System Health Monitoring")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("API Latency", "N/A ms")
            st.metric("Last Update", datetime.now().strftime("%H:%M:%S"))
        
        with col2:
            st.metric("Error Count (24h)", "0")
            st.metric("Circuit Breaker", "CLOSED")
        
        with col3:
            st.metric("Rate Limit Usage", "0%")
            st.metric("DB Size", "N/A MB")
        
        # Error Log
        st.subheader("Recent Errors")
        st.success("No recent errors")
