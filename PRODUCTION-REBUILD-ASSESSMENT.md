# Production Rebuild Assessment

**Purpose:** Translate the current EUC/Amazon WorkSpaces Community Hub (built imperatively in a personal AWS account) into a clean, AWS-security-reviewable production application in a fresh production account.

**Audience:** The engineer(s) doing the rebuild, and AWS security reviewers.

**Status:** Planning artifact — not the implementation. Authored 2026-06-26 from an audit of the repo.

---

## 1. Executive summary

The GitHub repo (`https://github.com/stetlers/euccontenthub`) contains all **application source**, but it is **not a turnkey rebuild package**. The system was stood up imperatively via boto3 scripts and manual console steps; there is **zero Infrastructure-as-Code**, account-specific identifiers are **hardcoded across ~118 files**, and the repo carries hundreds of one-off throwaway scripts mixed in with the load-bearing ones.

The production effort is therefore a **re-platforming, not a lift-and-shift**:

1. Author the infrastructure as **CDK** (AWS security requirement).
2. **Parameterize** every account/region/resource-specific value.
3. Replace **Google OAuth** federation with **AWS Builder ID**.
4. **Curate** a clean repo (app source + CDK + docs) for review on **GitLab** (`gitlab.aws.dev`), not a mirror of the messy GitHub repo.

Good news up front: [`INFRASTRUCTURE.md`](./INFRASTRUCTURE.md) already enumerates nearly every resource and its config — it is the single best translation spec for the CDK app (with the caveats in §6).

---

## 2. Target architecture (from INFRASTRUCTURE.md, confirmed against code)

Two environments (staging + prod), same shape:

| Layer | Resource (current prod names) | Notes |
|---|---|---|
| CDN | CloudFront `E20CC1TSSWTCWN` (prod), `E1IB9VDMV64CQA` (staging) | → CDK distribution; IDs become outputs, stop being hardcoded |
| Static hosting | S3 `aws-blog-viewer-031421429609` (prod), `aws-blog-viewer-staging-031421429609` (staging) | Bucket-name → CDK construct + env suffix |
| API | API Gateway REST (`xox05733ce`), stages `/prod` `/staging` | Lambda proxy integration |
| Compute | 5 Lambdas: `aws-blog-api`, `aws-blog-crawler`, `aws-blog-summary-generator`, `aws-blog-classifier`, `aws-blog-chat` | Python 3.11; see source in repo root |
| Data | DynamoDB: `aws-blog-posts`, `euc-user-profiles` (+ `-staging`) | PAY_PER_REQUEST; enable PITR in prod |
| Auth | Cognito User Pool `us-east-1_MOvNrTnua`, client `3pv5jf235vj14gu148b9vjt3od` | **Swap Google IdP → Builder ID** (§5) |
| AI | Bedrock (Claude models) + Bedrock Agent | Model access is a manual prereq |
| Crawler (heavy) | ECS/Fargate cluster `euc-content-hub-cluster`, ECR `builder-selenium-crawler` | Selenium crawler; see `Dockerfile.selenium`, `ecs_selenium_crawler.py` |
| Edge/DNS | ACM cert + Route53 for `awseuccontent.com` | New domain needed for prod account |

Async pipeline wiring (must be preserved in CDK as Lambda invoke perms / triggers): **crawler → summary generator (10/batch) → classifier (50/batch)**.

---

## 3. Load-bearing vs. throwaway (what carries over)

The repo root has hundreds of `check_*.py`, `fix_*.py`, `diagnose_*.py`, `test_*.py`, `*-complete.md`, `response*.json` files. **These do NOT carry over.** They are session scratch from the original build.

**Application source that DOES carry over** (becomes the prod app):

- **Frontend:** `frontend/` — `app.js`, `auth.js`, `profile.js`, `cart-*.js`, `chat-widget*.js`, `kb-editor*.js`, `styles-refined.css`, `index.html` (+ staging variants). *(Note: staging variants are a workaround for the lack of build-time config — see §4.)*
- **Lambdas:** `lambda_api/` + root `enhanced_crawler_lambda.py`, `summary_lambda.py`, `classifier_lambda.py`, `chat_lambda*.py`, `ecs_selenium_crawler.py`, `builder_selenium_crawler.py`.
- **Containers:** `Dockerfile.ecs`, `Dockerfile.selenium`, `buildspec.yml`.
- **MCP:** `mcp/euc-content-hub-mcp/` (already on GitLab).
- **IAM policy JSON** (as a reference for least-privilege CDK policies — do not copy the broad `*FullAccess` grants; see §7).
- **Docs:** `INFRASTRUCTURE.md`, `DEPLOYMENT.md`, this file.

**Reference-only (read, then re-derive in CDK — do not run):** `setup_*.py`, `deploy_*.py`, `configure_*.py`. They encode the resource shapes but are imperative and account-bound.

> ⚠️ `INFRASTRUCTURE.md` references several deploy scripts that **do not exist** in the repo (`deploy_frontend_complete.py`, `rollback_api_lambda.py`, `redeploy_selenium_crawler.py`, `trigger_crawler.py`). The real frontend deploy script is `deploy_frontend.py`. Treat the doc's resource definitions as authoritative but its script names as stale.

---

## 4. Hardcoded values to parameterize

Account ID `031421429609` appears in **118 tracked files**; CloudFront distro IDs in **56**; Cognito refs in **11**. Most evaporate when the throwaway scripts are dropped, but these **load-bearing** spots must become CDK context / build-time config:

| Value | Where (load-bearing) | Target |
|---|---|---|
| AWS account ID `031421429609` | IAM role ARNs, ECR URIs, bucket names | CDK env / `Stack` account |
| Region `us-east-1` | everywhere | CDK env / context |
| API endpoint `https://xox05733ce.execute-api…` | `frontend/app.js:5-9`, `app-staging.js:3` | Build-time inject (CDK output → frontend config) |
| Cognito pool `us-east-1_MOvNrTnua` | `frontend/auth.js:11` | Build-time inject |
| Cognito client `3pv5jf235vj14gu148b9vjt3od` | `frontend/auth.js:12` | Build-time inject |
| Bucket names `aws-blog-viewer-*` | `deploy_frontend.py:20-28` | CDK construct + env suffix |
| CloudFront IDs `E20CC1TSSWTCWN` / `E1IB9VDMV64CQA` | `deploy_frontend.py`, INFRASTRUCTURE.md | CDK output (never hardcode) |
| Domain `awseuccontent.com` | auth callbacks, CF aliases | CDK context per env |

**Key cleanup:** the existence of `*-staging.js`/`index-staging.html` duplicate files is itself a smell — it exists *because* config is hardcoded per-environment. With build-time config injection (one source, env-parameterized), the staging duplicates collapse into a single codebase.

---

## 5. Auth change: Google OAuth → AWS Builder ID

Current: Cognito User Pool with **Google** as a federated IdP (`INFRASTRUCTURE.md` §7, `--supported-identity-providers COGNITO Google`).

Production: **AWS Builder ID** instead of Google.

- Keep the Cognito User Pool architecture; replace the `Google` identity provider with Builder ID federation.
- **Removes** the out-of-band Google Cloud Console dependency (one fewer non-reproducible manual step).
- **Open design question:** federate Builder ID *through* Cognito (OIDC provider) vs. talk to it directly — this changes the CDK auth constructs and the frontend `auth.js` flow. Resolve before building the auth stack.
- Frontend `auth.js` hardcoded pool/client IDs (§4) get injected at build time regardless.

---

## 6. External / manual prerequisites (not reproducible from code)

These are **not** in git and **cannot** be fully codified — document them as explicit prereqs for the new account:

1. **Bedrock model access** — request access to the Claude models the app uses (approval can take hours). The Bedrock **Agent** instructions live in `bedrock-agent-instruction.txt`; the agent/alias itself is created against live AWS.
2. **ACM certificate + DNS** — request/validate a cert and create Route53 records for the prod domain. New domain likely needed (current `awseuccontent.com` is in the personal account).
3. **OpenSearch / Knowledge Base ingestion** — chat/KB features depend on a vector store + ingestion setup.
4. **Initial data** — crawled content lives only in DynamoDB, not git. A fresh account starts empty and must run the crawler → summary → classify pipeline to populate.
5. **Builder ID app registration** — depending on the §5 design decision.

---

## 7. AWS security review readiness (gaps to close)

The current setup will not pass review as-is. Known issues to fix during the CDK rebuild:

- **Over-broad IAM.** INFRASTRUCTURE.md attaches `AmazonDynamoDBFullAccess` and `AmazonBedrockFullAccess` to one shared Lambda role. Replace with **per-function least-privilege** policies scoped to specific tables/models.
- **Public S3 bucket policy.** Current frontend bucket uses a public `s3:GetObject` policy. Use **CloudFront OAC (Origin Access Control)** with a private bucket instead.
- **Single shared Lambda role** across all 5 functions → split per function.
- **Secrets handling.** Move any secrets to **Secrets Manager / Parameter Store** (already gitignored locally, but make it explicit in CDK).
- **Logging/monitoring.** CloudTrail, GuardDuty, log retention, and alarms (INFRASTRUCTURE.md §Monitoring lists these as "to do" — make them CDK constructs, not optional).

---

## 8. Repo / review logistics (GitLab)

Target review home: **`gitlab.aws.dev`** (same place as the MCP repo).

Pushing there already works (the MCP was pushed 2026-06-24). Known gotchas (none are blockers):

- Commit author must be **`stetlers@amazon.com`** (GitLab rejects GitHub noreply addresses → `pre-receive hook declined`).
- **`main` is a protected branch** — push a new branch and set it as default in the UI; don't force-push `main`.
- Run the push from a **real terminal** (`Start-Process powershell …`) so SSH can prompt for the `id_rsa` passphrase (the disabled `ssh-agent` service is not a blocker — it just means re-typing the passphrase per push).

**Recommendation:** create the GitLab repo fresh with only the curated, CDK-based codebase — do **not** mirror the current GitHub repo with its hundreds of scratch files.

---

## 9. Suggested phased plan

1. **Resolve open design questions** — Builder ID federation approach (§5); confirm prod domain.
2. **Scaffold CDK app** (TypeScript recommended for AWS-internal familiarity) — one stack per concern (data, auth, api, compute, crawler, edge) parameterized by env.
3. **Translate resources** from INFRASTRUCTURE.md §1–8 into CDK constructs, closing the §7 security gaps as you go.
4. **Build-time frontend config injection** — collapse the staging/prod duplicate files (§4).
5. **Containers** — port `Dockerfile.selenium` + ECS task into CDK (`aws-ecs` constructs / CodeBuild).
6. **Curate + push** the clean repo to GitLab (§8) for AWS security review.
7. **Stand up + populate** the new account; run the crawler pipeline; validate.

---

*This is a living document. Update as design questions resolve.*
