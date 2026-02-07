import { Page, TestInfo } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Test utilities for enhanced debugging based on Jules UI Debugging Research.
 * Implements accessibility tree capture and error context aggregation.
 */

/**
 * Capture the accessibility tree of the page as a YAML-like structure.
 * This is more AI-parseable than raw HTML and recommended for debugging.
 */
export async function captureAccessibilityTree(page: Page): Promise<string> {
    try {
        const snapshot = await page.locator('body').ariaSnapshot();
        return snapshot;
    } catch (error) {
        return `[Error capturing accessibility tree: ${error}]`;
    }
}

/**
 * Format an accessibility node recursively as YAML-like structure.
 */
function formatAccessibilityNode(node: any, indent: number): string {
    if (!node) return '';

    const padding = '  '.repeat(indent);
    let result = `${padding}- ${node.role || 'unknown'}`;

    // Add relevant properties
    if (node.name) result += ` "${node.name}"`;
    if (node.selected) result += ' [selected]';
    if (node.checked) result += ' [checked]';
    if (node.disabled) result += ' [disabled]';
    if (node.focused) result += ' [focused]';
    if (node.expanded !== undefined) result += node.expanded ? ' [expanded]' : ' [collapsed]';

    result += ':\n';

    // Add value if present
    if (node.value) {
        result += `${padding}  value: ${node.value}\n`;
    }

    // Recurse into children
    if (node.children && node.children.length > 0) {
        for (const child of node.children) {
            result += formatAccessibilityNode(child, indent + 1);
        }
    }

    return result;
}

/**
 * Generate a comprehensive error context file for debugging failed tests.
 * This is called automatically on test failure.
 * 
 * @param page The Playwright page instance
 * @param testInfo The test info object
 * @param errorMessage The error message from the test failure
 */
export async function generateErrorContext(
    page: Page,
    testInfo: TestInfo,
    errorMessage: string
): Promise<void> {
    const outputDir = testInfo.outputDir;
    const contextPath = path.join(outputDir, 'praxis-error-context.md');

    const lines: string[] = [
        `# Error Context: ${testInfo.title}`,
        '',
        '## Summary',
        `- **Test**: ${testInfo.titlePath.join(' › ')}`,
        `- **Status**: ${testInfo.status}`,
        `- **Duration**: ${testInfo.duration}ms`,
        `- **Retry**: ${testInfo.retry}`,
        '',
        '## Error',
        '```',
        errorMessage,
        '```',
        '',
    ];

    // Add accessibility tree
    try {
        const accessibilityTree = await captureAccessibilityTree(page);
        lines.push('## Page State (Accessibility Tree)');
        lines.push('```yaml');
        lines.push(accessibilityTree);
        lines.push('```');
        lines.push('');
    } catch (e) {
        lines.push('## Page State');
        lines.push(`[Could not capture: ${e}]`);
        lines.push('');
    }

    // Add console logs if available
    lines.push('## Console Logs');
    lines.push('_Check trace file for console logs_');
    lines.push('');

    // Add attachment references
    lines.push('## Attachments');

    const screenshots = testInfo.attachments.filter(a => a.contentType === 'image/png');
    const traces = testInfo.attachments.filter(a => a.name.includes('trace'));
    const videos = testInfo.attachments.filter(a => a.contentType === 'video/webm');

    if (screenshots.length > 0) {
        lines.push('### Screenshots');
        for (const ss of screenshots) {
            const relPath = ss.path ? path.relative(outputDir, ss.path) : ss.name;
            lines.push(`- [${ss.name}](./${relPath})`);
        }
    }

    if (traces.length > 0) {
        lines.push('### Traces');
        for (const tr of traces) {
            const relPath = tr.path ? path.relative(outputDir, tr.path) : tr.name;
            lines.push(`- [${tr.name}](./${relPath})`);
        }
    }

    if (videos.length > 0) {
        lines.push('### Videos');
        for (const vid of videos) {
            const relPath = vid.path ? path.relative(outputDir, vid.path) : vid.name;
            lines.push(`- [${vid.name}](./${relPath})`);
        }
    }

    // Write the context file
    try {
        fs.writeFileSync(contextPath, lines.join('\n'));
        console.log(`[ErrorContext] Generated: ${contextPath}`);
    } catch (e) {
        console.error(`[ErrorContext] Failed to write: ${e}`);
    }
}

/**
 * Debug helper: Print the current page's accessibility tree to console.
 * Useful during test development.
 */
export async function debugAccessibilityTree(page: Page): Promise<void> {
    const tree = await captureAccessibilityTree(page);
    console.log('\n===== ACCESSIBILITY TREE =====\n');
    console.log(tree);
    console.log('\n==============================\n');
}
