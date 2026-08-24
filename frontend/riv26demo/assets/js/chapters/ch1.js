/* ============================================================
   Amazon WorkSpaces: From Zero to Agentic — re:Invent 2026 demo
   ch1.js — Chapter 1: Why Virtual Desktops? (Act 1)

   Chapter content file. Per the engine.js contract it registers
   itself via DEMO.registerChapter at parse time and does nothing
   else (no DOM access; screen functions run only when rendered
   inside the 1600x900 stage canvas).

   Steps:
     s1  Distributed-workforce map (inline SVG)     advance: next
     s2  Traditional VDI pain points (3 cards)      advance: next
     s3  "What if it was just... a service?" CTA    advance: hotspot
   ============================================================ */

(function () {
  "use strict";

  /* ----------------------------------------------------------
     Inline-SVG helpers — pure string builders, no DOM access.
     Palette on the dark slide: #fff primary, #9aa7bd secondary,
     #ec7211 accent.
     ---------------------------------------------------------- */

  var GLYPH = {
    hq:
      '<rect x="-11" y="-15" width="22" height="29" rx="1.5"/>' +
      '<rect x="-6.5" y="-10" width="5" height="5" fill="#fff" stroke="none"/>' +
      '<rect x="1.5" y="-10" width="5" height="5" fill="#fff" stroke="none"/>' +
      '<rect x="-6.5" y="-2" width="5" height="5" fill="#fff" stroke="none"/>' +
      '<rect x="1.5" y="-2" width="5" height="5" fill="#fff" stroke="none"/>' +
      '<path d="M -3 14 V 7 H 3 V 14"/>',

    home:
      '<path d="M -14 1 L 0 -12 L 14 1"/>' +
      '<path d="M -10 -1 V 13 H 10 V -1"/>' +
      '<path d="M -3 13 V 6 H 3 V 13"/>',

    cafe:
      '<circle cx="0" cy="9" r="2.4" fill="#fff" stroke="none"/>' +
      '<path d="M -6 3 A 8.5 8.5 0 0 1 6 3"/>' +
      '<path d="M -11 -3 A 15.5 15.5 0 0 1 11 -3"/>' +
      '<path d="M -16 -9 A 22.5 22.5 0 0 1 16 -9"/>',

    contractor:
      '<circle cx="0" cy="-7" r="5.5"/>' +
      '<path d="M -11 14 A 11 11 0 0 1 11 14"/>',

    regulated:
      '<path d="M 0 -14 L 11 -9.5 L 11 0.5 C 11 8.5 6.5 12.8 0 15.5 C -6.5 12.8 -11 8.5 -11 0.5 L -11 -9.5 Z"/>' +
      '<path d="M -4.5 0.5 L -1 4 L 5.5 -3.5"/>'
  };

  var PAIN_GLYPH = {
    capex:
      '<rect x="-17" y="-11" width="34" height="22" rx="3"/>' +
      '<circle cx="0" cy="0" r="5.5"/>' +
      '<line x1="-11" y1="0" x2="-8" y2="0"/>' +
      '<line x1="8" y1="0" x2="11" y2="0"/>',

    stack:
      '<rect x="-16" y="-14" width="32" height="8" rx="2"/>' +
      '<rect x="-16" y="-4" width="32" height="8" rx="2"/>' +
      '<rect x="-16" y="6" width="32" height="8" rx="2"/>' +
      '<circle cx="-11" cy="-10" r="1.5" fill="#ec7211" stroke="none"/>' +
      '<circle cx="-11" cy="0" r="1.5" fill="#ec7211" stroke="none"/>' +
      '<circle cx="-11" cy="10" r="1.5" fill="#ec7211" stroke="none"/>',

    gauge:
      '<path d="M -14 7 A 14 14 0 0 1 14 7"/>' +
      '<line x1="0" y1="7" x2="10" y2="-3"/>' +
      '<circle cx="0" cy="7" r="2" fill="#ec7211" stroke="none"/>'
  };

  function endpointNode(x, y, label, glyph) {
    return (
      '<g transform="translate(' + x + " " + y + ')">' +
        '<circle r="36" fill="none" stroke="#9aa7bd" stroke-width="2"/>' +
        '<g fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
          glyph +
        "</g>" +
        '<text y="62" text-anchor="middle" font-size="17" fill="#fff">' + label + "</text>" +
      "</g>"
    );
  }

  function streamLine(x1, y1, x2, y2) {
    return '<line x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '"/>';
  }

  /** Distributed workforce: five endpoints, encrypted streams, one Region. */
  function workforceDiagram() {
    return (
      '<div class="ch1-map-wrap" data-hotspot="workforce-map">' +
        '<svg class="ch1-map" viewBox="0 0 1000 420" width="1000" height="420" role="img" aria-label="Five user locations - headquarters, home office, cafe Wi-Fi, a contractor, and a regulated site - connect over dashed encrypted streams to a desktop running inside an AWS Region cloud.">' +

          /* Encrypted streams converging on the Region */
          '<g stroke="#9aa7bd" stroke-width="2" stroke-dasharray="7 7" stroke-linecap="round">' +
            streamLine(189, 90, 402, 142) +
            streamLine(145, 210, 356, 201) +
            streamLine(187, 330, 398, 252) +
            streamLine(821, 125, 652, 156) +
            streamLine(822, 294, 658, 243) +
          "</g>" +

          /* AWS Region cloud */
          '<path d="M 400 250 A 52 52 0 0 1 400 150 A 70 70 0 0 1 530 115 A 62 62 0 0 1 640 160 A 47 47 0 0 1 640 250 Z" fill="none" stroke="#ec7211" stroke-width="3" stroke-linejoin="round"/>' +

          /* Desktop glyph inside the cloud */
          '<g fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round">' +
            '<rect x="452" y="150" width="130" height="78" rx="6"/>' +
            '<line x1="517" y1="228" x2="517" y2="239"/>' +
            '<line x1="488" y1="240" x2="546" y2="240"/>' +
          "</g>" +
          '<g stroke="#9aa7bd" stroke-width="2" stroke-linecap="round">' +
            '<line x1="452" y1="170" x2="582" y2="170"/>' +
            '<line x1="466" y1="190" x2="540" y2="190"/>' +
            '<line x1="466" y1="206" x2="516" y2="206"/>' +
          "</g>" +
          '<text x="517" y="288" text-anchor="middle" font-size="18" font-weight="700" fill="#fff">AWS Region</text>' +

          /* Endpoints */
          endpointNode(150, 80, "HQ", GLYPH.hq) +
          endpointNode(105, 212, "Home office", GLYPH.home) +
          endpointNode(150, 344, "Cafe Wi-Fi", GLYPH.cafe) +
          endpointNode(860, 118, "Contractor", GLYPH.contractor) +
          endpointNode(860, 306, "Regulated site", GLYPH.regulated) +

          /* Legend */
          '<line x1="260" y1="398" x2="316" y2="398" stroke="#9aa7bd" stroke-width="2" stroke-dasharray="7 7" stroke-linecap="round"/>' +
          '<text x="328" y="403" font-size="15" fill="#9aa7bd">Encrypted streams &mdash; pixels travel, application data stays in the Region</text>' +
        "</svg>" +
      "</div>"
    );
  }

  function painCard(glyph, heading, body) {
    return (
      '<div class="slide-card">' +
        '<svg class="pain-glyph" viewBox="-28 -28 56 56" aria-hidden="true" focusable="false">' +
          '<g fill="none" stroke="#ec7211" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">' +
            glyph +
          "</g>" +
        "</svg>" +
        "<h3>" + heading + "</h3>" +
        "<p>" + body + "</p>" +
      "</div>"
    );
  }

  /* ----------------------------------------------------------
     Chapter-scoped styles (every rule prefixed with .ch1).
     ---------------------------------------------------------- */

  var STYLES = [
    ".ch1 .ch1-map-wrap { width: 1000px; max-width: 94%; margin: 28px auto 0; }",
    ".ch1 .ch1-map { display: block; width: 100%; height: auto; }",
    ".ch1 .ch1-map text { font-family: var(--font-ui); }",
    ".ch1 .ch1-cards { margin-top: 44px; }",
    ".ch1 .slide-card { text-align: center; }",
    ".ch1 .slide-card h3 { margin: 0 0 10px; font-size: 23px; font-weight: 700; color: #fff; }",
    ".ch1 .slide-card p { margin: 0; font-size: 17px; line-height: 1.55; color: #9aa7bd; }",
    ".ch1 .pain-glyph { display: block; width: 54px; height: 54px; margin: 0 auto 16px; }",
    ".ch1 .ch1-statement { font-size: 66px; line-height: 1.12; letter-spacing: -1px; }",
    ".ch1 .ch1-sub-wide { max-width: 880px; margin-left: auto; margin-right: auto; }",
    ".ch1 .ch1-cta-row { margin-top: 48px; }",
    ".ch1 .ch1-cta { display: inline-block; background: #ec7211; color: #16191f; font-size: 22px; font-weight: 700; padding: 16px 38px; border-radius: 10px; cursor: pointer; letter-spacing: 0.2px; box-shadow: 0 8px 22px rgba(236, 114, 17, 0.35); }",
    ".ch1 .ch1-cta:hover { background: #eb5f07; }"
  ].join("\n");

  /* ----------------------------------------------------------
     Chapter registration
     ---------------------------------------------------------- */

  DEMO.registerChapter({
    id: "ch1",
    act: 1,
    number: 1,
    title: "Why Virtual Desktops?",
    hook: "Your users are everywhere. Your data shouldn't be.",
    talkingPoints: [
      "Security & compliance: data never leaves the cloud",
      "Elasticity: scale up for a project, scale down after",
      "Global reach: deploy desktops in any AWS Region"
    ],
    styles: STYLES,
    steps: [

      /* s1 — the modern workforce ------------------------------ */
      {
        id: "s1",
        screen: function () {
          return DEMO.frames.slide(
            '<div class="slide-kicker">The modern workforce</div>' +
            '<div class="slide-title">Your users are everywhere. Your data shouldn&rsquo;t be.</div>' +
            '<div class="slide-sub">Hybrid employees, contractors, BYOD, regulated industries &mdash; they all need a secure desktop, wherever they sit.</div>' +
            workforceDiagram()
          );
        },
        tooltip: "Enterprises need secure desktop access from anywhere \u2014 without shipping hardware.",
        target: "[data-hotspot='workforce-map']",
        placement: "bottom-right",
        advance: "next"
      },

      /* s2 — traditional VDI pain ------------------------------ */
      {
        id: "s2",
        screen: function () {
          return DEMO.frames.slide(
            '<div class="slide-kicker">Traditional VDI pain</div>' +
            '<div class="slide-title">Owning the whole stack means owning every problem</div>' +
            '<div class="slide-sub">On-premises VDI can put a desktop anywhere too &mdash; once you&rsquo;ve built a data center&rsquo;s worth of plumbing.</div>' +
            '<div class="slide-row ch1-cards" data-hotspot="vdi-pain">' +
              painCard(PAIN_GLYPH.capex, "Capital-heavy",
                "Millions in CAPEX before the first desktop boots &mdash; hardware, licenses, and a 3&ndash;5 year refresh treadmill.") +
              painCard(PAIN_GLYPH.stack, "Complex",
                "Months of planning across hypervisors, storage arrays, and networking &mdash; plus the specialists to keep it all running.") +
              painCard(PAIN_GLYPH.gauge, "Over-provisioned and risky",
                "Sized for a peak that rarely comes, while corporate data sits on every endpoint.") +
            "</div>"
          );
        },
        tooltip: "Traditional VDI means months of planning, millions in CAPEX, and ongoing management headaches.",
        target: "[data-hotspot='vdi-pain']",
        placement: "bottom-right",
        advance: "next"
      },

      /* s3 — the shift to DaaS --------------------------------- */
      {
        id: "s3",
        screen: function () {
          return DEMO.frames.slide(
            '<div class="slide-kicker">The shift</div>' +
            '<div class="slide-title ch1-statement">What if it was just&hellip; a service?</div>' +
            '<div class="slide-sub ch1-sub-wide">Desktop-as-a-Service: request a desktop like any other cloud resource &mdash; no hardware to buy, no infrastructure to run, in any AWS Region, scaled up or down on demand.</div>' +
            '<div class="ch1-cta-row"><span class="ch1-cta" data-hotspot="see-portfolio" role="button" tabindex="0">See the portfolio</span></div>'
          );
        },
        tooltip: "The shift to Desktop-as-a-Service: no hardware to buy, no infrastructure to run. Let's meet the family.",
        target: "[data-hotspot='see-portfolio']",
        placement: "bottom",
        advance: "hotspot"
      }
    ]
  });
})();
