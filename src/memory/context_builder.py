from html import escape

# The compact episode serializer moved into the episodic library (CC-002);
# the harness consumes it from there. Span rendering stays here: spans are
# distillation output, which the library does not produce.
from episodic._render import render_episode_element


def build_prompt(
    episodes: list,
    system_prompt: str,
    rule_episodes: list = None,
) -> str:
    parts = [system_prompt, ""]

    if rule_episodes:
        parts.append("--- PINNED RULES ---")
        for ep in rule_episodes:
            parts.append(f"[Turn {ep['turn_number']}]")
            parts.append(f"User: {ep['user_message']}")
            parts.append(f"Assistant: {ep['assistant_message']}")
            parts.append("")
        parts.append("--- END PINNED RULES ---")
        parts.append("")

    if not episodes and not rule_episodes:
        return system_prompt

    if episodes:
        parts.append("--- RETRIEVED CONVERSATION HISTORY ---")

        for ep in episodes:
            parts.append(f"[Turn {ep['turn_number']}]")
            parts.append(f"User: {ep['user_message']}")
            parts.append(f"Assistant: {ep['assistant_message']}")
            parts.append("")

        parts.append("--- END HISTORY ---")

    return "\n".join(parts)


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def _build_rule_block_text(rule_episodes: list) -> str:
    if not rule_episodes:
        return ""
    lines = ["--- PINNED RULES ---"]
    for ep in rule_episodes:
        lines.append(f"[Turn {ep['turn_number']}]")
        lines.append(f"User: {ep['user_message']}")
        lines.append(f"Assistant: {ep['assistant_message']}")
        lines.append("")
    lines.append("--- END PINNED RULES ---")
    return "\n".join(lines)


def build_tagged_context(
    system_prompt: str,
    current_user_message: str,
    rule_episodes: list | None = None,
    recent_episodes: list | None = None,
    stm_episodes: list | None = None,
    ltm_episodes: list | None = None,
) -> str:
    """Render the five ordered Study 004 context blocks.

    Placement is defensive as well as presentational: LTM provenance takes
    precedence over recency, while recency takes precedence over STM K-only
    retrieval. LTM also takes precedence over STM for a post-arbitration
    episode that has both provenances.
    """
    rules = list(rule_episodes or [])
    ltm = _unique_episodes(ltm_episodes or [])
    ltm_ids = {episode.get("id") for episode in ltm}
    recent = [
        episode
        for episode in _unique_episodes(recent_episodes or [])
        if episode.get("id") not in ltm_ids
    ]
    recent_ids = {episode.get("id") for episode in recent}
    stm = [
        episode
        for episode in _unique_episodes(stm_episodes or [])
        if episode.get("id") not in recent_ids
        and episode.get("id") not in ltm_ids
    ]

    blocks = [
        _render_rules_block(rules),
        _render_episode_block("recent_context", recent, "recent"),
        _render_episode_block("retrieved_stm", stm, "stm"),
        _render_episode_block("retrieved_ltm", ltm, "ltm"),
        _render_current_turn(current_user_message),
    ]
    return "\n\n".join([system_prompt, *blocks])


def build_pinned_rules_block(rule_episodes: list | None) -> str:
    """Expose the exact tagged rule block for token accounting."""
    return _render_rules_block(list(rule_episodes or []))


def render_ltm_block(ltm_episodes: list | None) -> str:
    """Expose the exact LTM renderer for budget replay and fidelity checks."""
    return _render_episode_block(
        "retrieved_ltm",
        _unique_episodes(ltm_episodes or []),
        "ltm",
    )


def _unique_episodes(episodes: list) -> list:
    seen: set[str] = set()
    unique = []
    for episode in episodes:
        identity = _context_identity(episode)
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(episode)
    return unique


def _context_identity(episode: dict) -> str:
    if episode.get("render_mode") == "span" and episode.get("distilled_id"):
        return f"span:{episode['distilled_id']}"
    return f"episode:{episode.get('id')}"


def _render_rules_block(rules: list) -> str:
    if not rules:
        return "<pinned_rules/>"
    lines = ["<pinned_rules>"]
    for rule in rules:
        rule_id = _attribute(rule.get("rule_id", rule.get("id", "")))
        set_at_turn = _attribute(
            rule.get("set_at_turn", rule.get("turn_number", ""))
        )
        summary = rule.get("rule_summary") or rule.get("user_message", "")
        lines.append(
            f'  <rule id="{rule_id}" set_at_turn="{set_at_turn}">'
            f"{_text(summary)}</rule>"
        )
    lines.append("</pinned_rules>")
    return "\n".join(lines)


def _render_episode_block(name: str, episodes: list, tier: str) -> str:
    if not episodes:
        return f"<{name}/>"
    lines = [f"<{name}>"]
    for episode in episodes:
        if tier == "ltm" and episode.get("render_mode") == "span":
            lines.append(render_ltm_span_element(episode))
            continue
        lines.append(render_episode_element(episode))
    lines.append(f"</{name}>")
    return "\n".join(lines)


def render_ltm_span_element(episode: dict) -> str:
    """Serialize one span exactly as it appears inside retrieved_ltm."""
    source_turn = episode.get("turn_number", "")
    if episode.get("source_turns"):
        source_turn = episode["source_turns"][0]
    attributes = [
        f'distilled_id="{_attribute(episode.get("distilled_id", ""))}"',
        f'source_episode_id="{_attribute(episode.get("id", ""))}"',
        f'source_turn="{_attribute(source_turn)}"',
        f'role="{_attribute(episode.get("role", ""))}"',
        f'topic="{_attribute(episode.get("topic_label", episode.get("topic_id", "")))}"',
        f'dream_event="{_attribute(episode.get("dream_event", ""))}"',
        f'span_start="{_attribute(episode.get("span_start", ""))}"',
        f'span_end="{_attribute(episode.get("span_end", ""))}"',
    ]
    if episode.get("event_type"):
        attributes.append(
            f'event_type="{_attribute(episode["event_type"])}"'
        )
    if episode.get("similarity") is not None:
        attributes.append(
            f'similarity="{float(episode["similarity"]):.6f}"'
        )
    return (
        f"  <span {' '.join(attributes)}>"
        f"{_text(episode.get('span_text', ''))}</span>"
    )


def _render_current_turn(user_message: str) -> str:
    return (
        "<current_turn>\n"
        f"  <user_message>{_text(user_message)}</user_message>\n"
        "</current_turn>"
    )


def _attribute(value) -> str:
    return escape(str(value), quote=True)


def _text(value) -> str:
    return escape(str(value), quote=False)
