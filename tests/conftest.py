from pathlib import Path

import pytest

from quiron.vault import Vault

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "vault"


@pytest.fixture
def vault() -> Vault:
    return Vault(root=FIXTURE_ROOT)
