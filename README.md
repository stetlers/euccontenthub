# EUC Content Hub MCP Server

An [MCP](https://modelcontextprotocol.io) server that exposes the **EUC Content
Hub** corpus — AWS Blog and Builder.AWS posts about Amazon **WorkSpaces** and
other End User Computing (EUC) services — plus the community's **content
proposals**, so an AI agent (Kiro, Claude, Amazon Q, …) can discover what
content already exists and reason about what's missing.

The premise: EUC specialists increasingly work *through* a chat agent rather than
browsing the website. This server lets their agent see the whole curated corpus,
check what's already been proposed, and spot what's *missing* — so they can
develop a genuinely new content idea grounded in what already exists.

It is **read-only by design.** This server's job is discovery, not submission:
once a specialist has an idea, they file it however they already work — through
Kiro, Amazon Q, Claude, or the Content Hub website. We deliberately don't add a
submit step here, to avoid getting in the way of that workflow.

It sources everything from the Content Hub's public HTTP API. No AWS credentials
are required except for `list_content_gaps` (see Authentication).

> **Companion server:** [`workspaces-whats-new-mcp`](../workspaces-whats-new-mcp)
> owns the AWS *What's New* announcement feed. This server deliberately does not
> duplicate it — run both if you want announcements *and* the blog/builder corpus.

## Tools (v1 — read-only, public)

| Tool | Description |
|------|-------------|
| `search_content` | Keyword-search the existing corpus. Args: `query`, `source` (optional), `label` (optional), `limit` (default 10). Use it to confirm whether a topic is already covered before proposing new content. |
| `list_content` | Browse posts, most recent first. Args: `source`, `label`, `limit` (default 25). |
| `get_content_facets` | The `source` and `label` values present in the corpus — valid filter values for the two tools above. |
| `list_proposals` | Existing community content proposals (article/feature ideas). Args: `status` (optional). Check before proposing to avoid duplicates. |
| `list_content_gaps` | **The demand signal** — searches EUC specialists ran that returned zero/few results. Args: `zero_only`, `low_only`, `min_count`, `limit` (default 50). **Requires a token** (see Authentication). |

`source` accepts `aws-blog` or `builder` (aliases for the stored values
`aws-blog` / `builder.aws.com`). `label` is a content-type such as
`Technical How-To`, `Announcement`, `Best Practices`, `Thought Leadership`, or
`Customer Story`.

### The core workflow

`list_content_gaps` is the point of the server: it surfaces what people looked
for in the Hub and *didn't find*. The intended loop —

**`list_content_gaps` → `search_content` (confirm genuinely uncovered) → develop a new content idea**

— lets an EUC specialist's agent turn unmet demand into a concrete, non-duplicate
content idea. Filing that idea is out of scope: the specialist submits it through
whatever tool they already use (Kiro, Amazon Q, Claude, or the Content Hub site).

### Note on search

`search_content` fetches the corpus once, caches it in-process, and ranks
locally across title/tags/summary/authors/body. It deliberately does **not** call
the Hub's server-side `/posts?q=` filter, which scans the whole table per request
*and* logs each query into the Hub's search analytics — the very signal used to
detect content gaps. Keeping agent traffic out of that signal is intentional.

## Authentication

`list_content_gaps` calls an authenticated endpoint (`GET /search-analytics/gaps`,
**401** without a token). The server resolves a Cognito JWT in this order:

1. **`CONTENT_HUB_TOKEN` env var** — paste in a Cognito JWT. Works immediately
   with no backend change; ideal for testing. Tokens expire (~1h).
2. **Cached login** — a token from a prior interactive login, auto-refreshed via
   the Cognito token endpoint when expired. Cached at
   `~/.euc-content-hub/token.json` (override with `CONTENT_HUB_TOKEN_CACHE`).
3. **Interactive loopback PKCE login** — opens the Cognito Hosted UI in your
   browser, captures the code on `http://localhost:<port>/callback`, and
   exchanges it for tokens.

If no token can be obtained, `list_content_gaps` returns a structured
`authentication_required` error (it does not crash or block).

> **The browser login (path 3) works out of the box.** `http://localhost:3000/callback`
> is already registered on the Cognito app client, so the loopback flow needs no
> backend change. (Cognito's Hosted UI doesn't support the OAuth device grant, which
> is why the loopback redirect is used.) If you change `CONTENT_HUB_LOOPBACK_PORT`,
> the new `http://localhost:<port>/callback` must also be registered on the app
> client, or the login will fail with a redirect-mismatch error.

## Scope: read-only by design

This server intentionally has **no write tools** — nothing here submits a
proposal, feature request, or innovation back to the Hub. Discovery and idea
development happen here; filing the idea happens in whatever tool the specialist
already uses. Keeping the server read-only avoids cutting across that workflow
and keeps the security surface to public reads plus one authenticated read
(`list_content_gaps`).

## Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `CONTENT_HUB_API` | the production API base | Override the Content Hub API base URL (e.g. to target staging). |
| `CONTENT_HUB_TOKEN` | _(none)_ | Cognito JWT for authenticated tools, with or without a `Bearer ` prefix. |
| `CONTENT_HUB_TOKEN_CACHE` | `~/.euc-content-hub/token.json` | Where cached login tokens are stored. |
| `CONTENT_HUB_NONINTERACTIVE` | _(unset)_ | Set to `1` to never open a browser; missing-token cases return an error instead. |
| `CONTENT_HUB_LOOPBACK_PORT` | `3000` | Port for the PKCE loopback redirect. `3000` is pre-registered on the app client; changing it requires registering the new callback URL too. |
| `CONTENT_HUB_COGNITO_DOMAIN` / `CONTENT_HUB_COGNITO_CLIENT_ID` / `CONTENT_HUB_COGNITO_SCOPES` | EUC Content Hub pool | Override Cognito settings (e.g. for staging). |

## Requirements

- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pipx`.

## Install & Run

The server speaks MCP over stdio; the clients below launch it for you. To start
it manually for testing:

```bash
uvx --from /path/to/euc-content-hub-mcp euc-content-hub-mcp
```

### Kiro

Add to `.kiro/settings/mcp.json` (workspace) or `~/.kiro/settings/mcp.json` (global):

```json
{
  "mcpServers": {
    "euc-content-hub": {
      "command": "uvx",
      "args": ["--from", "/path/to/euc-content-hub-mcp", "euc-content-hub-mcp"],
      "disabled": false,
      "autoApprove": ["search_content", "list_content", "get_content_facets", "list_proposals", "list_content_gaps"]
    }
  }
}
```

### Claude Desktop

Add to `claude_desktop_config.json`
(macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`,
Windows: `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "euc-content-hub": {
      "command": "uvx",
      "args": ["--from", "/path/to/euc-content-hub-mcp", "euc-content-hub-mcp"]
    }
  }
}
```

Restart Claude Desktop after editing. The tools appear under the 🔌 (plug) icon.

### Claude Code (CLI)

```bash
claude mcp add euc-content-hub -- uvx --from /path/to/euc-content-hub-mcp euc-content-hub-mcp
```

### Amazon Q Developer (Desktop / CLI)

Add to `~/.aws/amazonq/mcp.json` (global) or `.amazonq/mcp.json` (workspace):

```json
{
  "mcpServers": {
    "euc-content-hub": {
      "command": "uvx",
      "args": ["--from", "/path/to/euc-content-hub-mcp", "euc-content-hub-mcp"]
    }
  }
}
```

## Example prompts

- "What are EUC folks searching the content hub for and not finding?"
  *(`list_content_gaps`)*
- "Take the top content gaps, confirm they're not already covered, and draft
  article ideas for the real ones." *(`list_content_gaps` → `search_content`)*
- "Search the EUC content hub for AppStream GPU pricing — is it covered?"
- "List recent Builder.AWS posts tagged Technical How-To."
- "What content proposals are already pending? Don't suggest duplicates."

## Development

```bash
# install deps + run tests
pip install -e . pytest
PYTHONPATH=src python -m pytest tests/ -q
```

### Layout

```
src/euc_content_hub_mcp/
  hub.py      # Content Hub API client: /posts (cached), /proposals, /gaps
  auth.py     # Cognito token resolution: env var, cached login, loopback PKCE
  server.py   # FastMCP server exposing the five tools
tests/
  test_hub.py
  test_auth.py
```

## License

MIT-0
