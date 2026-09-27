"""Command line interface for FitFindr. Run `python app.py --help`."""

import argparse
import json

from agent import run_agent
from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe, load_listings


EXAMPLE_QUERIES = [
    "vintage graphic tee under $30, size M",
    "90s track jacket size M",
    "black combat boots size 8",
    "designer ballgown size XXS under $5",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Find a thrift listing and style it.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    ask = subparsers.add_parser("ask", help="Run the complete agent")
    ask.add_argument("query", help="Quote the whole query, for example 'vintage graphic tee under $30'")
    ask.add_argument("--empty-wardrobe", action="store_true")
    ask.add_argument("--json", action="store_true", help="Print the entire session state")
    subparsers.add_parser("fields", help="Show listing and wardrobe field names")
    listings = subparsers.add_parser("listings", help="Inspect listing data")
    listings.add_argument("--full", action="store_true")
    listings.add_argument("-n", type=int, default=6)
    subparsers.add_parser("examples", help="Show example queries")
    tool = subparsers.add_parser("tool", help="Try one tool by itself")
    tool.add_argument("name", choices=["search", "outfit", "card"])
    tool.add_argument("--description", default="vintage graphic tee")
    tool.add_argument("--size", default=None)
    tool.add_argument("--max-price", type=float, default=None)
    tool.add_argument("--item-id", default="lst_002")
    tool.add_argument("--outfit", default="Pair it with baggy jeans and chunky white sneakers.")
    arguments = parser.parse_args()

    if arguments.command == "fields":
        print("Listing:", ", ".join(load_listings()[0].keys()))
        print("Wardrobe item:", ", ".join(get_example_wardrobe()["items"][0].keys()))
    elif arguments.command == "listings":
        selected = load_listings()[: max(0, arguments.n)]
        for item in selected:
            print(json.dumps(item, ensure_ascii=False) if arguments.full else f"{item['id']}: {item['title']} (${item['price']:.2f})" )
    elif arguments.command == "examples":
        for query in EXAMPLE_QUERIES:
            print(query)
    elif arguments.command == "tool":
        if arguments.name == "search":
            matches = search_listings(arguments.description, arguments.size, arguments.max_price)
            print(json.dumps({"count": len(matches), "first": matches[0] if matches else None}, ensure_ascii=False))
        else:
            item = next((listing for listing in load_listings() if listing["id"] == arguments.item_id), None)
            if item is None:
                parser.error(f"Unknown item ID: {arguments.item_id}")
            result = suggest_outfit(item, get_example_wardrobe()) if arguments.name == "outfit" else create_fit_card(arguments.outfit, item)
            print(result.replace("\n", " "))
    elif arguments.command == "ask":
        wardrobe = get_empty_wardrobe() if arguments.empty_wardrobe else get_example_wardrobe()
        session = run_agent(arguments.query, wardrobe)
        if arguments.json:
            print(json.dumps(session, ensure_ascii=False, indent=2))
        elif session["error"]:
            print(session["error"])
        else:
            item = session["selected_item"]
            print(f"Listing: {item['title']} | {item['size']} | ${item['price']:.2f} | {item['platform']}")
            print(f"Outfit: {session['outfit_suggestion']}")
            print(f"Fit card: {session['fit_card']}")


if __name__ == "__main__":
    main()
