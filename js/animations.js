/* ==========================================================================
   Ibn Sina Hospital — Animations
   Loaded after GSAP + ScrollTrigger. All animations are additive — pages
   render fully without JS.
   ========================================================================== */
'use strict';

(function () {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') return;

  gsap.registerPlugin(ScrollTrigger);

  const mm = gsap.matchMedia();

  // ---- Hero: scale/fade, NO opacity:0 on the LCP element ----
  // Rule: never animate opacity on hero-title, hero-subtitle, or hero-ctas.
  // Instead animate `y` from a small positive offset — this keeps the element
  // visible from the first paint even if GSAP fails.

  mm.add('(min-width: 769px)', () => {
    const hero = document.querySelector('.hero');
    if (hero) {
      gsap.from('.hero-title', { y: 30, duration: 0.9, ease: 'power3.out' });
      gsap.from('.hero-subtitle', { y: 24, duration: 0.9, delay: 0.15, ease: 'power3.out' });
      gsap.from('.hero-ctas .btn', {
        y: 20,
        duration: 0.7,
        delay: 0.3,
        stagger: 0.08,
        ease: 'power3.out',
      });
    }
  });

  // ---- Section headings: subtle clip-path reveal ----
  gsap.utils.toArray('.section-title').forEach(title => {
    gsap.from(title, {
      y: 24,
      duration: 0.8,
      ease: 'power2.out',
      scrollTrigger: { trigger: title, start: 'top 88%', once: true },
    });
  });

  // ---- Cards: batch stagger on scroll ----
  const cardSelectors = [
    '.card',
    '.doctor-card',
    '.blog-card',
    '.why-card',
    '.process-step',
    '.explore-card',
    '.faq-item',
    '.stat-card',
    '.testimonial-card',
  ];
  cardSelectors.forEach(sel => {
    const els = gsap.utils.toArray(sel);
    if (!els.length) return;
    ScrollTrigger.batch(els, {
      start: 'top 92%',
      once: true,
      onEnter: batch =>
        gsap.from(batch, {
          y: 30,
          duration: 0.65,
          stagger: 0.07,
          ease: 'power2.out',
          clearProps: 'transform',
        }),
    });
  });

  // ---- Section lead: gentle rise ----
  gsap.utils.toArray('.section-lead').forEach(el => {
    gsap.from(el, {
      y: 20,
      duration: 0.7,
      ease: 'power2.out',
      scrollTrigger: { trigger: el, start: 'top 90%', once: true },
    });
  });

  // ---- CTA banner rise ----
  const cta = document.querySelector('.cta-banner');
  if (cta) {
    gsap.from('.cta-banner-inner', {
      y: 40,
      duration: 0.8,
      ease: 'power2.out',
      scrollTrigger: { trigger: cta, start: 'top 82%', once: true },
    });
  }

  // ---- Refresh on load ----
  window.addEventListener('load', () => ScrollTrigger.refresh());
})();
