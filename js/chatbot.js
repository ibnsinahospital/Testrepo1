/* ==========================================================================
   Ibn Sina Hospital — Chatbot (Ibn Sina Bot)
   Lazy-loaded: data is fetched only when the user opens the chat.
   ========================================================================== */
'use strict';

(function () {
  const DATA_URLS = {
    doctors:     '/data/doctors.json',
    departments: '/data/departments.json',
  };
  const APPOINTMENT_ENDPOINT =
    'https://script.google.com/macros/s/AKfycbwOmEFb0cu0rQ3IzRKrzP9wLNgjXZLUuvpZJWp2xEcZSvuknyppjiavPWST31QNEWoS/exec';

  const LANG = {
    en: {
      welcome: "Hello! I'm Ibn Sina Bot. How can I help you?",
      prompt: 'Ask me about OPD timings, location, services, departments, doctors, or booking an appointment.',
      quick: ['OPD Timings', 'Services', 'Book Appointment', 'Contact', 'Doctors'],
      opd: 'Our OPD, emergency, pharmacy, and lab are open 24/7, 365 days a year.',
      location: 'We are near Railway Station, Ompora Railway Station Road, Ompora, Budgam, J&K 191111.',
      emergency: 'For emergencies, call 9622552553 or 9419023501. Available 24/7.',
      services: 'We offer 24/7 emergency, ambulance, dialysis, endoscopy, TMT, Holter, ABPM, digital X-ray, ultrasound, physiotherapy, and full diagnostic lab services.',
      contact: 'Reception: 9622552553 / 9419023501. Email: weibnsina@gmail.com',
      departments: 'Our departments:',
      doctors: 'Our doctors:',
      doctors_specialty: 'Doctors in {specialty}:',
      fallback: "I'm still learning. Try asking about OPD timings, services, doctors, or booking an appointment. For urgent help, call 9622552553.",
      help: "I can help with:\n- OPD timings & location\n- Services & departments\n- Doctors\n- Booking an appointment\n- Common health questions",
      book_intro: "Sure, let's book an appointment. Type \"cancel\" anytime to stop.",
      book_name: 'Please type your full name.',
      book_phone: 'Now type your 10-digit phone number.',
      book_phone_bad: 'That phone number doesn\'t look right. Please enter 7–15 digits.',
      book_dept: 'Which department or reason for the visit? (Type "skip" if not sure)',
      book_time: 'Preferred date/time? (e.g. "Tomorrow 11 AM", or "skip")',
      book_confirm: 'Confirm:\nName: {name}\nPhone: {phone}\nDepartment: {dept}\nTime: {time}\n\nType "confirm" to submit or "cancel" to abort.',
      book_done: "Request sent. We'll call you shortly to confirm. If you don't hear back, call 9622552553.",
      book_cancelled: 'Appointment cancelled.',
      book_submitting: 'Sending your request…',
      loading: 'One moment…',
      data_unavailable: "That info isn't available right now. Please call 9622552553.",
      thanks: "You're welcome! Anything else?",
      bye: 'Take care. Call 9622552553 anytime.',
    },
    hi: {
      welcome: 'Namaste! Main Ibn Sina Bot hoon. Aapki kya madad karoon?',
      prompt: 'OPD timings, location, services, departments, doctors, ya appointment booking ke baare mein poochein.',
      quick: ['OPD Timings', 'Services', 'Appointment', 'Contact', 'Doctors'],
      opd: 'Hamara OPD, emergency, pharmacy aur lab 24/7, saal ke 365 din khule rehte hain.',
      location: 'Hum Railway Station ke paas, Ompora, Budgam, J&K 191111 mein hain.',
      emergency: 'Emergency ke liye call karein: 9622552553 ya 9419023501.',
      services: 'Hum 24/7 emergency, ambulance, dialysis, endoscopy, TMT, Holter, ABPM, digital X-ray, ultrasound, physiotherapy aur diagnostic lab provide karte hain.',
      contact: 'Reception: 9622552553 / 9419023501. Email: weibnsina@gmail.com',
      departments: 'Humare departments:',
      doctors: 'Humare doctors:',
      doctors_specialty: '{specialty} ke doctors:',
      fallback: 'Samajh nahi aaya. OPD timings, services, doctors ya appointment ke baare mein poochein. Urgent madad ke liye 9622552553 call karein.',
      help: "Main in cheezon mein madad kar sakta hoon:\n- OPD timings & location\n- Services & departments\n- Doctors\n- Appointment booking\n- Common health questions",
      book_intro: 'Theek hai, appointment book karte hain. Kabhi bhi "cancel" likhein.',
      book_name: 'Apna poora naam likhein.',
      book_phone: 'Ab apna 10-digit phone number likhein.',
      book_phone_bad: 'Number sahi nahi lag raha. Kripya 7–15 digits daalein.',
      book_dept: 'Kis department ya reason ke liye? ("skip" likhein agar pata nahi)',
      book_time: 'Preferred date/time? (jaise "Kal 11 AM", ya "skip")',
      book_confirm: 'Confirm karein:\nNaam: {name}\nPhone: {phone}\nDepartment: {dept}\nTime: {time}\n\n"confirm" ya "cancel" likhein.',
      book_done: 'Request bhej di gayi. Hum jald call karenge. Agar call na aaye toh 9622552553 par call karein.',
      book_cancelled: 'Appointment cancel kar di gayi.',
      book_submitting: 'Bhej rahe hain…',
      loading: 'Ek minute…',
      data_unavailable: 'Jaankari abhi uplabdh nahi. Kripya 9622552553 par call karein.',
      thanks: 'Aapka swagat hai! Aur kuch?',
      bye: 'Apna khayal rakhein. Zaroorat par 9622552553 par call karein.',
    },
  };

  const SPECIALTY_SYNONYMS = {
    cardiology: ['cardiology', 'heart', 'cardiologist', 'cardiac'],
    dentistry: ['dental', 'dentist', 'teeth', 'tooth'],
    dermatology: ['dermatology', 'skin', 'dermatologist', 'hair'],
    ent: ['ent', 'ear nose throat', 'otolaryngology'],
    gastroenterology: ['gastroenterology', 'stomach', 'digestive', 'gastro'],
    'general-medicine': ['general medicine', 'internal medicine', 'physician'],
    'general-surgery': ['general surgery', 'surgeon'],
    gynaecology: ['gynaecology', 'gynecology', 'gynaecologist', 'gynecologist', 'women'],
    nephrology: ['nephrology', 'kidney', 'dialysis', 'renal'],
    ophthalmology: ['ophthalmology', 'eye', 'ophthalmologist'],
    orthopaedics: ['orthopaedics', 'orthopedics', 'bone', 'joint', 'ortho'],
    'pediatric-surgery': ['pediatric surgery', 'paediatric surgery', 'child surgery'],
    physiotherapy: ['physiotherapy', 'physio', 'rehab'],
    'plastic-surgery': ['plastic surgery', 'cosmetic surgery'],
    pulmonology: ['pulmonology', 'chest', 'respiratory', 'lungs'],
    radiology: ['radiology', 'x-ray', 'scan', 'imaging'],
    rheumatology: ['rheumatology', 'arthritis', 'rheumatologist'],
    urology: ['urology', 'urologist', 'urinary', 'prostate'],
  };

  let currentLang = 'en';
  let step = null;
  let booking = { name: '', phone: '', dept: '', time: '' };
  let departmentsCache = null;
  let doctorsCache = null;
  let dataLoading = false;
  let dataLoaded = false;
  let isSubmitting = false;

  /* ---------- Helpers ---------- */
  function el(tag, attrs = {}, html = '') {
    const node = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === 'class') node.className = v;
      else if (k === 'dataset') Object.assign(node.dataset, v);
      else node.setAttribute(k, v);
    });
    if (html) node.innerHTML = html;
    return node;
  }

  function cleanName(raw) {
    let n = String(raw || '').trim().replace(/\.+$/, '').replace(/^dr\.?\s*/i, '');
    if (!n) return 'Doctor';
    n = n.split(/\s+/).map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');
    return 'Dr. ' + n;
  }

  function titleCase(s) {
    return String(s || '').toLowerCase().split(' ').map(w => w ? w.charAt(0).toUpperCase() + w.slice(1) : '').join(' ');
  }

  /* ---------- Styles + DOM injection ---------- */
  function injectStyles() {
    if (document.getElementById('ibn-bot-styles')) return;
    const style = el('style', { id: 'ibn-bot-styles' });
    style.textContent = `
      .ibn-bot-fab{position:fixed;bottom:24px;right:24px;z-index:9998;width:60px;height:60px;background:#2d4a2b;color:#fff;border:none;border-radius:50%;cursor:pointer;font-size:26px;display:flex;align-items:center;justify-content:center;box-shadow:0 6px 24px rgba(0,0,0,.2);transition:transform .2s}
      .ibn-bot-fab:hover{transform:scale(1.06)}
      .ibn-bot-fab:focus-visible{outline:2px solid #8fd19e;outline-offset:2px}
      .ibn-bot-window{position:fixed;bottom:96px;right:24px;z-index:9998;width:min(380px,94vw);max-height:min(640px,80vh);background:#fff;border-radius:20px;box-shadow:0 12px 40px rgba(0,0,0,.25);display:none;flex-direction:column;overflow:hidden;font-family:'Nunito',system-ui,sans-serif}
      .ibn-bot-window.open{display:flex}
      .ibn-bot-header{background:#2d4a2b;color:#fff;padding:14px 16px;display:flex;align-items:center;justify-content:space-between;gap:8px}
      .ibn-bot-header h3{margin:0;font-size:1rem;font-family:'Poppins',sans-serif}
      .ibn-bot-header-actions{display:flex;gap:6px}
      .ibn-bot-header button{background:none;border:none;color:#fff;font-size:1.1rem;cursor:pointer;padding:4px 6px;border-radius:6px;line-height:1}
      .ibn-bot-header button:hover{background:rgba(255,255,255,.12)}
      .ibn-bot-lang{display:flex;gap:6px;padding:8px 12px;background:#f4f4ef;border-bottom:1px solid #e4e4de}
      .ibn-bot-lang button{background:#fff;border:1px solid #d4d4c8;border-radius:14px;padding:3px 10px;font-size:.75rem;cursor:pointer}
      .ibn-bot-lang button.active{background:#2d4a2b;color:#fff;border-color:#2d4a2b}
      .ibn-bot-messages{flex:1;padding:14px;overflow-y:auto;background:#f9f9f4;display:flex;flex-direction:column;gap:10px;min-height:200px}
      .ibn-bot-msg{max-width:85%;padding:10px 14px;border-radius:14px;line-height:1.45;font-size:.9rem;white-space:pre-line;word-wrap:break-word;position:relative}
      .ibn-bot-msg.bot{background:#e6e6d6;color:#1a1a1a;border-bottom-left-radius:4px;align-self:flex-start}
      .ibn-bot-msg.user{background:#2d4a2b;color:#fff;border-bottom-right-radius:4px;align-self:flex-end}
      .ibn-bot-msg .ts{display:block;font-size:.68rem;opacity:.55;margin-top:4px;text-align:right}
      .ibn-bot-typing{display:flex;gap:4px;align-items:center;width:fit-content;align-self:flex-start;background:#e6e6d6;padding:12px 16px;border-radius:14px;border-bottom-left-radius:4px}
      .ibn-bot-typing span{width:6px;height:6px;border-radius:50%;background:#777;animation:ibn-blink 1.2s infinite}
      .ibn-bot-typing span:nth-child(2){animation-delay:.15s}
      .ibn-bot-typing span:nth-child(3){animation-delay:.3s}
      @keyframes ibn-blink{0%,80%,100%{opacity:.2}40%{opacity:1}}
      .ibn-bot-quick{display:flex;flex-wrap:wrap;gap:6px;padding:8px 12px;background:#f9f9f4;border-top:1px solid #e4e4de}
      .ibn-bot-quick button{background:#fff;border:1px solid #2d4a2b;color:#2d4a2b;border-radius:14px;padding:5px 12px;font-size:.78rem;cursor:pointer;transition:all .15s}
      .ibn-bot-quick button:hover{background:#2d4a2b;color:#fff}
      .ibn-bot-input-area{display:flex;gap:8px;padding:10px;border-top:1px solid #e4e4de;background:#fff}
      .ibn-bot-input{flex:1;padding:10px 12px;border:1px solid #d4d4c8;border-radius:20px;font-family:inherit;font-size:.88rem;outline:none}
      .ibn-bot-input:focus{border-color:#2d4a2b}
      .ibn-bot-input:disabled{background:#f2f2ed}
      .ibn-bot-send{background:#2d4a2b;color:#fff;border:none;border-radius:20px;padding:0 18px;cursor:pointer;font-weight:600;font-size:.85rem}
      .ibn-bot-send:disabled{opacity:.5;cursor:not-allowed}
      @media (max-width:480px){
        .ibn-bot-fab{width:52px;height:52px;bottom:16px;right:16px}
        .ibn-bot-window{right:8px;left:8px;bottom:80px;width:auto}
      }
    `;
    document.head.appendChild(style);
  }

  function injectDOM() {
    if (document.getElementById('ibn-bot-fab')) return;
    const frag = document.createDocumentFragment();

    const fab = el('button', {
      class: 'ibn-bot-fab',
      id: 'ibn-bot-fab',
      type: 'button',
      'aria-label': 'Open chat with Ibn Sina Bot',
      'aria-haspopup': 'dialog',
      'aria-expanded': 'false',
    }, '💬');

    const win = el('div', {
      class: 'ibn-bot-window',
      id: 'ibn-bot-window',
      role: 'dialog',
      'aria-label': 'Ibn Sina Bot chat',
      'aria-modal': 'false',
    });

    win.innerHTML = `
      <div class="ibn-bot-header">
        <h3>Ibn Sina Bot</h3>
        <div class="ibn-bot-header-actions">
          <button type="button" data-action="call" aria-label="Call hospital">📞</button>
          <button type="button" data-action="clear" aria-label="Clear chat">🗑️</button>
          <button type="button" data-action="close" aria-label="Close chat">×</button>
        </div>
      </div>
      <div class="ibn-bot-lang" role="group" aria-label="Language">
        <button type="button" data-lang="en" class="active" aria-pressed="true">English</button>
        <button type="button" data-lang="hi" aria-pressed="false">Hinglish</button>
      </div>
      <div class="ibn-bot-messages" id="ibn-bot-messages" role="log" aria-live="polite"></div>
      <div class="ibn-bot-quick" id="ibn-bot-quick"></div>
      <div class="ibn-bot-input-area">
        <input type="text" class="ibn-bot-input" id="ibn-bot-input" placeholder="Type here…" aria-label="Type your message">
        <button type="button" class="ibn-bot-send" id="ibn-bot-send">Send</button>
      </div>`;

    frag.appendChild(fab);
    frag.appendChild(win);
    document.body.appendChild(frag);
  }

  /* ---------- Chat UI ---------- */
  function addMessage(text, sender) {
    const messages = document.getElementById('ibn-bot-messages');
    if (!messages) return;
    const msg = el('div', { class: `ibn-bot-msg ${sender}` });
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    msg.innerHTML = `${escapeHtml(text)}<span class="ts">${time}</span>`;
    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function showTyping() {
    const messages = document.getElementById('ibn-bot-messages');
    if (!messages) return null;
    const t = el('div', { class: 'ibn-bot-typing' }, '<span></span><span></span><span></span>');
    messages.appendChild(t);
    messages.scrollTop = messages.scrollHeight;
    return t;
  }

  function botReply(text, delay = 400) {
    const typing = showTyping();
    return new Promise(resolve => {
      setTimeout(() => {
        if (typing) typing.remove();
        addMessage(text, 'bot');
        resolve();
      }, delay);
    });
  }

  function renderQuickReplies(list) {
    const container = document.getElementById('ibn-bot-quick');
    if (!container) return;
    container.innerHTML = '';
    (list || LANG[currentLang].quick).forEach(label => {
      const btn = el('button', { type: 'button' }, escapeHtml(label));
      btn.addEventListener('click', () => handleUserText(label));
      container.appendChild(btn);
    });
  }

  function setInputEnabled(enabled) {
    const input = document.getElementById('ibn-bot-input');
    const send = document.getElementById('ibn-bot-send');
    if (input) input.disabled = !enabled;
    if (send) send.disabled = !enabled;
    if (enabled && input) input.focus();
  }

  /* ---------- Data loading (lazy) ---------- */
  async function loadData() {
    if (dataLoaded || dataLoading) return;
    dataLoading = true;
    try {
      const [depts, docs] = await Promise.all([
        fetch('/data/departments.json', { cache: 'default' }).then(r => r.ok ? r.json() : []).catch(() => []),
        fetch('/data/doctors.json', { cache: 'default' }).then(r => r.ok ? r.json() : []).catch(() => []),
      ]);
      departmentsCache = Array.isArray(depts) ? depts : [];
      doctorsCache = Array.isArray(docs) ? docs : [];
      dataLoaded = true;
    } catch (e) {
      console.warn('Chatbot data load failed', e);
    } finally {
      dataLoading = false;
    }
  }

  /* ---------- Intent detection ---------- */
  function detectIntent(text) {
    const t = text.toLowerCase().trim();
    const has = (...words) => words.some(w => new RegExp(`\\b${w}\\b`, 'i').test(t));
    if (has('hello', 'hi', 'hey', 'namaste', 'salam')) return 'greeting';
    if (has('opd', 'timing', 'hours', 'open', 'close', 'khula')) return 'opd';
    if (has('location', 'address', 'where', 'direction', 'kahan')) return 'location';
    if (has('emergency', 'ambulance', 'urgent')) return 'emergency';
    if (has('service', 'treatment', 'facility', 'facilities')) return 'services';
    if (has('contact', 'phone', 'call', 'email', 'number')) return 'contact';
    if (has('department', 'specialty', 'speciality', 'dept')) return 'departments';
    if (has('doctor', 'dr', 'physician', 'specialist', 'consultant')) return 'doctors';
    if (has('appointment', 'book', 'schedule', 'visit')) return 'appointment';
    if (has('thank', 'thanks', 'shukriya')) return 'thanks';
    if (has('bye', 'goodbye')) return 'bye';
    if (has('help', 'option')) return 'help';
    return 'fallback';
  }

  function extractSpecialty(text) {
    const t = text.toLowerCase();
    if (departmentsCache && departmentsCache.length) {
      for (const d of departmentsCache) {
        const name = String(d.name || '').toLowerCase();
        const slug = String(d.slug || '').toLowerCase();
        if (name && t.includes(name)) return d;
        if (slug && t.includes(slug.replace(/-/g, ' '))) return d;
      }
    }
    for (const [slug, synonyms] of Object.entries(SPECIALTY_SYNONYMS)) {
      for (const syn of synonyms) {
        if (new RegExp(`\\b${syn}\\b`, 'i').test(t)) {
          return departmentsCache?.find(d => d.slug === slug) || { name: titleCase(syn), slug };
        }
      }
    }
    return null;
  }

  function filterDoctors(specialty) {
    if (!specialty || !doctorsCache) return [];
    const s = (specialty.name || '').toLowerCase();
    const slug = (specialty.slug || '').toLowerCase();
    return doctorsCache.filter(d => {
      const docSpec = String(d.specialty || '').toLowerCase();
      const docDept = String(d.department || '').toLowerCase();
      return docSpec.includes(slug) || docDept.includes(s.replace(/-/g, ' ')) || docSpec === slug;
    });
  }

  /* ---------- Message processing ---------- */
  async function processMessage(text) {
    const L = LANG[currentLang];
    const t = text.toLowerCase().trim();

    if (step && t === 'cancel') {
      step = null;
      booking = { name: '', phone: '', dept: '', time: '' };
      return botReply(L.book_cancelled);
    }

    if (step === 'confirm') {
      if (['confirm', 'yes', 'haan', 'ha'].includes(t)) {
        step = null;
        return submitBooking();
      }
      if (t === 'cancel') {
        step = null;
        booking = { name: '', phone: '', dept: '', time: '' };
        return botReply(L.book_cancelled);
      }
      return botReply('Please type "confirm" or "cancel".');
    }

    if (step === 'name') {
      booking.name = text.trim();
      step = 'phone';
      return botReply(L.book_phone);
    }
    if (step === 'phone') {
      const digits = text.replace(/[^\d]/g, '');
      if (digits.length < 7 || digits.length > 15) {
        return botReply(L.book_phone_bad);
      }
      booking.phone = text.trim();
      step = 'dept';
      const deptNames = (departmentsCache || []).slice(0, 6).map(d => d.name);
      renderQuickReplies([...deptNames, 'skip']);
      return botReply(L.book_dept);
    }
    if (step === 'dept') {
      booking.dept = t === 'skip' ? '' : text.trim();
      step = 'time';
      renderQuickReplies(['skip']);
      return botReply(L.book_time);
    }
    if (step === 'time') {
      booking.time = t === 'skip' ? '' : text.trim();
      step = 'confirm';
      const msg = L.book_confirm
        .replace('{name}', booking.name)
        .replace('{phone}', booking.phone)
        .replace('{dept}', booking.dept || 'Not specified')
        .replace('{time}', booking.time || 'Flexible');
      renderQuickReplies(['confirm', 'cancel']);
      return botReply(msg);
    }

    const intent = detectIntent(t);

    if (intent === 'doctors') {
      if (!dataLoaded) await loadData();
      const specialty = extractSpecialty(t);
      if (specialty) {
        const docs = filterDoctors(specialty);
        if (docs.length) {
          const list = docs.slice(0, 8).map((d, i) => `${i + 1}. ${cleanName(d.name)} — ${titleCase(d.specialty || 'Specialist')}`).join('\n');
          renderQuickReplies(['Book Appointment', 'All Doctors', 'Contact']);
          return botReply(`${L.doctors_specialty.replace('{specialty}', titleCase(specialty.name))}\n\n${list}`);
        }
        renderQuickReplies(['All Doctors', 'Contact']);
        return botReply(`No doctors listed for ${titleCase(specialty.name)} right now. Please call 9622552553.`);
      }
      if (doctorsCache && doctorsCache.length) {
        const list = doctorsCache.slice(0, 12).map((d, i) => `${i + 1}. ${cleanName(d.name)} — ${titleCase(d.specialty || 'Specialist')}`).join('\n');
        renderQuickReplies(['Book Appointment', 'Departments', 'Contact']);
        return botReply(`${L.doctors}\n\n${list}\n\nAsk about a specialty for a shorter list.`);
      }
      renderQuickReplies(['Contact', 'Book Appointment']);
      return botReply(L.data_unavailable);
    }

    switch (intent) {
      case 'greeting':
        renderQuickReplies(L.quick);
        await botReply(L.welcome);
        return botReply(L.prompt, 600);
      case 'opd':
        renderQuickReplies(['Book Appointment', 'Contact']);
        return botReply(L.opd);
      case 'location':
        renderQuickReplies(['Contact', 'OPD Timings']);
        return botReply(L.location);
      case 'emergency':
        renderQuickReplies(['Call 9622552553', 'Book Appointment']);
        return botReply(L.emergency);
      case 'services':
        renderQuickReplies(['Departments', 'Doctors', 'Book Appointment']);
        return botReply(L.services);
      case 'contact':
        renderQuickReplies(['Call Now', 'Book Appointment']);
        return botReply(L.contact);
      case 'departments':
        if (!dataLoaded) await loadData();
        if (departmentsCache && departmentsCache.length) {
          const list = departmentsCache.map((d, i) => `${i + 1}. ${titleCase(d.name)}`).join('\n');
          renderQuickReplies(['Doctors', 'Book Appointment']);
          return botReply(`${L.departments}\n\n${list}`);
        }
        renderQuickReplies(['Contact']);
        return botReply(L.data_unavailable);
      case 'appointment':
        step = 'name';
        renderQuickReplies(['cancel']);
        await botReply(L.book_intro);
        return botReply(L.book_name, 700);
      case 'thanks':
        renderQuickReplies(L.quick);
        return botReply(L.thanks);
      case 'bye':
        renderQuickReplies(L.quick);
        return botReply(L.bye);
      case 'help':
        renderQuickReplies(L.quick);
        return botReply(L.help);
      default:
        renderQuickReplies(['Help', 'Book Appointment', 'Contact']);
        return botReply(L.fallback);
    }
  }

  async function submitBooking() {
    if (isSubmitting) return;
    isSubmitting = true;
    setInputEnabled(false);
    const L = LANG[currentLang];
    const typing = showTyping();

    const formData = new FormData();
    formData.append('patient_name', booking.name);
    formData.append('phone', booking.phone);
    formData.append('department', booking.dept || 'Not specified');
    formData.append('preferred_date', booking.time || 'Flexible');
    formData.append('reason', 'Chatbot booking');
    formData.append('source', 'chatbot');

    try {
      await fetch(APPOINTMENT_ENDPOINT, { method: 'POST', body: formData, mode: 'no-cors' });
      if (typing) typing.remove();
      await botReply(L.book_done, 200);
    } catch (e) {
      if (typing) typing.remove();
      await botReply('Sorry, we could not submit your request right now. Please call 9622552553.', 200);
    } finally {
      booking = { name: '', phone: '', dept: '', time: '' };
      step = null;
      isSubmitting = false;
      setInputEnabled(true);
      renderQuickReplies(L.quick);
    }
  }

  /* ---------- Interaction ---------- */
  function handleUserText(text) {
    const t = String(text || '').trim();
    if (!t) return;
    addMessage(t, 'user');
    processMessage(t);
  }

  function setLanguage(lang) {
    currentLang = LANG[lang] ? lang : 'en';
    document.querySelectorAll('.ibn-bot-lang button').forEach(btn => {
      const active = btn.dataset.lang === currentLang;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-pressed', String(active));
    });
    const messages = document.getElementById('ibn-bot-messages');
    if (messages) messages.innerHTML = '';
    botReply(LANG[currentLang].welcome, 100);
    botReply(LANG[currentLang].prompt, 500);
    renderQuickReplies(LANG[currentLang].quick);
  }

  function clearChat() {
    const messages = document.getElementById('ibn-bot-messages');
    if (messages) messages.innerHTML = '';
    step = null;
    booking = { name: '', phone: '', dept: '', time: '' };
    botReply(LANG[currentLang].welcome, 100);
    botReply(LANG[currentLang].prompt, 500);
    renderQuickReplies(LANG[currentLang].quick);
  }

  /* ---------- Init ---------- */
  function init() {
    injectStyles();
    injectDOM();

    const fab = document.getElementById('ibn-bot-fab');
    const win = document.getElementById('ibn-bot-window');
    const messages = document.getElementById('ibn-bot-messages');
    const input = document.getElementById('ibn-bot-input');
    const send = document.getElementById('ibn-bot-send');

    let firstOpen = true;

    function openWindow() {
      win.classList.add('open');
      fab.setAttribute('aria-expanded', 'true');
      if (firstOpen) {
        firstOpen = false;
        loadData(); // lazy-load only on first open
        botReply(LANG[currentLang].welcome, 200);
        botReply(LANG[currentLang].prompt, 700);
        renderQuickReplies(LANG[currentLang].quick);
      }
      input.focus();
    }
    function closeWindow() {
      win.classList.remove('open');
      fab.setAttribute('aria-expanded', 'false');
      fab.focus();
    }

    fab.addEventListener('click', () => win.classList.contains('open') ? closeWindow() : openWindow());

    win.querySelector('[data-action="close"]').addEventListener('click', closeWindow);
    win.querySelector('[data-action="clear"]').addEventListener('click', clearChat);
    win.querySelector('[data-action="call"]').addEventListener('click', () => window.location.href = 'tel:+919622552553');

    win.querySelectorAll('.ibn-bot-lang button').forEach(btn =>
      btn.addEventListener('click', () => setLanguage(btn.dataset.lang))
    );

    send.addEventListener('click', () => {
      handleUserText(input.value);
      input.value = '';
    });
    input.addEventListener('keypress', e => {
      if (e.key === 'Enter') { e.preventDefault(); send.click(); }
    });

    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && win.classList.contains('open')) closeWindow();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
