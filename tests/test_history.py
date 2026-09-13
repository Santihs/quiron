from quiron.history import append_events, load_history, make_event
from quiron.vault import Vault


def test_history_append_is_idempotent(tmp_path):
    (tmp_path / "00-Meta").mkdir()
    vault = Vault(root=tmp_path)
    event = make_event(
        "policy_decided",
        operation_id="op-1",
        subject="concept-x",
        card_policy="needed",
    )

    assert append_events(vault, [event]) == 1
    assert append_events(vault, [event]) == 0

    history = load_history(vault)
    assert len(history) == 1
    assert history[0]["version"] == 1
    assert history[0]["operation_id"] == "op-1"


def test_history_keeps_distinct_events_for_one_operation():
    events = [
        make_event("policy_decided", operation_id="op-1", subject="concept-a"),
        make_event("policy_decided", operation_id="op-1", subject="concept-b"),
    ]

    assert events[0]["event_id"] != events[1]["event_id"]
