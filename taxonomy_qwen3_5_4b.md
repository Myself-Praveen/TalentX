# Error Taxonomy for qwen3.5:4b

The analysis of the failed test cases reveals several recurring patterns in how the voice-bot misinterprets user intent and actions. These failures range from complete inaction to misclassifying the severity or type of user request, often exhibiting specific challenges with multilingual input (Hinglish/Marathi).

Here's a highly structured Error Taxonomy:

---

### Error Taxonomy for Collections Agent Voice-Bot

**1. Missing Intent Fulfillment (No Action Taken)**
*   **Explanation:** The bot completely fails to identify any relevant user intent and, consequently, does not execute any tool, even when a clear action was expected. This indicates a significant breakdown in intent recognition or a lack of confidence in identified intent. This can stem from NLU limitations, poor speech-to-text accuracy, or overly strict confidence thresholds.
*   **Examples:**
    *   `eng_17`: Expected `capture_ptp` (promise to pay 10000 on "25th"), Actual `NONE`.
    *   `mar_160`: Expected `mark_dispute` ("already paid" in Marathi), Actual `NONE`. This highlights a potential NLU gap for dispute intent in Marathi.

**2. Intent Misclassification - Granularity & Severity**
*   **Explanation:** The bot identifies an intent related to the user's request but misjudges its severity, urgency, or specificity. It selects a tool that is less appropriate (e.g., too general, too specific, or insufficient for handling the urgency) than the expected one. This often leads to under-escalation or less actionable logging.
*   **Examples:**
    *   `eng_28`: Expected `escalate_human` (borrower has legal representation), Actual `mark_dispute`. The bot recognized a legal issue but failed to escalate it, opting for a lower-severity dispute log.
    *   `hin_92`: Expected `escalate_human` (legal escalation with RBI/lawyer in Hinglish), Actual `mark_dispute`. The bot identified a legal complaint but under-classified its critical nature, which clearly warrants human intervention. The complexity of the Hinglish utterance might have contributed to this misclassification.

**3. Intent Misclassification - Confused Action Semantics**
*   **Explanation:** The bot confuses two distinct actions that, while potentially related in a user journey or workflow, represent fundamentally different user intents or system operations. This points to an overlap in the bot's semantic understanding.
*   **Examples:**
    *   `eng_8`: Expected `send_payment_link` (amount 2500), Actual `capture_ptp` (amount 2500, date "2024-12-19"). The bot interpreted a request for a payment link as the user making a promise to pay.
    *   `hin_95`: Expected `capture_ptp` (promise to pay 4000 "tomorrow afternoon"), Actual `send_payment_link` (whatsapp, amount 4000). The bot directly sent a payment link instead of first capturing the promise to pay, confusing the sequence of actions.

**4. Spurious Tool Execution (Unwarranted Action)**
*   **Explanation:** The bot executes a tool when the user's utterance did not warrant any specific tool call, or when the expected action was explicitly `NONE`. This suggests over-eagerness, hallucination of an intent, or an incorrect default behavior.
*   **Examples:**
    *   `eng_10`: Expected `NONE`, Actual `escalate_human` (borrower in financial distress). While genuine distress might *eventually* lead to escalation, no immediate tool call was expected.
    *   `hin_81`: Expected `NONE`, Actual `mark_dispute` (debt_refusal, "Main nahi bhar raha, jo ukhadna hai ukhad lo."). The bot correctly identified the refusal (albeit aggressive Hinglish), but acted when no specific tool call was expected by the evaluation.
    *   `hin_109`: Expected `NONE`, Actual `escalate_human` (borrower expressing genuine financial distress). Similar to `eng_10`, the bot reacted to distress with an unmandated escalation.

**5. Argument Extraction & Hallucination**
*   **Explanation:** The bot identifies a tool (even if misclassified or spurious) but then either fails to extract necessary parameters (like amount, date, channel) from the user's utterance or hallucinates and generates incorrect parameter values not explicitly mentioned by the user.
*   **Examples:**
    *   `hin_138`: Expected `NONE`, Actual `capture_ptp` (promised_amount 2000, promised_date "2025-06-18", confidence "tentative"). Here, the primary error is spurious tool execution, but the specific date "2025-06-18" is highly likely to be a date hallucination if the borrower did not explicitly state it within the conversation.

---

### Observations on Hinglish/Marathi Specific Issues:

*   **Prevalence of "Missing Intent Fulfillment" in Marathi:** A significant number of Marathi cases (`mar_142`, `mar_143`, `mar_144`, `mar_150`, `mar_151`, `mar_157`, `mar_160`) result in `NONE` when specific actions like `capture_ptp` or `send_payment_link` were expected. This suggests a core NLU weakness in Marathi for accurately identifying and parsing these critical collections intents and their associated arguments. `mar_160` (dispute of "already paid") is a clear case of complete failure to comprehend the Marathi statement.
*   **Severity Misjudgment in Hinglish:** Hinglish cases (`hin_72`, `hin_75`, `hin_86`, `hin_89`, `hin_92`, `hin_102`, `hin_125`, `hin_128`) frequently fall under `Intent Misclassification - Granularity & Severity`. The bot often opts for a generic `log_disposition` or `mark_dispute` instead of the more specific and actionable `capture_ptp` or `escalate_human`. This indicates a struggle with understanding the nuances, urgency, and specific implications conveyed through code-switching, colloquialisms, and more direct or aggressive phrasing common in Hinglish, leading to under-classification of critical situations like legal threats or explicit promises to pay.
    *   For example, `hin_92` involves complex Hinglish describing legal escalation (RBI ombudsman, lawyer, legal department), which the bot failed to interpret as a direct call for human escalation.
    *   Similarly, `hin_81` ("Main nahi bhar raha, jo ukhadna hai ukhad lo.") is a strong, defiant refusal that the bot did detect as a "debt_refusal" dispute, but the expected outcome was `NONE`, highlighting a mismatch in the bot's handling of aggressive language.