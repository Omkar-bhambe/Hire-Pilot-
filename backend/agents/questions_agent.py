class QuestionAgent:
    def __init__(self, gemini):
        self.gemini = gemini

    # ================= FIRST QUESTION =================
    def first_question(self, job_description, resume):
        prompt = f"""
You are a friendly AI interviewer.

Generate the FIRST interview question based on:

Job Description:
{job_description}

Candidate Resume:
{resume}

Rules:
- Ask a simple opening question
- Keep it conversational
- Do NOT ask multiple questions
- Return only the question text
"""

        return self._safe_generate(prompt)

    # ================= NEXT QUESTION =================
    def next_question(self, job_description, resume, previous_q, answer, history):
        prompt = f"""
You are a smart AI interviewer.

Generate the NEXT interview question.

Context:
Job Description: {job_description}
Resume: {resume}

Previous Question:
{previous_q}

Candidate Answer:
{answer}

Conversation History:
{history}

Rules:
- Ask a relevant follow-up OR new question
- Increase difficulty gradually
- If answer is weak → simplify
- If strong → ask deeper question
- Ask ONLY ONE question
"""

        return self._safe_generate(prompt)

    # ================= SAFE CALL =================
    def _safe_generate(self, prompt):
        try:
            response = self.gemini.generate(prompt)

            if not response or len(response.strip()) < 5:
                return "Can you explain that in more detail?"

            return response.strip()

        except Exception:
            return "Let's move to the next question. Can you tell me about your experience?"