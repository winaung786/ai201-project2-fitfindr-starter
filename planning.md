# FitFindr plan

## Tools

### `search_listings(description: str, size: str | None, max_price: float | None) -> list[dict]`

- **Does:** Loads the supplied listing data with `load_listings()`, applies size and price filters, then ranks text matches.
- **Inputs:** `description` is the item and style keywords; `size` is an optional garment or shoe size; `max_price` is an optional inclusive dollar limit.
- **Returns:** Listing dictionaries in relevance order. Each has `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.
- **Empty case:** Returns `[]`. The agent then tells the user to change a keyword, size, or price limit.

### `suggest_outfit(new_item: dict, wardrobe: dict) -> str`

- **Does:** Asks the text model for an outfit around the selected listing using named pieces from `wardrobe["items"]`.
- **Inputs:** `new_item` is one complete listing dictionary; `wardrobe` is a dictionary with an `items` list.
- **Returns:** A nonempty outfit suggestion string. With an empty wardrobe, the model gives general pairing advice without pretending the user owns pieces.
- **Failure case:** If the model is unavailable, a local styling suggestion keeps the command usable.

### `create_fit_card(outfit: str, new_item: dict) -> str`

- **Does:** Asks the text model for a short social caption describing the selected item and outfit.
- **Inputs:** `outfit` is the previous tool's string; `new_item` is the same listing dictionary.
- **Returns:** A short caption string mentioning the actual item, price, and platform.
- **Empty case:** If `outfit` is blank, returns an explanatory error string. If the model is unavailable, returns a local caption.

## Planning loop and state

`agent.py::run_agent` parses the query and stores the filters in `session["parsed"]`. It calls `search_listings` and writes the list into `session["search_results"]`. If the list is empty, it sets `session["error"]` and stops. Otherwise it stores the first listing in `session["selected_item"]`, reads that item back from the session for `suggest_outfit`, stores the outfit in `session["outfit_suggestion"]`, then reads both session values back for `create_fit_card`. It stores the caption in `session["fit_card"]` and stops. The finite set of stages also bounds the number of tool calls.

The query parser uses regular expressions for `under $N` and `size N`, leaving the remaining words as the description. This avoids spending a model call to parse simple search filters. The visible session includes `tool_calls` so the next unit can check that the empty path stopped and that the same listing ID moved through both later calls.

## Error handling

| Tool | Failure mode | Agent response |
| --- | --- | --- |
| `search_listings` | No listing matches all filters | Stop before outfit generation and suggest relaxing one filter. |
| `suggest_outfit` | Wardrobe is empty | Request general advice instead of naming owned pieces. |
| `suggest_outfit` or `create_fit_card` | Model key or service unavailable | Use a deterministic local fallback. |
| `create_fit_card` | Outfit input is blank | Return a clear error string; the agent does not present it as a caption. |

## Architecture

```text
query + wardrobe
       |
       v
parse filters -> session.parsed
       |
       v
search_listings -> session.search_results
       |                       |
       | []                    | one or more
       v                       v
session.error; stop     session.selected_item
                               |
                               v
                       suggest_outfit
                               |
                               v
                    session.outfit_suggestion
                               |
                               v
                       create_fit_card
                               |
                               v
                       session.fit_card; stop
```

## How AI assistance will be checked

I will compare any suggested search implementation against the specified `[]` empty result and all three filters. I will check generated outfit and caption text against the exact listing selected in the session, and use local tests with a simulated model to verify the prompts and state flow. A real model run, when a key and network are available, checks the complete user experience.

## Example interaction

For `vintage graphic tee under $30, size M`, the parser stores the description, `M`, and `30.0`. Search returns matching listing dictionaries and the first one becomes `selected_item`. Outfit generation receives that exact listing and the supplied wardrobe. Caption generation receives the stored outfit and same listing. The user sees the listing, outfit idea, and fit card. If search returns `[]`, the user sees only a suggestion to relax the request.
