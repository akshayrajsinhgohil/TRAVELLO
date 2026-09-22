/* =============================================================================
   Travello — interaction layer
   Everything here degrades gracefully: if a library fails to load or the user
   prefers reduced motion, the page still works and reads correctly.
   ========================================================================== */
(function () {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* --- 1. Scroll reveal ---------------------------------------------------
     One shared observer instead of a library. Elements fade up once, then the
     observer lets them go. */
  function initReveal() {
    const items = document.querySelectorAll("[data-reveal]");
    if (!items.length) return;
    if (reduceMotion || !("IntersectionObserver" in window)) {
      items.forEach((el) => el.classList.add("is-visible"));
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const delay = parseInt(entry.target.dataset.revealDelay || "0", 10);
          setTimeout(() => entry.target.classList.add("is-visible"), delay);
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -60px" }
    );
    items.forEach((el) => observer.observe(el));
  }

  /* --- 2. 3D tilt on trip cards ------------------------------------------
     Pointer position drives a small rotation. Touch devices skip it. */
  function initTilt() {
    if (reduceMotion || !window.matchMedia("(hover: hover)").matches) return;
    document.querySelectorAll("[data-tilt]").forEach((card) => {
      const strength = parseFloat(card.dataset.tilt) || 7;
      card.addEventListener("pointermove", (event) => {
        const rect = card.getBoundingClientRect();
        const x = (event.clientX - rect.left) / rect.width - 0.5;
        const y = (event.clientY - rect.top) / rect.height - 0.5;
        card.style.transform =
          `perspective(900px) rotateX(${(-y * strength).toFixed(2)}deg) ` +
          `rotateY(${(x * strength).toFixed(2)}deg) translateY(-6px)`;
      });
      card.addEventListener("pointerleave", () => {
        card.style.transform = "";
      });
    });
  }

  /* --- 3. Magnetic buttons ------------------------------------------------ */
  function initMagnetic() {
    if (reduceMotion || !window.matchMedia("(hover: hover)").matches) return;
    document.querySelectorAll(".magnetic").forEach((el) => {
      el.addEventListener("pointermove", (event) => {
        const rect = el.getBoundingClientRect();
        const x = event.clientX - rect.left - rect.width / 2;
        const y = event.clientY - rect.top - rect.height / 2;
        el.style.transform = `translate(${x * 0.18}px, ${y * 0.3}px)`;
      });
      el.addEventListener("pointerleave", () => (el.style.transform = ""));
    });
  }

  /* --- 4. Parallax layers ------------------------------------------------- */
  function initParallax() {
    const layers = document.querySelectorAll("[data-parallax]");
    if (!layers.length || reduceMotion) return;
    let ticking = false;
    function update() {
      const scrolled = window.scrollY;
      layers.forEach((layer) => {
        const speed = parseFloat(layer.dataset.parallax) || 0.2;
        layer.style.transform = `translate3d(0, ${(scrolled * speed).toFixed(1)}px, 0)`;
      });
      ticking = false;
    }
    window.addEventListener(
      "scroll",
      () => {
        if (!ticking) {
          window.requestAnimationFrame(update);
          ticking = true;
        }
      },
      { passive: true }
    );
  }

  /* --- 5. Sticky header state --------------------------------------------- */
  function initHeader() {
    const header = document.getElementById("site-header");
    if (!header) return;
    const onScroll = () => {
      header.classList.toggle("is-stuck", window.scrollY > 24);
      header.style.borderBottomColor =
        window.scrollY > 24 ? "rgba(255,255,255,0.10)" : "transparent";
      header.style.background =
        window.scrollY > 24 ? "rgba(14,10,31,0.72)" : "transparent";
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });

    const toggle = document.getElementById("nav-toggle");
    const menu = document.getElementById("mobile-menu");
    if (toggle && menu) {
      toggle.addEventListener("click", () => {
        const open = menu.classList.toggle("hidden");
        toggle.setAttribute("aria-expanded", String(!open));
      });
    }
  }

  /* --- 6. Hero entrance (GSAP when available, CSS fallback otherwise) ------ */
  function initHeroTimeline() {
    const hero = document.getElementById("hero");
    if (!hero) return;
    const lines = hero.querySelectorAll(".hero-line > span");
    const supporting = hero.querySelectorAll("[data-hero-step]");

    if (reduceMotion || typeof window.gsap === "undefined") {
      lines.forEach((l) => (l.style.transform = "none"));
      supporting.forEach((el) => (el.style.opacity = 1));
      return;
    }
    const tl = window.gsap.timeline({ defaults: { ease: "power3.out" } });
    tl.from(lines, { yPercent: 115, duration: 1.05, stagger: 0.09 })
      .from(supporting, { y: 18, opacity: 0, duration: 0.7, stagger: 0.12 }, "-=0.55");
  }

  /* --- 7. Count-up statistics --------------------------------------------- */
  function initCounters() {
    const counters = document.querySelectorAll("[data-count-to]");
    if (!counters.length) return;
    if (reduceMotion || !("IntersectionObserver" in window)) {
      counters.forEach((el) => (el.textContent = el.dataset.countTo));
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        const target = parseFloat(el.dataset.countTo) || 0;
        const started = performance.now();
        const duration = 1200;
        function step(now) {
          const progress = Math.min((now - started) / duration, 1);
          const eased = 1 - Math.pow(1 - progress, 3);
          el.textContent = Math.round(target * eased).toLocaleString();
          if (progress < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
        observer.unobserve(el);
      });
    }, { threshold: 0.5 });
    counters.forEach((el) => observer.observe(el));
  }

  /* --- 8. Wishlist heart -------------------------------------------------- */
  function initWishlist() {
    document.querySelectorAll("[data-wishlist-url]").forEach((button) => {
      button.addEventListener("click", async (event) => {
        event.preventDefault();
        const token = document.querySelector("[name=csrfmiddlewaretoken]");
        if (!token) {
          window.location.href = button.dataset.loginUrl || "/accounts/login/";
          return;
        }
        button.disabled = true;
        try {
          const response = await fetch(button.dataset.wishlistUrl, {
            method: "POST",
            headers: {
              "X-CSRFToken": token.value,
              "X-Requested-With": "XMLHttpRequest",
            },
          });
          if (response.status === 403 || response.redirected) {
            window.location.href = button.dataset.loginUrl || "/accounts/login/";
            return;
          }
          const data = await response.json();
          button.dataset.saved = data.saved ? "1" : "0";
          button.setAttribute("aria-pressed", String(data.saved));
          const icon = button.querySelector("[data-heart]");
          if (icon) icon.textContent = data.saved ? "♥" : "♡";
          const label = button.querySelector("[data-wishlist-label]");
          if (label) label.textContent = data.saved ? "Saved" : "Save this trip";
          button.classList.toggle("text-magenta", data.saved);
        } catch (error) {
          window.location.href = button.dataset.loginUrl || "/accounts/login/";
        } finally {
          button.disabled = false;
        }
      });
    });
  }

  /* --- 9. Live checkout pricing ------------------------------------------- */
  function initQuote() {
    const form = document.getElementById("booking-form");
    if (!form) return;
    const endpoint = form.dataset.quoteUrl;
    const adults = form.querySelector("#id_adults");
    const children = form.querySelector("#id_children");
    const coupon = form.querySelector("#id_coupon_code");
    const output = {
      guests: document.querySelector("[data-quote-guests]"),
      base: document.querySelector("[data-quote-base]"),
      discount: document.querySelector("[data-quote-discount]"),
      discountRow: document.querySelector("[data-quote-discount-row]"),
      tax: document.querySelector("[data-quote-tax]"),
      total: document.querySelector("[data-quote-total]"),
      note: document.querySelector("[data-quote-note]"),
    };
    const symbol = form.dataset.currency || "";

    const money = (value) =>
      symbol + Number(value).toLocaleString(undefined, { maximumFractionDigits: 0 });

    let timer;
    async function refresh() {
      const guests =
        (parseInt(adults?.value, 10) || 0) + (parseInt(children?.value, 10) || 0);
      if (guests < 1) return;
      const url = `${endpoint}?guests=${guests}&coupon=${encodeURIComponent(
        coupon?.value || ""
      )}`;
      try {
        const response = await fetch(url, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        const data = await response.json();
        if (output.guests) output.guests.textContent = data.guests;
        if (output.base) output.base.textContent = money(data.base_amount);
        if (output.tax) output.tax.textContent = money(data.tax_amount);
        if (output.total) output.total.textContent = money(data.total_amount);
        if (output.discount) output.discount.textContent = "−" + money(data.discount_amount);
        if (output.discountRow)
          output.discountRow.classList.toggle("hidden", Number(data.discount_amount) === 0);
        if (output.note) {
          if (coupon && coupon.value && !data.coupon_applied) {
            output.note.textContent = "That code isn't valid right now.";
            output.note.className = "text-xs text-magenta mt-2";
          } else if (data.coupon_applied) {
            output.note.textContent = `${data.coupon_code} applied.`;
            output.note.className = "text-xs text-mint mt-2";
          } else {
            output.note.textContent = "";
          }
        }
      } catch (error) {
        /* Leave the server-rendered figures in place if the request fails. */
      }
    }

    [adults, children, coupon].forEach((field) => {
      if (!field) return;
      field.addEventListener("input", () => {
        clearTimeout(timer);
        timer = setTimeout(refresh, 320);
      });
    });
  }

  /* --- 10. Gallery lightbox ---------------------------------------------- */
  function initGallery() {
    const main = document.getElementById("gallery-main");
    if (!main) return;
    document.querySelectorAll("[data-gallery-thumb]").forEach((thumb) => {
      thumb.addEventListener("click", () => {
        main.src = thumb.dataset.galleryThumb;
        main.alt = thumb.dataset.galleryAlt || main.alt;
        document
          .querySelectorAll("[data-gallery-thumb]")
          .forEach((t) => t.classList.remove("ring-2", "ring-magenta"));
        thumb.classList.add("ring-2", "ring-magenta");
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initReveal();
    initTilt();
    initMagnetic();
    initParallax();
    initHeader();
    initHeroTimeline();
    initCounters();
    initWishlist();
    initQuote();
    initGallery();
  });
})();
