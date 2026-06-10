import streamlit as st
import plotly.graph_objects as go


def render(DATA, page_header, kpi_card, insight_card):
    page_header(
        "Q10 — Age Band Analysis",
        "Do outcomes differ across age groups?"
    )

    ag = DATA["age_stats"]
    if ag is None or ag.empty:
        st.warning("No age-band data available in Atlas.")
        return

    df = ag.copy()
    df["age_band"] = df["age_band"].astype(str)

    best = df.loc[df["avg_grade"].idxmax()]
    worst = df.loc[df["avg_grade"].idxmin()]

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, str(best["age_band"]), "Top Age Band (grade)",
             delta_up=True, delta=f"{best['avg_grade']:.1f}%")
    kpi_card(c2, str(worst["age_band"]), "Lowest Age Band (grade)",
             delta_up=False, delta=f"{worst['avg_grade']:.1f}%")
    if "student_count" in df.columns:
        biggest = df.loc[df["student_count"].idxmax()]
        kpi_card(c3, str(biggest["age_band"]), "Largest Age Band",
                 delta=f"{int(biggest['student_count'])} students")
    kpi_card(c4, len(df), "Age Bands")

    st.markdown("---")

    metrics = [
        ("avg_grade",      "Avg Grade (%)",      "#0D7377"),
        ("avg_attendance", "Avg Attendance (%)", "#14BDAC"),
        ("avg_engagement", "Avg Engagement",     "#F6A623"),
    ]
    fig = go.Figure()
    for col, label, color in metrics:
        if col in df.columns:
            fig.add_trace(go.Bar(
                x=df["age_band"], y=df[col], name=label, marker_color=color))
    fig.update_layout(
        title="Grade, Attendance & Engagement by Age Band",
        xaxis_title="Age Band", yaxis_title="Value",
        barmode="group", template="plotly_dark", height=460,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.2),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Detail table
    st.subheader("Age Band Detail")
    fmt = {c: "{:.1f}" for c in ["avg_grade", "avg_attendance",
                                 "avg_engagement", "avg_failed_conc"] if c in df.columns}
    st.dataframe(df.style.format(fmt), use_container_width=True)

    # Insights
    insight_card(
        f"The '{best['age_band']}' band performs best ({best['avg_grade']:.1f}% "
        f"avg grade); '{worst['age_band']}' trails at {worst['avg_grade']:.1f}%.",
        "finding")
    insight_card(
        "Age-band gaps are often confounded by life stage (work, family) rather "
        "than ability — read these alongside attendance before drawing conclusions.",
        "insight")
    insight_card(
        "If a band lags on attendance but not engagement, offer flexible / "
        "recorded sessions rather than remedial content.",
        "action")
