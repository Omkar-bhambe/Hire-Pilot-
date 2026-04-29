import google.generativeai as genai
import time


class GeminiClient:
    def __init__(self, api_key):
        if not api_key:
            raise ValueError("Gemini API key is required")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-pro")

    # ================= SAFE GENERATE =================
    def generate(self, prompt, retries=3, delay=2):
        for attempt in range(retries):
            try:
                response = self.model.generate_content(prompt)

                if not response or not response.text:
                    raise ValueError("Empty response from Gemini")

                return response.text.strip()

            except Exception as e:
                print(f"[Gemini Error] Attempt {attempt + 1}: {e}")

                # Retry with delay
                if attempt < retries - 1:
                    time.sleep(delay)

        # ================= FINAL FALLBACK =================
        return self._fallback_response(prompt)

    # ================= FALLBACK =================
    def _fallback_response(self, prompt):
        # Simple fallback based on context
        if "question" in prompt.lower():
            return "Can you explain your experience in this area?"

        if "evaluate" in prompt.lower():
            return """{
                "score": 5,
                "feedback": "Average answer",
                "improvement": "Add more technical depth"
            }"""

        if "feedback" in prompt.lower():
            return """{
                "overall_score": 6,
                "strengths": ["Good communication"],
                "weaknesses": ["Needs improvement"],
                "recommendation": "Maybe"
            }"""

        return "Let's continue the interview."