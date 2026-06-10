import streamlit as st
import plotly.express as px


def render(DATA, page_header, kpi_card, insight_card):
    page_header(
        "Q11 — Student Segmentation",
        "Four data-driven personas for targeted intervention"
    )

    sc = DATA["student_clusters"]
    cl = DATA["clusters"]
    if sc is None or sc.empty:
        st.warning("No clustering data available in Atlas.")
        return

    # KPIs — one per segment, sized by population
    sizes = sc["cluster_label"].value_counts()
    cols = st.columns(min(4, len(sizes)) or 1)
    for col, (label, n) in zip(cols, sizes.items()):
        kpi_card(col, int(n), str(label))

    st.markdown("---")

    hover = [c for c in ["full_name", "failed_concepts", "course_name"] if c in sc.columns]
    fig = px.scatter(
        sc, x="attendance_rate", y="avg_grade",
        color="cluster_label",
        size="engagement_score" if "engagement_score" in sc.columns else None,
        hover_data=hover,
        title="Student Segments — Attendance vs Grade",
        labels={"attendance_rate": "Attendance Rate (%)",
                "avg_grade": "Average Grade (%)",
                "cluster_label": "Segment"},
        template="plotly_dark", height=520, opacity=0.75, size_max=18,
    )
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    # Segment profile cards from the clusters collection
    if cl is not None and not cl.empty:
        st.subheader("Segment Profiles & Recommended Actions")
        for _, row in cl.sort_values("avg_grade", ascending=False).iterrows():
            with st.expander(
                f"{row.get('display_label', row['cluster_label'])} "
                f"— {int(row.get('student_count', 0))} students",
                expanded=True,
            ):
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Avg Grade",      f"{row.get('avg_grade', 0):.1f}%")
                m2.metric("Avg Attendance", f"{row.get('avg_attendance', 0):.1f}%")
                m3.metric("Avg Engagement", f"{row.get('avg_engagement', 0):.0f}")
                m4.metric("Avg Failed Concepts", f"{row.get('avg_failed_concepts', 0):.1f}")
                if row.get("description"):
                    st.markdown(f"**Profile:** {row['description']}")
                if row.get("recommended_action"):
                    st.markdown(f"**Action:** {row['recommended_action']}")

    # Insights
    largest = sizes.index[0]
    insight_card(
        f"The largest segment is '{largest}' ({int(sizes.iloc[0])} students). "
        "Sizing your intervention to the biggest segment yields the most impact.",
        "finding")
    insight_card(
        "Segments were built with K-Means on attendance, grade, engagement and "
        "failed concepts (k = 4, chosen for clean mapping to four business personas).",
        "insight")
    insight_card(
        "Assign a tailored playbook per segment rather than one-size-fits-all: "
        "stretch goals for High Achievers, foundations for Engaged Strugglers, "
        "outreach for At Risk, activation nudges for Passive Learners.",
        "action")
