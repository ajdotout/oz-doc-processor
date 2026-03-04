import os
import logging
from typing import Literal
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from src.config import CLASSIFIER_MODEL


CLASSIFIER_SYSTEM_PROMPT = """
You are a document classifier for real estate investment documents.

Given the filename and a preview of a document's content, classify it into EXACTLY ONE category:

- om: The main deal document. Offering Memorandums, investor pitch decks, sponsor decks, loan request packages. If the document describes a specific investment opportunity (deal terms, returns, property description, sponsor background), it's an OM. When in doubt, choose this.
- proforma: Financial model or projections spreadsheet. Mostly numerical tables — cash flows, unit economics, construction budgets, HUD worksheets, sensitivity analyses. Very little narrative text.
- research: Context documents about the site or market. Area demographic summaries, market surveys, rent comp tables, feasibility studies, appraisals, architectural/site plans, zoning submittals, elevation drawings, environmental reports.
- supplemental: Miscellaneous notes, emails, cover letters, or anything that doesn't fit the above.

Rules:
1. If a document contains BOTH deal narrative AND sponsor info, classify as om.
2. If a document is primarily financial tables with minimal narrative, classify as proforma.
3. If a document is about the broader market/area/site (not a specific deal), classify as research.
4. When in doubt, classify as om.
"""


class DocumentClassification(BaseModel):
    category: Literal["om", "proforma", "research", "supplemental"]
    reasoning: str = Field(..., description="One sentence explaining why")


class DocumentClassifier:
    def __init__(self, model_name: str = CLASSIFIER_MODEL):
        self.model_name = model_name
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")

        logging.info(f"Initializing classifier with model: {model_name}")
        provider = GoogleProvider(api_key=self.api_key)
        model = GoogleModel(model_name, provider=provider)
        self.agent = Agent(
            model,
            instructions=CLASSIFIER_SYSTEM_PROMPT,
            output_type=DocumentClassification,
        )

    def run(self, filename: str, preview: str) -> DocumentClassification:
        prompt = f"FILENAME: {filename}\n\nPREVIEW:\n{preview or ''}"
        result = self.agent.run_sync(prompt)
        if getattr(result, "output", None) is None:
            raise ValueError(f"Classifier did not return output for {filename}")
        return result.output
