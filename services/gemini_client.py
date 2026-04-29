import os
import json
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging

logger = logging.getLogger(__name__)

# Use gemini-1.5-flash: It has the highest free limits (15 RPM / 1M TPM)
MODEL_NAME = 'gemini-2.5-flash'
genai.configure(api_key=os.getenv("AIzaSyCuLV-6RKIcpv23wKJGMrvs9syjujeLpvU"))
model = genai.GenerativeModel(MODEL_NAME)

class GeminiQuotaError(Exception):
    """Custom exception for rate limits."""
    pass

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=10, max=60), # Starts at 10s, grows to 60s
    retry=retry_if_exception_type(GeminiQuotaError)
)
def get_gemini_response(prompt: str, is_json: bool = False):
    try:
        config = {"response_mime_type": "application/json"} if is_json else {}
        response = model.generate_content(prompt, generation_config=config)
        return response.text
    except Exception as e:
        # Check if the error is a Quota/Rate Limit error (Code 429)
        if "429" in str(e) or "quota" in str(e).lower():
            logger.warning("Quota reached. Agentic backoff triggered... waiting to retry.")
            raise GeminiQuotaError("Gemini Rate Limit Hit")
        raise e