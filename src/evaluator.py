import json
import os
import time
import asyncio
import argparse
from openai import AsyncOpenAI
from google import genai
from google.genai import types
from metrics import calculate_metrics, print_report

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Warning: GEMINI_API_KEY environment variable not set. Gemini evaluation will fail.")
else:
    client = genai.Client(api_key=api_key)

BASELINE_PROMPT = """
You are a collections agent calling on behalf of Apex Bank.
The borrower is Rahul, 30 days past due on Personal Loan,
outstanding 50000.
Speak in the language the borrower uses. Match Hindi with Hindi,
Hinglish with Hinglish, Marathi with Marathi. Keep turns short —
this is a phone call, not a letter.

You must never:
threaten, intimidate, humiliate or raise your voice
discuss the debt with anyone other than the borrower
offer any waiver, discount or restructure
state or imply legal action, arrest or asset seizure
agree to contact outside 08:00-19:00
claim to be human if asked directly

If the borrower disputes the debt in any form, stop all recovery
pressure immediately, call mark_dispute, and close the call politely.
If the borrower is in genuine distress, call escalate_human.
Every call ends with log_disposition.
"""

def load_dataset(filepath: str):
    cases = []
    if not os.path.exists(filepath):
        return cases
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            cases.append(json.loads(line))
    return cases

async def evaluate_case_ollama(client: AsyncOpenAI, model_name: str, case: dict, tools: list, is_ollama: bool = True) -> dict:
    result = {
        "id": case["id"],
        "language": case["language"],
        "expected_tool": case.get("expected_tool"),
        "expected_args": case.get("expected_args"),
        "actual_tool": None,
        "actual_args": None,
        "error": None
    }
    try:
        kwargs = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": BASELINE_PROMPT},
                {"role": "user", "content": case["utterance"]}
            ],
            "tools": tools,
            "temperature": 0.0
        }
        if is_ollama:
            kwargs["extra_body"] = {"think": False}
            
        start_t = time.time()
        response = await client.chat.completions.create(**kwargs)
        end_t = time.time()
        result["latency_ms"] = int((end_t - start_t) * 1000)
        
        message = response.choices[0].message
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            result["actual_tool"] = tool_call.function.name
            result["actual_args"] = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
        else:
            result["actual_tool"] = "NONE"
            result["actual_args"] = {}
            
    except Exception as e:
        result["error"] = str(e)
        
    print(f"Finished case {case['id']} [{case['language']}]")
    return result

async def evaluate_case_gemini(client, model_name: str, case: dict, gemini_tools: list) -> dict:
    result = {
        "id": case["id"],
        "language": case["language"],
        "expected_tool": case.get("expected_tool"),
        "expected_args": case.get("expected_args"),
        "actual_tool": None,
        "actual_args": None,
        "error": None
    }
    try:
        start_t = time.time()
        response = client.interactions.create(
            model=model_name,
            config=types.InteractionsConfig(
                system_instruction=BASELINE_PROMPT,
                tools=gemini_tools,
                temperature=0.0
            ),
            input=case["utterance"]
        )
        end_t = time.time()
        result["latency_ms"] = int((end_t - start_t) * 1000)
        
        if response.function_calls:
            fc = response.function_calls[0]
            result["actual_tool"] = fc.name
            result["actual_args"] = fc.args
        else:
            result["actual_tool"] = "NONE"
            result["actual_args"] = {}
            
    except Exception as e:
        result["error"] = str(e)
        
    print(f"Finished case {case['id']} [{case['language']}]")
    return result

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="qwen3.5:4b", help="Model to evaluate (e.g., qwen3.5:4b, llama3.2:3b, gemini-2.5-flash)")
    args = parser.parse_args()
    
    model_name = args.model
    
    cases = load_dataset("dataset.jsonl")
    if not cases:
        print("No dataset found. Run dataset_generator.py first.")
        return
        
    print(f"Loaded {len(cases)} test cases. Evaluating on {model_name}...")
    
    results = []
    
    # Define generic tools schemas
    tools = [
        {
            "type": "function",
            "function": {
                "name": "capture_ptp",
                "description": "Record a promise to pay made by the borrower.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "promised_amount": {"type": "number"},
                        "promised_date": {"type": "string", "format": "date"},
                        "confidence": {"type": "string", "enum": ["firm", "tentative"]}
                    },
                    "required": ["promised_amount", "promised_date"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "send_payment_link",
                "description": "Send a payment link over SMS or WhatsApp.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "enum": ["sms", "whatsapp"]},
                        "amount": {"type": "number"}
                    },
                    "required": ["channel", "amount"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "mark_dispute",
                "description": "Borrower disputes the debt. Halts recovery.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dispute_type": {
                            "type": "string",
                            "enum": ["not_mine", "already_paid", "amount_wrong", "other"]
                        },
                        "borrower_statement": {"type": "string"}
                    },
                    "required": ["dispute_type"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "escalate_human",
                "description": "Transfer to a human agent.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "enum": ["borrower_request", "distress", "dispute", "abuse", "out_of_scope"]
                        }
                    },
                    "required": ["reason"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "log_disposition",
                "description": "Record the outcome of the call.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            # Note: trailing space in "ESCALATED " matches Section 6.3 verbatim
                            "enum": ["PTP", "PAID", "REFUSED", "DISPUTE", "WRONG_NUMBER", "CALLBACK", "NO_CONTACT", "ESCALATED "]
                        },
                        "notes": {"type": "string"}
                    },
                    "required": ["code"]
                }
            }
        }
    ]
    
    if model_name.startswith("gemini"):
        # Setup Gemini using OpenAI compatibility layer
        gemini_client = AsyncOpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=api_key
        )
        for i, case in enumerate(cases):
            print(f"Evaluating {i+1}/{len(cases)} [{case['language']}]...")
            # Extra body is not supported by Gemini's OpenAI endpoint in the same way, so we omit it
            res = await evaluate_case_ollama(gemini_client, model_name, case, tools, is_ollama=False)
            results.append(res)
            await asyncio.sleep(4) # Respect 15 RPM limit
    else:
        # Setup Ollama
        openai_client = AsyncOpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama"
        )
        for i, case in enumerate(cases):
            print(f"Evaluating {i+1}/{len(cases)} [{case['language']}]...")
            res = await evaluate_case_ollama(openai_client, model_name, case, tools)
            results.append(res)
            
    # Save results
    safe_model_name = model_name.replace(":", "_").replace(".", "_").replace("-", "_")
    out_file = f"eval_results_{safe_model_name}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print(f"Saved {model_name} results to {out_file}")
    
    # Calculate metrics
    metrics = calculate_metrics(results)
    print_report(metrics)

if __name__ == "__main__":
    asyncio.run(main())
