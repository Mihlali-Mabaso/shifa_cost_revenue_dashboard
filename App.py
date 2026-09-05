"""
Shifa — Financial Dashboard (2027)
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="Shifa — Financial Model 2027",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1a3a5c;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1rem;
        font-weight: 400;
        color: #4a6a8a;
        text-align: center;
        padding-bottom: 1rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        border-left: 4px solid #2E86C1;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a3a5c;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #6c757d;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA
# ============================================================================

@st.cache_data
def generate_financial_data():
    """Generate realistic monthly financial projections for 2027"""
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    # Invoice growth: 50 → 1,000 over 12 months
    invoices = np.round(50 + (1000 - 50) / (1 + np.exp(-0.6 * (np.arange(12) - 6)))).astype(int)
    
    # Costs
    aws_lambda = 150  # Base, scales slightly
    aws_textract = invoices * 0.30
    aws_bedrock = invoices * 0.20
    aws_dynamodb = 100
    aws_s3 = 50
    aws_api = invoices * 0.01
    aws_sns = invoices * 0.02
    aws_total = aws_lambda + aws_textract + aws_bedrock + aws_dynamodb + aws_s3 + aws_api + aws_sns
    
    multi_cloud = aws_total * 0.10
    dev_costs = 120000  # Fixed
    marketing = 15000 + (invoices * 0.50)  # Variable
    compliance = 8000  # Fixed
    total_costs = aws_total + multi_cloud + dev_costs + marketing + compliance
    
    # Revenue
    avg_invoice_value = 185000
    absa_invoices = invoices * 0.40
    nonabsa_invoices = invoices * 0.60
    
    fee_revenue_absa = absa_invoices * 0.015 * avg_invoice_value
    fee_revenue_nonabsa = nonabsa_invoices * 0.045 * avg_invoice_value
    fee_revenue = fee_revenue_absa + fee_revenue_nonabsa
    
    escrow_revenue = invoices * 0.005 * avg_invoice_value
    collections_revenue = invoices * 0.005 * avg_invoice_value * 0.10
    
    total_revenue = fee_revenue + escrow_revenue + collections_revenue
    
    # Absa gains
    absa_share = (fee_revenue * 0.20) + (escrow_revenue * 0.20)
    new_customers = nonabsa_invoices * 0.60
    cross_sell_revenue = new_customers * 5000  # R5,000 LTV per customer
    
    return pd.DataFrame({
        'Month': months,
        'Invoices': invoices,
        'AWS_Costs': aws_total,
        'Multi_Cloud': multi_cloud,
        'Dev_Costs': dev_costs,
        'Marketing': marketing,
        'Compliance': compliance,
        'Total_Costs': total_costs,
        'Fee_Revenue': fee_revenue,
        'Escrow_Revenue': escrow_revenue,
        'Collections_Revenue': collections_revenue,
        'Total_Revenue': total_revenue,
        'Profit': total_revenue - total_costs,
        'Absa_Share': absa_share,
        'New_Customers': new_customers,
        'Cross_Sell': cross_sell_revenue
    })

# ============================================================================
# DASHBOARD
# ============================================================================

def main():
    
    st.markdown('<p class="main-header">Shifa — Financial Model</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">2027 Projections · Invoice-to-Cash Marketplace</p>', unsafe_allow_html=True)
    
    data = generate_financial_data()
    total = data.sum()
    latest = data.iloc[-1]
    
    # =========================================================================
    # KPI ROW
    # =========================================================================
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">R{total['Total_Revenue']/1e6:,.1f}M</div>
            <div class="metric-label">Annual Revenue</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">R{total['Total_Costs']/1e6:,.2f}M</div>
            <div class="metric-label">Annual Costs</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #28a745;">R{(total['Total_Revenue'] - total['Total_Costs'])/1e6:,.1f}M</div>
            <div class="metric-label">Annual Profit</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        profit_margin = ((total['Total_Revenue'] - total['Total_Costs']) / total['Total_Revenue']) * 100
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #28a745;">{profit_margin:.1f}%</div>
            <div class="metric-label">Profit Margin</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{int(total['Invoices']):,}</div>
            <div class="metric-label">Total Invoices (2027)</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # =========================================================================
    # CHARTS
    # =========================================================================
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Revenue vs Costs (Monthly)")
        
        fig, ax = plt.subplots(figsize=(10, 4))
        
        ax.plot(data['Month'], data['Total_Revenue']/1000, 
                marker='o', linewidth=2.5, color='#2E86C1', label='Revenue')
        ax.plot(data['Month'], data['Total_Costs']/1000, 
                marker='s', linewidth=2.5, color='#E74C3C', label='Costs')
        ax.fill_between(data['Month'], data['Total_Revenue']/1000, 
                        data['Total_Costs']/1000, 
                        where=(data['Total_Revenue'] > data['Total_Costs']),
                        color='#28a745', alpha=0.15)
        
        ax.set_xlabel('2027')
        ax.set_ylabel('R Thousands')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        
        st.pyplot(fig)
    
    with col2:
        st.subheader("Revenue Sources")
        
        fig2, ax2 = plt.subplots(figsize=(5, 4))
        
        sources = [total['Fee_Revenue'], total['Escrow_Revenue'], total['Collections_Revenue']]
        labels = ['Transaction Fees', 'Escrow Fees', 'Collections']
        colors = ['#2E86C1', '#28a745', '#8E44AD']
        
        ax2.pie(sources, labels=labels, autopct='%1.0f%%', colors=colors, startangle=90)
        ax2.axis('equal')
        
        st.pyplot(fig2)
    
    # =========================================================================
    # COST BREAKDOWN
    # =========================================================================
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Cost Breakdown")
        
        fig3, ax3 = plt.subplots(figsize=(8, 4))
        
        costs = [total['AWS_Costs'], total['Multi_Cloud'], total['Dev_Costs'], 
                 total['Marketing'], total['Compliance']]
        labels = ['AWS', 'Multi-Cloud', 'Development', 'Marketing', 'Compliance']
        colors = ['#3498db', '#9b59b6', '#2ecc71', '#f39c12', '#e74c3c']
        
        bars = ax3.bar(labels, [c/1000 for c in costs], color=colors)
        ax3.set_ylabel('R Thousands')
        ax3.set_title('Annual Cost Breakdown (R{:.2f}M Total)'.format(total['Total_Costs']/1e6))
        ax3.tick_params(axis='x', rotation=15)
        
        for bar, val in zip(bars, [c/1000 for c in costs]):
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10,
                    f'R{val:,.0f}K', ha='center', va='bottom', fontsize=8)
        
        st.pyplot(fig3)
    
    with col2:
        st.subheader("Absa Gains")
        
        fig4, ax4 = plt.subplots(figsize=(8, 4))
        
        absa_gains = [total['Absa_Share'], total['Cross_Sell']]
        labels_gains = ['Fee Share', 'Cross-Sell']
        colors_gains = ['#27AE60', '#2E86C1']
        
        bars_g = ax4.bar(labels_gains, [g/1000 for g in absa_gains], color=colors_gains)
        ax4.set_ylabel('R Thousands')
        ax4.set_title('Absa Annual Gains')
        
        for bar, val in zip(bars_g, [g/1000 for g in absa_gains]):
            ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10,
                    f'R{val:,.0f}K', ha='center', va='bottom', fontsize=10)
        
        st.pyplot(fig4)
    
    # =========================================================================
    # DETAILED TABLE
    # =========================================================================
    
    with st.expander("📊 View Detailed Monthly Data"):
        
        display = pd.DataFrame({
            'Month': data['Month'],
            'Invoices': data['Invoices'],
            'Revenue (R)': data['Total_Revenue'].apply(lambda x: f"R{x:,.0f}"),
            'Costs (R)': data['Total_Costs'].apply(lambda x: f"R{x:,.0f}"),
            'Profit (R)': data['Profit'].apply(lambda x: f"R{x:,.0f}"),
            'Absa Share (R)': data['Absa_Share'].apply(lambda x: f"R{x:,.0f}"),
            'New Customers': data['New_Customers'].apply(lambda x: f"{int(x):,}")
        })
        st.dataframe(display, use_container_width=True)

if __name__ == "__main__":
    main()
