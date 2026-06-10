import streamlit as st
import numpy as np
import plotly.graph_objects as go


def render(DATA, page_header, kpi_card, insight_card):
    page_header(
        "Q13 — Group Merge Recommendation",
        "Which group should the smallest cohort be merged into?"
    )

    gm = DATA["group_metrics"]
    if gm is None or gm.empty or "true_count" not in gm.columns:
        st.warning("No group-metrics data available in Atlas.")
        return

    # profile metrics available on the group_metrics collection
    metric_map = {
        "avg_grade":             "Grade",
        "group_attendance_rate": "Attendance",
        "avg_engagement":        "Engagement",
        "avg_failed_concepts":   "Failed Concepts",
    }
    metrics = [m for m in metric_map if m in gm.columns]
    if len(metrics) < 2:
        st.warning("Not enough profile metrics to compute similarity.")
        return

    prof = gm.dropna(subset=metrics).copy()
    if len(prof) < 2:
        st.warning("Not enough complete group profiles to compare.")
        return

    name_col = "group_name" if "group_name" in prof.columns else "group_id"

    # smallest viable cohort
    tiny = prof.loc[prof["true_count"].idxmin()]
    tiny_id = tiny["group_id"]

    # standardise then euclidean distance to every other group
    X = prof[metrics].to_numpy(dtype=float)
    mu, sigma = X.mean(axis=0), X.std(axis=0)
    sigma[sigma == 0] = 1.0
    Xz = (X - mu) / sigma
    tiny_pos = prof.index.get_loc(tiny.name)
    dists = np.linalg.norm(Xz - Xz[tiny_pos], axis=1)
    prof = prof.assign(distance=dists)

    best = prof[prof["group_id"] != tiny_id].sort_values("distance").iloc[0]

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, str(tiny_id), "Smallest Group",
             delta_up=False, delta=f"{int(tiny['true_count'])} students")
    kpi_card(c2, str(best["group_id"]), "Closest Match",
             delta=f"dist = {best['distance']:.2f}")
    kpi_card(c3, int(tiny["true_count"] + best["true_count"]),
             "Combined Size", delta_up=True)
    kpi_card(c4, f"{tiny.get('avg_grade', float('nan')):.1f}%", "Smallest Grp Grade")

    st.markdown("---")

    # radar comparing the two group profiles
    categories = [metric_map[m] for m in metrics]
    fig = go.Figure()
    for row, color in [(tiny, "#E53935"), (best, "#0D7377")]:
        vals = [float(row[m]) for m in metrics]
        vals += [vals[0]]
        fig.add_trace(go.Scatterpolar(
            r=vals, theta=categories + [categories[0]],
            fill="toself",
            name=f"{row['group_id']} — {row.get(name_col, '')}",
            line=dict(color=color), opacity=0.65,
        ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        title=f"Profile Match: {tiny_id} → {best['group_id']}",
        template="plotly_dark", height=500,
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.15),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Insights
    insight_card(
        f"Group {tiny_id} has only {int(tiny['true_count'])} students — too small "
        "to be a viable standalone cohort.",
        "finding")
    insight_card(
        f"Across {', '.join(categories).lower()}, Group {best['group_id']} "
        f"({best.get(name_col, '')}) is the closest profile match "
        f"(distance = {best['distance']:.2f}). A merge keeps cohort dynamics intact.",
        "insight")
    insight_card(
        f"Recommend merging {tiny_id} into {best['group_id']}, combining them into "
        f"a {int(tiny['true_count'] + best['true_count'])}-student group. Notify "
        "both instructors and align session times before the move.",
        "solution")
