"""
Shifa — 2027 Ramp, Fee Split & Startup Capital
================================================
Answers three judge questions directly:
  1. Realistic invoice-volume estimate for Year 1 (2027) — pilot-stage,
     not the old 200->3,000/month curve.
  2. What Shifa actually earns from the transaction fee, and how that's
     split with Absa (Absa fronts the capital and carries credit risk —
     that's a bank's job, not a startup's — so Shifa's own P&L only
     carries its own platform costs).
  3. How much startup capital Shifa needs to implement and run this
     until its own P&L breaks even — separate from the capital Absa
     deploys to fund invoices, which is Absa's balance sheet, not Shifa's.
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Shifa — 2027 Ramp & Capital Ask", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    .main-header { font-size: 2rem; font-weight: 700; color: #1a3a5c; text-align: center; padding: 1rem 0; }
    .sub-header { font-size: 1rem; font-weight: 400; color: #4a6a8a; text-align: center; padding-bottom: 1rem; }
    .metric-card { background-color: #f8f9fa; border-radius: 8px; padding: 1rem; border-left: 4px solid #2E86C1; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .ask-card { background-color: #fff8f5; border-radius: 8px; padding: 1rem; border-left: 4px solid #E4002B; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .metric-value { font-size: 1.8rem; font-weight: 700; color: #1a3a5c; }
    .ask-value { font-size: 1.8rem; font-weight: 700; color: #9C0018; }
    .metric-label { font-size: 0.8rem; color: #6c757d; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def generate_2027_model(shifa_fee_share, aws_per_invoice, manual_review_share, cost_per_review,
                         team_start, team_end, absa_start_share, absa_end_share):
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    idx = np.arange(12)

    # --- Conservative pilot-stage volume ramp ---
    # Starts at real pilot scale, not an established platform's volume.
    invoices = np.round(15 + (330 - 15) / (1 + np.exp(-0.55 * (idx - 6.5)))).astype(int)
    avg_value = np.round(150000 + (230000 - 150000) / (1 + np.exp(-0.4 * (idx - 5))), -3)
    absa_share = absa_start_share + (absa_end_share - absa_start_share) / (1 + np.exp(-0.4 * (idx - 6)))

    total_value = invoices * avg_value
    absa_value = total_value * absa_share
    nonabsa_value = total_value * (1 - absa_share)

    # --- The pool that gets split with Absa ---
    gross_transaction_fee = absa_value * 0.015 + nonabsa_value * 0.045
    escrow_revenue = total_value * 0.005       # Shifa's own service fee — not split
    collections_revenue = total_value * 0.005 * 0.10  # Shifa's own service fee — not split

    shifa_fee_revenue = gross_transaction_fee * shifa_fee_share
    absa_fee_revenue = gross_transaction_fee * (1 - shifa_fee_share)
    shifa_revenue = shifa_fee_revenue + escrow_revenue + collections_revenue

    # --- Absa's side (capital deployed, for context only — not Shifa's ask) ---
    advance_rate = absa_share * 0.85 + (1 - absa_share) * 0.65
    absa_advances = total_value * advance_rate

    # --- Shifa's OWN operating costs (grounded in sourced AWS pricing) ---
    aws_cost = invoices * aws_per_invoice
    credit_desk_cost = invoices * manual_review_share * cost_per_review
    team_cost = np.round(np.linspace(team_start, team_end, 12), -3)
    marketing = 8000 + invoices * 15
    compliance = np.full(12, 10000.0)

    shifa_cost = aws_cost + credit_desk_cost + team_cost + marketing + compliance
    shifa_profit = shifa_revenue - shifa_cost
    cumulative = np.cumsum(shifa_profit)

    return pd.DataFrame({
        'Month': months, 'Invoices': invoices, 'Avg_Value': avg_value, 'Absa_Share_Pct': absa_share * 100,
        'Total_Value': total_value, 'Gross_Transaction_Fee': gross_transaction_fee,
        'Shifa_Fee_Revenue': shifa_fee_revenue, 'Absa_Fee_Revenue': absa_fee_revenue,
        'Escrow_Revenue': escrow_revenue, 'Collections_Revenue': collections_revenue,
        'Shifa_Revenue': shifa_revenue, 'AWS_Cost': aws_cost, 'CreditDesk_Cost': credit_desk_cost,
        'Team_Cost': team_cost, 'Marketing_Cost': marketing, 'Compliance_Cost': compliance,
        'Shifa_Cost': shifa_cost, 'Shifa_Profit': shifa_profit, 'Cumulative': cumulative,
        'Absa_Advances': absa_advances,
    })


def main():
    st.markdown('<p class="main-header">Shifa — 2027 Ramp, Fee Split &amp; Startup Capital</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Realistic Year 1 volume · What Shifa keeps vs. Absa · What we actually need to raise</p>', unsafe_allow_html=True)

    st.sidebar.header("Assumptions")
    st.sidebar.caption("Nothing here is fact — these are the levers a real negotiation with Absa and a real cost quote would settle. Move them to stress-test.")

    shifa_fee_share = st.sidebar.slider("Shifa's share of the transaction fee (%)", 10, 60, 35, 5,
                                         help="Absa keeps the rest — they're funding the advances and carrying credit risk, which is why they keep the larger share.") / 100.0
    absa_start = st.sidebar.slider("Absa customer share — January (%)", 10, 50, 25, 5) / 100.0
    absa_end = st.sidebar.slider("Absa customer share — December (%)", 30, 80, 50, 5) / 100.0
    aws_per_invoice = st.sidebar.slider("AWS infra cost per invoice (R)", 0.5, 3.0, 0.96, 0.05,
                                         help="Sourced bottom-up from AWS's published af-south-1 pricing — Textract Forms extraction is ~99% of this line.")
    manual_review_share = st.sidebar.slider("Share of invoices routed to credit desk (%)", 0, 100, 60, 5) / 100.0
    cost_per_review = st.sidebar.slider("Cost per manual review (R)", 50, 500, 180, 10)
    team_start = st.sidebar.slider("Team cost — January (R/month)", 20000, 150000, 60000, 5000,
                                    help="Placeholder for founder/contractor cost — replace with real numbers.")
    team_end = st.sidebar.slider("Team cost — December (R/month)", 60000, 300000, 120000, 5000)

    st.sidebar.markdown("---")
    st.sidebar.subheader("One-Time Implementation Costs")
    sec_cost = st.sidebar.number_input("Security hardening & pen test (R)", value=80000, step=5000)
    legal_cost = st.sidebar.number_input("Legal & compliance setup (R)", value=60000, step=5000)
    integration_cost = st.sidebar.number_input("Absa API integration & UAT (R)", value=50000, step=5000)
    prelaunch_cost = st.sidebar.number_input("Pre-launch team runway (R)", value=100000, step=5000)
    buffer_months = st.sidebar.slider("Safety-buffer months (beyond breakeven math)", 0, 12, 4, 1,
                                       help="No credible team budgets to the exact rand the model predicts — this covers slower-than-modeled adoption.")

    data = generate_2027_model(shifa_fee_share, aws_per_invoice, manual_review_share, cost_per_review,
                                team_start, team_end, absa_start, absa_end)

    total_impl = sec_cost + legal_cost + integration_cost + prelaunch_cost
    trough = data['Cumulative'].min()
    trough_month = data.loc[data['Cumulative'].idxmin(), 'Month']
    breakeven_rows = data[data['Cumulative'] >= 0]
    breakeven_month = breakeven_rows.iloc[0]['Month'] if len(breakeven_rows) else "Not within 2027"
    buffer_amount = buffer_months * data['Shifa_Cost'].iloc[0]
    total_ask = total_impl + abs(min(trough, 0)) + buffer_amount

    # =========================================================================
    # KPI ROW
    # =========================================================================
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{int(data['Invoices'].sum()):,}</div>
        <div class="metric-label">Invoices, Full Year 2027</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">R{data['Shifa_Revenue'].sum()/1e6:.2f}M</div>
        <div class="metric-label">Shifa's Own Revenue (Year 1)</div></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{breakeven_month}</div>
        <div class="metric-label">Shifa P&amp;L Breakeven Month</div></div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">R{trough:,.0f}</div>
        <div class="metric-label">Peak Cash Gap (Month: {trough_month})</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # =========================================================================
    # STARTUP CAPITAL ASK
    # =========================================================================
    st.markdown("### What We Actually Need to Raise")
    acol1, acol2, acol3, acol4 = st.columns(4)
    with acol1:
        st.markdown(f"""<div class="ask-card"><div class="ask-value">R{total_impl:,.0f}</div>
        <div class="metric-label">One-Time Implementation</div></div>""", unsafe_allow_html=True)
    with acol2:
        st.markdown(f"""<div class="ask-card"><div class="ask-value">R{abs(min(trough,0)):,.0f}</div>
        <div class="metric-label">P&amp;L Funding Gap to Breakeven</div></div>""", unsafe_allow_html=True)
    with acol3:
        st.markdown(f"""<div class="ask-card"><div class="ask-value">R{buffer_amount:,.0f}</div>
        <div class="metric-label">{buffer_months}-Month Safety Buffer</div></div>""", unsafe_allow_html=True)
    with acol4:
        st.markdown(f"""<div class="ask-card" style="border-left-color:#1a3a5c;"><div class="metric-value">R{total_ask:,.0f}</div>
        <div class="metric-label">Total Recommended Raise</div></div>""", unsafe_allow_html=True)

    st.caption("This is Shifa's own ask — covering platform build-out and operating burn. It does NOT include the capital Absa deploys to fund invoice advances; that's Absa's balance sheet and credit risk, the same as any bank funding a lending product.")
    st.caption("Absa's advances for context, not part of Shifa's ask: " + f"R{data['Absa_Advances'].sum()/1e6:,.1f}M deployed across 2027, generating Absa R{data['Absa_Fee_Revenue'].sum()/1e6:,.2f}M in fee revenue.")

    st.markdown("---")

    # =========================================================================
    # THE DOUBLE BAR CHART — Cost vs. Revenue ("profit"), month by month
    # =========================================================================
    st.subheader("Monthly Cost vs. Revenue — 2027")
    st.caption("Two bars per month: what it costs Shifa to run the platform that month, and what Shifa earns from its share of the fee plus its own service fees. Early months, cost sits above revenue — that gap is the funding ask. From the breakeven month on, revenue overtakes cost.")

    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(data))
    width = 0.38

    bars_cost = ax.bar(x - width/2, data['Shifa_Cost'], width, label='Cost', color='#E74C3C')
    bars_rev = ax.bar(x + width/2, data['Shifa_Revenue'], width, label='Revenue ("Profit" line)', color='#2E86C1')

    ax.set_xticks(x)
    ax.set_xticklabels(data['Month'])
    ax.set_ylabel('R')
    ax.set_title("Shifa's Own Monthly Cost vs. Revenue — 2027")
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3, axis='y')

    # Mark the breakeven month
    if len(breakeven_rows):
        be_idx = data[data['Month'] == breakeven_month].index[0]
        ax.axvline(be_idx - 0.5, color='#28a745', linestyle='--', linewidth=1.5)
        ax.text(be_idx - 0.45, ax.get_ylim()[1]*0.95, 'Breakeven', color='#28a745', fontsize=9, fontweight='bold')

    st.pyplot(fig)

    st.caption("Net monthly profit/loss (Revenue − Cost) and cumulative position, for reference:")
    profit_table = pd.DataFrame({
        'Month': data['Month'],
        'Invoices': data['Invoices'],
        'Cost (R)': data['Shifa_Cost'].apply(lambda x: f"R{x:,.0f}"),
        'Revenue (R)': data['Shifa_Revenue'].apply(lambda x: f"R{x:,.0f}"),
        'Net (R)': data['Shifa_Profit'].apply(lambda x: f"R{x:,.0f}"),
        'Cumulative (R)': data['Cumulative'].apply(lambda x: f"R{x:,.0f}"),
    })
    st.dataframe(profit_table, use_container_width=True, hide_index=True)

    st.markdown("---")

    # =========================================================================
    # FEE SPLIT DETAIL
    # =========================================================================
    st.subheader("Where the Fee Actually Goes")
    col1, col2 = st.columns([1, 1])
    with col1:
        fig2, ax2 = plt.subplots(figsize=(5, 4))
        totals = [data['Shifa_Fee_Revenue'].sum(), data['Absa_Fee_Revenue'].sum()]
        ax2.pie(totals, labels=[f'Shifa ({shifa_fee_share*100:.0f}%)', f'Absa ({(1-shifa_fee_share)*100:.0f}%)'],
                autopct=lambda p: f'R{p/100*sum(totals)/1e6:.1f}M', colors=['#2E86C1', '#E4002B'], startangle=90)
        ax2.set_title('Annual Transaction-Fee Split')
        st.pyplot(fig2)
    with col2:
        st.markdown("""
        **Why the split looks like this:**
        - **Absa** fronts the advance to the SME, carries the funding cost and the credit risk if the buyer doesn't pay — the same role a bank plays in any factoring product. That's why it keeps the larger share.
        - **Shifa** carries the platform: extraction, verification, the trust-scoring integration, and the credit-desk workflow for invoices above R100k. Shifa's share is sized to cover that operating cost, not to compete with a bank's margin on deployed capital.
        - **Escrow and collections fees stay with Shifa entirely** — those are platform services, not capital-risk compensation, so they aren't part of the negotiated split.
        """)

    with st.expander("View Full Monthly Detail"):
        st.dataframe(data.round(0), use_container_width=True)


if __name__ == "__main__":
    main()
