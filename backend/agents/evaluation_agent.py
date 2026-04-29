import json


class EvaluationAgent:
    def __init__(self, gemini):
        self.gemini = gemini

    def evaluate(self, question, answer):
        prompt = f"""
You are an expert technical interviewer.

Evaluate the candidate's answer.

Question:
{question}

Answer:
{answer}

Evaluation Criteria:
- Technical accuracy
- Clarity of explanation
- Relevance
- Depth of knowledge

Return STRICT JSON format:
{{
  "score": 1-10,
  "feedback": "short feedback",
  "improvement": "how to improve"
}}
"""

        try:
            response = self.gemini.generate(prompt)

            if not response:
                raise ValueError("Empty response")

            # Clean response (remove markdown if present)
            cleaned = response.strip()

            if cleaned.startswith("```"):
                cleaned = cleaned.replace("```json", "").replace("```", "").strip()

            result = json.loads(cleaned)

            # Validate structure
            if "score" not in result:
                raise ValueError("Invalid response format")

            return result

        except Exception:
            return {
                "score": 5,
                "feedback": "Average answer, could be improved.",
                "improvement": "Try to provide more structured and detailed explanation."
            }