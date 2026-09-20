import os
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = os.path.join(os.getcwd(), "slide_assets")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Slide 2: Core Innovation Graphic
def create_core_innovation_diagram():
    fig, ax = plt.subplots(figsize=(6, 6), dpi=300)
    ax.set_facecolor('#0f172a')
    fig.patch.set_facecolor('#0f172a')
    
    # Draw center circle
    circle_center = plt.Circle((0, 0), 0.35, color='#0284c7', ec='#38bdf8', lw=3, zorder=3)
    ax.add_patch(circle_center)
    ax.text(0, 0.05, "DUAL-FUSION\nAI ENGINE", color='white', weight='bold', fontsize=12, ha='center', va='center', zorder=4)
    ax.text(0, -0.15, "0.55 ML + 0.45 Physics", color='#bae6fd', weight='bold', fontsize=8, ha='center', va='center', zorder=4)

    # 4 Nodes around center
    nodes = [
        ("30m SRTM DEM\nHorn's Slope Gradient", (0, 0.75), '#059669', '#34d399'),
        ("Multi-Depth Soil Saturation\n(0-81cm ECMWF / In-Situ)", (0.8, 0), '#d97706', '#fbbf24'),
        ("GSI NLSM 1:50k\nCorridor Micro-Zonation", (0, -0.75), '#7c3aed', '#a78bfa'),
        ("Offline Citizen & Official\nGeo-Tagged Field Reports", (-0.8, 0), '#dc2626', '#f87171'),
    ]

    for label, (x, y), bg_col, ec_col in nodes:
        # Connecting line
        ax.plot([0, x], [0, y], color='#475569', lw=2, ls='--', zorder=1)
        node_box = plt.Circle((x, y), 0.26, color=bg_col, ec=ec_col, lw=2.5, zorder=3)
        ax.add_patch(node_box)
        ax.text(x, y, label, color='white', weight='bold', fontsize=7.5, ha='center', va='center', zorder=4)

    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-1.15, 1.15)
    ax.axis('off')
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "core_innovation.png")
    plt.savefig(path, facecolor=fig.get_facecolor(), bbox_inches='tight', pad_inches=0.05)
    plt.close()
    print("Saved:", path)


# 2. Slide 3: System Architecture & Data Flow
def create_architecture_diagram():
    fig, ax = plt.subplots(figsize=(8.2, 4.2), dpi=300)
    ax.set_facecolor('#0f172a')
    fig.patch.set_facecolor('#0f172a')
    
    # 4 Columns of Architecture
    cols = [
        ("1. INGESTION", ["• Open-Meteo & IMD (Rain)", "  (6h, 24h, 48h, 7d windows)", "• ECMWF ERA5 (Soil 0-81cm)", "• USGS 30m SRTM Global DEM", "• GSI NLSM 1:50k Vectors"], '#0284c7', 0.12),
        ("2. SPATIAL ENGINE", ["• Horn's 3x3 Convolution", "• Real-Time Slope & Aspect", "• Point-in-Polygon Match", "• Drainage & Road Buffers", "• Geomorphic Zonation"], '#0d9488', 0.38),
        ("3. DUAL-FUSION AI", ["• XGBoost Classifier v3.0", "• Empirical GSI I-D Failsafe", "  (I = 43.26·D^-0.78)", "• 0.55 ML + 0.45 Physics", "• 4 Action Bands (<0.45, 0.65)"], '#d97706', 0.64),
        ("4. ACTION & ALERTS", ["• Leaflet Interactive GIS Map", "• 6-Layer Scientific Inspector", "• Multilingual SMS Alerts", "• Offline Field Incident App", "• What-If Scenario Simulator"], '#e11d48', 0.90),
    ]

    for title, items, col_color, cx in cols:
        # Card Background
        rect = plt.Rectangle((cx - 0.105, 0.08), 0.21, 0.84, color='#1e293b', ec=col_color, lw=2, zorder=2)
        ax.add_patch(rect)
        # Header banner
        hdr = plt.Rectangle((cx - 0.105, 0.78), 0.21, 0.14, color=col_color, zorder=3)
        ax.add_patch(hdr)
        ax.text(cx, 0.85, title, color='white', weight='bold', fontsize=8.5, ha='center', va='center', zorder=4)
        
        # Bullets
        y_text = 0.70
        for it in items:
            ax.text(cx - 0.09, y_text, it, color='#e2e8f0', fontsize=6.2, va='center', zorder=4)
            y_text -= 0.12

        # Draw arrow to next column
        if cx < 0.8:
            ax.annotate('', xy=(cx + 0.135, 0.5), xytext=(cx + 0.105, 0.5),
                        arrowprops=dict(arrowstyle="->", color='#38bdf8', lw=2.5), zorder=5)

    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.0)
    ax.axis('off')
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "architecture_pipeline.png")
    plt.savefig(path, facecolor=fig.get_facecolor(), bbox_inches='tight', pad_inches=0.05)
    plt.close()
    print("Saved:", path)


# 3. Slide 5: Comparison Bar Chart (Current Crisis vs LEWS Sentinel)
def create_impact_comparison_chart():
    fig, ax = plt.subplots(figsize=(6.2, 4.0), dpi=300)
    ax.set_facecolor('#0f172a')
    fig.patch.set_facecolor('#0f172a')

    metrics = [
        "Community Reached (%)",
        "False Alarm Rate (%)",
        "Detection Accuracy (%)",
        "Road Clearance Lead-Time (Hrs)",
        "Preemptive Warning Time (Hrs)"
    ]

    current_system = [15, 68, 30, 4, 1]
    lews_sentinel = [95, 8.6, 88.5, 48, 72]

    y = np.arange(len(metrics))
    height = 0.35

    ax.barh(y - height/2, current_system, height, label='Current Reactive System', color='#ef4444', alpha=0.85, edgecolor='#f87171')
    ax.barh(y + height/2, lews_sentinel, height, label='LEWS AI Sentinel', color='#10b981', alpha=0.9, edgecolor='#34d399')

    ax.set_yticks(y)
    ax.set_yticklabels(metrics, color='#f8fafc', fontsize=8, weight='bold')
    ax.tick_params(axis='x', colors='#94a3b8')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#475569')
    ax.spines['bottom'].set_color('#475569')
    ax.xaxis.grid(True, color='#334155', linestyle='--', alpha=0.7)

    # Value annotations
    for i, (c, l) in enumerate(zip(current_system, lews_sentinel)):
        ax.text(c + 1.5, i - height/2, f"{c}", color='#fca5a5', va='center', fontsize=7.5, weight='bold')
        ax.text(l + 1.5, i + height/2, f"{l}", color='#6ee7b7', va='center', fontsize=7.5, weight='bold')

    ax.set_xlim(0, 110)
    ax.legend(loc='lower right', facecolor='#1e293b', edgecolor='#475569', labelcolor='#f8fafc', fontsize=8)
    ax.set_title("Operational Comparison: Current Reactive vs. LEWS Sentinel", color='#38bdf8', weight='bold', fontsize=9.5, pad=10)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "impact_comparison.png")
    plt.savefig(path, facecolor=fig.get_facecolor(), bbox_inches='tight', pad_inches=0.05)
    plt.close()
    print("Saved:", path)


# 4. Slide 6: UI/UX Showcase Cards
def create_ui_mockup_panels():
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.2), dpi=300)
    fig.patch.set_facecolor('#0f172a')

    # Card 1: GIS Command Map
    ax1 = axes[0]
    ax1.set_facecolor('#1e293b')
    ax1.set_title("Interactive GIS Command Map", color='#38bdf8', fontsize=8.5, weight='bold', pad=8)
    # Simulated map graphic
    ax1.plot([0.2, 0.4, 0.6, 0.8], [0.3, 0.7, 0.4, 0.8], color='#ef4444', lw=3, label='NH-10 Highway Corridor')
    ax1.scatter([0.2, 0.4, 0.6, 0.8], [0.3, 0.7, 0.4, 0.8], c=['#10b981', '#ef4444', '#f59e0b', '#ef4444'], s=120, edgecolors='white', zorder=4)
    ax1.text(0.4, 0.76, "Mangan: CRITICAL (0.88)", color='#fca5a5', fontsize=6.5, weight='bold', ha='center')
    ax1.text(0.6, 0.46, "Gangtok: MODERATE (0.57)", color='#fde68a', fontsize=6.5, weight='bold', ha='center')
    ax1.text(0.2, 0.36, "Rangpo: LOW (0.24)", color='#a7f3d0', fontsize=6.5, weight='bold', ha='center')
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')

    # Card 2: 6-Layer Scientific Decomposition
    ax2 = axes[1]
    ax2.set_facecolor('#1e293b')
    ax2.set_title("6-Layer Scientific Inspector", color='#38bdf8', fontsize=8.5, weight='bold', pad=8)
    layers = [
        ("1. Static Susceptibility", "GSI NLSM High (1.00)"),
        ("2. Dynamic Telemetry", "Rain: 150mm/7d | Soil: 0.34"),
        ("3. ML Inference (XGBoost)", "Failure Probability: 73.1%"),
        ("4. Physics Hazard Index", "Empirical Power Law: 0.44"),
        ("5. Compound Decision", "Score: 0.60 -> MODERATE"),
        ("6. Scientific Synthesis", "Ant-moisture failure hazard")
    ]
    for idx, (title, val) in enumerate(layers):
        y_pos = 0.85 - idx * 0.15
        rect = plt.Rectangle((0.05, y_pos - 0.05), 0.90, 0.12, color='#334155', ec='#0284c7', lw=1.2)
        ax2.add_patch(rect)
        ax2.text(0.08, y_pos + 0.02, title, color='#38bdf8', fontsize=6.0, weight='bold')
        ax2.text(0.08, y_pos - 0.03, val, color='#f8fafc', fontsize=5.8)
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')

    # Card 3: Citizen Field Report & Offline Node
    ax3 = axes[2]
    ax3.set_facecolor('#1e293b')
    ax3.set_title("Citizen App & Field Reporting", color='#38bdf8', fontsize=8.5, weight='bold', pad=8)
    # Form simulation
    ax3.text(0.1, 0.85, "Field Incident Report Submission", color='#f8fafc', fontsize=7, weight='bold')
    ax3.text(0.1, 0.72, "• GPS: 27.3389°N, 88.6065°E (Auto-Pinned)", color='#94a3b8', fontsize=6.2)
    ax3.text(0.1, 0.58, "• Anomaly: 15cm Road Tension Crack", color='#fca5a5', fontsize=6.2)
    ax3.text(0.1, 0.44, "• Evidence: Geo-tagged Photo Uploaded", color='#38bdf8', fontsize=6.2)
    ax3.text(0.1, 0.30, "• Status: Dispatched to SDMA & BRO", color='#34d399', fontsize=6.2, weight='bold')
    btn = plt.Rectangle((0.1, 0.10), 0.8, 0.14, color='#e11d48', ec='#f43f5e', lw=1.5)
    ax3.add_patch(btn)
    ax3.text(0.5, 0.17, "TRANSMIT EMERGENCY SOS", color='white', weight='bold', fontsize=6.8, ha='center', va='center')
    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.axis('off')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "ui_showcase_panels.png")
    plt.savefig(path, facecolor=fig.get_facecolor(), bbox_inches='tight', pad_inches=0.05)
    plt.close()
    print("Saved:", path)


if __name__ == "__main__":
    create_core_innovation_diagram()
    create_architecture_diagram()
    create_impact_comparison_chart()
    create_ui_mockup_panels()
    print("All slide graphics generated successfully!")
