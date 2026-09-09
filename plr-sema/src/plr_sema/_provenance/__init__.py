"""plr_sema._provenance: provenance capture (spec 260901 §2).

git_state.py is a verbatim cherry-pick (see its own header for provenance).
stamp.py wraps it into the process-memoized SurveyStamp that pins which PLR
tree and which analyzer tree a run/event was computed against.
"""

from plr_sema._provenance.stamp import DEFAULT_SURFACE, Surface, SurveyStamp, survey_stamp

__all__ = ["DEFAULT_SURFACE", "Surface", "SurveyStamp", "survey_stamp"]
