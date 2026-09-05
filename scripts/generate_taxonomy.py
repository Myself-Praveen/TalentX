import json
import os
import argparse
from google import genai
from google.genai import types


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True, help="Model to generate taxonomy for (e.g., qwen3_5_4b)")
    args = parser.parse_args()
    
    safe_model = args.model.replace(":", "_").replace(".", "_").replace("-", "_")
    result_file = f"eval_results_{safe_model}.json"
    
    if not os.path.exists(result_file):
        print(f"Results file {result_file} not found.")
        return
        
    with open(result_file, "r", encoding="utf-8") as f:
        results = json.load(f)
        
    failed_cases = [r for r in results if r["expected_tool"] != r["actual_tool"] or r["error"]]
    
    if not failed_cases:
        print("No failures to analyze!")
        return
        
    print(f"Found {len(failed_cases)} failures. Requesting Error Taxonomy from Gemini...")
    
    # We will sample up to 50 failures to avoid context limits
    sample = failed_cases[:50]
    
    prompt = f"""
    Analyze the following failed test cases from a collections agent voice-bot evaluation.
    Create a highly structured "Error Taxonomy" — categorize the recurring shapes of failure (e.g., "Script Inconsistency", "Date Hallucination", "Spurious Calls on Ambiguity").
    For each category, provide a brief explanation and one or two examples from the data.
    Focus especially on issues related to Hinglish/Marathi if you spot them.
    
    Failed Cases Data (JSON):
    {json.dumps(sample, indent=2)}
    """
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY environment variable not set. Cannot generate taxonomy.")
        return
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    
    out_file = f"taxonomy_{safe_model}.md"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(f"# Error Taxonomy for {args.model}\n\n")
        f.write(response.text)
        
    print(f"Saved Error Taxonomy to {out_file}")

if __name__ == "__main__":
    main()
