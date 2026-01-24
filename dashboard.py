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
all_categories = list(data['categories'].keys())
# Remove 'Other' from top selection if possible to focus on tech
if 'Other' in all_categories: all_categories.remove('Other')
all_categories.sort()

selected_category = st.sidebar.selectbox("Select Career Path", all_categories)

# --- MAIN DASHBOARD ---

# 1. HIGH LEVEL METRICS
col1, col2, col3 = st.columns(3)
cat_data = data['categories'][selected_category]

with col1:
    st.metric("Job Openings", f"{cat_data['job_count']}")
with col2:
    salary = cat_data.get('salary', {})
    avg_min = salary.get('avg_min', 0)
    avg_max = salary.get('avg_max', 0)
    st.metric("Est. Base Salary (MYR)", f"{avg_min:,.0f} - {avg_max:,.0f}")
with col3:
    st.metric("Market Share", f"{(cat_data['job_count'] / data['total_jobs_analyzed'] * 100):.1f}%")

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
    st.markdown("### ☁️ Keyword Cloud")
    # Generate WordCloud from FREQUENCIES (Much higher quality)
    
    # Merge hard skills + context for a rich cloud
    freq_dict = {}
    for item in hard_skills + context_list:
        freq_dict[item['name']] = item['count']
        
    if freq_dict:
        # Create cloud with better font/background
        wc = WordCloud(
            width=800, 
            height=400, 
            background_color='#0e1117', # Matches Streamlit Dark Mode
            colormap='BuPu',
            prefer_horizontal=0.9
        ).generate_from_frequencies(freq_dict)
        
        fig_wc, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wc, interpolation='bilinear')
        ax.axis("off")
        # Remove whitespace around plot
        plt.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
        st.pyplot(fig_wc)

# --- RAW DATA VIEW ---
with st.expander("🔎 View Raw JSON Segment"):
    st.json(cat_data)