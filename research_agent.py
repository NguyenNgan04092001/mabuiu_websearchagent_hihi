#!/usr/bin/env python3

import typing as t
import argparse, json, os, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import httpx
from dotenv import load_dotenv
from openai import OpenAI
from tavily import TavilyClient

load_dotenv()


# -------------------------------------------------------------------------
# Helper: Get API keys from Streamlit Secrets or environment
# -------------------------------------------------------------------------

def get_secret(key: str, default: str = None) -> str:
    """
    Get secret from Streamlit st.secrets (production) or os.getenv (local).
    Safe fallback if Streamlit is not available.
    """
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except (ImportError, AttributeError):
        pass
    return os.getenv(key, default)


# -------------------------------------------------------------------------
# Domain presets (for Tavily include_domains filtering)
# -------------------------------------------------------------------------

ACADEMIC_DOMAINS = [
    "scholar.google.com",
    "semanticscholar.org",
    "openalex.org",
    "core.ac.uk",
    "base-search.net",
    "jstor.org",
    "ssrn.com",
    "doaj.org",
]

IR_DOMAINS_RU = [
    "cyberleninka.ru",
    "elibrary.ru",
    "istina.msu.ru",
    "dissercat.com",
    "mgimo.ru",
    "hse.ru",
    "russiancouncil.ru",
    "valdaiclub.com",
    "globalaffairs.ru",
    "carnegie.ru",
]

IR_DOMAINS_EN = [
    "cfr.org",
    "brookings.edu",
    "rand.org",
    "chathamhouse.org",
    "carnegieendowment.org",
    "csis.org",
    "sipri.org",
    "iiss.org",
    "ecfr.eu",
    "ifri.org",
    "swp-berlin.org",
    "un.org",
    "digitallibrary.un.org",
    "worldbank.org",
    "imf.org",
    "oecd.org",
    "nato.int",
    "foreignaffairs.com",
    "foreignpolicy.com",
    "thediplomat.com",
    "lawfaremedia.org",
    "warontherocks.com",
    "responsiblestatecraft.org",
]

IR_DOMAINS_MIXED = ACADEMIC_DOMAINS + IR_DOMAINS_EN + IR_DOMAINS_RU

SOURCE_PRESETS: dict[str, list[str]] = {
    "General web": [],
    "IR — Mixed (EN + RU)": IR_DOMAINS_MIXED,
    "IR — English only": ACADEMIC_DOMAINS + IR_DOMAINS_EN,
    "IR — Russian only": ACADEMIC_DOMAINS + IR_DOMAINS_RU,
    "Academic only": ACADEMIC_DOMAINS,
}


def _log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)


def _decode_inverted_abstract(idx: t.Optional[dict]) -> str:
    """OpenAlex stores abstracts as {word: [positions]} — reconstruct linear text."""
    if not idx:
        return ""
    positions: list[tuple[int, str]] = []
    for word, locs in idx.items():
        for loc in locs:
            positions.append((loc, word))
    positions.sort()
    return " ".join(w for _, w in positions)


class ResearchAgent:
    """LLM‑powered researcher combining Tavily + Semantic Scholar + OpenAlex."""

    def __init__(
        self,
        model: str = "o3",
        topn: int = 10,
        debug: bool = False,
        openai_key: t.Optional[str] = None,
        tavily_key: t.Optional[str] = None,
        base_url: t.Optional[str] = None,
        on_event: t.Optional[t.Callable[[dict], None]] = None,
        include_domains: t.Optional[list[str]] = None,
        enable_academic_tools: bool = True,
        search_depth: str = "advanced",
    ) -> None:
        self.model = model
        self.topn = topn
        self.debug = debug
        self.on_event = on_event
        self.include_domains = include_domains or []
        self.enable_academic_tools = enable_academic_tools
        self.search_depth = search_depth
        self.openai_key = openai_key or get_secret("OPENROUTER_API_KEY") or get_secret("OPENAI_API_KEY")
        self.tavily_key = tavily_key or get_secret("TAVILY_API_KEY")
        self.base_url = base_url or get_secret("OPENAI_BASE_URL")
        self.s2_key = get_secret("SEMANTIC_SCHOLAR_API_KEY")
        self.openalex_email = get_secret("OPENALEX_EMAIL")
        if not self.openai_key or not self.tavily_key:
            raise RuntimeError("OPENAI_API_KEY (or OPENROUTER_API_KEY) and TAVILY_API_KEY must be set.")

        self.client = OpenAI(api_key=self.openai_key, base_url=self.base_url)
        self.tavily = TavilyClient(api_key=self.tavily_key)
        self.http = httpx.Client(timeout=30.0)

        self.tools = self._build_tools()
        self.sys_prompt = self._build_system_prompt()

    def _build_tools(self) -> list[dict]:
        tools: list[dict] = [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": (
                        "Search the web via Tavily. Best for news, think tank reports, "
                        "policy analyses, blog posts, and recent commentary. "
                        "Returns title + URL + snippet."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query string"},
                        },
                        "required": ["query"],
                    },
                },
            }
        ]
        if self.enable_academic_tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": "search_semantic_scholar",
                    "description": (
                        "Search peer-reviewed academic papers via Semantic Scholar. "
                        "Returns full abstracts (much richer than web snippets), "
                        "authors, year, venue. Strong for English-language scholarship. "
                        "Use for citing peer-reviewed research."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Academic search query"},
                        },
                        "required": ["query"],
                    },
                },
            })
            tools.append({
                "type": "function",
                "function": {
                    "name": "search_openalex",
                    "description": (
                        "Search 250M+ scholarly works via OpenAlex (free, comprehensive, "
                        "multilingual — includes Russian and other non-English papers). "
                        "Returns abstracts, DOI, year, authors, venue. "
                        "Complementary to Semantic Scholar — try both for important topics."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Academic search query"},
                        },
                        "required": ["query"],
                    },
                },
            })
        return tools

    def _build_system_prompt(self) -> str:
        tool_list = "`search_web`"
        if self.enable_academic_tools:
            tool_list = (
                "`search_web` (news, think tanks), "
                "`search_semantic_scholar` (peer-reviewed, English), "
                "`search_openalex` (peer-reviewed, multilingual incl. Russian)"
            )

        tool_strategy = (
            "Tool selection strategy:\n"
            "- For peer-reviewed academic literature → use search_semantic_scholar AND search_openalex.\n"
            "- For Russian-language academic work → search_openalex (it indexes RU papers well).\n"
            "- For think tank reports, policy briefs, news, recent commentary → use search_web.\n"
            "- Mix tools across the 2-8 calls. E.g. for an IR question, do 2-3 academic searches "
            "+ 2-3 web searches covering different angles.\n\n"
            if self.enable_academic_tools
            else ""
        )

        domain_note = ""
        if self.include_domains:
            domain_note = (
                f"\n\nNote: web searches are restricted to a curated whitelist of "
                f"{len(self.include_domains)} domains (academic publishers, think tanks, IR sources). "
                "If a search returns few results, try rephrasing rather than abandoning the angle."
            )

        return (
            "You are a research assistant whose job is to find relevant articles, "
            "papers, and reports for the user's topic. You have access to: "
            f"{tool_list}.\n\n"
            f"{tool_strategy}"
            "STEP 1 — Generate searches: emit between 2 and 8 tool calls "
            "in a SINGLE assistant message, covering different angles of the topic. "
            "Do not write any text, only tool calls.\n\n"
            "STEP 2 — After all results return, curate the most relevant items "
            "and respond with ONLY a JSON object in this exact shape (no markdown, no commentary):\n"
            "{\n"
            "  \"articles\": [\n"
            "    {\n"
            "      \"title\": \"...\",\n"
            "      \"url\": \"...\",\n"
            "      \"summary\": \"detailed multi-paragraph summary (5-8 sentences)\",\n"
            "      \"why_relevant\": \"2-3 sentences on why it matters for the user's query\",\n"
            "      \"source_type\": \"academic | think_tank | news | other\"\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- Include 8-15 of the BEST articles, ranked by relevance.\n"
            "- Mix academic and non-academic sources when both are available.\n"
            "- Summary must be SUBSTANTIVE: 10-15 sentences covering main claims, "
            "methods, key findings, concrete examples. Use the abstract when "
            "available (academic results give full abstracts).\n"
            "- why_relevant: 2-3 sentences on the connection to the user's question.\n"
            "- Deduplicate near-identical sources.\n"
            "- Use the EXACT URL returned — do not invent URLs.\n"
            "- Prefer recent and authoritative sources."
            f"{domain_note}"
        )

    def _emit(self, event: dict) -> None:
        if self.on_event:
            try:
                self.on_event(event)
            except Exception:
                pass

    def _search_web(self, query: str) -> str:
        _log(f"  Tavily search: '{query}'")
        self._emit({"type": "search_start", "query": query, "engine": "web"})
        t0 = time.time()
        kwargs: dict[str, t.Any] = {
            "query": query,
            "max_results": self.topn,
            "search_depth": self.search_depth,
        }
        if self.include_domains:
            kwargs["include_domains"] = self.include_domains
        resp = self.tavily.search(**kwargs)
        results = resp.get("results", [])[: self.topn]
        elapsed = time.time() - t0
        _log(f"  Tavily done ({len(results)} results, {elapsed:.1f}s): '{query}'")
        self._emit({
            "type": "search_done", "query": query, "engine": "web",
            "count": len(results), "elapsed": elapsed,
        })
        return "\n\n".join(
            f"- TITLE: {r.get('title','(untitled)')}\n"
            f"  URL: {r.get('url','')}\n"
            f"  CONTENT: {r.get('content','(no snippet)')}"
            for r in results
        ) or "No results found."

    def _search_semantic_scholar(self, query: str) -> str:
        _log(f"  Semantic Scholar: '{query}'")
        self._emit({"type": "search_start", "query": query, "engine": "semantic_scholar"})
        t0 = time.time()
        try:
            headers = {"x-api-key": self.s2_key} if self.s2_key else {}
            r = self.http.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={
                    "query": query,
                    "limit": self.topn,
                    "fields": "title,abstract,url,year,authors,venue,externalIds",
                },
                headers=headers,
            )
            r.raise_for_status()
            data = r.json()
            results = data.get("data", [])
        except Exception as e:
            elapsed = time.time() - t0
            _log(f"  Semantic Scholar error ({elapsed:.1f}s): {e}")
            self._emit({
                "type": "search_done", "query": query, "engine": "semantic_scholar",
                "count": 0, "elapsed": elapsed, "error": str(e),
            })
            return f"Semantic Scholar error: {e}"

        elapsed = time.time() - t0
        _log(f"  Semantic Scholar done ({len(results)} results, {elapsed:.1f}s): '{query}'")
        self._emit({
            "type": "search_done", "query": query, "engine": "semantic_scholar",
            "count": len(results), "elapsed": elapsed,
        })
        if not results:
            return "No results found."
        out = []
        for p in results:
            authors = ", ".join(a.get("name", "") for a in (p.get("authors") or [])[:5])
            year = p.get("year") or ""
            venue = p.get("venue") or ""
            url = p.get("url") or ""
            doi = (p.get("externalIds") or {}).get("DOI")
            if doi and not url:
                url = f"https://doi.org/{doi}"
            out.append(
                f"- TITLE: {p.get('title','(untitled)')}\n"
                f"  URL: {url}\n"
                f"  AUTHORS: {authors}\n"
                f"  YEAR: {year}  VENUE: {venue}\n"
                f"  ABSTRACT: {p.get('abstract') or '(no abstract)'}"
            )
        return "\n\n".join(out)

    def _search_openalex(self, query: str) -> str:
        _log(f"  OpenAlex: '{query}'")
        self._emit({"type": "search_start", "query": query, "engine": "openalex"})
        t0 = time.time()
        try:
            params: dict[str, t.Any] = {
                "search": query,
                "per-page": self.topn,
                "select": "id,doi,title,abstract_inverted_index,publication_year,authorships,primary_location,language",
            }
            if self.openalex_email:
                params["mailto"] = self.openalex_email
            r = self.http.get("https://api.openalex.org/works", params=params)
            r.raise_for_status()
            data = r.json()
            results = data.get("results", [])
        except Exception as e:
            elapsed = time.time() - t0
            _log(f"  OpenAlex error ({elapsed:.1f}s): {e}")
            self._emit({
                "type": "search_done", "query": query, "engine": "openalex",
                "count": 0, "elapsed": elapsed, "error": str(e),
            })
            return f"OpenAlex error: {e}"

        elapsed = time.time() - t0
        _log(f"  OpenAlex done ({len(results)} results, {elapsed:.1f}s): '{query}'")
        self._emit({
            "type": "search_done", "query": query, "engine": "openalex",
            "count": len(results), "elapsed": elapsed,
        })
        if not results:
            return "No results found."
        out = []
        for w in results:
            authors = ", ".join(
                (a.get("author") or {}).get("display_name", "")
                for a in (w.get("authorships") or [])[:5]
            )
            year = w.get("publication_year") or ""
            lang = w.get("language") or ""
            primary = w.get("primary_location") or {}
            source = (primary.get("source") or {}).get("display_name", "")
            url = primary.get("landing_page_url") or w.get("doi") or w.get("id") or ""
            abstract = _decode_inverted_abstract(w.get("abstract_inverted_index"))
            out.append(
                f"- TITLE: {w.get('title','(untitled)')}\n"
                f"  URL: {url}\n"
                f"  AUTHORS: {authors}\n"
                f"  YEAR: {year}  VENUE: {source}  LANG: {lang}\n"
                f"  ABSTRACT: {abstract or '(no abstract)'}"
            )
        return "\n\n".join(out)

    def _dispatch_tool(self, name: str, query: str) -> str:
        if name == "search_web":
            return self._search_web(query)
        if name == "search_semantic_scholar":
            return self._search_semantic_scholar(query)
        if name == "search_openalex":
            return self._search_openalex(query)
        return f"Unknown tool: {name}"

    def run(self, question: str) -> dict[str, t.Any]:
        messages = [
            {"role": "system", "content": self.sys_prompt},
            {"role": "user", "content": question},
        ]
        steps: list[dict[str, t.Any]] = []
        turn = 0

        while True:
            turn += 1
            _log(f"Turn {turn}: calling LLM ({self.model}) …")
            self._emit({"type": "turn_start", "turn": turn, "model": self.model})
            t0 = time.time()
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
            )
            msg = resp.choices[0].message
            elapsed = time.time() - t0
            n_calls = len(msg.tool_calls) if msg.tool_calls else 0
            _log(f"Turn {turn}: LLM responded in {elapsed:.1f}s (tool_calls={n_calls})")
            self._emit({"type": "turn_done", "turn": turn, "elapsed": elapsed, "tool_calls": n_calls})

            if msg.tool_calls:
                messages.append(msg)

                def fetch(call):
                    args = json.loads(call.function.arguments)
                    q = args["query"]
                    name = call.function.name
                    steps.append({"type": "tool_call", "tool": name, "query": q})
                    return call.id, name, q, self._dispatch_tool(name, q)

                with ThreadPoolExecutor() as pool:
                    results = list(pool.map(fetch, msg.tool_calls))

                for call_id, name, q, result in results:
                    steps.append({"type": "tool_result", "tool": name, "content": result})
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": result,
                        }
                    )
                continue

            answer = msg.content.strip()
            steps.append({"type": "assistant_answer", "content": answer})
            return {"question": question, "answer": answer, "steps": steps}


# -------------------------------------------------------------------------
# CLI wrapper
# -------------------------------------------------------------------------

def _cli():
    p = argparse.ArgumentParser(description="ResearchAgent CLI")
    p.add_argument("-q", "--query", required=True)
    p.add_argument("-m", "--model", default="openai/gpt-oss-120b:free")
    p.add_argument("-n", "--topn", type=int, default=10)
    p.add_argument("-o", "--outfile", type=Path)
    p.add_argument("-d", "--debug", action="store_true")
    p.add_argument(
        "--preset",
        choices=list(SOURCE_PRESETS.keys()),
        default="General web",
        help="Source domain preset",
    )
    p.add_argument("--no-academic", action="store_true", help="Disable Semantic Scholar + OpenAlex")
    p.add_argument("--depth", choices=["basic", "advanced"], default="advanced")
    cfg = p.parse_args()

    agent = ResearchAgent(
        model=cfg.model,
        topn=cfg.topn,
        debug=cfg.debug,
        include_domains=SOURCE_PRESETS[cfg.preset],
        enable_academic_tools=not cfg.no_academic,
        search_depth=cfg.depth,
    )
    result = agent.run(cfg.query)

    answer = result["answer"]
    articles = _extract_articles(answer)

    print("\n" + "=" * 80)
    print(f"Topic: {cfg.query}")
    print("=" * 80)
    if articles:
        for i, a in enumerate(articles, 1):
            print(f"\n[{i}] {a.get('title', '(no title)')}")
            print(f"    URL: {a.get('url', '')}")
            if a.get("source_type"):
                print(f"    Type: {a['source_type']}")
            if a.get("summary"):
                print(f"    Summary: {a['summary']}")
            if a.get("why_relevant"):
                print(f"    Why: {a['why_relevant']}")
        print(f"\n{'=' * 80}\nFound {len(articles)} relevant articles.")
    else:
        print("Could not parse article list. Raw output:")
        print(answer)
    print("=" * 80)

    if cfg.outfile:
        cfg.outfile.write_text(json.dumps(
            {**result, "articles": articles}, indent=2, ensure_ascii=False,
        ))
        print(f"Saved full trace → {cfg.outfile}")


def _extract_articles(text: str) -> list[dict]:
    """Extract the articles list from the model's JSON response, tolerant to markdown fences."""
    s = text.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.lstrip().startswith("json"):
            s = s.lstrip()[4:]
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1:
        return []
    try:
        data = json.loads(s[start:end + 1])
        return data.get("articles", []) if isinstance(data, dict) else []
    except json.JSONDecodeError:
        return []


if __name__ == "__main__":
    _cli()
