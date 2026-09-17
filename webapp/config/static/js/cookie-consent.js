/*
 * CookieConsentBanner (REQ-008, 04-ux-design.md §2 전역 컴포넌트) — 점진적
 * 향상. 배너 마크업은 base.html에 항상 서버 렌더링되어 JS 없이도 안내 문구
 * 자체는 항상 노출된다(04 §0 "모든 화면은 JS 없이도 동작"). 이 스크립트는
 * "확인 후 재방문 시 다시 보여주지 않는" 향상 기능만 추가한다 — 배너는
 * 비모달이라(포커스 트랩 없음) 이 스크립트가 없어도 콘텐츠 열람을 막지 않는다.
 *
 * base.html의 인라인 스크립트(배너 바로 아래)가 이미 페인트 전에 동의 여부를
 * 확인해 숨김 처리를 시도하므로, 이 파일은 "확인" 버튼 클릭 시 저장/숨김과
 * ESC 키 닫기만 담당한다.
 */
(function () {
  "use strict";

  var STORAGE_KEY = "cookie_consent_ack";
  var banner = document.getElementById("cookie-consent");
  var acceptButton = document.getElementById("cookie-consent-accept");
  if (!banner || !acceptButton) {
    return;
  }

  function hasConsentAck() {
    try {
      return !!(window.localStorage && localStorage.getItem(STORAGE_KEY));
    } catch (e) {
      return false;
    }
  }

  function dismiss() {
    banner.hidden = true;
    try {
      if (window.localStorage) {
        localStorage.setItem(STORAGE_KEY, "1");
      }
    } catch (e) {
      // localStorage를 쓸 수 없는 환경(프라이빗 모드 등)이어도 배너를 닫는
      // 동작 자체는 계속 동작해야 하므로 조용히 무시한다 — 다음 방문 시
      // 다시 노출될 수 있다는 것이 이 상황의 정상적인 트레이드오프다.
    }
  }

  if (hasConsentAck()) {
    banner.hidden = true;
  }

  acceptButton.addEventListener("click", function () {
    dismiss();
  });

  banner.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      dismiss();
    }
  });
})();
