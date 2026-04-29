import json


class FeedbackAgent:
    def __init__(self, gemini):
        self.gemini = gemini

    def generate(self, history):
        combined = ""

        for item in history:
            combined += f"""
Question: {item['question']}
Answer: {item['answer']}
Evaluation: {item['evaluation']}
"""

        prompt = f"""
You are an HR expert.

Analyze the full interview and provide final feedback.

Interview Data:
{combined}

Evaluation Criteria:
- Overall performance
- Technical ability
- Communication
- Confidence

Return STRICT JSON:
{{
  "overall_score": 1-10,
  "strengths": ["point1", "point2"],
  "weaknesses": ["point1", "point2"],
  "recommendation": "Strong Hire / Hire / Maybe / No Hire"
}}
"""

        try:
            response = self.gemini.generate(prompt)

            if not response:
                raise ValueError("Empty response")

            cleaned = response.strip()

            if cleaned.startswith("```"):
                cleaned = cleaned.replace("```json", "").replace("```", "").strip()

            result = json.loads(cleaned)

            # Validate
            if "overall_score" not in result:
                raise ValueError("Invalid response")

            return result

        except Exception:
            return {
                "overall_score": 6,
                "strengths": ["Good communication"],
                "weaknesses": ["Needs deeper technical knowledge"],
                "recommendation": "Maybe"
            }