"""
Dev server for Side-by-Side Blueprint.

Combines HTTP serving with WebSocket live reload and file watching.
When files change, the watcher triggers regeneration and pushes
reload messages to all connected browsers.
"""

from __future__ import annotations

import argparse
import asyncio
import functools
import json
import threading
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional

import websockets
from websockets.asyncio.server import serve as ws_serve, ServerConnection

from sbs.commands.watch import (
    ChangeAction,
    ChangeClassifier,
    Debouncer,
    Regenerator,
    SBSEventHandler,
    resolve_project,
    get_assets_dir,
    DEBOUNCE_SECONDS,
)
from sbs.core.utils import log, SBS_ROOT

try:
    from watchdog.observers import Observer
except ImportError:
    Observer = None  # type: ignore


# =============================================================================
# Injected Client Script
# =============================================================================

# The WebSocket port placeholder is replaced at runtime via str.replace().
LIVE_RELOAD_SCRIPT = """
<script>
(function() {
  var wsPort = __SBS_WS_PORT__;
  var ws = null;
  var reconnectDelay = 500;
  var maxReconnectDelay = 5000;
  var overlay = null;

  function createOverlay() {
    if (overlay) return overlay;
    overlay = document.createElement('div');
    overlay.id = 'sbs-reload-overlay';
    overlay.style.cssText = [
      'position: fixed',
      'top: 12px',
      'right: 12px',
      'background: rgba(0,0,0,0.75)',
      'color: #fff',
      'padding: 8px 16px',
      'border-radius: 6px',
      'font: 13px/1.4 -apple-system, sans-serif',
      'z-index: 999999',
      'pointer-events: none',
      'opacity: 0',
      'transition: opacity 0.2s'
    ].join(';');
    document.body.appendChild(overlay);
    return overlay;
  }

  function showOverlay(text) {
    var el = createOverlay();
    el.textContent = text;
    el.style.opacity = '1';
  }

  function hideOverlay() {
    if (overlay) overlay.style.opacity = '0';
  }

  function reloadCSS(filename) {
    var links = document.querySelectorAll('link[rel="stylesheet"]');
    var reloaded = 0;
    var stamp = '?t=' + Date.now();
    for (var i = 0; i < links.length; i++) {
      var href = links[i].getAttribute('href');
      if (!href) continue;
      // Strip existing query string for comparison
      var base = href.split('?')[0];
      if (!filename || base.indexOf(filename) !== -1 || base.endsWith('.css')) {
        links[i].setAttribute('href', base + stamp);
        reloaded++;
      }
    }
    return reloaded;
  }

  function connect() {
    try {
      ws = new WebSocket('ws://localhost:' + wsPort + '/ws');
    } catch (e) {
      scheduleReconnect();
      return;
    }

    ws.onopen = function() {
      reconnectDelay = 500;
      console.log('[SBS] Live reload connected');
    };

    ws.onmessage = function(event) {
      var msg;
      try {
        msg = JSON.parse(event.data);
      } catch (e) {
        return;
      }

      if (msg.type === 'css-reload') {
        showOverlay('Updating styles...');
        var count = reloadCSS(msg.file || null);
        console.log('[SBS] CSS reload: ' + count + ' stylesheet(s) updated');
        setTimeout(hideOverlay, 600);
      } else if (msg.type === 'reload') {
        showOverlay('Reloading...');
        setTimeout(function() { location.reload(); }, 100);
      }
    };

    ws.onclose = function() {
      ws = null;
      scheduleReconnect();
    };

    ws.onerror = function() {
      if (ws) ws.close();
    };
  }

  function scheduleReconnect() {
    setTimeout(function() {
      reconnectDelay = Math.min(reconnectDelay * 1.5, maxReconnectDelay);
      connect();
    }, reconnectDelay);
  }

  // Start connection when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', connect);
  } else {
    connect();
  }
})();
</script>
"""


# =============================================================================
# Script-Injecting HTTP Handler
# =============================================================================


class InjectingHandler(SimpleHTTPRequestHandler):
    """HTTP handler that injects the live reload script into HTML responses."""

    ws_port: int = 8001
    quiet: bool = True

    def __init__(self, *args, directory: str | None = None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format, *args):
        """Suppress default HTTP logging unless verbose."""
        if not self.quiet:
            super().log_message(format, *args)

    def do_GET(self):
        """Serve files, injecting reload script into HTML."""
        # Parse the path
        path = self.translate_path(self.path)
        f_path = Path(path)

        # If path is a directory, try index.html
        if f_path.is_dir():
            index = f_path / "index.html"
            if index.exists():
                f_path = index

        # For HTML files, inject the script
        if f_path.exists() and f_path.suffix in (".html", ".htm"):
            try:
                content = f_path.read_bytes()
                content_str = content.decode("utf-8", errors="replace")

                # Inject script before </body>
                script = LIVE_RELOAD_SCRIPT.replace("__SBS_WS_PORT__", str(self.ws_port))
                if "</body>" in content_str:
                    content_str = content_str.replace(
                        "</body>", script + "\n</body>", 1
                    )
                elif "</html>" in content_str:
                    content_str = content_str.replace(
                        "</html>", script + "\n</html>", 1
                    )
                else:
                    content_str += script

                encoded = content_str.encode("utf-8")

                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                # Prevent caching during dev
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                self.wfile.write(encoded)
                return
            except Exception:
                pass  # Fall through to default handling

        # For non-HTML files, serve normally
        super().do_GET()


# =============================================================================
# WebSocket Broadcast Server
# =============================================================================


class ReloadBroadcaster:
    """Manages WebSocket connections and broadcasts reload messages."""

    def __init__(self):
        self._clients: set[ServerConnection] = set()
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def handler(self, websocket: ServerConnection) -> None:
        """Handle a new WebSocket connection."""
        with self._lock:
            self._clients.add(websocket)
        count = self.client_count
        log.info(f"  Browser connected ({count} client{'s' if count != 1 else ''})")

        try:
            # Keep connection alive, handle pings automatically
            async for _ in websocket:
                pass  # We don't expect messages from clients
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            with self._lock:
                self._clients.discard(websocket)
            count = self.client_count
            log.info(f"  Browser disconnected ({count} client{'s' if count != 1 else ''})")

    def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients.

        Thread-safe: can be called from the watchdog/debouncer thread.
        """
        if self._loop is None:
            return

        with self._lock:
            clients = set(self._clients)

        if not clients:
            return

        data = json.dumps(message)

        async def _send_all():
            tasks = []
            for client in clients:
                tasks.append(self._safe_send(client, data))
            await asyncio.gather(*tasks)

        # Schedule the broadcast on the asyncio event loop
        asyncio.run_coroutine_threadsafe(_send_all(), self._loop)

    @staticmethod
    async def _safe_send(client: ServerConnection, data: str) -> None:
        try:
            await client.send(data)
        except Exception:
            pass  # Client disconnected, will be cleaned up in handler

    def notify_reload(self) -> None:
        """Send a full page reload message."""
        self.broadcast({"type": "reload"})

    def notify_css_reload(self, filename: Optional[str] = None) -> None:
        """Send a CSS-only reload message."""
        msg: dict = {"type": "css-reload"}
        if filename:
            msg["file"] = filename
        self.broadcast(msg)


# =============================================================================
# Notification Debouncer
# =============================================================================


class NotificationDebouncer:
    """Debounces reload notifications to avoid rapid-fire browser reloads.

    After the Regenerator finishes, we wait 50ms before notifying browsers
    in case another regeneration fires immediately.
    """

    def __init__(self, broadcaster: ReloadBroadcaster, delay: float = 0.05):
        self.broadcaster = broadcaster
        self.delay = delay
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._pending_type: Optional[str] = None
        self._pending_file: Optional[str] = None

    def schedule(self, reload_type: str, filename: Optional[str] = None) -> None:
        """Schedule a reload notification."""
        with self._lock:
            # Upgrade css-reload to full reload if needed
            if self._pending_type == "reload" and reload_type == "css-reload":
                # Already pending full reload, don't downgrade
                return
            self._pending_type = reload_type
            self._pending_file = filename

            if self._timer is not None:
                self._timer.cancel()

            self._timer = threading.Timer(self.delay, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        with self._lock:
            rtype = self._pending_type
            rfile = self._pending_file
            self._pending_type = None
            self._pending_file = None
            self._timer = None

        if rtype == "css-reload":
            self.broadcaster.notify_css_reload(rfile)
        elif rtype == "reload":
            self.broadcaster.notify_reload()

    def cancel(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None


# =============================================================================
# Dev Server
# =============================================================================


def _determine_reload_type(action: ChangeAction, paths: list[Path]) -> tuple[str, Optional[str]]:
    """Determine what kind of reload to send based on the regeneration action."""
    if action == ChangeAction.COPY_ASSETS:
        # Check if all changed files are CSS
        css_files = [p for p in paths if p.suffix == ".css"]
        if css_files and len(css_files) == len([p for p in paths if p.suffix in (".css", ".js")]):
            # All changed assets are CSS -> CSS-only reload
            return "css-reload", css_files[0].name if len(css_files) == 1 else None
    # Everything else: full reload
    return "reload", None


def cmd_dev(args: argparse.Namespace) -> int:
    """Execute the dev server command."""
    if Observer is None:
        log.error("watchdog is required: pip install watchdog>=3.0")
        return 1

    try:
        project_name, project_root = resolve_project(args.project)
    except ValueError as e:
        log.error(str(e))
        return 1

    try:
        assets_dir = get_assets_dir(project_root)
    except ValueError as e:
        log.error(str(e))
        return 1

    dressed_dir = project_root / ".lake" / "build" / "dressed"
    site_dir = project_root / ".lake" / "build" / "runway"
    http_port = args.port
    ws_port = http_port + 1

    # Validate site exists
    if not site_dir.exists():
        log.error(
            f"Site directory not found at {site_dir}\n"
            f"Run a build first: python build.py"
        )
        return 1

    log.header(f"SBS Dev Server: {project_name}")

    # Kill existing processes on both ports
    from sbs.build.phases import kill_processes_on_port
    kill_processes_on_port(http_port)
    kill_processes_on_port(ws_port)

    # --- Set up broadcaster ---
    broadcaster = ReloadBroadcaster()
    notifier = NotificationDebouncer(broadcaster)

    # --- Set up regenerator with notification callback ---
    classifier = ChangeClassifier(project_root, assets_dir, dressed_dir)
    regenerator = Regenerator(project_root, project_name, assets_dir)

    def on_regen(action: ChangeAction, paths: list[Path]) -> None:
        regenerator.execute(action, paths)
        reload_type, filename = _determine_reload_type(action, paths)
        notifier.schedule(reload_type, filename)
        client_count = broadcaster.client_count
        if client_count > 0:
            log.info(
                f"  Notifying {client_count} browser{'s' if client_count != 1 else ''}: "
                f"{reload_type}"
            )

    debouncer = Debouncer(DEBOUNCE_SECONDS, on_regen)
    handler = SBSEventHandler(classifier, debouncer)

    # --- Start HTTP server ---
    InjectingHandler.ws_port = ws_port
    handler_factory = functools.partial(
        InjectingHandler, directory=str(site_dir)
    )

    httpd = HTTPServer(("", http_port), handler_factory)
    http_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    http_thread.start()
    log.success(f"HTTP server: http://localhost:{http_port}")

    # --- Set up file watcher ---
    observer = Observer()

    watch_targets: list[tuple[str, Path, bool]] = []

    if assets_dir.exists():
        watch_targets.append(("Assets", assets_dir, False))
    else:
        log.warning(f"Assets directory not found: {assets_dir}")

    if dressed_dir.exists():
        watch_targets.append(("Artifacts", dressed_dir, True))
    else:
        log.info(f"Dressed artifacts dir not found (yet): {dressed_dir}")

    watch_targets.append(("Config", project_root, False))

    runway_lean_dir = SBS_ROOT / "toolchain" / "Runway"
    if runway_lean_dir.exists():
        watch_targets.append(("Templates", runway_lean_dir, True))

    for label, path, recursive in watch_targets:
        try:
            observer.schedule(handler, str(path), recursive=recursive)
            log.info(f"  Watching: {label} ({path})")
        except Exception as e:
            log.warning(f"  Could not watch {label}: {e}")

    observer.start()

    # --- Start WebSocket server on asyncio loop ---
    loop = asyncio.new_event_loop()
    broadcaster.set_loop(loop)

    async def run_ws_server():
        async with ws_serve(
            broadcaster.handler,
            "localhost",
            ws_port,
            # Process path: only accept /ws
            process_request=_ws_process_request,
        ):
            await asyncio.Future()  # Run forever

    def ws_thread_target():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_ws_server())

    ws_thread = threading.Thread(target=ws_thread_target, daemon=True)
    ws_thread.start()
    log.success(f"WebSocket server: ws://localhost:{ws_port}/ws")

    log.info("")
    log.info(f"Watching for changes... (Ctrl+C to stop)")
    log.info(f"  Site: http://localhost:{http_port}")
    log.info(f"  Live reload: ws://localhost:{ws_port}/ws")
    log.info("")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("")
        log.header("Shutting down")

        notifier.cancel()
        debouncer.cancel()
        observer.stop()
        observer.join(timeout=5)

        httpd.shutdown()
        loop.call_soon_threadsafe(loop.stop)

        kill_processes_on_port(http_port)
        kill_processes_on_port(ws_port)

        log.info(f"Regenerations performed: {regenerator.regen_count}")
        log.success("Dev server stopped")

    return 0


async def _ws_process_request(connection, request):
    """Only accept WebSocket connections on /ws path."""
    if request.path != "/ws":
        return connection.respond(HTTPStatus.NOT_FOUND, "Not found\n")
    return None
