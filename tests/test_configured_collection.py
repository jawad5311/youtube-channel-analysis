import json
import tempfile
import unittest
from pathlib import Path

from src.collectors.configured_collection import collect_configured, load_profile
from src.analysis.skill_inputs import prepare_skill_inputs


class FakeClient:
    def __init__(self):
        self.calls = []
        self.request_count = 0

    def get(self, resource, **params):
        self.calls.append((resource, params))
        self.request_count += 1
        if resource == "channels":
            return {"items": [{"id": "UCexample", "snippet": {"title": "Example", "description": "About"},
                               "contentDetails": {"relatedPlaylists": {"uploads": "UUexample"}}}]}
        if resource == "playlistItems":
            if params.get("pageToken"):
                return {"items": [{"contentDetails": {"videoId": "short"}}]}
            return {"items": [{"contentDetails": {"videoId": "long"}}], "nextPageToken": "page2"}
        if resource == "videos":
            short = params["id"] == "short"
            return {"items": [{"id": params["id"], "snippet": {"title": "Short" if short else "Long",
                               "description": "Description", "publishedAt": "2026-10-01T00:00:00Z"},
                               "contentDetails": {"duration": "PT30S" if short else "PT15M"},
                               "statistics": {"viewCount": "123"}}]}
        if resource == "playlists":
            return {"items": [{"id": "p", "status": {"privacyStatus": "public"},
                               "snippet": {"title": "Series", "description": "Playlist description"},
                               "contentDetails": {"itemCount": 2}}]}
        raise AssertionError(resource)


class ConfiguredCollectionTests(unittest.TestCase):
    def profile(self):
        return {"channel": {"name": True, "description": True},
                "videos": {"limit": 1, "fields": ["title", "duration", "viewCount"]},
                "shorts": {"limit": 1, "fields": ["title", "publishedAt"]},
                "playlists": {"enabled": True, "fields": ["title", "description", "itemCount"]},
                "community_posts": {"enabled": True, "source": "browser", "limit": 10, "fields": ["text"]},
                "max_uploads_to_scan": 300}

    def test_collects_pages_fields_and_marks_browser_pending(self):
        client = FakeClient()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(self.profile()), encoding="utf-8")
            run, data = collect_configured("@example", Path(tmp), client, path)
            self.assertEqual(data["videos"][0], {"snippet": {"title": "Long"},
                             "contentDetails": {"duration": "PT15M"}, "statistics": {"viewCount": "123"}})
            self.assertNotIn("id", data["shorts_candidates"][0])
            self.assertNotIn("contentDetails", data["shorts_candidates"][0])
            self.assertEqual(data["playlists"][0]["itemCount"], 2)
            self.assertIn(data["community_posts"]["status"], {"http_failed", "http_no_data", "http_no_posts"})
            self.assertTrue((run / "browser-collection-request.json").exists())
            video_request = next(params for resource, params in client.calls if resource == "videos")
            self.assertIn("statistics", video_request["part"])
            self.assertNotIn("snippet(duration", video_request["fields"])
            inputs = Path(tmp) / "inputs.json"
            inputs.write_text(json.dumps({
                "channel_niche_search": {"channel_name": True, "videos": [{"title": True, "description": False}]},
                "channel_issues": {"shorts": [{"publishedAt": True}], "playlists": [{"itemCount": True}],
                                   "community_posts": [{"text": True}]} }), encoding="utf-8")
            files = prepare_skill_inputs(run, data["channel"], data["videos"], inputs, data)
            niche = json.loads(files["niche_search"].read_text())
            self.assertEqual(niche["videos"], [{"title": "Long"}])
            issues = json.loads(files["issues"].read_text())
            self.assertEqual(issues["total_shorts"], 1)
            self.assertRegex(issues["analysis_date"], r"^[A-Z][a-z]{2} - \d{2} - [A-Z][a-z]{2} - \d{2}$")
            self.assertIn(issues["community_status"], {"http_failed", "http_no_data", "http_no_posts"})

    def test_scan_cap_prevents_second_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = self.profile()
            profile["max_uploads_to_scan"] = 1
            profile["playlists"]["enabled"] = False
            profile["community_posts"]["enabled"] = False
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(profile), encoding="utf-8")
            client = FakeClient()
            _, data = collect_configured("@example", Path(tmp), client, path)
            self.assertEqual(data["collection_metadata"]["uploads_scanned"], 1)
            self.assertEqual(len(data["shorts_candidates"]), 1)
            self.assertEqual(sum(r == "playlistItems" for r, _ in client.calls), 3)

    def test_current_profile_supported(self):
        self.assertEqual(load_profile()["max_uploads_to_scan"], 300)

    def test_disabled_collections_make_no_extra_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"channel": {"name": True}}), encoding="utf-8")
            client = FakeClient()
            collect_configured("@example", Path(tmp), client, path)
            self.assertEqual([r for r, _ in client.calls], ["channels"])


if __name__ == "__main__":
    unittest.main()
