---
title: 'Recon report: asset wizard visual grid sizing'
---

<recon_report>
<grid_analysis>
  <current_sizing>
    <property>grid-template-columns</property>
    <value>repeat(auto-fill, minmax(220px, 1fr)) for category grid and repeat(auto-fill, minmax(180px, 1fr)) for results grid</value>
    <issue>The minimum width of the grid items is too large, especially for the category selection. This results in fewer columns and a feeling of wasted space, contributing to the oversized and clunky appearance.</issue>
  </current_sizing>
  <current_sizing>
    <property>gap</property>
    <value>20px for type selection, 12px for category and results grids</value>
    <issue>The gap values are hardcoded and inconsistent. The 20px gap in the type selection is likely too large.</issue>
  </current_sizing>
</grid_analysis>

<spacing_issues>
  <issue location=".step-content" property="padding">
    <current>24px</current>
    <problem>Hardcoded pixel value. Should use a theme variable for consistency.</problem>
  </issue>
  <issue location=".type-selection" property="gap">
    <current>20px</current>
    <problem>Hardcoded pixel value and likely too large. Should use a theme variable.</problem>
  </issue>
  <issue location=".category-grid" property="gap">
    <current>12px</current>
    <problem>Hardcoded pixel value. Should use a theme variable.</problem>
  </issue>
    <issue location=".asset-wizard-container" property="height">
    <current>650px</current>
    <problem>The fixed height of the container can lead to either wasted space or clipped content on different screen sizes, contributing to the clunky feel. A more flexible approach using min-height or max-height would be better.</problem>
  </issue>
</spacing_issues>

<comparison_to_polished>
  <component name="machine-card">
    <pattern>The machine-card component uses TailwindCSS utility classes for spacing and layout, which ensures consistency and adherence to a design system. It also uses more subtle and modern styling, such as gradients and gentle hover effects. It does not have a fixed height, allowing it to adapt to its content.</pattern>
    <applicable_here>The asset-wizard should adopt a similar approach by using theme variables for all spacing and sizing, and by using more subtle and modern styling for cards and other elements. The fixed height on the container should be removed in favor of a more flexible layout.</applicable_here>
  </component>
</comparison_to_polished>

<full_issue_list>
  <issue priority="high">The grid layout is oversized due to large minimum item widths, resulting in a clunky and inefficient use of space.</issue>
  <issue priority="high">Inconsistent spacing due to a mix of hardcoded pixel values and theme variables.</issue>
  <issue priority="medium">The fixed height of the main container can lead to poor responsive behavior.</issue>
  <issue priority="medium">The card styling is heavy-handed, with large borders and shadows on hover, making it feel dated compared to other components.</issue>
  <issue priority="low">The use of `!important` in the SCSS should be avoided where possible.</issue>
</full_issue_list>
</recon_report>
