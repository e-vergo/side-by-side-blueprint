#!/usr/bin/env python3
"""Scrape all Zulip posts by Eric Vergo from leanprover.zulipchat.com.

Usage:
    # First time: install dependencies
    pip install playwright
    playwright install chromium

    # Mode 1: Authenticated scrape via participated tab (RECOMMENDED)
    # Opens browser, waits for you to log in, then scrapes all participated threads
    python scrape_vergo.py --participated

    # Mode 2: Public search (limited, doesn't require login)
    python scrape_vergo.py --sender "Eric Vergo"

    # Verbose mode to see progress
    python scrape_vergo.py --participated -v

Output:
    - messages.json: All messages with metadata
    - messages.md: Human-readable markdown format
    - by_stream/: Messages organized by stream
"""

import argparse
import asyncio
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote

# Zulip base URL
ZULIP_BASE_URL = "https://leanprover.zulipchat.com"

# Output directory (same as script location)
OUTPUT_DIR = Path(__file__).parent


@dataclass
class ZulipMessage:
    """A single Zulip message."""
    id: int
    sender: str
    content: str
    timestamp: str
    stream: Optional[str] = None
    topic: Optional[str] = None
    url: Optional[str] = None


@dataclass
class ThreadInfo:
    """Information about a Zulip thread from participated tab."""
    stream: str
    topic: str
    url: str


async def wait_for_login(page, verbose: bool = False) -> bool:
    """Wait for user to log in manually.

    Returns True if login detected, False if timeout.
    """
    if verbose:
        print("\n" + "="*60)
        print("MANUAL LOGIN REQUIRED")
        print("="*60)
        print("1. A browser window has opened to Zulip")
        print("2. Please log in with your credentials")
        print("3. Once logged in, the script will continue automatically")
        print("="*60 + "\n")

    # Wait for login by checking for the compose box or user avatar
    # These elements only appear after successful login
    max_wait = 300  # 5 minutes max
    check_interval = 2  # Check every 2 seconds

    for _ in range(max_wait // check_interval):
        # Check for elements that indicate logged-in state
        logged_in = await page.evaluate("""
            () => {
                // Check for compose box
                const compose = document.querySelector('#compose-textarea');
                // Check for user avatar/settings
                const avatar = document.querySelector('.settings-dropdown');
                // Check for left sidebar streams
                const streams = document.querySelector('#streams_list');
                return !!(compose || avatar || streams);
            }
        """)

        if logged_in:
            if verbose:
                print("Login detected! Continuing with scrape...")
            return True

        await page.wait_for_timeout(check_interval * 1000)

    print("Login timeout - please try again")
    return False


async def get_participated_threads(page, verbose: bool = False) -> list[ThreadInfo]:
    """Extract all threads from the participated tab."""
    threads: list[ThreadInfo] = []

    # Navigate to participated view
    participated_url = f"{ZULIP_BASE_URL}/#narrow/is/participated"
    if verbose:
        print(f"Navigating to participated view: {participated_url}")

    await page.goto(participated_url, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(3000)  # Wait for threads to load

    # Click on "Recent conversations" tab if it exists
    try:
        await page.click('text="Recent conversations"', timeout=5000)
        await page.wait_for_timeout(2000)
    except Exception:
        pass  # Tab might already be selected or not exist

    # Scroll to load more threads
    seen_threads: set[str] = set()
    no_progress_count = 0
    max_no_progress = 3

    while no_progress_count < max_no_progress:
        # Extract thread info from the page
        raw_threads = await page.evaluate("""
            () => {
                const threads = [];
                // Try multiple selectors for different Zulip UI versions
                const items = document.querySelectorAll(
                    '.topic-list-item, .recent_topic_row, .conversation-row'
                );

                for (const item of items) {
                    const streamEl = item.querySelector('.stream_label, .stream-name');
                    const topicEl = item.querySelector('.topic_name, .topic-name');
                    const linkEl = item.querySelector('a[href*="narrow"]');

                    if (streamEl && topicEl) {
                        threads.push({
                            stream: streamEl.textContent?.trim() || '',
                            topic: topicEl.textContent?.trim() || '',
                            url: linkEl?.href || '',
                        });
                    }
                }
                return threads;
            }
        """)

        initial_count = len(seen_threads)
        for t in raw_threads:
            key = f"{t['stream']}|{t['topic']}"
            if key not in seen_threads:
                seen_threads.add(key)
                threads.append(ThreadInfo(
                    stream=t['stream'],
                    topic=t['topic'],
                    url=t['url'] or f"{ZULIP_BASE_URL}/#narrow/stream/{quote(t['stream'])}/topic/{quote(t['topic'])}",
                ))

        if len(seen_threads) == initial_count:
            no_progress_count += 1
        else:
            no_progress_count = 0
            if verbose:
                print(f"  Found {len(threads)} threads so far...")

        # Scroll down to load more
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1500)

    if verbose:
        print(f"Found {len(threads)} participated threads total")

    return threads


async def scrape_thread_messages(
    page,
    stream: str,
    topic: str,
    sender_name: str,
    verbose: bool = False,
) -> list[ZulipMessage]:
    """Scrape all messages from a specific thread that match the sender."""
    messages: list[ZulipMessage] = []
    seen_ids: set[int] = set()

    # Build thread URL
    thread_url = f"{ZULIP_BASE_URL}/#narrow/stream/{quote(stream)}/topic/{quote(topic)}"

    if verbose:
        print(f"  Scraping: {stream} > {topic}")

    await page.goto(thread_url, wait_until="domcontentloaded", timeout=60000)

    # Wait for messages to load
    try:
        await page.wait_for_selector(".message_row", timeout=10000)
    except Exception:
        return messages  # No messages in thread

    await page.wait_for_timeout(2000)

    # Scroll to load all messages in thread
    no_progress_count = 0
    max_no_progress = 3

    while no_progress_count < max_no_progress:
        # Extract messages
        raw_messages = await page.evaluate("""
            () => {
                const messages = [];
                const rows = document.querySelectorAll('.message_row');
                for (const row of rows) {
                    const content = row.querySelector('.message_content');
                    const sender = row.querySelector('.sender_name');
                    const time = row.querySelector('.message_time');
                    const msgId = parseInt(row.getAttribute('data-message-id') || '0');

                    if (content && msgId) {
                        messages.push({
                            id: msgId,
                            sender: sender?.textContent?.trim() || 'Unknown',
                            content: content.textContent?.trim() || '',
                            timestamp: time?.getAttribute('datetime') || '',
                        });
                    }
                }
                return messages;
            }
        """)

        initial_count = len(seen_ids)
        for msg in raw_messages:
            if msg["id"] not in seen_ids:
                seen_ids.add(msg["id"])
                # Only include messages from the target sender
                if msg["sender"].lower() == sender_name.lower():
                    messages.append(ZulipMessage(
                        id=msg["id"],
                        sender=msg["sender"],
                        content=msg["content"],
                        timestamp=msg["timestamp"] or datetime.now().isoformat(),
                        stream=stream,
                        topic=topic,
                        url=f"{ZULIP_BASE_URL}/#narrow/id/{msg['id']}",
                    ))

        if len(seen_ids) == initial_count:
            no_progress_count += 1
        else:
            no_progress_count = 0

        # Scroll up to load older messages
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)

    return messages


async def scrape_participated(
    sender_name: str,
    verbose: bool = False,
) -> list[ZulipMessage]:
    """Scrape all messages from participated threads after manual login.

    Args:
        sender_name: Display name of the sender to filter messages
        verbose: Print progress information

    Returns:
        List of ZulipMessage objects
    """
    from playwright.async_api import async_playwright

    all_messages: list[ZulipMessage] = []

    async with async_playwright() as p:
        # Launch visible browser for login
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
        )
        page = await context.new_page()

        # Navigate to Zulip
        await page.goto(ZULIP_BASE_URL, wait_until="domcontentloaded", timeout=60000)

        # Wait for manual login
        if not await wait_for_login(page, verbose):
            await browser.close()
            return all_messages

        # Get all participated threads
        threads = await get_participated_threads(page, verbose)

        if not threads:
            print("No participated threads found!")
            await browser.close()
            return all_messages

        # Scrape each thread
        print(f"\nScraping {len(threads)} threads for messages from {sender_name}...")
        for i, thread in enumerate(threads):
            if verbose:
                print(f"[{i+1}/{len(threads)}] ", end="")

            thread_messages = await scrape_thread_messages(
                page, thread.stream, thread.topic, sender_name, verbose
            )
            all_messages.extend(thread_messages)

            if verbose and thread_messages:
                print(f"    -> Found {len(thread_messages)} messages")

        await browser.close()

    # Sort by message ID (roughly chronological)
    all_messages.sort(key=lambda m: m.id)

    if verbose:
        print(f"\nTotal messages found: {len(all_messages)}")

    return all_messages


async def scrape_sender_messages(
    sender_name: str,
    max_messages: int = 1000,
    headless: bool = True,
    verbose: bool = False,
    filter_sender: bool = True,
) -> list[ZulipMessage]:
    """Scrape messages using public search (limited, doesn't require login).

    Args:
        sender_name: Display name of the sender to search for
        max_messages: Maximum number of messages to retrieve
        headless: Run browser in headless mode
        verbose: Print progress information
        filter_sender: Only include messages where sender matches sender_name

    Returns:
        List of ZulipMessage objects
    """
    from playwright.async_api import async_playwright

    messages: list[ZulipMessage] = []
    seen_ids: set[int] = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="zulip-scraper/1.0"
        )
        page = await context.new_page()

        # Build search URL - search by name (more reliable than email)
        search_url = f"{ZULIP_BASE_URL}/#narrow/search/{quote(sender_name)}"

        if verbose:
            print(f"Navigating to: {search_url}")

        await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)

        # Wait for initial messages to load
        try:
            await page.wait_for_selector(".message_row", timeout=15000)
        except Exception:
            print("No messages found or page didn't load properly")
            await browser.close()
            return messages

        # Give extra time for messages to fully render
        await page.wait_for_timeout(3000)

        if verbose:
            print("Initial messages loaded, starting extraction...")

        # Scroll and extract messages
        last_count = 0
        no_progress_count = 0
        max_no_progress = 5  # Stop after 5 scrolls with no new messages

        while len(messages) < max_messages and no_progress_count < max_no_progress:
            # Extract visible messages with improved stream/topic detection
            raw_messages = await page.evaluate("""
                () => {
                    const messages = [];
                    const rows = document.querySelectorAll('.message_row');
                    for (const row of rows) {
                        const content = row.querySelector('.message_content');
                        const sender = row.querySelector('.sender_name');
                        const time = row.querySelector('.message_time');

                        // Get message ID from data attribute
                        const msgId = parseInt(row.getAttribute('data-message-id') || '0');

                        // Find stream/topic from recipient row (parent container)
                        let stream = null;
                        let topic = null;
                        const recipientRow = row.closest('.recipient_row');
                        if (recipientRow) {
                            const streamEl = recipientRow.querySelector('.stream_label');
                            const topicEl = recipientRow.querySelector('.topic_name') ||
                                           recipientRow.querySelector('.narrow_header .topic_text');
                            stream = streamEl?.textContent?.trim() || null;
                            topic = topicEl?.textContent?.trim() || null;
                        }

                        if (content && msgId) {
                            messages.push({
                                id: msgId,
                                sender: sender?.textContent?.trim() || 'Unknown',
                                content: content.textContent?.trim() || '',
                                timestamp: time?.getAttribute('datetime') || '',
                                stream: stream,
                                topic: topic,
                            });
                        }
                    }
                    return messages;
                }
            """)

            # Add new messages (optionally filter by sender)
            for msg in raw_messages:
                if msg["id"] not in seen_ids:
                    seen_ids.add(msg["id"])
                    # Filter by sender if requested
                    if filter_sender and msg["sender"].lower() != sender_name.lower():
                        continue
                    messages.append(ZulipMessage(
                        id=msg["id"],
                        sender=msg["sender"],
                        content=msg["content"],
                        timestamp=msg["timestamp"] or datetime.now().isoformat(),
                        stream=msg["stream"],
                        topic=msg["topic"],
                        url=f"{ZULIP_BASE_URL}/#narrow/id/{msg['id']}",
                    ))

            if verbose:
                print(f"  Extracted {len(messages)} messages so far...")

            # Check progress
            if len(messages) == last_count:
                no_progress_count += 1
            else:
                no_progress_count = 0
                last_count = len(messages)

            # Scroll up to load older messages (Zulip loads older messages at top)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(1500)  # Wait for messages to load

        await browser.close()

    # Sort by timestamp (oldest first)
    messages.sort(key=lambda m: m.timestamp)

    if verbose:
        print(f"Finished! Total messages: {len(messages)}")

    return messages


def save_messages_json(messages: list[ZulipMessage], output_path: Path) -> None:
    """Save messages to JSON file."""
    data = {
        "scraped_at": datetime.now().isoformat(),
        "total_count": len(messages),
        "messages": [asdict(m) for m in messages],
    }
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"Saved {len(messages)} messages to {output_path}")


def save_messages_markdown(messages: list[ZulipMessage], output_path: Path) -> None:
    """Save messages to markdown file."""
    lines = [
        "# Zulip Messages",
        "",
        f"Scraped: {datetime.now().isoformat()}",
        f"Total: {len(messages)} messages",
        "",
        "---",
        "",
    ]

    # Group by stream/topic
    grouped: dict[str, list[ZulipMessage]] = {}
    for msg in messages:
        key = f"{msg.stream or 'unknown'} > {msg.topic or 'unknown'}"
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(msg)

    for stream_topic, msgs in sorted(grouped.items()):
        lines.append(f"## {stream_topic}")
        lines.append("")
        for msg in msgs:
            # Format timestamp
            try:
                dt = datetime.fromisoformat(msg.timestamp.replace("Z", "+00:00"))
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                time_str = msg.timestamp[:16] if msg.timestamp else "unknown"

            lines.append(f"### {msg.sender} ({time_str})")
            lines.append("")
            # Indent content and escape any markdown
            content = msg.content.replace("\n", "\n> ")
            lines.append(f"> {content}")
            lines.append("")
            if msg.url:
                lines.append(f"[View on Zulip]({msg.url})")
            lines.append("")
            lines.append("---")
            lines.append("")

    output_path.write_text("\n".join(lines))
    print(f"Saved markdown to {output_path}")


def save_by_stream(messages: list[ZulipMessage], output_dir: Path) -> None:
    """Save messages organized by stream into separate files."""
    by_stream_dir = output_dir / "by_stream"
    by_stream_dir.mkdir(exist_ok=True)

    # Group by stream
    streams: dict[str, list[ZulipMessage]] = {}
    for msg in messages:
        stream = msg.stream or "unknown"
        # Sanitize stream name for filename
        safe_stream = re.sub(r'[^\w\-]', '_', stream)
        if safe_stream not in streams:
            streams[safe_stream] = []
        streams[safe_stream].append(msg)

    for stream_name, msgs in streams.items():
        stream_file = by_stream_dir / f"{stream_name}.json"
        data = {
            "stream": stream_name,
            "message_count": len(msgs),
            "messages": [asdict(m) for m in msgs],
        }
        stream_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    print(f"Saved messages by stream to {by_stream_dir}/")


async def main():
    parser = argparse.ArgumentParser(description="Scrape Zulip messages by sender")
    parser.add_argument(
        "--sender",
        default="Eric Vergo",
        help="Display name of sender to search for (default: Eric Vergo)",
    )
    parser.add_argument(
        "--participated",
        action="store_true",
        help="Use authenticated participated tab scraping (recommended, requires manual login)",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=1000,
        help="Maximum messages to retrieve in search mode (default: 1000)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show browser window in search mode (useful for debugging)",
    )
    parser.add_argument(
        "--no-filter",
        action="store_true",
        help="Include all messages in search results, not just from sender",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print progress information",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})",
    )

    args = parser.parse_args()

    print(f"Scraping Zulip messages from sender: {args.sender}")
    print(f"Mode: {'Participated (authenticated)' if args.participated else 'Public search'}")
    print(f"Output directory: {args.output_dir}")
    print()

    if args.participated:
        messages = await scrape_participated(
            sender_name=args.sender,
            verbose=args.verbose,
        )
    else:
        print(f"Max messages: {args.max_messages}")
        print(f"Filter by sender: {not args.no_filter}")
        messages = await scrape_sender_messages(
            sender_name=args.sender,
            max_messages=args.max_messages,
            headless=not args.no_headless,
            verbose=args.verbose,
            filter_sender=not args.no_filter,
        )

    if messages:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        save_messages_json(messages, args.output_dir / "messages.json")
        save_messages_markdown(messages, args.output_dir / "messages.md")
        save_by_stream(messages, args.output_dir)
    else:
        print("No messages found!")


if __name__ == "__main__":
    asyncio.run(main())
