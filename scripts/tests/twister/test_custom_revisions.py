# SPDX-License-Identifier: Apache-2.0
"""Regression tests for explicitly requested custom board revisions.
Add to scripts/tests/twister/test_custom_revisions.py in Zephyr v4.5.0-rc1.
"""

from types import SimpleNamespace

import pytest
from list_boards import Board, Soc
from twisterlib.platform import Platform


@pytest.fixture
def custom_revision_plan(class_testplan, tmp_path):
    board = Board(
        name="test_custom_revision",
        directories=[tmp_path],
        hwm="v2",
        vendor="others",
        revision_format="custom",
        socs=[Soc("soc1")],
    )
    base = Platform()
    base.load(
        board,
        "test_custom_revision/soc1",
        ["test_custom_revision/soc1", "test_custom_revision"],
        {"arch": "arm", "type": "mcu", "testing": {"default": True}},
        {},
    )
    class_testplan.platforms = [base]
    class_testplan.platform_names = list(base.aliases)
    return class_testplan


def test_unlisted_custom_revision_short_and_qualified(custom_revision_plan):
    plan = custom_revision_plan
    requested = ["test_custom_revision@rev_b", "test_custom_revision@rev_b/soc1"]
    assert plan.verify_platforms_existence(requested) == [
        "test_custom_revision@rev_b/soc1",
        "test_custom_revision@rev_b/soc1",
    ]
    platform = plan.get_platform("test_custom_revision@rev_b")
    assert platform is plan.get_platform("test_custom_revision@rev_b/soc1")
    assert platform.name == "test_custom_revision@rev_b/soc1"
    assert platform.arch == "arm"
    assert platform.board.revision_format == "custom"
    assert not platform.default
    assert len(plan.platforms) == 2  # Only one explicit revision added.
    assert plan.get_platform("test_custom_revision").name == "test_custom_revision/soc1"


def test_custom_revision_in_test_yaml_filters(custom_revision_plan):
    plan = custom_revision_plan
    suite = SimpleNamespace(
        name="test_custom_revision.build",
        integration_platforms=["test_custom_revision@rev_a"],
        platform_allow=["test_custom_revision@rev_b"],
        platform_exclude=[],
        harness_config=SimpleNamespace(required_devices=[]),
        required_applications=[],
    )
    plan._resolve_suite_platform_names(suite)
    assert suite.integration_platforms == ["test_custom_revision@rev_a/soc1"]
    assert suite.platform_allow == ["test_custom_revision@rev_b/soc1"]
    assert len(plan.platforms) == 3
    assert not plan.get_platform("test_custom_revision@rev_a").default
    assert not plan.get_platform("test_custom_revision@rev_b").default


def test_unknown_board_and_bad_qualifier_still_rejected(custom_revision_plan):
    plan = custom_revision_plan
    for name in ("not_a_board@rev_b", "test_custom_revision@rev_b/unknown"):
        with pytest.raises(SystemExit) as exc:
            plan.verify_platforms_existence([name])
        assert exc.value.code == 2
    assert len(plan.platforms) == 1


def test_non_custom_board_does_not_accept_arbitrary_revision(custom_revision_plan):
    plan = custom_revision_plan
    board = Board(
        name="normal_board",
        directories=[],
        hwm="v2",
        revision_format="number",
        socs=[Soc("soc1")],
    )
    platform = Platform()
    platform.load(
        board, "normal_board/soc1", ["normal_board/soc1", "normal_board"], {"arch": "arm"}, {}
    )
    plan.platforms.append(platform)
    plan.platform_names.extend(platform.aliases)
    with pytest.raises(SystemExit) as exc:
        plan.verify_platforms_existence(["normal_board@not_listed"])
    assert exc.value.code == 2


def test_custom_revision_twister_yaml_override(custom_revision_plan, tmp_path):
    """Requested custom revisions should get their own Twister metadata."""
    (tmp_path / "twister.yaml").write_text(
        """arch: arm
type: mcu
variants:
  test_custom_revision@rev_b/soc1:
    ram: 32
""",
        encoding="utf-8",
    )
    plan = custom_revision_plan
    plan.verify_platforms_existence(["test_custom_revision@rev_b"])
    assert plan.get_platform("test_custom_revision@rev_b").ram == 32
    assert plan.get_platform("test_custom_revision").ram == 128
