import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
st.set_page_config(page_title="UDiff Market Intelligence", layout="wide")

INPUT_FOLDER_NAME = 'analyzer'
INPUT_FILE = 'gap_report.json'
INPUT_FILE_PATH = os.path.join(os.getcwd(), INPUT_FOLDER_NAME, INPUT_FILE)

# --- THEME CSS ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #262730; padding: 15px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- LOAD DATA ---
@st.cache_data
def load_data():
    try:
        with open(INPUT_FILE_PATH, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        return None

data = load_data()

# --- HEADER ---
st.title("🚀 UDiff: The Engineering Gap Report")
st.markdown("Bridging the gap between **University Curriculum** and **Industry Reality**.")

if not data:
    st.error(f"❌ Could not find {INPUT_FILE_PATH}. Run the pipeline first!")
    st.stop()

# --- SIDEBAR (FILTERS) ---
st.sidebar.header("🔍 Filters")

# 1. CATEGORY SELECTION
all_categories = list(data['categories'].keys())

# Remove jobs of 'Other '
if 'Other' in all_categories: 
    all_categories.remove('Other')

all_categories.sort()

selected_category = st.sidebar.selectbox(
    "Select Career Path", 
    all_categories,
    key="category_select"  # <--- UNIQUE KEY ADDED
)

# --- MAIN DASHBOARD ---

# --- NEW: EXPERIENCE LEVEL FILTER ---

cat_data_root = data['categories'][selected_category]

# Check if this is the OLD JSON format (flat dictionary) or NEW (nested levels)
if 'job_count' in cat_data_root:
    # OLD FORMAT DETECTED (Pipeline hasn't finished running yet)
    st.sidebar.warning("⚠️ Using legacy data. Run pipeline for 'Level' filters.")
    selected_level = 'All'
    cat_data = cat_data_root # Treat the whole object as the data
else:
    # NEW FORMAT DETECTED (Nested levels)
    available_levels = list(cat_data_root.keys())
    level_order = ['All', 'Junior', 'Mid', 'Senior']
    sorted_levels = [l for l in level_order if l in available_levels]

    selected_level = st.sidebar.radio(
        "Experience Level", 
        sorted_levels, 
        horizontal=True,
        key="level_select" # <--- UNIQUE KEY ADDED
    )
    cat_data = cat_data_root[selected_level]

# 1. HIGH LEVEL METRICS (Now Dynamic!)
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(f"{selected_level} Openings", f"{cat_data['job_count']}")
    
with col2:
    salary = cat_data.get('salary', {})
    avg_min = salary.get('avg_min', 0)
    avg_max = salary.get('avg_max', 0)
    # Highlight salary changes based on level
    st.metric("Est. Base Salary (MYR)", f"{avg_min:,.0f} - {avg_max:,.0f}")
    
with col3:
    # --- ROBUST MARKET SHARE CALCULATION ---
    # Check if we are using the new nested data (has 'All') or old flat data
    if 'All' in cat_data_root:
        # New Format
        total_in_cat = cat_data_root['All']['job_count']
    else:
        # Old Format (Fallback)
        total_in_cat = cat_data_root['job_count']

    # Prevent division by zero
    if total_in_cat > 0:
        share = (cat_data['job_count'] / total_in_cat) * 100
    else:
        share = 0

    st.metric(f"Share of {selected_category}", f"{share:.1f}%")

# 2. HARD SKILLS & CONTEXT LAYOUT
st.markdown("### 🛠️ Technical Landscape")

# Create two columns: Left for Skills (Bar), Right for Context (Bar/Tags)
col_hard, col_ctx = st.columns(2)

with col_hard:
    st.markdown("#### Top Hard Skills")
    st.caption(f"Most requested tools for {selected_category}.")
    
    hard_skills = cat_data.get('top_hard_skills', [])
    if hard_skills:
        df_skills = pd.DataFrame(hard_skills)
        df_skills = df_skills.sort_values('count', ascending=True) # Sort for chart
        
        fig = px.bar(
            df_skills, 
            x='percentage', 
            y='name', 
            orientation='h',
            text='percentage',
            color='percentage',
            color_continuous_scale='Viridis'
        )
        fig.update_layout(xaxis_title="% of Jobs", yaxis_title=None, showlegend=False)
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        st.plotly_chart(fig, width='stretch')

with col_ctx:
    st.markdown("#### 🌍 Technical Context")
    st.caption("How these skills are applied (Domain/Application).")
    
    context_list = cat_data.get('top_technical_context', [])
    
    if context_list:
        # VISUALIZATION 1: Clean Bar Chart (Easier to read than WordCloud)
        df_ctx = pd.DataFrame(context_list)
        df_ctx = df_ctx.sort_values('count', ascending=True)
        
        fig_ctx = px.bar(
            df_ctx, 
            x='percentage', 
            y='name', 
            orientation='h',
            text='percentage',
            color='percentage',
            color_continuous_scale='Magma' # Different color to distinguish
        )
        fig_ctx.update_layout(xaxis_title="% of Jobs", yaxis_title=None, showlegend=False)
        fig_ctx.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        st.plotly_chart(fig_ctx, width='stretch')
        
    else:
        st.info("No specific context data available for this category.")

# 3. SOFT SKILLS & WORD CLOUD (Polished)
st.markdown("---")
c1, c2 = st.columns([1, 2])

with c1:
    st.markdown("### 🧠 Soft Skills")
    soft_skills = cat_data.get('top_soft_skills', [])
    if soft_skills:
        for skill in soft_skills:
            st.success(f"**{skill}**")

with c2:
    st.markdown("### 🗺️ Context Map")
    st.caption("Dominant technologies and domains represented by area size.")
    
    # Prepare data for Treemap
    treemap_data = []
    # Combine hard skills (top 15) and context (top 10)
    for item in hard_skills[:15] + context_list[:10]:
        treemap_data.append({
            "Label": item['name'],
            "Value": item['count'],
            "Type": "Skill" if item in hard_skills else "Context"
        })
    
    if treemap_data:
        df_tree = pd.DataFrame(treemap_data)
        
        fig_tree = px.treemap(
            df_tree, 
            path=['Type', 'Label'], 
            values='Value',
            color='Value',
            color_continuous_scale='Blues',
            title=''
        )
        fig_tree.update_layout(margin=dict(t=0, l=0, r=0, b=0))
        st.plotly_chart(fig_tree, use_container_width=True)

# 4. Personal Skill Check Roadmap
st.markdown("---")
st.header("✅ Am I Ready?")
st.caption("Select the skills you already possess to see your market fit.")

## 1. Get all top skills for this category
top_skill_names = [s['name'] for s in cat_data.get('top_hard_skills', [])][:20]

## 2. User Input
user_skills = st.multiselect("My Tech Stack", top_skill_names)

## 3. Calculation
if user_skills:
    match_count = len(user_skills)
    total_needed = len(top_skill_names)
    score = (match_count / total_needed) * 100
    
    # 4. Feedback
    col_score, col_msg = st.columns([1, 3])
    
    with col_score:
        st.metric("Readiness Score", f"{score:.0f}%")
        
    with col_msg:
        if score < 30:
            st.warning("⚠️ You have a significant gap. Focus on the top 3 missing skills.")
        elif score < 70:
            st.info("📈 Good foundation! Build 1-2 projects using the missing tools.")
        else:
            st.success("🚀 You are highly competitive! Start applying now.")
            
    # Show missing skills
    missing = [s for s in top_skill_names if s not in user_skills]
    if missing:
        st.write("**Recommended to learn next:**")
        st.write(", ".join(missing[:5]))

# --- RAW DATA VIEW ---
with st.expander("🔎 View Raw JSON Segment"):
    st.json(cat_data)