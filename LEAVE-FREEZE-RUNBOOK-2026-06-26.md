# Crawler Freeze Runbook — Owner Leave (effective 2026-06-26)

**Why:** The repo owner is on unpaid leave starting Mon 2026-06-29 with no access to the
corporate device. The content crawlers have caused production data incidents before
(SPA-shell title poisoning; Selenium Chrome crashes), so all autonomous and manual
crawling was frozen to prevent unattended data corruption. The **serving stack is
untouched** — the site, reads, auth, chat, and voting all keep working. Only **content
ingestion** is paused (no new posts during leave).

Account: `031421429609`  Region: `us-east-1`

---

## Why both layers were needed

Two independent paths trigger the crawlers:

1. **Scheduled** — EventBridge rules fire the crawler Lambdas / ECS on a timer.
2. **Manual** — the "Refresh Posts" button → `POST /crawl` → API Lambda `trigger_crawler()`
   → **invokes `aws-blog-crawler` directly**, bypassing EventBridge.

Disabling schedules alone leaves the manual button live. So a defense-in-depth freeze was
applied: disable the schedules **and** set reserved concurrency=0 on the crawler Lambdas
(the chokepoint both paths funnel through). With concurrency=0 every invocation is
throttled and never executes — the button still returns its 202 "started" message, but
nothing runs and nothing is written to DynamoDB.

---

## What was changed (2026-06-26)

### A. EventBridge rules disabled (`aws events disable-rule`)
| Rule | Schedule | Target |
|---|---|---|
| `builder-selenium-weekly-crawl` | Sun 2 AM UTC | ECS selenium-crawler-cluster |
| `euc-daily-backfill-schedule` | daily 6 AM UTC | `euc-daily-backfill` Lambda → SQS |
| `whats-new-crawler-daily-production` | rate(1 day) | `aws-whats-new-crawler` Lambda |
| `whats-new-crawler-daily-staging` | rate(1 day) | `aws-whats-new-crawler` Lambda |

(`aws-blog-crawler-schedule`, rate(7 days), was **already DISABLED** before the freeze —
leave it as-is unless you know it should be on.)

### B. Lambda reserved concurrency set to 0 (`aws lambda put-function-concurrency`)
`aws-blog-crawler`, `aws-whats-new-crawler`, `euc-daily-backfill`

**Pre-freeze state (for exact rollback):** none of these had reserved concurrency
configured — they used the default unreserved pool. So the correct restore is to **delete**
the concurrency setting, NOT set it to some number.

### C. NOT touched
- `aws-blog-api` (the serving/API Lambda) — left at default. Do not change.
- Any non-app rules: `DO-NOT-DELETE-GatedGarden-*`, `SSMOpsItems-*`, `WorkSpaces*`,
  `Daily_WksImageCopy`, `WorkSpacesCostOptimizer-*`, etc. These are account/org
  infrastructure, NOT this app.

---

## How to RE-ENABLE on return (or if a teammate must, with appropriate creds)

```powershell
# 1. Re-enable the schedules
foreach ($r in 'builder-selenium-weekly-crawl','euc-daily-backfill-schedule','whats-new-crawler-daily-production','whats-new-crawler-daily-staging') {
    aws events enable-rule --name $r --region us-east-1
}

# 2. Remove the concurrency kill switch (restores original unreserved behavior)
foreach ($fn in 'aws-blog-crawler','aws-whats-new-crawler','euc-daily-backfill') {
    aws lambda delete-function-concurrency --function-name $fn --region us-east-1
}
```

### Verify after re-enabling
```powershell
# Schedules should read ENABLED
foreach ($r in 'builder-selenium-weekly-crawl','euc-daily-backfill-schedule','whats-new-crawler-daily-production','whats-new-crawler-daily-staging') {
    "{0,-45} {1}" -f $r, (aws events describe-rule --name $r --region us-east-1 --query State --output text)
}
# Concurrency should read None for all three
foreach ($fn in 'aws-blog-crawler','aws-whats-new-crawler','euc-daily-backfill') {
    "{0,-25} {1}" -f $fn, (aws lambda get-function-concurrency --function-name $fn --region us-east-1 --query ReservedConcurrentExecutions --output text)
}
```

---

## Verified frozen state as of 2026-06-26
- All 4 EUC schedules: **DISABLED** (plus aws-blog-crawler-schedule already disabled)
- aws-blog-crawler / aws-whats-new-crawler / euc-daily-backfill reserved concurrency: **0**
- aws-blog-api reserved concurrency: **None** (unchanged — serving stack healthy)
