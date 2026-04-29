"""
Interview state schema and types for LangGraph conversation flow.
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class QuestionTurn:
    """Single Q/A turn in the interview."""
    question_id:        int
    question_text:      str
    category:           str
    difficulty:         str
    intent:             str
    follow_ups:         List[str]
    expected_time_sec:  int
    asked_at:           str

    # Answer fields
    answer_text:           Optional[str]   = None
    answer_duration:       int             = 0
    answered_at:           Optional[str]   = None
    answer_score:          Optional[float] = None
    answer_feedback:       Optional[str]   = None
    interviewer_response:  Optional[str]   = None

    # ✅ Follow-up tracking
    is_followup:           bool            = False   # True if this turn is a follow-up
    parent_question_id:    Optional[int]   = None    # Which question triggered this follow-up
    followup_count:        int             = 0       # How many follow-ups have been asked for the parent

    # ✅ Emotion context at time of question
    emotion_at_ask:        Optional[str]   = None    # Emotion detected when question was asked


@dataclass
class InterviewState:
    """
    Central state for the adaptive interview conversation.
    Managed and passed through LangGraph agents.
    """
    # Metadata
    interview_id:     str
    candidate_name:   str
    candidate_email:  str
    job_description:  str
    resume_text:      str
    created_at:       str

    # Interview control
    status:                  str  = 'created'   # created | in_progress | paused | completed | auto_submitted
    mode:                    str  = 'ai'         # ai | manual
    current_question_index:  int  = 0
    max_questions:           int  = 999          # No fixed limit; time-based (30 min)
    question_turns:          List[QuestionTurn]  = field(default_factory=list)

    # Conversation history (for Gemini context window)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)

    # Evaluation
    answer_scores:   List[float]        = field(default_factory=list)
    category_scores: Dict[str, Any]     = field(default_factory=dict)
    overall_score:   Optional[float]    = None

    # ✅ Follow-up control
    # Tracks how many follow-ups have been asked per parent question index
    followup_counts: Dict[int, int]     = field(default_factory=dict)
    max_followups:   int                = 2      # Max follow-ups per weak answer before moving on

    # ✅ Weak answer threshold (score out of 10)
    weak_answer_threshold:   float = 5.0   # Below this → trigger follow-up
    strong_answer_threshold: float = 7.5   # Above this → escalate difficulty

    # Proctoring
    violations:    List[Dict[str, Any]] = field(default_factory=list)
    warning_count: int                  = 0
    max_warnings:  int                  = 3

    # Emotion tracking
    emotion_timeline:  List[Dict[str, Any]] = field(default_factory=list)
    dominant_emotions: List[str]            = field(default_factory=list)
    current_emotion:   Optional[str]        = None   # ✅ Latest detected emotion

    # Face detection
    face_detection_logs: List[Dict[str, Any]] = field(default_factory=list)

    # Personality
    personality: str = 'friendly'   # friendly | neutral

    # Timestamps
    started_at:   Optional[str] = None
    completed_at: Optional[str] = None

    # ✅ 30-minute timer
    interview_duration_minutes: int          = 30
    time_warning_sent:          bool         = False   # True once the 5-min warning has been emitted

    # Flags
    interview_ended_early:  bool          = False
    auto_submitted_reason:  Optional[str] = None

    # ─────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────

    def elapsed_minutes(self) -> Optional[float]:
        """Return minutes elapsed since interview started. None if not started."""
        if not self.started_at:
            return None
        try:
            start = datetime.fromisoformat(self.started_at)
            return (datetime.now() - start).total_seconds() / 60
        except (ValueError, TypeError):
            return None

    def is_time_expired(self) -> bool:
        """Return True if the 30-minute limit has been reached."""
        elapsed = self.elapsed_minutes()
        if elapsed is None:
            return False
        return elapsed >= self.interview_duration_minutes

    def minutes_remaining(self) -> Optional[float]:
        """Return minutes remaining. None if not started."""
        elapsed = self.elapsed_minutes()
        if elapsed is None:
            return None
        return max(0.0, self.interview_duration_minutes - elapsed)

    def last_score(self) -> Optional[float]:
        """Return the most recent answer score, or None."""
        return self.answer_scores[-1] if self.answer_scores else None

    def recent_avg_score(self, n: int = 3) -> Optional[float]:
        """Return the average of the last n scores, or None if no scores."""
        recent = self.answer_scores[-n:]
        return sum(recent) / len(recent) if recent else None

    def current_parent_question_index(self) -> int:
        """
        Return the index of the current 'parent' (non-follow-up) question.
        Used to track how many follow-ups have been asked for it.
        """
        for turn in reversed(self.question_turns):
            if not turn.is_followup:
                return turn.question_id
        return 0

    def followups_asked_for_current(self) -> int:
        """Return how many follow-ups have been asked for the current parent question."""
        parent_idx = self.current_parent_question_index()
        return self.followup_counts.get(parent_idx, 0)

    def should_ask_followup(self) -> bool:
        """
        Return True if the last answer was weak enough to warrant a follow-up
        AND we haven't hit the max follow-up limit for this question.
        """
        score = self.last_score()
        if score is None:
            return False
        if score >= self.weak_answer_threshold:
            return False
        return self.followups_asked_for_current() < self.max_followups

    def current_difficulty(self) -> str:
        """
        Dynamically adapt difficulty based on recent performance.
        - avg >= strong_threshold  → hard
        - avg <= weak_threshold    → easy
        - otherwise                → medium
        """
        avg = self.recent_avg_score()
        if avg is None:
            return 'medium'
        if avg >= self.strong_answer_threshold:
            return 'hard'
        if avg <= self.weak_answer_threshold:
            return 'easy'
        return 'medium'

    # ─────────────────────────────────────────────
    # Serialisation
    # ─────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            'interview_id':               self.interview_id,
            'candidate_name':             self.candidate_name,
            'candidate_email':            self.candidate_email,
            'job_description':            self.job_description,
            'resume_text':                self.resume_text,
            'created_at':                 self.created_at,
            'status':                     self.status,
            'mode':                       self.mode,
            'current_question_index':     self.current_question_index,
            'max_questions':              self.max_questions,
            'question_turns': [
                {
                    'question_id':           t.question_id,
                    'question_text':         t.question_text,
                    'category':              t.category,
                    'difficulty':            t.difficulty,
                    'intent':                t.intent,
                    'follow_ups':            t.follow_ups,
                    'expected_time_sec':     t.expected_time_sec,
                    'asked_at':              t.asked_at,
                    'answer_text':           t.answer_text,
                    'answer_duration':       t.answer_duration,
                    'answered_at':           t.answered_at,
                    'answer_score':          t.answer_score,
                    'answer_feedback':       t.answer_feedback,
                    'interviewer_response':  t.interviewer_response,
                    'is_followup':           t.is_followup,
                    'parent_question_id':    t.parent_question_id,
                    'followup_count':        t.followup_count,
                    'emotion_at_ask':        t.emotion_at_ask,
                }
                for t in self.question_turns
            ],
            'conversation_history':           self.conversation_history,
            'answer_scores':                  self.answer_scores,
            'category_scores':                self.category_scores,
            'overall_score':                  self.overall_score,
            'followup_counts':                self.followup_counts,
            'max_followups':                  self.max_followups,
            'weak_answer_threshold':          self.weak_answer_threshold,
            'strong_answer_threshold':        self.strong_answer_threshold,
            'violations':                     self.violations,
            'warning_count':                  self.warning_count,
            'max_warnings':                   self.max_warnings,
            'emotion_timeline':               self.emotion_timeline,
            'dominant_emotions':              self.dominant_emotions,
            'current_emotion':                self.current_emotion,
            'face_detection_logs':            self.face_detection_logs,
            'personality':                    self.personality,
            'started_at':                     self.started_at,
            'completed_at':                   self.completed_at,
            'interview_duration_minutes':     self.interview_duration_minutes,
            'time_warning_sent':              self.time_warning_sent,
            'interview_ended_early':          self.interview_ended_early,
            'auto_submitted_reason':          self.auto_submitted_reason,
            'elapsed_minutes':                self.elapsed_minutes(),
            'minutes_remaining':              self.minutes_remaining(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InterviewState':
        question_turns = []
        for t in data.get('question_turns', []):
            question_turns.append(QuestionTurn(
                question_id          = t.get('question_id', 0),
                question_text        = t.get('question_text', ''),
                category             = t.get('category', ''),
                difficulty           = t.get('difficulty', ''),
                intent               = t.get('intent', ''),
                follow_ups           = t.get('follow_ups', []),
                expected_time_sec    = t.get('expected_time_sec', 60),
                asked_at             = t.get('asked_at', ''),
                answer_text          = t.get('answer_text'),
                answer_duration      = t.get('answer_duration', 0),
                answered_at          = t.get('answered_at'),
                answer_score         = t.get('answer_score'),
                answer_feedback      = t.get('answer_feedback'),
                interviewer_response = t.get('interviewer_response'),
                is_followup          = t.get('is_followup', False),
                parent_question_id   = t.get('parent_question_id'),
                followup_count       = t.get('followup_count', 0),
                emotion_at_ask       = t.get('emotion_at_ask'),
            ))

        return cls(
            interview_id              = data.get('interview_id', ''),
            candidate_name            = data.get('candidate_name', ''),
            candidate_email           = data.get('candidate_email', ''),
            job_description           = data.get('job_description', ''),
            resume_text               = data.get('resume_text', ''),
            created_at                = data.get('created_at', datetime.now().isoformat()),
            status                    = data.get('status', 'created'),
            mode                      = data.get('mode', 'ai'),
            current_question_index    = data.get('current_question_index', 0),
            max_questions             = data.get('max_questions', 999),
            question_turns            = question_turns,
            conversation_history      = data.get('conversation_history', []),
            answer_scores             = data.get('answer_scores', []),
            category_scores           = data.get('category_scores', {}),
            overall_score             = data.get('overall_score'),
            followup_counts           = data.get('followup_counts', {}),
            max_followups             = data.get('max_followups', 2),
            weak_answer_threshold     = data.get('weak_answer_threshold', 5.0),
            strong_answer_threshold   = data.get('strong_answer_threshold', 7.5),
            violations                = data.get('violations', []),
            warning_count             = data.get('warning_count', 0),
            max_warnings              = data.get('max_warnings', 3),
            emotion_timeline          = data.get('emotion_timeline', []),
            dominant_emotions         = data.get('dominant_emotions', []),
            current_emotion           = data.get('current_emotion'),
            face_detection_logs       = data.get('face_detection_logs', []),
            personality               = data.get('personality', 'friendly'),
            started_at                = data.get('started_at'),
            completed_at              = data.get('completed_at'),
            interview_duration_minutes = data.get('interview_duration_minutes', 30),
            time_warning_sent         = data.get('time_warning_sent', False),
            interview_ended_early     = data.get('interview_ended_early', False),
            auto_submitted_reason     = data.get('auto_submitted_reason'),
        )