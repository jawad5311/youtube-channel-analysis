import json
import tempfile
import unittest
from pathlib import Path
from src.collectors.youtube_data_api import collect_channel, parse_channel_reference

class ParseChannelReferenceTests(unittest.TestCase):
    def test_handle_url(self):
        ref = parse_channel_reference("https://www.youtube.com/@GoogleDevelopers/videos")
        self.assertEqual((ref.filter_name, ref.filter_value), ("forHandle", "@GoogleDevelopers"))
    def test_channel_id_url(self):
        ref = parse_channel_reference("https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw")
        self.assertEqual((ref.filter_name, ref.filter_value), ("id", "UC_x5XG1OV2P6uZZ5FSM9Ttw"))
    def test_rejects_video_url(self):
        with self.assertRaises(ValueError): parse_channel_reference("https://www.youtube.com/watch?v=abc")

class CollectChannelTests(unittest.TestCase):
    def test_collects_channel_metadata_only(self):
        class FakeClient:
            request_count = 0
            calls = []

            def get(self, resource, **params):
                self.request_count += 1
                self.calls.append((resource, params))
                return {
                    "items": [{
                        "id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
                        "snippet": {"title": "Google Developers"},
                        "statistics": {"subscriberCount": "1000"},
                    }]
                }

        client = FakeClient()
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = collect_channel("@GoogleDevelopers", Path(tmpdir), client)
            collection = json.loads((run_dir / "normalized" / "collection.json").read_text(encoding="utf-8"))
            manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual([call[0] for call in client.calls], ["channels"])
        self.assertEqual(client.calls[0][1]["part"], "snippet,statistics,status,topicDetails,brandingSettings")
        self.assertEqual(
            client.calls[0][1]["fields"],
            "items(id,snippet(title,description,country),statistics(viewCount,subscriberCount,videoCount),"
            "topicDetails(topicIds,topicCategories),status(madeForKids),"
            "brandingSettings/channel(title,description,keywords,defaultLanguage,country))",
        )
        self.assertEqual(collection["collection_scope"], "channel_metadata")
        self.assertNotIn("playlist_items", collection)
        self.assertNotIn("videos", collection)
        self.assertEqual(manifest["collection_scope"], "channel_metadata")
        self.assertEqual(manifest["api_requests"], 1)

if __name__ == "__main__": unittest.main()
