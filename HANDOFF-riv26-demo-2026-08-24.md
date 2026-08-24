# Handoff — re:Invent 2026 Interactive Demo in the staging toolbar (2026-08-24)

Adding the standalone "Amazon WorkSpaces: From Zero to Agentic" interactive demo
to the staging site's top nav, next to the Proposals button.

---

## Status at a glance

- **The feature is DONE, deployed to staging, and verified live in a browser.**
- **NOTHING IS COMMITTED.** All changes are working-tree only. HEAD is still
  `78469a0`. See [Open / next items](#open--next-items).
- **Production is untouched.** `frontend/index.html` (prod) has no reference to
  the demo; only `index-staging.html` does.
- Live at: https://staging.awseuccontent.com — click **🎬 Demo** in the top bar.
- CloudFront invalidation `I86B6XEXEUGDNQ092SYSOHPFNZ` (staging dist
  `E1IB9VDMV64CQA`) — completed.

---

## Context

The demo is a **self-contained static bundle** authored outside this repo at
`D:\Users\stetlers\Kirov2\riv26demo\demo\` (13 files, 284 KB: `index.html` +
`assets/css/{engine,theme}.css` + `assets/js/engine.js` +
`assets/js/chapters/ch1-9.js`). It has **no network calls, no absolute paths, no
build step, and no dependencies** — one namespaced `sessionStorage` key
(`riv26-demo-presenter`). The source-of-truth narrative lives in
`D:\Users\stetlers\Kirov2\riv26demo\WorkSpaces re_Invent Demo Plan.md`.

Requirement was: put it in the staging toolbar next to Proposals.

Chosen approach (decided with the user):

| Decision | Choice |
|---|---|
| How it opens | **Full-screen overlay containing an iframe** (not a new tab, not inlined) |
| Who sees it | **Everyone** — visible signed out, unlike `Proposals ▾` |
| Scope | Code **and** deploy to staging |

The demo ships its own `engine.css`/`theme.css`, which would collide with
`styles-console.css` if inlined. The **iframe is load-bearing** — it's what makes
the two stylesheets safe to coexist. Don't "simplify" it away.

---

## Completed changes

1. **Demo bundle vendored** into `frontend/riv26demo/` — copied verbatim from
   `D:\Users\stetlers\Kirov2\riv26demo\demo\`, structure preserved. Relative
   asset paths mean the directory must stay intact as a unit.

2. **`frontend/riv26-demo.js`** (new) — `Riv26Demo` class. Modeled on the
   existing `zoom-mode.js` separate-feature-file pattern; self-registers on
   `window.riv26Demo` inside `DOMContentLoaded`. Builds the overlay, wires the
   nav button, handles Restart / Close / Escape, and locks page scroll while open.
   The iframe `src` is set **on first open** so 284 KB of demo assets never cost
   the hub's initial page load.

3. **Nav button** — added statically to `index-staging.html` inside
   `header .header-right`, directly after `#proposeArticleBtn`.

4. **`frontend/styles-console.css`** — `.btn-riv26-demo` reuses the existing flat
   nav recipe (identical to `.proposals-dropdown-btn`), plus the overlay chrome
   (`.riv26-demo-container` at `z-index: 6000`, above Innovation Hub's 5000).

5. **`deploy_frontend.py`** — added `riv26-demo.js` to `FRONTEND_FILES`, and a new
   **`FRONTEND_DIRS`** mechanism that uploads directory bundles recursively,
   preserving relative paths. The script was previously **flat-file only**, so a
   nested `assets/` tree would have silently not deployed.

6. **`.kiro/steering/feature-registry.md`** — entry **#24** + a staging smoke-test
   line, following the existing Files / Verify / Dependencies convention.

### Two design calls worth preserving

- **`app-staging.js` was deliberately NOT touched.** The button is static HTML
  instead. That file is 303 KB, uniformly double-spaced with CRLF, and this repo
  has a history of a corrupt-CRLF git blob. Verified clean at the time
  (12298 CRLF, 0 CRCRLF, 0 lone CR) — but not worth the risk.
- **Button placement is not accidental.** `setupProposalsDropdown()`
  (`app-staging.js:4247`) injects `Proposals ▾` as `proposeArticleBtn.nextSibling`.
  Putting the Demo button statically *after* `#proposeArticleBtn` means the
  dropdown injects itself *between* them, so Demo lands immediately right of
  Proposals ▾ — **with no script-ordering race.** If you ever move the Demo
  button, re-check this.

### Fixed during the session

- First build duplicated the title: the overlay bar repeated the demo's own
  topbar title. Removed the redundant `.riv26-demo-title` span; the bar is now
  actions-only (`justify-content: flex-end`, height 44px) and the demo gets that
  vertical space back.

### Incidentally diagnosed (NOT bugs in this feature)

- **Stale `AWS_*` env vars shadow `~/.aws/credentials`.** `ada credentials update`
  reported success and correctly rewrote the file, yet every AWS call still
  returned `ExpiredToken` — because `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
  / `AWS_SESSION_TOKEN` are present in the environment and **win the AWS
  credential precedence chain**. They are *not* in `HKCU\Environment`, *not* in
  machine-scope registry, and *not* in any bash profile — they are **inherited
  from the process that launched Claude Code**. Fix: relaunch from a clean
  terminal. Workaround used for every AWS call this session:

      unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN

  (`AWS_REGION` is also set and is harmless.) Shell state does not persist
  between tool calls, so this must be repeated in *every* invocation, including
  `python deploy_*.py` runs — boto3 reads the same vars.

- **Working tree was already deployed.** Before deploying, the 7 unrelated
  pre-modified frontend files (`chat-widget.js`, `chat-widget.css`, `profile.js`,
  `cart-manager.js`, `cart-ui.js`, `zoom-mode.js`, `chat-widget-kb-styles.css`)
  were compared against S3 and **all matched byte-for-byte** — staging already ran
  the working tree, so the deploy was a no-op for them. Consistent with the known
  "staging/prod runs the working tree, not HEAD" behavior. The only pre-existing
  `index-staging.html` diff was chat-widget cache-buster bumps.

- A `SEVERE` console 404 for `euc-service-name-mapping.json` appears when serving
  `frontend/` from a bare local HTTP server — that file lives at the repo root
  (`ADDITIONAL_FILES`), not in `frontend/`. Not a real error; absent on the live
  site.

---

## Files changed (NOT committed — working tree only)

Modified (tracked):

```
 .kiro/steering/feature-registry.md |  9 +++-
 deploy_frontend.py                 | 49 ++++++++++++++++++++-
 frontend/index-staging.html        | 11 +++--
 frontend/styles-console.css        | 87 ++++++++++++++++++++++++++++++++++++++
 4 files changed, 151 insertions(+), 5 deletions(-)
```

New (untracked):

```
?? frontend/riv26-demo.js
?? frontend/riv26demo/            (13 files)
```

Note: `git diff` warns `LF will be replaced by CRLF` on `index-staging.html`.
That is pre-existing repo behavior, not introduced here.

---

## Deploy mechanics (how staging updates)

```bash
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN   # see above
ada credentials update --account=031421429609 --provider=isengard --role=Admin --once
cd /c/EUCContentHub
python deploy_frontend.py staging
```

- Staging bucket `aws-blog-viewer-staging-031421429609`, dist `E1IB9VDMV64CQA`.
- **Staging and production live in the SAME account** (`031421429609`;
  prod bucket is `aws-blog-viewer-031421429609`). Admin credentials there *can*
  reach prod — pass `staging` explicitly and never run the orchestrator, since
  `.deployment-config.yaml` has `auto_deploy_to_production: true`.
- `deploy_frontend.py` itself does **not** cascade; production is only reachable
  via an explicit `production` arg.
- Staging filename remap: `index.html`→`index-staging.html`,
  `app.js`→`app-staging.js`, `auth.js`→`auth-staging.js`. Files land at the
  bucket **root**; `FRONTEND_DIRS` bundles keep their subpath.
- **Cache-busting is mandatory.** Current tag is `?v=20260821-riv26demo` on
  `styles-console.css` and `riv26-demo.js`. Bump it on any further edit to those,
  or browsers serve stale files.

### Verification performed (all passing on the live site)

- Toolbar order: `💡 Innovation Hub · 🌙 · ✍️ Propose Article · [Proposals ▾,
  hidden when signed out] · 🎬 Demo · 🔐 Sign In`
- All 13 bundle assets return **200** with correct content types.
- Overlay activates at `z-index: 6000`; iframe `src` is `null` before first click
  (lazy load confirmed), then `riv26demo/index.html`.
- Inside the iframe: correct `<title>`, `<h1>`, 3 Act cards; clicking **Next**
  advances to "Chapter 1 · Why Virtual Desktops?" (progress 2%) — engine runs.
- Close and Escape both dismiss and restore page scroll.
- **0 SEVERE console entries** on the live site.

---

## Open / next items

1. **Commit the work — nothing is committed.** HEAD is `78469a0`. Suggested:
   stage only this feature's files, since the tree has unrelated pre-existing
   modifications that were deliberately left alone (see
   `HANDOFF-staging-ui-2026-07-30.md` lines 127-129):

   ```bash
   cd /c/EUCContentHub
   git add frontend/riv26-demo.js frontend/riv26demo/ \
           frontend/index-staging.html frontend/styles-console.css \
           deploy_frontend.py .kiro/steering/feature-registry.md \
           HANDOFF-riv26-demo-2026-08-24.md
   git commit -m "Add re:Invent 2026 interactive demo to staging toolbar"
   ```

   Beware: `frontend/index-staging.html` also carries unrelated chat-widget
   cache-buster bumps, which this commit would sweep in. Also note commit
   `66fe89f` may still be local-only and unpushed per the earlier handoff.

2. **Relaunch Claude Code / your terminal from a clean shell** to drop the stale
   inherited `AWS_*` env vars, so `ada` refreshes actually take effect.

3. **Decide whether this ships to production.** Currently staging-only. To
   promote, the button + script tag must be added to `frontend/index.html` and
   the styles to `styles-refined.css` (prod theme), then
   `python deploy_frontend.py production`. **Not done, not requested.**

4. **Source-of-truth question.** `frontend/riv26demo/` is a *vendored copy* of
   `D:\Users\stetlers\Kirov2\riv26demo\demo\`. There is no sync mechanism — edits
   to either diverge silently. Decide whether this repo now owns the demo, or add
   a refresh step.

5. Optional polish: the demo captures arrow keys inside the iframe, so parent
   Escape only fires when focus is outside it. A same-origin `keydown` listener is
   attached to the iframe document on load (`bindFrameEscape`) to cover this, in a
   try/catch. If the bundle is ever served cross-origin, that silently degrades to
   the Close button only.
