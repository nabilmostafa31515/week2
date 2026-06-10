import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.load_all import load_everything
from src.preprocessing.clean import clean_all
from src.analytics.model import build_model
from src.analytics.features import compute_all_features 

KAYFA_COLORS = {
    "primary":   "#0D7377",
    "secondary": "#14BDAC",
    "accent":    "#F6A623",
    "danger":    "#E53935",
    "success":   "#2E7D32",
    "neutral":   "#455A64",
    "bg":        "#0F1923",
    "card":      "#1A2535",
    "text":      "#E8EDF2",
}

TEMPLATE = "plotly_dark"

# ══════════════════════════════════════════════════════
#  Q1 — ATTENDANCE RATE PER GROUP
# ══════════════════════════════════════════════════════

def q1_attendance_per_group(group_att: pd.DataFrame) -> go.Figure:
    """
    Business Objective : Identify underperforming groups
    Metrics            : group_attendance_rate, platform_avg
    Visual             : Horizontal bar chart + threshold line
    """
    df = group_att.sort_values("group_attendance_rate")
    platform_avg = df["platform_avg_attendance"].iloc[0]

    colors = [
        KAYFA_COLORS["danger"] if b else KAYFA_COLORS["primary"]
        for b in df["below_platform_avg"]
    ]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["group_attendance_rate"],
        y=df["group_id"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:.1f}%" for v in df["group_attendance_rate"]],
        textposition="outside",
        name="Attendance Rate",
    ))

    fig.add_vline(
        x=platform_avg,
        line_dash="dash",
        line_color=KAYFA_COLORS["accent"],
        annotation_text=f"Platform avg: {platform_avg:.1f}%",
        annotation_position="top right",
    )

    fig.update_layout(
        title="Q1 — Attendance Rate per Group",
        xaxis_title="Attendance Rate (%)",
        yaxis_title="Group",
        template=TEMPLATE,
        height=450,
        xaxis=dict(range=[0, 110]),
        showlegend=False,
    )

    below = df[df["below_platform_avg"]]["group_id"].tolist()
    print(f"\n💡 Q1 Insight: Groups below platform average: {below}")
    print(f"   Platform average attendance: {platform_avg:.1f}%")

    return fig

# ══════════════════════════════════════════════════════
#  Q2 — SCORE DISTRIBUTION BY ASSESSMENT TYPE
# ══════════════════════════════════════════════════════

def q2_score_distribution_by_type(grades: pd.DataFrame) -> go.Figure:
    """
    Business Objective : Find which assessment type is most volatile
    Metrics            : score_pct distribution per type
    Visual             : Box plot (shows spread + outliers)
    """
    valid = grades[~grades["invalid_score"] & grades["score_pct"].notna()]

    fig = px.box(
        valid,
        x="type",
        y="score_pct",
        color="type",
        points="outliers",
        title="Q2 — Score Distribution by Assessment Type",
        labels={"score_pct": "Score (%)", "type": "Assessment Type"},
        color_discrete_sequence=[
            KAYFA_COLORS["primary"],
            KAYFA_COLORS["secondary"],
            KAYFA_COLORS["accent"],
            KAYFA_COLORS["danger"],
        ],
        template=TEMPLATE,
    )

    fig.update_layout(
        height=450,
        showlegend=False,
    )

    # find most volatile type
    std_by_type = valid.groupby("type")["score_pct"].std()
    most_volatile = std_by_type.idxmax()
    print(f"\n💡 Q2 Insight: Most volatile type = {most_volatile} "
          f"(std={std_by_type[most_volatile]:.1f}%)")

    return fig

# ══════════════════════════════════════════════════════
#  Q3 — COURSE GRADE COMPARISON
# ══════════════════════════════════════════════════════

def q3_course_grade_comparison(
    course_grades: pd.DataFrame,
    courses: pd.DataFrame
) -> go.Figure:
    """
    Business Objective : Find best and worst performing courses
    Metrics            : avg grade + grade spread per course
    Visual             : Bar + error bars (std)
    """
    df = course_grades.merge(
        courses[["course_id", "course_name"]], on="course_id"
    ).sort_values("course_avg_grade", ascending=False)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["course_name"],
        y=df["course_avg_grade"],
        error_y=dict(
            type="data",
            array=df["course_grade_std"],
            visible=True,
            color=KAYFA_COLORS["accent"],
        ),
        marker_color=[
            KAYFA_COLORS["success"] if i == 0
            else KAYFA_COLORS["danger"] if i == len(df) - 1
            else KAYFA_COLORS["primary"]
            for i in range(len(df))
        ],
        text=[f"{v:.1f}%" for v in df["course_avg_grade"]],
        textposition="outside",
    ))

    fig.update_layout(
        title="Q3 — Average Grade per Course (error bars = std deviation)",
        xaxis_title="Course",
        yaxis_title="Average Grade (%)",
        template=TEMPLATE,
        height=450,
        yaxis=dict(range=[0, 110]),
    )

    best  = df.iloc[0]
    worst = df.iloc[-1]
    print(f"\n💡 Q3 Insight: Best course  = {best['course_name']} "
          f"({best['course_avg_grade']:.1f}%)")
    print(f"   Worst course = {worst['course_name']} "
          f"({worst['course_avg_grade']:.1f}%)")

    return fig

# ══════════════════════════════════════════════════════
#  Q4 — ATTENDANCE vs GRADE
# ══════════════════════════════════════════════════════

def q4_attendance_vs_grade(student_summary: pd.DataFrame) -> go.Figure:
    """
    Business Objective : Quantify impact of attendance on grade
    Metrics            : attendance_rate vs avg_grade per student
    Visual             : Scatter + trendline
    """
    df = student_summary[
        student_summary["attendance_rate"].notna() &
        student_summary["avg_grade"].notna()
    ]

    corr = df["attendance_rate"].corr(df["avg_grade"])

    fig = px.scatter(
        df,
        x="attendance_rate",
        y="avg_grade",
        color="course_name",
        hover_data=["full_name", "group_name"],
        trendline="ols",
        trendline_scope="overall",
        title=f"Q4 — Attendance Rate vs Average Grade  (r = {corr:.2f})",
        labels={
            "attendance_rate": "Attendance Rate (%)",
            "avg_grade":       "Average Grade (%)",
        },
        template=TEMPLATE,
        height=500,
        opacity=0.7,
    )

    fig.update_traces(
        selector=dict(mode="lines"),
        line=dict(color=KAYFA_COLORS["accent"], width=2),
    )

    print(f"\n💡 Q4 Insight: Pearson correlation = {corr:.2f}")
    if corr > 0.5:
        print("   Strong positive link: higher attendance → higher grades")
    elif corr > 0.3:
        print("   Moderate positive link between attendance and grades")
    else:
        print("   Weak link — other factors dominate grade outcomes")

    return fig

# ══════════════════════════════════════════════════════
#  Q5 — ENGAGEMENT vs PERFORMANCE
# ══════════════════════════════════════════════════════

def q5_engagement_vs_performance(student_summary: pd.DataFrame) -> go.Figure:
    """
    Business Objective : Does more engagement mean better grades?
    Metrics            : engagement_score + total_watch_hours vs avg_grade
    Visual             : Scatter (bubble = watch time)
    """
    df = student_summary[
        student_summary["avg_grade"].notna() &
        student_summary["engagement_score"].notna()
    ]

    corr_eng   = df["engagement_score"].corr(df["avg_grade"])
    corr_watch = df["total_watch_hours"].corr(df["avg_grade"])

    fig = px.scatter(
        df,
        x="engagement_score",
        y="avg_grade",
        size="total_watch_hours",
        color="course_name",
        hover_data=["full_name", "login_count", "total_watch_hours"],
        trendline="ols",
        trendline_scope="overall",
        title=(f"Q5 — Engagement Score vs Grade  "
               f"(r_eng={corr_eng:.2f}, r_watch={corr_watch:.2f})"),
        labels={
            "engagement_score": "Engagement Score",
            "avg_grade":        "Average Grade (%)",
        },
        template=TEMPLATE,
        height=500,
        opacity=0.65,
        size_max=20,
    )

    print(f"\n💡 Q5 Insight: Engagement↔Grade correlation = {corr_eng:.2f}")
    print(f"   Watch time↔Grade correlation = {corr_watch:.2f}")

    return fig

# ══════════════════════════════════════════════════════
#  Q6 — CONCEPT FAILURE RATES
# ══════════════════════════════════════════════════════

def q6_concept_failure_rates(
    concept_fail: pd.DataFrame,
    courses: pd.DataFrame,
    top_n: int = 15
) -> go.Figure:
    """
    Business Objective : Find curriculum weak spots
    Metrics            : failure_rate per concept
    Visual             : Horizontal bar, coloured by course
    """
    df = concept_fail.head(top_n).merge(
        courses[["course_id", "course_name"]], on="course_id"
    )

    fig = px.bar(
        df,
        x="failure_rate",
        y="concept_name",
        color="course_name",
        orientation="h",
        title=f"Q6 — Top {top_n} Concepts by Failure Rate",
        labels={
            "failure_rate": "Failure Rate (%)",
            "concept_name": "Concept",
        },
        text=[f"{v:.1f}%" for v in df["failure_rate"]],
        template=TEMPLATE,
        height=520,
    )

    fig.update_traces(textposition="outside")
    fig.update_layout(yaxis=dict(autorange="reversed"))

    worst = concept_fail.iloc[0]
    print(f"\n💡 Q6 Insight: Biggest weak spot = '{worst['concept_name']}' "
          f"in course {worst['course_id']} "
          f"({worst['failure_rate']:.1f}% failure rate)")

    return fig

# ══════════════════════════════════════════════════════
#  Q7 — WORST CONCEPT TREND OVER TIME
# ══════════════════════════════════════════════════════

def q7_worst_concept_trend(
    concept_trend: pd.DataFrame,
    concept_fail: pd.DataFrame
) -> go.Figure:
    """
    Business Objective : Is the hardest concept getting better or worse?
    Metrics            : pass_rate of worst concept per month
    Visual             : Line chart with trend direction annotation
    """
    worst_id   = concept_fail.iloc[0]["concept_id"]
    worst_name = concept_fail.iloc[0]["concept_name"]

    df = concept_trend[
        concept_trend["concept_id"] == worst_id
    ].sort_values("month")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["month"],
        y=df["pass_rate"],
        mode="lines+markers",
        name="Pass Rate",
        line=dict(color=KAYFA_COLORS["primary"], width=2.5),
        marker=dict(size=8),
        fill="tozeroy",
        fillcolor="rgba(13,115,119,0.15)",
    ))

    fig.add_trace(go.Scatter(
        x=df["month"],
        y=df["avg_score"],
        mode="lines+markers",
        name="Avg Score",
        line=dict(color=KAYFA_COLORS["accent"], width=1.5, dash="dot"),
        marker=dict(size=6),
    ))

    fig.update_layout(
        title=f"Q7 — Mastery Trend: '{worst_name}'",
        xaxis_title="Month",
        yaxis_title="Rate / Score (%)",
        template=TEMPLATE,
        height=430,
    )

    # detect trend direction
    if len(df) >= 2:
        delta = df["pass_rate"].iloc[-1] - df["pass_rate"].iloc[0]
        direction = "improving ↑" if delta > 5 else \
                    "declining ↓" if delta < -5 else "flat →"
        print(f"\n💡 Q7 Insight: '{worst_name}' is {direction} "
              f"(Δ={delta:+.1f}% over the term)")

    return fig

# ══════════════════════════════════════════════════════
#  Q8 — LATE SUBMISSION vs SCORE
# ══════════════════════════════════════════════════════

def q8_late_submission_vs_score(
    submissions: pd.DataFrame,
    grades: pd.DataFrame
) -> go.Figure:
    """
    Business Objective : Do late submitters score lower?
    Metrics            : avg score for late vs on-time submissions
    Visual             : Box plot split by is_late + scatter delay vs score
    """
    valid_subs = submissions[submissions["submitted_at"].notna()]

    # join with grades on assessment_id + student_id
    df = valid_subs.merge(
        grades[["student_id","assessment_id","score_pct","invalid_score"]],
        on=["student_id","assessment_id"],
        how="inner"
    )
    df = df[~df["invalid_score"] & df["score_pct"].notna()]
    df["submission_status"] = df["is_late"].map(
        {True: "Late", False: "On Time", 1: "Late", 0: "On Time"}
    )

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=[
            "Score distribution: Late vs On Time",
            "Submission delay vs Score"
        ],
    )

    for status, color in [
        ("On Time", KAYFA_COLORS["success"]),
        ("Late",    KAYFA_COLORS["danger"]),
    ]:
        sub = df[df["submission_status"] == status]
        fig.add_trace(go.Box(
            y=sub["score_pct"],
            name=status,
            marker_color=color,
            boxmean=True,
        ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df["submission_delay_hours"],
        y=df["score_pct"],
        mode="markers",
        marker=dict(
            color=df["is_late"].map({True: KAYFA_COLORS["danger"],
                                     False: KAYFA_COLORS["success"],
                                     1: KAYFA_COLORS["danger"],
                                     0: KAYFA_COLORS["success"]}),
            size=5, opacity=0.5,
        ),
        name="Student",
        showlegend=False,
    ), row=1, col=2)

    fig.update_layout(
        title="Q8 — Late Submission Effect on Score",
        template=TEMPLATE,
        height=450,
    )

    late_avg    = df[df["is_late"] == True]["score_pct"].mean()
    on_time_avg = df[df["is_late"] == False]["score_pct"].mean()
    print(f"\n💡 Q8 Insight: On-time avg = {on_time_avg:.1f}% | "
          f"Late avg = {late_avg:.1f}% | "
          f"Penalty ≈ {on_time_avg - late_avg:.1f}%")

    return fig

# ══════════════════════════════════════════════════════
#  Q9 — COHORT TRENDS OVER TIME
# ══════════════════════════════════════════════════════

def q9_cohort_trends(
    monthly_att: pd.DataFrame,
    monthly_eng: pd.DataFrame
) -> go.Figure:
    """
    Business Objective : Find cohort-wide dip windows
    Metrics            : monthly attendance + engagement trend
    Visual             : Dual-axis line chart
    """
    att_monthly = monthly_att.groupby("month")["monthly_att_rate"].mean().reset_index()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(
        x=att_monthly["month"],
        y=att_monthly["monthly_att_rate"],
        name="Attendance Rate (%)",
        mode="lines+markers",
        line=dict(color=KAYFA_COLORS["primary"], width=2.5),
        marker=dict(size=8),
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=monthly_eng["month"],
        y=monthly_eng["total_events"],
        name="Total Engagement Events",
        mode="lines+markers",
        line=dict(color=KAYFA_COLORS["accent"], width=2, dash="dot"),
        marker=dict(size=7),
    ), secondary_y=True)

    fig.update_layout(
        title="Q9 — Attendance & Engagement Trends Over 6 Months",
        template=TEMPLATE,
        height=450,
    )
    fig.update_yaxes(title_text="Attendance Rate (%)", secondary_y=False)
    fig.update_yaxes(title_text="Engagement Events",   secondary_y=True)

    # find the dip month
    dip_month = att_monthly.loc[
        att_monthly["monthly_att_rate"].idxmin(), "month"
    ]
    print(f"\n💡 Q9 Insight: Lowest attendance month = {dip_month}")
    print("   Possible cause: exam period, public holiday, or mid-term burnout")

    return fig

# ══════════════════════════════════════════════════════
#  Q10 — AGE BAND ANALYSIS
# ══════════════════════════════════════════════════════

def q10_age_band_analysis(age_stats: pd.DataFrame) -> go.Figure:
    """
    Business Objective : Does age relate to outcomes?
    Metrics            : grade, attendance, engagement per age band
    Visual             : Grouped bar chart
    """
    fig = go.Figure()

    metrics = {
        "avg_grade":      ("Avg Grade (%)",      KAYFA_COLORS["primary"]),
        "avg_attendance": ("Avg Attendance (%)", KAYFA_COLORS["secondary"]),
        "avg_engagement": ("Avg Engagement",     KAYFA_COLORS["accent"]),
    }

    for col, (label, color) in metrics.items():
        fig.add_trace(go.Bar(
            x=age_stats["age_band"].astype(str),
            y=age_stats[col],
            name=label,
            marker_color=color,
        ))

    fig.update_layout(
        title="Q10 — Grade, Attendance & Engagement by Age Band",
        xaxis_title="Age Band",
        yaxis_title="Value",
        barmode="group",
        template=TEMPLATE,
        height=450,
    )

    best_age = age_stats.loc[age_stats["avg_grade"].idxmax(), "age_band"]
    print(f"\n💡 Q10 Insight: Best performing age band = {best_age}")

    return fig

# ══════════════════════════════════════════════════════
#  Q11 — STUDENT SEGMENTATION
#  (will be built properly in Phase 8 - Clustering)
#  here we just plot the cluster results
# ══════════════════════════════════════════════════════

def q11_plot_clusters(student_summary_with_clusters: pd.DataFrame) -> go.Figure:
    """
    Business Objective : Segment students for targeted intervention
    Metrics            : cluster assignments
    Visual             : Scatter (attendance vs grade, coloured by cluster)
    """
    fig = px.scatter(
        student_summary_with_clusters,
        x="attendance_rate",
        y="avg_grade",
        color="cluster_label",
        size="engagement_score",
        hover_data=["full_name", "failed_concepts"],
        title="Q11 — Student Segmentation",
        labels={
            "attendance_rate": "Attendance Rate (%)",
            "avg_grade":       "Average Grade (%)",
            "cluster_label":   "Segment",
        },
        template=TEMPLATE,
        height=500,
        opacity=0.75,
        size_max=18,
    )

    return fig

# ══════════════════════════════════════════════════════
#  Q12 — GROUP SIZE VALIDATION
# ══════════════════════════════════════════════════════

def q12_group_size_validation(group_size: pd.DataFrame) -> go.Figure:
    """
    Business Objective : Catch groups with wrong headcounts
    Metrics            : stated vs true student count per group
    Visual             : Grouped bar + discrepancy annotation
    """
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=group_size["group_id"],
        y=group_size["stated_num_students"],
        name="Stated Count",
        marker_color=KAYFA_COLORS["neutral"],
    ))

    fig.add_trace(go.Bar(
        x=group_size["group_id"],
        y=group_size["true_count"],
        name="True Count",
        marker_color=KAYFA_COLORS["primary"],
    ))

    # annotate discrepancies
    for _, row in group_size[group_size["flag"]].iterrows():
        fig.add_annotation(
            x=row["group_id"],
            y=max(row["stated_num_students"], row["true_count"]) + 1.5,
            text=f"Δ{row['discrepancy']:+d}",
            showarrow=False,
            font=dict(color=KAYFA_COLORS["danger"], size=11),
        )

    fig.update_layout(
        title="Q12 — Stated vs True Group Size",
        xaxis_title="Group",
        yaxis_title="Student Count",
        barmode="group",
        template=TEMPLATE,
        height=450,
    )

    flagged = group_size[group_size["flag"]]["group_id"].tolist()
    print(f"\n💡 Q12 Insight: Groups flagged for investigation: {flagged}")

    return fig

# ══════════════════════════════════════════════════════
#  Q13 — TINY GROUP MERGE RECOMMENDATION
# ══════════════════════════════════════════════════════

def q13_merge_recommendation(
    student_summary: pd.DataFrame,
    group_size: pd.DataFrame,
    student_concepts: pd.DataFrame
) -> go.Figure:
    """
    Business Objective : Should the tiny group be merged?
    Metrics            : concept profile similarity
    Visual             : Radar chart comparing tiny group vs best match
    """
    # identify tiny group (smallest true count)
    tiny_group_id = group_size.loc[
        group_size["true_count"].idxmin(), "group_id"
    ]
    tiny_group_name = group_size.loc[
        group_size["true_count"].idxmin(), "group_name"
    ]

    # get students in tiny group
    tiny_students = student_summary[
        student_summary["group_id"] == tiny_group_id
    ]["student_id"].tolist()

    # compare group avg metrics
    metrics = ["avg_grade", "attendance_rate",
               "engagement_score", "failed_concepts",
               "concept_pass_rate"]

    group_profiles = student_summary[
        student_summary[metrics].notna().all(axis=1)
    ].groupby("group_id")[metrics].mean().reset_index()

    # find most similar group using euclidean distance
    tiny_profile = group_profiles[
        group_profiles["group_id"] == tiny_group_id
    ][metrics].values

    if len(tiny_profile) == 0:
        print(f"\n⚠️  Q13: No valid profile for {tiny_group_id}")
        return go.Figure()

    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import pairwise_distances

    other_groups = group_profiles[
        group_profiles["group_id"] != tiny_group_id
    ]
    scaler = StandardScaler()
    all_profiles = scaler.fit_transform(
        group_profiles[metrics].fillna(0)
    )
    tiny_idx  = group_profiles[
        group_profiles["group_id"] == tiny_group_id
    ].index[0]
    dists = pairwise_distances(
        all_profiles[tiny_idx].reshape(1, -1),
        all_profiles
    )[0]
    group_profiles["distance"] = dists
    best_match = group_profiles[
        group_profiles["group_id"] != tiny_group_id
    ].sort_values("distance").iloc[0]

    best_match_id   = best_match["group_id"]
    best_match_name = student_summary[
        student_summary["group_id"] == best_match_id
    ]["group_name"].iloc[0]

    # radar chart
    categories = ["Grade", "Attendance",
                  "Engagement", "Concepts Failed", "Concept Pass Rate"]

    fig = go.Figure()

    for gid, gname, color in [
        (tiny_group_id,  tiny_group_name,  KAYFA_COLORS["danger"]),
        (best_match_id,  best_match_name,  KAYFA_COLORS["primary"]),
    ]:
        profile = group_profiles[
            group_profiles["group_id"] == gid
        ][metrics].values[0]

        fig.add_trace(go.Scatterpolar(
            r=profile,
            theta=categories,
            fill="toself",
            name=f"{gid} — {gname}",
            line=dict(color=color),
            opacity=0.7,
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        title=(f"Q13 — Merge Recommendation: {tiny_group_id} "
               f"→ closest match: {best_match_id}"),
        template=TEMPLATE,
        height=480,
    )

    print(f"\n💡 Q13 Insight: Tiny group = {tiny_group_id} ({tiny_group_name})")
    print(f"   Closest match = {best_match_id} ({best_match_name})")
    print(f"   Recommendation: Merge {tiny_group_id} into {best_match_id}")

    return fig

# ══════════════════════════════════════════════════════
#  Q14 — AT-RISK RANKING
# ══════════════════════════════════════════════════════

def q14_at_risk_ranking(risk_df: pd.DataFrame) -> go.Figure:
    """
    Business Objective : Surface top 10 students needing intervention
    Metrics            : at_risk_score (composite)
    Visual             : Horizontal stacked bar showing each risk component
    """
    top10 = risk_df.head(10).copy()
    top10["display_name"] = top10["full_name"] + " (" + top10["group_name"] + ")"

    fig = go.Figure()

    components = {
        "risk_grade":      ("Grade Risk",      KAYFA_COLORS["danger"]),
        "risk_attendance": ("Attendance Risk", KAYFA_COLORS["accent"]),
        "risk_engagement": ("Engagement Risk", KAYFA_COLORS["neutral"]),
        "risk_concepts":   ("Concept Risk",    KAYFA_COLORS["secondary"]),
    }

    for col, (label, color) in components.items():
        fig.add_trace(go.Bar(
            y=top10["display_name"],
            x=top10[col],
            name=label,
            orientation="h",
            marker_color=color,
        ))

    fig.update_layout(
        title="Q14 — Top 10 At-Risk Students (composite risk score)",
        xaxis_title="Risk Component Score",
        yaxis_title="Student",
        barmode="stack",
        template=TEMPLATE,
        height=480,
        yaxis=dict(autorange="reversed"),
    )

    print(f"\n💡 Q14 Insight: Top at-risk student = "
          f"{top10.iloc[0]['full_name']} "
          f"(score={top10.iloc[0]['at_risk_score']:.3f})")
    print("   Action: Contact top 10 immediately for academic support")

    return fig

# ══════════════════════════════════════════════════════
#  Q15 — GROUP GRADE TRENDS
# ══════════════════════════════════════════════════════

def q15_group_grade_trends(
    grade_trend: pd.DataFrame,
    groups: pd.DataFrame
) -> go.Figure:
    """
    Business Objective : Which groups are improving vs sliding?
    Metrics            : avg grade per group across assessments over time
    Visual             : Multi-line chart (one line per group)
    """
    df = grade_trend.merge(
        groups[["group_id","group_name"]], on="group_id", how="left"
    ).sort_values(["group_id","assessment_id"])

    fig = px.line(
        df,
        x="assessment_id",
        y="avg_score",
        color="group_name",
        markers=True,
        title="Q15 — Group Grade Trends Across Assessments",
        labels={
            "avg_score":     "Average Score (%)",
            "assessment_id": "Assessment",
            "group_name":    "Group",
        },
        template=TEMPLATE,
        height=500,
    )

    fig.update_layout(
        xaxis=dict(tickangle=-45),
        legend=dict(orientation="h", y=-0.25),
    )

    # find trending up vs down
    trends = {}
    for gid, gdf in df.groupby("group_id"):
        gdf = gdf.sort_values("assessment_id")
        if len(gdf) >= 2:
            delta = gdf["avg_score"].iloc[-1] - gdf["avg_score"].iloc[0]
            trends[gid] = delta

    improving = [g for g, d in trends.items() if d > 3]
    declining = [g for g, d in trends.items() if d < -3]
    print(f"\n💡 Q15 Insight: Improving groups = {improving}")
    print(f"   Declining groups = {declining}")

    return fig

# ══════════════════════════════════════════════════════
#  RUN ALL QUESTIONS
# ══════════════════════════════════════════════════════

def answer_all_questions(model: dict, features: dict) -> dict:
    print("\n" + "=" * 55)
    print("  KAYFA — Answering all 15 questions")
    print("=" * 55)

    figures = {}

    figures["q1"]  = q1_attendance_per_group(features["group_att"])
    figures["q2"]  = q2_score_distribution_by_type(model["grades"])
    figures["q3"]  = q3_course_grade_comparison(
                         features["course_grades"], model["courses"])
    figures["q4"]  = q4_attendance_vs_grade(model["student_summary"])
    figures["q5"]  = q5_engagement_vs_performance(model["student_summary"])
    figures["q6"]  = q6_concept_failure_rates(
                         features["concept_fail"], model["courses"])
    figures["q7"]  = q7_worst_concept_trend(
                         features["concept_trend"], features["concept_fail"])
    figures["q8"]  = q8_late_submission_vs_score(
                         model["submissions"], model["grades"])
    figures["q9"]  = q9_cohort_trends(
                         features["monthly_att"], features["monthly_eng"])
    figures["q10"] = q10_age_band_analysis(features["age_stats"])
    # q11 needs clustering — will be filled in Phase 8
    figures["q12"] = q12_group_size_validation(features["group_size"])
    figures["q13"] = q13_merge_recommendation(
                         model["student_summary"],
                         features["group_size"],
                         features["student_concepts"])
    figures["q14"] = q14_at_risk_ranking(features["risk_df"])
    figures["q15"] = q15_group_grade_trends(
                         features["grade_trend"], model["groups"])

    print("\n" + "=" * 55)
    print(f"  ✅ {len(figures)} figures generated")
    print("=" * 55)

    return figures


if __name__ == "__main__":
    dfs      = load_everything()
    cleaned  = clean_all(dfs)
    model    = build_model(cleaned)
    features = compute_all_features(model)
    figures  = answer_all_questions(model, features)

    # preview first figure
    figures["q1"].show()