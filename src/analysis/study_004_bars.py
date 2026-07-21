"""Pre-registered Study 004 scoring-bar arithmetic."""

Q14_ALLOWED_SCORES = frozenset({0.0, 0.5, 1.0})


def validate_q14_score(score: float) -> float:
    value = float(score)
    if value not in Q14_ALLOWED_SCORES:
        raise ValueError("Q14 score must be one of 0.0, 0.5, or 1.0")
    return value


def evaluate_breadth_bar(
    q11_score: float,
    q14_score: float,
    q11_ltm_attributed: bool,
    q14_ltm_attributed: bool,
) -> dict:
    """Evaluate Bar 1, including its LTM-provenance attribution clause."""
    q11 = float(q11_score)
    q14 = validate_q14_score(q14_score)
    score_pass = q11 >= 0.5 and q14 >= 0.5 and q11 + q14 >= 1.5
    attribution_pass = q11_ltm_attributed and q14_ltm_attributed
    return {
        "passed": score_pass and attribution_pass,
        "score_pass": score_pass,
        "attribution_pass": attribution_pass,
        "q11": q11,
        "q14": q14,
        "combined": q11 + q14,
    }


def evaluate_non_regression_bar(
    q1_q13_total: float,
    category_1: float,
    category_2: float,
    category_3: float,
    category_5: float,
) -> dict:
    """Evaluate Bar 2 without allowing Q14 to enter the 13-point total."""
    checks = {
        "q1_q13_total": float(q1_q13_total) >= 12.0,
        "category_1": float(category_1) >= 3.0,
        "category_2": float(category_2) >= 3.0,
        "category_3": float(category_3) >= 2.0,
        "category_5": float(category_5) >= 2.0,
    }
    return {"passed": all(checks.values()), "checks": checks}


def evaluate_consolidation_bar(
    turn_121_topic_count: int,
    cross_domain_merge_count: int,
) -> dict:
    """Evaluate Bar 3's topic-count band and zero-impurity requirement."""
    topic_count_pass = 3 <= int(turn_121_topic_count) <= 10
    purity_pass = int(cross_domain_merge_count) == 0
    return {
        "passed": topic_count_pass and purity_pass,
        "topic_count_pass": topic_count_pass,
        "purity_pass": purity_pass,
    }
