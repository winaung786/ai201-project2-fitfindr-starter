"""The three FitFindr tools. Each can be called independently."""

import re

from model_adapter import ModelUnavailable, generate_text
from utils.data_loader import load_listings


_STOP_WORDS = {"a", "an", "and", "for", "i", "in", "looking", "me", "of", "the", "want", "with"}
_ITEM_WORDS = {"tee", "jacket", "skirt", "boot", "jean", "pant", "top", "shirt", "dress", "hoodie", "sneaker", "bag", "belt", "cardigan", "blazer", "vest", "trouser", "sweatshirt", "hat", "flannel", "polo", "short"}


def _words(text: str) -> set[str]:
    words = set(re.findall(r"[a-z0-9]+", text.lower().replace("t-shirt", "tee"))) - _STOP_WORDS
    aliases = {"tees": "tee", "tshirt": "tee", "tshirts": "tee", "jeans": "jean", "pants": "pant", "boots": "boot", "sneakers": "sneaker", "trousers": "trouser", "shorts": "short"}
    return {aliases.get(word, word) for word in words}


def _size_matches(wanted: str, actual: str) -> bool:
    wanted = wanted.strip().upper()
    actual = actual.upper()
    if wanted in {"XXS", "XS", "S", "M", "L", "XL", "XXL"}:
        return bool(re.search(rf"(?<![A-Z]){re.escape(wanted)}(?![A-Z])", actual))
    return bool(re.search(rf"(?<![A-Z0-9.]){re.escape(wanted)}(?![A-Z0-9.])", actual))


def search_listings(
    description: str, size: str | None = None, max_price: float | None = None
) -> list[dict]:
    """Return relevant listing dictionaries satisfying optional size and price limits."""
    query_words = _words(description)
    if not query_words:
        return []
    scored = []
    for listing in load_listings():
        if max_price is not None and float(listing["price"]) > max_price:
            continue
        if size and not _size_matches(size, listing["size"]):
            continue
        title_words = _words(listing["title"])
        tag_words = _words(" ".join(listing["style_tags"]))
        other_words = _words(" ".join([
            listing["description"], listing["category"],
            " ".join(listing["colors"]), listing.get("brand") or "",
        ]))
        item_words = query_words & _ITEM_WORDS
        # A description may mention another garment (for example, a mesh top
        # advertised as layering under a graphic tee). It is not that item.
        if item_words and not item_words & (title_words | tag_words):
            continue
        score = 3 * len(query_words & title_words) + 2 * len(query_words & tag_words) + len(query_words & other_words)
        if score:
            scored.append((score, listing))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["price"], pair[1]["id"]))
    return [listing for _, listing in scored]


def _fallback_outfit(new_item: dict, wardrobe_items: list[dict]) -> str:
    title = new_item["title"]
    category = new_item["category"]
    wanted_categories = ["bottoms", "shoes"] if category == "tops" else ["tops", "shoes"]
    if category == "shoes":
        wanted_categories = ["tops", "bottoms"]
    owned = []
    for wanted in wanted_categories:
        match = next((item["name"] for item in wardrobe_items if item["category"] == wanted), None)
        if match:
            owned.append(match)
    if owned:
        return f"Wear the {title} with {' and '.join(owned)} for an easy secondhand look."
    return f"Pair the {title} with relaxed jeans and clean sneakers for an easy everyday look."


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """Suggest an outfit using a model, with useful advice for an empty wardrobe."""
    items = wardrobe.get("items", [])
    names = [item["name"] for item in items]
    if names:
        context = "Available owned pieces: " + "; ".join(names)
        rule = "Use only these named owned pieces. Suggest one outfit with the new item."
    else:
        context = "The user's wardrobe is empty."
        rule = "Give general pairing ideas, but do not claim the user owns any clothes."
    prompt = (
        f"You are a concise thrift stylist. New item: {new_item['title']} "
        f"({new_item['category']}; colors: {', '.join(new_item['colors'])}). "
        f"{context} {rule} Name the new item and keep the answer to 1-2 sentences."
    )
    try:
        result = generate_text(prompt, temperature=0.6).strip()
        return result if new_item["title"].lower() in result.lower() else f"For the {new_item['title']}: {result}"
    except ModelUnavailable:
        return _fallback_outfit(new_item, items)


def create_fit_card(outfit: str, new_item: dict) -> str:
    """Write a short caption for the selected listing and outfit."""
    if not outfit or not outfit.strip():
        return "Cannot create a fit card without an outfit suggestion."
    title = new_item["title"]
    price = f"${float(new_item['price']):.2f}"
    platform = new_item["platform"]
    prompt = (
        "Write a casual social-media outfit caption in 1-3 sentences. "
        f"Mention this exact item title once: {title}. Mention its exact price {price} "
        f"and platform {platform} once each. Outfit: {outfit}. "
        "The wearer found this secondhand item and is not its seller. Do not say they "
        "listed it, are selling it, or own the listing. Use specific style details, "
        "no invented wardrobe pieces, and no hashtags."
    )
    try:
        result = generate_text(prompt, temperature=0.9).strip()
        seller_claim = re.search(r"\b(?:i|we)\s+(?:just\s+)?(?:listed|sell|selling)\b", result, re.I)
        if not seller_claim and title.lower() in result.lower() and price in result and platform.lower() in result.lower():
            return result
    except ModelUnavailable:
        pass
    outfit_text = re.sub(rf"\bthe\s+{re.escape(title)}", "it", outfit.strip(), count=1, flags=re.I)
    return f"Found {title} for {price} on {platform}. {outfit_text}"
