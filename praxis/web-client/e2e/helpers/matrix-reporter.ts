/**
 * Matrix Reporter Utilities
 *
 * Helper functions for categorizing and reporting protocol simulation test failures.
 * Used by protocol-simulation-matrix.spec.ts for failure analysis.
 */

/**
 * Result of a single protocol matrix test
 */
export interface MatrixResult {
    /** Protocol accession_id */
    protocolId: string;
    /** Test outcome */
    status: 'passed' | 'failed' | 'skipped';
    /** Categorized failure type (if failed) */
    failureCategory?: 'protocol_bug' | 'app_bug' | 'timeout' | 'setup_error' | 'unknown';
    /** Error message (if failed) */
    errorMessage?: string;
    /** Test duration in milliseconds */
    duration: number;
}

/**
 * Categorize a test failure based on error message patterns.
 *
 * Categories:
 * - protocol_bug: Python errors in protocol execution (Traceback, NameError, etc.)
 * - app_bug: Playwright selector/locator failures
 * - timeout: Execution timeout
 * - setup_error: Navigation or database setup issues
 * - unknown: Uncategorized failure
 */
export function categorizeFailure(errorMessage: string): MatrixResult['failureCategory'] {
    const msg = errorMessage.toLowerCase();

    // Python/protocol errors
    if (
        msg.includes('traceback') ||
        msg.includes('nameerror') ||
        msg.includes('typeerror') ||
        msg.includes('indexerror') ||
        msg.includes('keyerror') ||
        msg.includes('attributeerror') ||
        msg.includes('valueerror') ||
        msg.includes('syntaxerror') ||
        msg.includes('python') ||
        msg.includes('pyodide')
    ) {
        return 'protocol_bug';
    }

    // Timeout
    if (msg.includes('timeout') || msg.includes('timed out') || msg.includes('exceeded')) {
        return 'timeout';
    }

    // Playwright/selector errors
    if (
        msg.includes('locator') ||
        msg.includes('selector') ||
        msg.includes('element') ||
        msg.includes('visible') ||
        msg.includes('clickable') ||
        msg.includes('expect(')
    ) {
        return 'app_bug';
    }

    // Setup/navigation errors
    if (
        msg.includes('navigation') ||
        msg.includes('page.goto') ||
        msg.includes('database') ||
        msg.includes('sqlite') ||
        msg.includes('opfs')
    ) {
        return 'setup_error';
    }

    return 'unknown';
}

/**
 * Format matrix results as a markdown summary
 */
export function formatMatrixSummary(results: MatrixResult[]): string {
    const passed = results.filter((r) => r.status === 'passed');
    const failed = results.filter((r) => r.status === 'failed');
    const skipped = results.filter((r) => r.status === 'skipped');

    const protocolBugs = failed.filter((r) => r.failureCategory === 'protocol_bug');
    const appBugs = failed.filter((r) => r.failureCategory === 'app_bug');
    const timeouts = failed.filter((r) => r.failureCategory === 'timeout');
    const setupErrors = failed.filter((r) => r.failureCategory === 'setup_error');
    const unknown = failed.filter((r) => r.failureCategory === 'unknown');

    let output = `# Protocol Simulation Matrix Results\n\n`;
    output += `## Summary\n`;
    output += `- **Total**: ${results.length} protocols\n`;
    output += `- **Passed**: ${passed.length}\n`;
    output += `- **Failed (Protocol Bug)**: ${protocolBugs.length}\n`;
    output += `- **Failed (App Bug)**: ${appBugs.length}\n`;
    output += `- **Failed (Timeout)**: ${timeouts.length}\n`;
    output += `- **Failed (Setup Error)**: ${setupErrors.length}\n`;
    if (unknown.length > 0) {
        output += `- **Failed (Unknown)**: ${unknown.length}\n`;
    }
    output += `- **Skipped**: ${skipped.length}\n`;

    if (protocolBugs.length > 0) {
        output += `\n## Protocol Bugs (to fix in protocol definitions)\n`;
        for (const r of protocolBugs) {
            output += `- \`${r.protocolId}\`: ${r.errorMessage?.slice(0, 100) ?? 'Unknown error'}\n`;
        }
    }

    if (appBugs.length > 0) {
        output += `\n## Application Bugs (to fix in execution logic)\n`;
        for (const r of appBugs) {
            output += `- \`${r.protocolId}\`: ${r.errorMessage?.slice(0, 100) ?? 'Unknown error'}\n`;
        }
    }

    if (timeouts.length > 0) {
        output += `\n## Timeouts (need investigation)\n`;
        for (const r of timeouts) {
            output += `- \`${r.protocolId}\`: ${r.errorMessage?.slice(0, 100) ?? 'Timed out'}\n`;
        }
    }

    if (setupErrors.length > 0) {
        output += `\n## Setup Errors (infrastructure issues)\n`;
        for (const r of setupErrors) {
            output += `- \`${r.protocolId}\`: ${r.errorMessage?.slice(0, 100) ?? 'Setup failed'}\n`;
        }
    }

    if (skipped.length > 0) {
        output += `\n## Skipped (require real hardware)\n`;
        for (const r of skipped) {
            output += `- \`${r.protocolId}\`\n`;
        }
    }

    return output;
}
