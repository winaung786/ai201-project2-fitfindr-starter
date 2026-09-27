"""Tests for the search branch, state transfer, and generated text contracts."""

import unittest
from unittest.mock import patch

from agent import _parse_query, run_agent
from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


class FitFindrTests(unittest.TestCase):
    def test_query_parser_extracts_filters(self):
        self.assertEqual(
            _parse_query("vintage graphic tee under $30, size M"),
            {"description": "vintage graphic tee", "size": "M", "max_price": 30.0},
        )

    def test_search_filters_price_and_size_and_ranks_relevant_result(self):
        matches = search_listings("vintage graphic tee", "M", 30.0)
        self.assertTrue(matches)
        self.assertEqual(matches[0]["id"], "lst_002")
        self.assertNotIn("lst_017", [item["id"] for item in matches])
        self.assertTrue(all(item["price"] <= 30 and item["size"] in {"M", "S/M", "M/L"} for item in matches))
        self.assertEqual(search_listings("designer ballgown", "XXS", 5.0), [])

    def test_empty_search_does_not_call_later_tools(self):
        with patch("agent.suggest_outfit") as outfit, patch("agent.create_fit_card") as card:
            session = run_agent("designer ballgown size XXS under $5", get_example_wardrobe())
        outfit.assert_not_called()
        card.assert_not_called()
        self.assertEqual([call["tool"] for call in session["tool_calls"]], ["search_listings"])
        self.assertIsNone(session["fit_card"])
        self.assertIn("size", session["error"])

    def test_full_run_passes_same_item_through_session(self):
        with patch("tools.generate_text", side_effect=[
            "For the Y2K Baby Tee — Butterfly Print: pair it with baggy jeans and chunky white sneakers.",
            "Y2K Baby Tee — Butterfly Print for $18.00 on depop. Baggy jeans and chunky sneakers make it easy.",
        ]) as model:
            session = run_agent("vintage graphic tee under $30, size M", get_example_wardrobe())
        self.assertIsNone(session["error"])
        self.assertEqual(model.call_count, 2)
        self.assertEqual(
            [call["tool"] for call in session["tool_calls"]],
            ["search_listings", "suggest_outfit", "create_fit_card"],
        )
        selected_id = session["selected_item"]["id"]
        self.assertEqual(session["tool_calls"][1]["new_item_id"], selected_id)
        self.assertEqual(session["tool_calls"][2]["new_item_id"], selected_id)
        self.assertIn("$18.00", session["fit_card"])

    def test_empty_wardrobe_and_missing_model_still_produce_advice(self):
        item = search_listings("vintage graphic tee", "M", 30.0)[0]
        with patch("tools.generate_text", side_effect=__import__("model_adapter").ModelUnavailable("offline")):
            outfit = suggest_outfit(item, get_empty_wardrobe())
            card = create_fit_card(outfit, item)
        self.assertIn(item["title"], outfit)
        self.assertIn("jeans", outfit.lower())
        self.assertIn("$18.00", card)
        self.assertEqual(create_fit_card("", item), "Cannot create a fit card without an outfit suggestion.")


if __name__ == "__main__":
    unittest.main()
