/* ============================================================
   Amazon WorkSpaces: From Zero to Agentic — re:Invent 2026 demo
   ch7.js — Chapter 7: Enhanced CloudWatch Metrics for
   Troubleshooting (Act 3)

   Classic script. Calls DEMO.registerChapter() at parse time and
   nothing else; screen functions run only when the engine renders
   them inside the 1600x900 stage canvas. Every rule in `styles`
   is prefixed with .ch7 per the engine contract.

   Story: Martha Major (mmajor, WorkSpace ws-9x7demo12) files
   ticket #48291 at 2:14 PM — "my desktop is slow." The enhanced
   AWS/WorkSpaces CloudWatch metrics show exactly why: a latency
   spike starting 2:04 PM, pegged CPU, a storage bottleneck, and
   reconnect churn — and an alarm that paged ops at 2:09 PM,
   five minutes before the ticket was even opened.
   ============================================================ */

(function () {
  "use strict";

  var REGION = "US West (Oregon) us-west-2";
  var WS_ID = "ws-9x7demo12";
  var HOURS = ["12 PM", "1 PM", "2 PM", "3 PM", "4 PM"];
  var BLUE = "#0073bb", ORANGE = "#ec7211", GREEN = "#1d8102", RED = "#d13212";
  var BC_METRICS = "CloudWatch &rsaquo; Metrics &rsaquo; AWS/WorkSpaces &rsaquo; " + WS_ID;

  /* ---------------------------------------------------------- */
  /* Shared builders (run at render time only)                    */
  /* ---------------------------------------------------------- */

  function nav(active) {
    return ["Dashboards", "Alarms", "Metrics", "Logs", "Insights"].map(function (label) {
      return label === active ? { label: label, active: true } : label;
    });
  }

  function cw(active, breadcrumbs, inner) {
    return DEMO.frames.consoleFrame(
      { service: "CloudWatch", region: REGION, sidenav: nav(active), breadcrumbs: breadcrumbs },
      inner
    );
  }

  function leg(color, label) {
    return '<span><span class="legend-swatch" style="background:' + color + '"></span>' + label + "</span>";
  }

  /** chart-card shell. o: { title, sub, body, legend, foot, cls, hotspot, badge } */
  function chartCard(o) {
    return (
      '<div class="chart-card' + (o.cls ? " " + o.cls : "") + '"' +
        (o.hotspot ? ' data-hotspot="' + o.hotspot + '"' : "") + ">" +
        (o.badge
          ? '<div class="tile-head"><p class="chart-title">' + o.title + "</p>" +
            '<span class="badge badge-alarm">' + o.badge + "</span></div>"
          : '<p class="chart-title">' + o.title + "</p>") +
        (o.sub ? '<p class="chart-sub">' + o.sub + "</p>" : "") +
        (o.body || "") +
        (o.legend ? '<div class="chart-legend">' + o.legend + "</div>" : "") +
        (o.foot || "") +
      "</div>"
    );
  }

  function metaRow(label, value) {
    return (
      '<div class="meta-row">' +
        '<span class="u-muted">' + label + "</span>" +
        "<strong>" + value + "</strong>" +
      "</div>"
    );
  }

  function actRow(time, text) {
    return (
      '<div class="act-row">' +
        '<span class="act-time">' + time + "</span>" +
        "<span>" + text + "</span>" +
      "</div>"
    );
  }

  function nsCard(name, count, chip, hot) {
    return (
      '<div class="console-card ns-card' + (hot ? " ns-hot" : " ns-muted") + '"' +
        (hot ? ' data-hotspot="ws-namespace"' : "") + ">" +
        '<p class="ns-name">' + name + "</p>" +
        '<p class="ns-count">' + count + "</p>" +
        (chip ? '<p class="u-mt-8"><span class="chip-ok">' + chip + "</span></p>" : "") +
      "</div>"
    );
  }

  function seg(mins, cls) {
    return '<i class="' + cls + '" style="flex:' + mins + '"></i>';
  }

  /* ---------------------------------------------------------- */
  /* Screens                                                      */
  /* ---------------------------------------------------------- */

  /* s1 — The helpdesk ticket: "my desktop is slow." */
  function screenS1() {
    return DEMO.frames.browserFrame(
      { url: "https://support.corp.example.com/tickets/48291" },
      '<div class="hd-page">' +
        '<div class="hd-top">' +
          '<span class="hd-brand">Example Corp &middot; IT Service Desk</span>' +
          '<span class="hd-nav">Queues &middot; Reports &middot; Knowledge base</span>' +
          '<span class="hd-user">Signed in: euc-ops</span>' +
        "</div>" +
        '<div class="hd-body">' +
          '<div class="hd-main">' +
            '<div class="ticket-card">' +
              '<p class="ticket-id">Ticket #48291 &middot; Desktop / Performance</p>' +
              '<h1 class="ticket-title">#48291 &mdash; &ldquo;My desktop is slow&rdquo;</h1>' +
              '<div class="ticket-chips">' +
                '<span class="chip-warn">P2</span>' +
                '<span class="chip-info">Open</span>' +
                '<span class="chips-meta">Requester: <strong>Martha Major</strong> &nbsp;&middot;&nbsp; Opened: <strong>Today 2:14 PM</strong></span>' +
              "</div>" +
              '<div class="ticket-quote">&ldquo;Everything takes forever since about 2 o&rsquo;clock. Files, apps, everything. ' +
                "I can&rsquo;t tell you more than that &mdash; it&rsquo;s just slow.&rdquo;</div>" +
              '<div class="ticket-actions">' +
                '<span class="btn-primary" data-hotspot="investigate">Investigate in CloudWatch</span>' +
                '<span class="btn-secondary">Reply to requester</span>' +
              "</div>" +
            "</div>" +
            '<div class="ticket-card hd-activity">' +
              "<h3>Activity</h3>" +
              actRow("2:14 PM", "Ticket created by <strong>mmajor</strong> via self-service portal") +
              actRow("2:15 PM", "Auto-triage: routed to <strong>EUC Ops</strong> queue") +
              actRow("2:16 PM", "Priority set to <strong>P2</strong> &mdash; response SLA 2 hours") +
            "</div>" +
          "</div>" +
          '<div class="hd-side">' +
            '<div class="ticket-card meta-card">' +
              "<h3>Details</h3>" +
              metaRow("Requester", "Martha Major (mmajor)") +
              metaRow("Assignee", "EUC Ops") +
              metaRow("Asset", WS_ID) +
              metaRow("Platform", "Amazon WorkSpaces") +
              metaRow("Region", "us-west-2") +
              metaRow("Opened", "Today 2:14 PM") +
              metaRow("Respond by", "Today 4:14 PM") +
            "</div>" +
            '<div class="ticket-card meta-card">' +
              "<h3>Requester notes</h3>" +
              '<p class="u-small u-muted">No recent changes reported. Same laptop, same home network as yesterday. ' +
                "Issue affects the cloud desktop only.</p>" +
            "</div>" +
          "</div>" +
        "</div>" +
      "</div>"
    );
  }

  /* s2 — CloudWatch metrics namespaces. */
  function screenS2() {
    return cw(
      "Metrics",
      "CloudWatch &rsaquo; Metrics &rsaquo; All namespaces",
      '<h1 class="page-title">Metrics &rsaquo; All namespaces</h1>' +
      '<p class="page-desc">Select a namespace to browse metrics. Enhanced WorkSpaces metrics publish automatically ' +
        "&mdash; no agent install, no configuration.</p>" +
      '<div class="ns-filter">Filter namespaces</div>' +
      '<div class="grid-3 ns-grid">' +
        nsCard("AWS/WorkSpaces", "126 metrics", "NEW &mdash; enhanced metrics", true) +
        nsCard("AWS/EC2", "342 metrics") +
        nsCard("AWS/EBS", "96 metrics") +
        nsCard("AWS/Lambda", "124 metrics") +
        nsCard("AWS/RDS", "168 metrics") +
      "</div>" +
      '<p class="u-small u-muted u-mt-16">Custom namespaces: CWAgent &middot; example-corp/apps</p>'
    );
  }

  /* s3 — Network metrics: the latency spike. */
  function screenS3() {
    var latency = DEMO.ui.lineChart({
      w: 520, h: 230, yMax: 200, yLabel: "ms", xLabels: HOURS,
      series: [{ points: [22, 21, 24, 23, 26, 180, 168, 142], color: BLUE, fill: true }],
      annotations: [{ x: 5, label: "2:04 PM" }],
      label: "Round-trip latency for " + WS_ID + ": steady near 22 ms, then jumps past 140 ms starting at 2:04 PM"
    });
    var loss = DEMO.ui.lineChart({
      w: 520, h: 230, yMax: 4, yLabel: "%", xLabels: HOURS,
      series: [{ points: [0, 0, 0.1, 0, 0.2, 1.8, 2.3, 2.5], color: ORANGE, fill: true }],
      label: "Packet loss for " + WS_ID + ": near zero all morning, rising to 2.5 percent after 2 PM"
    });
    return cw(
      "Metrics",
      BC_METRICS + " &rsaquo; Network",
      '<h1 class="page-title">' + WS_ID + " &mdash; Network</h1>" +
      '<p class="page-desc">Martha Major (mmajor) &middot; enhanced metrics &middot; today, 12 PM &ndash; 4 PM</p>' +
      '<div class="grid-2 metric-grid">' +
        chartCard({
          title: "Round-trip latency (ms)", sub: "Client &harr; " + WS_ID + " &middot; 1-minute period",
          hotspot: "latency-chart", body: latency, legend: leg(BLUE, "Round-trip latency (ms)")
        }) +
        chartCard({
          title: "Packet loss (%)", sub: "Streaming session &middot; 1-minute period",
          body: loss, legend: leg(ORANGE, "Packet loss (%)")
        }) +
      "</div>" +
      '<div class="flash flash-warning metric-grid u-mt-16"><strong>Latency spike correlates with ticket #48291</strong> ' +
        "(opened 2:14 PM). Degradation began 2:04 PM &mdash; ten minutes before the user reported it.</div>"
    );
  }

  /* s4 — Compute metrics: CPU pegged. */
  function screenS4() {
    var cpu = DEMO.ui.lineChart({
      w: 520, h: 230, yMax: 100, yLabel: "%", xLabels: HOURS,
      series: [{ points: [34, 41, 38, 45, 52, 98, 100, 100], color: BLUE, fill: true }],
      annotations: [{ x: 5, label: "sustained 100%" }],
      label: "CPU utilization for " + WS_ID + ": 34 to 52 percent through the morning, then pegged at 100 percent from 2 PM on"
    });
    var gpu = DEMO.ui.lineChart({
      w: 520, h: 230, yMax: 100, yLabel: "%", xLabels: HOURS,
      series: [{ points: [4, 6, 5, 7, 5, 6, 8, 6], color: GREEN, fill: false }],
      label: "GPU utilization for " + WS_ID + ": flat around 5 percent all afternoon"
    });
    return cw(
      "Metrics",
      BC_METRICS + " &rsaquo; Compute",
      '<h1 class="page-title">' + WS_ID + " &mdash; Compute</h1>" +
      '<p class="page-desc">Martha Major (mmajor) &middot; Power bundle: 4 vCPU, 16 GB &middot; today, 12 PM &ndash; 4 PM</p>' +
      '<div class="grid-2 metric-grid">' +
        chartCard({
          title: "CPU utilization (%)", sub: "Host-level &middot; 1-minute period",
          hotspot: "cpu-chart", body: cpu, legend: leg(BLUE, "CPU utilization (%)"),
          foot: '<p class="u-mt-8"><span class="chip-warn">Sustained 100% CPU &mdash; consider a larger bundle</span></p>'
        }) +
        chartCard({
          title: "GPU utilization (%)", sub: "Host-level &middot; 1-minute period",
          body: gpu, legend: leg(GREEN, "GPU utilization (%)"),
          foot: '<p class="u-mt-8"><span class="chip-ok">GPU idle &mdash; not a graphics bottleneck</span></p>'
        }) +
      "</div>"
    );
  }

  /* s5 — Storage and memory metrics. */
  function screenS5() {
    var queue = DEMO.ui.lineChart({
      w: 380, h: 210, yMax: 12, yLabel: "depth", xLabels: HOURS,
      series: [{ points: [1, 2, 1, 2, 3, 9, 11, 12], color: BLUE, fill: true }],
      label: "Disk queue depth for the root volume: 1 to 3 all morning, elevated between 8 and 12 after 2 PM"
    });
    var iops = DEMO.ui.lineChart({
      w: 380, h: 210, yMax: 4000, yLabel: "IOPS", xLabels: HOURS,
      series: [{ points: [820, 900, 870, 940, 1180, 3000, 3000, 3000], color: ORANGE, fill: true }],
      annotations: [{ x: 5, label: "volume IOPS limit" }],
      label: "Disk IOPS for the root volume: under 1,200 all morning, then a flat plateau at the 3,000 IOPS volume limit"
    });
    return cw(
      "Metrics",
      BC_METRICS + " &rsaquo; Storage &amp; memory",
      '<h1 class="page-title">' + WS_ID + " &mdash; Storage &amp; memory</h1>" +
      '<p class="page-desc">Martha Major (mmajor) &middot; root volume 175 GB &middot; today, 12 PM &ndash; 4 PM</p>' +
      '<div class="grid-3 tri-grid">' +
        chartCard({
          title: "Disk queue depth", sub: "Root volume &middot; 1-minute period",
          hotspot: "queue-chart", body: queue, legend: leg(BLUE, "Queue depth"),
          foot: '<p class="u-mt-8"><span class="chip-warn">I/O waiting on the volume</span></p>'
        }) +
        chartCard({
          title: "Disk IOPS", sub: "Root volume &middot; 1-minute period",
          body: iops, legend: leg(ORANGE, "Read + write IOPS"),
          foot: '<p class="u-mt-8"><span class="chip-warn">Flat plateau = throttling at the limit</span></p>'
        }) +
        chartCard({
          title: "Memory (GB)", sub: WS_ID + " &middot; sampled now",
          cls: "mem-card",
          body:
            '<div class="mem-track" aria-hidden="true"><i class="mem-fill"></i></div>' +
            '<p class="mem-label"><strong>14.8 / 16.0 GB used</strong> (92%)</p>' +
            '<p class="u-mt-8"><span class="chip-warn">Memory pressure</span></p>' +
            metaRow("Commit charge", "97%") +
            metaRow("Page faults", "240/sec &mdash; high") +
            metaRow("Largest process", "analytics-batch.exe"),
          foot: '<p class="u-small u-muted u-mt-8">Paging to disk is amplifying the storage bottleneck.</p>'
        }) +
      "</div>"
    );
  }

  /* s6 — Session health: reconnect churn. */
  function screenS6() {
    var reconnects = DEMO.ui.lineChart({
      w: 1000, h: 230, yMax: 4, yLabel: "count", xLabels: HOURS,
      series: [{ points: [0, 1, 0, 0, 1, 4, 3, 1], color: BLUE, fill: true }],
      label: "Session reconnects per hour: zero or one all morning, spiking to four between 2 and 3 PM"
    });
    var strip =
      seg(124, "seg-ok") + seg(6, "seg-warn") + seg(25, "seg-ok") + seg(6, "seg-warn") +
      seg(29, "seg-ok") + seg(5, "seg-warn") + seg(45, "seg-ok");
    return cw(
      "Metrics",
      BC_METRICS + " &rsaquo; Session health",
      '<h1 class="page-title">' + WS_ID + " &mdash; Session health</h1>" +
      '<p class="page-desc">Martha Major (mmajor) &middot; Amazon DCV session &middot; today, 12 PM &ndash; 4 PM</p>' +
      '<div class="sess-wrap">' +
        chartCard({
          title: "Session reconnects (per hour)", sub: "Automatic client reconnects &middot; hourly sum",
          body: reconnects, legend: leg(BLUE, "Reconnects")
        }) +
        chartCard({
          title: "Connection state &mdash; " + WS_ID, sub: "Today, 12 PM &ndash; 4 PM",
          hotspot: "session-timeline",
          body:
            '<div class="conn-strip" aria-hidden="true">' + strip + "</div>" +
            '<div class="conn-scale" aria-hidden="true">' +
              "<span>12 PM</span><span>1 PM</span><span>2 PM</span><span>3 PM</span><span>4 PM</span>" +
            "</div>",
          legend: leg(GREEN, "Connected") + leg(ORANGE, "Reconnecting"),
          foot: '<p class="u-small u-muted u-mt-8">Three reconnect bursts between 2:04 PM and 3:15 PM &mdash; ' +
            "the same window as the latency spike.</p>"
        }) +
      "</div>"
    );
  }

  /* s7 — Fleet dashboard: euc-fleet-health. */
  function screenS7() {
    function tile(cfg) { return DEMO.ui.lineChart(cfg); }
    var latP90 = tile({
      w: 380, h: 150, yMax: 120, xLabels: HOURS,
      series: [{ points: [24, 25, 26, 28, 31, 96, 88, 74], color: BLUE, fill: true }],
      label: "Fleet latency p90 in milliseconds, breaching after 2 PM"
    });
    var cpuP90 = tile({
      w: 380, h: 150, yMax: 100, xLabels: HOURS,
      series: [{ points: [38, 42, 40, 45, 48, 72, 70, 68], color: GREEN, fill: true }],
      label: "Fleet CPU p90 percent, elevated but not critical"
    });
    var lossAvg = tile({
      w: 380, h: 150, yMax: 4, xLabels: HOURS,
      series: [{ points: [0.2, 0.3, 0.2, 0.4, 0.5, 1.9, 1.6, 1.2], color: ORANGE, fill: true }],
      label: "Fleet average packet loss percent, bumping up after 2 PM"
    });
    var recon = tile({
      w: 380, h: 150, yMax: 16, xLabels: HOURS,
      series: [{ points: [2, 1, 3, 2, 4, 14, 11, 8], color: BLUE, fill: true }],
      label: "Fleet reconnects per hour, spiking after 2 PM"
    });
    var queueP90 = tile({
      w: 380, h: 150, yMax: 8, xLabels: HOURS,
      series: [{ points: [1, 1, 2, 1, 2, 6, 5, 4], color: ORANGE, fill: true }],
      label: "Fleet storage queue depth p90, elevated after 2 PM"
    });
    return cw(
      "Dashboards",
      "CloudWatch &rsaquo; Dashboards &rsaquo; euc-fleet-health",
      '<h1 class="page-title">Dashboard: euc-fleet-health</h1>' +
      '<p class="page-desc">2,000 WorkSpaces &middot; us-west-2 &middot; auto-refresh: 1 minute</p>' +
      '<div class="grid-3 tri-grid">' +
        chartCard({
          title: "Fleet latency p90 (ms)", badge: "ALARM", cls: "tile-alarm", hotspot: "alarm-tile",
          sub: "Breaching: " + WS_ID + " (mmajor)", body: latP90
        }) +
        chartCard({ title: "Fleet CPU p90 (%)", sub: "All WorkSpaces", body: cpuP90 }) +
        chartCard({ title: "Packet loss avg (%)", sub: "All streaming sessions", body: lossAvg }) +
        chartCard({ title: "Reconnects (per hour)", sub: "Fleet-wide sum", body: recon }) +
        '<div class="chart-card stat-tile">' +
          '<p class="chart-title">Active sessions</p>' +
          '<p class="chart-sub">Connected right now</p>' +
          '<p class="stat-big">412</p>' +
          '<p class="u-small u-muted">of 2,000 WorkSpaces &middot; peak today: 486</p>' +
          '<p class="u-mt-8"><span class="chip-ok">Healthy: 411</span> <span class="chip-warn">Impaired: 1</span></p>' +
        "</div>" +
        chartCard({ title: "Storage queue p90", sub: "Root volumes", body: queueP90 }) +
      "</div>"
    );
  }

  /* s8 — Alarm detail + SNS notification. */
  function screenS8() {
    var alarmChart = DEMO.ui.lineChart({
      w: 640, h: 230, yMax: 200, yLabel: "ms", xLabels: HOURS,
      series: [
        { points: [24, 23, 26, 25, 30, 180, 168, 142], color: BLUE, fill: true },
        { points: [100, 100, 100, 100, 100, 100, 100, 100], color: RED }
      ],
      label: "InSessionLatency for " + WS_ID + " crossing the flat 100 millisecond alarm threshold shortly after 2 PM"
    });
    return cw(
      "Alarms",
      "CloudWatch &rsaquo; Alarms &rsaquo; WorkSpaces-Latency-mmajor",
      '<h1 class="page-title">Alarm: WorkSpaces-Latency-mmajor</h1>' +
      '<p class="page-desc"><span class="badge badge-alarm">ALARM</span> &nbsp;In alarm since 2:09 PM today</p>' +
      '<div class="console-card alarm-card">' +
        "<h2>InSessionLatency &gt; 100 ms for 5 minutes</h2>" +
        alarmChart +
        '<div class="chart-legend">' +
          leg(BLUE, "InSessionLatency &middot; " + WS_ID) +
          leg(RED, "Threshold: 100 ms") +
        "</div>" +
        '<div class="alarm-rows u-mt-16">' +
          metaRow("Metric", "AWS/WorkSpaces &middot; InSessionLatency &middot; WorkspaceId = " + WS_ID) +
          metaRow("Condition", "&gt; 100 ms for 5 consecutive 1-minute datapoints") +
          metaRow("Actions", "SNS topic: euc-ops-pager") +
          metaRow("State changed", "OK &rarr; ALARM at 2:09 PM") +
        "</div>" +
      "</div>" +
      '<div class="sns-toast" data-hotspot="sns-toast">' +
        '<span class="badge badge-alarm">ALARM</span>' +
        '<p class="toast-title">WorkSpaces-Latency-mmajor &rarr; euc-ops-pager &middot; 2:09 PM</p>' +
        '<p class="toast-line">Ops was notified 5 minutes before the ticket was opened.</p>' +
      "</div>"
    );
  }

  /* ---------------------------------------------------------- */
  /* Registration                                                 */
  /* ---------------------------------------------------------- */

  DEMO.registerChapter({
    id: "ch7",
    act: 3,
    number: 7,
    title: "Enhanced CloudWatch Metrics for Troubleshooting",
    hook: "When a user says 'my desktop is slow,' now you can see exactly why.",
    talkingPoints: [
      "No agent install required \u2014 metrics flow automatically",
      "Pairs with existing CloudWatch Logs for full-stack observability",
      "Enables data-driven right-sizing and capacity planning"
    ],
    styles:
      /* s1 — helpdesk ticket page */
      ".ch7 .hd-page { min-height: 100%; background: #f4f5f7; font-size: 14px; }\n" +
      ".ch7 .hd-top { display: flex; align-items: center; gap: 28px; background: #1f2a37; color: #fff; padding: 14px 32px; font-size: 14px; }\n" +
      ".ch7 .hd-brand { font-weight: 700; }\n" +
      ".ch7 .hd-nav { color: #aab7c4; }\n" +
      ".ch7 .hd-user { margin-left: auto; color: #aab7c4; font-size: 13px; }\n" +
      ".ch7 .hd-body { display: flex; align-items: flex-start; gap: 24px; padding: 28px 40px; }\n" +
      ".ch7 .hd-main { flex: 1; min-width: 0; display: grid; gap: 20px; }\n" +
      ".ch7 .hd-side { width: 330px; flex: none; display: grid; gap: 20px; }\n" +
      ".ch7 .ticket-card { background: #fff; border: 1px solid #d9dde3; border-radius: 4px; padding: 20px 24px; }\n" +
      ".ch7 .ticket-card h3 { font-size: 15px; margin: 0 0 8px; }\n" +
      ".ch7 .ticket-id { font-size: 12.5px; color: var(--color-text-secondary); margin: 0 0 4px; }\n" +
      ".ch7 .ticket-title { font-size: 26px; font-weight: 700; margin: 0; }\n" +
      ".ch7 .ticket-chips { display: flex; align-items: center; gap: 8px; margin-top: 10px; }\n" +
      ".ch7 .chips-meta { font-size: 13px; color: var(--color-text-secondary); }\n" +
      ".ch7 .ticket-quote { border-left: 4px solid #d9dde3; background: #f8f9fa; padding: 14px 18px; margin: 18px 0 0; font-size: 15.5px; font-style: italic; color: #333; }\n" +
      ".ch7 .ticket-actions { display: flex; gap: 12px; margin-top: 18px; }\n" +
      ".ch7 .act-row { display: flex; gap: 14px; padding: 8px 0; border-bottom: 1px solid #eef0f3; font-size: 13px; }\n" +
      ".ch7 .act-row:last-child { border-bottom: none; }\n" +
      ".ch7 .act-time { color: var(--color-text-secondary); flex: none; width: 62px; }\n" +
      ".ch7 .meta-row { display: flex; justify-content: space-between; gap: 12px; padding: 7px 0; border-bottom: 1px solid var(--color-border); font-size: 13px; }\n" +
      ".ch7 .meta-row:last-child { border-bottom: none; }\n" +
      /* s2 — namespaces */
      ".ch7 .ns-filter { width: 420px; background: #fff; border: 1px solid #879596; border-radius: 2px; padding: 7px 12px; font-size: 13px; color: var(--color-text-secondary); margin-bottom: 16px; }\n" +
      ".ch7 .ns-grid { max-width: 1290px; }\n" +
      ".ch7 .ns-name { font-size: 16px; font-weight: 700; margin: 0 0 2px; }\n" +
      ".ch7 .ns-count { font-size: 13px; color: var(--color-text-secondary); margin: 0; }\n" +
      ".ch7 .ns-hot { border-color: var(--color-accent); box-shadow: 0 0 0 1px var(--color-accent); }\n" +
      ".ch7 .ns-muted { opacity: 0.55; }\n" +
      /* s3–s7 — metric grids and cards */
      ".ch7 .metric-grid { max-width: 1140px; }\n" +
      ".ch7 .tri-grid { max-width: 1290px; }\n" +
      ".ch7 .tile-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }\n" +
      ".ch7 .tile-head .chart-title { margin-bottom: 0; }\n" +
      ".ch7 .tile-alarm { border-color: var(--badge-red); box-shadow: 0 0 0 1px var(--badge-red); }\n" +
      ".ch7 .stat-big { font-size: 46px; font-weight: 300; color: var(--color-link); line-height: 1.1; margin: 16px 0 4px; }\n" +
      /* s5 — memory bar */
      ".ch7 .mem-track { height: 22px; background: var(--color-border); border-radius: 4px; overflow: hidden; margin: 12px 0 8px; }\n" +
      ".ch7 .mem-fill { display: block; height: 100%; width: 92.5%; background: var(--badge-red); }\n" +
      ".ch7 .mem-label { font-size: 13px; margin: 0 0 4px; }\n" +
      /* s6 — session timeline */
      ".ch7 .sess-wrap { max-width: 1080px; display: grid; gap: 16px; }\n" +
      ".ch7 .conn-strip { display: flex; height: 28px; border-radius: 3px; overflow: hidden; margin: 12px 0 6px; }\n" +
      ".ch7 .conn-strip i { display: block; height: 100%; }\n" +
      ".ch7 .seg-ok { background: var(--badge-green); }\n" +
      ".ch7 .seg-warn { background: var(--color-accent); }\n" +
      ".ch7 .conn-scale { display: flex; justify-content: space-between; font-size: 10.5px; color: var(--color-text-secondary); margin-bottom: 4px; }\n" +
      /* s8 — alarm detail + SNS toast */
      ".ch7 .alarm-card { max-width: 900px; }\n" +
      ".ch7 .alarm-rows { max-width: 640px; }\n" +
      ".ch7 .sns-toast { position: absolute; top: 12px; right: 24px; width: 390px; background: #fff; border: 1px solid var(--badge-red); border-left-width: 4px; border-radius: 2px; padding: 14px 16px; box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18); }\n" +
      ".ch7 .toast-title { font-size: 13.5px; font-weight: 700; margin: 8px 0 4px; }\n" +
      ".ch7 .toast-line { font-size: 12.5px; color: var(--color-text-secondary); margin: 0; }",
    steps: [
      {
        id: "s1",
        screen: screenS1,
        tooltip: "The classic helpdesk scenario: 'Something is wrong but I can't tell you what.'",
        target: '[data-hotspot="investigate"]',
        placement: "right",
        advance: "hotspot"
      },
      {
        id: "s2",
        screen: screenS2,
        tooltip: "New dedicated metrics namespace with dozens of per-WorkSpace data points.",
        target: '[data-hotspot="ws-namespace"]',
        placement: "right",
        advance: "hotspot"
      },
      {
        id: "s3",
        screen: screenS3,
        tooltip: "Is it the network? The latency spike at 2 PM correlates with the user's complaint.",
        target: '[data-hotspot="latency-chart"]',
        placement: "bottom",
        advance: "next"
      },
      {
        id: "s4",
        screen: screenS4,
        tooltip: "Is it compute? CPU pegged at 100% \u2014 time to right-size the bundle.",
        target: '[data-hotspot="cpu-chart"]',
        placement: "bottom",
        advance: "next"
      },
      {
        id: "s5",
        screen: screenS5,
        tooltip: "Is it disk? High queue depth = storage bottleneck \u2014 upgrade the root volume.",
        target: '[data-hotspot="queue-chart"]',
        placement: "bottom",
        advance: "next"
      },
      {
        id: "s6",
        screen: screenS6,
        tooltip: "Frequent reconnects? Client network instability \u2014 point the user to a better connection.",
        target: '[data-hotspot="session-timeline"]',
        placement: "bottom",
        advance: "next"
      },
      {
        id: "s7",
        screen: screenS7,
        tooltip: "Build a single dashboard that shows health across your entire fleet \u2014 proactive, not reactive.",
        target: '[data-hotspot="alarm-tile"]',
        placement: "right",
        advance: "next"
      },
      {
        id: "s8",
        screen: screenS8,
        tooltip: "Set alarms on thresholds \u2014 get notified before users even notice a problem.",
        target: '[data-hotspot="sns-toast"]',
        placement: "left",
        advance: "next"
      }
    ]
  });
})();
