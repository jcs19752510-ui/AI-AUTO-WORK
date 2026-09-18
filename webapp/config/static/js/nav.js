/*
 * 모바일 내비게이션 드로어 — 점진적 향상(04-ux-design.md §0/§6).
 * JS 없이도 #nav-menu는 [hidden] 속성이 없는 일반 목록으로 렌더링되어
 * 모든 메뉴 항목이 그대로 노출/사용 가능하다(핵심 기능은 JS 비의존).
 * 이 스크립트는 모바일 폭에서 메뉴를 접고, 포커스를 관리(WCAG 2.4.3)하는
 * 향상 기능만 추가한다.
 */
(function () {
  "use strict";

  var toggle = document.getElementById("nav-toggle");
  var menu = document.getElementById("nav-menu");
  if (!toggle || !menu) {
    return;
  }

  var mobileQuery = window.matchMedia("(max-width: 767px)");

  function isMobile() {
    return mobileQuery.matches;
  }

  function closeMenu(returnFocus) {
    menu.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
    if (returnFocus) {
      toggle.focus();
    }
  }

  function openMenu() {
    menu.hidden = false;
    toggle.setAttribute("aria-expanded", "true");
    var firstLink = menu.querySelector("a");
    if (firstLink) {
      firstLink.focus();
    }
  }

  if (isMobile()) {
    closeMenu(false);
  }

  toggle.addEventListener("click", function () {
    if (menu.hidden) {
      openMenu();
    } else {
      closeMenu(false);
    }
  });

  menu.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && isMobile()) {
      closeMenu(true);
    }
  });

  window.addEventListener("resize", function () {
    if (!isMobile()) {
      menu.hidden = false;
      toggle.setAttribute("aria-expanded", "false");
    } else if (toggle.getAttribute("aria-expanded") !== "true") {
      menu.hidden = true;
    }
  });
})();
