import json
import tempfile
import unittest
from pathlib import Path

from src.analysis.categorization import build_categorization_request, save_category_result, validate_category_result


class CategorizationTests(unittest.TestCase):
    def test_accepts_only_allowed_category(self):
        self.assertEqual(validate_category_result("Healthcare\n"), "Healthcare")
        with self.assertRaises(ValueError):
            validate_category_result("Health")

    def test_builds_skill_handoff_from_generated_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "data-for-channel-categorization.json"
            input_path.write_text(json.dumps({
                "channel_name": "Kidney Coach",
                "channel_description": "A team of naturopathic doctors providing kidney care.",
                "videos": [{"title": "Kidney health", "description": "Kidney education"}],
            }), encoding="utf-8")
            request = build_categorization_request(input_path, Path("skills/youtube-channel-categorization.md"))
            self.assertEqual(request["skill"], "youtube-channel-categorization")
            self.assertIn("one label", request["output_contract"])

    def test_saves_validated_skill_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = save_category_result(Path(tmp), "Healthcare")
            self.assertEqual(json.loads(output.read_text())["category"], "Healthcare")
            self.assertEqual((Path(tmp) / "analysis/channel-categorization.txt").read_text(), "Healthcare\n")


if __name__ == "__main__":
    unittest.main()
