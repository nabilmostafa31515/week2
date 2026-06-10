import streamlit as st
import plotly.express as px


def render(DATA, page_header, kpi_card, insight_card):
    page_header(
        "Q15 — Group Grade Trends",
        "Which groups are improving across assessments, and which are sliding?"
    )

    gt = DATA["grade_trends"]
    if gt is None or gt.empty:
        st.warning("No grade-trend data available in Atlas.")
        return

    df = gt.copy()

    # attach group names if available
    gm = DATA.get("group_metrics")
    name_col = "group_id"
    if gm is not None and not gm.empty and "group_name" in gm.columns:
        df = df.merge(gm[["group_id", "group_name"]], on="group_id", how="left")
        name_col = "group_name"

    df = df.sort_values(["group_id", "assessment_id"])

    # compute per-group first→last delta
    trends = {}
    for gid, g in df.groupby("group_id"):
        g = g.sort_values("assessment_id")
        if len(g) >= 2:
            trends[gid] = g["avg_score"].iloc[-1] - g["avg_score"].iloc[0]
    improving = [g for g, d in trends.items() if d > 3]
    declining = [g for g, d in trends.items() if d < -3]

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, len(df["group_id"].unique()), "Groups Tracked")
    kpi_card(c2, len(improving), "Improving Groups", delta_up=True)
    kpi_card(c3, len(declining), "Declining Groups", delta_up=False)
    if trends:
        worst_gid = min(trends, key=trends.get)
        kpi_card(c4, str(worst_gid), "Steepest Decline",
                 delta_up=False, delta=f"{trends[worst_gid]:+.1f}%")

    st.markdown("---")

    fig = px.line(
        df, x="assessment_id", y="avg_score", color=name_col, markers=True,
        title="Group Grade Trends Across Assessments",
        labels={"avg_score": "Average Score (%)",
                "assessment_id": "Assessment", name_col: "Group"},
        template="plotly_dark", height=520,
    )
    fig.update_layout(
        xaxis=dict(tickangle=-45),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.3),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Insights
    insight_card(
        f"Declining groups: {declining or 'none'}. A downward slope across "
        "successive assessments means the gap is widening, not closing.",
        "finding")
    insight_card(
        f"Improving groups: {improving or 'none'}. Capture what these instructors "
        "are doing differently — it is the cheapest source of best practice.",
        "insight")
    insight_card(
        "Schedule a mid-term review for any declining group before the next "
        "assessment, while the trend is still reversible.",
        "action")
