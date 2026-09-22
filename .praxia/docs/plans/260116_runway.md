# 🛫 Launch Runway: Project "Praxis"

**Target**: `maraxen.github.io/praxis`
**Method**: Rename Repository `pylabpraxis` -> `praxis`

---

## Phase 1: Pre-Flight Checks (Local)

- [ ] **Commit & Merge**
  - [ ] Review pending changes in `web-client` (Bug fixes, tech debt).
  - [ ] Ensure `main` branch passes all tests (`make test-fast`, `npm run test`).
  - [ ] Merge all feature branches into `main`.

- [ ] **Repository Hygiene**
  - [ ] Archive stale branches:

      ```bash
      git branch --merged | grep -v "\*" | grep -v "main" | xargs -n 1 git branch -d
      ```

  - [ ] Delete remote stale branches.
  - [ ] Verify `.gitignore` is clean.

- [ ] **Configuration Verification**
  - [ ] Verify `praxis/web-client/angular.json` has `baseHref` set to `/praxis/` for `gh-pages`.
  - [ ] Verify `environment.gh-pages.ts` has `production: true` (optional but recommended) and correct API settings for browser mode.
  - [ ] Check `.github/workflows/deploy.yml` exists and is configured to build `main`.

---

## Phase 1.5: Hardware Verification

- [ ] **Physical Hardware Checks**
    - [ ] Test on physical robot (if available).
    - [ ] Verify Serial/USB connectivity.

---

## Phase 2: The Rename (GitHub)

> ⚠️ **Warning**: This action will change the remote URL.

1. Go to **Settings** > **General** on GitHub.
2. Change Repository Name from **`pylabpraxis`** to **`praxis`**.
3. Confirm the rename.

---

## Phase 3: Alignment (Local)

- [ ] **Update Local Remote**

    ```bash
    git remote set-url origin https://github.com/maraxen/praxis.git
    git remote -v # Verify
    ```

- [ ] **Update Documentation References**
  - [ ] Grep for `pylabpraxis` and replace with `praxis` in `README.md`, `pyproject.toml`, `mkdocs.yml`, etc.
  - [ ] `git commit -am "chore: rename references to praxis"`

- [ ] **Documentation Review**
  - [ ] Review all docs for broken links.
  - [ ] Verify screenshots match the new UI (post-polish).

---

## Phase 4: Ignition (Deployment)

- [ ] **Trigger Deployment**

    ```bash
    git push origin main
    ```

- [ ] **Monitor Actions**
  - Watch the "Deploy to GitHub Pages" workflow in the Actions tab.
  - Verify `gh-pages` branch is updated.

- [ ] **Verify Live Site**
  - Go to: [https://maraxen.github.io/praxis](https://maraxen.github.io/praxis)
  - Check:
    - [ ] Browser Mode loads without 404s.
    - [ ] Assets (images, fonts) load correctly.
    - [ ] Routing (deep links) works (via 404 hack).
    - [ ] Documentation is accessible at `/praxis/docs/`.

---

## Phase 5: Announcement

- [ ] **Prepare Post**
  - Title: "Introducing Praxis: Browser-based Lab Automation"
  - Link: `https://maraxen.github.io/praxis`
- [ ] **Publish** to Discourse / Socials.
