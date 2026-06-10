import streamlit as st
from plotly.subplots import make_subplots
import plotly.graph_objects as go


def render(DATA, page_header, kpi_card, insight_card):
    page_header(
        "Q9 — Cohort Trends Over Time",
        "When does the whole cohort dip — and do attendance & engagement move together?"
    )

    ma = DATA["monthly_att"]
    me = DATA["monthly_eng"]
    if (ma is None or ma.empty) and (me is None or me.empty):
        st.warning("No monthly trend data available in Atlas.")
        return

    att = (ma.groupby("month")["monthly_att_rate"].mean().reset_index()
           .sort_values("month")) if ma is not None and not ma.empty else None
    eng = me.sort_values("month") if me is not None and not me.empty else None

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    if att is not None and not att.empty:
        dip = att.loc[att["monthly_att_rate"].idxmin()]
        peak = att.loc[att["monthly_att_rate"].idxmax()]
        kpi_card(c1, f"{att['monthly_att_rate'].mean():.1f}%", "Avg Monthly Attendance")
        kpi_card(c2, str(dip["month"]), "Lowest Attendance Month",
                 delta_up=False, delta=f"{dip['monthly_att_rate']:.1f}%")
        kpi_card(c3, str(peak["month"]), "Best Attendance Month",
                 delta_up=True, delta=f"{peak['monthly_att_rate']:.1f}%")
    if eng is not None and not eng.empty and "total_events" in eng.columns:
        kpi_card(c4, f"{int(eng['total_events'].sum()):,}", "Total Engagement Events")

    st.markdown("---")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    if att is not None and not att.empty:
        fig.add_trace(go.Scatter(
            x=att["month"], y=att["monthly_att_rate"],
            name="Attendance Rate (%)", mode="lines+markers",
            line=dict(color="#0D7377", width=2.5), marker=dict(size=8),
        ), secondary_y=False)
    if eng is not None and not eng.empty and "total_events" in eng.columns:
        fig.add_trace(go.Scatter(
            x=eng["month"], y=eng["total_events"],
            name="Engagement Events", mode="lines+markers",
            line=dict(color="#F6A623", width=2, dash="dot"), marker=dict(size=7),
        ), secondary_y=True)
    fig.update_layout(
        title="Attendance & Engagement Trends",
        template="plotly_dark", height=460,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.2),
    )
    fig.update_yaxes(title_text="Attendance Rate (%)", secondary_y=False)
    fig.update_yaxes(title_text="Engagement Events", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

    # Insights
    if att is not None and not att.empty:
        insight_card(
            f"Attendance bottoms out in {dip['month']} "
            f"({dip['monthly_att_rate']:.1f}%) — likely an exam period, holiday, "
            "or mid-term burnout window.",
            "finding")
    insight_card(
        "When attendance and engagement dip in the same month, the cause is "
        "usually external (calendar / workload) rather than content quality.",
        "insight")
    insight_card(
        "Front-load support and lighten deadlines around the identified dip "
        "month, and schedule a re-engagement push immediately after.",
        "action")
