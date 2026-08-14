## Context

The IPv6 RAG frontend is currently styled with a default dark palette. The user requested adding Dark and Light theme toggle buttons, where Dark uses a dark gray background and Light uses a white background, with harmonious accent colors tailored to each theme.

## Goals / Non-Goals

**Goals:**
- Provide intuitive Dark/Light toggle controls accessible from the sidebar.
- Implement CSS variables keyed on `:root[data-theme="dark"]` and `:root[data-theme="light"]`.
- Ensure flawless text contrast, code block highlighting readability, and citation drawer appearance in both modes.
- Save user choice in `localStorage.getItem('theme')` and apply instantly without page flicker.

**Non-Goals:**
- Custom RGB color pickers (stick to carefully designed Dark Gray & Pure White themes).

## Decisions

1. **Color Palette Design**:
   - **Dark Theme (深灰主題)**:
     - Background: `--bg-main: #18181b` (Zinc-900), Sidebar: `--bg-sidebar: #121215`, Card: `--bg-card: #27272a`, Borders: `--border-color: #3f3f46`
     - Foreground Accent: `--accent: #38bdf8` (Sky Blue) & `--accent-soft: rgba(56, 189, 248, 0.15)`
     - Text: `--text-main: #f4f4f5`, `--text-muted: #a1a1aa`
   - **Light Theme (明亮純白主題)**:
     - Background: `--bg-main: #ffffff`, Sidebar: `--bg-sidebar: #f8fafc`, Card: `--bg-card: #f1f5f9`, Borders: `--border-color: #e2e8f0`
     - Foreground Accent: `--accent: #0284c7` (Ocean Blue) & `--accent-soft: rgba(2, 132, 199, 0.12)`
     - Text: `--text-main: #0f172a`, `--text-muted: #475569`, User Bubble: `#2563eb` with white text.

2. **Storage & Hydration**:
   - Apply `data-theme` attribute on `<html>` / `<body>` before render to avoid flash of incorrect theme.

## Risks / Trade-offs

- [Risk] Highlight.js code blocks might have illegible background in light mode.
  → *Mitigation*: Adjust inline pre/code CSS styles to dynamically adapt to current theme variables.
