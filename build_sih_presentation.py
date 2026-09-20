import os
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

TEMPLATE_PATH = r"C:\Users\saide\Downloads\SIH2026-IDEA-Presentation-Format.pptx"
OUTPUT_PATH = r"C:\Users\saide\Downloads\SIH2026_PS26001_LEWS_Presentation.pptx"
ASSETS_DIR = os.path.join(os.getcwd(), "slide_assets")

prs = pptx.Presentation(TEMPLATE_PATH)

# Color Palette Constants
NAVY_DARK = RGBColor(15, 23, 42)      # #0f172a
NAVY_CARD = RGBColor(30, 41, 59)      # #1e293b
NAVY_BORDER = RGBColor(51, 65, 85)    # #334155
CYAN_ACCENT = RGBColor(56, 189, 248)  # #38bdf8
TEAL_ACCENT = RGBColor(13, 148, 136)  # #0d9488
GREEN_ALERT = RGBColor(16, 185, 129)  # #10b981
RED_ALERT = RGBColor(239, 68, 68)     # #ef4444
AMBER_ALERT = RGBColor(245, 158, 11)  # #f59e0b
WHITE = RGBColor(255, 255, 255)
LIGHT_GRAY = RGBColor(226, 232, 240)  # #e2e8f0
MUTED_GRAY = RGBColor(148, 163, 184)  # #94a3b8

def style_text_frame(tf):
    tf.word_wrap = True
    tf.margin_left = Inches(0.08)
    tf.margin_right = Inches(0.08)
    tf.margin_top = Inches(0.08)
    tf.margin_bottom = Inches(0.08)

def add_bullet_point(tf, bold_prefix, text_body, pt_size=10, bold_color=CYAN_ACCENT, body_color=LIGHT_GRAY, space_after=4):
    p = tf.add_paragraph()
    p.space_after = Pt(space_after)
    run_bold = p.add_run()
    run_bold.text = bold_prefix + ": " if bold_prefix else "• "
    run_bold.font.bold = True
    run_bold.font.size = Pt(pt_size)
    run_bold.font.color.rgb = bold_color
    run_bold.font.name = "Segoe UI"
    
    run_body = p.add_run()
    run_body.text = text_body
    run_body.font.bold = False
    run_body.font.size = Pt(pt_size)
    run_body.font.color.rgb = body_color
    run_body.font.name = "Segoe UI"
    return p


# ==============================================================================
# SLIDE 1: TITLE PAGE
# ==============================================================================
slide1 = prs.slides[0]

# Clear placeholder subtitle 'TITLE PAGE'
for shape in slide1.shapes:
    if shape.name == "Subtitle 3" and shape.has_text_frame:
        shape.text_frame.clear()
    elif shape.name == "TextBox 9" and shape.has_text_frame:
        tf = shape.text_frame
        tf.clear()
        
        items = [
            ("Problem Statement ID", "26001 (SIH_26001)", RED_ALERT),
            ("Problem Statement Title", "AI-Powered Real-Time Landslide Early Warning & Monitoring System for North Eastern Region (NER)", WHITE),
            ("Theme", "Disaster Management / Climate Resilience & Disaster Management", CYAN_ACCENT),
            ("PS Category", "Software", GREEN_ALERT),
            ("Team ID", "92770", AMBER_ALERT),
            ("Team Name", "404 The Optimists (Project: GeoSentinel-AI)", WHITE)
        ]
        
        for label, val, val_col in items:
            p = tf.add_paragraph()
            p.space_after = Pt(7)
            r1 = p.add_run()
            r1.text = f"• {label} – "
            r1.font.bold = True
            r1.font.size = Pt(13)
            r1.font.color.rgb = RGBColor(15, 23, 42)
            r1.font.name = "Segoe UI"
            
            r2 = p.add_run()
            r2.text = val
            r2.font.bold = True
            r2.font.size = Pt(13)
            r2.font.color.rgb = RGBColor(30, 58, 138) if val_col == WHITE else val_col
            r2.font.name = "Segoe UI"

# Add Project Tagline Badge on Slide 1
tag_shape = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.36), Inches(5.65), Inches(6.8), Inches(0.95))
tag_shape.fill.solid()
tag_shape.fill.fore_color.rgb = NAVY_CARD
tag_shape.line.color.rgb = CYAN_ACCENT
tag_shape.line.width = Pt(1.5)
tf_tag = tag_shape.text_frame
style_text_frame(tf_tag)
p1 = tf_tag.paragraphs[0]
p1.alignment = PP_ALIGN.LEFT
r_tag = p1.add_run()
r_tag.text = "GeoSentinel-AI: Multi-Sensor Early Warning & Decision Support"
r_tag.font.bold = True
r_tag.font.size = Pt(12)
r_tag.font.color.rgb = CYAN_ACCENT
p2 = tf_tag.add_paragraph()
r_sub = p2.add_run()
r_sub.text = "Fusing USGS/NASA 30m SRTM DEM, Live Radar Rainfall, Soil Moisture & GSI NLSM"
r_sub.font.size = Pt(9.5)
r_sub.font.color.rgb = LIGHT_GRAY


# ==============================================================================
# SLIDE 2: IDEA TITLE & PROPOSED SOLUTION
# ==============================================================================
slide2 = prs.slides[1]

# Update Title & Team Oval
for s in slide2.shapes:
    if s.name == "Title 1" and s.has_text_frame:
        s.left = Inches(1.85)
        s.width = Inches(8.75)
        s.text_frame.text = "GeoSentinel: AI Landslide Early Warning & Monitoring System for NER"
        s.text_frame.paragraphs[0].font.size = Pt(20)
        s.text_frame.paragraphs[0].font.bold = True
        s.text_frame.paragraphs[0].font.color.rgb = RGBColor(30, 58, 138)
        s.text_frame.paragraphs[0].font.name = "Segoe UI"
    elif s.name == "Oval 9" and s.has_text_frame:
        s.text_frame.text = "404 The\nOptimists"
        s.text_frame.paragraphs[0].font.size = Pt(9.5)
        s.text_frame.paragraphs[0].font.bold = True
    elif s.name == "TextBox 8":
        # Clear template placeholder
        s.text_frame.clear()

# Left Column: Problem & Solution Stack (3 Cards)
y_pos = Inches(1.30)
box_height = Inches(1.55)
box_width = Inches(4.30)

cards_s2 = [
    ("Real-World Crisis", "Fragile Himalayan geology, unplanned slope excavation, and monsoonal cloudbursts trigger recurring slope failures across NER, severing connectivity and isolating communities.", RED_ALERT),
    ("Strategic Impact", "Over ₹500+ Cr annual road restoration costs; critical supply & defense corridors (NH-10) paralyzed for 7–14 days; 95% of current monitoring is purely reactive.", AMBER_ALERT),
    ("Our AI Solution", "Physics-informed dual-fusion platform combining 30m SRTM DEM, live radar rainfall, 5-layer soil saturation, and GSI susceptibility to predict slope failures 24–72 hours in advance.", GREEN_ALERT)
]

for title, body, col in cards_s2:
    shape = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.40), y_pos, box_width, box_height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = NAVY_CARD
    shape.line.color.rgb = col
    shape.line.width = Pt(1.5)
    tf = shape.text_frame
    style_text_frame(tf)
    p_title = tf.paragraphs[0]
    r_t = p_title.add_run()
    r_t.text = f"🚨 {title}" if "Crisis" in title else (f"⚠️ {title}" if "Strategic" in title else f"💡 {title}")
    r_t.font.bold = True
    r_t.font.size = Pt(11)
    r_t.font.color.rgb = col
    
    p_b = tf.add_paragraph()
    p_b.space_before = Pt(3)
    r_b = p_b.add_run()
    r_b.text = body
    r_b.font.size = Pt(9.2)
    r_b.font.color.rgb = LIGHT_GRAY
    y_pos += box_height + Inches(0.12)

# Prototype Pill at bottom of left column
proto_pill = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.40), y_pos, box_width, Inches(0.55))
proto_pill.fill.solid()
proto_pill.fill.fore_color.rgb = RGBColor(15, 23, 42)
proto_pill.line.color.rgb = CYAN_ACCENT
proto_pill.line.width = Pt(1.2)
tf_p = proto_pill.text_frame
style_text_frame(tf_p)
p_pr = tf_p.paragraphs[0]
p_pr.alignment = PP_ALIGN.CENTER
r_pr = p_pr.add_run()
r_pr.text = "PROTOTYPE: Live GIS Command Map  |  Field Citizen Mobile App"
r_pr.font.bold = True
r_pr.font.size = Pt(9.5)
r_pr.font.color.rgb = CYAN_ACCENT

# Center: Core Innovation Diagram (Embedded Graphic)
core_img_path = os.path.join(ASSETS_DIR, "core_innovation.png")
if os.path.exists(core_img_path):
    slide2.shapes.add_picture(core_img_path, Inches(4.85), Inches(1.30), Inches(4.15), Inches(4.15))

# Right Column: Risk vs Solution 3-Tier Matchup (Matching Reference Format)
y_match = Inches(1.30)
match_height = Inches(1.65)
match_width = Inches(3.75)

matches = [
    ("HIGHWAY BLACKOUTS", "NH-10 & border routes cut off for days without warning.",
     "CORRIDOR RISK ALERTS", "Preemptive GIS corridor heatmaps & traffic diversion.", RED_ALERT, GREEN_ALERT),
    ("EMERGENCY DELAYS", "7–14 day response delays for medical & food aid.",
     "24–72H ADVANCE WARNING", "Empowers SDRF/NDRF early staging before cutoffs.", AMBER_ALERT, CYAN_ACCENT),
    ("MONITORING BLINDSPOTS", "Remote steep habitations have zero sensor coverage.",
     "CROWDSOURCED CITIZEN APP", "Geo-tagged photo/crack reporting with offline sync.", RGBColor(244, 63, 94), RGBColor(52, 211, 153))
]

for r_t, r_b, s_t, s_b, r_c, s_c in matches:
    # Outer Container
    cnt = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(9.15), y_match, match_width, match_height)
    cnt.fill.solid()
    cnt.fill.fore_color.rgb = NAVY_CARD
    cnt.line.color.rgb = NAVY_BORDER
    cnt.line.width = Pt(1)
    tf_m = cnt.text_frame
    style_text_frame(tf_m)
    
    # Risk Row
    p_r = tf_m.paragraphs[0]
    run_rt = p_r.add_run()
    run_rt.text = f"❌ Risk: {r_t} — "
    run_rt.font.bold = True
    run_rt.font.size = Pt(9.5)
    run_rt.font.color.rgb = r_c
    run_rb = p_r.add_run()
    run_rb.text = r_b
    run_rb.font.size = Pt(8.8)
    run_rb.font.color.rgb = LIGHT_GRAY
    
    # Solution Row
    p_s = tf_m.add_paragraph()
    p_s.space_before = Pt(4)
    run_st = p_s.add_run()
    run_st.text = f"✅ Solution: {s_t} — "
    run_st.font.bold = True
    run_st.font.size = Pt(9.5)
    run_st.font.color.rgb = s_c
    run_sb = p_s.add_run()
    run_sb.text = s_b
    run_sb.font.size = Pt(8.8)
    run_sb.font.color.rgb = WHITE
    
    y_match += match_height + Inches(0.12)


# ==============================================================================
# SLIDE 3: TECHNICAL APPROACH
# ==============================================================================
slide3 = prs.slides[2]

for s in slide3.shapes:
    if s.name == "Title 1" and s.has_text_frame:
        s.left = Inches(1.85)
        s.width = Inches(8.75)
        s.text_frame.text = "TECHNICAL APPROACH & SYSTEM ARCHITECTURE"
        s.text_frame.paragraphs[0].font.size = Pt(21)
        s.text_frame.paragraphs[0].font.bold = True
        s.text_frame.paragraphs[0].font.color.rgb = RGBColor(30, 58, 138)
    elif s.name in ["Oval 10", "Oval 9"] and s.has_text_frame:
        s.text_frame.text = "404 The\nOptimists"
        s.text_frame.paragraphs[0].font.size = Pt(9.5)
        s.text_frame.paragraphs[0].font.bold = True
    elif s.name == "TextBox 8":
        s.text_frame.clear()

# Top Banner: Architecture Flow Diagram Image
arch_img_path = os.path.join(ASSETS_DIR, "architecture_pipeline.png")
if os.path.exists(arch_img_path):
    slide3.shapes.add_picture(arch_img_path, Inches(0.40), Inches(1.30), Inches(8.30), Inches(4.30))

# Right Column: Technologies Used (4 Vertical Cards)
tech_cards = [
    ("FrontEnd & Visuals", "React / Modern HTML5, Leaflet GIS, Chart.js, Lucide Icons, Mobile Responsive PWA", CYAN_ACCENT),
    ("BackEnd & Engine", "FastAPI (Python 3), Rasterio, GeoPandas, NumPy, ThreadPoolExecutor (<1s Latency)", TEAL_ACCENT),
    ("AI / ML Models", "XGBoost Classifier v3.0, Scikit-learn, Calibrated Probability Tuning (ROC-AUC 0.98)", AMBER_ALERT),
    ("GIS, Satellites & IoT", "USGS/NASA 30m SRTM DEM, GSI NLSM 1:50k Vectors, Open-Meteo Radar, LoRaWAN IoT", GREEN_ALERT),
]

y_tech = Inches(1.30)
t_height = Inches(1.02)
t_width = Inches(4.15)

for title, details, col in tech_cards:
    card = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.85), y_tech, t_width, t_height)
    card.fill.solid()
    card.fill.fore_color.rgb = NAVY_CARD
    card.line.color.rgb = col
    card.line.width = Pt(1.5)
    tf_c = card.text_frame
    style_text_frame(tf_c)
    p_t = tf_c.paragraphs[0]
    r_th = p_t.add_run()
    r_th.text = f"💻 {title}" if "FrontEnd" in title else (f"⚙️ {title}" if "BackEnd" in title else (f"🤖 {title}" if "AI" in title else f"🛰️ {title}"))
    r_th.font.bold = True
    r_th.font.size = Pt(10.5)
    r_th.font.color.rgb = col
    
    p_d = tf_c.add_paragraph()
    p_d.space_before = Pt(2)
    r_dt = p_d.add_run()
    r_dt.text = details
    r_dt.font.size = Pt(8.8)
    r_dt.font.color.rgb = LIGHT_GRAY
    y_tech += t_height + Inches(0.12)

# Bottom Links Bar across full width
links_bar = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.40), Inches(5.80), Inches(12.60), Inches(0.75))
links_bar.fill.solid()
links_bar.fill.fore_color.rgb = RGBColor(15, 23, 42)
links_bar.line.color.rgb = CYAN_ACCENT
links_bar.line.width = Pt(1.5)
tf_l = links_bar.text_frame
style_text_frame(tf_l)
p_lb = tf_l.paragraphs[0]
p_lb.alignment = PP_ALIGN.CENTER
r_l = p_lb.add_run()
r_l.text = "🔗 REPOSITORIES & LIVE VERIFICATION:  "
r_l.font.bold = True
r_l.font.size = Pt(10)
r_l.font.color.rgb = WHITE
r_l2 = p_lb.add_run()
r_l2.text = "Interactive GIS Command Center  |  FastAPI Backend Engine  |  GSI NLSM Sikkim Pilot Dataset  |  Holdout Validation Suite"
r_l2.font.bold = False
r_l2.font.size = Pt(9.5)
r_l2.font.color.rgb = CYAN_ACCENT


# ==============================================================================
# SLIDE 4: FEASIBILITY AND VIABILITY
# ==============================================================================
slide4 = prs.slides[3]

for s in slide4.shapes:
    if s.name == "Title 1" and s.has_text_frame:
        s.left = Inches(1.85)
        s.width = Inches(8.75)
        s.text_frame.text = "FEASIBILITY AND VIABILITY ANALYSIS"
        s.text_frame.paragraphs[0].font.size = Pt(21)
        s.text_frame.paragraphs[0].font.bold = True
        s.text_frame.paragraphs[0].font.color.rgb = RGBColor(30, 58, 138)
    elif s.name in ["Oval 11", "Oval 10"] and s.has_text_frame:
        s.text_frame.text = "404 The\nOptimists"
        s.text_frame.paragraphs[0].font.size = Pt(9.5)
        s.text_frame.paragraphs[0].font.bold = True
    elif s.name == "TextBox 8":
        s.text_frame.clear()

col_width = Inches(4.05)
col_height = Inches(5.25)
y_c = Inches(1.35)

# Col 1: FEASIBILITY ANALYSIS (⭐⭐⭐⭐⭐ 4.8/5)
c1 = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.40), y_c, col_width, col_height)
c1.fill.solid()
c1.fill.fore_color.rgb = NAVY_CARD
c1.line.color.rgb = AMBER_ALERT
c1.line.width = Pt(1.5)
tf1 = c1.text_frame
style_text_frame(tf1)
p_h1 = tf1.paragraphs[0]
r_h1 = p_h1.add_run()
r_h1.text = "FEASIBILITY ANALYSIS\n⭐⭐⭐⭐⭐ (4.8 / 5.0)"
r_h1.font.bold = True
r_h1.font.size = Pt(12)
r_h1.font.color.rgb = AMBER_ALERT
p_h1.alignment = PP_ALIGN.CENTER

add_bullet_point(tf1, "Infrastructure Reusability", "Reuses existing IMD weather radars, open satellite DEM, and GSI maps; zero immediate hardware sensor dependency.", 9.2, CYAN_ACCENT, space_after=8)
add_bullet_point(tf1, "Scalable Deployment", "Field-tested in Sikkim pilot (10 arterial nodes: Gangtok, Mangan, Pakyong); ready for immediate rollout across all 8 NER states.", 9.2, CYAN_ACCENT, space_after=8)
add_bullet_point(tf1, "Cost-Effectiveness", "Pure open-source software stack + lightweight microservices; reduces capital setup expenditure by >85% compared to proprietary systems.", 9.2, CYAN_ACCENT, space_after=8)
add_bullet_point(tf1, "Authority Integration", "Role-based portals for District Magistrates, SDMA/NDRF emergency response units, and Border Roads Organisation (BRO).", 9.2, CYAN_ACCENT, space_after=6)

# Col 2: VIABILITY (Proven Concept ✔)
c2 = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4.65), y_c, col_width, col_height)
c2.fill.solid()
c2.fill.fore_color.rgb = NAVY_CARD
c2.line.color.rgb = GREEN_ALERT
c2.line.width = Pt(1.5)
tf2 = c2.text_frame
style_text_frame(tf2)
p_h2 = tf2.paragraphs[0]
r_h2 = p_h2.add_run()
r_h2.text = "VIABILITY & VALIDATION\n✔ PROVEN DUAL-FUSION MODEL"
r_h2.font.bold = True
r_h2.font.size = Pt(12)
r_h2.font.color.rgb = GREEN_ALERT
p_h2.alignment = PP_ALIGN.CENTER

add_bullet_point(tf2, "Proven Dual Concept", "Geotechnical slope physics (saturation) fused with gradient boosting ML eliminates blindspots and prevents uncalibrated false alarms.", 9.2, GREEN_ALERT, space_after=8)
add_bullet_point(tf2, "Builds Public Trust", "6-layer scientific decomposition explains exact rationale for every risk score (Static Susceptibility ≠ Dynamic Hazard ≠ Compound Risk).", 9.2, GREEN_ALERT, space_after=8)
add_bullet_point(tf2, "Guarantees Accountability", "5-stage immutable audit trail from raw satellite feed to final alert dispatch for post-disaster audits.", 9.2, GREEN_ALERT, space_after=8)
add_bullet_point(tf2, "Offline & Low-Bandwidth", "Client-side caching and offline manual risk calculator work seamlessly in zero-connectivity valleys.", 9.2, GREEN_ALERT, space_after=6)

# Col 3: BUSINESS & STRATEGIC POTENTIAL
c3 = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.90), y_c, col_width, col_height)
c3.fill.solid()
c3.fill.fore_color.rgb = NAVY_CARD
c3.line.color.rgb = CYAN_ACCENT
c3.line.width = Pt(1.5)
tf3 = c3.text_frame
style_text_frame(tf3)
p_h3 = tf3.paragraphs[0]
r_h3 = p_h3.add_run()
r_h3.text = "BUSINESS & STRATEGIC VALUE\n💼 ECONOMIC & DISASTER ROI"
r_h3.font.bold = True
r_h3.font.size = Pt(12)
r_h3.font.color.rgb = CYAN_ACCENT
p_h3.alignment = PP_ALIGN.CENTER

add_bullet_point(tf3, "Government Cost Savings", "Preemptive road clearance mobilization saves ₹100+ Cr annually in idle heavy machinery, emergency fuel, and detours.", 9.2, WHITE, space_after=8)
add_bullet_point(tf3, "Zero-Casualty Evacuations", "Empowers disaster management to evacuate vulnerable toe habitations 24–48 hours before slope collapse.", 9.2, WHITE, space_after=8)
add_bullet_point(tf3, "Climate-Resilient Governance", "Dynamic GIS heatmaps provide district administrations with data-driven hill cutting regulations and road planning.", 9.2, WHITE, space_after=8)
add_bullet_point(tf3, "Defense & Tourism Security", "Guarantees continuous logistics for Indian Army border posts and safeguards 15+ lakh annual Himalayan tourists.", 9.2, WHITE, space_after=6)


# ==============================================================================
# SLIDE 5: IMPACT AND BENEFITS
# ==============================================================================
slide5 = prs.slides[4]

for s in slide5.shapes:
    if s.name == "Title 1" and s.has_text_frame:
        s.left = Inches(1.85)
        s.width = Inches(8.75)
        s.text_frame.text = "IMPACT AND MEASURABLE BENEFITS"
        s.text_frame.paragraphs[0].font.size = Pt(21)
        s.text_frame.paragraphs[0].font.bold = True
        s.text_frame.paragraphs[0].font.color.rgb = RGBColor(30, 58, 138)
    elif s.name in ["Oval 11", "Oval 10"] and s.has_text_frame:
        s.text_frame.text = "404 The\nOptimists"
        s.text_frame.paragraphs[0].font.size = Pt(9.5)
        s.text_frame.paragraphs[0].font.bold = True
    elif s.name == "TextBox 8":
        s.text_frame.clear()

# Left Column: 4 Numbered Impact Badges & Descriptions
y_imp = Inches(1.35)
imp_height = Inches(1.15)
imp_width = Inches(5.80)

impacts = [
    ("1. Reduced Road Blockages", "40–50% reduction in prolonged highway cuts through proactive slope monitoring, pre-staged earthmovers, and controlled transit.", GREEN_ALERT),
    ("2. 24–72h Emergency Lead-Time", "Advance warning enables NDRF/SDRF deployment and vulnerable community evacuation before monsoonal road cutoffs.", CYAN_ACCENT),
    ("3. Minimized Economic Loss", "Protects perishable agricultural supply chains, trade routes, and strategic military mobility across international borders.", AMBER_ALERT),
    ("4. Community & Citizen Empowerment", "Geo-targeted multilingual SMS (Hindi, Nepali, Assamese, Bengali) and offline incident reporting safeguard remote hamlets.", RED_ALERT)
]

for title, desc, col in impacts:
    card = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.40), y_imp, imp_width, imp_height)
    card.fill.solid()
    card.fill.fore_color.rgb = NAVY_CARD
    card.line.color.rgb = col
    card.line.width = Pt(1.5)
    tf_i = card.text_frame
    style_text_frame(tf_i)
    p_t = tf_i.paragraphs[0]
    r_it = p_t.add_run()
    r_it.text = title
    r_it.font.bold = True
    r_it.font.size = Pt(11)
    r_it.font.color.rgb = col
    
    p_d = tf_i.add_paragraph()
    p_d.space_before = Pt(3)
    r_id = p_d.add_run()
    r_id.text = desc
    r_id.font.size = Pt(9.2)
    r_id.font.color.rgb = LIGHT_GRAY
    y_imp += imp_height + Inches(0.12)

# Right Column: Quantitative Comparison Chart Image
chart_img_path = os.path.join(ASSETS_DIR, "impact_comparison.png")
if os.path.exists(chart_img_path):
    slide5.shapes.add_picture(chart_img_path, Inches(6.45), Inches(1.35), Inches(6.45), Inches(4.15))

# Bottom Transition Banner
trans_banner = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.45), Inches(5.65), Inches(6.45), Inches(0.85))
trans_banner.fill.solid()
trans_banner.fill.fore_color.rgb = RGBColor(15, 23, 42)
trans_banner.line.color.rgb = GREEN_ALERT
trans_banner.line.width = Pt(1.5)
tf_tb = trans_banner.text_frame
style_text_frame(tf_tb)
p_tb = tf_tb.paragraphs[0]
p_tb.alignment = PP_ALIGN.CENTER
r_tb1 = p_tb.add_run()
r_tb1.text = "TRANSFORMATION GOAL:\n"
r_tb1.font.bold = True
r_tb1.font.size = Pt(10.5)
r_tb1.font.color.rgb = GREEN_ALERT
r_tb2 = p_tb.add_run()
r_tb2.text = "From Reactive Post-Disaster Rescue  ➔  Proactive AI Predictive Shield"
r_tb2.font.bold = True
r_tb2.font.size = Pt(11)
r_tb2.font.color.rgb = WHITE


# ==============================================================================
# SLIDE 6: RESEARCH AND REFERENCES
# ==============================================================================
slide6 = prs.slides[5]

for s in slide6.shapes:
    if s.name == "Title 1" and s.has_text_frame:
        s.left = Inches(1.85)
        s.width = Inches(8.75)
        s.text_frame.text = "RESEARCH, REFERENCES & UI/UX DEMONSTRATION"
        s.text_frame.paragraphs[0].font.size = Pt(20)
        s.text_frame.paragraphs[0].font.bold = True
        s.text_frame.paragraphs[0].font.color.rgb = RGBColor(30, 58, 138)
    elif s.name in ["Oval 8", "Oval 9"] and s.has_text_frame:
        s.text_frame.text = "404 The\nOptimists"
        s.text_frame.paragraphs[0].font.size = Pt(9.5)
        s.text_frame.paragraphs[0].font.bold = True
    elif s.name == "TextBox 8":
        s.text_frame.clear()

# Top Banner: 5-Stage Scientific Pipeline Chevron
pipeline_steps = [
    ("1. Data Ingestion", "IMD & Copernicus"),
    ("2. 3x3 Slope Engine", "Horn's Convolution"),
    ("3. Pore Saturation", "ECMWF 0-81cm Soil"),
    ("4. Dual Fusion AI", "0.55 ML + 0.45 Phys"),
    ("5. Early Warnings", "SMS & GIS Heatmap")
]

x_p = Inches(0.40)
p_w = Inches(2.45)
for step, sub in pipeline_steps:
    pbox = slide6.shapes.add_shape(MSO_SHAPE.CHEVRON, x_p, Inches(1.30), p_w, Inches(0.65))
    pbox.fill.solid()
    pbox.fill.fore_color.rgb = NAVY_CARD
    pbox.line.color.rgb = CYAN_ACCENT
    pbox.line.width = Pt(1.2)
    tf_pb = pbox.text_frame
    style_text_frame(tf_pb)
    p_step = tf_pb.paragraphs[0]
    p_step.alignment = PP_ALIGN.CENTER
    r_s1 = p_step.add_run()
    r_s1.text = f"{step}\n"
    r_s1.font.bold = True
    r_s1.font.size = Pt(9.2)
    r_s1.font.color.rgb = WHITE
    r_s2 = p_step.add_run()
    r_s2.text = sub
    r_s2.font.size = Pt(7.5)
    r_s2.font.color.rgb = CYAN_ACCENT
    x_p += p_w + Inches(0.08)

# Middle Row: 7 Research & Data Citations (Grid of 7 cards matching reference PDF)
citations = [
    ("GSI NLSM Sikkim", "1:50,000 Susceptibility Micro-Zonation", CYAN_ACCENT),
    ("USGS/NASA SRTM", "30m Global DEM (SRTMGL1 v003)", TEAL_ACCENT),
    ("ECMWF ERA5-Land", "Multi-Depth Volumetric Soil Moisture", GREEN_ALERT),
    ("GSI I-D Power Law", "Intensity-Duration (I = 43.26·D^-0.78)", AMBER_ALERT),
    ("NDMA Guidelines", "Landslide Risk Management Norms", RED_ALERT),
    ("XGBoost v3.0", "Trained on 155 GSI Events (ROC-AUC 0.98)", RGBColor(168, 85, 247)),
    ("IMD & Open-Meteo", "Radar Feeds & Numerical Weather APIs", RGBColor(236, 72, 153)),
]

x_c = Inches(0.40)
c_width = Inches(1.73)
for title, subtitle, col in citations:
    cite_card = slide6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x_c, Inches(2.10), c_width, Inches(1.15))
    cite_card.fill.solid()
    cite_card.fill.fore_color.rgb = NAVY_CARD
    cite_card.line.color.rgb = col
    cite_card.line.width = Pt(1.2)
    tf_c = cite_card.text_frame
    style_text_frame(tf_c)
    p_ct = tf_c.paragraphs[0]
    p_ct.alignment = PP_ALIGN.CENTER
    r_ct = p_ct.add_run()
    r_ct.text = f"{title}\n"
    r_ct.font.bold = True
    r_ct.font.size = Pt(8.5)
    r_ct.font.color.rgb = col
    r_cs = p_ct.add_run()
    r_cs.text = f"{subtitle}\n"
    r_cs.font.size = Pt(7.2)
    r_cs.font.color.rgb = LIGHT_GRAY
    r_link = p_ct.add_run()
    r_link.text = "[OFFICIAL SOURCE]"
    r_link.font.bold = True
    r_link.font.size = Pt(7.0)
    r_link.font.color.rgb = CYAN_ACCENT
    x_c += c_width + Inches(0.08)

# Bottom Row: UI/UX Command Center Mockup Graphic
ui_img_path = os.path.join(ASSETS_DIR, "ui_showcase_panels.png")
if os.path.exists(ui_img_path):
    slide6.shapes.add_picture(ui_img_path, Inches(0.40), Inches(3.40), Inches(12.60), Inches(3.20))


# ==============================================================================
# DELETE SLIDE 7 (Template instructions slide) -> EXACTLY 6 SLIDES
# ==============================================================================
if len(prs.slides) > 6:
    rId = prs.slides._sldIdLst[6].rId
    prs.part.drop_rel(rId)
    del prs.slides._sldIdLst[6]

prs.save(OUTPUT_PATH)
print(f"Successfully generated 6-slide SIH Presentation: {OUTPUT_PATH}")
print(f"Final slide count: {len(prs.slides)}")
