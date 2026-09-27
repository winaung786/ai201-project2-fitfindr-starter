# FitFindr acceptance criteria

These targets were set before implementation testing. A try means one fresh call to `run_agent` with the named input; record the returned session and tool call log each time. For model behavior, disable any response cache during the five tries.

1. Given `vintage graphic tee under $30, size M` with the example wardrobe, the agent completes `search_listings`, `suggest_outfit`, and `create_fit_card` in that order and returns a nonempty fit card in at least **4 of 5** tries.
   **Why this target:** The three-step flow is the main experience. One transient model failure is tolerable if the remaining tries work, but a lower target would hide a recurring failure.

2. Given `designer ballgown size XXS under $5` with the example wardrobe, the agent stops after `search_listings`, leaves `selected_item`, `outfit_suggestion`, and `fit_card` as `None`, and says to change a keyword, size, or price in **5 of 5** tries.
   **Why this target:** An empty result is deterministic for the supplied data, so every run should stop and offer a useful next action.

3. In at least **5 of 5** successful runs of the query in criterion 1, the listing `id` in `session["selected_item"]` equals the `new_item_id` recorded for both `suggest_outfit` and `create_fit_card` in `session["tool_calls"]`.
   **Why this target:** State transfer is deterministic and must never switch items between tools. A single mismatch would make the advice and caption misleading.

4. In at least **4 of 5** successful runs of the query in criterion 1, the fit card is 1-4 sentences, contains the selected item's title or a recognizable title fragment, contains its exact dollar price and platform, and contains no wardrobe piece absent from the supplied wardrobe.
   **Why this target:** Exact wording can change across model calls, but these observable facts make the caption usable. Allowing one miss leaves room for model variability without making the standard trivial.

5. Given `vintage graphic tee under $30, size M` and `get_empty_wardrobe()`, at least **4 of 5** runs return a nonempty outfit suggestion that names the selected item and offers at least one type of pairing, without claiming a specific owned wardrobe piece.
   **Why this target:** New users need useful advice even before entering clothes. One imperfect model response in five is tolerable; routine failures would make the empty-wardrobe route unusable.
