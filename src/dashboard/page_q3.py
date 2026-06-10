import streamlit as st
import plotly.graph_objects as go


def render(DATA, page_header, kpi_card, insight_card):
    page_header(
        "Q3 — Course Performance Comparison",
        "Which courses are thriving and which are struggling?"
    )

    cm = DATA["course_metrics"]
    if cm is None or cm.empty:
        st.warning("No course-metrics data available in Atlas.")
        return

    df = cm.sort_values("course_avg_grade", ascending=False).reset_index(drop=True)
    name_col = "course_name" if "course_name" in df.columns else "course_id"

    best  = df.iloc[0]
    worst = df.iloc[-1]

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, f"{best['course_avg_grade']:.1f}%",
             f"Best: {best[name_col]}", delta_up=True)
    kpi_card(c2, f"{worst['course_avg_grade']:.1f}%",
             f"Worst: {worst[name_col]}", delta_up=False)
    kpi_card(c3, f"{df['course_avg_grade'].mean():.1f}%", "Platform Avg Grade")
    kpi_card(c4, len(df), "Courses Tracked")

    st.markdown("---")

    # Bar + std error bars
    colors = [
        "#2E7D32" if i == 0 else "#E53935" if i == len(df) - 1 else "#0D7377"
        for i in range(len(df))
    ]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df[name_col],
        y=df["course_avg_grade"],
        error_y=dict(type="data", array=df.get("course_grade_std"),
                     visible="course_grade_std" in df.columns, color="#F6A623"),
        marker_color=colors,
        text=[f"{v:.1f}%" for v in df["course_avg_grade"]],
        textposition="outside",
    ))
    fig.update_layout(
        template="plotly_dark",
        height=460,
        yaxis=dict(range=[0, 110], title="Average Grade (%)"),
        xaxis_title="Course",
        title="Average Grade per Course (error bars = std deviation)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Detail table
    st.subheader("Course Detail")
    cols = [c for c in [name_col, "category", "difficulty_level", "duration_weeks",
                        "course_avg_grade", "course_grade_std",
                        "course_min_grade", "course_max_grade"] if c in df.columns]
    fmt = {c: "{:.1f}%" for c in ["course_avg_grade", "course_grade_std",
                                  "course_min_grade", "course_max_grade"] if c in df.columns}
    st.dataframe(df[cols].style.format(fmt), use_container_width=True)

    # Insights
    insight_card(
        f"'{worst[name_col]}' is the weakest course at "
        f"{worst['course_avg_grade']:.1f}% average — "
        f"{best['course_avg_grade'] - worst['course_avg_grade']:.1f} points below the best course.",
        "finding"
    )
    insight_card(
        "A large std-deviation bar means the cohort is split into strong and weak "
        "learners — a sign that pacing or prerequisites need attention, not just "
        "the average.",
        "insight"
    )
    insight_card(
        f"Run a content review on '{worst[name_col]}'. Compare its structure to "
        f"'{best[name_col]}', which is performing best, and port what works.",
        "action"
    )
