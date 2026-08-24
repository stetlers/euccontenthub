/* ============================================================
   Amazon WorkSpaces: From Zero to Agentic — re:Invent 2026 demo
   ch2.js — Chapter 2: The Amazon WorkSpaces Portfolio (Act 1)

   Classic script. Calls DEMO.registerChapter() at parse time and
   nothing else. No DOM access at parse time; screen functions run
   only when rendered into the 1600x900 stage canvas.
   ============================================================ */

(function () {
  "use strict";

  /* ------------------------------------------------------------
     Portfolio data (source: demo plan, "The Portfolio" table).
     On-screen card order: Personal, Applications, Core.
     ------------------------------------------------------------ */

  var SERVICES = [
    {
      key: "personal",
      name: "WorkSpaces Personal",
      bestFor: "Persistent desktops for full-time employees",
      differentiator: "1:1 user-to-desktop, personal storage, full Windows/Linux experience",
      chip: "Persistent 1:1 desktops",
      bullets: [
        "Power users who need a full desktop: developers, designers, analysts",
        "Each user keeps the same desktop and personal storage between sessions",
        "Full Windows or Linux experience, streamed over Amazon DCV"
      ]
    },
    {
      key: "applications",
      name: "WorkSpaces Applications",
      bestFor: "Non-persistent application streaming",
      differentiator: "App-level delivery, no full desktop needed",
      chip: "Stream apps, not desktops",
      bullets: [
        "Task workers who need two or three apps, not a whole desktop",
        "Non-persistent by design: a clean session at every launch",
        "Pay only while users are actively streaming"
      ]
    },
    {
      key: "core",
      name: "WorkSpaces Core",
      bestFor: "Bring-your-own VDI management (Citrix, Omnissa, etc.)",
      differentiator: "AWS infrastructure + your control plane",
      chip: "Your control plane on AWS",
      bullets: [
        "Keep the Citrix or Omnissa management layer you already run",
        "AWS supplies the fully managed infrastructure underneath",
        "Protect the VDI investment you have while exiting the data center"
      ]
    }
  ];

  /* ------------------------------------------------------------
     Building blocks
     ------------------------------------------------------------ */

  function svcIcon(key) {
    if (key === "personal") {
      return (
        '<span class="ch2-svc-icon ch2-icon-personal" aria-hidden="true">' +
          '<svg width="26" height="26" viewBox="0 0 24 24">' +
            '<rect x="2.5" y="3.5" width="19" height="13" rx="1.5" fill="#0073bb"></rect>' +
            '<rect x="4.5" y="5.5" width="15" height="9" rx="0.5" fill="#ffffff"></rect>' +
            '<rect x="10" y="17.5" width="4" height="2.2" fill="#0073bb"></rect>' +
            '<rect x="7" y="19.7" width="10" height="1.8" rx="0.9" fill="#0073bb"></rect>' +
          "</svg>" +
        "</span>"
      );
    }
    if (key === "applications") {
      return (
        '<span class="ch2-svc-icon ch2-icon-applications" aria-hidden="true">' +
          '<svg width="26" height="26" viewBox="0 0 24 24">' +
            '<rect x="3" y="3" width="8" height="8" rx="1.5" fill="#ec7211"></rect>' +
            '<rect x="13" y="3" width="8" height="8" rx="1.5" fill="#ec7211" opacity="0.55"></rect>' +
            '<rect x="3" y="13" width="8" height="8" rx="1.5" fill="#ec7211" opacity="0.55"></rect>' +
            '<rect x="13" y="13" width="8" height="8" rx="1.5" fill="#ec7211"></rect>' +
          "</svg>" +
        "</span>"
      );
    }
    return (
      '<span class="ch2-svc-icon ch2-icon-core" aria-hidden="true">' +
        '<svg width="26" height="26" viewBox="0 0 24 24">' +
          '<rect x="4" y="3.5" width="16" height="4.6" rx="1" fill="#232f3e"></rect>' +
          '<rect x="4" y="9.7" width="16" height="4.6" rx="1" fill="#546074"></rect>' +
          '<rect x="4" y="15.9" width="16" height="4.6" rx="1" fill="#8896a8"></rect>' +
        "</svg>" +
      "</span>"
    );
  }

  function pageHeader(title, sub) {
    return (
      '<div class="ch2-head">' +
        '<p class="ch2-kicker">Act 1 &middot; Chapter 2</p>' +
        '<h1 class="ch2-title">' + title + "</h1>" +
        '<p class="ch2-sub">' + sub + "</p>" +
      "</div>"
    );
  }

  function familyFoot() {
    return (
      '<div class="ch2-foot">' +
        '<span class="ch2-foot-label">Shared across the family</span>' +
        '<ul class="chip-list">' +
          "<li>Amazon DCV high-performance streaming</li>" +
          "<li>Bring Your Own Protocol (BYOP)</li>" +
          "<li>Fully managed infrastructure</li>" +
          "<li>Unified billing and security</li>" +
        "</ul>" +
      "</div>"
    );
  }

  function serviceCard(svc, highlight) {
    var cls = "console-card ch2-card";
    if (highlight === svc.key) {
      cls += " ch2-card-hl";
    } else if (highlight) {
      cls += " ch2-card-dim";
    }
    return (
      '<div class="' + cls + '" data-hotspot="card-' + svc.key + '">' +
        '<div class="ch2-card-head">' + svcIcon(svc.key) + "<h3>" + svc.name + "</h3></div>" +
        '<div class="ch2-card-row"><span class="ch2-row-label">Best for</span><p>' + svc.bestFor + "</p></div>" +
        '<div class="ch2-card-row"><span class="ch2-row-label">Key differentiator</span><p>' + svc.differentiator + "</p></div>" +
      "</div>"
    );
  }

  function detailStrip(highlight) {
    if (!highlight) {
      return (
        '<div class="ch2-strip ch2-strip-hint">' +
          "<p>Three services, one family. Step through each card to see where it fits best.</p>" +
        "</div>"
      );
    }
    var svc = null;
    for (var i = 0; i < SERVICES.length; i++) {
      if (SERVICES[i].key === highlight) { svc = SERVICES[i]; }
    }
    var items = svc.bullets.map(function (b) { return "<li>" + b + "</li>"; }).join("");
    return (
      '<div class="console-card ch2-strip ch2-strip-active">' +
        '<div class="ch2-strip-head"><h4>' + svc.name + '</h4><span class="chip-info">' + svc.chip + "</span></div>" +
        '<ul class="check-list ch2-strip-list">' + items + "</ul>" +
      "</div>"
    );
  }

  /* ------------------------------------------------------------
     Screens
     ------------------------------------------------------------ */

  /** Portfolio overview page; highlight is 'personal' | 'applications' | 'core' | null. */
  function portfolioScreen(highlight) {
    var cards = SERVICES.map(function (svc) { return serviceCard(svc, highlight); }).join("");
    return (
      '<div class="ch2-page">' +
        '<div class="ch2-inner">' +
          pageHeader(
            "The Amazon WorkSpaces family",
            "One family, three services, every use case &mdash; pick the right tool for each user population."
          ) +
          '<div class="grid-3 ch2-cards">' + cards + "</div>" +
          detailStrip(highlight) +
          familyFoot() +
        "</div>" +
      "</div>"
    );
  }

  function matrixRow(scenario, service, badgeCls, why) {
    return (
      "<tr>" +
        '<td class="ch2-scenario">' + scenario + "</td>" +
        '<td><span class="badge ' + badgeCls + '">' + service + "</span></td>" +
        "<td>" + why + "</td>" +
      "</tr>"
    );
  }

  function matrixScreen() {
    return (
      '<div class="ch2-page">' +
        '<div class="ch2-inner">' +
          pageHeader(
            "Which service for which scenario?",
            "Match each user population to the service that fits &mdash; or combine them."
          ) +
          '<div class="table-wrap ch2-matrix" data-hotspot="matrix">' +
            '<table class="console-table">' +
              "<thead><tr>" +
                '<th class="ch2-col-scenario">Scenario</th>' +
                '<th class="ch2-col-service">Recommended service</th>' +
                '<th class="ch2-col-why">Why it fits</th>' +
              "</tr></thead>" +
              "<tbody>" +
                matrixRow(
                  "Full-time engineer who needs a persistent development desktop",
                  "WorkSpaces Personal", "badge-info",
                  "A 1:1 persistent desktop with personal storage and a full Windows or Linux experience."
                ) +
                matrixRow(
                  "Task workers who need two or three apps, not a full desktop",
                  "WorkSpaces Applications", "badge-info",
                  "Streams just the applications &mdash; no desktop overhead, pay only when streaming."
                ) +
                matrixRow(
                  "Existing investment in Citrix or Omnissa VDI",
                  "WorkSpaces Core", "badge-info",
                  "Keep your management layer and run it on AWS infrastructure."
                ) +
                matrixRow(
                  "Mixed populations across departments",
                  "Combine services", "badge-available",
                  "Run multiple services side by side with unified billing and one security model."
                ) +
              "</tbody>" +
            "</table>" +
          "</div>" +
          familyFoot() +
        "</div>" +
      "</div>"
    );
  }

  /* ------------------------------------------------------------
     Chapter styles — every rule prefixed with .ch2
     ------------------------------------------------------------ */

  var styles = [
    ".ch2 .ch2-page { box-sizing: border-box; height: 100%; background: var(--color-surface); padding: 48px 64px; overflow: hidden; }",
    ".ch2 .ch2-inner { width: 100%; max-width: 1360px; height: 100%; margin: 0 auto; display: flex; flex-direction: column; }",
    ".ch2 .ch2-kicker { color: var(--color-accent); font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.1px; margin: 0 0 8px; }",
    ".ch2 .ch2-title { font-size: 36px; font-weight: 300; line-height: 1.15; }",
    ".ch2 .ch2-sub { font-size: 17px; color: var(--color-text-secondary); margin-top: 8px; }",
    ".ch2 .ch2-cards { margin-top: 30px; }",
    ".ch2 .ch2-card { background: #fafbfb; padding: 22px 24px; border-top: 3px solid transparent; }",
    ".ch2 .ch2-card-hl { background: var(--color-surface); border-top-color: var(--color-accent); transform: translateY(-4px) scale(1.01); box-shadow: 0 10px 26px rgba(15, 30, 50, 0.16); }",
    ".ch2 .ch2-card-dim { opacity: 0.8; }",
    ".ch2 .ch2-card-head { display: flex; align-items: center; gap: 14px; margin-bottom: 6px; }",
    ".ch2 .ch2-card-head h3 { font-size: 18px; font-weight: 700; margin: 0; }",
    ".ch2 .ch2-svc-icon { width: 46px; height: 46px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex: none; }",
    ".ch2 .ch2-icon-personal { background: #eaf4fb; }",
    ".ch2 .ch2-icon-applications { background: #fdf0e5; }",
    ".ch2 .ch2-icon-core { background: #eef0f2; }",
    ".ch2 .ch2-card-row { margin-top: 12px; font-size: 14px; line-height: 1.45; }",
    ".ch2 .ch2-card-row p { margin: 0; }",
    ".ch2 .ch2-row-label { display: block; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px; color: var(--color-text-secondary); margin-bottom: 2px; }",
    ".ch2 .ch2-strip { margin-top: 28px; min-height: 156px; }",
    ".ch2 .ch2-strip-hint { display: flex; align-items: center; justify-content: center; text-align: center; border: 1.5px dashed #aab7b8; border-radius: 4px; background: #fafbfb; color: var(--color-text-secondary); font-size: 15.5px; padding: 20px 24px; }",
    ".ch2 .ch2-strip-hint p { margin: 0; }",
    ".ch2 .ch2-strip-active { border-left: 4px solid var(--color-accent); padding: 20px 24px; }",
    ".ch2 .ch2-strip-head { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }",
    ".ch2 .ch2-strip-head h4 { font-size: 16px; font-weight: 700; margin: 0; }",
    ".ch2 .ch2-strip-list { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px 26px; margin: 0; }",
    ".ch2 .ch2-strip-list li { margin-bottom: 0; font-size: 13.5px; line-height: 1.5; }",
    ".ch2 .ch2-foot { margin-top: auto; display: flex; align-items: center; gap: 16px; padding-top: 26px; }",
    ".ch2 .ch2-foot-label { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--color-text-secondary); white-space: nowrap; }",
    ".ch2 .ch2-matrix { margin-top: 30px; }",
    ".ch2 .ch2-matrix .console-table th { font-size: 12px; padding: 12px 20px; }",
    ".ch2 .ch2-matrix .console-table td { padding: 17px 20px; font-size: 15px; line-height: 1.5; vertical-align: middle; }",
    ".ch2 .ch2-col-scenario { width: 42%; }",
    ".ch2 .ch2-col-service { width: 22%; }",
    ".ch2 .ch2-col-why { width: 36%; }",
    ".ch2 .ch2-scenario { font-weight: 700; }"
  ].join("\n");

  /* ------------------------------------------------------------
     Chapter registration
     ------------------------------------------------------------ */

  DEMO.registerChapter({
    id: "ch2",
    act: 1,
    number: 2,
    title: "The Amazon WorkSpaces Portfolio",
    hook: "One family, three services, every use case.",
    talkingPoints: [
      "Streaming protocol across all services: Amazon DCV (high-performance, adaptive) and Bring Your Own Protocol (BYOP).",
      "All services are fully managed — no infrastructure to maintain.",
      "Unified billing, unified security model."
    ],
    styles: styles,
    steps: [
      {
        id: "s1",
        screen: function () { return portfolioScreen(null); },
        tooltip: "Amazon WorkSpaces is a family of services — pick the right tool for each user population.",
        target: '[data-hotspot="card-personal"]',
        placement: "bottom",
        advance: "hotspot"
      },
      {
        id: "s2",
        screen: function () { return portfolioScreen("personal"); },
        tooltip: "For power users who need a full persistent desktop — developers, designers, analysts.",
        target: '[data-hotspot="card-applications"]',
        placement: "bottom",
        advance: "hotspot"
      },
      {
        id: "s3",
        screen: function () { return portfolioScreen("applications"); },
        tooltip: "For task workers who need specific apps — no desktop overhead, pay only when streaming.",
        target: '[data-hotspot="card-core"]',
        placement: "bottom",
        advance: "hotspot"
      },
      {
        id: "s4",
        screen: function () { return portfolioScreen("core"); },
        tooltip: "Already invested in Citrix or Omnissa? Keep your management layer and run on AWS infrastructure.",
        target: '[data-hotspot="card-core"]',
        placement: "bottom",
        advance: "next"
      },
      {
        id: "s5",
        screen: function () { return matrixScreen(); },
        tooltip: "You don't have to choose just one — many customers use multiple services for different populations.",
        target: '[data-hotspot="matrix"]',
        placement: "top",
        advance: "next"
      }
    ]
  });
})();
