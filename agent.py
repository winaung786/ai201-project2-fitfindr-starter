"""FitFindr's stateful planning loop."""

import re

from tools import create_fit_card, search_listings, suggest_outfit


def _new_session(query: str, wardrobe: dict) -> dict:
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "tool_calls": [],
        "error": None,
    }


def _parse_query(query: str) -> dict:
    price_match = re.search(r"\b(?:under|below|max(?:imum)?)\s*\$?\s*(\d+(?:\.\d+)?)\b", query, re.I)
    size_match = re.search(r"\bsize\s+([A-Za-z0-9./-]+)", query, re.I)
    description = query
    for match in (price_match, size_match):
        if match:
            description = description.replace(match.group(0), " ")
    description = re.sub(r"\s+", " ", description.strip(" ,.!? ")).strip(" ,.!? ")
    return {
        "description": description,
        "size": size_match.group(1).rstrip(".,!?;:") if size_match else None,
        "max_price": float(price_match.group(1)) if price_match else None,
    }


def run_agent(query: str, wardrobe: dict) -> dict:
    """Choose each next tool from the current session and stop after three stages."""
    session = _new_session(query, wardrobe)
    if not query or not query.strip():
        session["error"] = "Describe an item to search for, such as 'vintage graphic tee under $30'."
        return session
    session["parsed"] = _parse_query(query)
    stage = "search"
    while stage:
        if stage == "search":
            session["tool_calls"].append({"tool": "search_listings", "inputs": session["parsed"].copy()})
            try:
                session["search_results"] = search_listings(**session["parsed"])
            except (OSError, ValueError, KeyError, TypeError):
                session["error"] = "The listings could not be loaded. Check the data file and try again."
                break
            if not session["search_results"]:
                session["error"] = (
                    "No listings match that request. Try changing a keyword, "
                    "choosing another size, or raising the price limit."
                )
                break
            session["selected_item"] = session["search_results"][0]
            stage = "outfit"
        elif stage == "outfit":
            item = session["selected_item"]
            session["tool_calls"].append({"tool": "suggest_outfit", "new_item_id": item["id"]})
            session["outfit_suggestion"] = suggest_outfit(item, session["wardrobe"])
            if not session["outfit_suggestion"] or not session["outfit_suggestion"].strip():
                session["error"] = "No outfit suggestion was produced for this listing."
                break
            stage = "card"
        elif stage == "card":
            item = session["selected_item"]
            session["tool_calls"].append({"tool": "create_fit_card", "new_item_id": item["id"]})
            session["fit_card"] = create_fit_card(session["outfit_suggestion"], item)
            stage = None
        else:
            session["error"] = "The agent reached an unknown step."
            break
    return session
