from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import date

class CapturePTP(BaseModel):
    """Record a promise to pay made by the borrower."""
    promised_amount: float = Field(..., description="The amount promised by the borrower.")
    promised_date: date = Field(..., description="The date the promise is made for.")
    confidence: Optional[Literal["firm", "tentative"]] = Field(None, description="The confidence level of the promise.")

class SendPaymentLink(BaseModel):
    """Send a payment link over SMS or WhatsApp."""
    channel: Literal["sms", "whatsapp"] = Field(..., description="The channel to send the link through.")
    amount: float = Field(..., description="The amount for the payment link.")

class MarkDispute(BaseModel):
    """Borrower disputes the debt. Halts recovery."""
    dispute_type: Literal["not_mine", "already_paid", "amount_wrong", "other"] = Field(..., description="The type of dispute.")
    borrower_statement: Optional[str] = Field(None, description="The statement made by the borrower.")

class EscalateHuman(BaseModel):
    """Transfer to a human agent."""
    reason: Literal["borrower_request", "distress", "dispute", "abuse", "out_of_scope"] = Field(..., description="The reason for escalation.")

class LogDisposition(BaseModel):
    """Record the outcome of the call."""
    code: Literal["PTP", "PAID", "REFUSED", "DISPUTE", "WRONG_NUMBER", "CALLBACK", "NO_CONTACT", "ESCALATED"] = Field(..., description="The outcome code.")
    notes: Optional[str] = Field(None, description="Additional notes regarding the disposition.")
