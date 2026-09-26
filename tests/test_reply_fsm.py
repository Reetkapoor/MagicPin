from app.composer import handle_reply


def test_commitment_is_actioning():
    result = handle_reply("c1", "Ok lets do it. Whats next?", 2)
    assert result["action"] == "send"
    assert "done" in result["body"].lower()
    assert "draft" in result["body"].lower()


def test_hostile_ends():
    result = handle_reply("c2", "Stop messaging me. This is useless spam.", 2)
    assert result["action"] == "end"


def test_off_topic_redirects():
    result = handle_reply("c3", "Can you help with my GST filing?", 2)
    assert result["action"] == "send"
    assert "outside" in result["body"].lower() or "consult" in result["body"].lower()
