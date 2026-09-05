# Predixion AI | TalentX - PS-3 Submission (Tool Calls Under Code-Mixing)

## Problem
A collections voice agent needs to perform precise structured tool calls (e.g., `capture_ptp`, `escalate_human`) to be functional in a real-world scenario. However, in India, borrowers often speak in code-mixed languages like Hinglish and Marathi. The problem is that open-weight models suffer from degraded function-calling reliability when prompted in non-English languages. A missed `capture_ptp` is lost revenue. 

## Live Dashboard
The evaluation results have been visualized in an interactive, production-grade Streamlit dashboard. 
**Access the live demo here:** [https://c35wdubkb9a6vazfqtpvyc.streamlit.app/](https://c35wdubkb9a6vazfqtpvyc.streamlit.app/)

## Approach
We built a robust, automated evaluation harness in Python to measure the delta in tool-calling accuracy between English, Hinglish, and Marathi under local, open-weight conditions.
1. **Adversarial Dataset Synthesis**: We synthesized a 210-case JSONL dataset containing realistic borrower utterances (sustained abuse, ambiguous statements, threats, requests to contact family) mapped to the 5 official Section 6.3 tools.
2. **Local Evaluation Harness**: We built an async evaluation loop that injects the official baseline prompt (Section 6.4) and strict JSON schemas, testing against local Ollama inference (`qwen3.5:4b` and `llama3.2:3b`).
3. **Metrics Engine**: We compute the correct-tool rate, malformed-arguments rate, spurious calls, and missed calls to produce a clear English-vs-Indic degradation delta.
4. **Error Taxonomy**: We categorized the recurring shapes of failures (e.g., Tool Activation Failure, Hallucinated Enums) to understand *how* the models fail.

## Tech Stack
- **Python 3**: Core language.
- **Ollama**: Local inference engine for `qwen3.5:4b` and `llama3.2:3b` with 16GB RAM constraints.
- **google-genai**: Used for evaluating the baseline frontier model and generating the dataset.

## How to Run & Reproduce
1. Ensure your Python virtual environment is active: `.venv\Scripts\activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Ensure you have [Ollama](https://ollama.com/) installed and running locally.
4. Pull the required models:
   ```bash
   ollama pull qwen3.5:4b
   ollama pull llama3.2:3b
   ```
   *Note: Qwen 3.5's "thinking mode" must be disabled for the voice-loop latency requirement. The evaluator handles this automatically via the `extra_body={"think": False}` parameter in the API call.*
5. Set your Gemini API key (only required for dataset/taxonomy generation, or evaluating the baseline):
   ```powershell
   $env:GEMINI_API_KEY="your_api_key_here"
   ```
   *Note: The test suite (`dataset.jsonl`) is pre-generated and checked into the repository. You do NOT need a Gemini API key to run the local open-weight model evaluations.*
6. **Run the evaluation**:
   ```bash
   python src/evaluator.py --model qwen3.5:4b
   python src/evaluator.py --model llama3.2:3b
   ```
   *Note: Results are automatically saved to `eval_results_<model>.json`.*
7. **Generate Error Taxonomy** (requires Gemini API Key):
   ```bash
   python scripts/generate_taxonomy.py --model qwen3.5:4b
   ```

## Results & Insights
Read the comprehensive findings, metrics, and limitations in **[ps3_report.md](ps3_report.md)**.
