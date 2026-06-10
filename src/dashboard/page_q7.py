import streamlit as st
import plotly.graph_objects as go


def render(DATA, page_header, kpi_card, insight_card):
    page_header(
        "Q7 — Concept Mastery Trends",
        "Is the hardest concept improving or getting worse over time?"
    )

    ct = DATA["concept_trends"]
    cf = DATA["concept_failures"]
    if ct is None or ct.empty:
        st.warning("No concept-trend data available in Atlas.")
        return

    # default to the worst concept, but let the user explore any
    default_name = None
    if cf is not None and not cf.empty:
        default_name = cf.sort_values("failure_rate", ascending=False).iloc[0]["concept_name"]

    names = sorted(ct["concept_name"].dropna().unique().tolist())
    idx = names.index(default_name) if default_name in names else 0
    concept = st.selectbox("Select concept", names, index=idx)

    df = ct[ct["concept_name"] == concept].sort_values("month")
    if df.empty:
        st.warning("No trend rows for that concept.")
        return

    first, last = df["pass_rate"].iloc[0], df["pass_rate"].iloc[-1]
    delta = last - first
    direction = ("Improving" if delta > 5 else
                 "Declining" if delta < -5 else "Flat")

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, f"{last:.1f}%", "Latest Pass Rate")
    kpi_card(c2, f"{delta:+.1f}%", "Change Over Term",
             delta_up=delta >= 0, delta=direction)
    kpi_card(c3, f"{df['pass_rate'].mean():.1f}%", "Mean Pass Rate")
    kpi_card(c4, int(df["attempts"].sum()) if "attempts" in df.columns else len(df),
             "Total Attempts")

    st.markdown("---")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["month"], y=df["pass_rate"], mode="lines+markers",
        name="Pass Rate", line=dict(color="#0D7377", width=2.5),
        marker=dict(size=8), fill="tozeroy",
        fillcolor="rgba(13,115,119,0.15)",
    ))
    if "avg_score" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["month"], y=df["avg_score"], mode="lines+markers",
            name="Avg Score", line=dict(color="#F6A623", width=1.5, dash="dot"),
            marker=dict(size=6),
        ))
    fig.update_layout(
        title=f"Mastery Trend: '{concept}'",
        xaxis_title="Month", yaxis_title="Rate / Score (%)",
        template="plotly_dark", height=440,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.2),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Insights
    insight_card(
        f"'{concept}' is {direction.lower()} — pass rate moved {delta:+.1f}% "
        f"over the term (from {first:.1f}% to {last:.1f}%).",
        "finding" if delta < -5 else "insight")
    insight_card(
        "A flat or declining mastery trend means the current teaching approach "
        "is not landing — repetition alone will not move it.",
        "insight")
    insight_card(
        "If the trend is declining, re-sequence the prerequisite material and "
        "add a formative check; if improving, document what changed and replicate it.",
        "action")
