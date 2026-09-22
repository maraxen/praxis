# Development Notes

Lessons learned, gotchas, and specialized knowledge discovered during Praxis development.

> **Purpose**: Capture individual insights as they're discovered. Periodically distill patterns into [codestyles/](codestyles/) guides.

---

## How to Use

Add entries as you encounter notable patterns:

```markdown
## [Short Title]

**Date:** YYYY-MM-DD
**Area:** Backend | Frontend | REPL | Hardware

[Description of the lesson learned or gotcha]

**Files:** `path/to/relevant/file.ts`
```

---

## Entries

### SQLAlchemy Dataclass ORM Mapping

**Date:** 2026-01-06
**Area:** Backend - Testing

When using SQLAlchemy's dataclass-style ORM mapping, fields with defaults must use `kw_only=True` if they appear after non-default fields. Factory Boy's `SubFactory` doesn't automatically flush dependencies before creating the dependent ORM instance.

**Files:** `tests/factories.py`, `praxis/backend/models/orm/outputs.py`

---

### Angular Signal Inputs in Tests

**Date:** 2026-01-07
**Area:** Frontend - Testing

Angular's signal-based `input()` properties require special handling in unit tests. Use `fixture.componentRef.setInput('propertyName', value)` instead of direct assignment, and call `fixture.detectChanges()` afterward.

**Files:** `praxis/web-client/src/app/features/*/components/*/*.spec.ts`

---

### FTDI USB Status Bytes

**Date:** 2026-01-07
**Area:** Hardware - Drivers

FTDI chips prepend 2 status bytes to every 64-byte chunk of data. These must be stripped in the driver layer before passing data upstream. The standard WebSerial API doesn't handle this—use the custom `FtdiSerialDriver`.

**Files:** `praxis/web-client/src/app/features/repl/drivers/ftdi-web-serial.ts`

---

### JupyterLite Pyodide Environment Init

**Date:** 2026-01-06
**Area:** REPL

PyLabRobot module imports fail until `sys.path` is explicitly configured in the Pyodide worker. Run environment initialization code before any PLR imports.

**Files:** `praxis/web-client/src/app/features/repl/components/jupyterlite-repl/`

---
---

### Breadcrumb Removal

**Date:** 2026-01-14
**Area:** Frontend - UI

The global breadcrumb bar was removed from the unified shell as it served no purpose and added visual clutter. The `BreadcrumbService` and `BreadcrumbComponent` were also deleted.

**Files:** `praxis/web-client/src/app/layout/unified-shell.component.ts`, `praxis/web-client/src/app/core/components/breadcrumb/`, `praxis/web-client/src/app/core/services/breadcrumb.service.ts`

---

### SharedArrayBuffer & COOP/COEP Headers

**Date:** 2026-01-22
**Area:** Frontend - Browser Mode

Pyodide requires `SharedArrayBuffer` for multi-threading. Modern browsers disable this unless `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` headers are set. These headers have been added to the Angular dev server in `angular.json`. For production, the web server must be configured to send these headers.

**Files:** `praxis/web-client/angular.json`, `.agent/docs/known_issues/shared_array_buffer.md`

## User provided notes

git ls-files -- . ':!:*.json' ':!:*.png' ':!:*.bak' ':!:*.db' ':!:*.sql' | xargs wc -l | sort -gr | head -n 20 allows us to find the longest files in the repo
