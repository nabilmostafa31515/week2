import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from pathlib import Path
from src.extraction.load_all import load_everything
from src.preprocessing.clean import clean_all
from src.analytics.model import build_model
from src.analytics.features import compute_all_features

KAYFA_COLORS = {
    "primary":   "#25189E",
    "secondary": "#25189E",
    "accent":    "#25189E",
    "danger":    "#25189E",
    "success":   "#25189E",
    "neutral":   "#25189E",
    "purple":    "#25189E",
}

TEMPLATE = "plotly_dark"

# ══════════════════════════════════════════════════════
#  STEP 1 — PREPARE CLUSTERING FEATURES
# ══════════════════════════════════════════════════════

def prepare_cluster_features(student_summary: pd.DataFrame) -> tuple:
    print("\n── Step 1: Preparing clustering features ──")

    CLUSTER_FEATURES = [
        "attendance_rate",
        "avg_grade",
        "engagement_score",
        "failed_concepts",
    ]

    # keep only students with all 4 features present
    df = student_summary[
        student_summary[CLUSTER_FEATURES].notna().all(axis=1)
    ].copy()

    print(f"   Students with complete features: {len(df)}")
    print(f"   Features used: {CLUSTER_FEATURES}")

    # show feature stats before scaling
    print("\n   Feature statistics:")
    print(df[CLUSTER_FEATURES].describe().round(2).to_string())

    # scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df[CLUSTER_FEATURES])

    return df, X_scaled, scaler, CLUSTER_FEATURES

# ══════════════════════════════════════════════════════
#  STEP 2 — FIND OPTIMAL K (ELBOW + SILHOUETTE)
# ══════════════════════════════════════════════════════

def find_optimal_k(X_scaled: np.ndarray) -> go.Figure:
    print("\n── Step 2: Finding optimal K ──")

    k_range    = range(2, 9)
    inertias   = []
    silhouettes = []

    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X_scaled)
        inertias.append(km.inertia_)
        silhouettes.append(silhouette_score(X_scaled, labels))
        print(f"   k={k} | inertia={km.inertia_:.1f} | "
              f"silhouette={silhouette_score(X_scaled, labels):.3f}")

    # best k by silhouette
    best_k = list(k_range)[np.argmax(silhouettes)]
    print(f"\n   ✅ Best K by silhouette = {best_k}")

    # plot elbow + silhouette
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=["Elbow Method (Inertia)", "Silhouette Score"]
    )

    fig.add_trace(go.Scatter(
        x=list(k_range), y=inertias,
        mode="lines+markers",
        name="Inertia",
        line=dict(color=KAYFA_COLORS["primary"], width=2.5),
        marker=dict(size=8),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=list(k_range), y=silhouettes,
        mode="lines+markers",
        name="Silhouette",
        line=dict(color=KAYFA_COLORS["accent"], width=2.5),
        marker=dict(size=8),
    ), row=1, col=2)

    # mark best k
    fig.add_vline(
        x=best_k,
        line_dash="dash",
        line_color=KAYFA_COLORS["danger"],
        annotation_text=f"Best K={best_k}",
        row=1, col=2,
    )

    fig.update_layout(
        title="Step 2 — Optimal K Selection",
        template=TEMPLATE,
        height=400,
        showlegend=False,
    )

    return fig, best_k

# ══════════════════════════════════════════════════════
#  STEP 3 — FIT KMEANS WITH BEST K
# ══════════════════════════════════════════════════════

def fit_kmeans(
    df: pd.DataFrame,
    X_scaled: np.ndarray,
    k: int
) -> pd.DataFrame:
    print(f"\n── Step 3: Fitting K-Means (k={k}) ──")

    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    df = df.copy()
    df["cluster"] = km.fit_predict(X_scaled)

    # cluster sizes
    sizes = df["cluster"].value_counts().sort_index()
    print(f"\n   Cluster sizes:")
    for c, n in sizes.items():
        print(f"   Cluster {c}: {n} students")

    return df, km

# ══════════════════════════════════════════════════════
#  STEP 4 — DESCRIBE CLUSTERS
# ══════════════════════════════════════════════════════

CLUSTER_LABELS = {
    # will be filled dynamically based on centroid analysis
}

SEGMENT_DESCRIPTIONS = {
    "High Achievers": {
        "label":       "🏆 High Achievers",
        "color":       KAYFA_COLORS["success"],
        "description": (
            "High attendance, high grades, high engagement, "
            "low failed concepts. These students are on track."
        ),
        "action": (
            "Offer advanced challenges, peer-mentoring roles, "
            "and fast-track opportunities."
        ),
    },
    "At Risk": {
        "label":       "🚨 At Risk",
        "color":       KAYFA_COLORS["danger"],
        "description": (
            "Low attendance, low grades, low engagement, "
            "many failed concepts. Needs urgent intervention."
        ),
        "action": (
            "Immediate instructor outreach, attendance check, "
            "remedial concept sessions."
        ),
    },
    "Passive Learners": {
        "label":       "😴 Passive Learners",
        "color":       KAYFA_COLORS["accent"],
        "description": (
            "Average attendance and grades, but low engagement. "
            "Present but not active."
        ),
        "action": (
            "Encourage forum participation, project-based tasks, "
            "and peer learning."
        ),
    },
    "Engaged Strugglers": {
        "label":       "💪 Engaged Strugglers",
        "color":       KAYFA_COLORS["secondary"],
        "description": (
            "High engagement but low grades. Working hard "
            "but may lack foundations."
        ),
        "action": (
            "Targeted concept reinforcement, study skills coaching, "
            "extra office hours."
        ),
    },
}

def describe_clusters(
    df: pd.DataFrame,
    features: list,
    k: int
) -> pd.DataFrame:
    print(f"\n── Step 4: Describing clusters ──")

    # de-duplicate: `features` already includes the 4 core metrics, so adding
    # them again would create duplicate columns (a Series per label → ambiguous
    # truth-value errors below). dict.fromkeys preserves order while deduping.
    summary_cols = list(dict.fromkeys(features + [
        "attendance_rate", "avg_grade",
        "engagement_score", "failed_concepts",
        "late_submission_rate", "concept_pass_rate"
    ]))
    cluster_summary = df.groupby("cluster")[summary_cols].mean().round(2)

    print("\n   Cluster centroids:")
    print(cluster_summary.to_string())

    # auto-label clusters based on centroid values
    labels = {}
    for c in range(k):
        row = cluster_summary.loc[c]
        grade      = row["avg_grade"]
        attendance = row["attendance_rate"]
        engagement = row["engagement_score"]
        failed     = row["failed_concepts"]

        if grade >= 70 and attendance >= 70:
            labels[c] = "High Achievers"
        elif grade < 55 and attendance < 60:
            labels[c] = "At Risk"
        elif engagement < cluster_summary["engagement_score"].median() and grade >= 55:
            labels[c] = "Passive Learners"
        else:
            labels[c] = "Engaged Strugglers"

    df["cluster_label"] = df["cluster"].map(labels)

    # print segment summary
    print("\n   Segment assignment:")
    for c, label in labels.items():
        n = (df["cluster"] == c).sum()
        desc = SEGMENT_DESCRIPTIONS.get(label, {})
        print(f"\n   Cluster {c} → {label} ({n} students)")
        print(f"   {desc.get('description','')}")
        print(f"   Action: {desc.get('action','')}")

    return df, cluster_summary, labels

# ══════════════════════════════════════════════════════
#  STEP 5 — VISUALISE CLUSTERS
# ══════════════════════════════════════════════════════

def visualise_clusters(
    df: pd.DataFrame,
    X_scaled: np.ndarray,
    cluster_summary: pd.DataFrame,
) -> dict:
    print("\n── Step 5: Generating cluster visualisations ──")

    SEGMENT_COLORS = {
        "High Achievers":    KAYFA_COLORS["success"],
        "At Risk":           KAYFA_COLORS["danger"],
        "Passive Learners":  KAYFA_COLORS["accent"],
        "Engaged Strugglers":KAYFA_COLORS["secondary"],
    }

    figs = {}

    # ── Fig 1: Attendance vs Grade scatter ───────────
    figs["scatter_att_grade"] = px.scatter(
        df,
        x="attendance_rate",
        y="avg_grade",
        color="cluster_label",
        size="engagement_score",
        hover_data=["full_name", "failed_concepts", "course_name"],
        title="Clusters — Attendance vs Grade",
        labels={
            "attendance_rate": "Attendance Rate (%)",
            "avg_grade":       "Average Grade (%)",
            "cluster_label":   "Segment",
        },
        color_discrete_map=SEGMENT_COLORS,
        template=TEMPLATE,
        height=500,
        opacity=0.75,
        size_max=20,
    )

    # ── Fig 2: PCA 2D projection ──────────────────────
    pca = PCA(n_components=2, random_state=42)
    X_pca = pca.fit_transform(X_scaled)
    df_pca = df.copy()
    df_pca["pca_1"] = X_pca[:, 0]
    df_pca["pca_2"] = X_pca[:, 1]
    var1 = pca.explained_variance_ratio_[0] * 100
    var2 = pca.explained_variance_ratio_[1] * 100

    figs["pca"] = px.scatter(
        df_pca,
        x="pca_1",
        y="pca_2",
        color="cluster_label",
        hover_data=["full_name", "avg_grade", "attendance_rate"],
        title=f"Clusters — PCA Projection "
              f"(PC1={var1:.1f}%, PC2={var2:.1f}%)",
        labels={
            "pca_1": f"PC1 ({var1:.1f}% variance)",
            "pca_2": f"PC2 ({var2:.1f}% variance)",
            "cluster_label": "Segment",
        },
        color_discrete_map=SEGMENT_COLORS,
        template=TEMPLATE,
        height=500,
        opacity=0.75,
    )

    # ── Fig 3: Radar chart per cluster ───────────────
    radar_metrics = [
        "avg_grade", "attendance_rate",
        "engagement_score", "concept_pass_rate"
    ]
    radar_labels = [
        "Grade", "Attendance",
        "Engagement", "Concept Pass Rate"
    ]

    fig_radar = go.Figure()

    for label, color in SEGMENT_COLORS.items():
        sub = df[df["cluster_label"] == label]
        if len(sub) == 0:
            continue
        vals = sub[radar_metrics].mean().tolist()
        vals += [vals[0]]  # close the loop

        fig_radar.add_trace(go.Scatterpolar(
            r=vals,
            theta=radar_labels + [radar_labels[0]],
            fill="toself",
            name=label,
            line=dict(color=color),
            opacity=0.65,
        ))

    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title="Clusters — Radar Profile per Segment",
        template=TEMPLATE,
        height=500,
    )
    figs["radar"] = fig_radar

    # ── Fig 4: Cluster size bar ───────────────────────
    size_df = df["cluster_label"].value_counts().reset_index()
    size_df.columns = ["Segment", "Students"]

    figs["sizes"] = px.bar(
        size_df,
        x="Segment",
        y="Students",
        color="Segment",
        color_discrete_map=SEGMENT_COLORS,
        title="Clusters — Segment Sizes",
        text="Students",
        template=TEMPLATE,
        height=400,
    )
    figs["sizes"].update_traces(textposition="outside")

    # ── Fig 5: Heatmap of cluster means ──────────────
    heat_df = df.groupby("cluster_label")[radar_metrics].mean().round(1)

    figs["heatmap"] = px.imshow(
        heat_df,
        text_auto=True,
        color_continuous_scale="Teal",
        title="Clusters — Feature Heatmap",
        labels=dict(color="Value"),
        template=TEMPLATE,
        height=350,
    )

    print(f"   ✅ {len(figs)} cluster figures generated")
    return figs

# ══════════════════════════════════════════════════════
#  STEP 6 — BUILD CLUSTER DOCUMENT
# ══════════════════════════════════════════════════════

def build_cluster_document(
    df: pd.DataFrame,
    cluster_summary: pd.DataFrame,
    labels: dict
) -> pd.DataFrame:
    print("\n── Step 6: Building cluster document (for MongoDB) ──")

    docs = []
    for c, label in labels.items():
        sub  = df[df["cluster"] == c]
        desc = SEGMENT_DESCRIPTIONS.get(label, {})

        docs.append({
            "cluster_id":          int(c),
            "cluster_label":       label,
            "display_label":       desc.get("label", label),
            "color":               desc.get("color", "#888"),
            "description":         desc.get("description", ""),
            "recommended_action":  desc.get("action", ""),
            "student_count":       int(len(sub)),
            "avg_grade":           float(sub["avg_grade"].mean()),
            "avg_attendance":      float(sub["attendance_rate"].mean()),
            "avg_engagement":      float(sub["engagement_score"].mean()),
            "avg_failed_concepts": float(sub["failed_concepts"].mean()),
            "student_ids":         sub["student_id"].tolist(),
        })

    cluster_doc = pd.DataFrame(docs)
    print(cluster_doc[[
        "cluster_id","cluster_label",
        "student_count","avg_grade",
        "avg_attendance","avg_engagement"
    ]].to_string(index=False))

    return cluster_doc

# ══════════════════════════════════════════════════════
#  RUN FULL CLUSTERING PIPELINE
# ══════════════════════════════════════════════════════

def run_clustering(model: dict) -> dict:
    print("\n" + "=" * 55)
    print("  KAYFA — Running clustering pipeline")
    print("=" * 55)

    student_summary = model["student_summary"]

    # Step 1: prepare features
    df, X_scaled, scaler, features = prepare_cluster_features(
        student_summary
    )

    # Step 2: find optimal k
    elbow_fig, best_k = find_optimal_k(X_scaled)

    # force k=4 for interpretability
    # (4 segments maps cleanly to the 4 business personas)
    K = 4
    print(f"\n   Using K=4 for business interpretability "
          f"(silhouette best={best_k})")

    # Step 3: fit
    df, km = fit_kmeans(df, X_scaled, K)

    # Step 4: describe
    df, cluster_summary, labels = describe_clusters(df, features, K)

    # Step 5: visualise
    cluster_figs = visualise_clusters(df, X_scaled, cluster_summary)
    cluster_figs["elbow"] = elbow_fig

    # Step 6: build document
    cluster_doc = build_cluster_document(df, cluster_summary, labels)

    # merge cluster labels back into full student_summary
    model["student_summary"] = student_summary.merge(
        df[["student_id", "cluster", "cluster_label"]],
        on="student_id",
        how="left"
    )

    print("\n" + "=" * 55)
    print("  ✅ Clustering pipeline complete")
    print("=" * 55)

    return {
        "df_clustered":    df,
        "km":              km,
        "scaler":          scaler,
        "features":        features,
        "cluster_summary": cluster_summary,
        "labels":          labels,
        "cluster_doc":     cluster_doc,
        "figures":         cluster_figs,
    }


if __name__ == "__main__":
    dfs      = load_everything()
    cleaned  = clean_all(dfs)
    model    = build_model(cleaned)
    features = compute_all_features(model)

    cluster_results = run_clustering(model)

    # show all cluster figures
    for name, fig in cluster_results["figures"].items():
        print(f"\n── Showing: {name} ──")
        fig.show()