import hashlib
import importlib.util
import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = (
    Path(__file__).parents[1]
    / "skills/setup-complexity-cli/scripts/setup_complexity.py"
)
SPEC = importlib.util.spec_from_file_location("setup_complexity", SCRIPT)
assert SPEC and SPEC.loader
setup_complexity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup_complexity)

CHECKER_SCRIPT = (
    Path(__file__).parents[1]
    / "skills/complexity-cli/scripts/check_complexity.py"
)
CHECKER_SPEC = importlib.util.spec_from_file_location("check_complexity", CHECKER_SCRIPT)
assert CHECKER_SPEC and CHECKER_SPEC.loader
check_complexity = importlib.util.module_from_spec(CHECKER_SPEC)
CHECKER_SPEC.loader.exec_module(check_complexity)


class SetupComplexityTests(unittest.TestCase):
    def test_missing_binary_routes_to_setup_skill(self):
        with patch.object(check_complexity, "default_binaries", return_value=[]):
            with self.assertRaisesRegex(RuntimeError, r"\$setup-complexity-cli"):
                check_complexity.locate_binary(None)

    def test_selects_supported_release_target(self):
        with patch.object(setup_complexity.platform, "system", return_value="Darwin"):
            with patch.object(setup_complexity.platform, "machine", return_value="arm64"):
                self.assertEqual(setup_complexity.target(), "aarch64-apple-darwin")

    def test_verifies_release_checksum(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "complexity.tar.gz"
            checksum = root / "complexity.tar.gz.sha256"
            archive.write_bytes(b"release")
            digest = hashlib.sha256(b"release").hexdigest()
            checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")

            setup_complexity.verify_checksum(archive, checksum)

    def test_reads_only_executable_from_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "complexity.tar.gz"
            contents = b"executable"
            with tarfile.open(archive, mode="w:gz") as release:
                member = tarfile.TarInfo("complexity-0.4.0-target/complexity")
                member.size = len(contents)
                release.addfile(member, io.BytesIO(contents))

            self.assertEqual(
                setup_complexity.binary_bytes(archive, "complexity"), contents
            )


if __name__ == "__main__":
    unittest.main()
