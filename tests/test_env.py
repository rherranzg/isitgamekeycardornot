import pytest
from pytest_mock import MockerFixture

from switch2db.env import read_required_env


def test_read_required_env_success(mocker: MockerFixture) -> None:
    mocker.patch.dict("os.environ", {"SWITCH2DB_TEST_VAR": "value"})

    assert read_required_env("SWITCH2DB_TEST_VAR") == "value"


def test_read_required_env_raises_when_missing(mocker: MockerFixture) -> None:
    mocker.patch.dict("os.environ", {}, clear=True)

    with pytest.raises(RuntimeError, match="SWITCH2DB_TEST_VAR"):
        read_required_env("SWITCH2DB_TEST_VAR")


def test_read_required_env_raises_when_empty(mocker: MockerFixture) -> None:
    mocker.patch.dict("os.environ", {"SWITCH2DB_TEST_VAR": ""})

    with pytest.raises(RuntimeError, match="SWITCH2DB_TEST_VAR"):
        read_required_env("SWITCH2DB_TEST_VAR")
