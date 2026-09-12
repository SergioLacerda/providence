from __future__ import annotations

from providence_cli.shared.errors import CliContractError


def test_cli_contract_error_string_representation() -> None:
    err = CliContractError(reason_code="bad_contract", message="missing field")
    assert str(err) == "[bad_contract] missing field"
