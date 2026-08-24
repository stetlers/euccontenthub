/* ============================================================
   Amazon WorkSpaces: From Zero to Agentic — re:Invent 2026 demo
   ch8.js — Chapter 8: Nested Virtualization (Act 3)

   Chapter content file. Registers itself via DEMO.registerChapter
   at parse time and does nothing else (no DOM access at parse
   time; screen functions run only when rendered inside the
   1600x900 stage canvas). Uses DEMO.frames.* scaffolding and
   theme.css components; all chapter CSS is prefixed with .ch8.
   ============================================================ */

(function () {
  "use strict";

  /* ---------------------------------------------------------- */
  /* Shared fragments                                             */
  /* ---------------------------------------------------------- */

  /**
   * Absolutely positioned hotspot wrapper on the desktop surface.
   * Terminals and app windows render at x/y 0 inside it, so the
   * wrapper itself is the ring/callout target (data-hotspot).
   */
  function hsWrap(hotspot, x, y, w, h, inner) {
    return (
      '<div class="hs-wrap" data-hotspot="' + hotspot + '" style="left:' + x + "px;top:" + y +
        "px;width:" + w + "px;height:" + h + 'px;">' + inner + "</div>"
    );
  }

  /** s2 — label/value cell for the WorkSpace properties grid. */
  function prop(label, value) {
    return (
      "<div>" +
        '<div class="prop-label">' + label + "</div>" +
        '<div class="prop-value">' + value + "</div>" +
      "</div>"
    );
  }

  /** s2 — enable + verify CLI snippet (modify + describe). */
  function cliBlock() {
    return (
      '<div class="code-block">' +
        '<span class="tok-cmd">aws workspaces modify-workspace-properties</span> \\\n' +
        '    <span class="tok-flag">--workspace-id</span> ws-9x7demo12 \\\n' +
        '    <span class="tok-flag">--workspace-properties</span> NestedVirtualizationEnabled=true\n' +
        '<span class="tok-comment"># verify</span>\n' +
        '<span class="tok-cmd">aws workspaces describe-workspaces</span> ' +
          '<span class="tok-flag">--workspace-ids</span> ws-9x7demo12\n' +
        '<span class="tok-comment">    ...</span> "NestedVirtualization": "ENABLED"' +
      "</div>"
    );
  }

  /** s4 — one row of the Docker Desktop container list. */
  function dockRow(name, image, ports, started) {
    return (
      "<tr><td><strong>" + name + "</strong></td>" +
      "<td><code>" + image + "</code></td>" +
      '<td><span class="badge badge-available">Running</span></td>' +
      "<td>" + ports + "</td><td>" + started + "</td></tr>"
    );
  }

  /** s6 — one line of the fake Kotlin editor (gutter + code). */
  function codeLine(n, html) {
    return '<div class="cl"><span class="ln">' + n + "</span>" + html + "</div>";
  }

  /** s6 — Android Studio editor pane content. */
  function editorLines() {
    var kw = function (t) { return '<span class="tok-kw">' + t + "</span>"; };
    var ty = function (t) { return '<span class="tok-type">' + t + "</span>"; };
    var fn = function (t) { return '<span class="tok-fn">' + t + "</span>"; };
    var str = function (t) { return '<span class="tok-str">' + t + "</span>"; };
    return (
      codeLine(1, kw("class") + " " + ty("ExpensesActivity") + " : " + ty("AppCompatActivity") + "() {") +
      codeLine(2, "    " + kw("private") + " " + kw("val") + " repo = " + ty("ExpenseRepository") + "()") +
      codeLine(3, "&nbsp;") +
      codeLine(4, "    " + kw("override") + " " + kw("fun") + " " + fn("onCreate") +
        "(savedInstanceState: " + ty("Bundle") + "?) {") +
      codeLine(5, "        " + kw("super") + "." + fn("onCreate") + "(savedInstanceState)") +
      codeLine(6, "        " + fn("setContentView") + "(R.layout.activity_expenses)") +
      codeLine(7, "&nbsp;") +
      codeLine(8, "        " + kw("val") + " pending = repo." + fn("pendingExpenses") + "()") +
      codeLine(9, "        expenseList.adapter = " + ty("ExpenseAdapter") + "(pending)") +
      codeLine(10, "&nbsp;") +
      codeLine(11, "        submitButton." + fn("setOnClickListener") + " {") +
      codeLine(12, "            repo." + fn("submitReport") + "(pending)") +
      codeLine(13, "            " + fn("showToast") + "(" + str("&quot;Report submitted&quot;") + ")") +
      codeLine(14, "        }") +
      codeLine(15, "    }") +
      codeLine(16, "&nbsp;") +
      codeLine(17, "    " + kw("private") + " " + kw("fun") + " " + fn("showToast") +
        "(msg: " + ty("String") + ") =") +
      codeLine(18, "        " + ty("Toast") + "." + fn("makeText") + "(" + kw("this") +
        ", msg, " + ty("Toast") + ".LENGTH_SHORT)." + fn("show") + "()") +
      codeLine(19, "}")
    );
  }

  /** s6 — expense row inside the phone frame. */
  function phRow(title, meta, amount) {
    return (
      '<div class="ph-row">' +
        "<div><b>" + title + "</b><i>" + meta + "</i></div>" +
        '<span class="ph-amt">' + amount + "</span>" +
      "</div>"
    );
  }

  /** s7 — one nested VM box inside the isolation diagram. */
  function vmBox(x, title, sub) {
    return (
      '<rect x="' + x + '" y="130" width="240" height="180" rx="10" fill="rgba(255,255,255,0.09)" ' +
        'stroke="rgba(255,255,255,0.32)" stroke-width="1.5"/>' +
      '<rect x="' + (x + 104) + '" y="152" width="32" height="22" rx="3" fill="none" ' +
        'stroke="#7ee787" stroke-width="1.5"/>' +
      '<line x1="' + (x + 112) + '" y1="180" x2="' + (x + 128) + '" y2="180" ' +
        'stroke="#7ee787" stroke-width="1.5"/>' +
      '<text x="' + (x + 120) + '" y="212" text-anchor="middle" font-size="17" font-weight="700" ' +
        'fill="#ffffff">' + title + "</text>" +
      '<text x="' + (x + 120) + '" y="238" text-anchor="middle" font-size="12.5" ' +
        'fill="#b9c2d0">' + sub + "</text>"
    );
  }

  /** s7 — nested-boxes isolation diagram (inline SVG). */
  function isolationSvg() {
    return (
      '<svg viewBox="0 0 1000 420" width="1000" height="420" role="img" ' +
        'aria-label="Diagram: WSL2, Docker, and Android emulator virtual machines run nested inside ' +
        'WorkSpace ws-9x7demo12 with encrypted volumes, all inside the AWS Region us-west-2.">' +
        /* outer dashed Region boundary */
        '<rect x="8" y="8" width="984" height="404" rx="14" fill="none" stroke="#8b949e" ' +
          'stroke-width="1.5" stroke-dasharray="8 6"/>' +
        '<text x="34" y="40" font-size="15" fill="#b9c2d0">AWS Region (us-west-2)</text>' +
        /* solid WorkSpace boundary */
        '<rect x="80" y="62" width="840" height="318" rx="12" fill="rgba(255,255,255,0.06)" ' +
          'stroke="rgba(255,255,255,0.45)" stroke-width="1.5"/>' +
        '<text x="106" y="98" font-size="18" font-weight="700" fill="#ffffff">' +
          "WorkSpace ws-9x7demo12</text>" +
        /* padlock + encrypted volumes */
        '<path d="M738 82 v-8 a8 8 0 0 1 16 0 v8" fill="none" stroke="#7ee787" stroke-width="2.5"/>' +
        '<rect x="730" y="82" width="32" height="24" rx="4" fill="#7ee787"/>' +
        '<circle cx="746" cy="93" r="3.5" fill="#16191f"/>' +
        '<text x="772" y="99" font-size="13" fill="#b9c2d0">encrypted volumes</text>' +
        /* row of nested VMs */
        vmBox(110, "WSL2 VM", "Ubuntu 24.04") +
        vmBox(380, "Docker VM", "Linux containers") +
        vmBox(650, "Emulator VM", "Android 15 &middot; API 35") +
        '<text x="500" y="362" text-anchor="middle" font-size="12.5" fill="#8b949e">' +
          "Hardware virtualization extensions &middot; enabled</text>" +
      "</svg>"
    );
  }

  /* ---------------------------------------------------------- */
  /* Chapter styles (every rule prefixed with .ch8)               */
  /* ---------------------------------------------------------- */

  var STYLES =
    "/* --- s1: the developer ask --- */\n" +
    ".ch8 .dev-quote { font-size: 56px; font-weight: 300; line-height: 1.18; max-width: 1150px; }\n" +
    ".ch8 .dev-attr { font-size: 17px; font-style: italic; color: #9aa7bd; }\n" +
    ".ch8 .dev-chips { justify-content: center; margin-top: 4px; }\n" +
    ".ch8 .sim-slide .chip-list li { background: rgba(255,255,255,0.08); " +
      "border-color: rgba(255,255,255,0.42); color: #ffffff; font-size: 14px; padding: 5px 16px; }\n" +

    "/* --- s2: properties page + toggle --- */\n" +
    ".ch8 .s2-card { max-width: 900px; }\n" +
    ".ch8 .prop-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px 24px; }\n" +
    ".ch8 .prop-label { font-size: 12px; font-weight: 700; color: var(--color-text-secondary); }\n" +
    ".ch8 .prop-value { font-size: 14px; }\n" +
    ".ch8 .toggle-row { display: flex; align-items: flex-start; gap: 14px; margin: 4px 0 14px; }\n" +
    ".ch8 .toggle-row .sim-toggle { margin-top: 3px; }\n" +
    ".ch8 .toggle-title { font-size: 14px; font-weight: 700; }\n" +
    ".ch8 .toggle-desc { font-size: 13px; color: var(--color-text-secondary); }\n" +
    ".ch8 .cli-label { margin-top: 16px; }\n" +

    "/* --- s3-s6: absolute hotspot wrappers on the desktop --- */\n" +
    ".ch8 .hs-wrap { position: absolute; }\n" +

    "/* --- s4: Docker Desktop window --- */\n" +
    ".ch8 .dock { display: flex; flex-direction: column; height: 100%; }\n" +
    ".ch8 .dock-body { display: flex; flex: 1; min-height: 0; }\n" +
    ".ch8 .dock-side { width: 190px; flex: none; background: #0e1726; color: #c3ccd9; " +
      "padding: 14px 0; font-size: 13.5px; }\n" +
    ".ch8 .dock-item { padding: 9px 18px; border-left: 3px solid transparent; }\n" +
    ".ch8 .dock-item.active { color: #ffffff; font-weight: 700; border-left-color: #2496ed; " +
      "background: rgba(36,150,237,0.14); }\n" +
    ".ch8 .dock-main { flex: 1; min-width: 0; padding: 16px 20px; background: var(--color-bg); }\n" +
    ".ch8 .dock-main h3 { font-size: 17px; font-weight: 700; }\n" +
    ".ch8 .dock-sub { font-size: 12.5px; color: var(--color-text-secondary); margin: 2px 0 12px; }\n" +
    ".ch8 .dock-foot { flex: none; height: 40px; display: flex; align-items: center; gap: 20px; " +
      "padding: 0 20px; background: var(--color-surface); border-top: 1px solid var(--color-border); " +
      "font-size: 12.5px; color: var(--color-text-secondary); }\n" +
    ".ch8 .dock-engine { display: flex; align-items: center; gap: 7px; font-weight: 700; " +
      "color: var(--badge-green); }\n" +
    ".ch8 .dock-dot { width: 9px; height: 9px; border-radius: 50%; background: var(--badge-green); }\n" +
    ".ch8 .dock-meters { margin-left: auto; display: flex; gap: 24px; }\n" +
    ".ch8 .dock-meter { display: flex; align-items: center; gap: 8px; }\n" +
    ".ch8 .dock-meter b { color: var(--color-text); }\n" +
    ".ch8 .meter-bar { width: 90px; height: 6px; border-radius: 3px; background: #e4e7e9; " +
      "overflow: hidden; }\n" +
    ".ch8 .meter-fill { display: block; height: 100%; background: #2496ed; border-radius: 3px; }\n" +

    "/* --- s6: Android Studio window --- */\n" +
    ".ch8 .studio { display: flex; height: 100%; }\n" +
    ".ch8 .studio-edit { flex: 1; min-width: 0; display: flex; flex-direction: column; " +
      "background: #2b2b2b; }\n" +
    ".ch8 .edit-tabs { flex: none; display: flex; background: #3c3f41; font-size: 12.5px; " +
      "color: #9da5b0; }\n" +
    ".ch8 .edit-tab { padding: 7px 16px; }\n" +
    ".ch8 .edit-tab.active { background: #2b2b2b; color: #e8eaed; " +
      "box-shadow: inset 0 -2px 0 #4a88c7; }\n" +
    ".ch8 .edit-body { flex: 1; padding: 12px 0; font-family: var(--font-mono); font-size: 13px; " +
      "line-height: 1.75; overflow: hidden; }\n" +
    ".ch8 .cl { white-space: pre; color: #a9b7c6; }\n" +
    ".ch8 .cl .ln { display: inline-block; width: 40px; text-align: right; padding-right: 14px; " +
      "color: #5b6470; }\n" +
    ".ch8 .tok-kw { color: #cc7832; }\n" +
    ".ch8 .tok-str { color: #6a8759; }\n" +
    ".ch8 .tok-fn { color: #ffc66e; }\n" +
    ".ch8 .tok-type { color: #6897bb; }\n" +
    ".ch8 .studio-emu { flex: none; width: 370px; background: #16191f; display: flex; " +
      "flex-direction: column; align-items: center; justify-content: center; gap: 14px; " +
      "border-left: 1px solid rgba(255,255,255,0.09); }\n" +
    ".ch8 .phone-frame { display: flex; flex-direction: column; }\n" +
    ".ch8 .ph-status { flex: none; display: flex; justify-content: space-between; " +
      "align-items: center; padding: 4px 10px; font-size: 9.5px; color: #d5dbdb; " +
      "background: #1a2432; }\n" +
    ".ch8 .ph-header { flex: none; background: #232f3e; color: #ffffff; font-size: 12.5px; " +
      "font-weight: 700; padding: 10px 12px; }\n" +
    ".ch8 .ph-row { display: flex; justify-content: space-between; align-items: center; " +
      "padding: 9px 12px; border-bottom: 1px solid #eef1f3; font-size: 11px; color: #16191f; }\n" +
    ".ch8 .ph-row b { font-size: 11px; }\n" +
    ".ch8 .ph-row i { display: block; font-style: normal; color: #687078; font-size: 9.5px; " +
      "margin-top: 1px; }\n" +
    ".ch8 .ph-amt { font-weight: 700; font-family: var(--font-mono); font-size: 11px; }\n" +
    ".ch8 .ph-btn { margin: auto 12px 14px; background: var(--color-accent); color: #16191f; " +
      "text-align: center; font-size: 11.5px; font-weight: 700; padding: 8px 0; " +
      "border-radius: 16px; }\n" +
    ".ch8 .emu-caption { display: flex; align-items: center; gap: 8px; font-size: 13px; " +
      "color: #d5dbdb; }\n" +
    ".ch8 .emu-dot { width: 9px; height: 9px; border-radius: 50%; background: #7ee787; }\n" +

    "/* --- s7: isolation slide checks --- */\n" +
    ".ch8 .iso-checks { display: flex; gap: 38px; margin: 2px 0 0; font-size: 15px; " +
      "color: #d5dbdb; }\n" +
    ".ch8 .iso-checks li { margin-bottom: 0; }\n" +
    ".ch8 .iso-checks li::before { color: #7ee787; }\n";

  /* ---------------------------------------------------------- */
  /* Chapter registration                                         */
  /* ---------------------------------------------------------- */

  DEMO.registerChapter({
    id: "ch8",
    act: 3,
    number: 8,
    title: "Nested Virtualization",
    hook: "Run Docker, WSL2, Android emulators, or even Hyper-V — inside your WorkSpace.",
    talkingPoints: [
      "Supported on compatible instance families",
      "Unlocks the entire developer persona for WorkSpaces adoption",
      "No performance penalty for non-virtualization workloads when disabled",
      "CLI check: aws workspaces describe-workspaces shows nested virtualization status"
    ],
    styles: STYLES,
    steps: [

      /* s1 — developer persona: "I need Docker on my WorkSpace" */
      {
        id: "s1",
        screen: function () {
          return DEMO.frames.slide(
            '<p class="slide-kicker">The developer ask</p>' +
            '<p class="dev-quote">&ldquo;I need Docker on my WorkSpace.&rdquo;</p>' +
            '<p class="dev-attr">&mdash; every platform team, 2026</p>' +
            '<ul class="chip-list dev-chips">' +
              "<li>Docker Desktop</li>" +
              "<li>WSL2</li>" +
              "<li>Android emulators</li>" +
              "<li>Hyper-V</li>" +
              "<li>QEMU-KVM</li>" +
            "</ul>" +
            '<p class="slide-sub">All of these require hardware virtualization extensions &mdash; ' +
              "previously bare-metal only.</p>"
          );
        },
        tooltip: "Developers need containers, WSL2, Android Studio emulators — all require nested virtualization.",
        advance: "next",
        placement: "bottom"
      },

      /* s2 — enable nested virtualization (console toggle or CLI) */
      {
        id: "s2",
        screen: function () {
          return DEMO.frames.consoleFrame(
            { breadcrumbs: "WorkSpaces &rsaquo; Personal &rsaquo; ws-9x7demo12" },
            '<h1 class="page-title">ws-9x7demo12 &mdash; Properties</h1>' +
            '<p class="page-desc">Windows 11 WorkSpace for Martha Major &middot; ' +
              "hostname WSAMZN-MMAJOR &middot; us-west-2</p>" +
            '<div class="console-card u-mb-16 s2-card">' +
              "<h2>WorkSpace properties</h2>" +
              '<div class="prop-grid">' +
                prop("Bundle", "Power") +
                prop("Protocol", "DCV") +
                prop("Running mode", "AutoStop") +
                prop("User", "mmajor") +
              "</div>" +
            "</div>" +
            '<div class="console-card s2-card">' +
              "<h2>Nested virtualization</h2>" +
              '<div class="toggle-row">' +
                '<span class="sim-toggle" data-hotspot="nested-toggle"></span>' +
                "<div>" +
                  '<div class="toggle-title">Enable nested virtualization</div>' +
                  '<div class="toggle-desc">Enables hardware virtualization extensions inside ' +
                    "this WorkSpace.</div>" +
                "</div>" +
              "</div>" +
              '<div class="flash flash-warning">Enabling nested virtualization disconnects ' +
                "active sessions.</div>" +
              '<span class="field-label cli-label">Or enable via the AWS CLI</span>' +
              cliBlock() +
            "</div>"
          );
        },
        tooltip: "A single API call or console toggle enables hardware virtualization extensions.",
        advance: "hotspot",
        target: '[data-hotspot="nested-toggle"]',
        placement: "bottom-right"
      },

      /* s3 — verify in-guest: systeminfo reports Hyper-V capable */
      {
        id: "s3",
        screen: function () {
          return DEMO.frames.desktopFrame(
            { name: "WSAMZN-MMAJOR", clock: "3:04 PM" },
            hsWrap("verify-term", 280, 120, 1000, 520,
              DEMO.frames.terminal(
                { title: "Command Prompt &mdash; WSAMZN-MMAJOR", x: 0, y: 0, w: 1000, h: 520 },
                [
                  { text: "Microsoft Windows [Version 10.0.26100.4946]", cls: "term-dim" },
                  { text: "(c) Microsoft Corporation. All rights reserved.", cls: "term-dim" },
                  { text: "&nbsp;" },
                  { prompt: "C:\\Users\\mmajor&gt;", text: 'systeminfo | findstr /C:"Hyper-V"' },
                  { text: "Hyper-V Requirements:      VM Monitor Mode Extensions: Yes" },
                  { text: "                           Virtualization Enabled In Firmware: Yes", cls: "term-ok" },
                  { text: "                           Second Level Address Translation: Yes" },
                  { text: "                           Data Execution Prevention Available: Yes" },
                  { text: "&nbsp;" },
                  { prompt: "C:\\Users\\mmajor&gt;", text: "&#9608;" }
                ]
              )
            )
          );
        },
        tooltip: "The WorkSpace now reports virtualization support — WSL2, Docker, Hyper-V all light up.",
        advance: "next",
        target: '[data-hotspot="verify-term"]',
        placement: "right"
      },

      /* s4 — Docker Desktop running inside the WorkSpace */
      {
        id: "s4",
        screen: function () {
          return DEMO.frames.desktopFrame(
            { name: "WSAMZN-MMAJOR", clock: "3:09 PM" },
            hsWrap("docker-win", 250, 90, 1080, 600,
              DEMO.frames.appWindow(
                { title: "Docker Desktop", iconClass: "icon-docker", x: 0, y: 0, w: 1080, h: 600 },
                '<div class="dock">' +
                  '<div class="dock-body">' +
                    '<div class="dock-side">' +
                      '<div class="dock-item active">Containers</div>' +
                      '<div class="dock-item">Images</div>' +
                      '<div class="dock-item">Volumes</div>' +
                    "</div>" +
                    '<div class="dock-main">' +
                      "<h3>Containers</h3>" +
                      '<p class="dock-sub">3 containers &middot; all running</p>' +
                      '<div class="table-wrap"><table class="console-table">' +
                        "<thead><tr><th>Name</th><th>Image</th><th>Status</th>" +
                          "<th>Port(s)</th><th>Started</th></tr></thead>" +
                        "<tbody>" +
                          dockRow("api-gateway", "nginx:1.27", "8080:80", "2 min ago") +
                          dockRow("payments-svc", "amazoncorretto:21", "8081:8080", "8 min ago") +
                          dockRow("postgres-dev", "postgres:16", "5432:5432", "31 min ago") +
                        "</tbody>" +
                      "</table></div>" +
                    "</div>" +
                  "</div>" +
                  '<div class="dock-foot">' +
                    '<span class="dock-engine"><span class="dock-dot"></span>Engine running</span>' +
                    '<span class="dock-meters">' +
                      '<span class="dock-meter">CPU <b>38%</b><span class="meter-bar">' +
                        '<span class="meter-fill" style="width:38%"></span></span></span>' +
                      '<span class="dock-meter">Memory <b>5.2 GB</b><span class="meter-bar">' +
                        '<span class="meter-fill" style="width:54%"></span></span></span>' +
                    "</span>" +
                  "</div>" +
                "</div>"
              )
            )
          );
        },
        tooltip: "Full Docker Desktop experience — build, run, and test containers without leaving your cloud desktop.",
        advance: "next",
        target: '[data-hotspot="docker-win"]',
        placement: "right"
      },

      /* s5 — WSL2 + Ubuntu terminal */
      {
        id: "s5",
        screen: function () {
          return DEMO.frames.desktopFrame(
            { name: "WSAMZN-MMAJOR", clock: "3:11 PM" },
            hsWrap("wsl-term", 300, 130, 980, 500,
              DEMO.frames.terminal(
                { title: "mmajor@WSAMZN-MMAJOR: ~", x: 0, y: 0, w: 980, h: 500 },
                [
                  { prompt: "$", text: "wsl -l -v" },
                  { text: "  NAME            STATE           VERSION", cls: "term-dim" },
                  { text: "* Ubuntu-24.04    Running         2", cls: "term-hl" },
                  { text: "&nbsp;" },
                  { prompt: "$", text: "uname -a" },
                  { text: "Linux WSAMZN-MMAJOR 5.15.167.4-microsoft-standard-WSL2 #1 SMP x86_64 GNU/Linux" },
                  { text: "&nbsp;" },
                  { prompt: "$", text: "docker run hello-world" },
                  { text: "Unable to find image 'hello-world:latest' locally", cls: "term-dim" },
                  { text: "latest: Pulling from library/hello-world", cls: "term-dim" },
                  { text: "&nbsp;" },
                  { text: "Hello from Docker!", cls: "term-ok" },
                  { text: "This message shows that your installation appears to be working correctly.", cls: "term-dim" },
                  { text: "&nbsp;" },
                  { prompt: "$", text: "&#9608;" }
                ]
              )
            )
          );
        },
        tooltip: "Linux development environment inside a Windows WorkSpace — best of both worlds.",
        advance: "next",
        target: '[data-hotspot="wsl-term"]',
        placement: "right"
      },

      /* s6 — Android emulator in Android Studio */
      {
        id: "s6",
        screen: function () {
          return DEMO.frames.desktopFrame(
            { name: "WSAMZN-MMAJOR", clock: "3:14 PM" },
            hsWrap("emulator", 220, 70, 1140, 640,
              DEMO.frames.appWindow(
                { title: "Android Studio &mdash; Pixel 9 emulator", iconClass: "icon-android",
                  x: 0, y: 0, w: 1140, h: 640 },
                '<div class="studio">' +
                  '<div class="studio-edit">' +
                    '<div class="edit-tabs">' +
                      '<span class="edit-tab active">ExpensesActivity.kt</span>' +
                      '<span class="edit-tab">ExpenseRepository.kt</span>' +
                    "</div>" +
                    '<div class="edit-body">' + editorLines() + "</div>" +
                  "</div>" +
                  '<div class="studio-emu">' +
                    '<div class="phone-frame">' +
                      '<div class="ph-status"><span>3:14</span><span>5G &middot; 98%</span></div>' +
                      '<div class="ph-header">example-corp Expenses</div>' +
                      phRow("Team lunch", "Aug 12 &middot; Meals", "$42.10") +
                      phRow("Rideshare", "Aug 13 &middot; Travel", "$18.75") +
                      phRow("Monitor stand", "Aug 14 &middot; Equipment", "$64.99") +
                      '<div class="ph-btn">Submit report</div>' +
                    "</div>" +
                    '<p class="emu-caption"><span class="emu-dot"></span>' +
                      "Pixel 9 &mdash; API 35 &mdash; running</p>" +
                  "</div>" +
                "</div>"
              )
            )
          );
        },
        tooltip: "Mobile developers can test on virtual devices without dedicated hardware.",
        advance: "next",
        target: '[data-hotspot="emulator"]',
        placement: "left"
      },

      /* s7 — security isolation diagram */
      {
        id: "s7",
        screen: function () {
          return DEMO.frames.slide(
            '<p class="slide-kicker">Security model</p>' +
            '<h2 class="slide-title">Isolation is inherited</h2>' +
            '<div class="slide-diagram">' + isolationSvg() + "</div>" +
            '<ul class="check-list iso-checks">' +
              "<li>No data on the endpoint</li>" +
              "<li>Full CloudTrail audit trail</li>" +
              "<li>Security boundary inside the WorkSpace is customer-owned</li>" +
            "</ul>"
          );
        },
        tooltip: "Nested VMs inherit WorkSpaces security: encrypted, no data on endpoint, full audit trail.",
        advance: "next",
        placement: "bottom"
      }
    ]
  });
})();
