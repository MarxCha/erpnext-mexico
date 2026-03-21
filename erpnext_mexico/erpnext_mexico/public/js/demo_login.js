/**
 * ERPNext México — Demo Quick-Login Cards
 *
 * Inyecta cards de acceso rápido en la login page de Frappe.
 * Un click = login directo.
 */
(function () {
  'use strict';

  if (window.location.pathname !== '/login') return;

  var DEMO_USERS = [
    {
      label: 'Admin',
      desc: 'Sistema completo',
      email: 'Administrator',
      password: 'admin',
      icon: '\uD83D\uDEE1\uFE0F',
    },
    {
      label: 'Demo MX',
      desc: 'Facturación CFDI',
      email: 'demo@mdconsultoria.mx',
      password: 'Demo2026!',
      icon: '\uD83C\uDDF2\uD83C\uDDFD',
    },
  ];

  var CSS = [
    '#demo-cards{margin:24px 0 0;padding:20px 0 0;border-top:1px solid var(--border-color,#d1d5db)}',
    '#demo-cards .dh{display:flex;align-items:center;gap:8px;margin:0 0 12px;font-size:13px;color:var(--text-muted,#6b7280);font-weight:500}',
    '#demo-cards .dh b{font-size:10px;background:#dcfce7;color:#15803d;padding:2px 8px;border-radius:99px;font-weight:700;letter-spacing:.04em}',
    '#demo-cards .dg{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}',
    '#demo-cards .dc{display:flex;flex-direction:column;align-items:center;gap:4px;padding:14px 10px;border-radius:10px;cursor:pointer;transition:all .15s;border:2px solid transparent;background:var(--control-bg,#f3f4f6)}',
    '#demo-cards .dc:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.08);border-color:var(--primary,#2563eb)}',
    '#demo-cards .dc:active{transform:scale(.97)}',
    '#demo-cards .dc .di{font-size:26px;line-height:1}',
    '#demo-cards .dc .dl{font-size:13px;font-weight:600;color:var(--heading-color,#111827)}',
    '#demo-cards .dc .dd{font-size:11px;color:var(--text-muted,#6b7280)}',
    '#demo-cards .dc .de{font-size:10px;color:var(--text-light,#9ca3af);font-family:var(--font-stack);opacity:.7}',
    '#demo-cards .dc.loading{opacity:.5;pointer-events:none}',
    '#demo-cards .dc.loading .dl{color:var(--primary,#2563eb)}',
  ].join('\n');

  function loginUser(user, cardEl) {
    cardEl.classList.add('loading');
    cardEl.querySelector('.dl').textContent = 'Entrando...';

    // Use standard form POST via fetch
    var formData = new FormData();
    formData.append('usr', user.email);
    formData.append('pwd', user.password);
    formData.append('cmd', 'login');

    fetch('/api/method/login', {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'X-Frappe-CSRF-Token': (window.frappe && window.frappe.csrf_token) || getCookie('csrf_token') || 'None',
      },
      body: formData,
    })
    .then(function (res) {
      if (res.ok) {
        window.location.href = '/app';
      } else {
        // Fallback: fill the form fields
        fillAndSubmit(user);
      }
    })
    .catch(function () {
      fillAndSubmit(user);
    });
  }

  function getCookie(name) {
    var v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return v ? v.pop() : '';
  }

  function fillAndSubmit(user) {
    var e = document.getElementById('login_email');
    var p = document.getElementById('login_password');
    if (e) e.value = user.email;
    if (p) p.value = user.password;
    var btn = document.querySelector('.btn-login') || document.querySelector('.btn-primary-dark');
    if (btn) btn.click();
  }

  function inject() {
    if (document.getElementById('demo-cards')) return;

    var target = document.querySelector('.login-content.page-card')
      || document.querySelector('.page-card')
      || document.querySelector('.form-signin');
    if (!target) return;

    var style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);

    var wrap = document.createElement('div');
    wrap.id = 'demo-cards';

    var header = document.createElement('div');
    header.className = 'dh';
    header.innerHTML = 'Acceso rápido <b>DEMO</b>';
    wrap.appendChild(header);

    var grid = document.createElement('div');
    grid.className = 'dg';

    DEMO_USERS.forEach(function (u) {
      var c = document.createElement('div');
      c.className = 'dc';
      c.innerHTML =
        '<span class="di">' + u.icon + '</span>' +
        '<span class="dl">' + u.label + '</span>' +
        '<span class="dd">' + u.desc + '</span>' +
        '<span class="de">' + u.email + '</span>';
      c.addEventListener('click', function () { loginUser(u, c); });
      grid.appendChild(c);
    });

    wrap.appendChild(grid);

    // Append inside page-card, after form content
    var body = target.querySelector('.page-card-body') || target;
    body.appendChild(wrap);
  }

  // Retry injection until DOM is ready
  var attempts = 0;
  var timer = setInterval(function () {
    attempts++;
    inject();
    if (document.getElementById('demo-cards') || attempts > 30) {
      clearInterval(timer);
    }
  }, 200);
})();
