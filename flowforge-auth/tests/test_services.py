"""Unit tests — business layer only (no controller, no database)."""
from app import services


def test_assign_role_supervisor():
    assert services.assign_role("maria@flowforge.example", ["maria@flowforge.example"]) == "supervisor"


def test_assign_role_worker():
    assert services.assign_role("sam@flowforge.example", ["maria@flowforge.example"]) == "worker"


def test_assign_role_is_case_insensitive():
    assert services.assign_role("MARIA@FlowForge.Example", ["maria@flowforge.example"]) == "supervisor"


def test_assign_role_empty_email():
    assert services.assign_role("", ["maria@flowforge.example"]) == "worker"


def test_is_supervisor_true():
    assert services.is_supervisor("supervisor") is True


def test_is_supervisor_false():
    assert services.is_supervisor("worker") is False


def test_build_profile_supervisor():
    profile = services.build_profile("u1", "maria@flowforge.example", "supervisor")
    assert profile == {
        "uid": "u1",
        "email": "maria@flowforge.example",
        "role": "supervisor",
        "is_supervisor": True,
    }


def test_build_profile_worker_flag_false():
    assert services.build_profile("u2", "sam@flowforge.example", "worker")["is_supervisor"] is False
