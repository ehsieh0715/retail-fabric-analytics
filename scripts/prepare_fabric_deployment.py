"""Render portable Fabric templates into ``.deployment/fabric``.

Run each command from the repository root when its target Fabric dependencies
become available. Source-controlled files under ``fabric`` remain unchanged.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


SOURCE_DIR = Path("fabric")
OUTPUT_DIR = Path(".deployment/fabric")
PLACEHOLDER_PATTERN = re.compile(r"__[A-Z][A-Z0-9_]*__")


def get_fabric_id(workspace: str, item: str | None = None) -> str:
    """Get a workspace or item ID when that target object exists.

    Args:
        workspace: Target Fabric workspace name.
        item: Optional item path such as ``name.ItemType``.

    Returns:
        The ID returned by Fabric CLI.

    Raises:
        RuntimeError: If ``fab get`` is unavailable or unsuccessful.
    """

    target = f"{workspace}.Workspace"
    if item:
        target = f"{target}/{item}"

    try:
        result = subprocess.run(
            ["fab", "get", target, "-q", "id"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise RuntimeError("Fabric CLI executable 'fab' was not found.") from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or error.stdout.strip()
        raise RuntimeError(
            f"Unable to retrieve the Fabric ID for {target}"
            + (f": {detail}" if detail else "")
        ) from error

    item_id = result.stdout.strip().strip('"')
    if not item_id:
        raise RuntimeError(f"Fabric CLI returned an empty ID for {target}.")
    return item_id


def replace_placeholders(replacements: dict[str, str]) -> None:
    """Fill the bindings available at the current deployment stage.

    Args:
        replacements: Placeholder-to-value mappings for this stage.

    Raises:
        RuntimeError: If the deployment copy or an expected token is missing.
    """

    if not OUTPUT_DIR.is_dir():
        raise RuntimeError("Deployment copy not found. Run initialize first.")

    counts = dict.fromkeys(replacements, 0)
    for path in OUTPUT_DIR.rglob("*"):
        if not path.is_file():
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        rendered = original
        for placeholder, value in replacements.items():
            counts[placeholder] += rendered.count(placeholder)
            rendered = rendered.replace(placeholder, value)
        if rendered != original:
            path.write_text(rendered, encoding="utf-8")

    missing = [token for token, count in counts.items() if count == 0]
    if missing:
        raise RuntimeError("Expected placeholder(s) not found: " + ", ".join(missing))


def initialize(workspace: str, force: bool = False) -> None:
    """Create the deployment copy after creating the target Lakehouse.

    Args:
        workspace: Target Fabric workspace name.
        force: Replace an existing ``.deployment/fabric`` directory.

    Raises:
        RuntimeError: If templates are missing or output already exists.
    """

    if not SOURCE_DIR.is_dir():
        raise RuntimeError(f"Fabric template directory not found: {SOURCE_DIR}")
    if OUTPUT_DIR.exists() and not force:
        raise RuntimeError(
            f"Deployment output already exists: {OUTPUT_DIR}. Use --force to rebuild it."
        )

    replacements = {
        "__TARGET_WORKSPACE_ID__": get_fabric_id(workspace),
        "__TARGET_LAKEHOUSE_ID__": get_fabric_id(
            workspace, "lh_retail_analytics.Lakehouse"
        ),
        "__TARGET_WORKSPACE_NAME__": workspace,
    }

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE_DIR, OUTPUT_DIR)
    replace_placeholders(replacements)
    print(f"Initialized deployment copy: {OUTPUT_DIR}")


def bind_notebooks(workspace: str) -> None:
    """Bind the transformation pipeline after importing both notebooks.

    Args:
        workspace: Target workspace containing the imported notebooks.
    """

    replace_placeholders(
        {
            "__BRONZE_TO_SILVER_NOTEBOOK_ID__": get_fabric_id(
                workspace, "nb_bronze_to_silver.Notebook"
            ),
            "__SILVER_TO_GOLD_NOTEBOOK_ID__": get_fabric_id(
                workspace, "nb_silver_to_gold.Notebook"
            ),
        }
    )
    print("Bound transformation pipeline to target notebooks.")


def bind_report(workspace: str) -> None:
    """Bind the report after importing the target semantic model.

    Args:
        workspace: Target workspace containing the semantic model.
    """

    replace_placeholders(
        {
            "__TARGET_SEMANTIC_MODEL_ID__": get_fabric_id(
                workspace, "sm_retail_analytics.SemanticModel"
            )
        }
    )
    print("Bound report to target semantic model.")


def validate() -> None:
    """Check that every binding is resolved before the final import.

    Raises:
        RuntimeError: If output is missing or any placeholder remains.
    """

    if not OUTPUT_DIR.is_dir():
        raise RuntimeError("Deployment copy not found. Run initialize first.")

    unresolved = []
    for path in OUTPUT_DIR.rglob("*"):
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            unresolved.extend(
                (path.relative_to(OUTPUT_DIR), line_number, token)
                for token in PLACEHOLDER_PATTERN.findall(line)
            )

    if unresolved:
        details = "\n".join(
            f"  {path}:{line_number}: {token}"
            for path, line_number, token in unresolved
        )
        raise RuntimeError(f"Unresolved deployment placeholders remain:\n{details}")
    print(f"Deployment copy is fully resolved: {OUTPUT_DIR}")


def main(argv: list[str] | None = None) -> int:
    """Parse a deployment stage, execute it, and return a shell status.

    Args:
        argv: Optional arguments for programmatic use and tests.

    Returns:
        Zero on success or one for a handled deployment error.
    """

    parser = argparse.ArgumentParser(
        description="Prepare portable Microsoft Fabric item definitions."
    )
    parser.add_argument(
        "command",
        choices=("initialize", "bind-notebooks", "bind-report", "validate"),
    )
    parser.add_argument("--workspace")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    if args.command != "validate" and not args.workspace:
        parser.error("--workspace is required for this command")
    if args.force and args.command != "initialize":
        parser.error("--force can only be used with initialize")

    try:
        if args.command == "initialize":
            initialize(args.workspace, args.force)
        elif args.command == "bind-notebooks":
            bind_notebooks(args.workspace)
        elif args.command == "bind-report":
            bind_report(args.workspace)
        else:
            validate()
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
