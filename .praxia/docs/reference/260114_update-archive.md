# Update Archive Workflow

**Trigger**: When `.agent/archive/` becomes cluttered with loose folders (e.g., `prompts/`, `summaries/`, `backlog/`) that are no longer active.
**Goal**: Merge these loose folders into `archive.tar.gz` and update the manifest.

---

## Agent Instructions

Follow these steps to update the archive.

### 1. Setup

Initialize a temporary workspace.

```bash
# Create a temp directory for unpacking
mkdir -p .agent/archive/.temp_pack
```

### 2. Unpack Existing Archive

If `archive.tar.gz` exists, unpack it.

```bash
if [ -f .agent/archive/archive.tar.gz ]; then
  tar -xzf .agent/archive/archive.tar.gz -C .agent/archive/.temp_pack
  echo "Unpacked existing archive."
else
  echo "No existing archive found. Starting fresh."
fi
```

### 3. Merge Content

**Strategy**: We are performing a **flat merge** of the current loose folders into the existing archive structure. **Avoid nesting** (e.g., do not end up with `prompts/prompts/`).

1. **Prepare target directories** in the temp pack.

    ```bash
    mkdir -p .agent/archive/.temp_pack/prompts
    mkdir -p .agent/archive/.temp_pack/summaries
    mkdir -p .agent/archive/.temp_pack/backlog
    mkdir -p .agent/archive/.temp_pack/artifacts
    ```

2. **Move candidate directories** into the temp location using `rsync` with trailing slashes to ensure only contents are merged.

**Candidates to archive**:

- `.agent/archive/prompts`
- `.agent/archive/summaries`
- `.agent/archive/backlog`
- `.agent/archive/artifacts`
- *(Add any other dated or completed folders found in .agent/archive)*

**Exclusions**:

- `archive.tar.gz`, `README.md`, `UPDATE_ARCHIVE.md`, `COMPRESSED_ARCHIVE.md`, `.temp_pack`

**Command Template**:
For each candidate directory (e.g., `prompts`):

```bash
# Example for 'prompts'
if [ -d .agent/archive/prompts ]; then
  # Sync CONTENTS to temp/prompts. 
  # Note the trailing slashes: they ensure we merge contents and avoid nesting.
  rsync -av .agent/archive/prompts/ .agent/archive/.temp_pack/prompts/
  # Remove the source directory after successful sync
  rm -rf .agent/archive/prompts
  echo "Archived prompts."
fi
```

*Repeat this logic for all candidates.*

### 4. Optimize and Index

1. **Generate Tree**: Run `tree` or `ls -R` on `.agent/archive/.temp_pack` to analyze contents.
2. **Update Manifest**: Write a summary to `.agent/archive/COMPRESSED_ARCHIVE.md`.
    - List top-level directories.
    - Note the range of dates or prompt IDs (e.g., "Contains prompts from 260101 to 260115").
    - Append a log entry with today's date and what was added.

### 5. Repack and Cleanup

Compress the consolidated content back to the tarball.

```bash
# Compress
tar -czf .agent/archive/archive.tar.gz -C .agent/archive/.temp_pack .

# Cleanup temp
rm -rf .agent/archive/.temp_pack

# Report
ls -lh .agent/archive/archive.tar.gz
```

### 6. Validation

- Verify `archive.tar.gz` is non-empty.
- Verify `COMPRESSED_ARCHIVE.md` is updated.
- Verify loose folders are gone.
