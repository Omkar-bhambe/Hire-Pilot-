import json
import os
from datetime import datetime


# Valid status transitions: key = current status, value = allowed next statuses
STATUS_TRANSITIONS = {
    'created':     {'in_progress'},
    'in_progress': {'paused', 'submitted'},
    'paused':      {'in_progress', 'submitted'},
    'submitted':   set(),           # terminal — no further transitions allowed
    'evaluated':   set(),           # terminal
}


class InterviewManagerAgent:
    """Manages the overall interview lifecycle"""

    def __init__(self):
        self.interviews_folder = 'interviews'

    # ------------------------------------------------------------------
    # Public: lifecycle transitions
    # ------------------------------------------------------------------

    def start_interview(self, interview_id):
        """Mark interview as started (created → in_progress)"""
        interview_data, err = self._load(interview_id)
        if err:
            return err

        transition_error = self._validate_transition(
            interview_data, target_status='in_progress'
        )
        if transition_error:
            return transition_error

        interview_data['status']     = 'in_progress'
        interview_data['started_at'] = datetime.now().isoformat()

        # Initialise timeline list if not present
        self._append_timeline(interview_data, 'Interview Started', '🚀')

        self._save(interview_id, interview_data)
        return {
            'status':       'success',
            'message':      'Interview started',
            'interview_id': interview_id
        }

    def submit_interview(self, interview_id, auto_submitted=False):
        """Mark interview as completed (in_progress or paused → submitted)"""
        interview_data, err = self._load(interview_id)
        if err:
            return err

        transition_error = self._validate_transition(
            interview_data, target_status='submitted'
        )
        if transition_error:
            return transition_error

        interview_data['status']       = 'submitted'
        interview_data['completed_at'] = datetime.now().isoformat()
        interview_data['auto_submitted'] = auto_submitted

        if auto_submitted:
            interview_data['submission_reason'] = 'Auto-submitted due to policy violations'

        self._append_timeline(
            interview_data,
            'Interview Auto-Submitted' if auto_submitted else 'Interview Submitted',
            '⚠️' if auto_submitted else '✅'
        )

        # Calculate total duration if started_at exists
        interview_data['duration_seconds'] = self._calc_duration(
            interview_data.get('started_at'),
            interview_data['completed_at']
        )

        self._save(interview_id, interview_data)
        return {
            'status':         'success',
            'message':        'Interview submitted',
            'auto_submitted': auto_submitted,
            'interview_id':   interview_id
        }

    def pause_interview(self, interview_id):
        """Pause interview (in_progress → paused)"""
        interview_data, err = self._load(interview_id)
        if err:
            return err

        transition_error = self._validate_transition(
            interview_data, target_status='paused'
        )
        if transition_error:
            return transition_error

        interview_data['status']    = 'paused'
        interview_data['paused_at'] = datetime.now().isoformat()

        # ✅ Track all pause events, not just the last one
        self._append_timeline(interview_data, 'Interview Paused', '⏸️')

        self._save(interview_id, interview_data)
        return {
            'status':       'success',
            'message':      'Interview paused',
            'interview_id': interview_id
        }

    def resume_interview(self, interview_id):
        """Resume paused interview (paused → in_progress)"""
        interview_data, err = self._load(interview_id)
        if err:
            return err

        transition_error = self._validate_transition(
            interview_data, target_status='in_progress'
        )
        if transition_error:
            return transition_error

        interview_data['status']      = 'in_progress'
        interview_data['resumed_at']  = datetime.now().isoformat()

        # ✅ Track all resume events, not just the last one
        self._append_timeline(interview_data, 'Interview Resumed', '▶️')

        self._save(interview_id, interview_data)
        return {
            'status':       'success',
            'message':      'Interview resumed',
            'interview_id': interview_id
        }

    # ------------------------------------------------------------------
    # Public: read-only queries
    # ------------------------------------------------------------------

    def get_interview_status(self, interview_id):
        """Get current interview status and progress"""
        interview_data, err = self._load(interview_id)
        if err:
            return err

        questions = interview_data.get('questions', [])
        answers   = interview_data.get('answers', [])

        total     = len(questions)
        answered  = len(answers)
        progress  = {
            'total_questions': total,
            'answered':        answered,
            'pending':         total - answered,
            'percentage':      round((answered / total * 100), 1) if total else 0   # ✅ rounded
        }

        return {
            'status':           'success',
            'interview_id':     interview_id,
            'interview_status': interview_data.get('status', 'created'),
            'candidate_name':   interview_data.get('full_name'),
            'created_at':       interview_data.get('created_at'),
            'questions_count':  total,
            'progress':         progress,
            'warnings':         interview_data.get('warnings', 0),
            'violations':       len(interview_data.get('violations', [])),
            'duration_seconds': interview_data.get('duration_seconds'),    # ✅ added
        }

    def get_interview_summary(self, interview_id):
        """Get detailed interview summary"""
        interview_data, err = self._load(interview_id)
        if err:
            return err

        started_at   = interview_data.get('started_at')
        completed_at = interview_data.get('completed_at')

        return {
            'status': 'success',
            'interview': {
                'id': interview_data.get('interview_id'),
                'candidate': {
                    'name':  interview_data.get('full_name'),
                    'email': interview_data.get('email'),
                },
                'job_description': interview_data.get('job_description'),
                'dates': {
                    'created':   interview_data.get('created_at'),
                    'started':   started_at,
                    'completed': completed_at,
                },
                'duration_seconds': self._calc_duration(started_at, completed_at),  # ✅ added
                'status': interview_data.get('status'),
                'statistics': {
                    'total_questions': len(interview_data.get('questions', [])),
                    'total_answers':   len(interview_data.get('answers', [])),
                    'overall_score':   interview_data.get('evaluation', {}).get('overall_score'),
                    'violations':      len(interview_data.get('violations', [])),
                },
            }
        }

    def get_interview_timeline(self, interview_id):
        """
        Get interview timeline/history.
        Uses the persistent timeline list (supports multiple pause/resume cycles).
        Falls back to scalar timestamps for backwards compatibility.
        """
        interview_data, err = self._load(interview_id)
        if err:
            return err

        # ✅ Use stored timeline list if available
        timeline = interview_data.get('timeline', [])

        # Backwards-compatibility fallback for older records without timeline list
        if not timeline:
            timeline = self._rebuild_timeline_from_scalars(interview_data)

        # ✅ Sort by timestamp so ordering is always correct
        timeline_sorted = sorted(
            timeline,
            key=lambda e: e.get('timestamp', ''),
        )

        return {
            'status':       'success',
            'interview_id': interview_id,
            'timeline':     timeline_sorted,
        }

    # ------------------------------------------------------------------
    # Private: status transition validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_transition(interview_data, target_status):
        """
        Return an error dict if the transition is not allowed,
        or None if it is valid.
        """
        current = interview_data.get('status', 'created')
        allowed = STATUS_TRANSITIONS.get(current, set())

        if target_status not in allowed:
            return {
                'status':  'error',
                'message': (
                    f"Cannot transition from '{current}' to '{target_status}'. "
                    f"Allowed transitions: {sorted(allowed) or 'none (terminal state)'}"
                )
            }
        return None

    # ------------------------------------------------------------------
    # Private: timeline helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _append_timeline(interview_data, event, icon):
        """Append an event to the persistent timeline list inside the data dict"""
        if 'timeline' not in interview_data:
            interview_data['timeline'] = []

        # Seed created event if this is the first entry and it's missing
        created_at = interview_data.get('created_at')
        if created_at and not any(
            e['event'] == 'Interview Created' for e in interview_data['timeline']
        ):
            interview_data['timeline'].insert(0, {
                'event':     'Interview Created',
                'timestamp': created_at,
                'icon':      '📋',
            })

        interview_data['timeline'].append({
            'event':     event,
            'timestamp': datetime.now().isoformat(),
            'icon':      icon,
        })

    @staticmethod
    def _rebuild_timeline_from_scalars(interview_data):
        """
        Build a timeline list from old scalar fields for backwards compatibility.
        Only used when a record pre-dates the timeline list feature.
        """
        mapping = [
            ('created_at',   'Interview Created',   '📋'),
            ('started_at',   'Interview Started',   '🚀'),
            ('paused_at',    'Interview Paused',    '⏸️'),
            ('resumed_at',   'Interview Resumed',   '▶️'),
            ('completed_at', 'Interview Completed', '✅'),
        ]
        timeline = []
        for field, event, icon in mapping:
            ts = interview_data.get(field)
            if ts:
                timeline.append({'event': event, 'timestamp': ts, 'icon': icon})
        return timeline

    # ------------------------------------------------------------------
    # Private: duration helper
    # ------------------------------------------------------------------

    @staticmethod
    def _calc_duration(start_iso, end_iso):
        """
        Return duration in seconds between two ISO timestamps.
        Returns None if either timestamp is missing or unparseable.
        """
        if not start_iso or not end_iso:
            return None
        try:
            fmt = '%Y-%m-%dT%H:%M:%S.%f'
            start = datetime.fromisoformat(start_iso)
            end   = datetime.fromisoformat(end_iso)
            return round((end - start).total_seconds())
        except (ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # Private: safe file I/O (single source of truth)
    # ------------------------------------------------------------------

    def _load(self, interview_id):
        """
        Load interview JSON.
        Returns (data, None) on success or (None, error_dict) on failure.
        """
        path = os.path.join(self.interviews_folder, f'{interview_id}.json')
        if not os.path.exists(path):
            return None, {'status': 'error', 'message': 'Interview not found'}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f), None
        except (json.JSONDecodeError, IOError) as e:
            print(f"Failed to load interview file {path}: {e}")
            return None, {'status': 'error', 'message': f'Failed to read interview file: {e}'}

    def _save(self, interview_id, data):
        """Persist interview data safely"""
        path = os.path.join(self.interviews_folder, f'{interview_id}.json')
        os.makedirs(self.interviews_folder, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)