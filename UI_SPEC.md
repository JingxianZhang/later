# UI Design Specification: Project Later

## Design Principles
-   **Project Name:** Later
-   **Aesthetic:** "Digital Zen." Clean, organized, minimal, developer-friendly. Dark Mode preferred.
-   **Responsiveness:** Must be perfectly tailored for mobile (Audio-First) and desktop (Grid-First).

## 1. The Web Dashboard (Desktop)
**Use Case:** Organization, Deep Reading, Management.

### A. The "Drop Zone" (Hero Section)
-   **Placement:** Prominently centered at the top of the main dashboard.
-   **Visual:** Large, dashed-border rectangle.
-   **Text:** "Paste a link, drag a screenshot, or type a tool name here to start scouting."
-   **Key Feedback:** Must show a distinct state: "Scouting..." (with a loading bar) and "Knowledge Captured" (with a green check).

### B. The Knowledge Gallery (Main Content)
-   **Layout:** Responsive Masonry Grid or Card Grid.
-   **Filters/Tabs:** "All Tools", "Watchlist (Star Icon)", "New Updates (Badge)", "Categories (Pills)".
-   **Tool Card Component:**
    -   **Header:** Tool Icon + Name + **Watchlist Star (Toggle)**.
    -   **Badges:** Small pills showing auto-generated categories (e.g., `#Video`, `#RAG`).
    -   **Status Indicator:** Small colored dot (e.g., 🟢 for New Update, 🔵 for New Discovery).
    -   **Action:** Hover to show "Quick Summary" and "Start Chat" button.

### C. The Detail View (Modal or Split Screen)
-   **Layout:** Two-column split (e.g., 60% Left for Report, 40% Right for Chat).
-   **Left Panel (The Fact Sheet):**
    -   Renders the `one_pager` JSON data cleanly using richer fields:
        - overview_long (primary summary)
        - key_features_detailed (bulleted)
        - how_to_use (ordered steps)
        - use_cases
        - pricing (normalized tiers)
        - competitors (with differentiators)
        - integrations
        - user_feedback (short quotes + platform/source link)
        - tech_stack and sources
    -   Do not show verification badges in Phase 1; trust signals are backend-only for now.
-   **Right Panel (The Conversation):**
    -   Chat history specific to this tool.
    -   **Input:** Standard text box + prominent **Microphone Icon** (for desktop users with a mic).

## 2. The Mobile Interface
**Use Case:** Quick Capture & Audio Conversation.

### A. The Primary Capture Interface
-   **Home Screen Focus:** Dominated by a large, central **Microphone Button**.
-   **Interaction:** "Hold to speak" (like a Walkie-Talkie).
-   **Other Capture Modes:** Small icons for [Camera/Gallery] (for screenshots with OCR) and [Paste Link] below the microphone.

### B. The Feed View
-   **Layout:** Single-column vertical scroll of your saved tools.
-   **Content:** Only the Tool Name, One-Liner, and Watchlist status.
-   **Action:** Tapping a card opens the Detail View. Swiping right initiates the **Chat** interface directly.

### C. Conversation View (Mobile)
-   **Mode:** Full-screen overlay/drawer.
-   **Input:** The text field should have the **Microphone Icon** prominently placed to encourage audio input over typing on a small screen. Use a waveform visualizer when the user is speaking.