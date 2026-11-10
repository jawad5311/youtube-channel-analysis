import unittest

from src.analysis.quick_channel import analyze_quick_channel, canonical_channel_url, readable_country, render_quick_analysis


class QuickChannelAnalysisTests(unittest.TestCase):
    def test_country_names_use_crm_friendly_labels(self):
        self.assertEqual(readable_country("US"), "United States")
        self.assertEqual(readable_country("GB"), "United Kingdom")
        self.assertEqual(readable_country("AU"), "Australia")

    def test_channel_url_is_normalized_to_homepage(self):
        self.assertEqual(canonical_channel_url("https://www.youtube.com/@kidneycoach/videos"),
                         "youtube.com/@kidneycoach")

    def test_classifies_health_channel_and_finds_no_metadata_issue(self):
        analysis = analyze_quick_channel({
            "collection_scope": "channel_metadata",
            "channel": {
                "id": "UC123",
                "snippet": {
                    "title": "Kidney Coach",
                    "description": "Evidence-based kidney health education for people managing chronic kidney disease, including practical guidance on lab results, nutrition, treatment questions, and long-term lifestyle decisions.",
                    "country": "AU",
                },
                "topicDetails": {"topicCategories": ["https://en.wikipedia.org/wiki/Health"]},
                "brandingSettings": {"channel": {"keywords": "kidney health chronic kidney disease"}},
            },
        })

        self.assertEqual(analysis["channel_niches"], ["Health"])
        self.assertEqual(analysis["channel_category"], "Health")
        self.assertEqual(analysis["channel_issues"], [])
        self.assertIn("No metadata-level channel issues", render_quick_analysis(analysis))

    def test_reports_missing_metadata_as_issues(self):
        analysis = analyze_quick_channel({"channel": {"id": "UC123", "snippet": {"title": "Example"}}})

        self.assertEqual(analysis["channel_niches"], ["Unclear"])
        self.assertGreaterEqual(len(analysis["channel_issues"]), 3)


if __name__ == "__main__":
    unittest.main()
