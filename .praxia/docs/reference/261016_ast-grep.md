---
title: 'AST-Grep structural search patterns'
description: ast-grep quick patterns, complex-rule syntax and metavariables, moved verbatim out of the always-on harness file.
status: active
task_id: 261016_harness-fleet-audit
date: '261016'
---

Use `ast-grep` for structural code search (superior to text grep).

### Quick Patterns

```bash
# Find signal declarations
ast-grep run --pattern 'signal<$TYPE>($INIT)' --lang typescript src/

# Find all service injections
ast-grep run --pattern 'inject($SERVICE)' --lang typescript src/

# Find console.log calls
ast-grep run --pattern 'console.log($ARG)' --lang typescript src/
```

### Complex Rules (always use `stopBy: end`)

```bash
# Find async functions containing await
ast-grep scan --inline-rules "id: async-await
language: typescript
rule:
  kind: function_declaration
  has:
    pattern: await \$EXPR
    stopBy: end" src/
```

### Debug AST Structure

```bash
ast-grep run --pattern 'class $NAME { $$$BODY }' --lang typescript --debug-query=cst
```

### Metavariables
- `$VAR` - Single named node
- `$$VAR` - Single unnamed node (operators)
- `$$$MULTI` - Zero or more nodes
