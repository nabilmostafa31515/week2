import streamlit as st
import plotly.express as px


def render(DATA, page_header, kpi_card, insight_card):
    page_header(
        "Q6 — Concept Failure Rates",
        "Where are the curriculum's weakest spots?"
    )

    cf = DATA["concept_failures"]
    if cf is None or cf.empty:
        st.warning("No concept-failure data available in Atlas.")
        return

    cf = cf.sort_values("failure_rate", ascending=False).reset_index(drop=True)

    # optional course names
    cm = DATA.get("course_metrics")
    color_col = "course_id"
    if cm is not None and not cm.empty and "course_name" in cm.columns:
        cf = cf.merge(cm[["course_id", "course_name"]], on="course_id", how="left")
        color_col = "course_name"

    top_n = st.slider("Show top N concepts", 5, min(30, len(cf)), min(15, len(cf)))
    df = cf.head(top_n)

    worst = cf.iloc[0]

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, worst["concept_name"], "Hardest Concept",
             delta_up=False, delta=f"{worst['failure_rate']:.1f}% fail")
    kpi_card(c2, f"{cf['failure_rate'].mean():.1f}%", "Avg Failure Rate")
    kpi_card(c3, int((cf["failure_rate"] >= 50).sum()), "Concepts ≥ 50% Fail",
             delta_up=False)
    kpi_card(c4, len(cf), "Concepts Tracked")

    st.markdown("---")

    fig = px.bar(
        df, x="failure_rate", y="concept_name",
        color=color_col, orientation="h",
        title=f"Top {top_n} Concepts by Failure Rate",
        labels={"failure_rate": "Failure Rate (%)", "concept_name": "Concept"},
        text=[f"{v:.1f}%" for v in df["failure_rate"]],
        template="plotly_dark", height=max(420, top_n * 30),
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(yaxis=dict(autorange="reversed"),
                      paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    # Detail table
    st.subheader("Concept Detail")
    cols = [c for c in ["concept_name", color_col, "failure_rate",
                        "failed_count", "total_attempts", "avg_score"]
            if c in cf.columns]
    st.dataframe(
        cf.head(top_n)[cols].style.format(
            {"failure_rate": "{:.1f}%", "avg_score": "{:.1f}%"}),
        use_container_width=True,
    )

    # Insights
    insight_card(
        f"'{worst['concept_name']}' is the single biggest weak spot at "
        f"{worst['failure_rate']:.1f}% failure rate across "
        f"{int(worst['total_attempts'])} attempts.",
        "finding")
    insight_card(
        "Concepts clustered in the same course point to a sequencing problem — "
        "an earlier prerequisite was never mastered, so everything downstream fails.",
        "insight")
    insight_card(
        "Build targeted remediation modules for the top 5 concepts and place a "
        "mastery checkpoint before students advance past them.",
        "action")
