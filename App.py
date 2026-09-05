"""
Shifa — Cost & Revenue Dashboard
Professional, clean financial dashboard for the pitch deck
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Page config
st.set_page_config(
    page_title="Shifa — Cost & Revenue",
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
    .positive {
        color: #28a745;
    }
    .negative {
        color: #dc3545;
    }
    .neutral {
        color: #6c757d;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA GENERATION
# ============================================================================

@st.cache_data
def generate_financial_data():
    """Generate realistic cost and revenue projections for Year 1"""
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    months_idx = np.arange(len(months))
    
    # Invoices per month (growing from 200 to 3,000)
    invoices_per_month = np.round(200 + (3000 - 200) / (1 + np.exp(-0.6 * (months_idx - 6)))).astype(int)
    
    # Average invoice value: R150,000 - R250,000
    avg_invoice_value = np.round(150000 + (100000) / (1 + np.exp(-0.4 * (months_idx - 5))), -3)
    
    # Total invoice value per month
    total_value_per_month = invoices_per_month * avg_invoice_value
    
    # Transaction fee revenue (1.5-4.5%)
    fee_revenue_absa = total_value_per_month * 0.015  # 1.5% for Absa customers
    fee_revenue_nonabsa = total_value_per_month * 0.025  # 2.5% for non-Absa (mix)
    total_fee_revenue = fee_revenue_absa + fee_revenue_nonabsa
    
    # Escrow fee revenue (0.5% of total value)
    escrow_revenue = total_value_per_month * 0.005
    
    # Collections management revenue (0.5% of total value, 10% take-up)
    collections_revenue = total_value_per_month * 0.005 * 0.10
    
    # Total revenue
    total_revenue = total_fee_revenue + escrow_revenue + collections_revenue
    
    # Costs
    # AWS costs: Lambda, API Gateway, DynamoDB, S3, Textract, Bedrock
    aws_lambda = 2000 + (invoices_per_month * 0.15)  # Base + per invoice
    aws_textract = invoices_per_month * 0.30  # $0.30 per page
    aws_bedrock = invoices_per_month * 0.20  # $0.20 per call
    aws_storage = 500 + (invoices_per_month * 0.01)
    aws_total = aws_lambda + aws_textract + aws_bedrock + aws_storage
    
    # Development costs (amortized)
    dev_costs = 25000  # Per month, fixed
    
    # Marketing & acquisition
    marketing = 5000 + (invoices_per_month * 0.50)
    
    # Compliance & admin
    compliance = 3000  # Per month, fixed
    
    # Multi-cloud redundancy (Azure/GCP fallback)
    multi_cloud = aws_total * 0.10  # 10% premium for redundancy
    
    # Total costs
    total_costs = aws_total + dev_costs + marketing + compliance + multi_cloud
    
    # Profit
    profit = total_revenue - total_costs
    profit_margin = (profit / total_revenue) * 100
    
    return pd.DataFrame({
        'Month': months,
        'Invoices': invoices_per_month,
        'Invoice_Value': avg_invoice_value,
        'Total_Value': total_value_per_month,
        'Fee_Revenue': total_fee_revenue,
        'Escrow_Revenue': escrow_revenue,
        'Collections_Revenue': collections_revenue,
        'Total_Revenue': total_revenue,
        'AWS_Costs': aws_total,
        'Dev_Costs': dev_costs,
        'Marketing_Costs': marketing,
        'Compliance_Costs': compliance,
        'Multi_Cloud_Costs': multi_cloud,
        'Total_Costs': total_costs,
        'Profit': profit,
        'Profit_Margin': profit_margin
    })

# ============================================================================
# DASHBOARD
# ============================================================================

def main():
    
    # Header
    st.markdown('<p class="main-header">Shifa — Cost & Revenue Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Year 1 Projections · Invoice-to-Cash Marketplace</p>', unsafe_allow_html=True)
    
    # Load data
    data = generate_financial_data()
    latest = data.iloc[-1]
    total_annual = data.sum()
    
    # =========================================================================
    # KPI ROW
    # =========================================================================
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">R{total_annual['Total_Revenue']/1e6:,.1f}M</div>
            <div class="metric-label">Annual Revenue</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">R{total_annual['Total_Costs']/1e6:,.1f}M</div>
            <div class="metric-label">Annual Costs</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: {'#28a745' if total_annual['Profit'] > 0 else '#dc3545'}">
                R{total_annual['Profit']/1e6:,.1f}M
            </div>
            <div class="metric-label">Annual Profit</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: {'#28a745' if total_annual['Profit_Margin']/12 > 10 else '#6c757d'}">
                {total_annual['Profit_Margin']/12:.1f}%
            </div>
            <div class="metric-label">Avg Profit Margin</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{int(total_annual['Invoices']):,}</div>
            <div class="metric-label">Annual Invoices</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # =========================================================================
    # CHART 1: Revenue vs Costs (Monthly)
    # =========================================================================
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Revenue & Costs")
        
        fig, ax = plt.subplots(figsize=(10, 4))
        
        ax.plot(data['Month'], data['Total_Revenue']/1000, 
                marker='o', linewidth=2.5, color='#2E86C1', label='Revenue')
        ax.plot(data['Month'], data['Total_Costs']/1000, 
                marker='s', linewidth=2.5, color='#E74C3C', label='Costs')
        ax.fill_between(data['Month'], data['Total_Revenue']/1000, 
                        data['Total_Costs']/1000, 
                        where=(data['Total_Revenue'] > data['Total_Costs']),
                        color='#28a745', alpha=0.15, label='Profit Zone')
        ax.fill_between(data['Month'], data['Total_Revenue']/1000, 
                        data['Total_Costs']/1000, 
                        where=(data['Total_Revenue'] < data['Total_Costs']),
                        color='#dc3545', alpha=0.15, label='Loss Zone')
        
        ax.set_xlabel('2026')
        ax.set_ylabel('R Thousands')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        
        st.pyplot(fig)
    
    with col2:
        st.subheader("Breakdown")
        
        # Revenue breakdown pie
        fig2, ax2 = plt.subplots(figsize=(5, 4))
        
        revenue_sources = [
            total_annual['Fee_Revenue'],
            total_annual['Escrow_Revenue'],
            total_annual['Collections_Revenue']
        ]
        labels = ['Transaction Fees', 'Escrow Fees', 'Collections']
        colors = ['#2E86C1', '#28a745', '#8E44AD']
        
        ax2.pie(revenue_sources, labels=labels, autopct='%1.0f%%', colors=colors, startangle=90)
        ax2.axis('equal')
        ax2.set_title('Revenue Sources')
        
        st.pyplot(fig2)
    
    # =========================================================================
    # CHART 2: Cost Breakdown
    # =========================================================================
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Cost Breakdown")
        
        fig3, ax3 = plt.subplots(figsize=(8, 4))
        
        cost_categories = [
            total_annual['AWS_Costs'],
            total_annual['Dev_Costs'],
            total_annual['Marketing_Costs'],
            total_annual['Compliance_Costs'],
            total_annual['Multi_Cloud_Costs']
        ]
        cost_labels = ['AWS Infrastructure', 'Development', 'Marketing', 'Compliance', 'Multi-Cloud']
        colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6']
        
        bars = ax3.bar(cost_labels, [c/1000 for c in cost_categories], color=colors)
        ax3.set_ylabel('R Thousands')
        ax3.set_title('Annual Cost Breakdown')
        ax3.tick_params(axis='x', rotation=15)
        
        for bar, val in zip(bars, [c/1000 for c in cost_categories]):
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
                    f'R{val:,.0f}K', ha='center', va='bottom', fontsize=8)
        
        st.pyplot(fig3)
    
    with col2:
        st.subheader("Monthly Profit Trend")
        
        fig4, ax4 = plt.subplots(figsize=(8, 4))
        
        colors_profit = ['#28a745' if p > 0 else '#dc3545' for p in data['Profit']]
        ax4.bar(data['Month'], data['Profit']/1000, color=colors_profit, alpha=0.7)
        ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax4.set_xlabel('2026')
        ax4.set_ylabel('R Thousands')
        ax4.set_title('Monthly Profit / Loss')
        ax4.grid(True, alpha=0.3, axis='y')
        
        st.pyplot(fig4)
    
    # =========================================================================
    # CHART 3: Unit Economics
    # =========================================================================
    
    st.subheader("Unit Economics Per Invoice")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_revenue_per_invoice = total_annual['Total_Revenue'] / total_annual['Invoices']
        st.metric("Revenue / Invoice", f"R{avg_revenue_per_invoice:,.0f}")
    
    with col2:
        avg_cost_per_invoice = total_annual['Total_Costs'] / total_annual['Invoices']
        st.metric("Cost / Invoice", f"R{avg_cost_per_invoice:,.0f}")
    
    with col3:
        avg_profit_per_invoice = (total_annual['Total_Revenue'] - total_annual['Total_Costs']) / total_annual['Invoices']
        st.metric("Profit / Invoice", f"R{avg_profit_per_invoice:,.0f}")
    
    with col4:
        break_even_volume = total_annual['Total_Costs'].iloc[0] / avg_revenue_per_invoice
        st.metric("Break-Even Volume", f"{int(break_even_volume):,} / month")
    
    # =========================================================================
    # COST STRUCTURE TABLE
    # =========================================================================
    
    with st.expander("View Detailed Cost & Revenue Table"):
        
        # Revenue breakdown by month
        st.subheader("Revenue Breakdown")
        revenue_table = pd.DataFrame({
            'Month': data['Month'],
            'Invoices': data['Invoices'],
            'Transaction Fees (R)': data['Fee_Revenue'].apply(lambda x: f"R{x:,.0f}"),
            'Escrow Fees (R)': data['Escrow_Revenue'].apply(lambda x: f"R{x:,.0f}"),
            'Collections (R)': data['Collections_Revenue'].apply(lambda x: f"R{x:,.0f}"),
            'Total Revenue (R)': data['Total_Revenue'].apply(lambda x: f"R{x:,.0f}"),
            'Profit (R)': data['Profit'].apply(lambda x: f"R{x:,.0f}"),
            'Margin %': data['Profit_Margin'].apply(lambda x: f"{x:.1f}%")
        })
        st.dataframe(revenue_table, use_container_width=True)
        
        st.subheader("Cost Breakdown")
        cost_table = pd.DataFrame({
            'Month': data['Month'],
            'Invoices': data['Invoices'],
            'AWS Costs (R)': data['AWS_Costs'].apply(lambda x: f"R{x:,.0f}"),
            'Development (R)': data['Dev_Costs'].apply(lambda x: f"R{x:,.0f}"),
            'Marketing (R)': data['Marketing_Costs'].apply(lambda x: f"R{x:,.0f}"),
            'Compliance (R)': data['Compliance_Costs'].apply(lambda x: f"R{x:,.0f}"),
            'Multi-Cloud (R)': data['Multi_Cloud_Costs'].apply(lambda x: f"R{x:,.0f}"),
            'Total Costs (R)': data['Total_Costs'].apply(lambda x: f"R{x:,.0f}")
        })
        st.dataframe(cost_table, use_container_width=True)

if __name__ == "__main__":
    main()