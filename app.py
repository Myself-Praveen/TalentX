import streamlit as st
import json
import pandas as pd
import os
import sys

# Ensure src is in the path so we can import metrics
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from src.metrics import calculate_metrics
except ImportError:
    st.error("Could not import metrics. Make sure this is running in the root of the TalentX repo.")
    st.stop()

# Page Config
st.set_page_config(
    page_title="Guardrail Gauntlet | PS-3 Benchmark",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beauty
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        font-size: 3rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0rem;
        letter-spacing: -1px;
    }
    .sub-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #8892B0;
        margin-bottom: 2rem;
    }
    .highlight-box {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        padding: 2rem;
        border-radius: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-left: 6px solid #4ECDC4;
        margin-bottom: 2.5rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.1);
        color: #CCD6F6;
        font-size: 1.1rem;
        line-height: 1.6;
    }
    [data-testid="stMetricValue"] {
        font-size: 2.5rem;
        font-weight: 800;
        color: #E6F1FF;
    }
    [data-testid="stMetricLabel"] {
        font-size: 1.1rem;
        color: #8892B0;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Style the metric containers as cards */
    div[data-testid="metric-container"] {
        background: rgba(17, 34, 64, 0.4);
        border: 1px solid rgba(255,255,255,0.05);
        padding: 1.5rem;
        border-radius: 0.8rem;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        border-color: #4ECDC4;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">🛡️ The Guardrail Gauntlet (PS-3)</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Evaluating Open-Weight Tool Calls Under Code-Mixing (Hinglish/Marathi)</p>', unsafe_allow_html=True)

st.markdown("""
<div class="highlight-box">
    <b>Problem Statement:</b> Open-weight models (Qwen, Llama) suffer function-calling degradation when borrowers switch from English to Hindi/Marathi. This dashboard quantifies the exact tool-accuracy drop and latency spikes under a 210-case adversarial collections simulation.
</div>
""", unsafe_allow_html=True)


@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Sidebar
st.sidebar.title("Model Selection")
model_choice = st.sidebar.radio(
    "Choose a model to analyze:",
    ["Qwen 3.5 (4B)", "Llama 3.2 (3B)"]
)

st.sidebar.markdown("---")
st.sidebar.info("This is a static presentation dashboard of the local evaluation harness results.")

file_map = {
    "Qwen 3.5 (4B)": "eval_results_qwen3_5_4b.json",
    "Llama 3.2 (3B)": "eval_results_llama3_2_3b.json"
}

results = load_data(file_map[model_choice])

if not results:
    st.warning(f"Result file for {model_choice} not found. Ensure `{file_map[model_choice]}` is in the repository root.")
    st.stop()

# Calculate Metrics
metrics = calculate_metrics(results)

# Display Metrics for Languages
languages = ["english", "hinglish", "marathi"]

# Setup Data for charts
chart_data = []

st.markdown(f"### ⚡ {model_choice} Performance Breakdown")

cols = st.columns(3)
for i, lang in enumerate(languages):
    m = metrics[lang]
    total = m["total"]
    if total == 0:
        continue
        
    tool_acc = (m["correct_tool"] / total) * 100
    missed_rate = (m["missed"] / total) * 100
    spurious_rate = (m["spurious"] / total) * 100
    wrong_tool_rate = (m["wrong_tool"] / total) * 100
    avg_latency = (m["total_latency"] / m["latency_count"]) if m["latency_count"] > 0 else 0
    
    chart_data.append({
        "Language": lang.capitalize(),
        "Accuracy (%)": tool_acc,
        "Missed (%)": missed_rate,
        "Spurious (%)": spurious_rate
    })

    with cols[i]:
        st.subheader(f"🗣️ {lang.capitalize()}")
        st.metric("Tool Accuracy", f"{tool_acc:.1f}%")
        
        sub_cols = st.columns(2)
        sub_cols[0].metric("Missed Calls", f"{missed_rate:.1f}%")
        sub_cols[1].metric("Spurious Calls", f"{spurious_rate:.1f}%")
        
        if avg_latency > 0:
            st.metric("Avg Latency (TTFT)", f"{avg_latency:.0f} ms")

st.markdown("---")

# Visualizations
st.markdown("### 📉 Degradation Visualized")
df_chart = pd.DataFrame(chart_data)
st.bar_chart(df_chart.set_index("Language")[["Accuracy (%)", "Missed (%)", "Spurious (%)"]], height=400)

st.markdown("---")
st.markdown("### 🔍 Raw Evaluation Dataset (Sample)")
df_results = pd.DataFrame(results)
display_cols = ['id', 'language', 'utterance', 'expected_tool', 'actual_tool']
if 'latency_ms' in df_results.columns:
    display_cols.append('latency_ms')
st.dataframe(df_results[display_cols], use_container_width=True)
