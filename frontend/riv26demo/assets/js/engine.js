/* ============================================================
   Amazon WorkSpaces: From Zero to Agentic — re:Invent 2026 demo
   engine.js — step engine (CONTRACT FILE)
   Chapter builders must NOT modify this file.

   ------------------------------------------------------------
   CHAPTER CONTRACT
   Each chapter file (assets/js/chapters/chN.js) is a classic
   script that calls DEMO.registerChapter(chapter) at parse time
   and touches NOTHING else (no DOM access at parse time; screen
   functions run only when rendered).

   chapter = {
     id: "ch3",                     // ch1..ch9
     act: 1,                        // 1 | 2 | 3
     number: 3,
     title: "Deploying Your First WorkSpace",
     hook: "Let's go from zero to a running desktop…",
     talkingPoints: ["…", "…"],     // presenter notes
     styles: ".ch3 .foo { … }",     // optional; EVERY rule prefixed with .ch3
     steps: [{
       id: "s1",                    // s1..sN in order
       screen: function () { return "<html string>"; },
       tooltip: "Callout text from the demo plan",
       target: "[data-hotspot='x']",// required when advance === "hotspot"
       placement: "right",          // top|right|bottom|left|center (relative to target)
                                    // or a docked corner: top-left|top-right|
                                    // bottom-left|bottom-right (ignores target).
                                    // Default: bottom. Steps without a target
                                    // dock bottom-right unless "center" is set.
       advance: "hotspot"           // "hotspot" | "next"
     }]
   }

   Rules for chapter builders:
   - Use DEMO.frames.* for console/browser/desktop/window/terminal
     screens and DEMO.ui.lineChart for charts.
   - Never place a data-hotspot target inside the console topnav.
   - All imagery is HTML/CSS/inline SVG. No external URLs.
   ============================================================ */

(function () {
  "use strict";

  var CANVAS_W = 1600;
  var CANVAS_H = 900;

  // Expected chapters and step counts (Requirement 2.3).
  var MANIFEST = { ch1: 3, ch2: 5, ch3: 7, ch4: 7, ch5: 4, ch6: 5, ch7: 8, ch8: 7, ch9: 8 };
  var CHAPTER_ORDER = ["ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "ch7", "ch8", "ch9"];
  var ACT_NAMES = {
    1: "Act 1 — The Problem & The Promise",
    2: "Act 2 — Day-2 Operations",
    3: "Act 3 — What's New: re:Invent 2026"
  };

  var chapters = {};
  var sequence = [];        // flattened entries
  var indexByHash = {};
  var current = -1;
  var suppressHashEvent = false;
  var presenterOn = false;

  var el = {};              // chrome element refs, resolved in start()

  /* ---------------------------------------------------------- */
  /* Registry                                                     */
  /* ---------------------------------------------------------- */

  var DEMO = {
    registerChapter: function (ch) {
      if (ch && ch.id) { chapters[ch.id] = ch; }
    }
  };

  /* ---------------------------------------------------------- */
  /* Frame helpers (screen scaffolding for chapter builders)      */
  /* ---------------------------------------------------------- */

  DEMO.frames = {

    /** 16:9 narrative slide. opts: { left: true } for left-aligned. */
    slide: function (inner, opts) {
      var cls = opts && opts.left ? " slide-left" : "";
      return '<div class="sim-slide' + cls + '">' + inner + "</div>";
    },

    /**
     * AWS console chrome.
     * cfg: { service, breadcrumbs, sidenav: [string | {label, active}],
     *        search, region, account }
     */
    consoleFrame: function (cfg, inner) {
      cfg = cfg || {};
      var service = cfg.service || "Amazon WorkSpaces";
      var region = cfg.region || "US West (Oregon)";
      var account = cfg.account || "demo-admin @ example-corp";
      var search = cfg.search || "Search for services, features, and more";
      var sidenav = cfg.sidenav || [
        { label: "Personal", active: true },
        "Applications", "Core", "Directories", "Bundles", "Images", "WorkSpaces Advisor"
      ];
      var items = sidenav.map(function (it) {
        var label = typeof it === "string" ? it : it.label;
        var active = typeof it === "object" && it.active;
        return "<li" + (active ? ' class="active"' : "") + ">" + label + "</li>";
      }).join("");
      return (
        '<div class="sim-console">' +
          '<div class="sim-topnav" aria-hidden="true">' +
            '<span class="aws-mark">aws</span>' +
            '<span class="sim-search">' + search + "</span>" +
            '<span class="sim-top-right">' + region + " &nbsp;&middot;&nbsp; " + account + "</span>" +
          "</div>" +
          '<div class="sim-body">' +
            '<nav class="sim-sidenav"><h2>' + service + "</h2><ul>" + items + "</ul></nav>" +
            '<div class="sim-main">' +
              (cfg.breadcrumbs ? '<div class="sim-breadcrumbs">' + cfg.breadcrumbs + "</div>" : "") +
              inner +
            "</div>" +
          "</div>" +
        "</div>"
      );
    },

    /** Browser chrome. cfg: { url } */
    browserFrame: function (cfg, inner) {
      cfg = cfg || {};
      return (
        '<div class="sim-browser">' +
          '<div class="browser-bar">' +
            '<span class="win-dots" aria-hidden="true"><i></i><i></i><i></i></span>' +
            '<span class="browser-addr">' + (cfg.url || "https://example.com") + "</span>" +
          "</div>" +
          '<div class="browser-view">' + inner + "</div>" +
        "</div>"
      );
    },

    /**
     * Streamed Windows desktop with DCV toolbar and taskbar.
     * cfg: { name, clock, items: [{label, active, attrs}] }
     * inner is placed on .desktop-surface (windows, HUDs, menus).
     */
    desktopFrame: function (cfg, inner) {
      cfg = cfg || {};
      var name = cfg.name || "WSAMZN-MMAJOR";
      var clock = cfg.clock || "2:47 PM";
      var items = cfg.items || [
        { label: "Display" }, { label: "Devices" }, { label: "Clipboard" }, { label: "Settings" }
      ];
      var toolbar = items.map(function (it) {
        return "<span class=\"dcv-item" + (it.active ? " active" : "") + "\"" +
          (it.attrs ? " " + it.attrs : "") + ">" + it.label + "</span>";
      }).join("");
      var tiles = "";
      var tileCls = ["tile-start", "", "tile-accent", "", "tile-green", ""];
      for (var i = 0; i < 6; i++) {
        tiles += '<span class="task-tile ' + tileCls[i] + '"></span>';
      }
      return (
        '<div class="sim-desktop">' +
          '<div class="dcv-toolbar"><span class="dcv-name">Amazon DCV &middot; ' + name + "</span>" + toolbar + "</div>" +
          '<div class="desktop-surface">' + inner + "</div>" +
          '<div class="desktop-taskbar" aria-hidden="true">' + tiles +
            '<span class="task-clock">' + clock + "</span>" +
          "</div>" +
        "</div>"
      );
    },

    /** Application window. cfg: { title, iconClass, x, y, w, h } */
    appWindow: function (cfg, inner) {
      cfg = cfg || {};
      var style = "left:" + (cfg.x || 60) + "px;top:" + (cfg.y || 60) + "px;" +
                  "width:" + (cfg.w || 700) + "px;height:" + (cfg.h || 460) + "px;";
      return (
        '<div class="app-window" style="' + style + '">' +
          '<div class="app-titlebar">' +
            '<span class="app-icon ' + (cfg.iconClass || "") + '"></span>' +
            '<span class="app-title">' + (cfg.title || "Application") + "</span>" +
            '<span class="win-controls" aria-hidden="true"><i>&ndash;</i><i>&#9633;</i><i>&times;</i></span>' +
          "</div>" +
          '<div class="app-content">' + inner + "</div>" +
        "</div>"
      );
    },

    /**
     * Terminal window. cfg: { title, x, y, w, h }
     * lines: [{ prompt, text, cls }]  (cls: term-ok | term-hl | term-dim)
     */
    terminal: function (cfg, lines) {
      cfg = cfg || {};
      var style = "left:" + (cfg.x || 80) + "px;top:" + (cfg.y || 80) + "px;" +
                  "width:" + (cfg.w || 760) + "px;height:" + (cfg.h || 420) + "px;";
      var body = (lines || []).map(function (l) {
        return '<div class="term-line' + (l.cls ? " " + l.cls : "") + '">' +
          (l.prompt ? '<span class="term-prompt">' + l.prompt + "</span>" : "") +
          (l.text || "") + "</div>";
      }).join("");
      return (
        '<div class="sim-terminal" style="' + style + '">' +
          '<div class="term-titlebar">' + (cfg.title || "Command Prompt") + "</div>" +
          '<div class="term-body">' + body + "</div>" +
        "</div>"
      );
    }
  };

  DEMO.ui = {

    /**
     * Inline SVG line/area chart.
     * cfg: {
     *   w, h,                      // default 520x200
     *   yMax,                      // default: 1.15 * max value
     *   yLabel,                    // axis caption (small, rotated not supported — shown top-left)
     *   xLabels: ["12 PM", …],     // optional, spread across axis
     *   series: [{ points: [..], color, fill: true }],
     *   annotations: [{ x: index, label }],
     *   label                      // accessible description
     * }
     */
    lineChart: function (cfg) {
      cfg = cfg || {};
      var w = cfg.w || 520, h = cfg.h || 200;
      var padL = 46, padR = 14, padT = 16, padB = cfg.xLabels ? 30 : 14;
      var series = cfg.series || [];
      var palette = ["#0073bb", "#ec7211", "#1d8102", "#d13212", "#687078"];
      var maxLen = 2, maxVal = 0;
      series.forEach(function (s) {
        maxLen = Math.max(maxLen, s.points.length);
        s.points.forEach(function (v) { maxVal = Math.max(maxVal, v); });
      });
      var yMax = cfg.yMax || Math.ceil(maxVal * 1.15) || 1;
      var plotW = w - padL - padR, plotH = h - padT - padB;
      function X(i) { return padL + (i / (maxLen - 1)) * plotW; }
      function Y(v) { return padT + plotH - (v / yMax) * plotH; }

      var out = '<svg viewBox="0 0 ' + w + " " + h + '" width="' + w + '" height="' + h +
        '" role="img" aria-label="' + (cfg.label || "Metric chart") + '">';
      // grid + y ticks
      for (var g = 0; g <= 4; g++) {
        var gy = padT + (plotH * g) / 4;
        var gv = Math.round(yMax - (yMax * g) / 4);
        out += '<line x1="' + padL + '" y1="' + gy + '" x2="' + (w - padR) + '" y2="' + gy +
          '" stroke="#eaeded" stroke-width="1"/>';
        out += '<text x="' + (padL - 6) + '" y="' + (gy + 4) +
          '" text-anchor="end" font-size="10" fill="#687078">' + gv + "</text>";
      }
      if (cfg.yLabel) {
        out += '<text x="' + padL + '" y="10" font-size="10" fill="#687078">' + cfg.yLabel + "</text>";
      }
      // x labels
      if (cfg.xLabels) {
        cfg.xLabels.forEach(function (lb, i) {
          var lx = padL + (i / (cfg.xLabels.length - 1)) * plotW;
          out += '<text x="' + lx + '" y="' + (h - 8) +
            '" text-anchor="middle" font-size="10" fill="#687078">' + lb + "</text>";
        });
      }
      // series
      series.forEach(function (s, si) {
        var color = s.color || palette[si % palette.length];
        var pts = s.points.map(function (v, i) { return X(i) + "," + Y(v); }).join(" ");
        if (s.fill) {
          var area = "M" + X(0) + "," + Y(s.points[0]) +
            s.points.map(function (v, i) { return "L" + X(i) + "," + Y(v); }).join("") +
            "L" + X(s.points.length - 1) + "," + (padT + plotH) + "L" + X(0) + "," + (padT + plotH) + "Z";
          out += '<path d="' + area + '" fill="' + color + '" opacity="0.12"/>';
        }
        out += '<polyline points="' + pts + '" fill="none" stroke="' + color + '" stroke-width="2"/>';
      });
      // annotations
      (cfg.annotations || []).forEach(function (a) {
        var ax = X(a.x);
        out += '<line x1="' + ax + '" y1="' + padT + '" x2="' + ax + '" y2="' + (padT + plotH) +
          '" stroke="#d13212" stroke-width="1.5" stroke-dasharray="4 3"/>';
        out += '<text x="' + Math.min(ax + 5, w - 90) + '" y="' + (padT + 12) +
          '" font-size="10" font-weight="bold" fill="#d13212">' + a.label + "</text>";
      });
      out += "</svg>";
      return out;
    }
  };

  /* ---------------------------------------------------------- */
  /* Sequence building                                            */
  /* ---------------------------------------------------------- */

  function buildSequence() {
    sequence = [];
    indexByHash = {};

    function push(entry) {
      indexByHash[entry.hash] = sequence.length;
      sequence.push(entry);
    }

    push({ type: "view", id: "start", hash: "#start", template: "view-start" });

    CHAPTER_ORDER.forEach(function (id) {
      var ch = chapters[id];
      if (!ch) { return; }
      push({ type: "title", ch: ch, hash: "#" + id + "-title" });
      (ch.steps || []).forEach(function (step, i) {
        push({
          type: "step", ch: ch, step: step,
          stepNum: i + 1, stepCount: ch.steps.length,
          hash: "#" + id + "-s" + (i + 1)
        });
      });
      if (ch.number === 4) {
        push({ type: "view", id: "branch-act1", hash: "#branch-act1", template: "view-branch-act1" });
      }
    });

    push({ type: "view", id: "wrap-up", hash: "#wrap-up", template: "view-wrapup" });
  }

  /* ---------------------------------------------------------- */
  /* Self-check (Requirement 2.3 / Error handling)                */
  /* ---------------------------------------------------------- */

  function selfCheck() {
    var issues = [];
    CHAPTER_ORDER.forEach(function (id) {
      var ch = chapters[id];
      if (!ch) {
        issues.push(id + ": not registered");
      } else if (!ch.steps || ch.steps.length !== MANIFEST[id]) {
        issues.push(id + ": expected " + MANIFEST[id] + " steps, found " +
          (ch.steps ? ch.steps.length : 0));
      }
    });
    Object.keys(chapters).forEach(function (id) {
      if (!MANIFEST[id]) { issues.push(id + ": unexpected chapter id"); }
    });
    if (issues.length) {
      var banner = document.createElement("div");
      banner.className = "diagnostic-banner";
      banner.setAttribute("role", "alert");
      banner.innerHTML = "<strong>Demo self-check failed:</strong> " + issues.join(" &middot; ");
      document.body.appendChild(banner);
    }
  }

  function injectChapterStyles() {
    CHAPTER_ORDER.forEach(function (id) {
      var ch = chapters[id];
      if (ch && ch.styles) {
        var tag = document.createElement("style");
        tag.setAttribute("data-chapter", id);
        tag.textContent = ch.styles;
        document.head.appendChild(tag);
      }
    });
  }

  /* ---------------------------------------------------------- */
  /* Rendering                                                    */
  /* ---------------------------------------------------------- */

  function titleCardHtml(ch) {
    return (
      '<div class="title-card">' +
        '<p class="title-act">' + ACT_NAMES[ch.act] + "</p>" +
        '<p class="title-chnum">Chapter ' + ch.number + " of 9</p>" +
        "<h1>" + ch.title + "</h1>" +
        '<p class="title-hook">&ldquo;' + ch.hook + "&rdquo;</p>" +
      "</div>"
    );
  }

  function render() {
    var entry = sequence[current];
    if (!entry) { return; }

    var screenHost = el.screen;
    el.ring.hidden = true;
    el.callout.hidden = true;

    if (entry.type === "step") {
      screenHost.className = "canvas-screen canvas " + entry.ch.id;
      screenHost.innerHTML =
        '<h1 class="visually-hidden">Chapter ' + entry.ch.number + " — " + entry.ch.title +
        ", step " + entry.stepNum + " of " + entry.stepCount + "</h1>" +
        entry.step.screen();
      requestAnimationFrame(function () { placeStepOverlay(entry); });
    } else if (entry.type === "title") {
      screenHost.className = "canvas-screen";
      screenHost.innerHTML = titleCardHtml(entry.ch);
    } else {
      screenHost.className = "canvas-screen";
      var tpl = document.getElementById(entry.template);
      screenHost.innerHTML = tpl ? tpl.innerHTML : "<p>Missing view: " + entry.id + "</p>";
    }

    updateFooter(entry);
    updatePresenter(entry);
    updateHash(entry);
    announce(entry);

    if (entry.type !== "step") {
      screenHost.focus({ preventScroll: true });
    }
  }

  function canvasRect(target) {
    var c = el.canvas.getBoundingClientRect();
    var r = target.getBoundingClientRect();
    var s = c.width / CANVAS_W;
    return {
      left: (r.left - c.left) / s,
      top: (r.top - c.top) / s,
      width: r.width / s,
      height: r.height / s
    };
  }

  function placeStepOverlay(entry) {
    if (sequence[current] !== entry) { return; }  // stale render
    var step = entry.step;
    var target = null;
    if (step.target) {
      target = el.screen.querySelector(step.target);
      if (!target) {
        console.warn("[demo] hotspot target not found:", entry.ch.id, step.id, step.target);
      }
    }

    // Hotspot ring + activation
    if (target) {
      var tr = canvasRect(target);
      el.ring.style.left = (tr.left - 6) + "px";
      el.ring.style.top = (tr.top - 6) + "px";
      el.ring.style.width = (tr.width + 12) + "px";
      el.ring.style.height = (tr.height + 12) + "px";
      el.ring.hidden = false;

      if (step.advance === "hotspot") {
        target.setAttribute("role", "button");
        target.setAttribute("tabindex", "0");
        target.setAttribute("aria-label", "Continue: " + step.tooltip);
        target.style.cursor = "pointer";
        target.addEventListener("click", nextFromHotspot);
        target.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); nextFromHotspot(); }
        });
      }
    }

    // Callout
    var hotspotAdvance = step.advance === "hotspot" && target;
    el.callout.innerHTML =
      '<p class="callout-kicker">Chapter ' + entry.ch.number + " &middot; Step " +
        entry.stepNum + " of " + entry.stepCount + "</p>" +
      '<p class="callout-text">' + step.tooltip + "</p>" +
      (hotspotAdvance
        ? '<p class="callout-hint">Click the highlighted area &mdash; or press ' +
          '<span class="hint-key">&rarr;</span> to continue</p>'
        : '<button type="button" class="callout-next">Next</button>');
    el.callout.hidden = false;

    var nextBtn = el.callout.querySelector(".callout-next");
    if (nextBtn) { nextBtn.addEventListener("click", next); }

    positionCallout(target ? canvasRect(target) : null, step.placement || "bottom");
    el.callout.focus({ preventScroll: true });
  }

  var DOCKED_PLACEMENTS = {
    "top-left": true, "top-right": true, "bottom-left": true, "bottom-right": true
  };

  function positionCallout(targetRect, placement) {
    var co = el.callout;
    var cw = co.offsetWidth, chh = co.offsetHeight;
    var margin = 24, gap = 18;
    var x, y;

    function dockXY(p) {
      return {
        x: p.indexOf("right") !== -1 ? CANVAS_W - cw - margin : margin,
        y: p.indexOf("bottom") !== -1 ? CANVAS_H - chh - margin : margin
      };
    }

    if (DOCKED_PLACEMENTS[placement]) {
      // Explicit corner dock — target (if any) keeps its ring only.
      var d = dockXY(placement);
      x = d.x; y = d.y;
    } else if (!targetRect) {
      // No anchor: dock bottom-right (Storylane-style guide bubble)
      // instead of covering centered screen content. "center" opts out.
      if (placement === "center") {
        x = (CANVAS_W - cw) / 2;
        y = (CANVAS_H - chh) / 2;
      } else {
        var d2 = dockXY("bottom-right");
        x = d2.x; y = d2.y;
      }
    } else if (placement === "center") {
      x = (CANVAS_W - cw) / 2;
      y = (CANVAS_H - chh) / 2;
    } else {
      var attempts = [placement, "bottom", "top", "right", "left"];
      var placed = false;
      for (var i = 0; i < attempts.length; i++) {
        var p = attempts[i];
        if (p === "right") {
          x = targetRect.left + targetRect.width + gap;
          y = targetRect.top + targetRect.height / 2 - chh / 2;
        } else if (p === "left") {
          x = targetRect.left - cw - gap;
          y = targetRect.top + targetRect.height / 2 - chh / 2;
        } else if (p === "top") {
          x = targetRect.left + targetRect.width / 2 - cw / 2;
          y = targetRect.top - chh - gap;
        } else {
          x = targetRect.left + targetRect.width / 2 - cw / 2;
          y = targetRect.top + targetRect.height + gap;
        }
        if (x >= margin && y >= margin && x + cw <= CANVAS_W - margin && y + chh <= CANVAS_H - margin) {
          placed = true;
          break;
        }
      }
      if (!placed) {
        // No side fits: dock in the corner rather than covering the target.
        var d3 = dockXY("bottom-right");
        x = d3.x; y = d3.y;
      }
    }
    // Final clamp
    x = Math.max(margin, Math.min(x, CANVAS_W - cw - margin));
    y = Math.max(margin, Math.min(y, CANVAS_H - chh - margin));
    co.style.left = x + "px";
    co.style.top = y + "px";
  }

  /* ---------------------------------------------------------- */
  /* Chrome updates                                               */
  /* ---------------------------------------------------------- */

  function updateFooter(entry) {
    var text;
    if (entry.type === "step") {
      text = "Chapter " + entry.ch.number + " \u00B7 Step " + entry.stepNum + " of " + entry.stepCount +
        " \u00B7 " + entry.ch.title;
    } else if (entry.type === "title") {
      text = "Chapter " + entry.ch.number + " \u00B7 " + entry.ch.title;
    } else if (entry.id === "start") {
      text = "Start";
    } else if (entry.id === "branch-act1") {
      text = "Checkpoint \u2014 choose your path";
    } else {
      text = "Wrap-up";
    }
    el.positionText.textContent = text;

    var pct = Math.round((current / (sequence.length - 1)) * 100);
    el.progressFill.style.width = pct + "%";
    el.progressPct.textContent = pct + "%";
    el.progressTrack.setAttribute("aria-valuenow", String(pct));

    el.btnBack.disabled = current <= 0;
    el.btnNext.disabled = current >= sequence.length - 1;
  }

  function updatePresenter(entry) {
    var host = el.presenterBody;
    var ch = entry.ch;
    if (ch) {
      var points = (ch.talkingPoints || []).map(function (p) { return "<li>" + p + "</li>"; }).join("");
      host.innerHTML =
        '<p class="presenter-chapter">' + ACT_NAMES[ch.act] + " &middot; Chapter " + ch.number + ": " + ch.title + "</p>" +
        '<p class="presenter-hook">&ldquo;' + ch.hook + "&rdquo;</p>" +
        '<ul class="presenter-points">' + points + "</ul>";
    } else {
      host.innerHTML = '<p class="presenter-empty">Presenter notes appear here during chapters. ' +
        "Toggle with the button above or the P key.</p>";
    }
  }

  function announce(entry) {
    var msg;
    if (entry.type === "step") {
      msg = "Chapter " + entry.ch.number + ", step " + entry.stepNum + " of " + entry.stepCount +
        ": " + entry.step.tooltip +
        (entry.step.advance === "hotspot"
          ? " Activate the highlighted control or press Right Arrow to continue."
          : " Press Right Arrow or Next to continue.");
    } else if (entry.type === "title") {
      msg = ACT_NAMES[entry.ch.act] + ". Chapter " + entry.ch.number + ": " + entry.ch.title +
        ". " + entry.ch.hook;
    } else if (entry.id === "start") {
      msg = "Start screen. Amazon WorkSpaces: From Zero to Agentic, an interactive demo. " +
        "Choose Start the demo, or Skip to What's New.";
    } else if (entry.id === "branch-act1") {
      msg = "End of Act 1. Choose: continue to Day-2 Operations, or skip to What's New.";
    } else {
      msg = "Wrap-up. You have completed the demo.";
    }
    el.live.textContent = msg;
  }

  function updateHash(entry) {
    if (location.hash !== entry.hash) {
      suppressHashEvent = true;
      location.hash = entry.hash;
    }
  }

  /* ---------------------------------------------------------- */
  /* Navigation                                                   */
  /* ---------------------------------------------------------- */

  function setIndex(i) {
    if (i < 0 || i >= sequence.length || i === current) { return; }
    current = i;
    render();
  }

  function next() { setIndex(current + 1); }
  function back() { setIndex(current - 1); }
  function nextFromHotspot() { next(); }

  function gotoHash(hash) {
    var i = indexByHash.hasOwnProperty(hash) ? indexByHash[hash] : 0;
    if (i === current) { render(); return; }
    setIndex(i);
  }

  /* ---------------------------------------------------------- */
  /* Chapter menu                                                 */
  /* ---------------------------------------------------------- */

  function buildMenu() {
    var html = '<button type="button" class="chrome-btn menu-close" id="menu-close">Close</button>' +
      '<p class="menu-title">Contents</p>';
    html += '<button type="button" class="menu-item" data-goto="#start">Start screen' +
      '<span class="menu-sub">Title and overview</span></button>';
    [1, 2, 3].forEach(function (act) {
      html += '<p class="menu-act">' + ACT_NAMES[act] + "</p>";
      CHAPTER_ORDER.forEach(function (id) {
        var ch = chapters[id];
        if (!ch || ch.act !== act) { return; }
        html += '<button type="button" class="menu-item" data-goto="#' + id + '-title" data-menu-ch="' + id + '">' +
          "Chapter " + ch.number + " \u00B7 " + ch.title +
          '<span class="menu-sub">' + ch.steps.length + " steps</span></button>";
      });
    });
    html += '<p class="menu-act">Finish</p>' +
      '<button type="button" class="menu-item" data-goto="#wrap-up">Wrap-up' +
      '<span class="menu-sub">Recap and next steps</span></button>';
    el.menuPanel.innerHTML = html;
    document.getElementById("menu-close").addEventListener("click", closeMenu);
  }

  function openMenu() {
    // Highlight current chapter
    var entry = sequence[current];
    var items = el.menuPanel.querySelectorAll(".menu-item");
    for (var i = 0; i < items.length; i++) { items[i].classList.remove("current"); }
    if (entry && entry.ch) {
      var cur = el.menuPanel.querySelector('[data-menu-ch="' + entry.ch.id + '"]');
      if (cur) { cur.classList.add("current"); }
    }
    el.menuOverlay.hidden = false;
    el.btnMenu.setAttribute("aria-expanded", "true");
    var first = el.menuPanel.querySelector(".menu-item");
    if (first) { first.focus(); }
  }

  function closeMenu() {
    el.menuOverlay.hidden = true;
    el.btnMenu.setAttribute("aria-expanded", "false");
    el.btnMenu.focus();
  }

  function menuIsOpen() { return !el.menuOverlay.hidden; }

  /* ---------------------------------------------------------- */
  /* Presenter mode                                               */
  /* ---------------------------------------------------------- */

  function storageGet(key) {
    try { return window.sessionStorage.getItem(key); } catch (e) { return null; }
  }
  function storageSet(key, val) {
    try { window.sessionStorage.setItem(key, val); } catch (e) { /* in-memory only */ }
  }

  function setPresenter(on) {
    presenterOn = on;
    el.presenterPanel.hidden = !on;
    el.btnPresenter.setAttribute("aria-pressed", on ? "true" : "false");
    storageSet("riv26-demo-presenter", on ? "1" : "0");
    applyScale();
  }

  /* ---------------------------------------------------------- */
  /* Scaling                                                      */
  /* ---------------------------------------------------------- */

  function applyScale() {
    var stage = el.stage;
    var pad = 28;
    var s = Math.min(
      (stage.clientWidth - pad) / CANVAS_W,
      (stage.clientHeight - pad) / CANVAS_H
    );
    s = Math.max(0.2, Math.min(s, 2));
    el.canvas.style.transform = "scale(" + s + ")";
  }

  /* ---------------------------------------------------------- */
  /* Events                                                       */
  /* ---------------------------------------------------------- */

  function bindEvents() {
    el.btnNext.addEventListener("click", next);
    el.btnBack.addEventListener("click", back);
    el.btnMenu.addEventListener("click", function () {
      menuIsOpen() ? closeMenu() : openMenu();
    });
    el.btnPresenter.addEventListener("click", function () { setPresenter(!presenterOn); });

    // Any [data-goto] element (special views, menu items) navigates.
    document.addEventListener("click", function (e) {
      var t = e.target.closest ? e.target.closest("[data-goto]") : null;
      if (t) {
        if (menuIsOpen()) { closeMenu(); }
        gotoHash(t.getAttribute("data-goto"));
      }
    });

    // Scrim click closes menu.
    el.menuOverlay.addEventListener("click", function (e) {
      if (e.target === el.menuOverlay) { closeMenu(); }
    });

    window.addEventListener("hashchange", function () {
      if (suppressHashEvent) { suppressHashEvent = false; return; }
      gotoHash(location.hash || "#start");
    });

    window.addEventListener("resize", applyScale);

    document.addEventListener("keydown", function (e) {
      if (e.ctrlKey || e.metaKey || e.altKey) { return; }
      if (menuIsOpen()) {
        if (e.key === "Escape") { e.preventDefault(); closeMenu(); }
        return;
      }
      var onInteractive = e.target && e.target.closest &&
        e.target.closest("button, a, input, select, textarea, [role='button']");
      switch (e.key) {
        case "ArrowRight":
        case "PageDown":
          e.preventDefault(); next(); break;
        case "ArrowLeft":
        case "PageUp":
          e.preventDefault(); back(); break;
        case "Enter":
          if (!onInteractive) { e.preventDefault(); next(); }
          break;
        case "m": case "M":
          openMenu(); break;
        case "p": case "P":
          setPresenter(!presenterOn); break;
      }
    });
  }

  /* ---------------------------------------------------------- */
  /* Startup                                                      */
  /* ---------------------------------------------------------- */

  DEMO.start = function () {
    el.stage = document.getElementById("stage");
    el.canvas = document.getElementById("stage-canvas");
    el.screen = document.getElementById("canvas-screen");
    el.ring = document.getElementById("hotspot-ring");
    el.callout = document.getElementById("step-callout");
    el.btnNext = document.getElementById("btn-next");
    el.btnBack = document.getElementById("btn-back");
    el.btnMenu = document.getElementById("btn-menu");
    el.btnPresenter = document.getElementById("btn-presenter");
    el.positionText = document.getElementById("position-text");
    el.progressFill = document.getElementById("progress-fill");
    el.progressPct = document.getElementById("progress-pct");
    el.progressTrack = document.getElementById("progress-track");
    el.menuOverlay = document.getElementById("menu-overlay");
    el.menuPanel = document.getElementById("menu-panel");
    el.presenterPanel = document.getElementById("presenter-panel");
    el.presenterBody = document.getElementById("presenter-body");
    el.live = document.getElementById("live-region");

    selfCheck();
    injectChapterStyles();
    buildSequence();
    buildMenu();
    bindEvents();

    if (storageGet("riv26-demo-presenter") === "1") { setPresenter(true); }

    applyScale();
    current = -1;
    gotoHash(location.hash && indexByHash.hasOwnProperty(location.hash) ? location.hash : "#start");
  };

  window.DEMO = DEMO;
})();
