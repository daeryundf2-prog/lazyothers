#!/usr/bin/env python3
import json
import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.query_dev_resources import search_resources, list_summary, DEV_RESOURCES_DATA


class TestDevResources(unittest.TestCase):
    def test_list_summary(self):
        summary = list_summary()
        self.assertIn("free-for-dev", summary)
        self.assertIn("public-apis.io", summary)
        self.assertIn("daily-dev", summary)
        self.assertIn("devresourc.es", summary)

    def test_search_query(self):
        result = search_resources(query="postgres")
        self.assertTrue("Supabase" in result or "Neon" in result or "Render" in result)
        self.assertTrue("PostgreSQL" in result or "postgres" in result.lower())

    def test_search_platform(self):
        result = search_resources(platform="free-for-dev")
        self.assertIn("Vercel", result)
        self.assertIn("Platform: `free-for-dev`", result)

    def test_search_json(self):
        json_output = search_resources(query="Vercel", as_json=True)
        data = json.loads(json_output)
        self.setIsInstance(data, list) if hasattr(self, 'setIsInstance') else self.assertTrue(isinstance(data, list))
        self.assertGreaterEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Vercel")
        self.assertEqual(data[0]["platform"], "free-for-dev")

    def test_search_no_results(self):
        result = search_resources(query="nonexistent_xyz_12345")
        self.assertIn("찾을 수 없습니다", result)


if __name__ == "__main__":
    unittest.main()
