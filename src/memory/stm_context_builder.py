"""Tagged context rendering for the structurally minimal Study 009 STM arm."""

from html import escape


def build_stm_context(
    system_prompt: str,
    current_user_message: str,
    rule_episodes: list | None = None,
    recent_episodes: list | None = None,
    stm_episodes: list | None = None,
) -> str:
    rules = list(rule_episodes or [])
    recent = _unique_episodes(recent_episodes or [])
    recent_ids = {episode.get("id") for episode in recent}
    stm = [
        episode
        for episode in _unique_episodes(stm_episodes or [])
        if episode.get("id") not in recent_ids
    ]
    blocks = [
        render_rules_block(rules),
        render_episode_block("recent_context", recent, "recent"),
        render_episode_block("retrieved_stm", stm, "stm"),
        render_current_turn(current_user_message),
    ]
    return "\n\n".join([system_prompt, *blocks])


def render_rules_block(rules: list) -> str:
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


def render_episode_block(name: str, episodes: list, tier: str) -> str:
    if not episodes:
        return f"<{name}/>"
    lines = [f"<{name}>"]
    for episode in episodes:
        attributes = [
            f'turn="{_attribute(episode.get("turn_number", ""))}"',
            f'topic="{_attribute(episode.get("topic_label", episode.get("topic_id", "")))}"',
        ]
        if tier == "stm" and episode.get("similarity") is not None:
            attributes.append(f'similarity="{float(episode["similarity"]):.6f}"')
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


def render_current_turn(user_message: str) -> str:
    return (
        "<current_turn>\n"
        f"  <user_message>{_text(user_message)}</user_message>\n"
        "</current_turn>"
    )


def _unique_episodes(episodes: list) -> list:
    seen: set[str] = set()
    unique = []
    for episode in episodes:
        identity = str(episode.get("id"))
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(episode)
    return unique


def _attribute(value) -> str:
    return escape(str(value), quote=True)


def _text(value) -> str:
    return escape(str(value), quote=False)
