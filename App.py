"""
Shifa — Cost & Revenue Dashboard
Professional, clean financial dashboard for the pitch deck

v2: adds cost of capital (funding cost on advances outstanding) and a
credit-loss provision — the two cost lines a factoring/invoice-financing
business cannot honestly omit — and fixes two calculation bugs from v1:
  - "Avg Profit Margin" was computing annual margin / 12 (meaningless)
  - "Break-Even Volume" divided one month's fixed cost by the full-year
    average revenue-per-invoice instead of that month's own economics
  - Non-Absa fee revenue was applying BOTH the Absa and non-Absa rate to
    the full monthly value instead of splitting volume by customer mix
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
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
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1a3a5c;
        padding-top: 0.5rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        border-left: 4px solid #2E86C1;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .risk-card {
        background-color: #fff8f5;
        border-radius: 8px;
        padding: 1rem;
        border-left: 4px solid #E4002B;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a3a5c;
    }
    .risk-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #9C0018;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #6c757d;
    }
    .positive { color: #28a745; }
    .negative { color: #dc3545; }
    .neutral { color: #6c757d; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA GENERATION
# ============================================================================

@st.cache_data
def generate_financial_data(cost_of_funds_annual, credit_loss_rate, days_outstanding,
                             manual_review_share, cost_per_review):
    """Generate Year 1 cost and revenue projections, including the cost of
    the capital advanced against invoices and a credit-loss provision —
    the two line items that actually dominate an invoice-financing
    business's cost base, alongside a manual-review cost for invoices
    routed to the credit desk (see the >R100k admin-review threshold)."""

    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    months_idx = np.arange(len(months))

    # Invoices per month (growing from 200 to 3,000 as distribution matures)
    invoices_per_month = np.round(200 + (3000 - 200) / (1 + np.exp(-0.6 * (months_idx - 6)))).astype(int)

    # Average invoice value: R150,000 -> R250,000
    avg_invoice_value = np.round(150000 + 100000 / (1 + np.exp(-0.4 * (months_idx - 5))), -3)
    total_value_per_month = invoices_per_month * avg_invoice_value

    # Absa share of volume grows over the year — the built-in 4.5% -> 1.5%
    # incentive converting non-Absa users, same story as the deck's funnel
    absa_share = 0.30 + (0.55 - 0.30) / (1 + np.exp(-0.5 * (months_idx - 6)))
    absa_value = total_value_per_month * absa_share
    nonabsa_value = total_value_per_month * (1 - absa_share)

    # --- REVENUE ---
    # Transaction fee: 1.5% on the Absa-customer share, 4.5% on the rest —
    # split by actual segment value, not stacked on the full total (v1 bug)
    fee_revenue = absa_value * 0.015 + nonabsa_value * 0.045
    escrow_revenue = total_value_per_month * 0.005          # 0.5% escrow fee on all value
    collections_revenue = total_value_per_month * 0.005 * 0.10  # 0.5% on the 10% needing collections
    total_revenue = fee_revenue + escrow_revenue + collections_revenue

    # --- CAPITAL DEPLOYED ---
    # Blended advance rate: 85% for Absa customers, 65% for non-Absa
    advance_rate = absa_share * 0.85 + (1 - absa_share) * 0.65
    advances = total_value_per_month * advance_rate  # actual cash paid out to SMEs

    # --- OPERATING COSTS ---
    aws_lambda = 2000 + (invoices_per_month * 0.15)
    aws_textract = invoices_per_month * 0.30
    aws_bedrock = invoices_per_month * 0.20
    aws_storage = 500 + (invoices_per_month * 0.01)
    aws_total = aws_lambda + aws_textract + aws_bedrock + aws_storage
    multi_cloud = aws_total * 0.10  # redundancy premium
    infra_costs = aws_total + multi_cloud

    dev_costs = np.full(len(months), 25000.0)
    marketing = 5000 + (invoices_per_month * 0.50)
    compliance = np.full(len(months), 3000.0)

    # Credit-desk review cost: invoices above the R100k threshold route to
    # a human — modeled here as a fixed share of volume (see pitch: roughly
    # 60% of a typical invoice book sits above R100k) at a modest per-review cost
    credit_desk_costs = invoices_per_month * manual_review_share * cost_per_review

    # --- COST OF CAPITAL & CREDIT RISK (previously missing entirely) ---
    # Outstanding book approximates using average days-to-repayment; advances
    # aren't repaid within the same month they're made, so the funded book
    # runs larger than a single month's advance volume
    outstanding_book = advances * (days_outstanding / 30.0)
    cost_of_capital = outstanding_book * (cost_of_funds_annual / 100.0) / 12.0
    credit_loss_provision = advances * (credit_loss_rate / 100.0)

    total_costs = (infra_costs + dev_costs + marketing + compliance
                   + credit_desk_costs + cost_of_capital + credit_loss_provision)

    profit = total_revenue - total_costs
    profit_margin = (profit / total_revenue) * 100

    return pd.DataFrame({
        'Month': months,
        'Invoices': invoices_per_month,
        'Invoice_Value': avg_invoice_value,
        'Total_Value': total_value_per_month,
        'Advances': advances,
        'Fee_Revenue': fee_revenue,
        'Escrow_Revenue': escrow_revenue,
        'Collections_Revenue': collections_revenue,
        'Total_Revenue': total_revenue,
        'Infra_Costs': infra_costs,
        'Dev_Costs': dev_costs,
        'Marketing_Costs': marketing,
        'Compliance_Costs': compliance,
        'CreditDesk_Costs': credit_desk_costs,
        'CostOfCapital': cost_of_capital,
        'CreditLoss': credit_loss_provision,
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

    # =========================================================================
    # ASSUMPTIONS (sidebar) — stress-test the model live
    # =========================================================================
    st.sidebar.header("Model Assumptions")
    st.sidebar.caption("These four inputs drive the cost of capital and credit-risk lines below. Move them to stress-test the model live.")

    cost_of_funds = st.sidebar.slider("Cost of funds (annual %)", 6.0, 18.0, 11.0, 0.5,
                                       help="Blended annual rate to fund advances — proxy for a bank funding line off SA prime.")
    credit_loss_rate = st.sidebar.slider("Credit loss rate (% of advances)", 0.0, 4.0, 1.2, 0.1,
                                          help="Expected bad-debt rate on advanced capital — typical trade-receivable factoring range is roughly 0.5–2%.")
    days_outstanding = st.sidebar.slider("Average days to repayment", 15, 90, 45, 5,
                                          help="How long advanced capital sits on the book before the buyer settles.")
    manual_review_share = st.sidebar.slider("Share of invoices routed to credit desk (%)", 0, 100, 60, 5,
                                             help="Invoices above the R100k threshold get a human reviewer — see the admin-side threshold.") / 100.0
    cost_per_review = st.sidebar.slider("Cost per manual review (R)", 50, 500, 180, 10)

    data = generate_financial_data(cost_of_funds, credit_loss_rate, days_outstanding,
                                    manual_review_share, cost_per_review)
    latest = data.iloc[-1]
    total_annual = data.sum(numeric_only=True)
    blended_margin = (total_annual['Profit'] / total_annual['Total_Revenue']) * 100

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
            <div class="metric-label">Annual Costs (incl. capital &amp; risk)</div>
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
            <div class="metric-value" style="color: {'#28a745' if blended_margin > 10 else '#6c757d'}">
                {blended_margin:.1f}%
            </div>
            <div class="metric-label">Blended Profit Margin</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{int(total_annual['Invoices']):,}</div>
            <div class="metric-label">Annual Invoices</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # =========================================================================
    # CAPITAL & RISK ROW — the two lines the old model omitted
    # =========================================================================
    st.markdown('<p class="section-header">Capital &amp; Credit Risk</p>', unsafe_allow_html=True)
    rcol1, rcol2, rcol3 = st.columns(3)

    with rcol1:
        st.markdown(f"""
        <div class="risk-card">
            <div class="risk-value">R{total_annual['Advances']/1e6:,.1f}M</div>
            <div class="metric-label">Capital Advanced to SMEs (Year 1)</div>
        </div>
        """, unsafe_allow_html=True)

    with rcol2:
        st.markdown(f"""
        <div class="risk-card">
            <div class="risk-value">R{total_annual['CostOfCapital']/1e6:,.1f}M</div>
            <div class="metric-label">Cost of Capital ({cost_of_funds:.1f}%/yr funding rate)</div>
        </div>
        """, unsafe_allow_html=True)

    with rcol3:
        st.markdown(f"""
        <div class="risk-card">
            <div class="risk-value">R{total_annual['CreditLoss']/1e6:,.1f}M</div>
            <div class="metric-label">Credit-Loss Provision ({credit_loss_rate:.1f}% of advances)</div>
        </div>
        """, unsafe_allow_html=True)

    st.caption("These two lines are why margin looks materially different from a pure SaaS or software fee business — Shifa is deploying capital, not just moving data.")

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
        st.subheader("Revenue Sources")

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

        st.pyplot(fig2)

    # =========================================================================
    # CHART 2: Cost Breakdown
    # =========================================================================

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Cost Breakdown")

        fig3, ax3 = plt.subplots(figsize=(8, 4.2))

        cost_categories = [
            total_annual['Infra_Costs'],
            total_annual['Dev_Costs'],
            total_annual['Marketing_Costs'],
            total_annual['Compliance_Costs'],
            total_annual['CreditDesk_Costs'],
            total_annual['CostOfCapital'],
            total_annual['CreditLoss'],
        ]
        cost_labels = ['Infra', 'Dev', 'Marketing', 'Compliance', 'Credit Desk', 'Cost of\nCapital', 'Credit\nLoss']
        colors = ['#3498db', '#2ecc71', '#f39c12', '#95a5a6', '#8E44AD', '#E4002B', '#9C0018']

        bars = ax3.bar(cost_labels, [c/1000 for c in cost_categories], color=colors)
        ax3.set_ylabel('R Thousands')
        ax3.set_title('Annual Cost Breakdown')
        ax3.tick_params(axis='x', rotation=0, labelsize=8)

        for bar, val in zip(bars, [c/1000 for c in cost_categories]):
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(cost_categories)/1000*0.02,
                    f'R{val:,.0f}K', ha='center', va='bottom', fontsize=7.5)

        st.pyplot(fig3)

    with col2:
        st.subheader("Monthly Profit Trend")

        fig4, ax4 = plt.subplots(figsize=(8, 4.2))

        colors_profit = ['#28a745' if p > 0 else '#dc3545' for p in data['Profit']]
        ax4.bar(data['Month'], data['Profit']/1000, color=colors_profit, alpha=0.7)
        ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax4.set_xlabel('2026')
        ax4.set_ylabel('R Thousands')
        ax4.set_title('Monthly Profit / Loss (After Capital & Credit-Loss Costs)')
        ax4.grid(True, alpha=0.3, axis='y')

        st.pyplot(fig4)

    # =========================================================================
    # CHART 3: Unit Economics
    # =========================================================================

    st.subheader("Unit Economics Per Invoice")

    col1, col2, col3, col4 = st.columns(4)

    avg_revenue_per_invoice = total_annual['Total_Revenue'] / total_annual['Invoices']
    avg_cost_per_invoice = total_annual['Total_Costs'] / total_annual['Invoices']
    avg_profit_per_invoice = avg_revenue_per_invoice - avg_cost_per_invoice

    with col1:
        st.metric("Revenue / Invoice", f"R{avg_revenue_per_invoice:,.0f}")

    with col2:
        st.metric("Cost / Invoice", f"R{avg_cost_per_invoice:,.0f}")

    with col3:
        st.metric("Profit / Invoice", f"R{avg_profit_per_invoice:,.0f}")

    with col4:
        # Break-even volume: fixed costs vs. the *same month's* contribution
        # margin per invoice — not the old bug of mixing one month's fixed
        # cost against the full-year average revenue-per-invoice
        fixed_costs_latest = (latest['Dev_Costs'] + latest['Compliance_Costs']
                               + 2000 + 500 + 5000)  # fixed floors inside Infra/Marketing
        revenue_per_invoice_latest = latest['Total_Revenue'] / latest['Invoices']
        variable_cost_per_invoice_latest = (latest['Total_Costs'] - fixed_costs_latest) / latest['Invoices']
        contribution_margin = revenue_per_invoice_latest - variable_cost_per_invoice_latest
        break_even_volume = fixed_costs_latest / contribution_margin if contribution_margin > 0 else float('nan')
        st.metric("Break-Even Volume (Dec economics)", f"{break_even_volume:,.0f} / month")

    st.caption("Break-even is calculated on December's own fixed vs. variable cost split — not blended against the full-year average, which understates how quickly the model actually breaks even.")

    # =========================================================================
    # COST STRUCTURE TABLE
    # =========================================================================

    with st.expander("View Detailed Cost & Revenue Table"):

        st.subheader("Revenue & Capital Breakdown")
        revenue_table = pd.DataFrame({
            'Month': data['Month'],
            'Invoices': data['Invoices'],
            'Advances Paid Out (R)': data['Advances'].apply(lambda x: f"R{x:,.0f}"),
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
            'Infra (R)': data['Infra_Costs'].apply(lambda x: f"R{x:,.0f}"),
            'Development (R)': data['Dev_Costs'].apply(lambda x: f"R{x:,.0f}"),
            'Marketing (R)': data['Marketing_Costs'].apply(lambda x: f"R{x:,.0f}"),
            'Compliance (R)': data['Compliance_Costs'].apply(lambda x: f"R{x:,.0f}"),
            'Credit Desk (R)': data['CreditDesk_Costs'].apply(lambda x: f"R{x:,.0f}"),
            'Cost of Capital (R)': data['CostOfCapital'].apply(lambda x: f"R{x:,.0f}"),
            'Credit Loss (R)': data['CreditLoss'].apply(lambda x: f"R{x:,.0f}"),
            'Total Costs (R)': data['Total_Costs'].apply(lambda x: f"R{x:,.0f}")
        })
        st.dataframe(cost_table, use_container_width=True)

if __name__ == "__main__":
    main()
