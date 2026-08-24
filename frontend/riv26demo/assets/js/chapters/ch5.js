/* ============================================================
   Amazon WorkSpaces: From Zero to Agentic — re:Invent 2026 demo
   ch5.js — Chapter 5: Cost Optimization (Act 2)

   Classic script. Calls DEMO.registerChapter() at parse time and
   nothing else; screen functions run only when the engine renders
   them inside the 1600x900 stage canvas. Every rule in `styles`
   is prefixed with .ch5 per the engine contract.
   ============================================================ */

(function () {
  "use strict";

  var REGION = "US West (Oregon) us-west-2";
  var BC_ADVISOR = "Amazon WorkSpaces &rsaquo; WorkSpaces Advisor";
  var SIDENAV = [
    "Personal", "Applications", "Core", "Directories", "Bundles", "Images",
    { label: "WorkSpaces Advisor", active: true }
  ];

  /* ---------------------------------------------------------- */
  /* Shared builders (run at render time only)                    */
  /* ---------------------------------------------------------- */

  function frame(breadcrumbs, inner) {
    return DEMO.frames.consoleFrame(
      { region: REGION, sidenav: SIDENAV, breadcrumbs: breadcrumbs },
      inner
    );
  }

  /** 24 one-hour segments; hours in [from, to) render as billed. */
  function hourBar(from, to, caption) {
    var cells = "";
    for (var h = 0; h < 24; h++) {
      cells += "<i" + (h >= from && h < to ? ' class="on"' : "") + "></i>";
    }
    return (
      '<div class="hour-bar" aria-hidden="true">' + cells + "</div>" +
      '<div class="hour-scale" aria-hidden="true">' +
        "<span>12 AM</span><span>6 AM</span><span>12 PM</span><span>6 PM</span><span>12 AM</span>" +
      "</div>" +
      '<p class="hour-caption">' + caption + "</p>"
    );
  }

  function advRow(user, hrs, cur, rec, recChip, save) {
    return (
      "<tr>" +
        "<td><strong>" + user + "</strong></td>" +
        "<td>" + hrs + " hrs</td>" +
        "<td>" + cur + "</td>" +
        '<td><span class="' + recChip + '">' + rec + "</span></td>" +
        "<td><strong>$" + save + "</strong>/mo</td>" +
      "</tr>"
    );
  }

  function specRow(label, value) {
    return (
      '<div class="spec-row">' +
        '<span class="u-muted">' + label + "</span>" +
        "<strong>" + value + "</strong>" +
      "</div>"
    );
  }

  function stat(value, label) {
    return (
      '<div class="stat-widget">' +
        '<p class="stat-value">' + value + "</p>" +
        '<p class="stat-label">' + label + "</p>" +
      "</div>"
    );
  }

  function deptRow(name, users, cost, barPct, sharePct) {
    return (
      "<tr>" +
        "<td><strong>" + name + "</strong></td>" +
        "<td>" + users + "</td>" +
        "<td>$" + cost + "</td>" +
        '<td><span class="dept-bar"><i style="width:' + barPct + '%"></i></span>' +
        '<span class="bar-pct">' + sharePct + "%</span></td>" +
      "</tr>"
    );
  }

  /* ---------------------------------------------------------- */
  /* Screens                                                      */
  /* ---------------------------------------------------------- */

  /* s1 — Running modes: AlwaysOn vs. AutoStop comparison. */
  function screenS1() {
    return frame(
      BC_ADVISOR + " &rsaquo; Running modes",
      '<h1 class="page-title">Running modes</h1>' +
      '<p class="page-desc">Every WorkSpace bills in one of two modes. Choose per user and switch anytime &mdash; prices below use the Power bundle as an example.</p>' +
      '<div class="grid-2 mode-grid">' +
        '<div class="console-card mode-card">' +
          '<div class="mode-head"><h2>AlwaysOn</h2><span class="chip-info u-right">Flat monthly rate</span></div>' +
          '<p class="mode-price">$47<span class="per"> /month</span></p>' +
          '<p class="u-small u-muted">Unlimited usage &middot; desktop stays running</p>' +
          '<ul class="mode-list">' +
            "<li>One predictable price, no metering</li>" +
            "<li>Best for full-time users &mdash; 8+ hours a day</li>" +
            "<li>Instant connect, no resume wait</li>" +
          "</ul>" +
          hourBar(0, 24, "Billed 24 of 24 hours &mdash; connected or not") +
        "</div>" +
        '<div class="console-card mode-card mode-autostop" data-hotspot="autostop-card">' +
          '<div class="mode-head"><h2>AutoStop</h2><span class="chip-ok u-right">Typical savings: 40%</span></div>' +
          '<p class="mode-price">$9.75<span class="per"> /month</span> + $0.43<span class="per"> /hour</span></p>' +
          '<p class="u-small u-muted">Hourly billing &middot; pay only while connected</p>' +
          '<ul class="mode-list">' +
            "<li>Auto-suspends after 60 minutes idle</li>" +
            "<li>Resumes automatically when the user connects</li>" +
            "<li>Best for part-time, shift, and contractor use</li>" +
          "</ul>" +
          hourBar(8, 17, "Billed 9 of 24 hours &mdash; a typical workday") +
        "</div>" +
      "</div>"
    );
  }

  /* s2 — WorkSpaces Advisor running mode recommendations. */
  function screenS2() {
    return frame(
      BC_ADVISOR + " &rsaquo; Running mode recommendations",
      '<h1 class="page-title">Running mode recommendations</h1>' +
      '<p class="page-desc">WorkSpaces Advisor analyzed 90 days of connection history for every WorkSpace in this fleet.</p>' +
      '<div class="table-wrap adv-wrap" data-hotspot="advisor-table">' +
        '<table class="console-table">' +
          "<thead><tr><th>User</th><th>Avg connected hrs per month</th><th>Current mode</th><th>Recommended</th><th>Est. monthly savings</th></tr></thead>" +
          "<tbody>" +
            advRow("jchen", 32, "AlwaysOn", "AutoStop", "chip-ok", 28) +
            advRow("rpatel", 20, "AlwaysOn", "AutoStop", "chip-ok", 31) +
            advRow("asmith", 45, "AlwaysOn", "AutoStop", "chip-ok", 22) +
            advRow("mmajor", 168, "AutoStop", "AlwaysOn", "chip-info", 12) +
            advRow("dlopez", 26, "AlwaysOn", "AutoStop", "chip-ok", 29) +
          "</tbody>" +
        "</table>" +
      "</div>" +
      '<div class="flash flash-info adv-wrap u-mt-16">Projected fleet savings: <strong>$2,340/month (38%)</strong> if all recommendations are applied.</div>'
    );
  }

  /* s3 — Right-sizing detail for mmajor. */
  function screenS3() {
    var chart = DEMO.ui.lineChart({
      w: 700,
      h: 250,
      yMax: 32,
      yLabel: "GB",
      xLabels: ["Jul 27", "Aug 3", "Aug 10", "Aug 17", "Aug 24"],
      series: [{
        points: [10.4, 11.2, 10.7, 11.6, 10.9, 11.3, 10.2, 11.8, 12, 10.8, 11.4, 10.5, 11.9, 10.6, 11.1],
        color: "#0073bb",
        fill: true
      }],
      annotations: [{ x: 8, label: "Peak 12 GB" }],
      label: "Memory utilization for mmajor over the last 30 days: usage stays between 10 and 12 GB of the 32 GB provisioned"
    });
    return frame(
      BC_ADVISOR + " &rsaquo; Right-sizing &rsaquo; mmajor",
      '<h1 class="page-title">Right-sizing &mdash; Martha Major (mmajor)</h1>' +
      '<p class="page-desc">WorkSpace ws-9x7demo12 &middot; Power bundle &middot; corp.example.com</p>' +
      '<div class="rs-layout">' +
        '<div class="chart-card rs-chart">' +
          '<p class="chart-title">Memory utilization &mdash; last 30 days</p>' +
          '<p class="chart-sub">Sampled every 5 minutes &middot; August 2026</p>' +
          chart +
          '<div class="chart-legend"><span><span class="legend-swatch" style="background:#0073bb"></span>Memory in use (GB)</span></div>' +
        "</div>" +
        '<div class="rs-side">' +
          '<div class="console-card">' +
            "<h3>Current bundle</h3>" +
            specRow("Bundle", "Power") +
            specRow("vCPU", "4") +
            specRow("Memory", "32 GB") +
            specRow("Observed peak", "12 GB") +
            '<p class="u-mt-8"><span class="chip-warn">Memory over-provisioned</span></p>' +
          "</div>" +
          '<div class="rec-box" data-hotspot="rightsize-rec">' +
            '<span class="chip-ok">Advisor recommendation</span>' +
            '<p class="rec-title">Downgrade to Performance &mdash; save 40% ($19/mo)</p>' +
            '<p class="u-small u-muted">The 12 GB peak fits comfortably in a Performance bundle. The change applies at the next reboot &mdash; no data loss.</p>' +
            '<p class="u-mt-8"><span class="btn-primary">Apply recommendation</span></p>' +
          "</div>" +
        "</div>" +
      "</div>"
    );
  }

  /* s4 — Fleet-wide cost visibility. */
  function screenS4() {
    return frame(
      BC_ADVISOR + " &rsaquo; Cost visibility",
      '<h1 class="page-title">Cost visibility</h1>' +
      '<p class="page-desc">example-corp fleet &middot; 2,000 WorkSpaces &middot; August 2026, month to date</p>' +
      '<div class="stat-row cost-stats">' +
        stat("$54,120", "Monthly total") +
        stat("$27.06", "Average per user") +
        stat("62%", "AutoStop adoption") +
      "</div>" +
      '<div class="table-wrap dept-wrap u-mt-16" data-hotspot="dept-table">' +
        '<table class="console-table">' +
          "<thead><tr><th>Department</th><th>Users</th><th>Monthly cost</th><th>Share of spend</th></tr></thead>" +
          "<tbody>" +
            deptRow("Engineering", 820, "24,190", 100, "44.7") +
            deptRow("Finance", 240, "8,970", 37, "16.6") +
            deptRow("Support", 465, "9,420", 39, "17.4") +
            deptRow("Marketing", 190, "4,830", 20, "8.9") +
            deptRow("Data Science", 285, "6,710", 28, "12.4") +
          "</tbody>" +
        "</table>" +
      "</div>" +
      '<p class="u-small u-muted u-mt-8">Tag by department, team, or cost center &mdash; exportable to Cost Explorer and CUR.</p>'
    );
  }

  /* ---------------------------------------------------------- */
  /* Registration                                                 */
  /* ---------------------------------------------------------- */

  DEMO.registerChapter({
    id: "ch5",
    act: 2,
    number: 5,
    title: "Cost Optimization",
    hook: "Cloud desktops should save you money \u2014 here's how to make sure they do.",
    talkingPoints: [
      "AutoStop: typical savings of 40% for part-time users",
      "Bring Your Own License (BYOL) for Windows/Office"
    ],
    styles:
      ".ch5 .mode-grid { max-width: 1080px; }\n" +
      ".ch5 .mode-head { display: flex; align-items: center; gap: 12px; }\n" +
      ".ch5 .mode-head h2 { margin: 0; }\n" +
      ".ch5 .mode-autostop { border-color: var(--color-accent); box-shadow: 0 0 0 1px var(--color-accent); }\n" +
      ".ch5 .mode-price { font-size: 30px; font-weight: 300; color: var(--color-link); line-height: 1.1; margin: 10px 0 2px; }\n" +
      ".ch5 .mode-price .per { font-size: 14px; font-weight: 400; color: var(--color-text-secondary); }\n" +
      ".ch5 .mode-list { list-style: none; padding: 0; margin: 12px 0 0; }\n" +
      ".ch5 .mode-list li { padding: 6px 0; font-size: 13.5px; border-bottom: 1px solid var(--color-border); }\n" +
      ".ch5 .mode-list li:last-child { border-bottom: none; }\n" +
      ".ch5 .hour-bar { display: flex; gap: 2px; height: 18px; margin-top: 14px; }\n" +
      ".ch5 .hour-bar i { flex: 1; background: var(--color-border); border-radius: 1px; }\n" +
      ".ch5 .hour-bar i.on { background: var(--color-link); }\n" +
      ".ch5 .hour-scale { display: flex; justify-content: space-between; font-size: 10.5px; color: var(--color-text-secondary); margin-top: 4px; }\n" +
      ".ch5 .hour-caption { font-size: 12px; color: var(--color-text-secondary); margin-top: 6px; }\n" +
      ".ch5 .adv-wrap { max-width: 1080px; }\n" +
      ".ch5 .rs-layout { display: flex; align-items: flex-start; gap: 16px; max-width: 1120px; }\n" +
      ".ch5 .rs-chart { flex: none; }\n" +
      ".ch5 .rs-side { flex: 1; min-width: 300px; display: grid; gap: 16px; }\n" +
      ".ch5 .spec-row { display: flex; justify-content: space-between; gap: 12px; padding: 7px 0; border-bottom: 1px solid var(--color-border); font-size: 13.5px; }\n" +
      ".ch5 .spec-row:last-of-type { border-bottom: none; }\n" +
      ".ch5 .rec-box { background: #f2faf2; border: 1px solid var(--badge-green); border-left-width: 4px; border-radius: 2px; padding: 14px 16px; }\n" +
      ".ch5 .rec-title { font-size: 15px; font-weight: 700; margin: 8px 0 4px; }\n" +
      ".ch5 .cost-stats { max-width: 1080px; }\n" +
      ".ch5 .dept-wrap { max-width: 1080px; }\n" +
      ".ch5 .dept-bar { display: inline-block; width: 220px; height: 10px; background: var(--color-border); border-radius: 5px; overflow: hidden; vertical-align: middle; }\n" +
      ".ch5 .dept-bar i { display: block; height: 100%; background: var(--color-link); border-radius: 5px; }\n" +
      ".ch5 .bar-pct { font-size: 12px; color: var(--color-text-secondary); margin-left: 8px; vertical-align: middle; }",
    steps: [
      {
        id: "s1",
        screen: screenS1,
        tooltip: "AutoStop shuts down idle desktops and restarts them on connect \u2014 you only pay for hours used.",
        target: '[data-hotspot="autostop-card"]',
        placement: "left",
        advance: "hotspot"
      },
      {
        id: "s2",
        screen: screenS2,
        tooltip: "WorkSpaces Advisor analyzes usage patterns and recommends the cheapest running mode per user.",
        target: '[data-hotspot="advisor-table"]',
        placement: "bottom",
        advance: "next"
      },
      {
        id: "s3",
        screen: screenS3,
        tooltip: "A user on a Power bundle only uses 12 GB RAM? Downgrade to Performance and save 40%.",
        target: '[data-hotspot="rightsize-rec"]',
        placement: "right",
        advance: "next"
      },
      {
        id: "s4",
        screen: screenS4,
        tooltip: "Visibility into per-user, per-department costs \u2014 no surprises.",
        target: '[data-hotspot="dept-table"]',
        placement: "top",
        advance: "next"
      }
    ]
  });
})();
