/* ============================================================
   Amazon WorkSpaces: From Zero to Agentic — re:Invent 2026 demo
   ch6.js — Chapter 6: Security & Compliance (Act 2)

   Classic script. Calls DEMO.registerChapter() at parse time and
   nothing else; screen functions run only when the engine renders
   them inside the 1600x900 stage canvas. Every rule in `styles`
   is prefixed with .ch6 per the engine contract.

   Steps:
     s1  Data-flow architecture (inline SVG)         advance: next
     s2  Authentication settings (SAML, MFA, PIV)    advance: next
     s3  IP access control rules                     advance: next
     s4  Encryption at rest + in transit             advance: next
     s5  CloudTrail audit log                        advance: next
   ============================================================ */

(function () {
  "use strict";

  var REGION = "US West (Oregon) us-west-2";
  var ACCOUNT = "admin-jlee @ example-corp";
  var SIDENAV_SECURITY = [
    "Personal", "Applications", "Core", "Directories",
    { label: "Security", active: true },
    "Bundles", "Images", "WorkSpaces Advisor"
  ];
  var BC_SEC = "Amazon WorkSpaces &rsaquo; Security";
  var BC_IP = BC_SEC + " &rsaquo; IP access control";
  var BC_ENC = BC_SEC + " &rsaquo; Encryption";
  var BC_TRAIL = "CloudTrail &rsaquo; Event history";

  /* ---------------------------------------------------------- */
  /* Shared builders (run at render time only)                    */
  /* ---------------------------------------------------------- */

  function wsFrame(breadcrumbs, inner) {
    return DEMO.frames.consoleFrame(
      { breadcrumbs: breadcrumbs, region: REGION, account: ACCOUNT, sidenav: SIDENAV_SECURITY },
      inner
    );
  }

  /** Small padlock, line-art shackle + solid body. Nestable. */
  function lockGlyph(x, y, scale) {
    return (
      '<g transform="translate(' + x + " " + y + ') scale(' + scale + ')">' +
        '<path d="M -5 -2.5 V -7 A 5 5 0 0 1 5 -7 V -2.5" fill="none" stroke="#ec7211" stroke-width="2.4" stroke-linecap="round"/>' +
        '<rect x="-7.5" y="-2.5" width="15" height="12.5" rx="2" fill="#ec7211" stroke="none"/>' +
        '<circle cx="0" cy="3.5" r="2" fill="#101623" stroke="none"/>' +
      "</g>"
    );
  }

  /** s1 diagram: endpoint <-> encrypted stream <-> Region boundary. */
  function dataFlowDiagram() {
    return (
      '<div class="ch6-diagram" data-hotspot="region-boundary">' +
        '<svg viewBox="0 0 1050 400" width="1050" height="400" role="img" aria-label="Architecture diagram: an endpoint exchanges only encrypted pixels and input with a WorkSpace over the Amazon DCV stream, secured with TLS 1.3. The WorkSpace and its encrypted EBS volume run inside the AWS Region us-west-2, and application data never leaves the Region.">' +

          /* Endpoint (laptop) */
          '<g transform="translate(120 172)">' +
            '<g fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">' +
              '<rect x="-50" y="-52" width="100" height="64" rx="5"/>' +
              '<path d="M -64 12 H 64 L 52 28 H -52 Z"/>' +
            "</g>" +
            '<g stroke="#9aa7bd" stroke-width="2" stroke-linecap="round">' +
              '<line x1="-36" y1="-36" x2="36" y2="-36"/>' +
              '<line x1="-36" y1="-20" x2="10" y2="-20"/>' +
              '<line x1="-36" y1="-4" x2="24" y2="-4"/>' +
            "</g>" +
            '<text y="60" text-anchor="middle" font-size="17" font-weight="700" fill="#fff">Endpoint</text>' +
            '<text y="82" text-anchor="middle" font-size="13.5" fill="#9aa7bd">Pixels in, input out</text>' +
          "</g>" +

          /* Encrypted DCV stream (thick two-headed arrow + lock badge) */
          '<line x1="224" y1="175" x2="440" y2="175" stroke="#fff" stroke-width="6"/>' +
          '<polygon points="206,175 226,165 226,185" fill="#fff"/>' +
          '<polygon points="458,175 438,165 438,185" fill="#fff"/>' +
          '<text x="332" y="138" text-anchor="middle" font-size="15" font-weight="700" fill="#fff">Encrypted DCV stream (TLS 1.3)</text>' +
          '<circle cx="332" cy="175" r="17" fill="#101623" stroke="#ec7211" stroke-width="1.5"/>' +
          lockGlyph(332, 176, 1) +

          /* AWS Region boundary */
          '<rect x="470" y="34" width="548" height="330" rx="14" fill="rgba(255,255,255,0.04)" stroke="#ec7211" stroke-width="2.5" stroke-dasharray="10 8"/>' +
          '<text x="496" y="70" font-size="16.5" font-weight="700" fill="#fff">AWS Region (us-west-2)</text>' +

          /* WorkSpace VM */
          '<g transform="translate(618 168)">' +
            '<g fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round">' +
              '<rect x="-72" y="-58" width="144" height="92" rx="6"/>' +
              '<line x1="0" y1="34" x2="0" y2="47"/>' +
              '<line x1="-28" y1="49" x2="28" y2="49"/>' +
            "</g>" +
            '<g stroke="#9aa7bd" stroke-width="2" stroke-linecap="round">' +
              '<line x1="-72" y1="-38" x2="72" y2="-38"/>' +
              '<line x1="-58" y1="-18" x2="44" y2="-18"/>' +
              '<line x1="-58" y1="-2" x2="20" y2="-2"/>' +
            "</g>" +
            '<text y="78" text-anchor="middle" font-size="15.5" font-weight="700" fill="#fff">WorkSpace</text>' +
            '<text y="98" text-anchor="middle" font-size="12.5" fill="#9aa7bd">ws-9x7demo12</text>' +
          "</g>" +

          /* Link to storage */
          '<line x1="694" y1="168" x2="826" y2="168" stroke="#9aa7bd" stroke-width="2" stroke-dasharray="3 5" stroke-linecap="round"/>' +

          /* Encrypted EBS volume (cylinder + lock) */
          '<g transform="translate(882 168)">' +
            '<g fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round">' +
              '<ellipse cx="0" cy="-42" rx="52" ry="15"/>' +
              '<path d="M -52 -42 V 32 A 52 15 0 0 0 52 32 V -42"/>' +
            "</g>" +
            lockGlyph(0, 2, 1.3) +
            '<text y="78" text-anchor="middle" font-size="15.5" font-weight="700" fill="#fff">Encrypted EBS volume</text>' +
            '<text y="98" text-anchor="middle" font-size="12.5" fill="#9aa7bd">Customer-managed KMS key</text>' +
          "</g>" +

          /* Caption inside the boundary */
          '<text x="744" y="330" text-anchor="middle" font-size="15" fill="#e8ecf2">Application data never leaves the Region</text>' +
        "</svg>" +
      "</div>"
    );
  }

  function toggle(on, hotspot) {
    return '<span class="sim-toggle' + (on ? " on" : "") + '"' +
      (hotspot ? ' data-hotspot="' + hotspot + '"' : "") + "></span>";
  }

  function settingRow(label, desc, control) {
    return (
      '<div class="set-row">' +
        '<span class="set-info"><strong>' + label + "</strong>" +
          '<span class="set-desc">' + desc + "</span></span>" +
        '<span class="set-ctl">' + control + "</span>" +
      "</div>"
    );
  }

  function ipRule(name, cidr, desc) {
    return (
      "<tr><td><strong>" + name + "</strong></td>" +
      "<td><code>" + cidr + "</code></td>" +
      "<td>" + desc + "</td></tr>"
    );
  }

  function kvRow(label, value) {
    return '<div class="kv"><span class="kv-label">' + label + "</span><span>" + value + "</span></div>";
  }

  function volumeCard(name, drive, size) {
    return (
      '<div class="console-card">' +
        '<div class="card-head"><h3>' + name + '</h3><span class="chip-ok u-right">Encrypted</span></div>' +
        kvRow("Volume", drive + " drive &middot; " + size) +
        kvRow("KMS key", "<code>alias/corp-workspaces</code>") +
        kvRow("Key type", "Customer managed") +
      "</div>"
    );
  }

  function trailRow(time, evt, user, ip) {
    return (
      "<tr><td>" + time + "</td>" +
      '<td><span class="evt-link">' + evt + "</span></td>" +
      "<td>" + user + "</td>" +
      "<td>" + ip + "</td>" +
      "<td>us-west-2</td></tr>"
    );
  }

  /* ---------------------------------------------------------- */
  /* Screens                                                      */
  /* ---------------------------------------------------------- */

  /* s1 — data-flow architecture slide. */
  function screenS1() {
    return DEMO.frames.slide(
      '<div class="slide-kicker">Security &amp; compliance</div>' +
      '<div class="slide-title">Pixels travel. Application data doesn&rsquo;t.</div>' +
      '<div class="slide-sub">Amazon DCV streams encrypted pixels down to the endpoint and carries encrypted keyboard, mouse, and USB input back. The applications and their data stay inside the AWS Region.</div>' +
      dataFlowDiagram() +
      '<div class="ch6-compliance">' +
        '<span class="ch6-comp-label">Compliance programs</span>' +
        '<ul class="chip-list">' +
          "<li>FedRAMP High</li><li>HIPAA</li><li>PCI-DSS</li><li>SOC 2</li><li>ISO 27001</li>" +
        "</ul>" +
      "</div>"
    );
  }

  /* s2 — authentication settings. */
  function screenS2() {
    return wsFrame(BC_SEC,
      '<h1 class="page-title">Security</h1>' +
      '<p class="page-desc">Authentication, network access, and encryption for directory <code>corp.example.com</code>.</p>' +
      '<div class="console-card sec-card">' +
        "<h2>Authentication</h2>" +
        '<p class="u-small u-muted">How users prove who they are before a streaming session starts.</p>' +
        '<div class="set-rows">' +
          settingRow("SAML 2.0 identity provider",
            "Users federate through your IdP before the WorkSpaces client connects.",
            '<span class="chip-ok">Connected &mdash; idp.corp.example.com</span>') +
          settingRow("Require MFA at sign-in",
            "A second factor is required on every connection, including trusted networks.",
            '<span class="set-state">Enforced</span>' + toggle(true, "mfa-toggle")) +
          settingRow("Smart card authentication (PIV/CAC)",
            "Pre-session and in-session smart card support for badge-based sign-in.",
            '<span class="set-state">Enabled</span>' + toggle(true)) +
          settingRow("Certificate-based authentication",
            "Silent device trust with client certificates. Not yet enabled for this directory.",
            '<span class="set-state">Off</span>' + toggle(false)) +
        "</div>" +
      "</div>"
    );
  }

  /* s3 — IP access control rules. */
  function screenS3() {
    return wsFrame(BC_IP,
      '<h1 class="page-title">IP access control</h1>' +
      '<p class="page-desc">Allow WorkSpaces connections only from networks you trust. Everything else is stopped before authentication.</p>' +
      '<div class="ch6-list-head">' +
        "<span><strong>ipg-corp-trusted</strong> " +
          '<span class="u-small u-muted">&middot; associated with corp.example.com &middot; 3 rules</span></span>' +
        '<span class="btn-secondary">Add rule</span>' +
      "</div>" +
      '<div class="table-wrap ch6-wide" data-hotspot="ip-rules">' +
        '<table class="console-table">' +
          "<thead><tr><th>Rule name</th><th>CIDR</th><th>Description</th></tr></thead>" +
          "<tbody>" +
            ipRule("corp-hq", "203.0.113.0/24", "Corporate HQ egress") +
            ipRule("vpn-pool", "198.51.100.0/22", "AnyConnect VPN") +
            ipRule("branch-sea", "192.0.2.0/26", "Seattle branch office") +
          "</tbody>" +
        "</table>" +
      "</div>" +
      '<div class="flash flash-info ch6-wide u-mt-16"><strong>Implicit deny:</strong> connections from any other network are denied.</div>'
    );
  }

  /* s4 — encryption at rest and in transit. */
  function screenS4() {
    return wsFrame(BC_ENC,
      '<h1 class="page-title">Encryption</h1>' +
      '<p class="page-desc">At-rest and in-transit protection for WorkSpace <code>ws-9x7demo12</code> (mmajor) in corp.example.com.</p>' +
      '<div class="grid-2 ch6-wide" data-hotspot="kms-cards">' +
        volumeCard("Root volume", "C:", "175 GB") +
        volumeCard("User volume", "D:", "80 GB") +
      "</div>" +
      '<div class="console-card ch6-wide u-mt-16">' +
        '<div class="card-head"><h3>In transit</h3><span class="chip-ok u-right">DCV stream encrypted &mdash; TLS 1.3</span></div>' +
        '<p class="u-small u-muted">Every session negotiates TLS 1.3 between the client and the streaming gateway. Pixels, input, and device redirection all travel inside the encrypted stream.</p>' +
      "</div>"
    );
  }

  /* s5 — CloudTrail event history. */
  function screenS5() {
    return DEMO.frames.consoleFrame(
      {
        service: "CloudTrail",
        sidenav: ["Dashboard", { label: "Event history", active: true }, "Insights", "Trails"],
        breadcrumbs: BC_TRAIL,
        region: REGION,
        account: ACCOUNT
      },
      '<h1 class="page-title">Event history</h1>' +
      '<p class="page-desc">Management events from the last 90 days, filtered to Amazon WorkSpaces API activity.</p>' +
      '<div class="ch6-list-head">' +
        '<span class="field-box ch6-filter">Event source: workspaces.amazonaws.com</span>' +
        '<span class="chip-info">6 events &middot; August 14, 2026</span>' +
      "</div>" +
      '<div class="table-wrap ch6-wide" data-hotspot="trail-table">' +
        '<table class="console-table">' +
          "<thead><tr><th>Event time</th><th>Event name</th><th>User</th><th>Source IP</th><th>Region</th></tr></thead>" +
          "<tbody>" +
            trailRow("Aug 14, 2026, 3:22:41 PM", "TerminateWorkspaces", "automation-role", "203.0.113.87") +
            trailRow("Aug 14, 2026, 3:05:17 PM", "ModifyWorkspaceState", "automation-role", "203.0.113.87") +
            trailRow("Aug 14, 2026, 2:41:03 PM", "ModifyWorkspaceProperties", "admin-jlee", "203.0.113.24") +
            trailRow("Aug 14, 2026, 2:17:56 PM", "CreateWorkspaces", "admin-jlee", "203.0.113.24") +
            trailRow("Aug 14, 2026, 2:03:38 PM", "AuthorizeIpRules", "admin-jlee", "203.0.113.24") +
            trailRow("Aug 14, 2026, 1:58:12 PM", "CreateIpGroup", "admin-jlee", "203.0.113.24") +
          "</tbody>" +
        "</table>" +
      "</div>"
    );
  }

  /* ---------------------------------------------------------- */
  /* Registration                                                 */
  /* ---------------------------------------------------------- */

  DEMO.registerChapter({
    id: "ch6",
    act: 2,
    number: 6,
    title: "Security & Compliance",
    hook: "Data stays in the cloud. Period.",
    talkingPoints: [
      "Compliance: FedRAMP High, HIPAA, PCI-DSS, SOC 2, ISO 27001",
      "Data residency: desktops run in the Region you choose",
      "No data on the endpoint \u2014 lost laptop = no breach"
    ],
    styles:
      /* s1 — dark-slide diagram + light-on-dark compliance chips */
      ".ch6 .ch6-diagram { width: 1050px; max-width: 92%; margin: 6px auto 0; }\n" +
      ".ch6 .ch6-diagram svg { display: block; width: 100%; height: auto; }\n" +
      ".ch6 .ch6-diagram text { font-family: var(--font-ui); }\n" +
      ".ch6 .ch6-compliance { display: flex; align-items: center; gap: 16px; }\n" +
      ".ch6 .ch6-comp-label { font-size: 12.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #9aa7bd; white-space: nowrap; }\n" +
      ".ch6 .sim-slide .chip-list { justify-content: center; }\n" +
      ".ch6 .sim-slide .chip-list li { background: rgba(255, 255, 255, 0.07); border-color: rgba(255, 255, 255, 0.32); color: #e8ecf2; }\n" +
      /* s2 — authentication setting rows */
      ".ch6 .sec-card { max-width: 900px; }\n" +
      ".ch6 .set-rows { margin-top: 10px; }\n" +
      ".ch6 .set-row { display: flex; align-items: center; gap: 18px; padding: 13px 0; border-bottom: 1px solid var(--color-border); }\n" +
      ".ch6 .set-row:last-child { border-bottom: none; padding-bottom: 4px; }\n" +
      ".ch6 .set-info strong { font-size: 14px; }\n" +
      ".ch6 .set-desc { display: block; font-size: 12.5px; color: var(--color-text-secondary); margin-top: 2px; }\n" +
      ".ch6 .set-ctl { margin-left: auto; display: flex; align-items: center; gap: 10px; flex: none; }\n" +
      ".ch6 .set-state { font-size: 12.5px; font-weight: 700; color: var(--color-text-secondary); }\n" +
      /* s3/s4/s5 — shared layout */
      ".ch6 .ch6-wide { max-width: 1000px; }\n" +
      ".ch6 .ch6-list-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; max-width: 1000px; margin-bottom: 12px; }\n" +
      ".ch6 .ch6-list-head .btn-secondary { flex: none; }\n" +
      /* s4 — encryption cards */
      ".ch6 .card-head { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }\n" +
      ".ch6 .card-head h3 { margin-bottom: 0; }\n" +
      ".ch6 .kv { display: grid; grid-template-columns: 110px 1fr; gap: 12px; padding: 7px 0; border-bottom: 1px solid var(--color-border); font-size: 13.5px; }\n" +
      ".ch6 .kv:last-child { border-bottom: none; padding-bottom: 2px; }\n" +
      ".ch6 .kv-label { font-size: 12.5px; font-weight: 700; color: var(--color-text-secondary); }\n" +
      /* s5 — CloudTrail */
      ".ch6 .ch6-filter { flex: 1; max-width: 430px; color: var(--color-text); }\n" +
      ".ch6 .evt-link { color: var(--color-link); font-weight: 700; }",
    steps: [
      {
        id: "s1",
        screen: screenS1,
        tooltip: "User inputs travel over encrypted streams \u2014 application data never leaves the AWS Region.",
        target: '[data-hotspot="region-boundary"]',
        placement: "bottom-right",
        advance: "next"
      },
      {
        id: "s2",
        screen: screenS2,
        tooltip: "Enforce MFA at login \u2014 supports SAML 2.0 IdP, smart cards, and certificate-based authentication.",
        target: '[data-hotspot="mfa-toggle"]',
        placement: "right",
        advance: "next"
      },
      {
        id: "s3",
        screen: screenS3,
        tooltip: "Restrict connections to trusted networks \u2014 VPN, corporate IPs, or Zero Trust.",
        target: '[data-hotspot="ip-rules"]',
        placement: "bottom",
        advance: "next"
      },
      {
        id: "s4",
        screen: screenS4,
        tooltip: "Volumes are encrypted with customer-managed KMS keys \u2014 and the streaming protocol is encrypted as well.",
        target: '[data-hotspot="kms-cards"]',
        placement: "bottom",
        advance: "next"
      },
      {
        id: "s5",
        screen: screenS5,
        tooltip: "Every API call is logged \u2014 who did what, when, from where.",
        target: '[data-hotspot="trail-table"]',
        placement: "top",
        advance: "next"
      }
    ]
  });
})();
