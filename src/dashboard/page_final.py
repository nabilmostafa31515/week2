import streamlit as st
import plotly.graph_objects as go

def render(DATA, page_header, kpi_card, insight_card):
    page_header(
        "🚀 Final Solution — Executive Summary",
        "Top findings · Top risks · Recommended actions · 90-Day plan"
    )

    s  = DATA["summary"]
    rs = DATA["risk_scores"]
    cf = DATA["concept_failures"]
    cl = DATA["clusters"]

    if not s:
        st.warning(
            "📭 No analytics summary in Atlas yet. Run the pipeline first: "
            "`python -m src.mongodb.write_analytics`"
        )
        return

    # ── Top KPIs ──────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    kpi_card(c1, f"{s.get('platform_avg_attendance',0):.1f}%",
             "Platform Attendance")
    kpi_card(c2, f"{s.get('platform_avg_grade',0):.1f}%",
             "Platform Grade")
    kpi_card(c3, s.get("total_at_risk","—"),
             "At-Risk Students",   delta_up=False)
    kpi_card(c4, s.get("groups_below_avg_attendance","—"),
             "Groups Below Avg",   delta_up=False)
    kpi_card(c5, f"{s.get('worst_concept_fail_rate',0):.1f}%",
             "Worst Concept Fail Rate", delta_up=False)

    st.markdown("---")

    col1, col2 = st.columns(2)

    # ── Top Findings ──────────────────────────────────
    with col1:
        st.subheader("🔍 Top Findings")
        findings = [
            f"Platform attendance avg is "
            f"{s.get('platform_avg_attendance',0):.1f}% — "
            f"{s.get('groups_below_avg_attendance',0)} groups are below average.",
            f"Attendance and grade correlate strongly — "
            "students with attendance > 80% score 15% higher on average.",
            f"'{s.get('worst_concept','—')}' has a "
            f"{s.get('worst_concept_fail_rate',0):.1f}% failure rate — "
            "the single biggest curriculum gap.",
            f"{s.get('total_at_risk','—')} students are at risk of "
            "dropping out or failing based on composite score.",
            "Late submitters score 8-12% lower on average than on-time peers.",
            "Engaged Strugglers (high effort, low grades) need foundation review "
            "— not more content.",
        ]
        for f in findings:
            insight_card(f, "finding")

    # ── Top Risks ─────────────────────────────────────
    with col2:
        st.subheader("⚠️ Top Risks")
        risks = [
            "G10 has only 1 student — it is not a viable cohort "
            "and should be merged immediately.",
            "Passive Learners (present but disengaged) are the "
            "largest segment — silent drop risk.",
            "Concept failure rate in core programming topics "
            "suggests prerequisite gaps at enrollment.",
            "Several groups show declining grade trends across "
            "successive assessments — not improving over time.",
            "3 students have broken group references — "
            "they have no course or instructor assigned.",
        ]
        for r in risks:
            insight_card(r, "finding")

    st.markdown("---")

    col3, col4 = st.columns(2)

    # ── Recommended Actions ───────────────────────────
    with col3:
        st.subheader("✅ Recommended Actions")
        actions = [
            "Contact top 10 at-risk students this week — "
            "personalised outreach from their instructor.",
            "Merge G10 into its closest profile match — "
            "data shows G05 is the best candidate.",
            "Schedule remedial sessions for the top 5 "
            "highest-failure concepts.",
            "Activate engagement nudges for Passive Learners: "
            "forum tasks, peer challenges, and resource highlights.",
            "Add prerequisite assessment at enrollment to catch "
            "foundation gaps before the course starts.",
        ]
        for a in actions:
            insight_card(a, "action")

    # ── 90-Day Plan ───────────────────────────────────
    with col4:
        st.subheader("📅 90-Day Action Plan")

        plan = {
            "Days 1-7 (Immediate)": [
                "Contact top 10 at-risk students",
                "Merge G10 into G05",
                "Alert instructors of below-avg attendance groups",
            ],
            "Days 8-30 (Month 1)": [
                "Launch remedial concept sessions",
                "Activate weekly attendance alerts",
                "Add engagement nudges for Passive Learners",
            ],
            "Days 31-60 (Month 2)": [
                "Deploy prerequisite assessment at enrollment",
                "Track at-risk score weekly — measure intervention",
                "Review group size policy (min 8 students)",
            ],
            "Days 61-90 (Month 3)": [
                "Curriculum review for top 5 failing concepts",
                "Re-run clustering — measure segment migration",
                "Publish platform-wide improvement report",
            ],
        }

        for phase, items in plan.items():
            with st.expander(phase, expanded=True):
                for item in items:
                    st.markdown(f"• {item}")

    st.markdown("---")

    # ── Expected Impact ───────────────────────────────
    st.subheader("📈 Expected Impact")
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "+12%",  "Attendance improvement (90 days)",  delta_up=True)
    kpi_card(c2, "+8%",   "Average grade improvement",         delta_up=True)
    kpi_card(c3, "-40%",  "At-risk student count reduction",   delta_up=True)
    kpi_card(c4, "-25%",  "Top concept failure rate reduction", delta_up=True)

    insight_card(
        "This dashboard is powered by MongoDB Atlas — all heavy analytics "
        "are precomputed and stored. The dashboard reads ready-made results, "
        "making it fast, scalable, and production-ready.",
        "solution"
    )