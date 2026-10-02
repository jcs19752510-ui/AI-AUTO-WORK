/*
 * CommentForm 점진적 향상 (REQ-019, 04-ux-design.md §4).
 *
 * static/js/newsletter.js와 동일한 구조를 그대로 따른다:
 * 1. `[data-comment-form]` — 이미 서버가 렌더링해 보낸 실제 폼(캐시되지
 *    않는 comment_write_page.html, 또는 fetch로 채워진 조각).
 * 2. `[data-comment-slot]` — 캐시된 게시물 상세 페이지에 남겨진 빈 자리.
 *    comments/views.py 모듈 docstring이 설명한 이유로 캐시된 HTML에는
 *    CSRF 토큰이 담긴 폼을 직접 넣지 않는다 — 대신 이 스크립트가 캐시되지
 *    않는 조각 엔드포인트(`data-comment-fragment-url`)를 fetch해 항상
 *    방문자 본인의 CSRF 쿠키와 일치하는 폼으로 그 자리를 채운다.
 *
 * 무-JS 기본 동작: 슬롯 안의 `<noscript>` 링크가 캐시되지 않는 전용 페이지
 * (`/blog/<slug>/comment/`)로 보내 항상 동작한다(04 §0).
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
    var statusEl = form.querySelector("[data-comment-status]");
    var submitButton = form.querySelector('button[type="submit"]');
    var authorError = form.querySelector('[data-field="author_name"]');
    var bodyError = form.querySelector('[data-field="body"]');

    function setStatus(message, tone) {
      if (!statusEl) {
        return;
      }
      statusEl.textContent = message;
      statusEl.className = "comment-form__status" + (tone ? " comment-form__status--" + tone : "");
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();

      setFieldError(authorError, "");
      setFieldError(bodyError, "");
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
            setStatus("댓글이 접수되었습니다. 검토 후 게시됩니다.", "success");
            form.reset();
            return;
          }

          if (result.status === 429) {
            setStatus("요청이 너무 잦습니다. 잠시 후 다시 시도해주세요.", "error");
            return;
          }

          if (result.status === 400 && result.data.errors) {
            setStatus("입력 내용을 다시 확인해 주세요.", "error");
            if (result.data.errors.author_name) {
              setFieldError(authorError, result.data.errors.author_name[0].message);
            }
            if (result.data.errors.body) {
              setFieldError(bodyError, result.data.errors.body[0].message);
            }
            return;
          }

          setStatus("잠시 후 다시 시도해주세요.", "error");
        })
        .catch(function () {
          if (submitButton) {
            submitButton.disabled = false;
          }
          setStatus("네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", "error");
        });
    });
  }

  document.querySelectorAll("[data-comment-form]").forEach(enhanceForm);

  document.querySelectorAll("[data-comment-slot]").forEach(function (slot) {
    var fragmentUrl = slot.getAttribute("data-comment-fragment-url");
    var pageId = slot.getAttribute("data-comment-page-id");
    if (!fragmentUrl || !pageId) {
      return;
    }

    fetch(fragmentUrl + "?page_id=" + encodeURIComponent(pageId), { credentials: "same-origin" })
      .then(function (response) {
        return response.ok ? response.text() : null;
      })
      .then(function (html) {
        if (!html) {
          return;
        }
        slot.innerHTML = html;
        var form = slot.querySelector("[data-comment-form]");
        if (form) {
          enhanceForm(form);
        }
      })
      .catch(function () {
        // 조용히 무시한다 — subscribers/static/js/newsletter.js와 동일한
        // 트레이드오프(드문 네트워크 실패 시 용인 가능한 성능 저하).
      });
  });
})();
