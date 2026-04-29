# database/models/feedback.py
"""
Feedback database model.
Handles all DB operations for the feedback table.
Assumes a PostgreSQL connection available via get_db_connection().
"""
import json
from datetime import datetime
from database.connection import get_db_connection


class Feedback:
    """Database model for interview feedback records."""

    # ─────────────────────────────────────────────
    # Write operations
    # ─────────────────────────────────────────────

    @staticmethod
    def create(feedback_data: dict) -> dict:
        """
        Insert or update a feedback record.
        Uses UPSERT so re-running generate_feedback on the same
        interview_id updates the existing row instead of failing.

        Args:
            feedback_data: dict from FeedbackAgent.generate_feedback()

        Returns:
            The saved feedback row as a dict, or raises on DB error.
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO feedback (
                        interview_id,
                        candidate_email,
                        candidate_name,
                        job_title,
                        overall_score,
                        recommendation,
                        summary,
                        next_steps,
                        strengths,
                        weaknesses,
                        category_scores,
                        per_question_feedback,
                        generated_at,
                        generated_by
                    ) VALUES (
                        %(interview_id)s,
                        %(candidate_email)s,
                        %(candidate_name)s,
                        %(job_title)s,
                        %(overall_score)s,
                        %(recommendation)s,
                        %(summary)s,
                        %(next_steps)s,
                        %(strengths)s,
                        %(weaknesses)s,
                        %(category_scores)s,
                        %(per_question_feedback)s,
                        %(generated_at)s,
                        %(generated_by)s
                    )
                    ON CONFLICT (interview_id) DO UPDATE SET
                        overall_score         = EXCLUDED.overall_score,
                        recommendation        = EXCLUDED.recommendation,
                        summary               = EXCLUDED.summary,
                        next_steps            = EXCLUDED.next_steps,
                        strengths             = EXCLUDED.strengths,
                        weaknesses            = EXCLUDED.weaknesses,
                        category_scores       = EXCLUDED.category_scores,
                        per_question_feedback = EXCLUDED.per_question_feedback,
                        generated_at          = EXCLUDED.generated_at,
                        updated_at            = NOW()
                    RETURNING *
                """, {
                    'interview_id':         feedback_data.get('interview_id'),
                    'candidate_email':      feedback_data.get('candidate_email', ''),
                    'candidate_name':       feedback_data.get('candidate_name', ''),
                    'job_title':            feedback_data.get('job_title', ''),
                    'overall_score':        feedback_data.get('overall_score'),
                    'recommendation':       feedback_data.get('recommendation', 'MAYBE'),
                    'summary':              feedback_data.get('summary', ''),
                    'next_steps':           feedback_data.get('next_steps', ''),
                    'strengths':            json.dumps(feedback_data.get('strengths', [])),
                    'weaknesses':           json.dumps(feedback_data.get('weaknesses', [])),
                    'category_scores':      json.dumps(feedback_data.get('category_scores', {})),
                    'per_question_feedback': json.dumps(feedback_data.get('per_question_feedback', [])),
                    'generated_at':         feedback_data.get('generated_at', datetime.now().isoformat()),
                    'generated_by':         feedback_data.get('generated_by', 'AI'),
                })
                row = cur.fetchone()
                conn.commit()
                return Feedback._row_to_dict(cur, row)
        except Exception as e:
            conn.rollback()
            print(f"Feedback.create DB error: {e}")
            raise
        finally:
            conn.close()

    # ─────────────────────────────────────────────
    # Read operations
    # ─────────────────────────────────────────────

    @staticmethod
    def get_by_interview(interview_id: str) -> dict | None:
        """
        Fetch a single feedback record by interview_id.
        Returns None if not found.
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM feedback WHERE interview_id = %s",
                    (interview_id,)
                )
                row = cur.fetchone()
                return Feedback._row_to_dict(cur, row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_by_candidate(candidate_email: str, limit: int = 50) -> list:
        """
        Fetch all feedback records for a candidate, newest first.
        Returns empty list if none found.
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM feedback
                    WHERE candidate_email = %s
                    ORDER BY generated_at DESC
                    LIMIT %s
                """, (candidate_email, limit))
                rows = cur.fetchall()
                return [Feedback._row_to_dict(cur, r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_summary_stats() -> dict:
        """
        Aggregate stats across all feedback records.
        Used by the admin dashboard summary panel.

        Returns:
            {
                total_feedbacks: int,
                avg_score: float,
                recommendation_breakdown: { HIRE: int, MAYBE: int, REJECT: int },
                top_strengths: list[str],
                top_weaknesses: list[str],
                avg_category_scores: dict
            }
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Overall counts and avg score
                cur.execute("""
                    SELECT
                        COUNT(*)                              AS total,
                        ROUND(AVG(overall_score)::NUMERIC, 2) AS avg_score,
                        SUM(CASE WHEN recommendation = 'HIRE'   THEN 1 ELSE 0 END) AS hire_count,
                        SUM(CASE WHEN recommendation = 'MAYBE'  THEN 1 ELSE 0 END) AS maybe_count,
                        SUM(CASE WHEN recommendation = 'REJECT' THEN 1 ELSE 0 END) AS reject_count
                    FROM feedback
                """)
                row = cur.fetchone()
                total       = row[0] or 0
                avg_score   = float(row[1]) if row[1] else 0.0
                hire_count  = row[2] or 0
                maybe_count = row[3] or 0
                reject_count = row[4] or 0

                # Top strengths — unnest the JSONB array and count occurrences
                cur.execute("""
                    SELECT strength, COUNT(*) AS cnt
                    FROM feedback,
                         jsonb_array_elements_text(strengths) AS strength
                    GROUP BY strength
                    ORDER BY cnt DESC
                    LIMIT 10
                """)
                top_strengths = [r[0] for r in cur.fetchall()]

                # Top weaknesses
                cur.execute("""
                    SELECT weakness, COUNT(*) AS cnt
                    FROM feedback,
                         jsonb_array_elements_text(weaknesses) AS weakness
                    GROUP BY weakness
                    ORDER BY cnt DESC
                    LIMIT 10
                """)
                top_weaknesses = [r[0] for r in cur.fetchall()]

                # Average score per category across all feedback
                cur.execute("""
                    SELECT key, ROUND(AVG(value::FLOAT)::NUMERIC, 2) AS avg_score
                    FROM feedback,
                         jsonb_each_text(category_scores) AS kv(key, value)
                    GROUP BY key
                    ORDER BY key
                """)
                avg_category_scores = {r[0]: float(r[1]) for r in cur.fetchall()}

                return {
                    'total_feedbacks': total,
                    'avg_score':       avg_score,
                    'recommendation_breakdown': {
                        'HIRE':   hire_count,
                        'MAYBE':  maybe_count,
                        'REJECT': reject_count,
                    },
                    'top_strengths':      top_strengths,
                    'top_weaknesses':     top_weaknesses,
                    'avg_category_scores': avg_category_scores,
                }
        finally:
            conn.close()

    @staticmethod
    def get_recent(limit: int = 10) -> list:
        """Fetch the most recently generated feedback records."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM feedback
                    ORDER BY generated_at DESC
                    LIMIT %s
                """, (limit,))
                rows = cur.fetchall()
                return [Feedback._row_to_dict(cur, r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def delete_by_interview(interview_id: str) -> bool:
        """Delete feedback for an interview. Returns True if a row was deleted."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM feedback WHERE interview_id = %s",
                    (interview_id,)
                )
                deleted = cur.rowcount > 0
                conn.commit()
                return deleted
        except Exception as e:
            conn.rollback()
            print(f"Feedback.delete DB error: {e}")
            raise
        finally:
            conn.close()

    # ─────────────────────────────────────────────
    # Private helper
    # ─────────────────────────────────────────────

    @staticmethod
    def _row_to_dict(cur, row) -> dict:
        """Convert a DB row to a plain dict using cursor column names."""
        if row is None:
            return {}
        cols = [desc[0] for desc in cur.description]
        data = dict(zip(cols, row))

        # Parse JSONB fields back to Python objects
        for field in ('strengths', 'weaknesses', 'category_scores', 'per_question_feedback'):
            val = data.get(field)
            if isinstance(val, str):
                try:
                    data[field] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    data[field] = [] if field != 'category_scores' else {}
            elif val is None:
                data[field] = [] if field != 'category_scores' else {}

        # Serialise datetime fields to ISO strings
        for field in ('generated_at', 'created_at', 'updated_at'):
            val = data.get(field)
            if isinstance(val, datetime):
                data[field] = val.isoformat()

        return data