import json
import tempfile
import unittest
from pathlib import Path

from src.collectors.youtube_recent_videos import collect_recent_videos


class RecentVideoCollectorTests(unittest.TestCase):
    def test_collects_recent_video_metadata(self):
        class FakeClient:
            request_count = 0

            def __init__(self):
                self.calls = []

            def get(self, resource, **params):
                self.request_count += 1
                self.calls.append((resource, params))
                if resource == "channels":
                    return {
                        "items": [{
                            "id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
                            "snippet": {"title": "Google Developers"},
                            "contentDetails": {"relatedPlaylists": {"uploads": "UU_uploads"}},
                        }]
                    }
                if resource == "playlistItems":
                    return {"items": [{"contentDetails": {"videoId": "video-1"}}]}
                return {
                    "items": [{
                        "id": "video-1",
                        "snippet": {"title": "Recent video", "description": "Description", "tags": ["keyword"]},
                        "contentDetails": {"duration": "PT12M", "caption": "true"},
                        "statistics": {"viewCount": "100"},
                    }],
                }

        client = FakeClient()
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = collect_recent_videos("@GoogleDevelopers", Path(tmpdir), client, limit=1)
            collection = json.loads((run_dir / "normalized" / "recent-videos.json").read_text(encoding="utf-8"))
            manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual([call[0] for call in client.calls], ["channels", "playlistItems", "videos"])
        self.assertEqual(collection["collection_scope"], "recent_videos")
        self.assertEqual(collection["videos"][0]["snippet"]["tags"], ["keyword"])
        self.assertEqual(collection["videos"][0]["contentDetails"]["duration"], "PT12M")
        self.assertEqual(manifest["videos_retrieved"], 1)
        self.assertTrue(manifest["quality_passed"])


if __name__ == "__main__":
    unittest.main()
