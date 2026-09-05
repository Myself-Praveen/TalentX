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
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beauty
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Geist', -apple-system, sans-serif;
    }
    
    .main-header {
        font-size: 2.2rem;
        font-weight: 600;
        color: #ffffff;
        margin-bottom: 0.5rem;
        letter-spacing: -0.03em;
    }
    .sub-header {
        font-size: 1.1rem;
        font-weight: 400;
        color: #a1a1aa;
        margin-bottom: 2.5rem;
        letter-spacing: -0.01em;
    }
    .highlight-box {
        background: #09090b;
        padding: 1.5rem;
        border-radius: 6px;
        border: 1px solid #27272a;
        border-left: 4px solid #ffffff;
        margin-bottom: 2.5rem;
        color: #e4e4e7;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    [data-testid="stMetricValue"] {
        font-family: 'Geist Mono', monospace;
        font-size: 2.2rem;
        font-weight: 500;
        color: #ffffff;
        letter-spacing: -0.04em;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        color: #a1a1aa;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Minimal card style */
    div[data-testid="metric-container"] {
        background: #09090b;
        border: 1px solid #27272a;
        padding: 1.2rem;
        border-radius: 6px;
    }
    
    /* Remove default Streamlit top padding but leave enough room for header */
    .block-container {
        padding-top: 4rem !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">TalentX PS-3 Benchmark</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Evaluating Tool Call Reliability Under Indian Code-Mixing</p>', unsafe_allow_html=True)

st.markdown("""
<div class="highlight-box">
    <b>Problem Statement:</b> Open-weight models suffer function-calling degradation when inputs switch from English to Hindi or Marathi. This harness quantifies exactly how tool-accuracy drops and latency spikes during a 210-case adversarial collections simulation.
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

st.markdown(f"### {model_choice} Performance Breakdown")

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
        st.subheader(f"{lang.capitalize()}")
        st.metric("Tool Accuracy", f"{tool_acc:.1f}%")
        
        sub_cols = st.columns(2)
        sub_cols[0].metric("Missed Calls", f"{missed_rate:.1f}%")
        sub_cols[1].metric("Spurious Calls", f"{spurious_rate:.1f}%")
        
        if avg_latency > 0:
            st.metric("Avg Latency (TTFT)", f"{avg_latency:.0f} ms")

st.markdown("---")

# Visualizations
st.markdown("### Degradation Visualized")
df_chart = pd.DataFrame(chart_data)
st.bar_chart(
    df_chart.set_index("Language")[["Accuracy (%)", "Missed (%)", "Spurious (%)"]], 
    height=400,
    color=["#3b82f6", "#ef4444", "#f59e0b"]
)

st.markdown("---")
st.markdown("### Raw Evaluation Dataset (Sample)")
df_results = pd.DataFrame(results)
display_cols = [col for col in ['id', 'language', 'utterance', 'expected_tool', 'actual_tool', 'latency_ms'] if col in df_results.columns]
st.dataframe(df_results[display_cols], use_container_width=True)
