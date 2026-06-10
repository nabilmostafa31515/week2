import streamlit as st
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


def render(DATA, page_header, kpi_card, insight_card):
    page_header(
        "Q4 — Attendance vs Grade",
        "Does showing up actually translate into better grades?"
    )

    ss = DATA["student_summary"]
    if ss is None or ss.empty:
        st.warning("No student-summary data available in Atlas.")
        return

    df = ss[ss["attendance_rate"].notna() & ss["avg_grade"].notna()].copy()
    if df.empty:
        st.warning("No students have both attendance and grade recorded.")
        return

    corr = df["attendance_rate"].corr(df["avg_grade"])

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    strength = ("Strong" if abs(corr) > 0.5 else
                "Moderate" if abs(corr) > 0.3 else "Weak")
    kpi_card(c1, f"{corr:.2f}", "Pearson correlation (r)",
             delta=strength + " link", delta_up=corr > 0)
    hi = df[df["attendance_rate"] >= 80]["avg_grade"].mean()
    lo = df[df["attendance_rate"] < 80]["avg_grade"].mean()
    kpi_card(c2, f"{hi:.1f}%", "Avg grade (attendance ≥ 80%)", delta_up=True)
    kpi_card(c3, f"{lo:.1f}%", "Avg grade (attendance < 80%)", delta_up=False)
    gap = (hi - lo) if (np.isfinite(hi) and np.isfinite(lo)) else 0
    kpi_card(c4, f"{gap:+.1f}%", "Grade gap", delta_up=gap > 0)

    st.markdown("---")

    color_col = "course_name" if "course_name" in df.columns else None
    hover = [c for c in ["full_name", "group_name"] if c in df.columns]
    fig = px.scatter(
        df, x="attendance_rate", y="avg_grade",
        color=color_col, hover_data=hover,
        title=f"Attendance Rate vs Average Grade  (r = {corr:.2f})",
        labels={"attendance_rate": "Attendance Rate (%)",
                "avg_grade": "Average Grade (%)"},
        template="plotly_dark", height=520, opacity=0.7,
    )

    # manual OLS trendline (avoids the statsmodels dependency)
    m, b = np.polyfit(df["attendance_rate"], df["avg_grade"], 1)
    xs = np.array([df["attendance_rate"].min(), df["attendance_rate"].max()])
    fig.add_trace(go.Scatter(
        x=xs, y=m * xs + b, mode="lines", name="Trend",
        line=dict(color="#F6A623", width=3),
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    # Insights
    if corr > 0.5:
        verdict = ("a strong positive relationship — higher attendance "
                   "reliably predicts higher grades.")
    elif corr > 0.3:
        verdict = ("a moderate positive relationship between attendance and grades.")
    else:
        verdict = ("a weak link — attendance alone does not explain grades; "
                   "other factors dominate.")
    insight_card(
        f"The correlation is r = {corr:.2f}, indicating {verdict}", "finding")
    insight_card(
        f"Students attending ≥ 80% of sessions average {hi:.1f}%, versus "
        f"{lo:.1f}% for those below 80% — a {gap:+.1f}% swing.", "insight")
    insight_card(
        "Make attendance a tracked early-warning signal: any student dropping "
        "below 80% should trigger an automatic check-in before grades slip.",
        "action")
