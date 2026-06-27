// Web search is now handled ENTIRELY by the backend via the `web_search: true`
// flag on POST /query (Tavily integration — tools/websearch/tavily_search.py).
//
// The frontend just passes `web_search: true` in the query body and the
// backend returns web citations with `source_type: "web"` and a `url` field.
// No separate frontend web-search call needed.
//
// This file remains as a single place to check the feature flag, so components
// don't need to know backend details.

export const enabled = true  // web toggle is now live
