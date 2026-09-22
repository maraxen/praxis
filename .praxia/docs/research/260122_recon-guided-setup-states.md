---
title: 'Reconnaissance Report: Guided Setup Visual State Transitions'
---

# Reconnaissance Report: Guided Setup Visual State Transitions

## Summary of Investigation

This report documents the reconnaissance performed to analyze a reported UI state issue in a "guided setup" feature. The investigation was unable to locate the specified feature, and therefore cannot provide the requested analysis. This report details the search process and provides recommendations for moving forward.

### Search Process

The investigation began with a search for the files and CSS classes mentioned in the task description:

*   **File:** `praxis/web-client/src/app/features/run-protocol/components/guided-setup/guided-setup.component.ts`
*   **CSS Classes:** `.requirement-card`, `.setup-card`

When these searches yielded no results, the investigation was broadened to include a systematic search of the codebase. The following steps were taken:

1.  **File and Directory Listing:** The contents of the `praxis/web-client/src/app/features/run-protocol/` directory and its `components` subdirectory were listed to identify any components that might contain the guided setup feature. The components found were `run-protocol.component.ts` and `live-dashboard.component.ts`.

2.  **File Analysis:** The following files were read and analyzed:
    *   `praxis/web-client/src/app/features/run-protocol/components/run-protocol.component.ts`
    *   `praxis/web--client/src/app/features/run-protocol/components/live-dashboard.component.ts`
    *   `praxis/web-client/src/app/features/run-protocol/run-protocol.routes.ts`
    *   `praxis/web-client/src/app/features/run-protocol/services/execution.service.ts`

3.  **Keyword Searches:** The entire `praxis/web-client` directory was searched for the following keywords:
    *   `guided-setup`
    *   `requirement-card`
    *   `stepper`
    *   `carrier`

4.  **Full File Listing:** A full listing of all `.ts` files in the `praxis/web-client` directory was generated and reviewed to identify any other potential locations for the guided setup feature.

## Findings

The investigation concluded that **the guided setup feature, as described in the task, could not be located within the codebase.** None of the specified files or CSS classes were found, and extensive searches for related keywords did not reveal any components with similar functionality.

As a result, it is not possible to provide the requested analysis, which included:

*   Documentation of the current state machine
*   CSS class mapping
*   Identification of missing state transitions
*   A gap analysis of the carrier step
*   Implementation recommendations

It is likely that the feature either has a different name than "guided setup," is located in a different part of the codebase than was indicated, or does not yet exist.

## Recommendations

To proceed with the analysis, it is recommended that the user provide more specific information about the feature's location. This could include:

*   **The correct file name** of the component that contains the guided setup feature.
*   **The route** that is used to access the feature in the application.
*   **Any other relevant information** that could help to locate the feature, such as the name of a parent component or a related service.
