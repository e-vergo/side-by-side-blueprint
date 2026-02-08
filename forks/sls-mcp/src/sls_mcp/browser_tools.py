"""General browser tool implementations.

This module provides MCP tools for general-purpose browser automation:
- browser_navigate: Navigate to a URL (creates persistent active page)
- browser_click: Click an element on the active page
- browser_screenshot: Capture screenshot of the active page
- browser_evaluate: Run JavaScript on the active page
- browser_get_elements: Query DOM elements on the active page

Unlike Zulip tools (which create a new page per call), these tools maintain
a persistent active page across calls for stateful browsing sessions.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, List, Optional

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .sls_models import (
    BrowserClickResult,
    BrowserElementsResult,
    BrowserEvaluateResult,
    BrowserNavigateResult,
    BrowserScreenshotResult,
    ElementInfo,
)
from .sls_utils import (
    SBS_ROOT,
    compute_hash,
    sanitize_filename,
)


# Screenshot storage directory
QA_SCREENSHOT_DIR = SBS_ROOT / "dev" / "storage" / "qa"


class BrowserToolError(Exception):
    """Error raised by general browser tools."""
    pass


def register_browser_tools(mcp: FastMCP) -> None:
    """Register general browser tools with the MCP server."""

    @mcp.tool(
        "browser_navigate",
        annotations=ToolAnnotations(
            title="Browser Navigate",
            readOnlyHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def browser_navigate(
        ctx: Context,
        url: Annotated[str, Field(description="URL to navigate to")],
    ) -> BrowserNavigateResult:
        """Navigate the browser to a URL, creating a persistent active page.

        If no active page exists, creates one. Subsequent calls reuse the same
        page. Use browser_click, browser_screenshot, browser_evaluate, and
        browser_get_elements to interact with the page after navigating.

        Examples:
        - browser_navigate(url="http://localhost:8000")
        - browser_navigate(url="https://example.com")
        """
        app_ctx = ctx.request_context.lifespan_context

        if not app_ctx.browser_context:
            raise BrowserToolError(
                "Browser not available. Set ZULIP_ENABLED=1 and install playwright."
            )

        # Create active page if it doesn't exist
        if app_ctx.active_page is None:
            app_ctx.active_page = await app_ctx.browser_context.new_page()

        page = app_ctx.active_page

        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        status = response.status if response else 0
        title = await page.title()
        final_url = page.url

        return BrowserNavigateResult(
            url=final_url,
            title=title,
            status=status,
        )

    @mcp.tool(
        "browser_click",
        annotations=ToolAnnotations(
            title="Browser Click",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def browser_click(
        ctx: Context,
        selector: Annotated[str, Field(description="CSS selector of element to click")],
    ) -> BrowserClickResult:
        """Click an element on the active browser page.

        Requires a prior browser_navigate call to create the active page.

        Examples:
        - browser_click(selector="button.submit")
        - browser_click(selector="#theme-toggle")
        - browser_click(selector=".nav-link:first-child")
        """
        app_ctx = ctx.request_context.lifespan_context

        if not app_ctx.browser_context:
            raise BrowserToolError(
                "Browser not available. Set ZULIP_ENABLED=1 and install playwright."
            )

        if app_ctx.active_page is None:
            raise BrowserToolError(
                "No active page. Call browser_navigate first."
            )

        page = app_ctx.active_page

        # Check if element exists
        element = await page.query_selector(selector)
        if element is None:
            return BrowserClickResult(
                selector=selector,
                clicked=False,
                element_text=None,
            )

        # Get text content before clicking
        element_text = await element.text_content()
        if element_text:
            element_text = element_text.strip()[:200]

        # Click the element
        await element.click()

        # Brief wait for any resulting navigation or DOM changes
        await page.wait_for_timeout(500)

        return BrowserClickResult(
            selector=selector,
            clicked=True,
            element_text=element_text,
        )

    @mcp.tool(
        "browser_screenshot",
        annotations=ToolAnnotations(
            title="Browser Screenshot",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def browser_screenshot(
        ctx: Context,
        name: Annotated[
            Optional[str],
            Field(description="Screenshot filename (without extension). Auto-generated if omitted.")
        ] = None,
        full_page: Annotated[
            bool,
            Field(description="Capture full scrollable page")
        ] = False,
        selector: Annotated[
            Optional[str],
            Field(description="CSS selector to screenshot a specific element")
        ] = None,
    ) -> BrowserScreenshotResult:
        """Capture a screenshot of the active browser page.

        Requires a prior browser_navigate call. Screenshots are saved to
        dev/storage/qa/. Optionally capture just a specific element by selector.

        Examples:
        - browser_screenshot()
        - browser_screenshot(name="dashboard_after_fix", full_page=True)
        - browser_screenshot(selector=".graph-container", name="graph_detail")
        """
        app_ctx = ctx.request_context.lifespan_context

        if not app_ctx.browser_context:
            raise BrowserToolError(
                "Browser not available. Set ZULIP_ENABLED=1 and install playwright."
            )

        if app_ctx.active_page is None:
            raise BrowserToolError(
                "No active page. Call browser_navigate first."
            )

        page = app_ctx.active_page
        timestamp = datetime.now()

        # Generate filename
        if name:
            safe_name = sanitize_filename(name)
        else:
            safe_name = sanitize_filename(
                f"screenshot_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            )

        # Ensure directory exists
        QA_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        screenshot_path = QA_SCREENSHOT_DIR / f"{safe_name}.png"

        # Capture screenshot
        if selector:
            element = await page.query_selector(selector)
            if element is None:
                raise BrowserToolError(
                    f"Element not found for selector: {selector}"
                )
            await element.screenshot(path=str(screenshot_path))
        else:
            await page.screenshot(path=str(screenshot_path), full_page=full_page)

        # Compute hash
        file_hash = compute_hash(screenshot_path)

        return BrowserScreenshotResult(
            image_path=str(screenshot_path),
            url=page.url,
            captured_at=timestamp.isoformat(),
            hash=file_hash,
        )

    @mcp.tool(
        "browser_evaluate",
        annotations=ToolAnnotations(
            title="Browser Evaluate JS",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def browser_evaluate(
        ctx: Context,
        script: Annotated[str, Field(description="JavaScript code to evaluate in the page context")],
    ) -> BrowserEvaluateResult:
        """Evaluate JavaScript on the active browser page.

        Requires a prior browser_navigate call. The script runs in the page
        context and can access DOM, window, etc. Returns the result as a string.

        Examples:
        - browser_evaluate(script="document.title")
        - browser_evaluate(script="document.querySelectorAll('.node').length")
        - browser_evaluate(script="window.scrollTo(0, document.body.scrollHeight)")
        """
        app_ctx = ctx.request_context.lifespan_context

        if not app_ctx.browser_context:
            raise BrowserToolError(
                "Browser not available. Set ZULIP_ENABLED=1 and install playwright."
            )

        if app_ctx.active_page is None:
            raise BrowserToolError(
                "No active page. Call browser_navigate first."
            )

        page = app_ctx.active_page

        raw_result = await page.evaluate(script)

        # Convert result to string representation
        if raw_result is None:
            result_str = None
            result_type = "null"
        elif isinstance(raw_result, bool):
            result_str = str(raw_result).lower()
            result_type = "boolean"
        elif isinstance(raw_result, (int, float)):
            result_str = str(raw_result)
            result_type = "number"
        elif isinstance(raw_result, str):
            result_str = raw_result
            result_type = "string"
        elif isinstance(raw_result, (dict, list)):
            result_str = json.dumps(raw_result, default=str)
            result_type = "object" if isinstance(raw_result, dict) else "array"
        else:
            result_str = str(raw_result)
            result_type = type(raw_result).__name__

        return BrowserEvaluateResult(
            result=result_str,
            type=result_type,
        )

    @mcp.tool(
        "browser_get_elements",
        annotations=ToolAnnotations(
            title="Browser Get Elements",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def browser_get_elements(
        ctx: Context,
        selector: Annotated[str, Field(description="CSS selector to query")],
        limit: Annotated[
            int,
            Field(description="Maximum elements to return", ge=1, le=100)
        ] = 10,
    ) -> BrowserElementsResult:
        """Query DOM elements on the active browser page.

        Returns text content and key attributes for matching elements.
        Requires a prior browser_navigate call.

        Examples:
        - browser_get_elements(selector=".status-dot")
        - browser_get_elements(selector="a.nav-link", limit=20)
        - browser_get_elements(selector="h1, h2, h3")
        """
        app_ctx = ctx.request_context.lifespan_context

        if not app_ctx.browser_context:
            raise BrowserToolError(
                "Browser not available. Set ZULIP_ENABLED=1 and install playwright."
            )

        if app_ctx.active_page is None:
            raise BrowserToolError(
                "No active page. Call browser_navigate first."
            )

        page = app_ctx.active_page

        # Query elements and extract info via JS for efficiency
        raw_elements = await page.evaluate("""
            (args) => {
                const {selector, limit} = args;
                const all = document.querySelectorAll(selector);
                const total = all.length;
                const elements = [];
                for (let i = 0; i < Math.min(all.length, limit); i++) {
                    const el = all[i];
                    const attrs = {};
                    for (const attr of ['id', 'class', 'href', 'src', 'type', 'name', 'value', 'role', 'aria-label', 'data-status', 'data-id']) {
                        const val = el.getAttribute(attr);
                        if (val) attrs[attr] = val;
                    }
                    elements.push({
                        tag: el.tagName.toLowerCase(),
                        text: (el.textContent || '').trim().substring(0, 200),
                        attributes: attrs,
                    });
                }
                return {elements, total};
            }
        """, {"selector": selector, "limit": limit})

        elements = [
            ElementInfo(
                tag=e["tag"],
                text=e["text"],
                attributes=e["attributes"],
            )
            for e in raw_elements["elements"]
        ]

        return BrowserElementsResult(
            selector=selector,
            elements=elements,
            count=raw_elements["total"],
        )
