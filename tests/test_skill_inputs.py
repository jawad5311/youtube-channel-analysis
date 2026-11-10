import json
import tempfile
import unittest
from pathlib import Path

from src.analysis.skill_inputs import build_channel_categorization_data, prepare_skill_inputs


class SkillInputsTests(unittest.TestCase):
    def setUp(self):
        self.channel_data = {
            "snippet": {
                "title": "Kidney Coach",
                "description": "Naturopathic kidney health guidance.",
            }
        }
        self.recent_videos = [
            {
                "id": "v1",
                "snippet": {
                    "title": "Video 1 Title",
                    "description": "Video 1 Description",
                },
            },
            {
                "id": "v2",
                "snippet": {
                    "title": "Video 2 Title",
                    "description": "Video 2 Description",
                },
            },
        ]
        self.config = {
            "channel_categorization": {
                "skill_input_file": "data-for-channel-categorization.json",
                "channel_name": True,
                "channel_description": True,
                "total_videos": 50,
                "videos": [
                    {
                        "title": True,
                        "description": True,
                    }
                ],
            },
            "channel_niche_search": {},
            "channel_issues": {},
        }

    def test_build_channel_categorization_data(self):
        data = build_channel_categorization_data(
            self.channel_data,
            self.recent_videos,
            self.config["channel_categorization"],
        )
        self.assertEqual(data["channel_name"], "Kidney Coach")
        self.assertEqual(data["channel_description"], "Naturopathic kidney health guidance.")
        self.assertEqual(data["total_videos"], 2)
        self.assertEqual(len(data["videos"]), 2)
        self.assertEqual(data["videos"][0]["title"], "Video 1 Title")
        self.assertEqual(data["videos"][0]["description"], "Video 1 Description")

    def test_prepare_skill_inputs_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            cfg_file = run_dir / "test-config.json"
            cfg_file.write_text(json.dumps(self.config), encoding="utf-8")

            created = prepare_skill_inputs(
                run_dir=run_dir,
                channel_data=self.channel_data,
                recent_videos=self.recent_videos,
                config_path=cfg_file,
            )

            cat_file = run_dir / "normalized" / "data-for-channel-categorization.json"
            self.assertTrue(cat_file.exists())
            loaded = json.loads(cat_file.read_text(encoding="utf-8"))
            self.assertEqual(loaded["channel_name"], "Kidney Coach")
            self.assertEqual(len(loaded["videos"]), 2)


if __name__ == "__main__":
    unittest.main()

