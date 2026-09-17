/*
 * NewsletterSubscribeForm 점진적 향상 (REQ-016, 04-ux-design.md §4).
 *
 * 이 파일은 두 가지 마크업을 상대한다:
 * 1. `[data-newsletter-form]` — 이미 서버가 렌더링해 보낸 실제 폼(캐시되지
 *    않는 subscribers:page 전용 페이지, subscribers/newsletter_page.html).
 * 2. `[data-newsletter-slot]` — 캐시된 공개 페이지(홈/카테고리/태그/게시물
 *    상세)에 남겨진 빈 자리. subscribers/views.py 모듈 docstring이 설명한
 *    이유로 그 페이지들의 캐시된 HTML에는 CSRF 토큰이 담긴 폼을 직접 넣지
 *    않는다 — 대신 이 스크립트가 캐시되지 않는 조각 엔드포인트
 *    (`data-newsletter-fragment-url`)를 fetch해 항상 방문자 본인의 CSRF
 *    쿠키와 일치하는 폼으로 그 자리를 채운다.
 *
 * 무-JS 기본 동작: 슬롯 안의 `<noscript>` 링크가 캐시되지 않는 전용 페이지
 * (`/newsletter/`)로 보내 항상 동작한다(04 §0). 이 스크립트가 실행되면
 * 그 자리를 인라인 폼으로 즉시 대체해 페이지 이동 없이 구독할 수 있게
 * 한다(04 §2 "제출 → 성공/에러 인라인 메시지, 페이지 이동 없음").
 */
(function () {
  "use strict";

  function setFieldError(el, message) {
    if (!el) {
      return;
    }
    if (message) {
      el.textContent = message;
      el.hidden = false;
    } else {
      el.textContent = "";
      el.hidden = true;
    }
  }

  function enhanceForm(form) {
    var statusEl = form.querySelector("[data-newsletter-status]");
    var submitButton = form.querySelector('button[type="submit"]');
    var emailError = form.querySelector('[data-field="email"]');
    var consentError = form.querySelector('[data-field="consent"]');

    function setStatus(message, tone) {
      if (!statusEl) {
        return;
      }
      statusEl.textContent = message;
      statusEl.className = "newsletter-form__status" + (tone ? " newsletter-form__status--" + tone : "");
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();

      setFieldError(emailError, "");
      setFieldError(consentError, "");
      setStatus("전송 중입니다...", "submitting");
      if (submitButton) {
        submitButton.disabled = true;
      }

      fetch(form.getAttribute("action"), {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
        body: new FormData(form),
      })
        .then(function (response) {
          return response
            .json()
            .catch(function () {
              return {};
            })
            .then(function (data) {
              return { status: response.status, data: data };
            });
        })
        .then(function (result) {
          if (submitButton) {
            submitButton.disabled = false;
          }

          if (result.status === 200 && result.data.success) {
            setStatus("구독해주셔서 감사합니다.", "success");
            form.reset();
            return;
          }

          if (result.status === 429) {
            setStatus("요청이 너무 잦습니다. 잠시 후 다시 시도해주세요.", "error");
            return;
          }

          if (result.status === 400 && result.data.errors) {
            setStatus("입력 내용을 다시 확인해 주세요.", "error");
            if (result.data.errors.email) {
              setFieldError(emailError, result.data.errors.email[0].message);
            }
            if (result.data.errors.consent) {
              setFieldError(consentError, result.data.errors.consent[0].message);
            }
            return;
          }

          setStatus("잠시 후 다시 시도해주세요.", "error");
        })
        .catch(function () {
          // 네트워크 오류 시 서버 판정을 알 수 없으므로 일반적인 에러
          // 문구만 보여준다 — 재시도가 가장 단순하고 예측 가능한 복구
          // 경로이므로 무-JS 폴백(실제 페이지 이동)으로 전환하지 않는다.
          if (submitButton) {
            submitButton.disabled = false;
          }
          setStatus("네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", "error");
        });
    });
  }

  document.querySelectorAll("[data-newsletter-form]").forEach(enhanceForm);

  document.querySelectorAll("[data-newsletter-slot]").forEach(function (slot) {
    var fragmentUrl = slot.getAttribute("data-newsletter-fragment-url");
    if (!fragmentUrl) {
      return;
    }
    var formId = slot.getAttribute("data-newsletter-slot") || "";
    var variant = slot.getAttribute("data-newsletter-variant") || "";
    var params = "?form_id=" + encodeURIComponent(formId) + "&variant=" + encodeURIComponent(variant);

    fetch(fragmentUrl + params, { credentials: "same-origin" })
      .then(function (response) {
        return response.ok ? response.text() : null;
      })
      .then(function (html) {
        if (!html) {
          return;
        }
        slot.innerHTML = html;
        var form = slot.querySelector("[data-newsletter-form]");
        if (form) {
          enhanceForm(form);
        }
      })
      .catch(function () {
        // 조용히 무시한다 — fetch가 실패해도 페이지의 다른 기능에는
        // 영향이 없고, 사용자는 여전히 전용 페이지(/newsletter/)로 직접
        // 이동해 구독할 수 있다(다만 JS가 켜진 상태에서 noscript 링크
        // 자체는 브라우저가 렌더링하지 않으므로 이 슬롯은 빈 채로 남는다
        // — 드문 네트워크 실패 상황에서만 발생하는 용인 가능한 트레이드오프).
      });
  });
})();
