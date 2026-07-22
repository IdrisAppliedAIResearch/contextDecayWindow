from src.memory.context_builder import build_tagged_context


def test_tagged_context_snapshot_and_recency_precedence():
    recent = {
        "id": "shared",
        "turn_number": 2,
        "topic_label": "topic_a",
        "user_message": "Recent <question>",
        "assistant_message": "Answer & detail",
    }
    prompt = build_tagged_context(
        system_prompt="System prompt",
        current_user_message="Current & <query>",
        rule_episodes=[{
            "rule_id": "rule&1",
            "set_at_turn": 1,
            "rule_summary": "Use <lists> & care",
        }],
        recent_episodes=[recent],
        stm_episodes=[
            {**recent, "similarity": 0.99},
            {
                "id": "stm-only",
                "turn_number": 3,
                "topic_label": "topic_b",
                "user_message": "STM user",
                "assistant_message": "STM assistant",
                "similarity": 0.81234567,
                "novelty_score": 0.7,
                "weighted_score": 0.6,
            },
        ],
        ltm_episodes=[],
    )

    assert prompt == """System prompt

<pinned_rules>
  <rule id="rule&amp;1" set_at_turn="1">Use &lt;lists&gt; &amp; care</rule>
</pinned_rules>

<recent_context>
  <episode turn="2" topic="topic_a">
    <user_message>Recent &lt;question&gt;</user_message>
    <assistant_message>Answer &amp; detail</assistant_message>
  </episode>
</recent_context>

<retrieved_stm>
  <episode turn="3" topic="topic_b" similarity="0.812346">
    <user_message>STM user</user_message>
    <assistant_message>STM assistant</assistant_message>
  </episode>
</retrieved_stm>

<retrieved_ltm/>

<current_turn>
  <user_message>Current &amp; &lt;query&gt;</user_message>
</current_turn>"""
    assert prompt.count("Recent &lt;question&gt;") == 1
    assert "novelty" not in prompt
    assert "weighted" not in prompt
    assert "decay" not in prompt


def test_all_empty_tagged_blocks_are_present_and_self_closing():
    prompt = build_tagged_context(
        system_prompt="System",
        current_user_message="Hello",
    )

    assert prompt == """System

<pinned_rules/>

<recent_context/>

<retrieved_stm/>

<retrieved_ltm/>

<current_turn>
  <user_message>Hello</user_message>
</current_turn>"""


def test_ltm_placement_wins_over_stm_for_same_episode():
    common = {
        "id": "both",
        "turn_number": 4,
        "topic_label": "topic_c",
        "user_message": "Shared user",
        "assistant_message": "Shared assistant",
        "similarity": 0.75,
    }
    prompt = build_tagged_context(
        system_prompt="System",
        current_user_message="Question",
        stm_episodes=[common],
        ltm_episodes=[{
            **common,
            "promoted_at_turn": 31,
            "trigger_type": "weighted_threshold",
        }],
    )

    assert prompt.count("Shared user") == 1
    assert "<retrieved_stm/>" in prompt
    assert 'promoted_at_turn="31"' in prompt
    assert 'trigger_type="weighted_threshold"' in prompt


def test_ltm_placement_preserves_provenance_when_episode_is_also_recent():
    common = {
        "id": "recent-and-ltm",
        "turn_number": 7,
        "topic_label": "topic_a",
        "user_message": "Promoted recent user",
        "assistant_message": "Promoted recent assistant",
    }
    prompt = build_tagged_context(
        system_prompt="System",
        current_user_message="Question",
        recent_episodes=[common],
        ltm_episodes=[{
            **common,
            "similarity": 0.61,
            "promoted_at_turn": 31,
            "trigger_type": "weighted_threshold",
        }],
    )

    assert prompt.count("Promoted recent user") == 1
    assert "<recent_context/>" in prompt
    assert "<retrieved_ltm>" in prompt
    assert 'promoted_at_turn="31"' in prompt
