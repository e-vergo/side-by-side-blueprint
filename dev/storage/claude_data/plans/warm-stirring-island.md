# Plan: Professional Styling for Claude Code Chat Logs (Phase 2)

## Goal
Update the chat log background to match the project homepage's professional aesthetic.

## Scope (Minimal)
Based on discussion, the scope is intentionally narrow:
- **Do**: Update body background gradient to match homepage
- **Do**: Ensure title remains readable
- **Don't**: Change card/message styling
- **Don't**: Add custom tooltips (native `title` attributes work well)
- **Don't**: Add header bar styling
- **Don't**: Additional polish items

## Implementation

### 1. Update `style_logs.py`

Add CSS override for body background:

```python
# Add to BUTTON_ICON_CSS or create new constant
BACKGROUND_CSS = """
/* Match homepage color scheme */
body {
    background: linear-gradient(120deg, #09203F, #537895) !important;
    background-attachment: fixed;
}

/* Ensure title is readable on dark background */
h1 {
    color: #ffffff !important;
}
"""
```

### 2. Inject Before `</style>`

Update the injection in `process_html()`:
```python
content = content.replace('</style>', BUTTON_ICON_CSS + BACKGROUND_CSS + '\n</style>')
```

## Color Reference (from homepage)
- Primary: `#09203F` (deep navy)
- Secondary: `#537895` (steel blue)
- Gradient: `linear-gradient(120deg, #09203F, #537895)`

## Files Modified
- `chat_logs/style_logs.py` - Add background CSS injection

## Usage
```bash
claude-code-log chat_logs/ -o chat_logs/all_sessions.html
python3 chat_logs/style_logs.py chat_logs/*.html
```

## Verification
1. Run the script on HTML files
2. Open in browser
3. Confirm:
   - Background matches homepage gradient
   - Title (h1) is white and readable
   - Message cards remain unchanged and readable
   - Floating buttons still visible and functional
