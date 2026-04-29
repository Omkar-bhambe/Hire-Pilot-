import google.generativeai as genai
import json
import re
import time


class OnlineTestAgent:
    def __init__(self, api_key):
        """Initializes the Gemini engine with high-output stability."""
        genai.configure(api_key='AIzaSyAC1S4MNTmwUBUI_3UZoxlfEOUbDFTf8iE')
        # Using the model specified in your existing setup
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def generate_full_test(self, jd_text, q_count):
        """
        Orchestrates Chunked Generation:
        Breaks the total count into sections, and sections into batches of 10.
        """
        q_count = int(q_count)
        base_count = q_count // 3
        remainder = q_count % 3

        sections = [
            {"name": "Aptitude", "count": base_count},
            {"name": "Technical", "count": base_count},
            {"name": "Coding", "count": base_count + remainder}
        ]

        full_test_bank = []
        global_q_index = 10
        chunk_size = 5  # Safe batch size to prevent JSON truncation

        for sec in sections:
            print(f"🤖 HirePilot: Processing {sec['name']} Section ({sec['count']} questions)...")

            section_questions_remaining = sec['count']

            while section_questions_remaining > 0:
                # Determine how many to ask for in this specific API call
                current_batch_count = min(section_questions_remaining, chunk_size)

                print(f"   -> Generating batch of {current_batch_count}...")
                batch_questions = self._generate_batch(jd_text, sec['name'], current_batch_count)

                # Append and re-index
                for q in batch_questions:
                    q['id'] = f"Q{global_q_index}"
                    # Ensure the category/section key is consistent for the UI
                    q['category'] = sec['name']
                    full_test_bank.append(q)
                    global_q_index += 1

                section_questions_remaining -= len(batch_questions)

                # CRITICAL: Respect Rate Limits (RPM)
                if section_questions_remaining > 0 or sec['name'] != "Coding":
                    print("   (Cooldown: Sleeping for 2s to protect Quota)")
                    time.sleep(2)

        return full_test_bank[:q_count]

    def _generate_batch(self, jd_text, section_name, count):
        """Internal helper to generate a small batch of questions."""
        prompt = f"""
You are a Senior Technical Assessment Architect with 15+ years of experience designing hiring assessments for tech companies.

## YOUR MISSION
Analyze the provided Job Description with extreme precision, then craft {count} laser-targeted Multiple Choice Questions for the '{section_name}' assessment section.

## PHASE 1 — DEEP JD ANALYSIS (Internal reasoning, do not output)
Before generating a single question, thoroughly dissect the JD across these dimensions:
- **Core Technical Skills**: Languages, frameworks, tools explicitly required
- **Seniority Signals**: Experience level, ownership expectations, leadership cues
- **Domain Context**: Industry, product type, system scale (e.g., distributed, real-time, B2B)
- **Hidden Requirements**: Inferred skills from responsibilities (e.g., "owns deployment" → CI/CD knowledge)
- **Priority Weighting**: Distinguish "must-have" vs "nice-to-have" skills — bias questions toward must-haves
- **Red Flags to Test**: Common failure points for this exact role

## PHASE 2 — QUESTION GENERATION STRATEGY
Apply these rules when crafting questions:
- **Relevance**: Every question must map to a specific skill, tool, or concept extracted from the JD
- **No Generic Questions**: Avoid textbook questions that could belong to any job — anchor each to the role's context
- **Distractor Quality**: Wrong options must be plausible — use common misconceptions, off-by-one patterns, or near-correct alternatives
- **Real-World Framing**: Prefer scenario-based questions ("Given a microservices architecture as described in the role...") over pure theory
- **Difficulty Calibration**: Match difficulty to the seniority level inferred from the JD
- **Coding Questions** (if applicable): Use clean, realistic code snippets in backticks — test patterns actually used in this stack

## JOB DESCRIPTION
\"\"\"
{jd_text}
\"\"\"

## OUTPUT RULES — STRICT
1. Return ONLY a valid JSON array. No preamble, no explanation, no markdown fences.
2. Every question must be traceable to something in the JD above.
3. Vary question types: conceptual, scenario-based, debugging, best-practice, tool-specific.

## OUTPUT SCHEMA
[
  {{
    "id": "temp",
    "category": "{section_name}",
    "question": "...",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "correct": 0,
    "difficulty": "easy | medium | hard"
  }}
]

- "correct" → 0-indexed integer pointing to the right option in "options"
- "difficulty" → calibrated to the role seniority, not generic
- Aim for a mix: ~20% easy, ~60% medium, ~20% hard (unless section demands otherwise)
"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": 4096,
                    "response_mime_type": "application/json"
                }
            )

            json_text = response.text.strip()
            # Clean Markdown if present
            if json_text.startswith("```"):
                json_text = re.sub(r'^```json\s*|```$', '', json_text, flags=re.MULTILINE).strip()

            return json.loads(json_text)

        except Exception as e:
            print(f"❌ Batch Error ({section_name}): {e}")
            return []

    def calculate_score(self, user_answers, test_bank):
        """
        Calculates final score by aligning frontend 'q0' keys
        with backend 'Q1' IDs and matching option strings to indices.
        """
        if not test_bank:
            return 0

        correct_count = 0
        total_questions = len(test_bank)

        for idx, q in enumerate(test_bank):
            # 1. Align Keys: Frontend sends 'q0', 'q1'...
            # But Firestore question ID is 'Q1', 'Q2'...
            frontend_key = f"q{idx}"

            if frontend_key in user_answers:
                selected_text = user_answers[frontend_key]
                correct_index = q.get('correct')  # e.g., 3
                options = q.get('options', [])

                try:
                    # 2. Match the selected text to its index in the options list
                    # We strip whitespace to ensure a perfect match
                    if selected_text in options:
                        selected_index = options.index(selected_text)

                        if selected_index == correct_index:
                            correct_count += 1
                            print(f"✅ Question {idx + 1}: Correct")
                        else:
                            print(f"❌ Question {idx + 1}: Wrong (Got {selected_index}, Need {correct_index})")
                except Exception as e:
                    print(f"⚠️ Error matching question {idx}: {e}")
                    continue

        final_score = round((correct_count / total_questions) * 100, 2)
        print(f"📊 Final Calculation: {correct_count}/{total_questions} = {final_score}%")
        return final_score