#!/usr/bin/env python3
"""Generate summary plots for HPC Agent Benchmark results.

Reads results_summary.json and error_narrative.json from batch_results/,
produces:
  1. Speedup heatmap (framework × app) per session
  2. Combined heatmap across all sessions (best run per framework×app)
  3. Build success rate bar chart
  4. Error category summary table (rendered as figure)

Usage:
    source ~/envs/sweagent/bin/activate
    python analysis/plot_results.py
"""

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless nodes
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import seaborn as sns

RESULTS_DIR = Path(__file__).resolve().parent.parent / "batch_results"
OUTPUT_DIR = Path(__file__).resolve().parent / "figures"
OUTPUT_DIR.mkdir(exist_ok=True)

APPS = ["kripke", "laghos", "lulesh", "quicksilver"]
FRAMEWORK_ORDER = ["sweagent", "openhands", "opencode", "codex", "claude"]
FRAMEWORK_LABELS = {
    "sweagent": "SWE-agent",
    "openhands": "OpenHands",
    "opencode": "OpenCode",
    "codex": "Codex",
    "claude": "Claude Code",
}
APP_LABELS = {
    "kripke": "Kripke",
    "laghos": "Laghos",
    "lulesh": "LULESH",
    "quicksilver": "Quicksilver",
}


def load_results():
    """Load results_summary.json."""
    path = RESULTS_DIR / "results_summary.json"
    if not path.exists():
        print(f"ERROR: {path} not found. Run the data gathering step first.")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def load_error_narrative():
    """Load error_narrative.json."""
    path = RESULTS_DIR / "error_narrative.json"
    if not path.exists():
        print(f"WARNING: {path} not found. Skipping error summary plot.")
        return None
    with open(path) as f:
        return json.load(f)


# ─── Plot 1: Speedup Heatmap ────────────────────────────────────────────────

def plot_speedup_heatmap(results, session=None):
    """Create a framework × app heatmap of speedup values.

    Rules:
    - Real optimization with speedup → show value, colored
    - Build failed → show "FAIL", gray
    - Agent crashed / no real changes → show "N/C" (no change), light gray
    - No data → show "—", white
    """
    if session is not None:
        runs = [r for r in results if r.get("session") == session]
        title_suffix = f" (Session {session})"
    else:
        runs = results
        title_suffix = " (All Sessions — Best Per Framework)"

    # Build matrix: for each framework×app, pick the best meaningful run
    matrix = {}
    annotations = {}
    for fw in FRAMEWORK_ORDER:
        matrix[fw] = {}
        annotations[fw] = {}
        for app in APPS:
            best_speedup = None
            best_status = "no_data"  # no_data, no_change, build_fail, has_speedup

            fw_runs = [r for r in runs if r["framework"] == fw]
            for run in fw_runs:
                app_data = run.get("apps", {}).get(app)
                if app_data is None:
                    continue

                builds = app_data.get("builds", False)
                meaningful = app_data.get("meaningful_changes", False)
                speedup = app_data.get("speedup")

                if not builds:
                    if best_status == "no_data":
                        best_status = "build_fail"
                elif not meaningful:
                    if best_status in ("no_data", "build_fail"):
                        best_status = "no_change"
                    # Still record speedup for no_change (it's baseline noise)
                elif speedup is not None:
                    best_status = "has_speedup"
                    if best_speedup is None or speedup > best_speedup:
                        best_speedup = speedup

            if best_status == "has_speedup" and best_speedup is not None:
                matrix[fw][app] = best_speedup
                annotations[fw][app] = f"{best_speedup:.2f}x"
            elif best_status == "build_fail":
                matrix[fw][app] = 0.0
                annotations[fw][app] = "FAIL"
            elif best_status == "no_change":
                matrix[fw][app] = 0.0
                annotations[fw][app] = "N/C"
            else:
                matrix[fw][app] = np.nan
                annotations[fw][app] = "—"

    # Convert to DataFrames
    df = pd.DataFrame(matrix).T
    df = df.reindex(index=FRAMEWORK_ORDER, columns=APPS)
    df.index = [FRAMEWORK_LABELS.get(f, f) for f in df.index]
    df.columns = [APP_LABELS.get(a, a) for a in df.columns]

    annot_df = pd.DataFrame(annotations).T
    annot_df = annot_df.reindex(index=FRAMEWORK_ORDER, columns=APPS)
    annot_df.index = [FRAMEWORK_LABELS.get(f, f) for f in annot_df.index]
    annot_df.columns = [APP_LABELS.get(a, a) for a in annot_df.columns]

    # Create custom colormap: gray for 0, red<1, white=1, green>1
    cmap = sns.diverging_palette(10, 130, s=80, l=55, as_cmap=True)

    fig, ax = plt.subplots(figsize=(10, 6))

    # Mask NaN for proper rendering
    mask = df.isna()

    sns.heatmap(
        df,
        annot=annot_df,
        fmt="",
        cmap=cmap,
        center=1.0,
        vmin=0.0,
        vmax=2.0,
        mask=mask,
        linewidths=2,
        linecolor="white",
        cbar_kws={"label": "Speedup (×)", "shrink": 0.8},
        ax=ax,
        annot_kws={"size": 14, "weight": "bold"},
    )

    # Color the "FAIL" and "N/C" cells gray
    for i, fw in enumerate(df.index):
        for j, app in enumerate(df.columns):
            val = annot_df.iloc[i, j]
            if val in ("FAIL", "N/C", "—"):
                ax.add_patch(plt.Rectangle((j, i), 1, 1, fill=True,
                                           facecolor="#d9d9d9" if val != "—" else "#f5f5f5",
                                           edgecolor="white", linewidth=2))
                ax.text(j + 0.5, i + 0.5, val,
                        ha="center", va="center", fontsize=14, fontweight="bold",
                        color="#666666")

    ax.set_title(f"HPC Agent Benchmark — Speedup Results{title_suffix}",
                 fontsize=16, fontweight="bold", pad=15)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.tick_params(labelsize=13)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, ha="right")

    plt.tight_layout()
    suffix = f"_s{session}" if session else "_all"
    out_path = OUTPUT_DIR / f"speedup_heatmap{suffix}.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")
    return out_path


# ─── Plot 2: Build Success Rate ─────────────────────────────────────────────

def plot_build_success(results):
    """Bar chart showing build success rate per framework across all apps."""
    data = []
    for run in results:
        fw = run["framework"]
        for app in APPS:
            app_data = run.get("apps", {}).get(app)
            if app_data is None:
                continue
            data.append({
                "framework": FRAMEWORK_LABELS.get(fw, fw),
                "app": APP_LABELS.get(app, app),
                "builds": 1 if app_data.get("builds", False) else 0,
            })

    if not data:
        print("  No build data available")
        return None

    df = pd.DataFrame(data)
    summary = df.groupby(["framework", "app"])["builds"].mean().reset_index()
    summary.columns = ["Framework", "App", "Build Success Rate"]

    fig, ax = plt.subplots(figsize=(10, 5))
    pivot = summary.pivot(index="Framework", columns="App", values="Build Success Rate")
    # Reorder
    fw_order = [FRAMEWORK_LABELS[f] for f in FRAMEWORK_ORDER if FRAMEWORK_LABELS[f] in pivot.index]
    app_order = [APP_LABELS[a] for a in APPS if APP_LABELS[a] in pivot.columns]
    pivot = pivot.reindex(index=fw_order, columns=app_order)

    pivot.plot(kind="bar", ax=ax, width=0.7, edgecolor="white", linewidth=0.5)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Build Success Rate", fontsize=12)
    ax.set_xlabel("")
    ax.set_title("Build Success Rate by Framework and App", fontsize=14, fontweight="bold")
    ax.legend(title="App", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
    for p in ax.patches:
        height = p.get_height()
        if height > 0:
            ax.text(p.get_x() + p.get_width() / 2., height + 0.02,
                    f"{height:.0%}", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    out_path = OUTPUT_DIR / "build_success_rate.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")
    return out_path


# ─── Plot 3: Error Category Summary ─────────────────────────────────────────

def plot_error_summary(narrative):
    """Create a table-style figure summarizing error categories and counts."""
    if narrative is None:
        return None

    categories = narrative.get("categories", [])
    if not categories:
        print("  No error categories found")
        return None

    rows = []
    for cat in categories:
        issues = cat.get("issues", [])
        rows.append({
            "Category": cat["name"],
            "Issues Found": len(issues),
            "Example": issues[0]["title"] if issues else "—",
        })

    df = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(12, max(3, len(rows) * 0.6 + 1.5)))
    ax.axis("off")

    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc="left",
        loc="center",
        colWidths=[0.30, 0.12, 0.58],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.8)

    # Style header
    for j in range(len(df.columns)):
        cell = table[0, j]
        cell.set_facecolor("#2c3e50")
        cell.set_text_props(color="white", fontweight="bold")

    # Alternate row colors
    for i in range(1, len(df) + 1):
        color = "#f7f7f7" if i % 2 == 0 else "white"
        for j in range(len(df.columns)):
            table[i, j].set_facecolor(color)

    ax.set_title("Issues Discovered & Fixed Across Development Sessions",
                 fontsize=14, fontweight="bold", pad=20)

    plt.tight_layout()
    out_path = OUTPUT_DIR / "error_summary_table.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")
    return out_path


# ─── Plot 4: Detailed Error Timeline ────────────────────────────────────────

def plot_error_timeline(narrative):
    """Horizontal bar chart showing issues fixed per session."""
    if narrative is None:
        return None

    session_counts = {}
    for cat in narrative.get("categories", []):
        for issue in cat.get("issues", []):
            s = issue.get("session", 0)
            if s not in session_counts:
                session_counts[s] = {}
            cat_name = cat["name"]
            session_counts[s][cat_name] = session_counts[s].get(cat_name, 0) + 1

    if not session_counts:
        return None

    sessions = sorted(session_counts.keys())
    all_cats = sorted(set(
        cat["name"] for cat in narrative.get("categories", [])
    ))

    fig, ax = plt.subplots(figsize=(10, max(4, len(sessions) * 0.5 + 1)))

    bottom = np.zeros(len(sessions))
    colors = sns.color_palette("Set2", len(all_cats))

    for i, cat in enumerate(all_cats):
        values = [session_counts.get(s, {}).get(cat, 0) for s in sessions]
        ax.barh([f"Session {s}" for s in sessions], values, left=bottom,
                label=cat, color=colors[i], edgecolor="white", linewidth=0.5)
        bottom += np.array(values)

    ax.set_xlabel("Number of Issues Fixed", fontsize=12)
    ax.set_title("Issues Fixed Per Session", fontsize=14, fontweight="bold")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)

    plt.tight_layout()
    out_path = OUTPUT_DIR / "error_timeline.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")
    return out_path


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("Loading data...")
    results = load_results()
    narrative = load_error_narrative()

    sessions = sorted(set(r.get("session", 0) for r in results))
    print(f"  Found {len(results)} runs across sessions: {sessions}")
    if narrative:
        total_issues = sum(
            len(cat.get("issues", []))
            for cat in narrative.get("categories", [])
        )
        print(f"  Found {total_issues} issues across {len(narrative.get('categories', []))} categories")

    print("\nGenerating plots...")

    # Per-session heatmaps
    for s in sessions:
        plot_speedup_heatmap(results, session=s)

    # Combined heatmap (best per framework×app)
    plot_speedup_heatmap(results, session=None)

    # Build success rate
    plot_build_success(results)

    # Error summary
    plot_error_summary(narrative)
    plot_error_timeline(narrative)

    print(f"\nAll figures saved to: {OUTPUT_DIR}/")
    print("Done!")


if __name__ == "__main__":
    main()
