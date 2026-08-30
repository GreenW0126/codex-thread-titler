from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "restore_legacy_cache.py"
SPEC = importlib.util.spec_from_file_location("restore_legacy_cache", SCRIPT_PATH)
assert SPEC and SPEC.loader
RESTORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RESTORE)


class RestoreLegacyCacheTests(unittest.TestCase):
    def test_restores_runtime_files_without_tests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            destination = root / "cache" / "personal" / "plugin" / "old-version"
            (source / "scripts").mkdir(parents=True)
            (source / "tests").mkdir()
            (source / "scripts" / "thread_titler_hook.py").write_text("hook", encoding="utf-8")
            (source / "tests" / "test_hook.py").write_text("test", encoding="utf-8")

            with mock.patch.object(RESTORE, "plugin_root", return_value=source), mock.patch.object(
                RESTORE, "cache_root", return_value=(root / "cache").resolve()
            ):
                copied, unchanged = RESTORE.restore(destination)

            self.assertEqual((copied, unchanged), (1, 0))
            self.assertEqual(
                (destination / "scripts" / "thread_titler_hook.py").read_text(encoding="utf-8"),
                "hook",
            )
            self.assertFalse((destination / "tests").exists())

    def test_refuses_to_overwrite_conflicting_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            destination = root / "cache" / "personal" / "plugin" / "old-version"
            (source / "scripts").mkdir(parents=True)
            (destination / "scripts").mkdir(parents=True)
            (source / "scripts" / "thread_titler_hook.py").write_text("new", encoding="utf-8")
            (destination / "scripts" / "thread_titler_hook.py").write_text("old", encoding="utf-8")

            with mock.patch.object(RESTORE, "plugin_root", return_value=source), mock.patch.object(
                RESTORE, "cache_root", return_value=(root / "cache").resolve()
            ):
                with self.assertRaises(FileExistsError):
                    RESTORE.restore(destination)

            self.assertEqual(
                (destination / "scripts" / "thread_titler_hook.py").read_text(encoding="utf-8"),
                "old",
            )

    def test_rejects_destination_outside_codex_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            (source / "scripts").mkdir(parents=True)
            (source / "scripts" / "thread_titler_hook.py").write_text("hook", encoding="utf-8")

            with mock.patch.object(RESTORE, "plugin_root", return_value=source), mock.patch.object(
                RESTORE, "cache_root", return_value=(root / "cache").resolve()
            ):
                with self.assertRaises(ValueError):
                    RESTORE.restore(root / "outside")


if __name__ == "__main__":
    unittest.main()
