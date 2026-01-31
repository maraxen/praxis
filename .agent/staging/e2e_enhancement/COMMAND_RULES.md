# MANDATORY COMMAND EXECUTION RULES

**EVERY terminal command MUST use `WaitMsBeforeAsync: 500`** to ensure background execution.

## Pattern

```typescript
run_command({
  CommandLine: "<cmd> > /tmp/<name>.log 2>&1",
  Cwd: "<path>",
  SafeToAutoRun: true/false,
  WaitMsBeforeAsync: 500  // ALWAYS 500ms - sends to background
})
```

## Check Results

Use `command_status` with the returned command ID, then `view_file` on logs:

```typescript
command_status({ CommandId: "<id>", WaitDurationSeconds: 10, OutputCharacterCount: 500 })
view_file({ AbsolutePath: "/tmp/<name>.log" })
```

## NEVER

- Use `WaitMsBeforeAsync > 1000` for any command
- Omit the log file redirect
- Forget to check command status before assuming completion
