import os.path
from pathlib import Path
import sys
from typing import List

from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.lsp import DiagnosticsTypedDict
import typing


log = get_logger(__name__)


def _import_robocop():
    try:
        import robocop
    except ImportError:
        _parent_dir = os.path.dirname(__file__)
        _robocop_dir = os.path.join(_parent_dir, "libs", "robocop_lib")
        if not os.path.exists(_robocop_dir):
            raise RuntimeError("Expected: %s to exist." % (_robocop_dir,))
        sys.path.append(_robocop_dir)
        import robocop  # @UnusedImport

        log.info("Using vendored Robocop")

    log.info("Robocop module: %s", robocop)


def collect_robocop_diagnostics(
    project_root: Path, ast_model, filename: str, source: str
) -> List[DiagnosticsTypedDict]:
    _import_robocop()

    import robocop

    filename_parent = Path(filename).parent
    # Set the working directory to the project root (tricky handling: Robocop
    # relies on cwd to deal with the --ext-rules
    # See: https://github.com/robocorp/robotframework-lsp/issues/703).
    initial_cwd = os.getcwd()
    try:
        if os.path.exists(project_root):
            os.chdir(project_root)

        if hasattr(robocop, "Robocop"):
            # Legacy Robocop (<7.0)
            from robocop.config import Config
            from robocop.utils import issues_to_lsp_diagnostic

            if filename_parent.exists():
                config = Config(root=filename_parent)
            else:
                # Unsaved files.
                config = Config(root=project_root)
            robocop_runner = robocop.Robocop(config=config)
            robocop_runner.reload_config()

            issues = robocop_runner.run_check(ast_model, filename, source)
            diag_issues = typing.cast(
                List[DiagnosticsTypedDict], issues_to_lsp_diagnostic(issues)
            )
        else:
            # Robocop 7.0+
            from robocop.config import ConfigManager
            from robocop.linter.runner import RobocopLinter

            if filename_parent.exists():
                root = filename_parent
            else:
                root = project_root

            config_manager = ConfigManager(root=str(root))
            robocop_runner = RobocopLinter(config_manager)
            config = config_manager.get_default_config(None)

            # Monkeypatch Robocop 7.2.0 bug where it doesn't handle type hints without spaces (e.g. ${VAR:int})
            # See: https://github.com/MarketSquare/robotframework-robocop/issues/1065 (assumed/hypothetical issue)
            try:
                from robocop.linter.utils import misc

                def patched_remove_variable_type_conversion(name: str) -> str:
                    if ":" in name:
                        return name.split(":", 1)[0].strip()
                    return name

                misc.remove_variable_type_conversion = patched_remove_variable_type_conversion
            except (ImportError, AttributeError):
                pass

            issues = robocop_runner.run_check(
                model=ast_model,
                file_path=Path(filename),
                config=config,
                in_memory_content=source,
            )

            diag_issues = []
            for issue in issues:
                # Manual conversion to avoid import errors and bugs in Robocop 7.2.0 misc.py
                d: DiagnosticsTypedDict = {
                    "range": {
                        "start": {
                            "line": max(0, issue.range.start.line - 1),
                            "character": max(0, issue.range.start.character - 1),
                        },
                        "end": {
                            "line": max(0, issue.range.end.line - 1),
                            "character": max(0, issue.range.end.character - 1),
                        },
                    },
                    "severity": issue.severity.diag_severity(),
                    "code": issue.rule.rule_id,
                    "source": "robocop",
                    "message": issue.message,
                    "codeDescription": {"href": f"{issue.rule.docs_url}"},
                }
                diag_issues.append(d)

    finally:
        os.chdir(initial_cwd)
    return diag_issues
