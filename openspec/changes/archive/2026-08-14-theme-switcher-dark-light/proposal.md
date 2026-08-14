## Why

Adding a theme toggle between Dark and Light modes enhances usability and visual comfort across different lighting environments and user preferences.

## What Changes

- Add a Theme Switcher button/control (Dark / Light) in the frontend interface.
- Implement a dual-theme CSS variable system:
  - **Dark Mode**: Charcoal / dark gray background (`#18181b` / `#27272a`), slate card surfaces, cyan/sky blue accent, high legibility light text.
  - **Light Mode**: Clean white background (`#ffffff`), soft gray card surfaces (`#f8fafc` / `#f1f5f9`), vivid sapphire/indigo accent (`#2563eb`), crisp dark text.
- Support `localStorage` persistence and automatic system theme detection.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `qa-web-interface`: Added theme switching controls, CSS custom properties for Dark (dark gray) and Light (white) modes, and theme state persistence.

## Impact

- Frontend CSS (`app/static/style.css`), HTML (`app/static/index.html`), and JS (`app/static/app.js`).
- No backend or vector database changes required.
