import os

import pytest

from quiron.store import atomic_write_text, vault_lock
from quiron.vault import Vault


def test_atomic_write_preserves_previous_file_when_replace_fails(tmp_path, monkeypatch):
    path = tmp_path / "00-Meta" / "knowledge.json"
    path.parent.mkdir()
    path.write_text("old", encoding="utf-8")

    def fail_replace(source, destination):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError, match="disk full"):
        atomic_write_text(path, "new")

    assert path.read_text(encoding="utf-8") == "old"


def test_vault_lock_creates_shared_lock_file(tmp_path):
    vault = Vault(root=tmp_path)

    with vault_lock(vault):
        assert (tmp_path / ".quiron.lock").exists()
