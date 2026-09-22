---
title: 'Product Guidelines: PyLabPraxis'
---

# Product Guidelines: PyLabPraxis

## Visual Identity & Aesthetic
PyLabPraxis employs a tiered aesthetic that balances clarity with information density:
*   **The Clinical Core:** The primary navigation and "Home" dashboards are clean, high-contrast, and clinical. This minimizes distractions and emphasizes immediate operational status.
*   **Modern Accessibility:** Throughout the general application flow, the interface uses modern design principles (soft shadows, rounded corners, intuitive spacing) to provide a friendly, non-intimidating experience for all users.
*   **Dynamic Information Density:** In data-heavy suites (Data Visualization, Network Auditing), the UI transitions to a high-density, dashboard-style layout. These interfaces are user-specifiable, allowing for the maximum information throughput required for expert tasks.
*   **Theme Support:** Full support for both Light and Dark modes to accommodate different lighting conditions in the lab and personal preference.

## User Experience (UX) & Interaction
*   **Proactive Guardrails:** The system prioritizes pre-execution checks. It provides clear, actionable guidance (e.g., "Load these 96-well tip racks on the deck") to prevent failures before they occur.
*   **Layered Error Handling:**
    *   **Automated Recovery:** For known failure modes, the system offers patches or recovery operations (e.g., "Retry," "Skip Step") governed by state condition constraints.
    *   **Detailed Forensics:** For unresolvable or undocumented failures, the system provides deep forensic logs and stack traces accessible to Engineers/Admins, while presenting a simplified status message to Scientists.
*   **Context-Aware Identity:** The UI dynamically adapts based on the role, surfacing only the tools and complexities relevant to the current task and permissions.

## Communication & Messaging
*   **Helpful & Instructive Tone:** Messaging is clear, concise, and focused on instruction. It avoids unnecessary jargon for Researchers while remaining technically precise for Engineers.
*   **Guidance over Documentation:** Whenever possible, the UI guides the user through complex operations (like setting up a new workcell) rather than relying on external documentation.
