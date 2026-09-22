import unittest
from src.collectors.youtube_data_api import parse_channel_reference

class ParseChannelReferenceTests(unittest.TestCase):
    def test_handle_url(self):
        ref = parse_channel_reference("https://www.youtube.com/@GoogleDevelopers/videos")
        self.assertEqual((ref.filter_name, ref.filter_value), ("forHandle", "@GoogleDevelopers"))
    def test_channel_id_url(self):
        ref = parse_channel_reference("https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw")
        self.assertEqual((ref.filter_name, ref.filter_value), ("id", "UC_x5XG1OV2P6uZZ5FSM9Ttw"))
    def test_rejects_video_url(self):
        with self.assertRaises(ValueError): parse_channel_reference("https://www.youtube.com/watch?v=abc")

if __name__ == "__main__": unittest.main()
