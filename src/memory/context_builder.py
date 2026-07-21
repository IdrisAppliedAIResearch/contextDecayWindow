from html import escape


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

    Placement is defensive as well as presentational: recency takes precedence
    over retrieval, and LTM takes precedence over STM for a post-arbitration
    episode that has both provenances.
    """
    rules = list(rule_episodes or [])
    recent = _unique_episodes(recent_episodes or [])
    recent_ids = {episode.get("id") for episode in recent}

    ltm = [
        episode
        for episode in _unique_episodes(ltm_episodes or [])
        if episode.get("id") not in recent_ids
    ]
    ltm_ids = {episode.get("id") for episode in ltm}
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


def _unique_episodes(episodes: list) -> list:
    seen: set[str] = set()
    unique = []
    for episode in episodes:
        episode_id = episode.get("id")
        if episode_id in seen:
            continue
        seen.add(episode_id)
        unique.append(episode)
    return unique


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
        attributes = [
            f'turn="{_attribute(episode.get("turn_number", ""))}"',
            f'topic="{_attribute(episode.get("topic_label", episode.get("topic_id", "")))}"',
        ]
        if tier in {"stm", "ltm"} and episode.get("similarity") is not None:
            attributes.append(f'similarity="{float(episode["similarity"]):.6f}"')
        if tier == "ltm":
            if episode.get("promoted_at_turn") is not None:
                attributes.append(
                    f'promoted_at_turn="{_attribute(episode["promoted_at_turn"])}"'
                )
            if episode.get("trigger_type"):
                attributes.append(
                    f'trigger_type="{_attribute(episode["trigger_type"])}"'
                )
        lines.append(f"  <episode {' '.join(attributes)}>")
        lines.append(
            f"    <user_message>{_text(episode.get('user_message', ''))}</user_message>"
        )
        lines.append(
            "    <assistant_message>"
            f"{_text(episode.get('assistant_message', ''))}"
            "</assistant_message>"
        )
        lines.append("  </episode>")
    lines.append(f"</{name}>")
    return "\n".join(lines)


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
