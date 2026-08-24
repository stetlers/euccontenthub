/* ============================================================
   Amazon WorkSpaces: From Zero to Agentic — re:Invent 2026 demo
   ch4.js — Chapter 4: The End-User Experience (Act 1)

   Chapter content file. Registers itself via DEMO.registerChapter
   at parse time and does nothing else (no DOM access at parse
   time; screen functions run only when rendered inside the
   1600x900 stage canvas). Uses DEMO.frames.* scaffolding and
   theme.css components; all chapter CSS is prefixed with .ch4.

   Persona: Martha Major (mmajor@corp.example.com)
   Registration code WSpdx+ABC123 · WorkSpace WSAMZN-MMAJOR
   ============================================================ */

(function () {
  "use strict";

  /* ---------------------------------------------------------- */
  /* Shared builders (run at render time only)                    */
  /* ---------------------------------------------------------- */

  /** Windows-11-style wallpaper bloom behind the desktop scenes. */
  function bloom() {
    return '<div class="wall-bloom" aria-hidden="true"></div>';
  }

  /** Left column of desktop icons (s4-s7 continuity). */
  function deskIcons() {
    var apps = [
      { cls: "di-pc", glyph: "PC", label: "This PC" },
      { cls: "di-outlook", glyph: "O", label: "Outlook" },
      { cls: "di-excel", glyph: "X", label: "Excel" },
      { cls: "di-code", glyph: "VS", label: "VS Code" },
      { cls: "di-figma", glyph: "F", label: "Figma" }
    ];
    var out = apps.map(function (a) {
      return (
        '<div class="desk-icon">' +
          '<span class="di ' + a.cls + '">' + a.glyph + "</span>" +
          a.label +
        "</div>"
      );
    }).join("");
    return '<div class="desk-icons">' + out + "</div>";
  }

  /** Inbox list entry. */
  function mailItem(cls, from, when, subject) {
    return (
      '<div class="mail-item' + (cls ? " " + cls : "") + '">' +
        '<span class="mail-from">' + from +
          '<span class="mail-when">' + when + "</span></span>" +
        subject +
      "</div>"
    );
  }

  /** Client download card (s2). */
  function clientCard(opts) {
    return (
      '<div class="console-card client-card' + (opts.featured ? " card-featured" : "") + '"' +
        (opts.hotspot ? ' data-hotspot="' + opts.hotspot + '"' : "") + ">" +
        '<span class="client-ico ' + opts.ico + '">' + opts.glyph + "</span>" +
        "<h3>" + opts.name + "</h3>" +
        "<p>" + opts.desc + "</p>" +
        '<span class="' + (opts.primary ? "btn-primary" : "btn-secondary") + '">' +
          opts.btn + "</span>" +
      "</div>"
    );
  }

  /** Labeled, pre-filled field on the sign-in card (s3). */
  function authField(label, value) {
    return (
      '<span class="field-label">' + label + "</span>" +
      '<div class="field-box field-filled">' + value + "</div>"
    );
  }

  /** Numbered monitor rectangle in the arrangement diagram (s5). */
  function mon(num, primary) {
    return (
      '<div class="mon' + (primary ? " mon-primary" : "") + '">' + num +
        (primary ? '<span class="mon-tag">Primary</span>' : "") +
      "</div>"
    );
  }

  /** Display-settings detail row (s5). */
  function dispRow(label, value) {
    return (
      '<div class="disp-row"><strong>' + label + "</strong>" +
        "<span>" + value + "</span></div>"
    );
  }

  /** Redirected-device row in the DCV Devices menu (s6). */
  function deviceRow(glyph, cls, name, state) {
    return (
      '<div class="menu-row">' +
        '<span class="dev-ico ' + cls + '">' + glyph + "</span>" +
        "<span>" + name + "</span>" +
        '<span class="row-state chip-ok">' + state + "</span>" +
      "</div>"
    );
  }

  /** Connection-health HUD row (s7). */
  function hudRow(label, value) {
    return (
      '<div class="hud-row"><span>' + label + "</span>" +
        '<span class="hud-value">' + value + "</span></div>"
    );
  }

  /** Paused-video overlay glyph (s7, inline SVG). */
  function playSvg() {
    return (
      '<svg viewBox="0 0 96 96" width="96" height="96" role="img" aria-label="Video playback overlay">' +
        '<circle cx="48" cy="48" r="44" fill="rgba(255,255,255,0.14)" ' +
          'stroke="rgba(255,255,255,0.5)" stroke-width="2"/>' +
        '<polygon points="40,32 68,48 40,64" fill="#ffffff"/>' +
      "</svg>"
    );
  }

  /* ---------------------------------------------------------- */
  /* Screens                                                      */
  /* ---------------------------------------------------------- */

  /* s1 — invitation email in Martha's corporate inbox. */
  function screenS1() {
    return DEMO.frames.browserFrame(
      { url: "https://mail.corp.example.com/inbox" },
      '<div class="webmail">' +
        '<div class="mail-list">' +
          '<div class="mail-list-head">Inbox &mdash; mmajor@corp.example.com</div>' +
          mailItem("active unread", "Amazon WorkSpaces", "9:02 AM", "Your WorkSpace is ready") +
          mailItem("", "IT Communications", "8:41 AM", "Scheduled maintenance this weekend") +
          mailItem("", "Corp Payroll", "8:15 AM", "Your August payslip is available") +
          mailItem("", "Facilities", "Yesterday", "Parking garage access update") +
        "</div>" +
        '<div class="mail-read">' +
          '<h1 class="mail-subject">Your WorkSpace is ready</h1>' +
          '<p class="mail-meta">Amazon WorkSpaces &lt;no-reply@notify.workspaces.aws&gt; ' +
            "&middot; to mmajor@corp.example.com &middot; Tuesday, August 18, 2026, 9:02 AM</p>" +
          '<div class="mail-body">' +
            "<p>Hello Martha,</p>" +
            "<p>Your administrator at example-corp has created an Amazon WorkSpace for you " +
              "&mdash; a personal cloud desktop you can reach from any device. Keep your " +
              "registration code handy; you will enter it the first time you connect.</p>" +
            '<p class="field-label">Your registration code</p>' +
            '<div class="reg-code">WSpdx+ABC123</div>' +
            '<p><span class="btn-primary reg-btn" data-hotspot="reg-link">' +
              "Get started with your WorkSpace</span></p>" +
            '<p class="mail-foot">Sent by Amazon WorkSpaces on behalf of example-corp IT. ' +
              "Setup takes about two minutes &mdash; no helpdesk ticket required.</p>" +
          "</div>" +
        "</div>" +
      "</div>"
    );
  }

  /* s2 — client download page with the Web Access option. */
  function screenS2() {
    return DEMO.frames.browserFrame(
      { url: "https://clients.amazonworkspaces.com" },
      '<div class="clients-page">' +
        '<h1 class="clients-title">Amazon WorkSpaces clients</h1>' +
        '<p class="clients-sub">Choose how you want to connect &mdash; install a native client, ' +
          "or run WorkSpaces straight from your browser.</p>" +
        '<div class="grid-3 clients-grid">' +
          clientCard({
            ico: "ico-win", glyph: "WIN", name: "Windows",
            desc: "Native 64-bit client for Windows 10 and 11, with full multi-monitor and USB support.",
            btn: "Download 64-bit client"
          }) +
          clientCard({
            ico: "ico-mac", glyph: "MAC", name: "macOS",
            desc: "Universal client for Apple silicon and Intel Macs.",
            btn: "Download client"
          }) +
          clientCard({
            ico: "ico-web", glyph: "WEB", name: "Web Access",
            desc: "No install &mdash; run it in your browser.",
            btn: "Launch Web Access",
            primary: true, featured: true, hotspot: "web-access"
          }) +
        "</div>" +
        '<p class="client-note">Also available for Linux, iPad, Android, and Chromebook.</p>' +
      "</div>"
    );
  }

  /* s3 — Web Access client sign-in. */
  function screenS3() {
    return DEMO.frames.browserFrame(
      { url: "https://clients.amazonworkspaces.com/webclient" },
      '<div class="webclient-bg">' +
        '<div class="auth-card">' +
          '<p class="auth-brand">Amazon WorkSpaces</p>' +
          "<h2>Sign in to your WorkSpace</h2>" +
          authField("Registration code", "WSpdx+ABC123") +
          authField("Username", "mmajor") +
          authField("Password", "&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;") +
          '<p class="auth-note">MFA enforced by your organization</p>' +
          '<span class="btn-primary auth-btn" data-hotspot="sign-in">Sign in</span>' +
        "</div>" +
      "</div>"
    );
  }

  /* s4 — connected: a clean Windows desktop streamed over DCV. */
  function screenS4() {
    return DEMO.frames.desktopFrame(
      { clock: "9:06 AM" },
      bloom() +
      deskIcons() +
      '<span class="dcv-chip" data-hotspot="dcv-chip"><i class="live-dot"></i>' +
        "Streaming via Amazon DCV &mdash; up to 4K</span>"
    );
  }

  /* s5 — display settings: three-monitor arrangement. */
  function screenS5() {
    return DEMO.frames.desktopFrame(
      { clock: "9:08 AM" },
      bloom() +
      deskIcons() +
      DEMO.frames.appWindow(
        { title: "Settings &mdash; Display", x: 320, y: 120, w: 940, h: 560 },
        '<div class="settings">' +
          '<div class="settings-side">' +
            '<div class="settings-user"><span class="settings-avatar">MM</span>Martha Major</div>' +
            "<ul>" +
              '<li class="active">System</li>' +
              "<li>Bluetooth &amp; devices</li>" +
              "<li>Network &amp; internet</li>" +
              "<li>Personalization</li>" +
              "<li>Apps</li>" +
            "</ul>" +
          "</div>" +
          '<div class="settings-main">' +
            "<h3>Display</h3>" +
            '<p class="settings-sub">Select a display to change its settings, or drag displays to rearrange them.</p>' +
            '<div class="mon-arrange" data-hotspot="monitors">' +
              mon(1, false) + mon(2, true) + mon(3, false) +
            "</div>" +
            '<div class="mon-controls">' +
              '<span class="btn-secondary">Identify</span>' +
              '<span class="mon-select">Extend these displays<i>&#9662;</i></span>' +
            "</div>" +
            '<p class="mon-caption">Up to 4 monitors supported (4 x 4K)</p>' +
            dispRow("Scale", "150% (Recommended)") +
            dispRow("Display resolution", "3840 &times; 2160 (Recommended)") +
          "</div>" +
        "</div>"
      )
    );
  }

  /* s6 — DCV Devices menu: redirected peripherals. */
  function screenS6() {
    return DEMO.frames.desktopFrame(
      {
        clock: "9:09 AM",
        items: [
          { label: "Display" },
          { label: "Devices", active: true },
          { label: "Clipboard" },
          { label: "Settings" }
        ]
      },
      bloom() +
      deskIcons() +
      '<div class="dcv-menu" style="left:640px" data-hotspot="devices-menu">' +
        '<div class="menu-head">Devices</div>' +
        deviceRow("CAM", "dev-cam", "Logitech C920 webcam", "Connected") +
        deviceRow("AUD", "dev-aud", "Jabra Evolve2 headset", "Connected") +
        deviceRow("SC", "dev-sc", "Smart card reader", "Redirected") +
        '<div class="menu-note">Peripherals are redirected over the encrypted DCV stream.</div>' +
      "</div>"
    );
  }

  /* s7 — performance metrics overlay while 4K media plays. */
  function screenS7() {
    return DEMO.frames.desktopFrame(
      { clock: "9:11 AM" },
      bloom() +
      deskIcons() +
      DEMO.frames.appWindow(
        { title: "Media Player &mdash; Keynote_4K.mp4", iconClass: "icon-accent", x: 180, y: 130, w: 820, h: 520 },
        '<div class="media-body">' +
          playSvg() +
          '<div class="play-bar">' +
            "<span>12:41 / 33:05</span>" +
            '<span class="play-track"><i></i></span>' +
            "<span>4K UHD</span>" +
          "</div>" +
        "</div>"
      ) +
      '<div class="metrics-hud" data-hotspot="hud">' +
        '<div class="hud-title">Connection health</div>' +
        hudRow("Latency", "18 ms") +
        hudRow("Frame rate", "60 fps") +
        hudRow("Resolution", "3840x2160") +
        hudRow("Packet loss", "0.0%") +
        hudRow("Bandwidth", "Adaptive") +
      "</div>"
    );
  }

  /* ---------------------------------------------------------- */
  /* Chapter styles (every rule prefixed with .ch4)               */
  /* ---------------------------------------------------------- */

  var STYLES =
    "/* --- s1: webmail --- */\n" +
    ".ch4 .mail-when { float: right; font-weight: 400; font-size: 11.5px; color: var(--color-text-secondary); }\n" +
    ".ch4 .mail-body { font-size: 14px; max-width: 640px; }\n" +
    ".ch4 .mail-body p { margin: 0 0 12px; }\n" +
    ".ch4 .mail-body .field-label { margin-top: 6px; }\n" +
    ".ch4 .reg-code { display: inline-block; font-family: var(--font-mono); font-size: 17px; " +
      "letter-spacing: 1px; background: #f2f3f3; border: 1px dashed #aab7b8; border-radius: 4px; " +
      "padding: 7px 16px; margin-bottom: 14px; }\n" +
    ".ch4 .reg-btn { margin: 2px 0 6px; }\n" +
    ".ch4 .mail-foot { font-size: 12px; color: var(--color-text-secondary); " +
      "border-top: 1px solid var(--color-border); padding-top: 10px; margin-top: 16px; }\n" +

    "/* --- s2: clients page --- */\n" +
    ".ch4 .clients-page { height: 100%; background: var(--color-bg); padding: 64px 140px; " +
      "text-align: center; overflow: hidden; }\n" +
    ".ch4 .clients-title { font-size: 32px; font-weight: 300; margin-bottom: 8px; }\n" +
    ".ch4 .clients-sub { font-size: 15px; color: var(--color-text-secondary); margin-bottom: 30px; }\n" +
    ".ch4 .clients-grid { max-width: 1180px; margin: 0 auto; }\n" +
    ".ch4 .client-card { padding: 28px 24px; }\n" +
    ".ch4 .client-card.card-featured { border-color: var(--color-accent); " +
      "box-shadow: 0 0 0 1px var(--color-accent); }\n" +
    ".ch4 .client-ico { width: 52px; height: 52px; border-radius: 10px; margin: 0 auto 12px; " +
      "display: flex; align-items: center; justify-content: center; color: #ffffff; " +
      "font-size: 13px; font-weight: 700; letter-spacing: 0.5px; }\n" +
    ".ch4 .ico-win { background: #0078d4; }\n" +
    ".ch4 .ico-mac { background: #16191f; }\n" +
    ".ch4 .ico-web { background: var(--color-accent); }\n" +
    ".ch4 .client-card h3 { font-size: 17px; font-weight: 700; margin-bottom: 6px; }\n" +
    ".ch4 .client-card p { font-size: 13px; color: var(--color-text-secondary); " +
      "min-height: 40px; margin-bottom: 14px; }\n" +
    ".ch4 .client-note { margin-top: 24px; font-size: 13px; color: var(--color-text-secondary); }\n" +

    "/* --- s3: web client sign-in --- */\n" +
    ".ch4 .webclient-bg { height: 100%; overflow: hidden; " +
      "background: linear-gradient(135deg, #232f3e 0%, #17202f 60%, #101623 100%); }\n" +
    ".ch4 .auth-brand { font-size: 12px; font-weight: 700; text-transform: uppercase; " +
      "letter-spacing: 1px; color: var(--color-accent); margin-bottom: 4px; }\n" +
    ".ch4 .auth-card h2 { font-size: 20px; font-weight: 700; margin: 0 0 18px; }\n" +
    ".ch4 .auth-card .field-box { margin-bottom: 14px; }\n" +
    ".ch4 .auth-note { font-size: 12.5px; color: var(--color-text-secondary); margin: 0 0 16px; }\n" +
    ".ch4 .auth-btn { display: block; text-align: center; }\n" +

    "/* --- s4-s7: streamed desktop --- */\n" +
    ".ch4 .wall-bloom { position: absolute; left: 50%; top: 46%; transform: translate(-50%, -50%); " +
      "width: 540px; height: 540px; border-radius: 50%; z-index: 1; " +
      "background: radial-gradient(circle, rgba(76,194,255,0.32), rgba(76,194,255,0) 70%); }\n" +
    ".ch4 .desk-icons { position: absolute; left: 28px; top: 64px; z-index: 6; display: grid; gap: 20px; }\n" +
    ".ch4 .desk-icon { width: 88px; text-align: center; font-size: 12px; color: #ffffff; " +
      "text-shadow: 0 1px 3px rgba(0,0,0,0.65); }\n" +
    ".ch4 .desk-icon .di { width: 46px; height: 46px; border-radius: 9px; margin: 0 auto 6px; " +
      "display: flex; align-items: center; justify-content: center; color: #ffffff; " +
      "font-size: 13px; font-weight: 700; box-shadow: 0 3px 8px rgba(0,0,0,0.35); }\n" +
    ".ch4 .di-pc { background: linear-gradient(135deg, #67809b, #46586e); }\n" +
    ".ch4 .di-outlook { background: #0f6cbd; }\n" +
    ".ch4 .di-excel { background: #107c41; }\n" +
    ".ch4 .di-code { background: #007acc; }\n" +
    ".ch4 .di-figma { background: #a259ff; }\n" +
    ".ch4 .dcv-chip { position: absolute; left: 28px; top: 14px; z-index: 25; " +
      "display: inline-flex; align-items: center; gap: 8px; background: rgba(16,20,28,0.88); " +
      "border: 1px solid rgba(255,255,255,0.22); color: #ffffff; font-size: 12.5px; " +
      "padding: 5px 14px; border-radius: 15px; white-space: nowrap; }\n" +
    ".ch4 .dcv-chip .live-dot { width: 8px; height: 8px; border-radius: 50%; " +
      "background: #7ee787; flex: none; }\n" +

    "/* --- s5: display settings window --- */\n" +
    ".ch4 .settings { display: flex; height: 100%; font-size: 13.5px; }\n" +
    ".ch4 .settings-side { width: 220px; flex: none; background: #f7f8f9; " +
      "border-right: 1px solid var(--color-border); padding: 14px 0; overflow: hidden; }\n" +
    ".ch4 .settings-user { display: flex; align-items: center; gap: 10px; padding: 0 16px 12px; " +
      "font-size: 13px; font-weight: 700; }\n" +
    ".ch4 .settings-avatar { width: 30px; height: 30px; border-radius: 50%; " +
      "background: var(--color-link); color: #ffffff; font-size: 11px; font-weight: 700; " +
      "display: flex; align-items: center; justify-content: center; flex: none; }\n" +
    ".ch4 .settings-side ul { list-style: none; margin: 0; padding: 0; " +
      "border-top: 1px solid var(--color-border); }\n" +
    ".ch4 .settings-side li { padding: 8px 16px; font-size: 13px; " +
      "color: var(--color-text-secondary); border-left: 3px solid transparent; }\n" +
    ".ch4 .settings-side li.active { color: var(--color-text); font-weight: 700; " +
      "border-left-color: var(--color-accent); background: #eef1f4; }\n" +
    ".ch4 .settings-main { flex: 1; min-width: 0; padding: 18px 24px; overflow: hidden; }\n" +
    ".ch4 .settings-main h3 { font-size: 19px; font-weight: 700; margin-bottom: 4px; }\n" +
    ".ch4 .settings-sub { font-size: 12.5px; color: var(--color-text-secondary); margin-bottom: 14px; }\n" +
    ".ch4 .mon-arrange { display: flex; align-items: center; justify-content: center; gap: 12px; " +
      "background: #f2f3f3; border: 1px solid var(--color-border); border-radius: 6px; " +
      "padding: 22px; }\n" +
    ".ch4 .mon { width: 148px; height: 92px; border-radius: 6px; background: #dfe3e6; " +
      "border: 2px solid #aab7b8; color: var(--color-text-secondary); position: relative; " +
      "display: flex; align-items: center; justify-content: center; " +
      "font-size: 30px; font-weight: 300; }\n" +
    ".ch4 .mon-primary { background: var(--color-link); border-color: var(--color-link); " +
      "color: #ffffff; }\n" +
    ".ch4 .mon-tag { position: absolute; bottom: 6px; left: 50%; transform: translateX(-50%); " +
      "font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px; " +
      "background: rgba(255,255,255,0.24); border-radius: 8px; padding: 1px 8px; }\n" +
    ".ch4 .mon-controls { display: flex; align-items: center; gap: 12px; margin: 14px 0 6px; }\n" +
    ".ch4 .mon-select { display: inline-flex; align-items: center; height: 32px; padding: 0 12px; " +
      "background: #ffffff; border: 1px solid #aab7b8; border-radius: 2px; font-size: 13.5px; }\n" +
    ".ch4 .mon-select i { font-style: normal; margin-left: 24px; color: var(--color-text-secondary); }\n" +
    ".ch4 .mon-caption { font-size: 12.5px; color: var(--color-text-secondary); margin-bottom: 12px; }\n" +
    ".ch4 .disp-row { display: flex; justify-content: space-between; align-items: center; " +
      "border-top: 1px solid var(--color-border); padding: 11px 2px; font-size: 13.5px; }\n" +
    ".ch4 .disp-row span { color: var(--color-text-secondary); }\n" +

    "/* --- s6: DCV devices menu --- */\n" +
    ".ch4 .dcv-menu { min-width: 340px; }\n" +
    ".ch4 .dev-ico { width: 26px; height: 26px; border-radius: 5px; flex: none; " +
      "display: flex; align-items: center; justify-content: center; " +
      "font-size: 9px; font-weight: 700; color: #ffffff; }\n" +
    ".ch4 .dev-cam { background: #0073bb; }\n" +
    ".ch4 .dev-aud { background: #545b64; }\n" +
    ".ch4 .dev-sc { background: #1d8102; }\n" +
    ".ch4 .menu-note { padding: 9px 14px; font-size: 12px; color: var(--color-text-secondary); " +
      "background: #fafafa; border-top: 1px solid var(--color-border); border-radius: 0 0 4px 4px; }\n" +

    "/* --- s7: media window --- */\n" +
    ".ch4 .media-body { position: absolute; inset: 0; background: #10141c; " +
      "display: flex; align-items: center; justify-content: center; }\n" +
    ".ch4 .play-bar { position: absolute; left: 0; right: 0; bottom: 0; height: 42px; " +
      "background: rgba(22,25,31,0.85); display: flex; align-items: center; gap: 14px; " +
      "padding: 0 16px; color: #d5dbdb; font-size: 11.5px; font-family: var(--font-mono); }\n" +
    ".ch4 .play-track { flex: 1; height: 4px; border-radius: 2px; " +
      "background: rgba(255,255,255,0.25); position: relative; }\n" +
    ".ch4 .play-track i { position: absolute; left: 0; top: 0; bottom: 0; width: 38%; " +
      "background: var(--color-accent); border-radius: 2px; }\n";

  /* ---------------------------------------------------------- */
  /* Chapter registration                                         */
  /* ---------------------------------------------------------- */

  DEMO.registerChapter({
    id: "ch4",
    act: 1,
    number: 4,
    title: "The End-User Experience",
    hook: "What does this actually look and feel like for your users?",
    talkingPoints: [
      "Amazon DCV: adaptive codec, hardware-accelerated, low-latency",
      "Supports GPU workloads \u2014 Graphics bundles with NVIDIA",
      "Works on any network \u2014 gracefully handles bandwidth fluctuations"
    ],
    styles: STYLES,
    steps: [
      {
        id: "s1",
        screen: screenS1,
        tooltip: "Users receive a simple email with a registration link \u2014 no IT involvement needed.",
        target: '[data-hotspot="reg-link"]',
        placement: "right",
        advance: "hotspot"
      },
      {
        id: "s2",
        screen: screenS2,
        tooltip: "Native clients for Windows and macOS \u2014 or just use the Web Access client.",
        target: '[data-hotspot="web-access"]',
        placement: "bottom",
        advance: "hotspot"
      },
      {
        id: "s3",
        screen: screenS3,
        tooltip: "Zero install option: open a browser, authenticate, and you're in.",
        target: '[data-hotspot="sign-in"]',
        placement: "right",
        advance: "hotspot"
      },
      {
        id: "s4",
        screen: screenS4,
        tooltip: "A full Windows desktop, streaming at up to 4K resolution via Amazon DCV.",
        target: '[data-hotspot="dcv-chip"]',
        placement: "right",
        advance: "next"
      },
      {
        id: "s5",
        screen: screenS5,
        tooltip: "Support for up to 4 monitors \u2014 your users don't compromise on screen real estate.",
        target: '[data-hotspot="monitors"]',
        placement: "right",
        advance: "next"
      },
      {
        id: "s6",
        screen: screenS6,
        tooltip: "Webcams, headsets, smart cards \u2014 peripherals work like they're plugged directly in.",
        target: '[data-hotspot="devices-menu"]',
        placement: "right",
        advance: "next"
      },
      {
        id: "s7",
        screen: screenS7,
        tooltip: "Sub-30ms latency in most regions \u2014 users can't tell it's not local.",
        target: '[data-hotspot="hud"]',
        placement: "left",
        advance: "next"
      }
    ]
  });
})();
