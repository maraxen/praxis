---
title: 'AUDIT-09: Direct Control Feature'
---

# AUDIT-09: Direct Control Feature

## 1. Component Map

This table outlines the files related to the Direct Control feature and their primary purpose.

| File Path                                                                                | Purpose                                                                                                                                                             |
| ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `praxis/web-client/src/app/features/playground/components/direct-control/direct-control.component.ts` | **(Component Logic)** Manages state, builds parameter forms, and emits command execution events. Contains the mock data source for machine methods.              |
| `praxis/web-client/src/app/features/playground/components/direct-control/direct-control.component.html` | **(Component Template)** Renders the UI, including the machine header, method selection buttons, and the dynamic parameter form.                                        |
| `praxis/web-client/src/app/features/playground/components/direct-control/direct-control.component.scss` | **(Component Styles)** Provides the specific styling for the Direct Control component.                                                                              |
| `praxis/web-client/e2e/specs/playground-direct-control.spec.ts`                             | **(E2E Test)** A minimal test that verifies the component is visible after a machine is created. It **does not** test any of the feature's core functionality. |

## 2. User Flow Diagram

This diagram illustrates the current user and data flow within the Direct Control component.

```mermaid
graph TD
    A[User selects a machine in parent component] --> B(DirectControlComponent: @Input() machine);
    B --> C{ngOnChanges triggers};
    C --> D[loadMethods()];
    D --> E[getMockMethodsForCategory(category)];
    E --> F[Generate hardcoded list of MethodInfo[]];
    F --> G(UI: Render method buttons);

    subgraph User Interaction
        G --> H{User clicks a method};
        H --> I[onMethodSelected(method)];
        I --> J[buildForm(method)];
        J --> K(UI: Render parameter form);
        K --> L{User fills form};
        L --> M{User clicks 'Execute'};
    end

    M --> N[runCommand()];
    N --> O(Emit executeCommand event);

    subgraph Parent Component / External
        O --> P[Parent component listens for event];
        P --> Q[Sends command to backend];
        Q --> R{...receives response/error...};
    end

    subgraph GAP
        R -.-> S((No feedback loop to DirectControlComponent));
    end

    style GAP fill:#f00,color:#fff,stroke:#333,stroke-width:2px
```

## 3. Parameter Types Matrix

The component determines which input to render based on a simple string search within the `type` property of a method argument.

| Supported Type String          | Rendered Input Control | `getArgType` Logic Reference                                     |
| ------------------------------ | ---------------------- | ---------------------------------------------------------------- |
| `int`, `float` (or any substring) | `<input type="number">`  | `direct-control.component.ts:189` `type.includes('int')`         |
| `bool` (or any substring)         | `<mat-checkbox>`       | `direct-control.component.ts:190` `type.includes('bool')`        |
| **(Default)** Any other string     | `<input type="text">`    | `direct-control.component.ts:191` (Default case)                 |

_**Note:** This means complex types like `list[int]` are currently rendered as a generic text input, requiring the user to manually format the string correctly._

## 4. Gap / Limitation List

| Severity | ID / Title                                 | Description                                                                                                                                                                                                                                                              | File / Line Reference                                                                                                 |
| :------: | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
|    🔴    | **Mock Data Source**                       | The component **does not** fetch real methods from the machine's definition. It uses a hardcoded mock function (`getMockMethodsForCategory`) based on a simple category string. The UI is completely disconnected from the machine's actual capabilities.                  | `direct-control.component.ts:60-164`                                                                                  |
|    🔴    | **No Response/Error Handling**             | The component "fires and forgets" an event. There is no mechanism to display the result of a command (success or failure) to the user. This makes the feature unusable for any real workflow, as the user has no feedback.                                                | `direct-control.component.ts:200` (emit)                                                                              |
|    🟠    | **Limited Parameter Type Support**         | The `getArgType` function only supports `number`, `boolean`, and `text`. It cannot handle complex but common types like lists, dictionaries, or enums, forcing users into a poor UX with manual text entry for complex data.                                                | `direct-control.component.ts:187-193`                                                                                 |
|    🟠    | **Inadequate Parameter Validation**        | The `[disabled]="!form.valid"` check is superficial. It only ensures fields are present, not correctly formatted. For example, a `list[int]` field (rendered as text) would accept `"hello world"` as valid input.                                                      | `direct-control.component.html:89`                                                                                    |
|    🟡    | **Known Bug (FIX-04) Workaround**          | The code defensively checks `(method.args || [])` to prevent crashing if `args` is `undefined`. This is a workaround, not a fix for the underlying issue of why a method definition might be missing an `args` property.                                                     | `direct-control.component.ts:178`                                                                                     |
|    🟡    | **No State for Long-Running Commands**     | The UI provides no feedback for commands that are in progress. The "Execute" button can be clicked again, and there is no indication of activity, timeouts, or disconnections.                                                                                         | N/A (Feature is missing entirely)                                                                                     |

## 5. Recommended Test Cases

Based on the audit, the following test cases are recommended to ensure basic functionality and address the identified gaps.

#### Current State (Can be implemented now)
1.  **Machine Selection:** Test that when a machine is passed as input, the method buttons are rendered.
2.  **Method Selection:** Test that clicking a method button displays the correct parameter form.
3.  **Form Building:** Test that default values from `MethodInfo` are populated into the form fields.
4.  **No-Args Method:** Test that selecting a method with `args: []` shows the "No parameters required" message.
5.  **Event Emission:** Test that clicking "Execute" emits the `executeCommand` event with the correct `machineName`, `methodName`, and `args` payload.
6.  **Form Validation:** Test that the "Execute" button is disabled if a required parameter is missing.

#### Future State (Requires fixing gaps first)
7.  **Real Method Fetching:** Test that the component correctly fetches and displays methods from a live data source.
8.  **Success Feedback:** Test that a success message and/or data payload is displayed correctly after a command executes successfully.
9.  **Error Feedback:** Test that an error message from a failed command is displayed to the user.
10. **Complex Type Rendering:** Test that an argument with `type: 'list[int]'` renders a specialized UI control (e.g., a chip input).
11. **Complex Type Validation:** Test that the form correctly validates input for complex types (e.g., rejects non-numeric input for a list of ints).
12. **In-Progress State:** Test that the "Execute" button becomes disabled and shows a loading indicator while a command is pending.

## 6. Shipping Blockers

The following issues are considered critical and **must be addressed** before this feature can be considered shippable:

1.  **Reliance on Mock Data:** The feature is fundamentally non-functional as it does not reflect the real capabilities of any selected machine. It **must** be integrated with a backend service or the machine's introspection capabilities to fetch a real list of methods.
2.  **Lack of User Feedback:** The absence of any mechanism to show the result of an executed command (be it success or failure) makes the feature unusable and potentially dangerous. The user has no way of knowing if their action had any effect.

