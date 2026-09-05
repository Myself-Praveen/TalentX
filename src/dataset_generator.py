import os
import json
import random
from google import genai
from pydantic import BaseModel
from typing import List, Optional

import os

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable must be set to generate the dataset.")
client = genai.Client(api_key=api_key)

SYSTEM_PROMPT = """
You are generating a test dataset for a collections voice agent evaluation.
You need to generate realistic borrower utterances in a specific language (English, Hinglish, or Marathi).
The utterances should test whether an LLM can correctly identify which tool to call based on the borrower's intent.

Tools available:
1. capture_ptp(promised_amount, promised_date, confidence): Borrower promises to pay.
   - promised_amount: numeric (e.g. 5000)
   - promised_date: MUST be ISO date format YYYY-MM-DD
   - confidence: MUST be one of ["firm", "tentative"]
2. send_payment_link(channel, amount): Borrower asks for a link to pay.
   - channel: MUST be one of ["sms", "whatsapp"]
   - amount: numeric
3. mark_dispute(dispute_type, borrower_statement): Borrower disputes the debt.
   - dispute_type: MUST be one of ["not_mine", "already_paid", "amount_wrong", "other"]
4. escalate_human(reason): Borrower wants a human, is in distress, or abusive.
   - reason: MUST be one of ["borrower_request", "distress", "dispute", "abuse", "out_of_scope"]
5. log_disposition(code, notes): Call ends.
   - code: MUST be one of ["PTP", "PAID", "REFUSED", "DISPUTE", "WRONG_NUMBER", "CALLBACK", "NO_CONTACT", "ESCALATED "]
6. NONE: Borrower says something that doesn't trigger any tool.

Generate realistic, varied, and tricky utterances. Make sure they sound like a real phone call, not robotic.
IMPORTANT: `expected_args` MUST STRICTLY use the enum values specified above. Do not invent your own values for enums.
"""

class TestCase(BaseModel):
    id: str
    language: str
    intent_type: str
    utterance: str
    expected_tool: Optional[str]
    expected_args: Optional[dict]

class DatasetResponse(BaseModel):
    cases: List[TestCase]

def generate_cases(language: str, count: int) -> List[TestCase]:
    prompt = f"""
    Generate {count} test cases in {language}.
    Include a mix of clear intents, ambiguous intents (where NO tool should be called, or it's borderline), and edge cases.
    Ensure strict adherence to the schema.
    Language MUST be "{language}".
    CRITICAL REALISM: Simulate ASR (Automated Speech Recognition) transcription artefacts and phonetic variations. 
    For example, use variations like "pese" vs "paise", "kall" vs "kal", "pachaas hazaar" vs "50k", or slight grammar noise, exactly as a human speaking over a noisy phone line would be transcribed.
    """
    
    prompt += "\nReturn a raw JSON array. DO NOT use markdown code blocks. Each object must have keys: id, language, intent_type, utterance, expected_tool, expected_args."
    prompt += f"\n\nSystem Rules:\n{SYSTEM_PROMPT}"
    
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            break
        except Exception as e:
            if ("503" in str(e) or "429" in str(e)) and attempt < 4:
                print(f"Retrying due to rate limit/503... (attempt {attempt+1})", flush=True)
                time.sleep(15)
            else:
                raise
    
    text = response.text.strip()
    if text.startswith("```json"):
        text = text[7:-3]
    if text.startswith("```"):
        text = text[3:-3]
        
    data = json.loads(text.strip())
    if isinstance(data, dict) and "cases" in data:
        data = data["cases"]
        
    # Coerce id to string to avoid Pydantic validation errors
    for case in data:
        if "id" in case:
            case["id"] = str(case["id"])
        
    return [TestCase(**case) for case in data]

def main():
    languages = ["english", "hinglish", "marathi"]
    cases_per_lang = 70
    
    all_cases = []
    
    for lang in languages:
        print(f"Generating {cases_per_lang} cases for {lang}...", flush=True)
        try:
            cases = generate_cases(lang, cases_per_lang)
            # Assign unique IDs
            for j, case in enumerate(cases):
                case.id = f"{lang[:3]}_{j}"
            all_cases.extend(cases)
        except Exception as e:
            print(f"Failed to generate for {lang}: {e}")
            
        print("Sleeping 60 seconds to avoid API rate limit...", flush=True)
        time.sleep(60)
            
    # Save to JSONL
    output_path = "dataset.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for case in all_cases:
            f.write(case.model_dump_json() + "\n")
            
    print(f"Generated {len(all_cases)} test cases and saved to {output_path}")

if __name__ == "__main__":
    main()
