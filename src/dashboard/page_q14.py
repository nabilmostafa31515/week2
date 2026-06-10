import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

def render(DATA, page_header, kpi_card, insight_card):
    page_header(
        "Q14 — At-Risk Student Ranking",
        "Top 10 students an instructor should contact first"
    )

    rs = DATA["risk_scores"]
    if rs is None or rs.empty or "at_risk_score" not in rs.columns:
        st.warning(
            "📭 No risk-score data in Atlas yet. Run the pipeline first: "
            "`python -m src.mongodb.write_analytics`"
        )
        return

    top10 = rs.head(10).copy()
    total_at_risk = rs["is_at_risk"].sum()
    avg_risk = rs["at_risk_score"].mean()

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, total_at_risk,         "Total At-Risk Students",
             delta_up=False, delta="Top 20%")
    kpi_card(c2, f"{avg_risk:.3f}",     "Platform Avg Risk Score")
    kpi_card(c3, f"{rs['at_risk_score'].max():.3f}",
             "Highest Risk Score",      delta_up=False)
    kpi_card(c4, top10["group_name"].value_counts().index[0],
             "Most At-Risk Group",      delta_up=False)

    st.markdown("---")

    # Filters
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_group = st.selectbox(
            "Filter by Group",
            ["All"] + sorted(rs["group_name"].dropna().unique().tolist())
        )
    with col_f2:
        top_n = st.slider("Show top N students", 5, 50, 10)

    filtered = rs if selected_group == "All" \
               else rs[rs["group_name"] == selected_group]
    filtered = filtered.head(top_n).copy()
    filtered["display_name"] = (
        filtered["full_name"] + " (" + filtered["group_name"] + ")"
    )

    # Stacked bar chart
    fig = go.Figure()
    components = {
        "risk_grade":      ("Grade Risk",       "#E53935"),
        "risk_attendance": ("Attendance Risk",  "#F6A623"),
        "risk_engagement": ("Engagement Risk",  "#455A64"),
        "risk_concepts":   ("Concept Risk",     "#14BDAC"),
    }
    for col, (label, color) in components.items():
        fig.add_trace(go.Bar(
            y=filtered["display_name"],
            x=filtered[col],
            name=label,
            orientation="h",
            marker_color=color,
        ))

    fig.update_layout(
        barmode="stack",
        template="plotly_dark",
        height=max(400, top_n * 42),
        xaxis_title="Risk Score",
        yaxis=dict(autorange="reversed"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.15),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Detail table
    st.subheader("Student Detail")
    display_cols = [
        "full_name", "group_name", "course_name",
        "attendance_rate", "avg_grade",
        "engagement_score", "failed_concepts", "at_risk_score"
    ]
    st.dataframe(
        filtered[display_cols].style
        .format({
            "attendance_rate": "{:.1f}%",
            "avg_grade":       "{:.1f}%",
            "at_risk_score":   "{:.3f}",
        })
        .background_gradient(
            subset=["at_risk_score"],
            cmap="Reds"
        ),
        use_container_width=True,
    )

    # Insights
    top1 = top10.iloc[0]
    insight_card(
        f"The highest-risk student is {top1['full_name']} "
        f"(score={top1['at_risk_score']:.3f}) in {top1['group_name']}. "
        f"Attendance: {top1['attendance_rate']:.1f}%, "
        f"Grade: {top1['avg_grade']:.1f}%.",
        "finding"
    )
    insight_card(
        "The at-risk score combines 4 dimensions: "
        "Grade (35%), Attendance (30%), Engagement (20%), "
        "Failed Concepts (15%). A student can score high "
        "on one dimension and still be flagged.",
        "insight"
    )
    insight_card(
        "Instructors should contact these students this week. "
        "Prioritise those with HIGH grade risk AND high concept failures "
        "as they are the hardest to recover without direct intervention.",
        "action"
    )
    insight_card(
        "Export this list weekly from the MongoDB Atlas dashboard. "
        "Track each student's risk score over time — "
        "a declining score means the intervention is working.",
        "solution"
    )