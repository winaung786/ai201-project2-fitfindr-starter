# FitFindr

## What This Does

FitFindr takes a plain-language request for a secondhand clothing item, such as `vintage graphic tee under $30, size M`. It searches the supplied 40-listing sample, picks the most relevant result that fits the size and price limits, suggests an outfit, and writes a short caption for that find. It uses the example wardrobe by default or gives general advice when the wardrobe is empty. If nothing matches, it stops after the search and explains what the user can change.

## Run It

Use Python 3.10 or newer from this repository. The command line app and tests use only the Python standard library, so `pip install -r requirements.txt` is optional. Copy `.env.example` to `.env` and add your `GEMINI_API_KEY` to get model-written outfit ideas and captions. The `.env` file is ignored by Git. Without a valid key or when the model service is unavailable, the two text tools produce a local fallback so the complete command still runs.

```text
python test.py
python app.py fields
python app.py listings --full -n 6
python app.py examples
python app.py ask 'vintage graphic tee under $30, size M'
python app.py ask 'designer ballgown size XXS under $5'
python app.py ask 'vintage graphic tee under $30, size M' --empty-wardrobe
python app.py ask 'vintage graphic tee under $30, size M' --json
```

Use single quotes around queries containing `$` in PowerShell. `--json` prints the complete session, including the selected listing and the record of tool calls. The listing data is a fixed classroom sample, not a live marketplace feed. The model default is `gemini-3.5-flash-lite`; set `FITFINDR_MODEL` in your environment to choose another available Gemini model.

## Tool Inventory

### `search_listings(description: str, size: str | None = None, max_price: float | None = None) -> list[dict]`

- **Does:** Filters the supplied listings by size and inclusive price cap, then ranks them by overlap with item and style words.
- **Inputs:** `description` (`str`) is the requested item text; `size` (`str | None`) is an optional garment or shoe size; `max_price` (`float | None`) is an optional dollar ceiling.
- **Returns:** A relevance-ordered list of listing dictionaries, each with `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.
- **Nothing to give:** Returns `[]`, including when no item words match. It does not send an empty result into the outfit tool.

### `suggest_outfit(new_item: dict, wardrobe: dict) -> str`

- **Does:** Sends the chosen item and available wardrobe pieces to the text model for one outfit idea.
- **Inputs:** `new_item` (`dict`) is one listing from search; `wardrobe` (`dict`) contains an `items` list of wardrobe item dictionaries.
- **Returns:** A nonempty outfit suggestion string naming the selected item and, when available, owned pieces.
- **Nothing to give:** With an empty wardrobe, it suggests general pairings. If the model is unavailable, it uses a local suggestion built from the item and supplied wardrobe.

### `create_fit_card(outfit: str, new_item: dict) -> str`

- **Does:** Sends the outfit and the same selected listing to the text model for a short social caption.
- **Inputs:** `outfit` (`str`) is the outfit tool's result; `new_item` (`dict`) is the selected listing.
- **Returns:** A short caption string naming the listing, exact price, and platform. A response missing those facts or claiming the wearer is the seller is replaced with a local caption.
- **Nothing to give:** A blank `outfit` returns `Cannot create a fit card without an outfit suggestion.`

## Planning Loop

The branch is in `agent.py::run_agent`: after `search_listings`, an empty list sets a helpful message in `session["error"]` and stops. Otherwise the loop stores the first result in `session["selected_item"]`, reads it back for `suggest_outfit`, stores the returned text, and reads both values back for `create_fit_card`. The loop has only three stages: search, outfit, and card. `session["tool_calls"]` records the order and the selected listing ID passed to the later tools.

The parser takes `under $N` and `size N` from the request and leaves the remaining description for search. Search ranks title words above style tags and description words. When the request contains a garment type such as `tee`, it requires that type to appear in the listing data so a broad style word such as `vintage` does not select an unrelated item. The choice is deterministic for the same dataset; the model-written text can vary between runs.

## Sample Run

This full run used a valid Gemini key. Model wording may differ on another run.

```text
> python app.py ask 'vintage graphic tee under $30, size M'
Listing: Y2K Baby Tee — Butterfly Print | S/M | $18.00 | depop
Outfit: Pair the Y2K Baby Tee — Butterfly Print with baggy straight-leg jeans in dark wash, a brown leather belt, and chunky white sneakers. Complete the look with the black crossbody bag for an effortless throwback vibe.
Fit card: Thrifting this Y2K Baby Tee — Butterfly Print was such a massive win for only $18.00 on depop. I styled it with dark wash baggy straight-leg jeans, a brown leather belt, and chunky white sneakers, finishing it off with my black crossbody bag. It gives off the absolute best effortless throwback vibe.
```

Each tool was also run independently:

```text
> python app.py tool search --description 'vintage graphic tee' --size M --max-price 30
{"count": 2, "first": {"id": "lst_002", "title": "Y2K Baby Tee — Butterfly Print", "description": "Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.", "category": "tops", "style_tags": ["y2k", "vintage", "graphic tee", "cottagecore"], "size": "S/M", "condition": "excellent", "price": 18.0, "colors": ["white", "pink", "purple"], "brand": null, "platform": "depop"}}
> python app.py tool outfit --item-id lst_002
Pair the Y2K Baby Tee — Butterfly Print with baggy straight-leg jeans in dark wash, finished with chunky white sneakers and a black crossbody bag.
> python app.py tool card --item-id lst_002 --outfit 'Pair it with baggy jeans and chunky white sneakers.'
Scored this vintage Y2K Baby Tee — Butterfly Print secondhand on depop for just $18.00! It looks so good paired with baggy jeans and chunky white sneakers.
```

The no-match path is visible from the command line too:

```text
> python app.py ask 'designer ballgown size XXS under $5'
No listings match that request. Try changing a keyword, choosing another size, or raising the price limit.
```

## How I Used AI

I asked Codex to implement the three tool contracts from `planning.md` and to check the search against the supplied listings. Its first search for `vintage graphic tee` returned eight matches, including items matched only by `vintage`. I changed the search to require the requested garment type when one is present; the same command then returned two tee listings, with `lst_002` first.

I asked Codex to run the outfit and caption tools with the existing Gemini key. The first model request returned HTTP 404 because the adapter's default model name was unavailable, so I changed it to the model already configured in the earlier AI201 project and reran a complete query. A standalone caption then claimed the wearer had listed the item for sale, so I tightened the prompt and added a check that replaces such text with a local caption. Codex also drafted the three new criteria in `criteria.md`; they are explicit targets to review and defend for the next unit.

## Interaction Walkthrough

For `vintage graphic tee under $30, size M`, `search_listings` receives `description="vintage graphic tee"`, `size="M"`, and `max_price=30.0`. The top listing is `lst_002`, which the agent saves in `session["selected_item"]`. `suggest_outfit` receives that listing and the example wardrobe; `create_fit_card` receives the stored outfit text and the same listing. The user sees the listing, outfit, and caption shown above. If the search returns `[]`, neither text tool runs.

## Error Handling and Fail Points

| Tool | Failure mode | Agent response |
| --- | --- | --- |
| `search_listings` | No matches | Stop and suggest changing a keyword, size, or price. |
| `search_listings` | Data file cannot load | Return a readable error in the session. |
| `suggest_outfit` | Empty wardrobe | Give general pairing advice without claiming owned clothes. |
| `suggest_outfit` or `create_fit_card` | Model unavailable | Return local text based on the actual listing and wardrobe. |
| `create_fit_card` | Blank outfit | Return a descriptive error string. |

## Spec Reflection

Writing the `[]` search contract before coding made the branch straightforward: the agent can stop immediately and leave `fit_card` as `None`. Keeping the selected listing in the session also made it possible to check that the item ID passed to both later tools is identical.

The plan called for model-written outfit and caption text, but I added local fallbacks after testing the service connection. This keeps the command usable without a key while still calling the model when one is available. The caption also validates the model output against the listing's title, price, and platform because a fluent caption can still state the wrong facts.
