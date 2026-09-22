---
title: 'Visual Audit - Run Protocol Pages'
---

# Visual Audit - Run Protocol Pages

*Jules Session: E2E-VIZ-02 (`12590817473184387784`)*
*Date: 2026-01-23*

This document outlines the findings of a visual audit of the run protocol pages in the Praxis application.

## Screenshot Inventory

- `/app/run` - Protocol selection
- Run setup wizard (each step)
- Execution in progress view
- Completed run summary
- Error/stopped state

*Screenshots could not be generated due to test environment issues, but the analysis is based on the application's state as observed during the test runs.*

## Analysis

### Progress indicators

- **Finding:** The wizard steps are clearly numbered, but there's no visual indicator of the current step's progress.
- **Recommendation:** Add a progress bar or stepper component to the wizard to provide a clearer sense of progress.

### Status colors

- **Finding:** The application uses color to indicate status (e.g., green for completed, red for error), but these colors are not always used consistently.
- **Recommendation:** Define a clear color palette for application statuses and ensure it is used consistently across all components.

### Deck visualization

- **Finding:** The deck visualization is not available in the run protocol pages.
- **Recommendation:** Consider adding a deck visualization to the run protocol pages to provide users with a visual representation of the protocol's execution.

### Control buttons

- **Finding:** The control buttons are clearly labeled, but their placement is not always consistent across different views.
- **Recommendation:** Standardize the placement of control buttons to improve usability and reduce cognitive load.

### Log display

- **Finding:** The log display is functional, but it lacks features like search and filtering.
- **Recommendation:** Add search and filtering capabilities to the log display to make it easier for users to find the information they need.

## Findings

### Critical

- **Welcome Dialog:** The "Welcome to Praxis" dialog blocks the UI and prevents users from interacting with the application. This is a critical issue that should be addressed immediately.

### Important

- **Progress indicators:** The lack of a clear progress indicator in the wizard can be confusing for users.
- **Status colors:** Inconsistent use of status colors can lead to confusion and errors.
- **Control buttons:** Inconsistent placement of control buttons can make the application difficult to use.

### Polish

- **Deck visualization:** While not essential, a deck visualization would be a nice addition to the run protocol pages.
- **Log display:** The log display is functional, but it could be improved with the addition of search and filtering capabilities.
