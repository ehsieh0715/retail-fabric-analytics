import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY_ROOT / "scripts" / "prepare_fabric_deployment.py"


class PrepareFabricDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.source_dir = self.root / "fabric"
        self.output_dir = self.root / ".deployment" / "fabric"
        self.source_dir.mkdir()

        self.template_file = self.source_dir / "definition.txt"
        self.template_file.write_text(
            "\n".join(
                [
                    "workspace=__TARGET_WORKSPACE_ID__",
                    "lakehouse=__TARGET_LAKEHOUSE_ID__",
                    "workspace_name=__TARGET_WORKSPACE_NAME__",
                    "bronze_notebook=__BRONZE_TO_SILVER_NOTEBOOK_ID__",
                    "gold_notebook=__SILVER_TO_GOLD_NOTEBOOK_ID__",
                    "semantic_model=__TARGET_SEMANTIC_MODEL_ID__",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        fake_fab = self.bin_dir / "fab"
        fake_fab.write_text(
            f"""#!{sys.executable}
import sys

target = sys.argv[2]
if target.endswith("/lh_retail_analytics.Lakehouse"):
    print("target-lakehouse-id")
elif target.endswith("/nb_bronze_to_silver.Notebook"):
    print("bronze-notebook-id")
elif target.endswith("/nb_silver_to_gold.Notebook"):
    print("gold-notebook-id")
elif target.endswith("/sm_retail_analytics.SemanticModel"):
    print("semantic-model-id")
elif target.endswith(".Workspace"):
    print("target-workspace-id")
else:
    print(f"Unexpected target: {{target}}", file=sys.stderr)
    raise SystemExit(2)
""",
            encoding="utf-8",
        )
        fake_fab.chmod(fake_fab.stat().st_mode | stat.S_IXUSR)

        self.environment = os.environ.copy()
        self.environment["PATH"] = (
            f"{self.bin_dir}{os.pathsep}{self.environment['PATH']}"
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def run_script(self, *arguments):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            cwd=self.root,
            env=self.environment,
            capture_output=True,
            text=True,
        )

    def initialize(self, *extra_arguments):
        return self.run_script(
            "initialize",
            "--workspace",
            "Target Workspace",
            *extra_arguments,
        )

    def test_initialize_copies_templates_and_resolves_foundation_bindings(self):
        result = self.initialize()

        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = (self.output_dir / "definition.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn("workspace=target-workspace-id", rendered)
        self.assertIn("lakehouse=target-lakehouse-id", rendered)
        self.assertIn("workspace_name=Target Workspace", rendered)
        self.assertIn("__BRONZE_TO_SILVER_NOTEBOOK_ID__", rendered)
        self.assertIn("__TARGET_SEMANTIC_MODEL_ID__", rendered)
        self.assertIn("__TARGET_WORKSPACE_ID__", self.template_file.read_text())

    def test_initialize_refuses_to_replace_existing_output_without_force(self):
        self.assertEqual(self.initialize().returncode, 0)

        second_result = self.initialize()

        self.assertNotEqual(second_result.returncode, 0)
        self.assertIn("already exists", second_result.stderr)

    def test_initialize_force_rebuilds_output_from_clean_templates(self):
        self.assertEqual(self.initialize().returncode, 0)
        rendered_file = self.output_dir / "definition.txt"
        rendered_file.write_text("stale deployment content\n", encoding="utf-8")

        result = self.initialize("--force")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(
            "stale deployment content",
            rendered_file.read_text(encoding="utf-8"),
        )

    def test_bind_notebooks_resolves_both_imported_notebook_ids(self):
        self.assertEqual(self.initialize().returncode, 0)

        result = self.run_script(
            "bind-notebooks",
            "--workspace",
            "Target Workspace",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = (self.output_dir / "definition.txt").read_text()
        self.assertIn("bronze_notebook=bronze-notebook-id", rendered)
        self.assertIn("gold_notebook=gold-notebook-id", rendered)

    def test_bind_report_resolves_imported_semantic_model_id(self):
        self.assertEqual(self.initialize().returncode, 0)

        result = self.run_script(
            "bind-report",
            "--workspace",
            "Target Workspace",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = (self.output_dir / "definition.txt").read_text()
        self.assertIn("semantic_model=semantic-model-id", rendered)

    def test_validate_fails_until_every_placeholder_is_resolved(self):
        self.assertEqual(self.initialize().returncode, 0)

        unresolved_result = self.run_script("validate")

        self.assertNotEqual(unresolved_result.returncode, 0)
        self.assertIn("__BRONZE_TO_SILVER_NOTEBOOK_ID__", unresolved_result.stderr)
        self.assertIn("__TARGET_SEMANTIC_MODEL_ID__", unresolved_result.stderr)

        self.assertEqual(
            self.run_script(
                "bind-notebooks",
                "--workspace",
                "Target Workspace",
            ).returncode,
            0,
        )
        self.assertEqual(
            self.run_script(
                "bind-report",
                "--workspace",
                "Target Workspace",
            ).returncode,
            0,
        )

        valid_result = self.run_script("validate")
        self.assertEqual(valid_result.returncode, 0, valid_result.stderr)


if __name__ == "__main__":
    unittest.main()
