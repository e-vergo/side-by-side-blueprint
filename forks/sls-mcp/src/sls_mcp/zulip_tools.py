"""Zulip browsing tool implementations.

This module provides MCP tools for browsing Zulip chat history:
- zulip_search: Search messages across streams
- zulip_fetch_thread: Fetch complete thread content
- zulip_screenshot: Capture screenshot of a Zulip page
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Annotated, List, Optional
from urllib.parse import quote

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .sls_models import (
    ZulipMessage,
    ZulipScreenshotResult,
    ZulipSearchResult,
    ZulipThreadResult,
)
from .sls_utils import (
    ZULIP_ARCHIVE_DIR,
    compute_hash,
    sanitize_filename,
)

# Zulip base URL (configurable via env)
ZULIP_BASE_URL = os.environ.get("ZULIP_URL", "https://leanprover.zulipchat.com")


class ZulipToolError(Exception):
    """Error raised by Zulip tools."""
    pass


def _url_encode(s: str) -> str:
    """URL-encode a string for Zulip narrow URLs."""
    return quote(s, safe="")


def _build_search_url(query: str, stream: Optional[str], topic: Optional[str]) -> str:
    """Build a Zulip search URL with optional stream/topic filters."""
    parts = []
    if stream:
        parts.append(f"stream/{_url_encode(stream)}")
    if topic:
        parts.append(f"topic/{_url_encode(topic)}")
    parts.append(f"search/{_url_encode(query)}")
    return f"{ZULIP_BASE_URL}/#narrow/{'/'.join(parts)}"


def _build_thread_url(stream: str, topic: str) -> str:
    """Build a Zulip narrow URL for a specific thread."""
    return f"{ZULIP_BASE_URL}/#narrow/stream/{_url_encode(stream)}/topic/{_url_encode(topic)}"


async def _extract_messages(page, limit: int) -> List[ZulipMessage]:
    """Extract messages from the current Zulip page."""
    raw_messages = await page.evaluate("""
        (limit) => {
            const messages = [];
            const rows = document.querySelectorAll('.message_row');
            for (let i = 0; i < Math.min(rows.length, limit); i++) {
                const row = rows[i];
                const content = row.querySelector('.message_content');
                const sender = row.querySelector('.sender_name');
                const time = row.querySelector('.message_time');

                if (content) {
                    messages.push({
                        id: parseInt(row.getAttribute('data-message-id') || '0'),
                        sender: sender?.textContent?.trim() || 'Unknown',
                        content: content.textContent?.trim() || '',
                        timestamp: time?.getAttribute('datetime') || new Date().toISOString(),
                    });
                }
            }
            return messages;
        }
    """, limit)

    return [
        ZulipMessage(
            id=m["id"],
            sender=m["sender"],
            content=m["content"],
            timestamp=m["timestamp"],
            reactions=[],
        )
        for m in raw_messages
    ]


async def _extract_thread_messages(page, limit: int) -> List[ZulipMessage]:
    """Extract all messages from a thread, scrolling if needed."""
    messages = []
    seen_ids = set()

    # Initial extraction
    new_messages = await _extract_messages(page, limit)
    for msg in new_messages:
        if msg.id not in seen_ids:
            seen_ids.add(msg.id)
            messages.append(msg)

    # Scroll to load more if needed (simplified - just one scroll attempt)
    if len(messages) < limit:
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)

        more_messages = await _extract_messages(page, limit)
        for msg in more_messages:
            if msg.id not in seen_ids:
                seen_ids.add(msg.id)
                messages.append(msg)

    # Sort chronologically and limit
    messages.sort(key=lambda m: m.timestamp)
    return messages[:limit]


def _write_capture_metadata(
    directory: Path,
    stream: str,
    topic: str,
    url: str,
    timestamp: datetime
) -> None:
    """Write capture.json metadata file."""
    metadata = {
        "timestamp": timestamp.isoformat(),
        "type": "zulip",
        "base_url": ZULIP_BASE_URL,
        "viewport": {"width": 1920, "height": 1080},
        "captures": [
            {
                "name": f"thread_{stream}_{topic}",
                "path": f"{sanitize_filename(f'thread_{stream}_{topic}')}.png",
                "url": url,
                "status": "success",
                "stream": stream,
                "topic": topic,
            }
        ],
    }
    capture_path = directory / "capture.json"
    capture_path.write_text(json.dumps(metadata, indent=2))


def register_zulip_tools(mcp: FastMCP) -> None:
    """Register Zulip browsing tools with the MCP server."""

    @mcp.tool(
        "zulip_search",
        annotations=ToolAnnotations(
            title="Zulip Search",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def zulip_search(
        ctx: Context,
        query: Annotated[str, Field(description="Search query (supports Zulip search syntax)")],
        stream: Annotated[
            Optional[str],
            Field(description="Filter to specific stream (e.g., 'lean4')")
        ] = None,
        topic: Annotated[
            Optional[str],
            Field(description="Filter to specific topic within stream")
        ] = None,
        limit: Annotated[
            int,
            Field(description="Maximum messages to return", ge=1, le=100)
        ] = 20,
    ) -> ZulipSearchResult:
        """Search Zulip messages using browser automation.

        Searches the Zulip web interface for matching messages.

        Examples:
        - Simple search: zulip_search(query="simp lemma")
        - Stream-scoped: zulip_search(query="tactic", stream="lean4")
        - Topic-scoped: zulip_search(query="apply", stream="lean4", topic="Metaprogramming")
        """
        app_ctx = ctx.request_context.lifespan_context

        if not app_ctx.browser_context:
            raise ZulipToolError("Zulip tools not enabled. Set ZULIP_ENABLED=1 and install playwright")

        page = await app_ctx.browser_context.new_page()
        try:
            search_url = _build_search_url(query, stream, topic)
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

            # Wait for messages to load
            try:
                await page.wait_for_selector(".message_content", timeout=10000)
            except Exception:
                # No messages found
                return ZulipSearchResult(
                    messages=[],
                    total_count=0,
                    query=query,
                    stream=stream,
                    topic=topic,
                    truncated=False,
                )

            messages = await _extract_messages(page, limit)

            return ZulipSearchResult(
                messages=messages,
                total_count=len(messages),
                query=query,
                stream=stream,
                topic=topic,
                truncated=len(messages) >= limit,
            )
        finally:
            await page.close()

    @mcp.tool(
        "zulip_fetch_thread",
        annotations=ToolAnnotations(
            title="Zulip Fetch Thread",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def zulip_fetch_thread(
        ctx: Context,
        stream: Annotated[str, Field(description="Stream name (e.g., 'lean4')")],
        topic: Annotated[str, Field(description="Topic name")],
        limit: Annotated[
            int,
            Field(description="Maximum messages to fetch", ge=1, le=200)
        ] = 50,
    ) -> ZulipThreadResult:
        """Fetch complete thread content from Zulip.

        Navigates to the specified stream/topic and extracts all visible messages.
        Messages are returned in chronological order.

        Examples:
        - zulip_fetch_thread(stream="lean4", topic="Metaprogramming")
        - zulip_fetch_thread(stream="mathlib4", topic="PR reviews", limit=100)
        """
        app_ctx = ctx.request_context.lifespan_context

        if not app_ctx.browser_context:
            raise ZulipToolError("Zulip tools not enabled. Set ZULIP_ENABLED=1 and install playwright")

        page = await app_ctx.browser_context.new_page()
        try:
            thread_url = _build_thread_url(stream, topic)
            await page.goto(thread_url, wait_until="domcontentloaded", timeout=30000)

            # Wait for messages to load
            try:
                await page.wait_for_selector(".message_content", timeout=10000)
            except Exception:
                return ZulipThreadResult(
                    stream=stream,
                    topic=topic,
                    messages=[],
                    message_count=0,
                    participants=[],
                    first_message_date=None,
                    last_message_date=None,
                )

            messages = await _extract_thread_messages(page, limit)
            participants = list(set(m.sender for m in messages))
            first_date = messages[0].timestamp if messages else None
            last_date = messages[-1].timestamp if messages else None

            return ZulipThreadResult(
                stream=stream,
                topic=topic,
                messages=messages,
                message_count=len(messages),
                participants=participants,
                first_message_date=first_date,
                last_message_date=last_date,
            )
        finally:
            await page.close()

    @mcp.tool(
        "zulip_screenshot",
        annotations=ToolAnnotations(
            title="Zulip Screenshot",
            readOnlyHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def zulip_screenshot(
        ctx: Context,
        stream: Annotated[str, Field(description="Stream name")],
        topic: Annotated[str, Field(description="Topic name")],
        archive: Annotated[
            bool,
            Field(description="Save to archive in addition to latest")
        ] = False,
        full_page: Annotated[
            bool,
            Field(description="Capture full scrollable page")
        ] = False,
    ) -> ZulipScreenshotResult:
        """Capture screenshot of a Zulip thread.

        Navigates to the specified stream/topic and captures a screenshot.
        Screenshots are saved to dev/storage/zulip/latest/ by default.

        Examples:
        - zulip_screenshot(stream="lean4", topic="Metaprogramming")
        - zulip_screenshot(stream="mathlib4", topic="PR reviews", archive=True)
        """
        app_ctx = ctx.request_context.lifespan_context

        if not app_ctx.browser_context:
            raise ZulipToolError("Zulip tools not enabled. Set ZULIP_ENABLED=1 and install playwright")

        page = await app_ctx.browser_context.new_page()
        try:
            thread_url = _build_thread_url(stream, topic)
            await page.goto(thread_url, wait_until="domcontentloaded", timeout=30000)

            # Wait for content to load
            try:
                await page.wait_for_selector(".message_content", timeout=10000)
            except Exception:
                pass  # Proceed anyway, might still capture something useful

            # Wait for animations to settle
            await page.wait_for_timeout(500)

            # Setup paths
            timestamp = datetime.now()
            safe_name = sanitize_filename(f"thread_{stream}_{topic}")

            latest_dir = ZULIP_ARCHIVE_DIR / "latest"
            latest_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = latest_dir / f"{safe_name}.png"

            # Capture screenshot
            await page.screenshot(path=str(screenshot_path), full_page=full_page)

            # Optionally archive
            archived = False
            if archive:
                archive_dir = ZULIP_ARCHIVE_DIR / "archive" / timestamp.strftime("%Y-%m-%d_%H-%M-%S")
                archive_dir.mkdir(parents=True, exist_ok=True)
                archive_path = archive_dir / f"{safe_name}.png"
                shutil.copy2(screenshot_path, archive_path)
                _write_capture_metadata(archive_dir, stream, topic, thread_url, timestamp)
                archived = True

            # Write latest metadata
            _write_capture_metadata(latest_dir, stream, topic, thread_url, timestamp)

            # Compute hash
            file_hash = compute_hash(screenshot_path)

            return ZulipScreenshotResult(
                image_path=str(screenshot_path),
                url=thread_url,
                captured_at=timestamp.isoformat(),
                hash=file_hash,
                stream=stream,
                topic=topic,
                archived=archived,
            )
        finally:
            await page.close()
