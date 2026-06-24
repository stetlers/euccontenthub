"""
EUC Content Hub MCP server.

Exposes the EUC Content Hub corpus — AWS Blog and Builder.AWS posts about Amazon
WorkSpaces / End User Computing (EUC) services — plus community content
proposals, so an AI agent (Kiro, Claude, Amazon Q, etc.) can discover what
content already exists and reason about what's missing.

The discovery tools (search/list/facets/proposals) hit public endpoints and need
no credentials. ``list_content_gaps`` hits an authenticated endpoint and resolves
a Cognito token via ``auth.get_token`` (env var, cached login, or interactive
browser login). The server is read-only by design: it supports discovering
existing content and unmet demand so a specialist can develop a new idea, but it
does not submit anything back to the Hub — that stays in the user's own tools.

Data source can be overridden with the ``CONTENT_HUB_API`` environment variable.

Tools:
    search_content       - keyword-search the existing corpus
    list_content         - browse posts by source and/or content-type label
    get_content_facets   - the source and label values available for filtering
    list_proposals       - existing community content proposals
    list_content_gaps    - searches that returned zero/few results (demand signal)
"""

from mcp.server.fastmcp import FastMCP

from . import auth, hub

mcp = FastMCP('euc-content-hub')


@mcp.tool()
def search_content(query: str, source: str = '', label: str = '', limit: int = 10) -> dict:
    """Search existing EUC Content Hub posts by keyword.

    Ranks the crawled corpus (AWS Blog + Builder.AWS posts on Amazon WorkSpaces /
    EUC topics) against the query across title, tags, summary, authors, and body.
    Use this to check whether content on a topic ALREADY EXISTS before proposing
    something new — if a search returns little or nothing, that topic is a
    candidate for a new article.

    Args:
        query: Keywords to search for (e.g. "AppStream GPU pricing").
        source: Optional source filter. Accepts "aws-blog" or "builder"
            (aliases for the raw values "aws-blog" / "builder.aws.com").
        label: Optional content-type filter (e.g. "Technical How-To",
            "Announcement"). Case-insensitive substring match.
        limit: Maximum number of posts to return (default 10). Pass 0 for all
            matches.

    Returns:
        A dict with the match count and a list of posts, each having post_id,
        title, authors, url, source, label, date_published, summary, and
        description.
    """
    posts = hub.search_posts(query, source=source, label=label, limit=limit)
    return {
        'count': len(posts),
        'query': query,
        'source': 'EUC Content Hub',
        'posts': posts,
    }


@mcp.tool()
def list_content(source: str = '', label: str = '', limit: int = 25) -> dict:
    """Browse EUC Content Hub posts, most recent first, optionally filtered.

    Use this to survey what's been published recently or to enumerate everything
    of a given content type / from a given source. For topic lookups, prefer
    ``search_content``.

    Args:
        source: Optional source filter. Accepts "aws-blog" or "builder".
        label: Optional content-type filter (e.g. "Technical How-To").
            Case-insensitive substring match.
        limit: Maximum number of posts to return (default 25). Pass 0 for all.

    Returns:
        A dict with the count and a list of posts (same fields as
        ``search_content``).
    """
    posts = hub.list_posts(source=source, label=label, limit=limit)
    return {
        'count': len(posts),
        'source': 'EUC Content Hub',
        'posts': posts,
    }


@mcp.tool()
def get_content_facets() -> dict:
    """Return the source and content-type label values present in the corpus.

    Useful for discovering valid values for the ``source`` and ``label``
    arguments of ``search_content`` and ``list_content``.
    """
    return hub.known_sources_and_labels()


@mcp.tool()
def list_proposals(status: str = '') -> dict:
    """List existing community content proposals (article and feature ideas).

    Check this before proposing new content so you don't duplicate an idea that's
    already been submitted. Each proposal has a title, type, status, vote count,
    and description.

    Args:
        status: Optional status filter (e.g. "pending", "approved", "rejected").

    Returns:
        A dict with the count and a list of proposals, each having proposal_id,
        title, proposal_type, status, category, votes, display_name, created_at,
        and description.
    """
    proposals = hub.fetch_proposals(status=status)
    return {
        'count': len(proposals),
        'source': 'EUC Content Hub',
        'proposals': proposals,
    }


@mcp.tool()
def list_content_gaps(zero_only: bool = False, low_only: bool = False,
                      min_count: int = 1, limit: int = 50) -> dict:
    """List content gaps: searches EUC specialists ran that returned zero or few results.

    This is the demand signal for NEW content — what people looked for in the
    Content Hub and didn't find. Use it as the starting point for proposing new
    articles: pick a high-count gap, confirm it's genuinely uncovered with
    ``search_content``, then develop an article idea for it. (Filing the idea is
    out of scope — the user submits it through their own tooling.)

    Requires authentication. The server resolves a Cognito token from the
    ``CONTENT_HUB_TOKEN`` env var, a cached login, or an interactive browser
    login (see the README). If no token can be obtained, returns an ``error``
    with guidance instead of raising.

    Args:
        zero_only: Only queries that returned zero results (the strongest gaps).
        low_only: Only low-coverage queries (includes zero). Ignored if
            ``zero_only`` is set.
        min_count: Minimum times a query was seen, to filter out one-offs.
        limit: Maximum gaps to return (default 50).

    Returns:
        A dict with the count and a list of gaps, each having normalized_query,
        last_query_raw, count, unique_user_count, last_result_count,
        flag_zero_results, flag_low_coverage, first_seen_at, and last_seen_at.
    """
    try:
        token = auth.get_token()
    except auth.AuthError as e:
        return {
            'error': 'authentication_required',
            'message': str(e),
            'hint': 'Set CONTENT_HUB_TOKEN to a Cognito JWT, or complete the '
                    'interactive login. See the server README.',
        }

    try:
        gaps = hub.fetch_gaps(
            token, zero_only=zero_only, low_only=low_only,
            min_count=min_count, limit=limit,
        )
    except Exception as e:  # noqa: BLE001 - surface as data, not a crash
        return {'error': 'request_failed', 'message': str(e)}

    return {
        'count': len(gaps),
        'source': 'EUC Content Hub',
        'gaps': gaps,
    }


def main():
    """Console-script entry point — runs the server over stdio."""
    mcp.run()


if __name__ == '__main__':
    main()
