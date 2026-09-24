---
title: 'Dependency Audit Report'
---

# Dependency Audit Report

## Frontend Dependencies

### Outdated Dependencies

The following frontend packages are outdated and should be updated to their latest versions:

| Package | Current | Wanted | Latest |
|---|---|---|---|
| @angular/animations | 21.0.3 | 21.1.0 | 21.1.0 |
| @angular/build | 21.0.2 | 21.1.0 | 21.1.0 |
| @angular/cdk | 21.0.2 | 21.1.0 | 21.1.0 |
| @angular/cli | 21.0.2 | 21.1.0 | 21.1.0 |
| @angular/common | 21.0.3 | 21.1.0 | 21.1.0 |
| @angular/compiler | 21.0.3 | 21.1.0 | 21.1.0 |
| @angular/compiler-cli | 21.0.3 | 21.1.0 | 21.1.0 |
| @angular/core | 21.0.3 | 21.1.0 | 21.1.0 |
| @angular/forms | 21.0.3 | 21.1.0 | 21.1.0 |
| @angular/material | 21.0.2 | 21.1.0 | 21.1.0 |
| @angular/platform-browser | 21.0.3 | 21.1.0 | 21.1.0 |
| @angular/router | 21.0.3 | 21.1.0 | 21.1.0 |
| @ngrx/signals | 20.1.0 | 20.1.0 | 21.0.1 |
| jsdom | 27.3.0 | 27.4.0 | 27.4.0 |
| vitest | 4.0.15 | 4.0.17 | 4.0.17 |

### Security Issues

The `npm audit` reported 8 vulnerabilities (2 low, 6 high). The high severity vulnerabilities are in `@angular/animations`, `@angular/cli`.

### Unused Dependencies

Based on a review of `package.json`, there are no obviously unused dependencies.

## Python Dependencies

### Security Issues

The `uv pip audit` (via `pip-audit`) reported no known vulnerabilities.

### Unused Dependencies

A full dependency analysis was not performed, but a review of `pyproject.toml` did not reveal any obviously unused dependencies.

## Build Issues

The frontend build (`npm run build`) completed successfully but produced the following warning:
- `bundle initial exceeded maximum budget. Budget 500.00 kB was not met by 261.15 kB with a total of 761.15 kB.`

## Fix Priority

1.  **High:** Address the high-severity security vulnerabilities in the frontend dependencies (`@angular/animations`, `@angular/cli`).
2.  **Medium:** Update all outdated frontend dependencies to their latest versions.
3.  **Low:** Investigate the bundle size warning and consider options for optimization.

