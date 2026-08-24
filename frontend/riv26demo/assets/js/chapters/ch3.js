/* ============================================================
   Amazon WorkSpaces: From Zero to Agentic — re:Invent 2026 demo
   ch3.js — Chapter 3: Deploying Your First WorkSpace (Act 1)

   Classic script. Calls DEMO.registerChapter() at parse time and
   nothing else; screen functions run only when the engine renders
   them inside the 1600x900 stage canvas. Every rule in `styles`
   is prefixed with .ch3 per the engine contract.
   ============================================================ */

(function () {
  "use strict";

  var REGION = "US West (Oregon) us-west-2";
  var BC_HOME = "AWS Management Console";
  var BC_PERSONAL = "Amazon WorkSpaces &rsaquo; Personal";
  var BC_CREATE = "Amazon WorkSpaces &rsaquo; Personal &rsaquo; Create WorkSpaces";
  var BC_LIST = "Amazon WorkSpaces &rsaquo; Personal &rsaquo; WorkSpaces";
  var WIZ_LABELS = ["Directory", "Bundle", "User", "Review"];

  /* ---------------------------------------------------------- */
  /* Shared builders (run at render time only)                    */
  /* ---------------------------------------------------------- */

  function frame(cfg, inner) {
    cfg = cfg || {};
    if (!cfg.region) { cfg.region = REGION; }
    return DEMO.frames.consoleFrame(cfg, inner);
  }

  function wizardBar(active) {
    var out = '<div class="wizard-progress">';
    WIZ_LABELS.forEach(function (label, i) {
      if (i > 0) { out += '<span class="wsep">&rsaquo;</span>'; }
      if (i < active) {
        out += '<span class="wstep done">&#10003; ' + label + "</span>";
      } else if (i === active) {
        out += '<span class="wstep active">' + (i + 1) + ". " + label + "</span>";
      } else {
        out += '<span class="wstep">' + (i + 1) + ". " + label + "</span>";
      }
    });
    return out + "</div>";
  }

  function wizardFooter(showPrev, primaryLabel, hotspot) {
    return (
      '<div class="u-flex u-mt-16">' +
        '<span class="btn-secondary u-right">Cancel</span>' +
        (showPrev ? '<span class="btn-secondary">Previous</span>' : "") +
        '<span class="btn-primary" data-hotspot="' + hotspot + '">' + primaryLabel + "</span>" +
      "</div>"
    );
  }

  function wizardPage(active, card, footer) {
    return frame(
      { breadcrumbs: BC_CREATE },
      '<h1 class="page-title">Create WorkSpaces</h1>' +
      wizardBar(active) +
      '<div class="wiz">' + card + footer + "</div>"
    );
  }

  function svcRow(abbr, color, name) {
    return (
      '<div class="svc-row">' +
        '<span class="svc-icon" style="background:' + color + '">' + abbr + "</span>" +
        "<span>" + name + "</span>" +
      "</div>"
    );
  }

  function radioCard(selected, title, sub) {
    return (
      '<div class="radio-card' + (selected ? " selected" : "") + '">' +
        '<span class="radio-dot"></span>' +
        "<span><strong>" + title + "</strong>" +
        '<span class="opt-sub">' + sub + "</span></span>" +
      "</div>"
    );
  }

  function bundleRow(selected, name, vcpu, mem, storage, os, price) {
    return (
      "<tr" + (selected ? ' class="selected-row"' : "") + ">" +
        "<td><strong>" + name + "</strong>" +
          (selected ? ' <span class="chip-ok">Advisor pick</span>' : "") + "</td>" +
        "<td>" + vcpu + "</td><td>" + mem + "</td><td>" + storage + "</td>" +
        "<td>" + os + "</td><td>" + price + "</td>" +
      "</tr>"
    );
  }

  function userRow(selected, initials, name, email) {
    return (
      '<div class="user-row' + (selected ? " selected" : "") + '">' +
        '<span class="avatar' + (selected ? "" : " alt") + '">' + initials + "</span>" +
        "<span><strong>" + name + "</strong>" +
        '<span class="opt-sub">' + email + "</span></span>" +
        (selected ? '<span class="chip-ok u-right">Selected</span>' : "") +
      "</div>"
    );
  }

  function reviewRow(label, value) {
    return (
      '<div class="review-row">' +
        '<span class="review-label">' + label + "</span>" +
        "<span>" + value + "</span>" +
      "</div>"
    );
  }

  /* ---------------------------------------------------------- */
  /* Screens                                                      */
  /* ---------------------------------------------------------- */

  /* s1 — Console Home with the search dropdown open. */
  function screenS1() {
    var heights = [34, 48, 42, 60, 55, 72];
    var bars = "";
    for (var i = 0; i < heights.length; i++) {
      bars += "<i" + (i === heights.length - 1 ? ' class="now"' : "") +
        ' style="height:' + heights[i] + '%"></i>';
    }
    return frame(
      {
        service: "Console Home",
        sidenav: ["Recently visited", "Favorites", "All services"],
        search: "workspaces|",
        breadcrumbs: BC_HOME
      },
      '<h1 class="page-title">Console Home</h1>' +
      '<p class="page-desc">Signed in as demo-admin @ example-corp &middot; ' + REGION + "</p>" +
      '<div class="grid-2 home-grid">' +
        '<div class="console-card">' +
          "<h2>Recently visited</h2>" +
          svcRow("EC2", "#ec7211", "Amazon EC2") +
          svcRow("CW", "#b0084d", "Amazon CloudWatch") +
          svcRow("IAM", "#232f3e", "IAM") +
          svcRow("$", "#1d8102", "Billing and Cost Management") +
        "</div>" +
        '<div class="console-card">' +
          "<h2>Cost and usage</h2>" +
          '<p class="cost-value">$1,284.06</p>' +
          '<p class="cost-label">Month-to-date spend &middot; August 2026</p>' +
          '<div class="cost-bars" aria-hidden="true">' + bars + "</div>" +
          '<p class="u-small u-muted u-mt-8">Forecast: $1,982 by month end</p>' +
        "</div>" +
      "</div>" +
      '<div class="search-pop" style="top:6px;left:250px;">' +
        '<div class="pop-head">Services</div>' +
        '<div class="search-hit" data-hotspot="ws-search-hit">' +
          '<span class="hit-icon">WS</span>' +
          '<span><span class="hit-name">Amazon WorkSpaces</span>' +
          '<span class="hit-sub">Fully managed virtual desktops</span></span>' +
        "</div>" +
        '<div class="search-hit">' +
          '<span class="hit-icon hit-icon-alt">WA</span>' +
          '<span><span class="hit-name">Amazon WorkSpaces Applications</span>' +
          '<span class="hit-sub">Fully managed application streaming</span></span>' +
        "</div>" +
      "</div>"
    );
  }

  /* s2 — WorkSpaces Personal landing with Get started hero. */
  function screenS2() {
    return frame(
      { breadcrumbs: BC_PERSONAL },
      '<h1 class="page-title">Amazon WorkSpaces Personal</h1>' +
      '<p class="page-desc">Persistent cloud desktops for your workforce, streamed securely with Amazon DCV.</p>' +
      '<div class="console-card hero-card">' +
        "<h2>Get started</h2>" +
        "<p>The redesigned console walks you from zero to a running desktop in one guided flow: pick a directory, choose a bundle, and assign a user.</p>" +
        '<ul class="check-list u-mt-8">' +
          "<li>No prior VDI expertise required</li>" +
          "<li>Works with Microsoft Entra ID, Active Directory, or an AWS managed directory</li>" +
          "<li>WorkSpaces Advisor recommends the right bundle as you go</li>" +
        "</ul>" +
        '<p class="u-mt-16"><span class="btn-primary" data-hotspot="create-ws">Create WorkSpaces</span></p>' +
      "</div>" +
      '<div class="grid-2 home-grid u-mt-16">' +
        '<div class="console-card">' +
          "<h3>Redesigned console experience</h3>" +
          '<p class="u-small u-muted">Launched August 2026 &mdash; guided setup, inline recommendations, and faster navigation across Personal, Core, and Applications.</p>' +
        "</div>" +
        '<div class="console-card">' +
          "<h3>WorkSpaces Advisor built in</h3>" +
          '<p class="u-small u-muted">Advisor analyzes usage patterns and recommends right-sized bundles and running modes for every user.</p>' +
        "</div>" +
      "</div>"
    );
  }

  /* s3 — Wizard step 1 of 4: choose a directory. */
  function screenS3() {
    return wizardPage(0,
      '<div class="console-card">' +
        "<h2>Choose a directory</h2>" +
        '<p class="u-small u-muted">WorkSpaces uses a directory to authenticate users and manage their desktops.</p>' +
        '<div class="choice-stack">' +
          radioCard(true, "Microsoft Entra ID",
            "Use your existing identity provider &mdash; corp.example.com is connected and verified.") +
          radioCard(false, "AD Connector",
            "Connect your existing on-premises Active Directory.") +
          radioCard(false, "AWS Managed Microsoft AD",
            "Let AWS create and manage a directory for you.") +
        "</div>" +
      "</div>",
      wizardFooter(false, "Next", "wiz-next-1")
    );
  }

  /* s4 — Wizard step 2 of 4: select a bundle. */
  function screenS4() {
    return wizardPage(1,
      '<div class="console-card">' +
        "<h2>Select a bundle</h2>" +
        '<p class="u-small u-muted">Bundles are pre-configured combinations of vCPU, memory, storage, and an operating system. Prices shown are monthly, per WorkSpace.</p>' +
        '<div class="table-wrap u-mt-8">' +
          '<table class="console-table">' +
            "<thead><tr><th>Bundle</th><th>vCPU</th><th>Memory</th><th>Storage</th><th>OS</th><th>Monthly</th></tr></thead>" +
            "<tbody>" +
              bundleRow(false, "Value", "1", "2 GB", "90 GB", "Windows 11", "$21") +
              bundleRow(false, "Standard", "2", "4 GB", "130 GB", "Windows 11", "$25") +
              bundleRow(false, "Performance", "2", "8 GB", "175 GB", "Windows 11", "$35") +
              bundleRow(true, "Power", "4", "16 GB", "255 GB", "Windows 11", "$47") +
              bundleRow(false, "Graphics.g4dn", "4", "16 GB + GPU", "225 GB", "Windows 11", "$220") +
            "</tbody>" +
          "</table>" +
        "</div>" +
      "</div>",
      wizardFooter(true, "Next", "wiz-next-2")
    );
  }

  /* s5 — Wizard step 3 of 4: assign a user. */
  function screenS5() {
    return wizardPage(2,
      '<div class="console-card">' +
        "<h2>Assign a user</h2>" +
        '<p class="u-small u-muted">Map a directory user from corp.example.com to this WorkSpace.</p>' +
        '<p class="field-label u-mt-8">Search directory users</p>' +
        '<div class="field-box field-filled search-field">martha</div>' +
        '<div class="user-list">' +
          userRow(true, "MM", "Martha Major", "mmajor@corp.example.com") +
          userRow(false, "MR", "Martha Rivera", "mrivera@corp.example.com") +
        "</div>" +
        '<p class="u-mt-8"><span class="chip-info">1 user selected</span></p>' +
      "</div>",
      wizardFooter(true, "Next", "wiz-next-3")
    );
  }

  /* s6 — Wizard step 4 of 4: review and create. */
  function screenS6() {
    return wizardPage(3,
      '<div class="console-card">' +
        "<h2>Review and create</h2>" +
        '<p class="u-small u-muted">Confirm the configuration below. Everything can be changed after launch.</p>' +
        '<div class="review-rows">' +
          reviewRow("Directory", "corp.example.com &mdash; Microsoft Entra ID") +
          reviewRow("Bundle", "Power &mdash; 4 vCPU, 16 GB memory, 255 GB storage") +
          reviewRow("User", "Martha Major (mmajor)") +
          reviewRow("Running mode", "AutoStop") +
          reviewRow("Volume encryption", "Enabled &mdash; aws/workspaces KMS key") +
        "</div>" +
      "</div>",
      wizardFooter(true, "Create WorkSpace", "create-final")
    );
  }

  /* s7 — WorkSpaces list with the new WorkSpace AVAILABLE. */
  function screenS7() {
    return frame(
      { breadcrumbs: BC_LIST },
      '<h1 class="page-title">WorkSpaces <span class="u-muted">(1)</span></h1>' +
      '<div class="list-toolbar u-mt-8">' +
        '<span class="field-box">Find WorkSpaces by user, bundle, or ID</span>' +
        '<span class="btn-secondary">Actions</span>' +
        '<span class="btn-primary">Create WorkSpaces</span>' +
      "</div>" +
      '<div class="table-wrap list-wrap">' +
        '<table class="console-table">' +
          "<thead><tr><th>WorkSpace ID</th><th>User</th><th>Bundle</th><th>Running mode</th><th>Status</th></tr></thead>" +
          "<tbody><tr>" +
            "<td><code>ws-9x7demo12</code></td>" +
            "<td>mmajor</td><td>Power</td><td>AutoStop</td>" +
            '<td><span class="badge badge-available" data-hotspot="status-available">AVAILABLE</span></td>' +
          "</tr></tbody>" +
        "</table>" +
      "</div>" +
      '<div class="flash flash-info list-wrap u-mt-16"><strong>WorkSpaces Advisor:</strong> based on similar workloads, Power is right-sized for this user.</div>'
    );
  }

  /* ---------------------------------------------------------- */
  /* Registration                                                 */
  /* ---------------------------------------------------------- */

  DEMO.registerChapter({
    id: "ch3",
    act: 1,
    number: 3,
    title: "Deploying Your First WorkSpace",
    hook: "Let's go from zero to a running desktop in under 5 minutes.",
    talkingPoints: [
      "Contrast with traditional VDI: no hypervisor install, no storage provisioning, no network config",
      "WorkSpaces Advisor (embedded in the new console) provides right-sizing recommendations",
      "API, CLI, and CloudFormation available for automation at scale"
    ],
    styles:
      ".ch3 .home-grid { max-width: 1080px; }\n" +
      ".ch3 .hero-card { max-width: 1080px; }\n" +
      ".ch3 .wiz { max-width: 920px; }\n" +
      ".ch3 .search-pop .pop-head { padding: 8px 16px 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px; color: var(--color-text-secondary); }\n" +
      ".ch3 .search-hit .hit-name { display: block; font-weight: 700; }\n" +
      ".ch3 .search-hit .hit-sub { display: block; }\n" +
      ".ch3 .search-hit .hit-icon-alt { background: var(--color-link); }\n" +
      ".ch3 .svc-row { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 1px solid var(--color-border); font-size: 13.5px; }\n" +
      ".ch3 .svc-row:last-child { border-bottom: none; }\n" +
      ".ch3 .svc-icon { width: 24px; height: 24px; border-radius: 4px; color: #ffffff; font-size: 9.5px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none; }\n" +
      ".ch3 .cost-value { font-size: 30px; font-weight: 300; color: var(--color-link); line-height: 1.1; }\n" +
      ".ch3 .cost-label { font-size: 12px; color: var(--color-text-secondary); margin: 2px 0 12px; }\n" +
      ".ch3 .cost-bars { display: flex; align-items: flex-end; gap: 8px; height: 64px; }\n" +
      ".ch3 .cost-bars i { width: 34px; background: #dbe7f0; border-radius: 2px 2px 0 0; }\n" +
      ".ch3 .cost-bars i.now { background: var(--color-link); }\n" +
      ".ch3 .wizard-progress .wsep { color: #879596; }\n" +
      ".ch3 .choice-stack { display: grid; gap: 12px; margin-top: 12px; }\n" +
      ".ch3 .opt-sub { display: block; font-size: 12.5px; color: var(--color-text-secondary); margin-top: 2px; font-weight: 400; }\n" +
      ".ch3 .search-field { max-width: 380px; }\n" +
      ".ch3 .user-list { max-width: 560px; margin-top: 12px; border: 1px solid var(--color-border); border-radius: 2px; }\n" +
      ".ch3 .user-row { display: flex; align-items: center; gap: 12px; padding: 10px 14px; border-bottom: 1px solid var(--color-border); font-size: 14px; }\n" +
      ".ch3 .user-row:last-child { border-bottom: none; }\n" +
      ".ch3 .user-row.selected { background: var(--flash-info-bg); box-shadow: inset 3px 0 0 var(--color-link); }\n" +
      ".ch3 .avatar { width: 30px; height: 30px; border-radius: 50%; background: var(--color-link); color: #ffffff; font-size: 11.5px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none; }\n" +
      ".ch3 .avatar.alt { background: var(--badge-grey); }\n" +
      ".ch3 .review-rows { margin-top: 4px; }\n" +
      ".ch3 .review-row { display: grid; grid-template-columns: 230px 1fr; gap: 16px; padding: 10px 0; border-bottom: 1px solid var(--color-border); font-size: 14px; }\n" +
      ".ch3 .review-row:last-child { border-bottom: none; }\n" +
      ".ch3 .review-label { font-weight: 700; font-size: 13px; color: var(--color-text-secondary); }\n" +
      ".ch3 .list-toolbar { display: flex; align-items: center; gap: 12px; max-width: 1080px; margin-bottom: 12px; }\n" +
      ".ch3 .list-toolbar .field-box { flex: 1; max-width: 420px; color: var(--color-text-secondary); }\n" +
      ".ch3 .list-wrap { max-width: 1080px; }",
    steps: [
      {
        id: "s1",
        screen: screenS1,
        tooltip: "Sign in to the AWS Management Console and navigate to Amazon WorkSpaces.",
        target: '[data-hotspot="ws-search-hit"]',
        placement: "right",
        advance: "hotspot"
      },
      {
        id: "s2",
        screen: screenS2,
        tooltip: "The new guided setup helps you launch your first WorkSpace in minutes \u2014 no prior VDI expertise required.",
        target: '[data-hotspot="create-ws"]',
        placement: "right",
        advance: "hotspot"
      },
      {
        id: "s3",
        screen: screenS3,
        tooltip: "Connect your existing Entra ID or Active Directory \u2014 or let AWS create a managed directory for you.",
        target: '[data-hotspot="wiz-next-1"]',
        placement: "left",
        advance: "hotspot"
      },
      {
        id: "s4",
        screen: screenS4,
        tooltip: "Bundles are pre-configured combos of CPU, RAM, storage, and OS \u2014 pick one that fits your user's workload.",
        target: '[data-hotspot="wiz-next-2"]',
        placement: "left",
        advance: "hotspot"
      },
      {
        id: "s5",
        screen: screenS5,
        tooltip: "Map a directory user to this WorkSpace.",
        target: '[data-hotspot="wiz-next-3"]',
        placement: "left",
        advance: "hotspot"
      },
      {
        id: "s6",
        screen: screenS6,
        tooltip: "That's it. In about 20\u201330 minutes, your user will have a fully provisioned cloud desktop.",
        target: '[data-hotspot="create-final"]',
        placement: "left",
        advance: "hotspot"
      },
      {
        id: "s7",
        screen: screenS7,
        tooltip: "Status flips to AVAILABLE \u2014 the desktop is ready.",
        target: '[data-hotspot="status-available"]',
        placement: "right",
        advance: "next"
      }
    ]
  });
})();
