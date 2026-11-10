/* FLC & Associates LLP: Case Law Database (static, no dependencies) */
(function () {
  'use strict';

  var PAGE = 40;
  var state = { q: '', subject: '', topic: '', side: '', prov: '', status: '', court: '', outcome: '', from: '', to: '', sort: 'rel', cite: '', id: '', saved: '' };
  var RESET = { q: '', subject: '', topic: '', side: '', prov: '', status: '', court: '', outcome: '', from: '', to: '', sort: 'rel', saved: '' };
  var SAVE_KEY = 'flc-saved-entries', saved = loadSaved();
  function loadSaved() { try { var a = JSON.parse(localStorage.getItem(SAVE_KEY) || '[]'); return Array.isArray(a) ? a : []; } catch (e) { return []; } }
  function storeSaved() { try { localStorage.setItem(SAVE_KEY, JSON.stringify(saved)); } catch (e) {} }
  var DB = [], shown = PAGE, byCite = {};
  var $ = function (id) { return document.getElementById(id); };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function compact(s) { return String(s).toLowerCase().replace(/[\s.,:;()\-\/]/g, ''); }
  function uniq(a) { return a.filter(function (x, i) { return x && a.indexOf(x) === i; }); }

  /* ---------- load ---------- */
  fetch('data/cases.json', { cache: 'no-cache' })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(init)
    .catch(function () {
      $('status').innerHTML = '<div class="empty">The database could not be loaded. Please refresh the page.</div>';
      $('dbMeta').textContent = '';
    });

  function init(data) {
    DB = data.records.map(function (r, i) {
      r._i = i;
      var cites = r.citations.concat(r.relied, r.contrary);
      r._hay = [r.heading, r.text, r.topic, r.subject, r.title, r.court, r.outcome, (r.judges || []).join(' '),
        (r.provisions || []).join(' '), cites.join(' ')].join(' ').toLowerCase();
      r._compact = compact(r._hay);
      r.citations.forEach(function (c) { (byCite[c] = byCite[c] || { main: [], rel: [], con: [] }).main.push(r); });
      r.relied.forEach(function (c) { (byCite[c] = byCite[c] || { main: [], rel: [], con: [] }).rel.push(r); });
      r.contrary.forEach(function (c) { (byCite[c] = byCite[c] || { main: [], rel: [], con: [] }).con.push(r); });
      return r;
    });
    var d = data.generated ? new Date(data.generated) : null;
    $('dbMeta').textContent = DB.length + ' entries' + (d ? ' · updated ' + d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : '');
    $('yr').textContent = new Date().getFullYear();
    buildFilters();
    readHash();
    bind();
    render();
  }

  /* ---------- filters ---------- */
  function counts(key) {
    var m = {};
    DB.forEach(function (r) { var v = r[key]; if (v) m[v] = (m[v] || 0) + 1; });
    return m;
  }
  function fillSelect(el, label, values) {
    el.innerHTML = '<option value="">' + esc(label) + '</option>' + values.map(function (v) {
      return '<option value="' + esc(v) + '">' + esc(v) + '</option>';
    }).join('');
  }
  function buildFilters() {
    var subj = counts('subject'), order = [];
    DB.forEach(function (r) { if (order.indexOf(r.subject) < 0) order.push(r.subject); });
    $('subjectList').innerHTML = '<li><button type="button" data-subject="" class="on"><span>All subjects</span><span class="n">' + DB.length + '</span></button></li>' +
      order.map(function (s) {
        return '<li><button type="button" data-subject="' + esc(s) + '"><span>' + esc(s) + '</span><span class="n">' + subj[s] + '</span></button></li>';
      }).join('');
    var courts = counts('court');
    fillSelect($('fCourt'), 'All courts', Object.keys(courts).sort(function (a, b) { return courts[b] - courts[a]; }));
    var outs = counts('outcome');
    fillSelect($('fOutcome'), 'Any outcome', Object.keys(outs).sort());
    var years = uniq(DB.map(function (r) { return r.year; })).sort();
    fillSelect($('fFrom'), 'Any', years.map(String));
    fillSelect($('fTo'), 'Any', years.slice().reverse().map(String));
    var pm = {};
    DB.forEach(function (r) { (r.provisions || []).forEach(function (p) { pm[p] = (pm[p] || 0) + 1; }); });
    var provs = Object.keys(pm).sort(function (a, b) { return pm[b] - pm[a] || a.localeCompare(b, 'en', { numeric: true }); });
    $('fProv').innerHTML = '<option value="">Any provision</option>' + provs.map(function (p) {
      return '<option value="' + esc(p) + '">' + esc(p) + ' (' + pm[p] + ')</option>';
    }).join('');
  }
  function buildTopics() {
    var g = $('topicGroup');
    if (!state.subject) { g.hidden = true; return; }
    var m = {}, order = [];
    DB.forEach(function (r) {
      if (r.subject !== state.subject) return;
      var t = r.topic || 'General';
      if (!m[t]) { m[t] = 0; order.push(t); }
      m[t]++;
    });
    if (order.length < 2) { g.hidden = true; return; }
    g.hidden = false;
    $('fTopic').innerHTML = '<option value="">All topics (' + order.reduce(function (a, t) { return a + m[t]; }, 0) + ')</option>' +
      order.map(function (t) { return '<option value="' + esc(t) + '">' + esc(t) + ' (' + m[t] + ')</option>'; }).join('');
    $('fTopic').value = state.topic;
  }

  /* ---------- search ---------- */
  function terms(q) {
    var out = [], re = /"([^"]+)"|(\S+)/g, m;
    while ((m = re.exec(q))) out.push((m[1] || m[2]).toLowerCase());
    return out.filter(function (t) { return t.length > 0; });
  }
  function matches(r, ts) {
    for (var i = 0; i < ts.length; i++) {
      var t = ts[i];
      if (r._hay.indexOf(t) < 0 && r._compact.indexOf(compact(t)) < 0) return false;
    }
    return true;
  }
  function score(r, ts, qc) {
    var s = 0, cites = compact(r.citations.join(' '));
    if (qc.length > 5 && cites.indexOf(qc) >= 0) s += 50;
    ts.forEach(function (t) {
      var tc = compact(t);
      if (cites.indexOf(tc) >= 0) s += 6;
      if ((r.title || '').toLowerCase().indexOf(t) >= 0) s += 4;
      if ((r.heading || '').toLowerCase().indexOf(t) >= 0) s += 4;
      if ((r.topic || '').toLowerCase().indexOf(t) >= 0) s += 3;
      if (r.text.toLowerCase().indexOf(t) >= 0) s += 1;
    });
    return s;
  }

  function filtered() {
    var ts = terms(state.q), qc = compact(state.q);
    var list = DB.filter(function (r) {
      if (state.id) return r.id === state.id;
      if (state.cite) return r.citations.indexOf(state.cite) >= 0 || r.relied.indexOf(state.cite) >= 0 || r.contrary.indexOf(state.cite) >= 0;
      if (state.subject && r.subject !== state.subject) return false;
      if (state.topic && (r.topic || 'General') !== state.topic) return false;
      if (state.saved && saved.indexOf(r.id) < 0) return false;
      if (state.side && r.side !== state.side) return false;
      if (state.prov && (r.provisions || []).indexOf(state.prov) < 0) return false;
      if (state.status && r.status !== state.status) return false;
      if (state.court && r.court !== state.court) return false;
      if (state.outcome && r.outcome !== state.outcome) return false;
      if (state.from && (!r.year || r.year < +state.from)) return false;
      if (state.to && (!r.year || r.year > +state.to)) return false;
      if (ts.length && !matches(r, ts)) return false;
      return true;
    });
    if (state.sort === 'new' || state.sort === 'old') {
      var dir = state.sort === 'new' ? -1 : 1;
      list.sort(function (a, b) { return ((a.year || 0) - (b.year || 0)) * dir || a._i - b._i; });
    } else if (ts.length) {
      list.forEach(function (r) { r._s = score(r, ts, qc); });
      list.sort(function (a, b) { return b._s - a._s || a._i - b._i; });
    }
    return { list: list, ts: ts };
  }

  /* ---------- render ---------- */
  function hl(text, ts) {
    var h = esc(text);
    if (!ts.length) return h;
    ts.slice().sort(function (a, b) { return b.length - a.length; }).forEach(function (t) {
      if (t.length < 2) return;
      var re = new RegExp('(' + esc(t).replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')(?![^<]*>)', 'gi');
      h = h.replace(re, '<mark>$1</mark>');
    });
    return h;
  }

  function render() {
    syncControls();
    var res = filtered(), list = res.list, ts = res.ts;
    renderStatus(list.length);
    renderCitePanel();
    renderListPanel(list);
    $('filtersDone').textContent = 'Show ' + list.length + (list.length === 1 ? ' entry' : ' entries');
    $('listCount').textContent = saved.length;
    $('listBtn').setAttribute('aria-pressed', state.saved ? 'true' : 'false');
    var ol = $('cards');
    ol.innerHTML = '';
    if (!list.length) {
      ol.innerHTML = '<li class="empty">' + (state.saved && !saved.length ? 'Your list is empty. Press Save on an entry to add it here.' : 'No entries match. Try fewer words, or clear a filter.') + '</li>';
      $('moreWrap').hidden = true;
      return;
    }
    var tpl = $('cardTpl');
    list.slice(0, shown).forEach(function (r) { ol.appendChild(card(r, ts, tpl)); });
    $('moreWrap').hidden = list.length <= shown;
    $('moreBtn').textContent = 'Show more entries (' + (list.length - shown) + ' remaining)';
  }

  function card(r, ts, tpl) {
    var li = tpl.content.firstElementChild.cloneNode(true);
    li.id = r.id;
    if (r.heading) { var hd = li.querySelector('.heading'); hd.innerHTML = hl(r.heading, ts); hd.hidden = false; li.classList.add('has-heading'); }
    var c = li.querySelector('.cites');
    c.innerHTML = r.citations.length
      ? r.citations.map(function (k) { return '<span class="c" data-cite="' + esc(k) + '" title="Show all entries referring to ' + esc(k) + '">' + hl(k, ts) + '</span>'; }).join('<span class="sep">|</span>')
      : '<span class="nocite">' + (r.relied.length ? 'See authorities below' : 'No reported citation') + '</span>';
    var b = [];
    if (r.side === 'Accused') b.push('<span class="badge b-acc">Accused side</span>');
    if (r.side === 'Complainant') b.push('<span class="badge b-com">Complainant side</span>');
    if (r.outcome) b.push('<span class="badge b-out">' + esc(r.outcome) + '</span>');
    if (r.status === 'Verified') b.push('<span class="badge b-ok" title="Citation checked against the report">Verified</span>');
    if (r.status === 'Unverified') b.push('<span class="badge b-unv" title="Not yet checked against the report">Unverified</span>');
    if (r.status === 'Needs correction') b.push('<span class="badge b-rev" title="This entry is being checked by the firm">Under review</span>');
    li.querySelector('.badges').innerHTML = b.join('');
    var meta = [];
    if (r.title) meta.push('<span class="title">' + hl(r.title, ts) + '</span>');
    if (r.court) meta.push(esc(r.court));
    if (r.judges && r.judges.length) meta.push(esc(r.judges.join(', ')));
    li.querySelector('.meta').innerHTML = meta.join(' · ');
    li.querySelector('.crumb').innerHTML = '<button type="button" data-subject="' + esc(r.subject) + '">' + esc(r.subject) + '</button>' +
      (r.topic ? ' › <button type="button" data-subject="' + esc(r.subject) + '" data-topic="' + esc(r.topic) + '">' + esc(r.topic) + '</button>' : '');
    var body = li.querySelector('.body');
    body.innerHTML = hl(r.text, ts);
    var lines = r.text.split('\n').length;
    if (r.text.length > 520 || lines > 6) {
      body.classList.add('clamp');
      var ex = li.querySelector('.expand');
      ex.hidden = false;
      ex.addEventListener('click', function () {
        var open = body.classList.toggle('clamp');
        ex.textContent = open ? 'Show full entry' : 'Show less';
      });
    }
    var refs = [];
    if (r.relied.length) refs.push(refRow('Relied upon', r.relied, ''));
    if (r.contrary.length) refs.push(refRow('Contrary', r.contrary, 'contra'));
    var others = 0;
    r.citations.forEach(function (k) {
      var x = byCite[k]; if (!x) return;
      others += uniq(x.main.concat(x.rel, x.con)).filter(function (y) { return y !== r; }).length;
    });
    if (others) refs.push('<div class="refrow"><span class="lbl">Also cited in</span><button type="button" class="ref" data-cite="' + esc(r.citations[0]) + '">' + others + ' other entr' + (others === 1 ? 'y' : 'ies') + '</button></div>');
    li.querySelector('.refs').innerHTML = refs.join('');
    li.querySelector('.copy').addEventListener('click', function () { copy(citeText(r)); });
    var sv = li.querySelector('.save');
    var paint = function () { var on = saved.indexOf(r.id) >= 0; sv.textContent = on ? 'Saved' : 'Save'; sv.classList.toggle('on', on); sv.setAttribute('aria-pressed', on ? 'true' : 'false'); };
    paint();
    sv.addEventListener('click', function () {
      var i = saved.indexOf(r.id);
      if (i >= 0) saved.splice(i, 1); else saved.push(r.id);
      storeSaved();
      if (state.saved) render(); else { paint(); $('listCount').textContent = saved.length; }
    });
    var a = li.querySelector('.link');
    a.href = '#id=' + encodeURIComponent(r.id);
    li.querySelector('.id').textContent = r.id;
    return li;
  }
  function refRow(label, keys, cls) {
    return '<div class="refrow"><span class="lbl">' + label + '</span>' + keys.map(function (k) {
      return '<button type="button" class="ref ' + cls + '" data-cite="' + esc(k) + '">' + esc(k) + '</button>';
    }).join('') + '</div>';
  }
  function citeText(r) {
    var c = r.citations.join('; ');
    var t = (r.title || '').replace(/\s+Vs\.?\s+/i, ' v. ').replace(/\s+vs\.?\s+/i, ' v. ');
    return t ? t + (c ? ' (' + c + ')' : '') : c || r.id;
  }
  function copy(text) {
    var done = function () { toast('Copied: ' + text); };
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done, fallback);
    else fallback();
    function fallback() {
      var ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); done(); } catch (e) { toast(text); }
      document.body.removeChild(ta);
    }
  }
  var toastT;
  function toast(msg) {
    var t = document.querySelector('.toast');
    if (!t) { t = document.createElement('div'); t.className = 'toast'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
    t.textContent = msg.length > 110 ? msg.slice(0, 107) + '…' : msg;
    clearTimeout(toastT); toastT = setTimeout(function () { t.remove(); }, 2200);
  }

  function renderStatus(n) {
    var p = [];
    var pill = function (label, key) { return '<span class="pill">' + esc(label) + '<button type="button" data-clear="' + key + '" aria-label="Remove filter">&times;</button></span>'; };
    if (state.id) p.push(pill('Entry ' + state.id, 'id'));
    if (state.cite) p.push(pill('Citation: ' + state.cite, 'cite'));
    if (state.id || state.cite) { $('status').innerHTML = '<span><strong>' + n + '</strong> of ' + DB.length + ' entries</span>' + p.join(''); return; }
    if (state.saved) p.push(pill('My list', 'saved'));
    if (state.q) p.push(pill('“' + state.q.replace(/^"|"$/g, '') + '”', 'q'));
    if (state.subject) p.push(pill(state.subject, 'subject'));
    if (state.topic) p.push(pill(state.topic, 'topic'));
    if (state.side) p.push(pill(state.side + ' side', 'side'));
    if (state.prov) p.push(pill(state.prov, 'prov'));
    if (state.status) p.push(pill(state.status === 'Needs correction' ? 'Under review' : state.status, 'status'));
    if (state.court) p.push(pill(state.court, 'court'));
    if (state.outcome) p.push(pill(state.outcome, 'outcome'));
    if (state.from || state.to) p.push(pill((state.from || '…') + '–' + (state.to || '…'), 'years'));
    $('status').innerHTML = '<span><strong>' + n + '</strong> of ' + DB.length + ' entries</span>' + p.join('');
  }
  function renderCitePanel() {
    var el = $('citePanel');
    if (!state.cite) { el.hidden = true; return; }
    var x = byCite[state.cite] || { main: [], rel: [], con: [] };
    var parts = [];
    if (x.main.length) parts.push(x.main.length + ' as the main authority');
    if (x.rel.length) parts.push(x.rel.length + ' as an authority relied upon');
    if (x.con.length) parts.push(x.con.length + ' as contrary authority');
    el.innerHTML = '<h2>' + esc(state.cite) + '</h2><p>Referred to in ' + (parts.join(', ') || 'no entries') + '.</p>';
    el.hidden = false;
  }

  function renderListPanel(list) {
    var el = $('listPanel');
    if (!state.saved || state.id || state.cite) { el.hidden = true; return; }
    el.innerHTML = '<h2>My list</h2><p>Entries you have saved on this device. They are not shared with anyone else.</p>' +
      (list.length ? '<div class="list-actions"><button type="button" data-list="copy">Copy all citations</button><button type="button" data-list="print">Print list</button><button type="button" data-list="clear">Clear list</button></div>' : '');
    el.hidden = false;
  }

  /* ---------- state & events ---------- */
  function syncControls() {
    $('q').value = state.q;
    $('clearQ').hidden = !state.q;
    Array.prototype.forEach.call(document.querySelectorAll('#subjectList button'), function (b) {
      b.classList.toggle('on', b.getAttribute('data-subject') === state.subject);
    });
    buildTopics();
    Array.prototype.forEach.call(document.querySelectorAll('#sideChips .chip'), function (b) {
      b.classList.toggle('on', b.getAttribute('data-side') === state.side);
    });
    Array.prototype.forEach.call(document.querySelectorAll('#statusChips .chip'), function (b) {
      b.classList.toggle('on', b.getAttribute('data-status') === state.status);
    });
    $('fProv').value = state.prov;
    $('fCourt').value = state.court; $('fOutcome').value = state.outcome;
    $('fFrom').value = state.from; $('fTo').value = state.to; $('fSort').value = state.sort;
  }
  function writeHash() {
    var p = [];
    Object.keys(state).forEach(function (k) {
      if (state[k] && !(k === 'sort' && state[k] === 'rel')) p.push(k + '=' + encodeURIComponent(state[k]));
    });
    var h = p.join('&');
    if (location.hash.slice(1) !== h) history.replaceState(null, '', h ? '#' + h : location.pathname + location.search);
  }
  function readHash() {
    var h = location.hash.slice(1);
    Object.keys(state).forEach(function (k) { state[k] = k === 'sort' ? 'rel' : ''; });
    if (/^FLC-\d+$/.test(h)) { state.id = h; return; }
    h.split('&').forEach(function (kv) {
      var i = kv.indexOf('='); if (i < 0) return;
      var k = kv.slice(0, i), v = decodeURIComponent(kv.slice(i + 1));
      if (k in state) state[k] = v;
    });
  }
  function set(changes) {
    Object.keys(changes).forEach(function (k) { state[k] = changes[k]; });
    shown = PAGE;
    writeHash();
    render();
  }
  function go(changes) {  // a navigation: clear single-entry and citation views
    var c = { id: '', cite: '' };
    Object.keys(changes).forEach(function (k) { c[k] = changes[k]; });
    set(c);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function bind() {
    var t;
    $('q').addEventListener('input', function (e) {
      clearTimeout(t);
      var v = e.target.value;
      t = setTimeout(function () { go({ q: v.trim() }); }, 180);
    });
    $('searchForm').addEventListener('submit', function (e) { e.preventDefault(); go({ q: $('q').value.trim() }); });
    $('clearQ').addEventListener('click', function () { go({ q: '' }); $('q').focus(); });
    $('subjectList').addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return;
      go({ subject: b.getAttribute('data-subject'), topic: '' });
    });
    $('fTopic').addEventListener('change', function (e) { go({ topic: e.target.value }); });
    $('sideChips').addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return;
      go({ side: b.getAttribute('data-side') });
    });
    $('statusChips').addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return;
      go({ status: b.getAttribute('data-status') });
    });
    $('fProv').addEventListener('change', function (e) { go({ prov: e.target.value }); });
    $('listBtn').addEventListener('click', function () {
      var c = {}; Object.keys(RESET).forEach(function (k) { c[k] = RESET[k]; });
      c.saved = state.saved ? '' : '1';
      go(c);
    });
    $('listPanel').addEventListener('click', function (e) {
      var b = e.target.closest('[data-list]'); if (!b) return;
      var k = b.getAttribute('data-list');
      if (k === 'copy') copy(filtered().list.map(citeText).join('\n'));
      if (k === 'print') { shown = 9999; render(); window.print(); }
      if (k === 'clear') { saved = []; storeSaved(); render(); }
    });
    var sheet = function (open) {
      $('filterPanel').classList.toggle('open', open);
      $('sheetBackdrop').hidden = !open;
      document.body.classList.toggle('sheet-open', open);
      $('filtersToggle').setAttribute('aria-expanded', open ? 'true' : 'false');
    };
    $('filtersDone').addEventListener('click', function () { sheet(false); });
    $('filtersClose').addEventListener('click', function () { sheet(false); });
    $('sheetBackdrop').addEventListener('click', function () { sheet(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') sheet(false); });
    $('filtersToggle').addEventListener('click', function () { sheet(!$('filterPanel').classList.contains('open')); });
    $('fCourt').addEventListener('change', function (e) { go({ court: e.target.value }); });
    $('fOutcome').addEventListener('change', function (e) { go({ outcome: e.target.value }); });
    $('fFrom').addEventListener('change', function (e) { go({ from: e.target.value }); });
    $('fTo').addEventListener('change', function (e) { go({ to: e.target.value }); });
    $('fSort').addEventListener('change', function (e) { set({ sort: e.target.value }); });
    $('resetAll').addEventListener('click', function () {
      go(JSON.parse(JSON.stringify(RESET)));
    });
    $('moreBtn').addEventListener('click', function () { shown += PAGE; render(); });
    $('status').addEventListener('click', function (e) {
      var b = e.target.closest('[data-clear]'); if (!b) return;
      var k = b.getAttribute('data-clear'), c = {};
      if (k === 'years') { c.from = ''; c.to = ''; } else c[k] = '';
      if (k === 'subject') c.topic = '';
      set(c);
    });
    $('cards').addEventListener('click', function (e) {
      var el = e.target.closest('[data-cite]');
      if (el) { go({ cite: el.getAttribute('data-cite'), saved: '' }); return; }
      var s = e.target.closest('.crumb [data-subject]');
      if (s) go({ q: '', subject: s.getAttribute('data-subject'), topic: s.getAttribute('data-topic') || '' });
    });
    window.addEventListener('hashchange', function () { readHash(); shown = PAGE; render(); });
    document.querySelector('.brand').addEventListener('click', function (e) {
      e.preventDefault();
      go(JSON.parse(JSON.stringify(RESET)));
    });
  }
})();
