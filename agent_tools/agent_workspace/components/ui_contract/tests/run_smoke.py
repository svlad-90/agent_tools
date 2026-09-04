from __future__ import annotations

import argparse
from collections.abc import Callable
from unittest import SkipTest

from . import test_ui_contract


TestFunc = Callable[[], None]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run dependency-free UI contract smoke tests.")
    parser.add_argument(
        "--require-real-gtk",
        action="store_true",
        help="return a failure when the real GTK runtime snapshot test is skipped",
    )
    args = parser.parse_args(argv)

    tests: tuple[TestFunc, ...] = (
        test_ui_contract.test_compare_ui_trees_accepts_matching_trees,
        test_ui_contract.test_compare_ui_trees_reports_missing_and_changed_nodes,
        test_ui_contract.test_snapshot_widget_tree_reads_runtime_widget_metadata,
        test_ui_contract.test_snapshot_widget_tree_reads_toolkit_data_metadata,
        test_ui_contract.test_snapshot_widget_tree_reads_real_gtk_widgets,
        test_ui_contract.test_gtk_settings_dialog_runtime_tree_matches_source_contract_ids,
        test_ui_contract.test_web_settings_contract_matches_gtk_settings_contract,
        test_ui_contract.test_settings_contract_includes_limited_bash_split_fields,
    )
    skipped: list[str] = []
    for test in tests:
        try:
            test()
        except SkipTest as exc:
            skipped.append(f"{test.__name__}: {exc}")

    if args.require_real_gtk and any("real_gtk" in item or "gtk_settings_dialog" in item for item in skipped):
        for item in skipped:
            print(f"SKIP {item}")
        print("FAIL real GTK runtime snapshot was required")
        return 1

    for item in skipped:
        print(f"SKIP {item}")
    print(f"PASS ui_contract smoke tests: {len(tests) - len(skipped)} passed, {len(skipped)} skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
