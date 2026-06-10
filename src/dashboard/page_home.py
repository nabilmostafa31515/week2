import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

def render(DATA, page_header, kpi_card, insight_card):
    page_header(
        "🎓 Kayfa Student Analytics Dashboard",
        "Executive overview — Month 1 · Week 2 Evaluation · Data Analytics Track"
    )

    s  = DATA["summary"]
    gm = DATA["group_metrics"]
    rs = DATA["risk_scores"]
    ss = DATA["student_summary"]

    if gm is None or gm.empty or "group_attendance_rate" not in gm.columns:
        st.warning(
            "📭 No analytics found in MongoDB Atlas yet. "
            "Run the pipeline first:\n\n"
            "```\npython -m src.mongodb.write_analytics\n```"
        )
        return

    # ── KPI row ──────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    kpi_card(c1, s.get("total_students", "—"),
             "Total Students")
    kpi_card(c2, f"{s.get('platform_avg_attendance', 0):.1f}%",
             "Avg Attendance")
    kpi_card(c3, f"{s.get('platform_avg_grade', 0):.1f}%",
             "Avg Grade")
    kpi_card(c4, f"{s.get('platform_avg_engagement', 0):.0f}",
             "Avg Engagement Score")
    kpi_card(c5, s.get("total_at_risk", "—"),
             "At-Risk Students",
             delta="Needs action", delta_up=False)

    st.markdown("---")

    # ── Charts row ───────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Attendance Rate by Group")
        fig = px.bar(
            gm.sort_values("group_attendance_rate"),
            x="group_id",
            y="group_attendance_rate",
            color="below_platform_avg",
            color_discrete_map={True: "#E53935", False: "#0D7377"},
            template="plotly_dark",
            height=350,
            labels={"group_attendance_rate": "Rate (%)",
                    "group_id": "Group"},
        )
        fig.update_layout(showlegend=False,
                          paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Risk Score Distribution")
        fig2 = px.histogram(
            rs,
            x="at_risk_score",
            nbins=30,
            template="plotly_dark",
            height=350,
            color_discrete_sequence=["#0D7377"],
            labels={"at_risk_score": "At-Risk Score"},
        )
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                           plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

    # ── Insight cards ────────────────────────────────
    worst = s.get("worst_concept", "—")
    fail  = s.get("worst_concept_fail_rate", 0)
    below = s.get("groups_below_avg_attendance", 0)

    insight_card(
        f"{below} groups are below the platform attendance average — "
        "these cohorts need immediate engagement review.",
        "finding"
    )
    insight_card(
        f"The hardest concept on the platform is '{worst}' "
        f"with a {fail:.1f}% failure rate — a critical curriculum gap.",
        "finding"
    )
    insight_card(
        f"{s.get('total_at_risk','—')} students are classified as at-risk "
        "based on combined attendance, grade, engagement and concept data.",
        "action"
    )
    insight_card(
        "All precomputed analytics are stored in MongoDB Atlas. "
        "This dashboard reads ready-made results — zero recomputation on load.",
        "solution"
    )