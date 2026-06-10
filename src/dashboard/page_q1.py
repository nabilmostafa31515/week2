import streamlit as st
import plotly.graph_objects as go

def render(DATA, page_header, kpi_card, insight_card):
    page_header(
        "Q1 — Attendance Rate per Group",
        "Which groups sit well below the platform average?"
    )

    gm = DATA["group_metrics"]
    if gm is None or gm.empty or "group_attendance_rate" not in gm.columns:
        st.warning(
            "📭 No group data in Atlas yet. Run the pipeline first: "
            "`python -m src.mongodb.write_analytics`"
        )
        return

    platform_avg = gm["group_attendance_rate"].mean()
    below        = gm[gm["below_platform_avg"] == True]

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, f"{platform_avg:.1f}%",  "Platform Avg Attendance")
    kpi_card(c2, len(below),              "Groups Below Average",
             delta_up=False, delta="Needs review")
    kpi_card(c3, f"{gm['group_attendance_rate'].max():.1f}%",
             "Best Group Attendance")
    kpi_card(c4, f"{gm['group_attendance_rate'].min():.1f}%",
             "Worst Group Attendance", delta_up=False)

    st.markdown("---")

    # Chart
    df = gm.sort_values("group_attendance_rate")
    colors = ["#E53935" if b else "#0D7377"
              for b in df["below_platform_avg"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["group_attendance_rate"],
        y=df["group_id"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:.1f}%" for v in df["group_attendance_rate"]],
        textposition="outside",
    ))
    fig.add_vline(
        x=platform_avg,
        line_dash="dash",
        line_color="#F6A623",
        annotation_text=f"Platform avg: {platform_avg:.1f}%",
    )
    fig.update_layout(
        template="plotly_dark",
        height=480,
        xaxis=dict(range=[0, 110], title="Attendance Rate (%)"),
        yaxis_title="Group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Table
    st.subheader("Groups Below Platform Average")
    if len(below):
        st.dataframe(
            below[["group_id","group_name","group_attendance_rate",
                   "instructor","true_count"]].style.format(
                {"group_attendance_rate": "{:.1f}%"}
            ),
            use_container_width=True,
        )

    # Insights
    below_list = below["group_id"].tolist()
    insight_card(
        f"Groups {below_list} are below the platform average of "
        f"{platform_avg:.1f}%. These groups have a pattern of low "
        "attendance that directly risks academic outcomes.",
        "finding"
    )
    insight_card(
        "Attendance and grade are strongly correlated (see Q4). "
        "Every 10% drop in attendance typically corresponds to a "
        "5-7% drop in average grade.",
        "insight"
    )
    insight_card(
        "Schedule makeup sessions for below-average groups. "
        "Send weekly attendance alerts to their instructors. "
        "Consider changing session day/time for persistently low groups.",
        "action"
    )