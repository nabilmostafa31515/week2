import streamlit as st
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


def render(DATA, page_header, kpi_card, insight_card):
    page_header(
        "Q5 — Engagement vs Performance",
        "Does more platform activity mean better grades?"
    )

    ss = DATA["student_summary"]
    if ss is None or ss.empty:
        st.warning("No student-summary data available in Atlas.")
        return

    df = ss[ss["engagement_score"].notna() & ss["avg_grade"].notna()].copy()
    if df.empty:
        st.warning("No students have both engagement and grade recorded.")
        return

    corr_eng = df["engagement_score"].corr(df["avg_grade"])
    has_watch = "total_watch_hours" in df.columns
    corr_watch = df["total_watch_hours"].corr(df["avg_grade"]) if has_watch else float("nan")

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, f"{corr_eng:.2f}", "Engagement ↔ Grade (r)",
             delta_up=corr_eng > 0)
    kpi_card(c2, f"{corr_watch:.2f}" if has_watch else "—",
             "Watch-time ↔ Grade (r)", delta_up=(corr_watch > 0) if has_watch else True)
    kpi_card(c3, f"{df['engagement_score'].mean():.0f}", "Avg Engagement Score")
    if has_watch:
        kpi_card(c4, f"{df['total_watch_hours'].mean():.1f}h", "Avg Watch Time")
    else:
        kpi_card(c4, len(df), "Students")

    st.markdown("---")

    color_col = "course_name" if "course_name" in df.columns else None
    hover = [c for c in ["full_name", "login_count", "total_watch_hours"] if c in df.columns]
    fig = px.scatter(
        df, x="engagement_score", y="avg_grade",
        size="total_watch_hours" if has_watch else None,
        color=color_col, hover_data=hover,
        title=(f"Engagement Score vs Grade  "
               f"(r_eng = {corr_eng:.2f}"
               + (f", r_watch = {corr_watch:.2f}" if has_watch else "") + ")"),
        labels={"engagement_score": "Engagement Score",
                "avg_grade": "Average Grade (%)"},
        template="plotly_dark", height=520, opacity=0.65, size_max=20,
    )

    m, b = np.polyfit(df["engagement_score"], df["avg_grade"], 1)
    xs = np.array([df["engagement_score"].min(), df["engagement_score"].max()])
    fig.add_trace(go.Scatter(
        x=xs, y=m * xs + b, mode="lines", name="Trend",
        line=dict(color="#F6A623", width=3),
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    # Insights
    insight_card(
        f"Engagement correlates with grade at r = {corr_eng:.2f}"
        + (f" and watch-time at r = {corr_watch:.2f}." if has_watch else "."),
        "finding")
    insight_card(
        "Engagement is a leading indicator — it can be observed weeks before "
        "the first grade lands, making it the earliest intervention signal "
        "available.",
        "insight")
    insight_card(
        "Watch for the 'Engaged Strugglers' quadrant (high engagement, low grade): "
        "these students need foundation review, not more content — see Q11.",
        "action")
