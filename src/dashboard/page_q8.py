import streamlit as st
import plotly.express as px


def render(DATA, page_header, kpi_card, insight_card):
    page_header(
        "Q8 — Submission Behaviour",
        "How early or late do students actually submit their work?"
    )

    dd = DATA["delay_dist"]
    if dd is None or dd.empty:
        st.warning("No submission-delay data available in Atlas.")
        return

    # canonical ordering of the delay buckets
    order = ["2+ days early", "1-2 days early", "Same day early",
             "Up to 1 day late", "1-2 days late", "2+ days late"]
    df = dd.copy()
    df["delay_bucket"] = df["delay_bucket"].astype(str)
    df["__order"] = df["delay_bucket"].apply(
        lambda b: order.index(b) if b in order else len(order))
    df = df.sort_values("__order")

    total = df["count"].sum()
    late_mask = df["delay_bucket"].str.contains("late", case=False)
    late = df[late_mask]["count"].sum()
    early = total - late
    late_pct = (late / total * 100) if total else 0

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, f"{int(total):,}", "Total Submissions")
    kpi_card(c2, f"{late_pct:.1f}%", "Late Submissions",
             delta_up=False, delta="of all submissions")
    kpi_card(c3, f"{(early / total * 100) if total else 0:.1f}%",
             "On-time / Early", delta_up=True)
    worst_bucket = df.loc[df["count"].idxmax(), "delay_bucket"]
    kpi_card(c4, worst_bucket, "Most Common Pattern")

    st.markdown("---")

    colors = ["#E53935" if "late" in b.lower() else "#0D7377"
              for b in df["delay_bucket"]]
    fig = px.bar(
        df, x="delay_bucket", y="count",
        title="Submission Timing Distribution",
        labels={"delay_bucket": "Submission Timing", "count": "Submissions"},
        text="count", template="plotly_dark", height=460,
    )
    fig.update_traces(marker_color=colors, textposition="outside")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)",
                      xaxis_tickangle=-20)
    st.plotly_chart(fig, use_container_width=True)

    # Insights
    insight_card(
        f"{late_pct:.1f}% of submissions arrive late, with '{worst_bucket}' "
        "the single most common timing band.",
        "finding")
    insight_card(
        "Late submission is one of the earliest behavioural warning signs — it "
        "tends to appear before grades drop and feeds directly into the at-risk "
        "score (see Q14).",
        "insight")
    insight_card(
        "Send automated deadline reminders 48h and 24h out, and flag any student "
        "with a repeated late pattern for an instructor check-in.",
        "action")
