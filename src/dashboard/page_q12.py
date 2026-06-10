import streamlit as st
import plotly.graph_objects as go


def render(DATA, page_header, kpi_card, insight_card):
    page_header(
        "Q12 — Group Size Validation",
        "Do the stated headcounts match the real number of enrolled students?"
    )

    gm = DATA["group_metrics"]
    needed = {"stated_num_students", "true_count"}
    if gm is None or gm.empty or not needed.issubset(gm.columns):
        st.warning("No group-size data available in Atlas.")
        return

    df = gm.copy()
    if "discrepancy" not in df.columns:
        df["discrepancy"] = df["stated_num_students"] - df["true_count"]
    if "flag" not in df.columns:
        df["flag"] = df["discrepancy"].abs() > 3
    df = df.sort_values("discrepancy")

    flagged = df[df["flag"] == True]

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, len(df), "Groups Checked")
    kpi_card(c2, len(flagged), "Flagged Discrepancies",
             delta_up=False, delta="|Δ| > 3")
    kpi_card(c3, int(df["true_count"].min()), "Smallest Group",
             delta_up=False)
    kpi_card(c4, f"{df['discrepancy'].abs().max():+.0f}", "Largest |Δ|",
             delta_up=False)

    st.markdown("---")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["group_id"], y=df["stated_num_students"],
        name="Stated Count", marker_color="#455A64"))
    fig.add_trace(go.Bar(
        x=df["group_id"], y=df["true_count"],
        name="True Count", marker_color="#0D7377"))
    for _, row in flagged.iterrows():
        fig.add_annotation(
            x=row["group_id"],
            y=max(row["stated_num_students"], row["true_count"]) + 1.5,
            text=f"Δ{int(row['discrepancy']):+d}",
            showarrow=False, font=dict(color="#E53935", size=12))
    fig.update_layout(
        title="Stated vs True Group Size",
        xaxis_title="Group", yaxis_title="Student Count",
        barmode="group", template="plotly_dark", height=460,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.2),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Detail table
    st.subheader("Flagged Groups")
    if len(flagged):
        cols = [c for c in ["group_id", "group_name", "instructor",
                            "stated_num_students", "true_count", "discrepancy"]
                if c in flagged.columns]
        st.dataframe(flagged[cols], use_container_width=True)
    else:
        st.success("No groups exceed the discrepancy threshold.")

    # Insights
    flagged_ids = flagged["group_id"].tolist()
    insight_card(
        f"Groups {flagged_ids} have headcounts that do not match enrollment "
        "(|Δ| > 3). Stated numbers drive staffing and budgeting — these need "
        "reconciling.",
        "finding")
    insight_card(
        "The true count comes from students.csv (the source of truth); the stated "
        "count is what the group record claims. Drift usually means students moved "
        "groups without the roster being updated.",
        "insight")
    insight_card(
        "Reconcile flagged rosters this week and add a periodic automated check so "
        "stated vs true counts can't silently diverge again.",
        "action")
