---
title: 'RECONNAISSANCE REPORT: Praxis Logo and Gradient Branding'
---

# RECONNAISSANCE REPORT: Praxis Logo and Gradient Branding

## 1. Executive Summary
This report details the findings of a reconnaissance mission to locate and document the Praxis application's logo and its gradient styling. The investigation confirms the existence of a base SVG logo asset and identifies the specific brand colors used in the in-app gradient. A standalone SVG with the gradient applied does not currently exist; the effect is achieved dynamically with CSS. The report recommends the creation of a self-contained, gradient-styled SVG for wider use and identifies key integration points.

## 2. Existing Asset Inventory
- **Asset:** `praxis_logo.svg`
- **Location:** `praxis/web-client/src/assets/logo/praxis_logo.svg`
- **Format:** Scalable Vector Graphics (SVG)
- **Description:** The existing logo is a single-color SVG. The paths are filled with solid black (`#000000`). This asset serves as a base template that is styled with a gradient using CSS masking within the application's main shell component.

## 3. Gradient Color Values
The application's gradient styling is defined in `praxis/web-client/src/styles.scss`. The gradient is composed of a primary and a tertiary brand color, with an intermediate lighter shade.

- **Primary Color (Rose Pompadour):**
  - **Variable:** `$rose-pompadour`
  - **CSS Variable:** `--primary-color`
  - **Hex:** `#ED7A9B`
  - **RGB:** `rgb(237, 122, 155)`

- **Tertiary Color (Moonstone Blue):**
  - **Variable:** `$moonstone-blue`
  - **CSS Variable:** `--tertiary-color`
  - **Hex:** `#73A9C2`
  - **RGB:** `rgb(115, 169, 194)`

- **Intermediate Color (Light Rose):**
  - **Hex:** `#ff8fa8`
  - **RGB:** `rgb(255, 143, 168)`

- **CSS Gradient Definition:**
  ```css
  --gradient-primary: linear-gradient(135deg, var(--primary-color) 0%, #ff8fa8 50%, var(--tertiary-color) 100%);
  ```
  The logo in the unified shell uses a slightly different gradient:
  ```css
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--tertiary-color) 100%);
  ```

## 4. Logo Status
- **Status:** **Needs Creation**
- **Analysis:** There is currently no SVG asset for the Praxis logo that includes an embedded gradient. The gradient effect is applied dynamically at runtime using a CSS `mask` property on a `div` element, which uses the black SVG as the mask shape.
  - **File:** `praxis/web-client/src/app/layout/unified-shell.component.ts`
  - **CSS Snippet:**
    ```css
    .logo-image {
      background: linear-gradient(135deg, var(--primary-color) 0%, var(--tertiary-color) 100%);
      -webkit-mask: url('/assets/logo/praxis_logo.svg') no-repeat center;
      mask: url('/assets/logo/praxis_logo.svg') no-repeat center;
      mask-size: contain;
    }
    ```
This approach works well within the app but is not portable for use in other contexts (e.g., README files, documentation, favicons).

## 5. Proposed SVG Creation Approach
To create a portable, universally recognizable brand asset, it is recommended to create a new SVG file named `praxis_logo_gradient.svg`.

- **Method:**
  1. **Edit the existing `praxis_logo.svg` file.**
  2. **Add a `<defs>` section** to the SVG markup.
  3. **Define a `<linearGradient>`** inside `<defs>`. This gradient should have an ID (e.g., `praxis-gradient`) and contain `<stop>` elements corresponding to the colors and offsets from the CSS definition.
  4. **Modify the existing `<path>` elements.** Change the `fill="#000000"` attribute to `fill="url(#praxis-gradient)"` to apply the newly defined gradient.
  5. **Save the modified file** as `praxis_logo_gradient.svg` in the `praxis/web-client/src/assets/logo/` directory.

This approach will create a self-contained SVG that renders correctly across different platforms (web browsers, GitHub, image viewers) without requiring external CSS.

## 6. Integration Points
Once the new gradient logo SVG is created, it should be integrated into the following areas to ensure consistent branding:

1.  **README.md:** Add the logo to the main `README.md` file at the repository root.
2.  **Documentation:** Embed the logo in the main landing page of the project's documentation.
3.  **Favicon:** Use the new SVG as the source for generating `favicon.ico` and other related icon formats for the web client.
4.  **In-App Usage:** Consider replacing the current CSS mask implementation in `unified-shell.component.ts` with a direct `<img>` tag pointing to the new SVG for simplicity and to guarantee consistency.
