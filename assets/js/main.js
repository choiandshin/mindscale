/* MindScale Lab — site behaviour: mobile nav, active nav item, publication filters */
(function () {
  'use strict';

  /* ---------- mobile nav ---------- */
  function initNav() {
    var toggle = document.querySelector('.nav-toggle');
    var links = document.querySelector('.nav-links');
    if (!toggle || !links) return;
    document.documentElement.classList.add('nav-ready');
    function closeMenu() {
      links.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
    }
    toggle.addEventListener('click', function () {
      var open = links.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    links.addEventListener('click', function (ev) {
      if (ev.target.tagName === 'A') {
        closeMenu();
      }
    });
    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape' && links.classList.contains('is-open')) {
        closeMenu();
        toggle.focus();
      }
    });
    window.addEventListener('resize', function () {
      if (window.innerWidth > 720) closeMenu();
    });
  }

  /* ---------- active nav item ---------- */
  function initActive() {
    var path = window.location.pathname.split('/').pop() || 'index.html';
    var links = document.querySelectorAll('.nav-links a');
    for (var i = 0; i < links.length; i++) {
      var href = links[i].getAttribute('href');
      if (href === path || (path === '' && href === 'index.html')) {
        links[i].classList.add('is-active');
        links[i].setAttribute('aria-current', 'page');
      }
    }
  }

  /* ---------- publication filters ---------- */
  function initPubFilters() {
    var chips = document.querySelectorAll('.pub-filters .chip');
    if (!chips.length) return;
    var items = document.querySelectorAll('.pub[data-type]');
    var status = document.getElementById('pub-status');
    document.querySelector('.pub-filters').hidden = false;

    function apply(filter, label) {
      var count = 0;
      for (var i = 0; i < items.length; i++) {
        var types = (items[i].dataset.type || '').split(' ');
        var show = filter === 'all' || types.indexOf(filter) !== -1;
        items[i].style.display = show ? '' : 'none';
        if (show) count++;
      }
      // hide year headings with no visible entries
      var heads = document.querySelectorAll('.pub-year');
      for (var h = 0; h < heads.length; h++) {
        var any = false, n = heads[h].nextElementSibling;
        while (n && !n.classList.contains('pub-year')) {
          if (n.classList.contains('pub') && n.style.display !== 'none') { any = true; break; }
          n = n.nextElementSibling;
        }
        heads[h].style.display = any ? '' : 'none';
      }
      if (status) status.textContent = count + ' publications shown: ' + label + '.';
    }

    for (var c = 0; c < chips.length; c++) {
      chips[c].addEventListener('click', function (ev) {
        for (var k = 0; k < chips.length; k++) chips[k].setAttribute('aria-pressed', 'false');
        ev.currentTarget.setAttribute('aria-pressed', 'true');
        apply(ev.currentTarget.dataset.filter, ev.currentTarget.textContent);
      });
    }
  }

  /* ---------- year in footer ---------- */
  function initYear() {
    var els = document.querySelectorAll('[data-current-year]');
    var y = String(new Date().getFullYear());
    for (var i = 0; i < els.length; i++) els[i].textContent = y;
  }

  function boot() {
    initNav();
    initActive();
    initPubFilters();
    initYear();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else { boot(); }
})();
