import streamlit as st
import plotly.graph_objects as go


def render(DATA, page_header, kpi_card, insight_card):
    page_header(
        "Q2 — Score Distribution by Assessment Type",
        "Which assessment type is the most volatile / hardest?"
    )

    td = DATA["type_dist"]
    if td is None or td.empty:
        st.warning("No assessment-type data available in Atlas.")
        return

    df = td.sort_values("avg_score", ascending=False).reset_index(drop=True)

    most_volatile = df.loc[df["std_score"].idxmax(), "type"]
    hardest       = df.loc[df["avg_score"].idxmin(), "type"]

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, str(most_volatile).title(),       "Most Volatile Type",
             delta_up=False, delta=f"σ = {df['std_score'].max():.1f}%")
    kpi_card(c2, str(hardest).title(),             "Hardest Type",
             delta_up=False, delta=f"{df['avg_score'].min():.1f}% avg")
    kpi_card(c3, f"{df['avg_score'].mean():.1f}%",  "Mean Score (all types)")
    kpi_card(c4, f"{int(df['count'].sum()):,}",     "Total Graded Items")

    st.markdown("---")

    # Bar chart with std-deviation error bars + min/max range
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["type"].astype(str).str.title(),
        y=df["avg_score"],
        error_y=dict(type="data", array=df["std_score"],
                     visible=True, color="#F6A623"),
        marker_color="#0D7377",
        text=[f"{v:.1f}%" for v in df["avg_score"]],
        textposition="outside",
        name="Average Score",
    ))
    fig.add_trace(go.Scatter(
        x=df["type"].astype(str).str.title(),
        y=df["min_score"],
        mode="markers", name="Min", marker=dict(color="#E53935", size=9, symbol="triangle-down"),
    ))
    fig.add_trace(go.Scatter(
        x=df["type"].astype(str).str.title(),
        y=df["max_score"],
        mode="markers", name="Max", marker=dict(color="#2E7D32", size=9, symbol="triangle-up"),
    ))
    fig.update_layout(
        template="plotly_dark",
        height=460,
        yaxis=dict(range=[0, 110], title="Score (%)"),
        xaxis_title="Assessment Type",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.2),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Detail table
    st.subheader("Per-Type Statistics")
    st.dataframe(
        df[["type", "avg_score", "std_score", "min_score", "max_score", "count"]]
        .style.format({
            "avg_score": "{:.1f}%", "std_score": "{:.1f}%",
            "min_score": "{:.1f}%", "max_score": "{:.1f}%",
        }),
        use_container_width=True,
    )

    # Insights
    insight_card(
        f"'{str(most_volatile).title()}' assessments have the widest score spread "
        f"(σ = {df['std_score'].max():.1f}%). High volatility means inconsistent "
        "preparation or unclear grading — worth standardising.",
        "finding"
    )
    insight_card(
        f"'{str(hardest).title()}' has the lowest average ({df['avg_score'].min():.1f}%). "
        "A low mean across an entire assessment type usually points to a "
        "curriculum or difficulty-calibration gap, not individual students.",
        "insight"
    )
    insight_card(
        "Review rubrics for the most volatile type and add worked examples / "
        "practice rounds for the hardest type before it is graded.",
        "action"
    )
