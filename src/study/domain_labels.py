"""Ground-truth domain labels registered for Study 004 purity checks."""

CIVIL_ENGINEERING = "civil_engineering"
RENAISSANCE_ART = "renaissance_art"
MONETARY_POLICY = "monetary_policy"
MARINE_BIOLOGY = "marine_biology"
PROBE = "probe"
UNREGISTERED = "unregistered"

PROBE_TURN_START = 112
PROBE_TURN_END = 121


def ground_truth_domain_for_turn(turn_number: int) -> str:
    """Return the registered real-script domain for a turn number."""
    if 1 <= turn_number <= 30:
        return CIVIL_ENGINEERING
    if 31 <= turn_number <= 60:
        return RENAISSANCE_ART
    if 61 <= turn_number <= 90:
        return MONETARY_POLICY
    if 91 <= turn_number <= 111:
        return MARINE_BIOLOGY
    if PROBE_TURN_START <= turn_number <= PROBE_TURN_END:
        return PROBE
    return UNREGISTERED


def is_probe_turn(turn_number: int, ground_truth_domain: str | None = None) -> bool:
    """Recognize both real-script and explicitly labelled synthetic probes."""
    return (
        ground_truth_domain == PROBE
        or PROBE_TURN_START <= turn_number <= PROBE_TURN_END
    )
