# Foundation fixtures for agent-style evaluation cases.
AGENT_EVAL_CASES = [
    {
        "name": "single_turn_answer_has_citations",
        "goal": "Return a concise answer with at least one source reference.",
        "checks": ["answer_not_empty", "has_source_reference"],
    },
    {
        "name": "multi_turn_refinement",
        "goal": "Refine an initial answer after new evidence arrives.",
        "checks": ["tracks_new_evidence", "updates_prior_claims"],
    },
]
