/* ============================================================
   Amazon WorkSpaces: From Zero to Agentic — re:Invent 2026 demo
   ch9.js — Chapter 9: WorkSpaces for Agents (Act 3)

   Chapter content file. Registers itself via DEMO.registerChapter
   at parse time and does nothing else (no DOM access at parse
   time; screen functions run only when rendered inside the
   1600x900 stage canvas). Uses DEMO.frames.* scaffolding and
   theme.css components; all chapter CSS is prefixed with .ch9.
   ============================================================ */

(function () {
  "use strict";

  /* ---------------------------------------------------------- */
  /* Shared fragments — agent desktop scene (s3–s5)               */
  /* ---------------------------------------------------------- */

  /**
   * Agent "action ticker": dark card, top-right of the desktop
   * surface, listing timestamped agent actions. The last entry
   * is rendered as the active one (accent left border).
   */
  function ticker(entries, isHotspot) {
    var rows = entries.map(function (e, i) {
      var active = i === entries.length - 1;
      return (
        '<div class="tick-row' + (active ? " tick-active" : "") + '">' +
          '<span class="tick-time">' + e.t + "</span>" +
          '<span class="tick-text">' + e.text + "</span>" +
        "</div>"
      );
    }).join("");
    return (
      '<div class="agent-ticker"' + (isHotspot ? ' data-hotspot="ticker"' : "") + '>' +
        '<div class="ticker-title">Agent session &mdash; task #1042</div>' +
        rows +
      "</div>"
    );
  }

  /** Claims Portal application window (chrome shared by s3–s5). */
  function portalWindow(bodyInner) {
    return DEMO.frames.appWindow(
      { title: "Claims Portal &mdash; Internal", iconClass: "icon-portal", x: 120, y: 90, w: 900, h: 560 },
      '<div class="portal">' +
        '<div class="portal-head">' +
          '<span class="portal-brand">Example Corp Claims Portal</span>' +
          '<span class="portal-user">Signed in as <strong>svc-claims-bot</strong></span>' +
        "</div>" +
        '<div class="portal-body">' + bodyInner + "</div>" +
      "</div>"
    );
  }

  function formField(label, value, state) {
    var cls = state === "focus" ? " field-focus" : state === "filled" ? " field-filled" : "";
    return (
      '<div class="form-field">' +
        '<span class="field-label">' + label + "</span>" +
        '<div class="field-box' + cls + '">' + (value || "") + "</div>" +
      "</div>"
    );
  }

  /** s3 — pending claims queue inside the portal. */
  function queueBody() {
    return (
      '<div class="portal-crumb">Claims &rsaquo; Pending queue</div>' +
      "<h3>Pending claims queue</h3>" +
      '<p class="portal-sub">4 claims awaiting intake &middot; refreshed 2:01 PM, August 18, 2026</p>' +
      '<div class="table-wrap"><table class="console-table">' +
        "<thead><tr><th>Claim</th><th>Claimant</th><th>Amount</th><th>Received</th><th>Status</th></tr></thead>" +
        "<tbody>" +
          '<tr class="selected-row"><td>CLM-20841</td><td>R. Alvarez</td><td>$1,284.00</td>' +
            '<td>Aug 18, 2026</td><td><span class="badge badge-info">New</span></td></tr>' +
          "<tr><td>CLM-20842</td><td>T. Nguyen</td><td>$612.50</td>" +
            '<td>Aug 18, 2026</td><td><span class="badge badge-info">New</span></td></tr>' +
          "<tr><td>CLM-20839</td><td>M. Okafor</td><td>$2,090.00</td>" +
            '<td>Aug 17, 2026</td><td><span class="badge badge-pending">In review</span></td></tr>' +
          "<tr><td>CLM-20836</td><td>D. Silva</td><td>$458.75</td>" +
            '<td>Aug 17, 2026</td><td><span class="badge badge-pending">In review</span></td></tr>' +
        "</tbody>" +
      "</table></div>"
    );
  }

  /** s4/s5 — claim intake form inside the portal. */
  function claimFormBody(opts) {
    opts = opts || {};
    var dateField = opts.dateDone
      ? formField("Incident date", "08/14/2026", "filled")
      : formField("Incident date", '08/1<span class="type-caret"></span>', "focus");
    return (
      '<div class="portal-crumb">Claims &rsaquo; Pending queue &rsaquo; CLM-20841</div>' +
      "<h3>Claim CLM-20841</h3>" +
      '<p class="portal-sub">Intake &middot; section 1 of 2 &mdash; incident details</p>' +
      '<div class="claim-form"' + (opts.hotspot ? ' data-hotspot="claim-form"' : "") + ">" +
        '<div class="form-grid">' +
          formField("Claimant", "R. Alvarez", "filled") +
          formField("Policy number", "POL-88213-C", "filled") +
          formField("Amount", "$1,284.00", "filled") +
          dateField +
        "</div>" +
        '<div class="form-wide">' +
          '<span class="field-label">Description</span>' +
          '<div class="field-box field-area"></div>' +
        "</div>" +
        '<div class="form-actions">' +
          '<span class="btn-secondary">Save draft</span>' +
          '<span class="btn-primary">Submit claim</span>' +
        "</div>" +
      "</div>"
    );
  }

  /** s5 — unexpected session dialog + the agent's reasoning card. */
  function sessionDialog() {
    return (
      '<div class="sim-dialog agent-dialog" data-hotspot="dialog">' +
        '<div class="dialog-title">Session expiring</div>' +
        '<div class="dialog-body">Your session will expire in 2 minutes. Do you want to extend?</div>' +
        '<div class="dialog-actions">' +
          '<span class="btn-secondary">Log out</span>' +
          '<span class="btn-primary">Extend session</span>' +
        "</div>" +
      "</div>"
    );
  }

  function reasonCard() {
    return (
      '<div class="reason-card">' +
        '<div class="reason-title">Agent reasoning</div>' +
        '<div class="reason-line">Dialog detected</div>' +
        '<div class="reason-line"><span class="reason-arrow">&rarr;</span> reads: session expiry warning</div>' +
        '<div class="reason-line"><span class="reason-arrow">&rarr;</span> decision: extend to preserve work</div>' +
        '<div class="reason-line reason-action"><span class="reason-arrow">&rarr;</span> action: click "Extend session"</div>' +
      "</div>"
    );
  }

  /* ---------------------------------------------------------- */
  /* Shared fragments — s2 diagram and s7 audit table             */
  /* ---------------------------------------------------------- */

  /** s2 — AI agent -> MCP -> WorkSpace diagram (inline SVG). */
  function solutionSvg() {
    return (
      '<svg viewBox="0 0 1050 380" width="1050" height="380" role="img" ' +
        'aria-label="Diagram: an AI agent, reasoning with Amazon Bedrock, connects over MCP to a ' +
        'WorkSpace for Agents desktop where it sees the screen, moves the mouse, and types on the keyboard.">' +
        /* left box — the AI agent */
        '<rect x="30" y="100" width="290" height="160" rx="16" fill="rgba(255,255,255,0.06)" ' +
          'stroke="rgba(255,255,255,0.35)" stroke-width="1.5"/>' +
        '<line x1="145" y1="132" x2="175" y2="120" stroke="#ec7211" stroke-width="1.5"/>' +
        '<line x1="175" y1="120" x2="205" y2="132" stroke="#ec7211" stroke-width="1.5"/>' +
        '<line x1="145" y1="132" x2="205" y2="132" stroke="#ec7211" stroke-width="1.5"/>' +
        '<circle cx="145" cy="132" r="5" fill="#ec7211"/>' +
        '<circle cx="175" cy="120" r="5" fill="#ec7211"/>' +
        '<circle cx="205" cy="132" r="5" fill="#ec7211"/>' +
        '<text x="175" y="185" text-anchor="middle" font-size="26" font-weight="700" fill="#ffffff">AI agent</text>' +
        '<text x="175" y="214" text-anchor="middle" font-size="14" fill="#d5dbdb">Amazon Bedrock &mdash; reasoning</text>' +
        /* arrow labeled MCP */
        '<line x1="320" y1="180" x2="664" y2="180" stroke="#d5dbdb" stroke-width="2.5"/>' +
        '<polygon points="682,180 662,171 662,189" fill="#d5dbdb"/>' +
        '<text x="495" y="160" text-anchor="middle" font-size="16" font-weight="700" fill="#ec7211" ' +
          'font-family="Consolas, Monaco, monospace">MCP</text>' +
        '<text x="495" y="226" text-anchor="middle" font-size="14" fill="#b9c2d0">sees the screen</text>' +
        '<text x="495" y="251" text-anchor="middle" font-size="14" fill="#b9c2d0">moves the mouse</text>' +
        '<text x="495" y="276" text-anchor="middle" font-size="14" fill="#b9c2d0">types on the keyboard</text>' +
        /* right box — mini desktop window */
        '<rect x="690" y="88" width="330" height="200" rx="10" fill="#10141c" ' +
          'stroke="rgba(255,255,255,0.35)" stroke-width="1.5"/>' +
        '<path d="M690 116 v-18 a10 10 0 0 1 10 -10 h310 a10 10 0 0 1 10 10 v18 z" fill="#232f3e"/>' +
        '<circle cx="708" cy="102" r="3.5" fill="#87919b"/>' +
        '<circle cx="720" cy="102" r="3.5" fill="#87919b"/>' +
        '<circle cx="732" cy="102" r="3.5" fill="#87919b"/>' +
        '<text x="860" y="106" text-anchor="middle" font-size="11" fill="#d5dbdb">Amazon DCV &middot; WSAMZN-AGENT-07</text>' +
        '<rect x="698" y="124" width="314" height="156" rx="6" fill="#0f4c81"/>' +
        '<rect x="698" y="262" width="314" height="18" rx="4" fill="rgba(16,20,28,0.85)"/>' +
        '<rect x="714" y="140" width="170" height="104" rx="5" fill="#ffffff"/>' +
        '<rect x="714" y="140" width="170" height="18" rx="5" fill="#e9ebed"/>' +
        '<rect x="724" y="168" width="110" height="8" rx="2" fill="#d5dbdb"/>' +
        '<rect x="724" y="184" width="140" height="8" rx="2" fill="#eaeded"/>' +
        '<rect x="724" y="200" width="140" height="8" rx="2" fill="#eaeded"/>' +
        '<rect x="724" y="222" width="52" height="12" rx="2" fill="#ec7211"/>' +
        '<path d="M905 170 L905 216 L917 205 L924 221 L931 218 L924 202 L940 202 Z" ' +
          'fill="#ffffff" stroke="#16191f" stroke-width="2"/>' +
        '<text x="855" y="322" text-anchor="middle" font-size="18" font-weight="700" fill="#ffffff">' +
          "WorkSpace for Agents</text>" +
      "</svg>"
    );
  }

  /** s7 — small gray screen-capture thumbnail (inline SVG). */
  function capThumb(variant) {
    var inner;
    if (variant === "dialog") {
      inner = '<rect x="17" y="9" width="22" height="14" rx="2" fill="#fafafa" stroke="#aab7b8"/>';
    } else if (variant === "form") {
      inner = '<rect x="8" y="8" width="24" height="4" rx="1" fill="#fafafa"/>' +
              '<rect x="8" y="16" width="40" height="4" rx="1" fill="#fafafa"/>' +
              '<rect x="8" y="24" width="40" height="4" rx="1" fill="#fafafa"/>';
    } else {
      inner = '<rect x="8" y="7" width="40" height="4" rx="1" fill="#fafafa"/>' +
              '<rect x="8" y="14" width="40" height="4" rx="1" fill="#fafafa"/>' +
              '<rect x="8" y="21" width="28" height="4" rx="1" fill="#fafafa"/>';
    }
    return (
      '<svg class="cap-thumb" viewBox="0 0 56 32" width="56" height="32" role="img" aria-label="Screen capture">' +
        '<rect x="0.5" y="0.5" width="55" height="31" rx="3" fill="#d5dbdb" stroke="#aab7b8"/>' +
        inner +
      "</svg>"
    );
  }

  function auditRow(time, variant, action, reasoning) {
    return (
      '<tr><td class="audit-time">' + time + "</td>" +
      "<td>" + capThumb(variant) + "</td>" +
      '<td class="audit-action">' + action + "</td>" +
      "<td>" + reasoning + "</td></tr>"
    );
  }

  /* ---------------------------------------------------------- */
  /* Chapter styles (every rule prefixed with .ch9)               */
  /* ---------------------------------------------------------- */

  var STYLES =
    "/* --- s1: legacy-app vignettes --- */\n" +
    ".ch9 .vig { height: 118px; border-radius: 4px; overflow: hidden; margin: 6px 0 12px; }\n" +
    ".ch9 .vig-term { background: #0a0f0a; color: #33ff66; font-family: var(--font-mono); " +
      "font-size: 11px; line-height: 1.7; padding: 10px 12px; white-space: pre; }\n" +
    ".ch9 .vig-erp { background: #dfe3e6; border: 1px solid #c4cacd; padding: 10px 12px; " +
      "font-size: 11px; color: #3a4148; }\n" +
    ".ch9 .erp-title { font-weight: 700; border-bottom: 1px solid #c4cacd; padding-bottom: 4px; margin-bottom: 8px; }\n" +
    ".ch9 .erp-row { display: flex; align-items: center; gap: 8px; margin-bottom: 7px; }\n" +
    ".ch9 .erp-row span { width: 74px; flex: none; }\n" +
    ".ch9 .erp-row i { flex: 1; height: 15px; background: #f4f5f6; border: 1px solid #aab2b8; }\n" +
    ".ch9 .vig-portal { background: #ffffff; border: 1px solid #c4cacd; }\n" +
    ".ch9 .pbar { background: #e9ebed; font-size: 10.5px; color: #545b64; padding: 5px 10px; " +
      "border-bottom: 1px solid #d5dbdb; }\n" +
    ".ch9 .pbody { padding: 12px; }\n" +
    ".ch9 .pfield { display: block; height: 15px; background: #f4f5f6; border: 1px solid #aab2b8; " +
      "border-radius: 2px; margin-bottom: 9px; }\n" +
    ".ch9 .pbtn { display: inline-block; background: var(--color-link); color: #ffffff; " +
      "font-size: 11px; font-weight: 700; padding: 3px 14px; border-radius: 2px; }\n" +

    "/* --- s3-s5: agent action ticker --- */\n" +
    ".ch9 .agent-ticker { position: absolute; top: 52px; right: 24px; width: 380px; background: #16191f; " +
      "border: 1px solid rgba(255,255,255,0.18); border-radius: 8px; padding: 14px 16px 12px; " +
      "color: #d5dbdb; font-size: 13px; z-index: 22; box-shadow: 0 10px 32px rgba(0,0,0,0.4); }\n" +
    ".ch9 .ticker-title { font-size: 12px; font-weight: 700; color: #ffffff; text-transform: uppercase; " +
      "letter-spacing: 0.5px; padding-bottom: 8px; margin-bottom: 8px; " +
      "border-bottom: 1px solid rgba(255,255,255,0.14); }\n" +
    ".ch9 .tick-row { display: flex; gap: 10px; padding: 5px 8px; border-left: 3px solid transparent; }\n" +
    ".ch9 .tick-time { font-family: var(--font-mono); font-size: 12px; color: #8b949e; flex: none; padding-top: 1px; }\n" +
    ".ch9 .tick-text { min-width: 0; }\n" +
    ".ch9 .tick-active { border-left-color: var(--color-accent); background: rgba(236,114,17,0.12); }\n" +
    ".ch9 .tick-active .tick-text { color: #ffffff; font-weight: 700; }\n" +

    "/* --- s3-s5: claims portal window --- */\n" +
    ".ch9 .portal { display: flex; flex-direction: column; height: 100%; background: var(--color-bg); }\n" +
    ".ch9 .portal-head { flex: none; height: 46px; background: var(--color-header); color: #ffffff; " +
      "display: flex; align-items: center; gap: 14px; padding: 0 18px; font-size: 13.5px; }\n" +
    ".ch9 .portal-brand { font-weight: 700; }\n" +
    ".ch9 .portal-user { margin-left: auto; color: #d5dbdb; }\n" +
    ".ch9 .portal-user strong { color: #ffffff; font-family: var(--font-mono); font-size: 12.5px; }\n" +
    ".ch9 .portal-body { flex: 1; min-height: 0; padding: 14px 18px; overflow: hidden; }\n" +
    ".ch9 .portal-crumb { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 6px; }\n" +
    ".ch9 .portal-body h3 { font-size: 17px; font-weight: 700; }\n" +
    ".ch9 .portal-sub { font-size: 12.5px; color: var(--color-text-secondary); margin: 2px 0 12px; }\n" +

    "/* --- s4/s5: claim intake form --- */\n" +
    ".ch9 .claim-form { background: var(--color-surface); border: 1px solid var(--color-border); " +
      "border-radius: 2px; box-shadow: 0 1px 1px rgba(0,28,36,0.15); padding: 16px 18px; }\n" +
    ".ch9 .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 20px; }\n" +
    ".ch9 .form-wide { margin-top: 14px; }\n" +
    ".ch9 .field-area { height: 68px; }\n" +
    ".ch9 .type-caret { display: inline-block; width: 2px; height: 15px; background: var(--color-link); " +
      "vertical-align: -2px; margin-left: 1px; }\n" +
    ".ch9 .form-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 14px; }\n" +

    "/* --- s5: dialog scene --- */\n" +
    ".ch9 .surface-scrim { position: absolute; inset: 0; background: rgba(13,20,33,0.45); z-index: 15; }\n" +
    ".ch9 .agent-dialog { left: 600px; top: 318px; }\n" +
    ".ch9 .reason-card { position: absolute; left: 234px; top: 322px; width: 322px; background: #16191f; " +
      "border: 1px solid rgba(255,255,255,0.18); border-radius: 8px; padding: 14px 16px; color: #d5dbdb; " +
      "font-size: 13px; z-index: 40; box-shadow: 0 10px 32px rgba(0,0,0,0.4); }\n" +
    ".ch9 .reason-title { font-size: 12px; font-weight: 700; color: #ffffff; text-transform: uppercase; " +
      "letter-spacing: 0.5px; margin-bottom: 8px; }\n" +
    ".ch9 .reason-line { font-family: var(--font-mono); font-size: 12.5px; line-height: 1.9; }\n" +
    ".ch9 .reason-arrow { color: #8b949e; margin-right: 4px; }\n" +
    ".ch9 .reason-action { color: var(--color-accent); font-weight: 700; }\n" +

    "/* --- s6: task definition console --- */\n" +
    ".ch9 .task-def { max-width: 880px; min-height: 74px; background: #ffffff; border: 1px solid #aab7b8; " +
      "border-radius: 2px; padding: 10px 12px; font-size: 14px; line-height: 1.55; }\n" +
    ".ch9 .task-def-foot { display: flex; align-items: center; gap: 16px; margin-top: 12px; max-width: 880px; }\n" +
    ".ch9 .task-def-foot .btn-primary { margin-left: auto; }\n" +
    ".ch9 .queue-head { font-size: 17px; font-weight: 700; margin: 20px 0 10px; }\n" +

    "/* --- s7: audit log --- */\n" +
    ".ch9 .audit-stats { max-width: 980px; margin-bottom: 16px; }\n" +
    ".ch9 .audit-wrap { max-width: 1180px; }\n" +
    ".ch9 .audit-time { font-family: var(--font-mono); font-size: 12.5px; white-space: nowrap; }\n" +
    ".ch9 .audit-action { font-family: var(--font-mono); font-size: 12.5px; }\n" +
    ".ch9 .cap-thumb { display: block; }\n" +
    ".ch9 .audit-foot { padding: 10px 14px; font-size: 12.5px; color: var(--color-text-secondary); " +
      "background: #fafafa; border-top: 1px solid var(--color-border); }\n" +

    "/* --- s8: cost model page --- */\n" +
    ".ch9 .cost-page { height: 100%; background: var(--color-surface); padding: 92px 120px; }\n" +
    ".ch9 .cost-kicker { color: var(--color-accent); text-transform: uppercase; letter-spacing: 1.2px; " +
      "font-size: 13px; font-weight: 700; margin-bottom: 10px; }\n" +
    ".ch9 .cost-title { font-size: 40px; font-weight: 300; margin-bottom: 8px; }\n" +
    ".ch9 .cost-sub { font-size: 16px; color: var(--color-text-secondary); margin-bottom: 34px; }\n" +
    ".ch9 .timeline { display: flex; gap: 6px; height: 86px; max-width: 1300px; margin-bottom: 34px; }\n" +
    ".ch9 .tl-seg { border-radius: 6px; display: flex; flex-direction: column; justify-content: center; " +
      "gap: 3px; padding: 0 14px; overflow: hidden; }\n" +
    ".ch9 .tl-name { font-weight: 700; font-size: 14px; white-space: nowrap; }\n" +
    ".ch9 .tl-time { font-size: 12px; font-family: var(--font-mono); white-space: nowrap; }\n" +
    ".ch9 .tl-up { width: 9%; }\n" +
    ".ch9 .tl-down { width: 9%; }\n" +
    ".ch9 .tl-run { width: 36%; }\n" +
    ".ch9 .tl-gray { background: #e4e7e9; border: 1px solid #d0d5d8; color: var(--color-text-secondary); }\n" +
    ".ch9 .tl-accent { background: var(--color-accent); color: #16191f; }\n" +
    ".ch9 .tl-accent .tl-name { font-size: 16px; }\n" +
    ".ch9 .tl-accent .tl-time { color: rgba(22,25,31,0.75); }\n" +
    ".ch9 .tl-idle { flex: 1; border: 2px dashed #aab7b8; background: transparent; " +
      "color: var(--color-text-secondary); }\n" +
    ".ch9 .cost-stats { max-width: 1300px; }\n" +
    ".ch9 .cost-note { margin-top: 30px; font-size: 15px; color: var(--color-text-secondary); }\n";

  /* ---------------------------------------------------------- */
  /* Chapter registration                                         */
  /* ---------------------------------------------------------- */

  DEMO.registerChapter({
    id: "ch9",
    act: 3,
    number: 9,
    title: "WorkSpaces for Agents",
    hook: "What if your AI agent had its own desktop — and could use it like a human would?",
    talkingPoints: [
      'Solves the "last mile" automation problem for GUI-only apps',
      "More resilient than traditional RPA — it understands intent, not just pixel coordinates",
      "Inherits all WorkSpaces security: encryption, isolation, no data on endpoints",
      "Pairs with Amazon Bedrock for the AI reasoning layer"
    ],
    styles: STYLES,
    steps: [

      /* s1 — the problem: legacy apps with no API */
      {
        id: "s1",
        screen: function () {
          return DEMO.frames.slide(
            '<p class="slide-kicker">The automation gap</p>' +
            '<p class="slide-stat">80%</p>' +
            '<h2 class="slide-title">of enterprise software still has no API</h2>' +
            '<p class="slide-sub">You can&rsquo;t automate what you can&rsquo;t call programmatically.</p>' +
            '<div class="slide-row">' +
              '<div class="slide-card">' +
                '<span class="slide-card-kicker">Mainframe green screen</span>' +
                '<div class="vig vig-term" aria-hidden="true">' +
                  "<div>CLAIMS INQUIRY        CICS01</div>" +
                  "<div>ENTER CLAIM NO: ________</div>" +
                  "<div>ACTION: _   (A=ADJ  B=PAY)</div>" +
                  "<div>STATUS: 4 PENDING</div>" +
                  "<div>PF3=EXIT   PF5=REFRESH</div>" +
                "</div>" +
                "<p>Terminal emulation only &mdash; no service layer to call.</p>" +
              "</div>" +
              '<div class="slide-card">' +
                '<span class="slide-card-kicker">Thick-client ERP</span>' +
                '<div class="vig vig-erp" aria-hidden="true">' +
                  '<div class="erp-title">AP Invoice Entry</div>' +
                  '<div class="erp-row"><span>Vendor</span><i></i></div>' +
                  '<div class="erp-row"><span>PO number</span><i></i></div>' +
                  '<div class="erp-row"><span>Amount</span><i></i></div>' +
                "</div>" +
                "<p>Desktop-only client &mdash; screens, not services.</p>" +
              "</div>" +
              '<div class="slide-card">' +
                '<span class="slide-card-kicker">Internal web portal</span>' +
                '<div class="vig vig-portal" aria-hidden="true">' +
                  '<div class="pbar">intranet/claims</div>' +
                  '<div class="pbody">' +
                    '<i class="pfield"></i>' +
                    '<i class="pfield"></i>' +
                    '<span class="pbtn">Submit</span>' +
                  "</div>" +
                "</div>" +
                "<p>Built for humans in a browser &mdash; nothing to integrate with.</p>" +
              "</div>" +
            "</div>"
          );
        },
        tooltip: "80% of enterprise software still has no API — you can't automate what you can't call programmatically.",
        advance: "next",
        placement: "bottom"
      },

      /* s2 — the solution: give the agent a desktop */
      {
        id: "s2",
        screen: function () {
          return DEMO.frames.slide(
            '<p class="slide-kicker">The solution</p>' +
            '<h2 class="slide-title">Give the agent a desktop</h2>' +
            '<div class="slide-diagram">' + solutionSvg() + "</div>"
          );
        },
        tooltip: "WorkSpaces for Agents provisions a full cloud desktop for an AI agent — it sees the screen, moves the mouse, types on the keyboard.",
        advance: "next",
        placement: "bottom"
      },

      /* s3 — agent launches the claims portal */
      {
        id: "s3",
        screen: function () {
          return DEMO.frames.desktopFrame(
            { name: "WSAMZN-AGENT-07", clock: "2:01 PM" },
            portalWindow(queueBody()) +
            ticker([
              { t: "14:01:12", text: "Opening Claims Portal" },
              { t: "14:01:19", text: "Authenticating as svc-claims-bot" },
              { t: "14:01:31", text: "Navigating to Pending queue" }
            ], true)
          );
        },
        tooltip: "The agent navigates to an internal portal, logs in, and begins executing a multi-step workflow.",
        advance: "next",
        target: '[data-hotspot="ticker"]',
        placement: "left"
      },

      /* s4 — agent fills out the claim form */
      {
        id: "s4",
        screen: function () {
          return DEMO.frames.desktopFrame(
            { name: "WSAMZN-AGENT-07", clock: "2:01 PM" },
            portalWindow(claimFormBody({ hotspot: true })) +
            ticker([
              { t: "14:01:31", text: "Opening claim CLM-20841" },
              { t: "14:01:39", text: "Extracting fields from invoice PDF" },
              { t: "14:01:47", text: "Filling claim form &mdash; field 4 of 9" }
            ])
          );
        },
        tooltip: "No RPA scripts to maintain — the agent understands context and adapts to UI changes.",
        advance: "next",
        target: '[data-hotspot="claim-form"]',
        placement: "left"
      },

      /* s5 — agent handles an unexpected dialog */
      {
        id: "s5",
        screen: function () {
          return DEMO.frames.desktopFrame(
            { name: "WSAMZN-AGENT-07", clock: "2:02 PM" },
            portalWindow(claimFormBody({ dateDone: true })) +
            '<div class="surface-scrim"></div>' +
            ticker([
              { t: "14:01:47", text: "Filling claim form &mdash; field 4 of 9" },
              { t: "14:01:56", text: "Typing amount $1,284.00" },
              { t: "14:02:08", text: "Handling unexpected dialog" }
            ]) +
            reasonCard() +
            sessionDialog()
          );
        },
        tooltip: "Unexpected popup? The agent reads it, reasons about it, and takes appropriate action.",
        advance: "next",
        target: '[data-hotspot="dialog"]',
        placement: "right"
      },

      /* s6 — orchestration: tasks in natural language */
      {
        id: "s6",
        screen: function () {
          return DEMO.frames.consoleFrame(
            {
              service: "WorkSpaces for Agents",
              breadcrumbs: "WorkSpaces for Agents &rsaquo; Tasks",
              sidenav: [{ label: "Tasks", active: true }, "Agents", "Sessions", "Audit log"]
            },
            '<h1 class="page-title">Tasks</h1>' +
            '<p class="page-desc">Define work in natural language. Agents plan the steps and execute them ' +
              "on their own WorkSpaces.</p>" +
            '<div class="console-card">' +
              "<h2>Create task</h2>" +
              '<span class="field-label">Task definition (natural language)</span>' +
              '<div class="task-def" data-hotspot="task-def">Process this week&rsquo;s invoices in SAP: ' +
                "validate totals against the PO, post approved entries, and flag mismatches for review.</div>" +
              '<div class="task-def-foot">' +
                '<span class="u-small u-muted">No selectors. No scripts. The agent plans the steps.</span>' +
                '<span class="btn-primary">Create task</span>' +
              "</div>" +
            "</div>" +
            '<h2 class="queue-head">Task queue</h2>' +
            '<div class="table-wrap"><table class="console-table">' +
              "<thead><tr><th>Task</th><th>Name</th><th>Agent desktop</th><th>Status</th><th>Duration</th></tr></thead>" +
              "<tbody>" +
                "<tr><td>#1042</td><td>Claims intake</td><td>WSAMZN-AGENT-07</td>" +
                  '<td><span class="badge badge-in-progress">Running</span></td><td>2 min elapsed</td></tr>' +
                "<tr><td>#1041</td><td>Invoice posting</td><td>WSAMZN-AGENT-04</td>" +
                  '<td><span class="badge badge-launched">Completed</span></td><td>14 min</td></tr>' +
                "<tr><td>#1040</td><td>Vendor onboarding</td><td>WSAMZN-AGENT-02</td>" +
                  '<td><span class="badge badge-launched">Completed</span></td><td>22 min</td></tr>' +
              "</tbody>" +
            "</table></div>"
          );
        },
        tooltip: "Define tasks in natural language — 'Process these invoices in SAP' — not brittle XPath selectors.",
        advance: "next",
        target: '[data-hotspot="task-def"]',
        placement: "bottom"
      },

      /* s7 — observability: the agent action audit log */
      {
        id: "s7",
        screen: function () {
          return DEMO.frames.consoleFrame(
            {
              service: "WorkSpaces for Agents",
              breadcrumbs: "WorkSpaces for Agents &rsaquo; Audit log &rsaquo; Task #1042",
              sidenav: ["Tasks", "Agents", "Sessions", { label: "Audit log", active: true }]
            },
            '<h1 class="page-title">Audit log</h1>' +
            '<p class="page-desc">Task #1042 &middot; Claims intake &middot; Agent desktop WSAMZN-AGENT-07 ' +
              "&middot; August 18, 2026</p>" +
            '<div class="stat-row audit-stats">' +
              '<div class="stat-widget"><div class="stat-value">38</div>' +
                '<div class="stat-label">Actions logged</div></div>' +
              '<div class="stat-widget"><div class="stat-value">38</div>' +
                '<div class="stat-label">Screen captures retained</div></div>' +
              '<div class="stat-widget"><div class="stat-value">1</div>' +
                '<div class="stat-label">Exception handled &mdash; session dialog</div></div>' +
            "</div>" +
            '<div class="table-wrap audit-wrap" data-hotspot="audit-table">' +
              '<table class="console-table">' +
                "<thead><tr><th>Time</th><th>Capture</th><th>Action</th><th>Reasoning</th></tr></thead>" +
                "<tbody>" +
                  auditRow("14:02:11", "dialog", 'click "Extend session"', "Dialog would interrupt task") +
                  auditRow("14:02:08", "dialog", 'read dialog "Session expiring"', "Unexpected dialog during form fill") +
                  auditRow("14:01:56", "form", "type amount 1,284.00", "Matches invoice line 3") +
                  auditRow("14:01:44", "form", 'click field "Amount"', "Next required field in intake form") +
                  auditRow("14:01:31", "list", "open claim CLM-20841", "First item in Pending queue") +
                "</tbody>" +
              "</table>" +
              '<div class="audit-foot">Every screen capture, action, and decision &mdash; retained and queryable.</div>' +
            "</div>"
          );
        },
        tooltip: "Full audit trail: every screen capture, every action, every decision the agent made.",
        advance: "next",
        target: '[data-hotspot="audit-table"]',
        placement: "top"
      },

      /* s8 — cost model: pay only for execution time */
      {
        id: "s8",
        screen: function () {
          return (
            '<div class="cost-page">' +
              '<p class="cost-kicker">Cost model</p>' +
              '<h1 class="cost-title">Pay only for execution time</h1>' +
              '<p class="cost-sub">One agent task &mdash; claims intake, August 18, 2026</p>' +
              '<div class="timeline" data-hotspot="timeline">' +
                '<div class="tl-seg tl-gray tl-up"><span class="tl-name">Spin up</span>' +
                  '<span class="tl-time">0:00&ndash;0:02</span></div>' +
                '<div class="tl-seg tl-accent tl-run"><span class="tl-name">Task runs &mdash; 14 min</span>' +
                  '<span class="tl-time">0:02&ndash;0:16</span></div>' +
                '<div class="tl-seg tl-gray tl-down"><span class="tl-name">Spin down</span>' +
                  '<span class="tl-time">0:16</span></div>' +
                '<div class="tl-seg tl-idle"><span class="tl-name">Idle &mdash; $0</span>' +
                  '<span class="tl-time">rest of day</span></div>' +
              "</div>" +
              '<div class="stat-row cost-stats">' +
                '<div class="stat-widget"><div class="stat-value">$0.19</div>' +
                  '<div class="stat-label">This task &mdash; 14 minutes of execution</div></div>' +
                '<div class="stat-widget"><div class="stat-value">$47</div>' +
                  '<div class="stat-label">24/7 desktop equivalent &mdash; per month</div></div>' +
                '<div class="stat-widget"><div class="stat-value">3.2</div>' +
                  '<div class="stat-label">Fleet average &mdash; agent-hours per day</div></div>' +
              "</div>" +
              '<p class="cost-note">Agents do not need desktops 24/7 &mdash; provision on task start, ' +
                "terminate on completion.</p>" +
            "</div>"
          );
        },
        tooltip: "Agents don't need desktops 24/7 — spin up for the task, spin down when done.",
        advance: "next",
        target: '[data-hotspot="timeline"]',
        placement: "bottom"
      }
    ]
  });
})();
