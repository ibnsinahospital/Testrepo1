/* ==========================================================================
   Ibn Sina Hospital — Main JS
   Handles: nav, header, data loading, forms, chatbot hooks
   ========================================================================== */
'use strict';

/* --------------------------------------------------------------------------
   CONFIG
   -------------------------------------------------------------------------- */
const DATA_URLS = {
  doctors:     '/data/doctors.json',
  departments: '/data/departments.json',
  blog:        '/data/blog.json',
  careers:     '/data/careers.json',
  gallery:     '/data/gallery.json',
  updates:     '/data/updates.json',
};

const APPOINTMENT_ENDPOINT =
  'https://script.google.com/macros/s/AKfycbwOmEFb0cu0rQ3IzRKrzP9wLNgjXZLUuvpZJWp2xEcZSvuknyppjiavPWST31QNEWoS/exec';

const CACHE_VERSION = document.documentElement.dataset.version || '1';

/* --------------------------------------------------------------------------
   UTILITIES
   -------------------------------------------------------------------------- */
function escapeHTML(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function slugify(text) {
  return String(text || '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function cleanDoctorName(raw) {
  let name = String(raw || '').trim().replace(/\.+$/, '');
  name = name.replace(/^dr\.?\s*/i, '').trim();
  if (!name) return 'Doctor';
  name = name
    .split(/\s+/)
    .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
  return `Dr. ${name}`;
}

function titleCase(str) {
  return String(str || '')
    .toLowerCase()
    .split(' ')
    .map(w => (w ? w.charAt(0).toUpperCase() + w.slice(1) : ''))
    .join(' ');
}

function formatDate(value) {
  if (!value) return '';
  const parts = String(value).split(/[-/]/);
  let d;
  if (parts.length === 3) {
    const [a, b, c] = parts.map(p => parseInt(p, 10));
    if (c > 1900) d = new Date(c, b - 1, a);
    else if (a > 1900) d = new Date(a, b - 1, c);
  }
  if (!d || isNaN(d)) d = new Date(value);
  if (isNaN(d)) return String(value);
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
}

function calculateReadingTime(html) {
  const text = String(html || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
  const words = text ? text.split(' ').length : 0;
  return Math.max(1, Math.ceil(words / 200));
}

function isPublished(post) {
  const v = String((post && (post.is_published || post.isPublished)) || '')
    .toLowerCase().trim();
  return v === 'true' || v === 'yes' || v === '1' || v === 'y';
}

/* --------------------------------------------------------------------------
   JSON FETCH — cacheable, with version query
   -------------------------------------------------------------------------- */
async function fetchJSON(url, { timeout = 8000 } = {}) {
  if (!url) return [];
  const sep = url.includes('?') ? '&' : '?';
  const finalUrl = `${url}${sep}v=${CACHE_VERSION}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const res = await fetch(finalUrl, {
      cache: 'default',
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch (e) {
    console.error('[fetchJSON]', url, e);
    return [];
  } finally {
    clearTimeout(timer);
  }
}

/* --------------------------------------------------------------------------
   HEADER — hamburger, sticky, scroll state
   -------------------------------------------------------------------------- */
function initHeader() {
  const header = document.getElementById('site-header');
  const hamburger = document.getElementById('hamburger');
  const mainNav = document.getElementById('main-nav');
  if (header) {
    const onScroll = () => {
      header.classList.toggle('is-scrolled', window.scrollY > 20);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }
  if (!hamburger || !mainNav) return;

  hamburger.addEventListener('click', () => {
    const open = hamburger.getAttribute('aria-expanded') === 'true';
    hamburger.setAttribute('aria-expanded', String(!open));
    mainNav.classList.toggle('open', !open);
    document.body.style.overflow = !open ? 'hidden' : '';
  });

  mainNav.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', () => {
      hamburger.setAttribute('aria-expanded', 'false');
      mainNav.classList.remove('open');
      document.body.style.overflow = '';
    });
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && mainNav.classList.contains('open')) {
      hamburger.setAttribute('aria-expanded', 'false');
      mainNav.classList.remove('open');
      document.body.style.overflow = '';
      hamburger.focus();
    }
  });
}

/* --------------------------------------------------------------------------
   DOCTORS LISTING
   -------------------------------------------------------------------------- */
async function initDoctorsListing() {
  const grid = document.getElementById('doctor-grid');
  if (!grid) return;

  const filterDept = document.getElementById('filter-department');
  const searchInput = document.getElementById('search-doctor');

  grid.innerHTML = '<div class="skeleton" style="height:240px"></div>'.repeat(6);

  const [doctors, departments] = await Promise.all([
    fetchJSON(DATA_URLS.doctors),
    fetchJSON(DATA_URLS.departments),
  ]);

  if (filterDept) {
    filterDept.innerHTML = '<option value="">All Departments</option>' +
      departments
        .map(d => `<option value="${escapeHTML(d.slug)}">${escapeHTML(titleCase(d.name))}</option>`)
        .join('');
  }

  if (!doctors.length) {
    grid.innerHTML = '<p class="text-center">Doctor list is currently unavailable. Please call 9622552553.</p>';
    return;
  }

  doctors.sort((a, b) => (parseInt(a.display_order, 10) || 0) - (parseInt(b.display_order, 10) || 0));

  const render = () => {
    const dept = filterDept ? filterDept.value.toLowerCase() : '';
    const query = searchInput ? searchInput.value.trim().toLowerCase() : '';

    let filtered = doctors;
    if (dept) {
      filtered = filtered.filter(d =>
        String(d.department || '').toLowerCase().includes(dept.replace(/-/g, ' ')) ||
        String(d.specialty || '').toLowerCase().includes(dept.replace(/-/g, ' '))
      );
    }
    if (query) {
      filtered = filtered.filter(d =>
        [d.name, d.specialty, d.department, d.qualifications]
          .filter(Boolean).join(' ').toLowerCase().includes(query)
      );
    }

    if (!filtered.length) {
      grid.innerHTML = '<p class="text-center">No doctors match your criteria.</p>';
      return;
    }

    grid.innerHTML = filtered.map(d => {
      const name = cleanDoctorName(d.name);
      const slug = 'doctor-' + slugify(d.name);
      const specialty = titleCase(d.specialty || '');
      const photo = d.photo_url
        ? `<img class="doctor-card-img" src="${escapeHTML(d.photo_url)}" alt="${escapeHTML(name)}" loading="lazy" width="96" height="96">`
        : `<div class="doctor-card-placeholder" aria-hidden="true">👨‍⚕️</div>`;
      return `
        <a class="doctor-card" href="doctors/${slug}.html">
          ${photo}
          <h3>${escapeHTML(name)}</h3>
          <p class="doctor-card-specialty">${escapeHTML(specialty)}</p>
          <p class="doctor-card-qual">${escapeHTML(d.qualifications || '')}</p>
          <span class="btn btn-outline btn-sm">View Profile</span>
        </a>`;
    }).join('');
  };

  render();
  if (filterDept) filterDept.addEventListener('change', render);
  if (searchInput) searchInput.addEventListener('input', render);

  const params = new URLSearchParams(window.location.search);
  const deptParam = params.get('dept');
  if (deptParam && filterDept) {
    filterDept.value = deptParam;
    render();
  }
}

/* --------------------------------------------------------------------------
   FEATURED DOCTORS (homepage)
   -------------------------------------------------------------------------- */
async function initFeaturedDoctors() {
  const container = document.getElementById('featured-doctor-cards');
  if (!container) return;

  container.innerHTML = '<div class="skeleton" style="height:240px"></div>'.repeat(3);

  const doctors = await fetchJSON(DATA_URLS.doctors);
  if (!doctors.length) {
    container.innerHTML = '<p class="text-center">Doctor list coming soon.</p>';
    return;
  }

  doctors.sort((a, b) => (parseInt(a.display_order, 10) || 0) - (parseInt(b.display_order, 10) || 0));
  const featured = doctors.slice(0, 6);

  container.innerHTML = featured.map(d => {
    const name = cleanDoctorName(d.name);
    const slug = 'doctor-' + slugify(d.name);
    const specialty = titleCase(d.specialty || '');
    const photo = d.photo_url
      ? `<img class="doctor-card-img" src="${escapeHTML(d.photo_url)}" alt="${escapeHTML(name)}" loading="lazy" width="96" height="96">`
      : `<div class="doctor-card-placeholder" aria-hidden="true">👨‍⚕️</div>`;
    return `
      <a class="doctor-card" href="doctors/${slug}.html">
        ${photo}
        <h3>${escapeHTML(name)}</h3>
        <p class="doctor-card-specialty">${escapeHTML(specialty)}</p>
        <p class="doctor-card-qual">${escapeHTML(d.qualifications || '')}</p>
        <span class="btn btn-outline btn-sm">View Profile</span>
      </a>`;
  }).join('');
}

/* --------------------------------------------------------------------------
   DEPARTMENTS GRID
   -------------------------------------------------------------------------- */
async function initDepartmentsGrid() {
  const grid = document.getElementById('departments-grid');
  if (!grid) return;

  const departments = await fetchJSON(DATA_URLS.departments);
  if (!departments.length) {
    grid.innerHTML = '<p class="text-center">Departments list unavailable.</p>';
    return;
  }

  const isHomepage = /(^\/$|\/index\.html$)/.test(location.pathname);
  const display = isHomepage ? departments.slice(0, 6) : departments;

  grid.innerHTML = display.map(d => `
    <a class="explore-card" href="department-pages/${escapeHTML(d.slug)}.html">
      <span class="explore-card-icon" aria-hidden="true">🏥</span>
      <h3>${escapeHTML(titleCase(d.name))}</h3>
    </a>`).join('');
}

/* --------------------------------------------------------------------------
   BLOG LISTING
   -------------------------------------------------------------------------- */
async function initBlogListings() {
  const previewGrid = document.getElementById('blog-preview-grid');
  const fullGrid = document.getElementById('blog-grid');

  if (previewGrid) {
    previewGrid.innerHTML = '<div class="skeleton" style="height:320px"></div>'.repeat(3);
    const posts = await fetchJSON(DATA_URLS.blog);
    const published = posts
      .filter(isPublished)
      .sort((a, b) => new Date(b.published_at || 0) - new Date(a.published_at || 0))
      .slice(0, 3);
    if (!published.length) {
      previewGrid.innerHTML = '<p class="text-center">No blog posts yet.</p>';
    } else {
      previewGrid.innerHTML = published.map(renderBlogCard).join('');
    }
  }

  if (fullGrid) {
    fullGrid.innerHTML = '<div class="skeleton" style="height:320px"></div>'.repeat(6);
    const posts = await fetchJSON(DATA_URLS.blog);
    const published = posts
      .filter(isPublished)
      .sort((a, b) => new Date(b.published_at || 0) - new Date(a.published_at || 0));
    if (!published.length) {
      fullGrid.innerHTML = '<p class="text-center">No blog posts yet.</p>';
    } else {
      fullGrid.innerHTML = published.map(renderBlogCard).join('');
    }
  }
}

function renderBlogCard(p) {
  const url = `blog/blog-${escapeHTML(p.slug)}.html`;
  const image = p.cover_image_url
    ? `<a href="${url}" aria-hidden="true" tabindex="-1"><img class="blog-card-image" src="${escapeHTML(p.cover_image_url)}" alt="${escapeHTML(p.title)}" loading="lazy" width="600" height="200"></a>`
    : '';
  const category = escapeHTML(p.category || 'Health');
  const date = formatDate(p.published_at);
  const reading = calculateReadingTime(p.body);
  const summary = escapeHTML(p.short_summary || p['short summary'] || '');
  return `
    <article class="blog-card">
      ${image}
      <div class="blog-card-body">
        <div class="blog-card-meta">
          <span class="blog-card-category">${category}</span>
          <time datetime="${escapeHTML(p.published_at || '')}" class="blog-card-date">${escapeHTML(date)}</time>
        </div>
        <h3><a href="${url}">${escapeHTML(p.title)}</a></h3>
        <p>${summary}</p>
        <div class="blog-card-footer">
          <span class="blog-card-readtime">${reading} min read</span>
          <a href="${url}" class="blog-card-link">Read Article →</a>
        </div>
      </div>
    </article>`;
}

/* --------------------------------------------------------------------------
   UPDATES CAROUSEL
   -------------------------------------------------------------------------- */
async function initUpdatesCarousel() {
  const container = document.getElementById('updates-carousel');
  if (!container) return;

  let updates = await fetchJSON(DATA_URLS.updates);
  const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;
  const cutoff = Date.now() - THIRTY_DAYS_MS;

  updates = updates.filter(u => {
    const d = new Date(u.date || 0);
    return !isNaN(d) && d.getTime() >= cutoff;
  });

  if (!updates.length) {
    container.style.display = 'none';
    return;
  }

  updates.sort((a, b) => new Date(b.date || 0) - new Date(a.date || 0));

  let index = 0;
  let autoTimer = null;

  function isImageURL(url) {
    return url && /\.(jpe?g|png|gif|webp|svg|bmp)(\?.*)?$/i.test(url);
  }

  function isVideoURL(url) {
    return url && (url.includes('youtube.com/embed') || url.includes('vimeo.com') || /\.mp4($|\?)/i.test(url));
  }

  const slides = updates.map(u => {
    const media = u.media_url || u.image_url || u.link;
    let mediaHTML = '';
    if (media && isVideoURL(media)) {
      mediaHTML = `<div class="carousel-slide-media" style="padding:0"><iframe src="${escapeHTML(media)}" loading="lazy" style="width:100%;height:100%;border:0" title="${escapeHTML(u.title || 'Update')}"></iframe></div>`;
    } else if (media && isImageURL(media)) {
      mediaHTML = `<div class="carousel-slide-media" style="background-image:url('${escapeHTML(media)}')" role="img" aria-label="${escapeHTML(u.title || 'Update')}"></div>`;
    }
    const title = u.link && !isImageURL(u.link) && !isVideoURL(u.link)
      ? `<a href="${escapeHTML(u.link)}" target="_blank" rel="noopener">${escapeHTML(u.title)}</a>`
      : escapeHTML(u.title);
    return `
      <li class="carousel-slide" aria-hidden="${updates.length > 1 ? 'true' : 'false'}">
        ${mediaHTML}
        <div class="carousel-slide-body">
          <h3>${title}</h3>
          <p>${escapeHTML(u.description || '').replace(/\\n/g, ' ')}</p>
          <time datetime="${escapeHTML(u.date || '')}">${escapeHTML(formatDate(u.date))}</time>
        </div>
      </li>`;
  }).join('');

  const dots = updates.map((_, i) =>
    `<button type="button" class="carousel-dot${i === 0 ? ' active' : ''}" data-index="${i}" aria-label="Go to update ${i + 1}"></button>`
  ).join('');

  container.innerHTML = `
    <div class="updates-carousel" role="region" aria-roledescription="carousel" aria-label="Latest hospital updates">
      <button type="button" class="carousel-nav prev" aria-label="Previous update">‹</button>
      <ul class="carousel-track">${slides}</ul>
      <button type="button" class="carousel-nav next" aria-label="Next update">›</button>
      <div class="carousel-dots">${dots}</div>
    </div>`;

  const track = container.querySelector('.carousel-track');
  const slideEls = container.querySelectorAll('.carousel-slide');
  const dotEls = container.querySelectorAll('.carousel-dot');
  const prev = container.querySelector('.carousel-nav.prev');
  const next = container.querySelector('.carousel-nav.next');

  function goTo(i) {
    index = (i + updates.length) % updates.length;
    track.style.transform = `translateX(-${index * 100}%)`;
    dotEls.forEach((d, j) => d.classList.toggle('active', j === index));
    slideEls.forEach((s, j) => s.setAttribute('aria-hidden', String(j !== index)));
  }

  function startAuto() {
    if (updates.length < 2) return;
    stopAuto();
    autoTimer = setInterval(() => goTo(index + 1), 6000);
  }
  function stopAuto() {
    if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
  }

  prev.addEventListener('click', () => { goTo(index - 1); startAuto(); });
  next.addEventListener('click', () => { goTo(index + 1); startAuto(); });
  dotEls.forEach(dot => dot.addEventListener('click', () => {
    goTo(parseInt(dot.dataset.index, 10));
    startAuto();
  }));

  container.addEventListener('mouseenter', stopAuto);
  container.addEventListener('mouseleave', startAuto);
  container.addEventListener('focusin', stopAuto);
  container.addEventListener('focusout', startAuto);

  goTo(0);
  startAuto();
}

/* --------------------------------------------------------------------------
   APPOINTMENT FORM — with real success feedback
   -------------------------------------------------------------------------- */
function initAppointmentForms() {
  document.querySelectorAll('form[data-form="appointment"], #appointment-form').forEach(form => {
    if (form.dataset.bound === 'true') return;
    form.dataset.bound = 'true';

    const success = form.parentElement.querySelector('[data-form-success]');
    const errorEl = form.parentElement.querySelector('[data-form-error]');
    const submitBtn = form.querySelector('button[type="submit"]');

    form.addEventListener('submit', async e => {
      e.preventDefault();

      if (submitBtn) { submitBtn.disabled = true; submitBtn.dataset.originalText = submitBtn.textContent; submitBtn.textContent = 'Sending…'; }
      if (errorEl) { errorEl.style.display = 'none'; errorEl.textContent = ''; }

      const formData = new FormData(form);

      // Honeypot check
      if (formData.get('website')) {
        // Silent success for bots
        showSuccess();
        return;
      }

      try {
        const response = await fetch(form.action, {
          method: 'POST',
          body: formData,
          mode: 'no-cors', // Apps Script — response is opaque
        });
        // With no-cors we can't check status; treat any non-throwing response as success
        showSuccess();
      } catch (err) {
        console.error('Appointment submit failed:', err);
        if (errorEl) {
          errorEl.textContent = 'We could not submit your request. Please call 9622552553 so we can help.';
          errorEl.style.display = 'block';
        }
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = submitBtn.dataset.originalText || 'Submit';
        }
      }
    });

    function showSuccess() {
      if (success) {
        form.style.display = 'none';
        success.style.display = 'block';
        success.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } else {
        form.innerHTML = '<p class="form-success">Thank you — our team will call you shortly to confirm.</p>';
      }
    }
  });
}

/* --------------------------------------------------------------------------
   CONTACT / CAREERS FORMS (mailto based)
   -------------------------------------------------------------------------- */
function initContactForm() {
  const form = document.getElementById('contact-form');
  if (!form) return;
  form.addEventListener('submit', e => {
    e.preventDefault();
    const data = new FormData(form);
    const body = [
      `Name: ${data.get('name') || ''}`,
      `Phone: ${data.get('phone') || ''}`,
      `Email: ${data.get('email') || ''}`,
      '',
      data.get('message') || '',
    ].join('\n');
    const url = `mailto:weibnsina@gmail.com?subject=${encodeURIComponent('Website enquiry')}&body=${encodeURIComponent(body)}`;
    window.location.href = url;
  });
}

function initCareersForm() {
  const form = document.getElementById('careers-form');
  if (!form) return;
  form.addEventListener('submit', e => {
    e.preventDefault();
    const data = new FormData(form);
    const body = [
      `Position: ${data.get('position') || ''}`,
      `Name: ${data.get('name') || ''}`,
      `Phone: ${data.get('phone') || ''}`,
      `Email: ${data.get('email') || ''}`,
      '',
      data.get('cover') || '',
    ].join('\n');
    const url = `mailto:weibnsina@gmail.com?subject=${encodeURIComponent('Job Application')}&body=${encodeURIComponent(body)}`;
    window.location.href = url;
  });
}

/* --------------------------------------------------------------------------
   SCROLL REVEAL
   -------------------------------------------------------------------------- */
function initScrollReveal() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.querySelectorAll('[data-reveal]').forEach(el => el.classList.add('visible'));
    return;
  }
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
  document.querySelectorAll('[data-reveal]').forEach(el => observer.observe(el));
}

/* --------------------------------------------------------------------------
   SCROLL PROGRESS + BACK TO TOP
   -------------------------------------------------------------------------- */
function initScrollUI() {
  if (document.querySelector('.scroll-progress')) return;

  const bar = document.createElement('div');
  bar.className = 'scroll-progress';
  bar.setAttribute('aria-hidden', 'true');
  document.body.appendChild(bar);

  const btt = document.createElement('button');
  btt.type = 'button';
  btt.className = 'back-to-top';
  btt.setAttribute('aria-label', 'Back to top');
  btt.innerHTML = '↑';
  btt.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  document.body.appendChild(btt);

  let ticking = false;
  function update() {
    const scrolled = window.scrollY;
    const total = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.width = total > 0 ? `${(scrolled / total) * 100}%` : '0%';
    btt.classList.toggle('visible', scrolled > 500);
    ticking = false;
  }
  window.addEventListener('scroll', () => {
    if (!ticking) {
      requestAnimationFrame(update);
      ticking = true;
    }
  }, { passive: true });
  update();
}

/* --------------------------------------------------------------------------
   INIT
   -------------------------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', () => {
  initHeader();
  initScrollUI();
  initScrollReveal();
  initAppointmentForms();
  initContactForm();
  initCareersForm();
  initDoctorsListing();
  initFeaturedDoctors();
  initDepartmentsGrid();
  initBlogListings();
  initUpdatesCarousel();
});
