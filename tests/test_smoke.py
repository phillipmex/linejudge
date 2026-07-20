import unittest

from linejudge import __version__
from linejudge.cli import main


class SmokeTests(unittest.TestCase):
    def test_version_string(self):
        self.assertTrue(__version__)

    def test_cli_version_exit_code(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["--version"])
        self.assertEqual(ctx.exception.code, 0)

    def test_cli_no_args_shows_help(self):
        self.assertEqual(main([]), 0)


if __name__ == "__main__":
    unittest.main()
