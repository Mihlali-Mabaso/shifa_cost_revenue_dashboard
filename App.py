"""
AbsaFlow / Shifa -- Business Model & Value Projection
======================================================

A single-file Streamlit application that models the economics of the
AbsaFlow (Shifa) invoice-financing platform from launch (2027) onward:

  - market sizing and adoption (penetration of the overdue-invoice market)
  - fee revenue (Absa-customer vs non-Absa-customer pricing)
  - infrastructure cost, built bottom-up from real AWS Lambda measurements
    (CloudWatch REPORT lines captured for VerifyFunction, 20 invocations,
    af-south-1 -- see AbsaFlow_VerifyFunction_Latency_Stats)
  - the value Absa captures: its contractual share of every fee processed,
    plus the long-term banking-relationship value created when non-Absa
    SMEs convert into full Absa customers

Run locally with:   streamlit run app.py
Deploy on Streamlit Community Cloud by pointing it at this file plus a
requirements.txt containing: streamlit, pandas, numpy, plotly
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------
# Page setup / styling
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="AbsaFlow -- Business Model & Value Projection",
    layout="wide",
    initial_sidebar_state="expanded",
)

ABSA_RED = "#E4002B"
DARK = "#1A1A1A"
GREY = "#5C5C5C"
LIGHT = "#F4F4F4"

st.markdown(
    f"""
    <style>
    .block-container {{ padding-top: 1.6rem; }}
    div[data-testid="stMetric"] {{
        background-color: {LIGHT};
        border: 1px solid #e6e6e6;
        border-radius: 6px;
        padding: 14px 16px 10px 16px;
    }}
    div[data-testid="stMetricValue"] {{ color: {DARK}; }}
    div[data-testid="stMetricLabel"] {{ color: {GREY}; }}
    .banner {{
        background-color: {DARK};
        color: white;
        padding: 28px 32px;
        border-radius: 8px;
        margin-bottom: 22px;
    }}
    .banner h1 {{ color: white; margin-bottom: 4px; font-size: 2.1rem; }}
    .banner p {{ color: #B0B0B0; margin: 0; font-size: 1.02rem; }}
    .accent {{ color: {ABSA_RED}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="banner">
        <h1>AbsaFlow <span class="accent">|</span> Shifa -- Business Model & Value Projection</h1>
        <p>What the platform costs to run, what it earns, and what Absa captures --
        modeled year by year from launch.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------
# Formatting helpers
# ----------------------------------------------------------------------
def rand(value: float, decimals: int = 0) -> str:
    """Plain Rand formatting with thousands separators."""
    return f"R{value:,.{decimals}f}"


def rand_big(value: float) -> str:
    """Human-scaled Rand formatting: R1.2 billion / R340.5 million / R82.0 thousand."""
    abs_v = abs(value)
    if abs_v >= 1_000_000_000:
        return f"R{value / 1_000_000_000:,.2f} billion"
    if abs_v >= 1_000_000:
        return f"R{value / 1_000_000:,.1f} million"
    if abs_v >= 1_000:
        return f"R{value / 1_000:,.1f} thousand"
    return f"R{value:,.0f}"


# ----------------------------------------------------------------------
# Sidebar -- all assumptions live here, nothing is hard-coded downstream
# ----------------------------------------------------------------------
st.sidebar.header("Launch & Horizon")
launch_year = st.sidebar.number_input("Launch year", value=2027, step=1)
horizon = st.sidebar.slider("Projection horizon (years)", 5, 15, 10)

st.sidebar.header("Market (South African overdue invoices)")
market_overdue_value = st.sidebar.number_input(
    "Overdue invoice value at launch (R)", value=12_400_000_000, step=100_000_000, format="%d"
)
market_invoice_count = st.sidebar.number_input(
    "Outstanding invoices at launch (#)", value=95_399, step=1_000
)
market_growth_pct = st.sidebar.slider("Annual market growth (%)", 0.0, 20.0, 8.0) / 100

st.sidebar.header("Adoption")
year1_penetration_pct = st.sidebar.slider("Year 1 penetration of market (%)", 0.1, 15.0, 2.0) / 100
terminal_penetration_pct = st.sidebar.slider(
    f"Penetration by year {int(launch_year) + horizon - 1} (%)", 1.0, 80.0, 35.0
) / 100

st.sidebar.header("Customer mix (Absa vs non-Absa)")
absa_mix_start_pct = st.sidebar.slider("Absa-customer share -- Year 1 (%)", 0.0, 100.0, 60.0) / 100
absa_mix_terminal_pct = st.sidebar.slider(
    f"Absa-customer share -- Year {int(launch_year) + horizon - 1} (%)", 0.0, 100.0, 85.0
) / 100

st.sidebar.header("Fee structure")
fee_absa_pct = st.sidebar.slider("Fee -- Absa customers (%)", 0.5, 5.0, 1.5) / 100
fee_non_absa_pct = st.sidebar.slider("Fee -- non-Absa customers (%)", 0.5, 8.0, 4.5) / 100
absa_fee_share_pct = st.sidebar.slider(
    "Absa's contractual share of every fee processed (%)", 0.0, 100.0, 30.0
) / 100

st.sidebar.header("Customer conversion (non-Absa to Absa)")
invoices_per_sme_per_year = st.sidebar.slider("Average invoices per SME per year", 1, 52, 12)
conversion_rate_pct = st.sidebar.slider(
    "Annual conversion rate: non-Absa SMEs to full Absa banking (%)", 0.0, 40.0, 10.0
) / 100
relationship_value_per_customer = st.sidebar.number_input(
    "Lifetime relationship value per converted SME (R)", value=450_000, step=10_000
)

st.sidebar.header("Infrastructure cost")
usd_zar = st.sidebar.number_input("USD/ZAR exchange rate", value=18.50, step=0.10)
production_warm_rate_pct = st.sidebar.slider(
    "Assumed warm-invocation rate in steady production (%)", 50.0, 99.0, 92.0
) / 100
override_infra_cost = st.sidebar.checkbox("Override computed infra cost per invoice", value=False)
manual_infra_cost = st.sidebar.number_input(
    "Manual infra cost per invoice (R)", value=3.20, step=0.10, disabled=not override_infra_cost
)

st.sidebar.header("Valuation")
discount_rate_pct = st.sidebar.slider("Discount rate for NPV (%)", 0.0, 25.0, 12.0) / 100


# ----------------------------------------------------------------------
# Bottom-up infrastructure cost per invoice
# Grounded in real CloudWatch measurements of VerifyFunction
# (20 invocations, af-south-1): 14 cold starts averaging ~3,734 ms handler
# + ~357 ms init, 6 warm invocations averaging ~223 ms.
# Other functions are estimated on the same cold/warm pattern since they
# share the same .NET 8 / Lambda runtime, scaled by their configured memory.
# ----------------------------------------------------------------------
LAMBDA_GB_SECOND_USD = 0.0000166667
LAMBDA_PER_REQUEST_USD = 0.0000002
TEXTRACT_PER_PAGE_USD = 0.0015
BEDROCK_INPUT_PER_1K_USD = 0.00025   # Claude 3 Haiku, input tokens
BEDROCK_OUTPUT_PER_1K_USD = 0.00125  # Claude 3 Haiku, output tokens
DYNAMODB_WRITE_PER_MILLION_USD = 1.25
DYNAMODB_READ_PER_MILLION_USD = 0.25
S3_PUT_PER_1000_USD = 0.005
S3_GET_PER_1000_USD = 0.0004
SNS_PUBLISH_PER_MILLION_USD = 0.50

LAMBDA_FUNCTIONS = {
    # name                      memory_mb   cold_ms(measured/estimated)  warm_ms
    "Upload / Extract (Textract call)": (512, 4_500, 650),
    "Verify (measured -- CloudWatch)": (256, 3_734 + 357, 223),
    "Risk / Fund": (256, 3_800, 300),
    "Notify": (256, 1_200, 80),
}


def lambda_cost_usd(memory_mb: int, cold_ms: float, warm_ms: float, warm_rate: float) -> float:
    blended_ms = warm_rate * warm_ms + (1 - warm_rate) * cold_ms
    gb_seconds = (memory_mb / 1024) * (blended_ms / 1000)
    return gb_seconds * LAMBDA_GB_SECOND_USD + LAMBDA_PER_REQUEST_USD


def build_cost_breakdown(warm_rate: float, usd_zar_rate: float) -> pd.DataFrame:
    rows = []
    lambda_total = 0.0
    for name, (mem, cold, warm) in LAMBDA_FUNCTIONS.items():
        c = lambda_cost_usd(mem, cold, warm, warm_rate)
        lambda_total += c
        rows.append((f"Lambda -- {name}", f"{mem} MB, {int(warm_rate * 100)}% warm", c))

    textract = TEXTRACT_PER_PAGE_USD * 1  # 1 page assumed per invoice
    rows.append(("Textract (document OCR)", "1 page per invoice", textract))

    bedrock = 600 / 1000 * BEDROCK_INPUT_PER_1K_USD + 200 / 1000 * BEDROCK_OUTPUT_PER_1K_USD
    rows.append(("Bedrock (Claude 3 Haiku funding rationale)", "~600 in / 200 out tokens", bedrock))

    dynamo = (6 / 1_000_000) * DYNAMODB_WRITE_PER_MILLION_USD + (
        10 / 1_000_000
    ) * DYNAMODB_READ_PER_MILLION_USD
    rows.append(("DynamoDB (on-demand)", "6 writes + 10 reads per invoice", dynamo))

    s3 = (2 / 1000) * S3_PUT_PER_1000_USD + (3 / 1000) * S3_GET_PER_1000_USD
    rows.append(("S3 (document storage)", "2 PUT + 3 GET per invoice", s3))

    sns = (1 / 1_000_000) * SNS_PUBLISH_PER_MILLION_USD
    rows.append(("SNS (notifications)", "1 publish per invoice", sns))

    df = pd.DataFrame(rows, columns=["Component", "Assumption", "Cost per invoice (USD)"])
    df["Cost per invoice (R)"] = df["Cost per invoice (USD)"] * usd_zar_rate
    return df


cost_breakdown = build_cost_breakdown(production_warm_rate_pct, usd_zar)
computed_infra_cost_per_invoice = cost_breakdown["Cost per invoice (R)"].sum()
infra_cost_per_invoice = manual_infra_cost if override_infra_cost else computed_infra_cost_per_invoice


# ----------------------------------------------------------------------
# Core year-by-year projection
# ----------------------------------------------------------------------
t = np.arange(horizon)
years = (int(launch_year) + t).tolist()

market_value = market_overdue_value * (1 + market_growth_pct) ** t
market_count = market_invoice_count * (1 + market_growth_pct) ** t
avg_invoice_value = market_value / market_count

penetration = np.linspace(year1_penetration_pct, terminal_penetration_pct, horizon)
absa_mix = np.linspace(absa_mix_start_pct, absa_mix_terminal_pct, horizon)

invoices_processed = market_count * penetration
transaction_value = invoices_processed * avg_invoice_value

blended_fee_pct = absa_mix * fee_absa_pct + (1 - absa_mix) * fee_non_absa_pct
gross_fee_revenue = transaction_value * blended_fee_pct

infra_cost_total = invoices_processed * infra_cost_per_invoice
net_platform_margin = gross_fee_revenue - infra_cost_total

absa_fee_share_amount = gross_fee_revenue * absa_fee_share_pct

total_smes = invoices_processed / invoices_per_sme_per_year
non_absa_smes = total_smes * (1 - absa_mix)
new_conversions = non_absa_smes * conversion_rate_pct
cumulative_conversions = np.cumsum(new_conversions)
relationship_value_created = new_conversions * relationship_value_per_customer

absa_total_value = absa_fee_share_amount + relationship_value_created
discount_factors = 1 / (1 + discount_rate_pct) ** (t + 1)
absa_value_pv = absa_total_value * discount_factors

df = pd.DataFrame(
    {
        "Year": years,
        "Invoices processed": invoices_processed,
        "Avg invoice value (R)": avg_invoice_value,
        "Transaction value (R)": transaction_value,
        "Blended fee (%)": blended_fee_pct * 100,
        "Gross fee revenue (R)": gross_fee_revenue,
        "Infra cost (R)": infra_cost_total,
        "Net platform margin (R)": net_platform_margin,
        "Absa fee share (R)": absa_fee_share_amount,
        "New Absa conversions (SMEs)": new_conversions,
        "Cumulative Absa conversions (SMEs)": cumulative_conversions,
        "Relationship value created (R)": relationship_value_created,
        "Absa total value (R)": absa_total_value,
        "PV of Absa value (R)": absa_value_pv,
    }
)

# ----------------------------------------------------------------------
# Headline totals
# ----------------------------------------------------------------------
total_invoices = invoices_processed.sum()
total_transaction_value = transaction_value.sum()
total_gross_revenue = gross_fee_revenue.sum()
total_infra_cost = infra_cost_total.sum()
total_net_margin = net_platform_margin.sum()
total_absa_fee_share = absa_fee_share_amount.sum()
total_relationship_value = relationship_value_created.sum()
total_absa_value = absa_total_value.sum()
total_npv = absa_value_pv.sum()
total_conversions = cumulative_conversions[-1] if horizon > 0 else 0


# ----------------------------------------------------------------------
# Tabs
# ----------------------------------------------------------------------
tab_summary, tab_market, tab_revenue, tab_absa, tab_data = st.tabs(
    [
        "Executive Summary",
        "Market & Adoption",
        "Revenue & Cost",
        "Absa Value Capture",
        "Full Projection",
    ]
)

# ---------------- Executive Summary ----------------
with tab_summary:
    st.subheader(f"{int(launch_year)} -- {years[-1]}: the headline numbers")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total transaction value processed", rand_big(total_transaction_value))
    c2.metric("Total platform fee revenue", rand_big(total_gross_revenue))
    c3.metric("Total infrastructure cost", rand_big(total_infra_cost))
    c4.metric("Net platform margin", rand_big(total_net_margin))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Absa's cumulative fee share", rand_big(total_absa_fee_share))
    c6.metric("SMEs converted to full Absa customers", f"{total_conversions:,.0f}")
    c7.metric("Long-term relationship value created", rand_big(total_relationship_value))
    c8.metric("Total value delivered to Absa", rand_big(total_absa_value))

    st.markdown(
        f"""
        <div style="background-color:{LIGHT}; padding:20px 24px; border-radius:6px; margin-top:8px;">
        <b>Net present value of Absa's total value capture, discounted at {discount_rate_pct*100:.0f}% per year:
        <span class="accent">{rand_big(total_npv)}</span></b><br><br>
        Every invoice AbsaFlow processes earns Absa a contractual share of the transaction fee immediately.
        But the larger number is not the fee -- it is the relationship. Every non-Absa SME that experiences
        same-day payment through AbsaFlow is a warm lead for a full banking relationship: transactional
        banking, deposits, and eventually lending. At an annual conversion rate of
        {conversion_rate_pct*100:.0f}% and a lifetime relationship value of {rand(relationship_value_per_customer)}
        per converted SME, the model projects <b>{total_conversions:,.0f} SMEs</b> onboarded to Absa by
        {years[-1]}, worth <span class="accent">{rand_big(total_relationship_value)}</span> on top of transaction fees --
        a pipeline that compounds year over year into a business worth hundreds of millions, trending toward
        billions, on modest, defensible assumptions.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("")
    fig = go.Figure()
    fig.add_trace(
        go.Bar(x=years, y=absa_fee_share_amount, name="Absa fee share", marker_color=ABSA_RED)
    )
    fig.add_trace(
        go.Bar(x=years, y=relationship_value_created, name="Relationship value created", marker_color=DARK)
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=np.cumsum(absa_total_value),
            name="Cumulative total value",
            mode="lines+markers",
            yaxis="y2",
            line=dict(color=GREY, width=3, dash="dot"),
        )
    )
    fig.update_layout(
        barmode="stack",
        title="Absa's total annual value capture, with cumulative running total",
        yaxis=dict(title="Value created per year (R)"),
        yaxis2=dict(title="Cumulative value (R)", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=1.12),
        height=460,
        margin=dict(t=70),
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------- Market & Adoption ----------------
with tab_market:
    st.subheader("Market size and platform adoption")
    colA, colB = st.columns(2)
    with colA:
        st.metric(f"Overdue invoice market by {years[-1]}", rand_big(market_value[-1]))
        st.metric(f"Invoices processed by AbsaFlow in {years[-1]}", f"{invoices_processed[-1]:,.0f}")
    with colB:
        st.metric(f"Market penetration in {years[-1]}", f"{penetration[-1]*100:.1f}%")
        st.metric(f"Absa-customer share in {years[-1]}", f"{absa_mix[-1]*100:.1f}%")

    fig1 = go.Figure()
    fig1.add_trace(go.Bar(x=years, y=market_count, name="Total outstanding invoices (market)", marker_color=LIGHT, marker_line_color=GREY, marker_line_width=1))
    fig1.add_trace(go.Bar(x=years, y=invoices_processed, name="Invoices processed by AbsaFlow", marker_color=ABSA_RED))
    fig1.update_layout(
        barmode="overlay",
        title="Market size vs. invoices captured by AbsaFlow",
        yaxis_title="Invoices (#)",
        height=440,
        legend=dict(orientation="h", y=1.12),
    )
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=years, y=penetration * 100, name="Market penetration (%)", line=dict(color=ABSA_RED, width=3)))
    fig2.add_trace(go.Scatter(x=years, y=absa_mix * 100, name="Absa-customer share of volume (%)", line=dict(color=DARK, width=3, dash="dash")))
    fig2.update_layout(title="Penetration and customer-mix trajectory", yaxis_title="Percent", height=400)
    st.plotly_chart(fig2, use_container_width=True)

# ---------------- Revenue & Cost ----------------
with tab_revenue:
    st.subheader("Revenue, infrastructure cost, and margin")

    with st.expander("How the per-invoice infrastructure cost is calculated (bottom-up, from measured Lambda data)"):
        st.caption(
            "Verify's cold/warm split is real, taken from CloudWatch REPORT lines for 20 production "
            "invocations of absaflow-verify-invoice in af-south-1. Other functions are estimated on the "
            "same runtime profile, scaled by their configured memory."
        )
        display_cost = cost_breakdown.copy()
        display_cost["Cost per invoice (USD)"] = display_cost["Cost per invoice (USD)"].map(lambda v: f"${v:,.6f}")
        display_cost["Cost per invoice (R)"] = display_cost["Cost per invoice (R)"].map(lambda v: f"R{v:,.4f}")
        st.dataframe(display_cost, use_container_width=True, hide_index=True)
        st.markdown(f"**Total computed infrastructure cost per invoice: {rand(computed_infra_cost_per_invoice, 4)}**")
        if override_infra_cost:
            st.info(f"Override active -- model is using a manual figure of {rand(manual_infra_cost, 2)} per invoice instead.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Infra cost per invoice used in model", rand(infra_cost_per_invoice, 2))
    c2.metric(f"Blended fee, {years[-1]}", f"{blended_fee_pct[-1]:.2f}%")
    c3.metric(f"Net platform margin, {years[-1]}", rand_big(net_platform_margin[-1]))

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(x=years, y=gross_fee_revenue, name="Gross fee revenue", marker_color=ABSA_RED))
    fig3.add_trace(go.Bar(x=years, y=-infra_cost_total, name="Infrastructure cost", marker_color=GREY))
    fig3.add_trace(go.Scatter(x=years, y=net_platform_margin, name="Net platform margin", line=dict(color=DARK, width=3)))
    fig3.update_layout(
        barmode="relative",
        title="Fee revenue vs. infrastructure cost, and resulting net margin",
        yaxis_title="R per year",
        height=460,
        legend=dict(orientation="h", y=1.12),
    )
    st.plotly_chart(fig3, use_container_width=True)

# ---------------- Absa Value Capture ----------------
with tab_absa:
    st.subheader("What Absa specifically gains")

    c1, c2, c3 = st.columns(3)
    c1.metric("Cumulative Absa fee share", rand_big(total_absa_fee_share))
    c2.metric("Cumulative relationship value", rand_big(total_relationship_value))
    c3.metric("NPV of total Absa value", rand_big(total_npv))

    fig4 = go.Figure()
    fig4.add_trace(go.Bar(x=years, y=new_conversions, name="New SME conversions per year", marker_color=ABSA_RED))
    fig4.add_trace(
        go.Scatter(
            x=years,
            y=cumulative_conversions,
            name="Cumulative SMEs converted to Absa",
            yaxis="y2",
            line=dict(color=DARK, width=3),
        )
    )
    fig4.update_layout(
        title="Non-Absa SMEs converting into full Absa banking relationships",
        yaxis=dict(title="New conversions per year"),
        yaxis2=dict(title="Cumulative conversions", overlaying="y", side="right", showgrid=False),
        height=440,
        legend=dict(orientation="h", y=1.12),
    )
    st.plotly_chart(fig4, use_container_width=True)

    fig5 = go.Figure()
    fig5.add_trace(go.Scatter(x=years, y=np.cumsum(absa_fee_share_amount), name="Cumulative fee share", stackgroup="one", line=dict(color=ABSA_RED)))
    fig5.add_trace(go.Scatter(x=years, y=np.cumsum(relationship_value_created), name="Cumulative relationship value", stackgroup="one", line=dict(color=DARK)))
    fig5.update_layout(title="Cumulative value delivered to Absa, by source", yaxis_title="R, cumulative", height=440)
    st.plotly_chart(fig5, use_container_width=True)

    st.markdown(
        f"""
        <div style="background-color:{LIGHT}; padding:18px 22px; border-radius:6px;">
        Transaction fees are the immediate, provable return. The relationship value is the strategic one:
        Absa already owns the rails AbsaFlow runs on, so every SME that converts arrives pre-qualified,
        with a live payment history Absa can underwrite against. On these assumptions that pipeline is worth
        <b>{rand_big(total_relationship_value)}</b> over {horizon} years -- and it keeps compounding well
        beyond the projection window as each cohort of converted SMEs continues banking with Absa.
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------- Full data table ----------------
with tab_data:
    st.subheader("Full year-by-year projection")
    display_df = df.copy()
    money_cols = [
        "Avg invoice value (R)", "Transaction value (R)", "Gross fee revenue (R)", "Infra cost (R)",
        "Net platform margin (R)", "Absa fee share (R)", "Relationship value created (R)",
        "Absa total value (R)", "PV of Absa value (R)",
    ]
    for col in money_cols:
        display_df[col] = display_df[col].map(lambda v: f"R{v:,.0f}")
    display_df["Invoices processed"] = display_df["Invoices processed"].map(lambda v: f"{v:,.0f}")
    display_df["New Absa conversions (SMEs)"] = display_df["New Absa conversions (SMEs)"].map(lambda v: f"{v:,.0f}")
    display_df["Cumulative Absa conversions (SMEs)"] = display_df["Cumulative Absa conversions (SMEs)"].map(lambda v: f"{v:,.0f}")
    display_df["Blended fee (%)"] = display_df["Blended fee (%)"].map(lambda v: f"{v:.2f}%")

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download full projection as CSV",
        data=csv,
        file_name="absaflow_business_model_projection.csv",
        mime="text/csv",
    )

st.markdown(
    f"""
    <div style="margin-top:28px; color:{GREY}; font-size:0.85rem;">
    All figures are model outputs driven by the assumptions in the sidebar, not guarantees. Infrastructure
    cost defaults are grounded in real CloudWatch measurements of the deployed VerifyFunction; every other
    figure -- market growth, penetration, conversion, and relationship value -- is a stated, editable
    assumption. Adjust the sidebar to stress-test the model.
    </div>
    """,
    unsafe_allow_html=True,
)
