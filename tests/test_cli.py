import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CommandLineTests(unittest.TestCase):
    def test_rejected_builds_report_failure_without_changing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / 'existing'
            existing.mkdir()
            marker = existing / 'keep'
            marker.write_text('unchanged')
            for args, output, message in [
                (['--svg', '--theme', 'does-not-exist'], root / 'unknown', 'unknown theme'),
                ([], root / 'missing', 'require at least one'),
                (['--svg'], existing, 'already exist'),
            ]:
                with self.subTest(args=args):
                    result = subprocess.run(
                        [
                            sys.executable,
                            '-B',
                            'src/cursor_utils.py',
                            *args,
                            '--out-dir',
                            str(output),
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertIn(message, result.stderr)
                    if output != existing:
                        self.assertFalse(output.exists())
                    self.assertEqual(marker.read_text(), 'unchanged')


if __name__ == '__main__':
    unittest.main()
