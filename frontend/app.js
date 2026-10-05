const root = document.getElementById('app');
const toastRoot = document.getElementById('toast-root');

const state = {
  page: 'dashboard',
  scanMode: 'photo',
  dashboard: null,
  inspections: [],
  inspection: null,
  selectedOnion: null,
  rules: null,
  sources: [],
  dataset: null,
  fieldPhotos: null,
  models: null,
  reports: [],
  report: null,
  verification: null,
  verifyId: null,
  cameraStream: null,
  busy: false,
  trainingStatus: null,
  trainingTimer: null,
  annotationId: null,
  annotation: null,
  annotationDraft: [],
  annotationLabels: ['healthy'],
  annotationForm: null,
  annotationDirty: false,
  mobileMenuOpen: false,
  lastDatasetExport: null,
  error: null,
};

const icons = {
  brand: '<path d="M12 2.7c1.5 3.6 5.8 5.6 7.2 10.1 1.9 6.4-1.1 10.6-7.2 10.6S4.8 19.2 4.8 13c0-4.6 4.3-6.9 7.2-10.3Z"/><path d="M12 2.5c0 2.2-1.2 3.8-2.5 4.8"/><path d="M8.2 15.4c.5 2.1 2.1 3.5 4.4 3.7"/>',
  dashboard: '<rect x="3" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="3" width="8" height="5" rx="1.5"/><rect x="13" y="10" width="8" height="11" rx="1.5"/><rect x="3" y="13" width="8" height="8" rx="1.5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  camera: '<path d="M14.5 5.5h-7l-1.6 2H4a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-1.9l-1.6-2Z"/><circle cx="12" cy="13" r="3.3"/>',
  image: '<rect x="3" y="3" width="18" height="18" rx="2.5"/><circle cx="8.4" cy="8.2" r="1.3"/><path d="m21 15-5-5L5 20"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/>',
  book: '<path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v17H6.5A2.5 2.5 0 0 0 4 21.5z"/><path d="M4 4.5v17M8 6h8M8 10h8"/>',
  dataset: '<path d="M4 4.5C4 3.1 7.6 2 12 2s8 1.1 8 2.5S16.4 7 12 7 4 5.9 4 4.5Z"/><path d="M4 4.5v6C4 12 7.6 13 12 13c2.4 0 4.5-.3 6-1M4 10.5v6C4 18 7.6 19 12 19"/><path d="M20 12v7M16.5 15.5H23"/>',
  training: '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/>',
  model: '<path d="M12 3 4 7v10l8 4 8-4V7l-8-4Z"/><path d="m4 7 8 5 8-5M12 12v9M8 5l8 5"/>',
  rules: '<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="9" cy="6" r="2" fill="currentColor" stroke="none"/><circle cx="15" cy="12" r="2" fill="currentColor" stroke="none"/><circle cx="8" cy="18" r="2" fill="currentColor" stroke="none"/>',
  report: '<path d="M6 2.8h8l4 4V21H6a2 2 0 0 1-2-2V4.8a2 2 0 0 1 2-2Z"/><path d="M14 3v5h5M8 12h7M8 16h7"/>',
  settings: '<path d="M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z"/><path d="m19.4 15 .1.1a1.6 1.6 0 0 1-2.3 2.3l-.1-.1a1.6 1.6 0 0 0-2.7 1.1v.2a1.6 1.6 0 0 1-3.2 0v-.2a1.6 1.6 0 0 0-2.7-1.1l-.1.1a1.6 1.6 0 1 1-2.3-2.3l.1-.1a1.6 1.6 0 0 0-1.1-2.7h-.2a1.6 1.6 0 0 1 0-3.2h.2a1.6 1.6 0 0 0 1.1-2.7l-.1-.1a1.6 1.6 0 1 1 2.3-2.3l.1.1a1.6 1.6 0 0 0 2.7-1.1v-.2a1.6 1.6 0 0 1 3.2 0v.2a1.6 1.6 0 0 0 2.7 1.1l.1-.1a1.6 1.6 0 0 1 2.3 2.3l-.1.1a1.6 1.6 0 0 0 1.1 2.7h.2a1.6 1.6 0 0 1 0 3.2h-.2a1.6 1.6 0 0 0-1.1 2.7Z"/>',
  upload: '<path d="M12 16V4m0 0L7 9m5-5 5 5"/><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
  search: '<circle cx="10.8" cy="10.8" r="6.6"/><path d="m16 16 4.5 4.5"/>',
  arrow: '<path d="M5 12h14m-6-6 6 6-6 6"/>',
  chevron: '<path d="m9 18 6-6-6-6"/>',
  shield: '<path d="M12 3 4.5 6v5.7c0 4.3 3.2 7.8 7.5 9.3 4.3-1.5 7.5-5 7.5-9.3V6L12 3Z"/><path d="m9 12 2 2 4-4"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  alert: '<path d="M12 3 2.8 19h18.4L12 3Z"/><path d="M12 9v4m0 3h.01"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.2 2"/>',
  onion: '<path d="M12 2.7c1.5 3.6 5.8 5.6 7.2 10.1 1.9 6.4-1.1 10.6-7.2 10.6S4.8 19.2 4.8 13c0-4.6 4.3-6.9 7.2-10.3Z"/><path d="M12 2.5c0 2.2-1.2 3.8-2.5 4.8"/><path d="M12 19c-2.8 0-4.3-2-4.7-4.2"/>',
  gauge: '<path d="M4.9 19a9 9 0 1 1 14.2 0"/><path d="m12 13 4-4M6.5 16h.01M17.5 16h.01"/>',
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  external: '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h5"/>',
  download: '<path d="M12 3v12m0 0 5-5m-5 5-5-5"/><path d="M4 18v3h16v-3"/>',
  print: '<path d="M6 9V3h12v6M6 17H4a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v7H6z"/><path d="M18 12h.01"/>',
};

function icon(name, size = 18) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.onion}</svg>`;
}
function esc(value = '') {
  return String(value).replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
}
function fmt(value, digits = 1) { return value == null || Number.isNaN(Number(value)) ? '—' : Number(value).toFixed(digits); }
function todayKey() { return new Date().toISOString().slice(0, 10).replaceAll('-', ''); }
function humanDate(value, withTime = false) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', year: 'numeric', ...(withTime ? { hour: '2-digit', minute: '2-digit' } : {}) }).format(date);
}
function friendlyGrade(grade) { return ({ GRADE_A: 'Grade A', URS: 'URS', REJECT: 'Reject', MANUAL_REVIEW: 'Manual review' })[grade] || grade || '—'; }
function gradeClass(grade) { return ({ GRADE_A: 'green', URS: 'orange', REJECT: 'red', MANUAL_REVIEW: 'blue' })[grade] || 'gray'; }
function badge(grade, text = friendlyGrade(grade)) { return `<span class="badge badge-${gradeClass(grade)}">${esc(text)}</span>`; }
function pct(part, total) { return total ? Math.round((part / total) * 100) : 0; }

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, options);
  } catch (error) {
    throw new Error('Could not reach the PYAazScan service. Check that the backend is available and retry.');
  }
  const type = response.headers.get('content-type') || '';
  const body = type.includes('application/json') ? await response.json() : null;
  if (!response.ok) {
    const detail = body?.detail;
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status}).`);
  }
  return body;
}
function toast(message, kind = '') {
  const item = document.createElement('div');
  item.className = `toast ${kind}`;
  item.textContent = message;
  toastRoot.appendChild(item);
  setTimeout(() => item.remove(), 4200);
}
function stopCamera() {
  if (state.cameraStream) {
    state.cameraStream.getTracks().forEach((track) => track.stop());
    state.cameraStream = null;
  }
}

const navigation = [
  { label: 'OVERVIEW', items: [{ id: 'dashboard', label: 'Dashboard', icon: 'dashboard' }] },
  { label: 'FIELD INSPECTION', items: [{ id: 'new-inspection', label: 'New inspection', icon: 'plus' }, { id: 'inspections', label: 'Inspections', icon: 'list' }, { id: 'reports', label: 'Reports & verification', icon: 'report' }] },
  { label: 'MODEL DEVELOPMENT', items: [{ id: 'research', label: 'Research', icon: 'book' }, { id: 'dataset', label: 'Dataset & labels', icon: 'dataset' }, { id: 'training', label: 'Training', icon: 'training' }, { id: 'models', label: 'Models & evaluation', icon: 'model' }] },
  { label: 'GOVERNANCE', items: [{ id: 'rules', label: 'Rules & policy', icon: 'rules' }, { id: 'settings', label: 'Limitations & setup', icon: 'settings' }] },
];
const pageTitle = {
  dashboard: 'Dashboard', 'new-inspection': 'New inspection', inspections: 'Inspections', 'inspection-detail': 'Inspection detail', research: 'Research & model development', dataset: 'Dataset & annotation', 'dataset-annotate': 'Polygon annotation studio', training: 'Model training', models: 'Models & evaluation', rules: 'Procurement rules', reports: 'Reports & audit', settings: 'Limitations & setup', verify: 'Report verification',
};

function shell(content) {
  const activeId = state.page === 'inspection-detail' ? 'inspections' : state.page === 'dataset-annotate' ? 'dataset' : state.page;
  const nav = navigation.map((group) => `<div class="nav-label">${group.label}</div><div class="sidebar-nav">${group.items.map((item) => `<button class="nav-link ${activeId === item.id ? 'active' : ''}" data-nav="${item.id}" title="${item.label}">${icon(item.icon)}<span>${item.label}</span></button>`).join('')}</div>`).join('');
  const date = new Intl.DateTimeFormat('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }).format(new Date());
  return `<div class="app-shell">
    <aside class="sidebar">
      <a class="brand" href="#dashboard" data-nav="dashboard" aria-label="PYAazScan dashboard"><span class="brand-mark">${icon('brand', 23)}</span><span class="brand-copy"><span class="brand-name">PYAazScan</span><span class="brand-caption">Procurement intelligence</span></span></a>
      ${nav}
      <div class="sidebar-spacer"></div>
      <div class="engine-status"><div class="engine-status-head"><span class="status-dot"></span>Demo CV engine active</div><p>Classical vision fallback<br>No trained model loaded</p></div>
      <div class="sidebar-profile"><div class="avatar">KO</div><div><div class="profile-name">Kavita Officer</div><div class="profile-role">Procurement · Field user</div></div></div>
    </aside>
    <div class="main-wrap">
      <header class="topbar"><div class="breadcrumb"><span>FIELD OPERATIONS</span>${icon('chevron', 12)}<strong>${esc(pageTitle[state.page] || 'PYAazScan')}</strong></div><div class="topbar-right"><span class="topbar-status"><span class="status-dot"></span>Local system ready</span><span class="topbar-date">${date}</span><div class="avatar top-avatar">KO</div></div></header>
      <main class="content">${content}<footer class="footer-note"><span>PYAazScan · External visual quality assessment · Decision support only</span><span>Rule profile is buyer-configurable · Human review remains authoritative</span></footer></main>
    </div>
    <nav class="mobile-nav" aria-label="Mobile navigation"><button class="${activeId === 'dashboard' ? 'active' : ''}" data-nav="dashboard">${icon('dashboard', 17)}<span>Home</span></button><button class="${activeId === 'inspections' ? 'active' : ''}" data-nav="inspections">${icon('list', 17)}<span>Lots</span></button><button class="mobile-scan" data-nav="new-inspection" aria-label="New inspection">${icon('plus', 19)}</button><button class="${activeId === 'reports' ? 'active' : ''}" data-nav="reports">${icon('report', 17)}<span>Reports</span></button><button class="${state.mobileMenuOpen || activeId === 'settings' ? 'active' : ''}" data-action="open-mobile-menu" aria-expanded="${state.mobileMenuOpen ? 'true' : 'false'}">${icon('list', 17)}<span>Menu</span></button></nav>
    ${state.mobileMenuOpen ? `<div class="mobile-menu-backdrop" data-action="close-mobile-menu"><section class="mobile-menu-panel" role="dialog" aria-modal="true" aria-label="All PYAazScan pages"><div class="mobile-menu-heading"><div><strong>All workspace pages</strong><small>Navigate PYAazScan</small></div><button class="mobile-menu-close" data-action="close-mobile-menu" aria-label="Close menu">${icon('close', 17)}</button></div>${navigation.map((group) => `<div class="mobile-menu-group"><span>${group.label}</span><div>${group.items.map((item) => `<button class="mobile-menu-link ${activeId === item.id ? 'active' : ''}" data-nav="${item.id}">${icon(item.icon, 16)}<span>${item.label}</span>${activeId === item.id ? '<i>Current</i>' : ''}</button>`).join('')}</div></div>`).join('')}</section></div>` : ''}
    ${state.report ? renderReportModal() : ''}
    ${state.busy ? '<div class="processing-overlay"><div class="processing-card"><div class="spinner"></div><h3>Assessing visible onion quality</h3><p>Checking image quality, finding individual bulbs, measuring, scoring visible cues and applying the saved procurement rule profile.</p></div></div>' : ''}
  </div>`;
}
function heading(eyebrow, title, subtitle, actions = '') {
  return `<section class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p class="page-subtitle">${subtitle}</p></div>${actions ? `<div class="page-actions">${actions}</div>` : ''}</section>`;
}
function statCard(label, value, foot, ico, color = '') {
  return `<div class="card kpi-card"><div class="kpi-top"><span class="kpi-label">${label}</span><span class="kpi-icon ${color}">${icon(ico, 16)}</span></div><div class="kpi-value">${value}</div><div class="kpi-foot"><span class="dot-mini"></span>${foot}</div></div>`;
}
function emptyState(title, copy, button = '') {
  return `<div class="empty-state"><div class="empty-icon">${icon('onion', 22)}</div><p class="empty-title">${title}</p><p class="empty-copy">${copy}</p>${button}</div>`;
}
function dashboardPage() {
  const data = state.dashboard || {};
  const average = data.average_grade_a_percentage == null ? '—' : `${fmt(data.average_grade_a_percentage, 1)}%`;
  const review = data.average_manual_review_percentage == null ? '—' : `${fmt(data.average_manual_review_percentage, 1)}%`;
  const rows = data.recent_inspections || [];
  const table = rows.length ? `<div class="table-scroll"><table><thead><tr><th>Lot / inspection</th><th>Grade A</th><th>URS</th><th>Reject</th><th>Sample</th><th>Rule set</th><th>Status</th></tr></thead><tbody>${rows.slice(0, 6).map((item) => `<tr class="clickable" data-action="open-inspection" data-id="${esc(item.inspection_id)}"><td><span class="lot-id">${esc(item.lot_id)}</span><div class="card-caption" style="margin-top:4px">${esc(item.inspection_id)} · ${humanDate(item.created_at)}</div></td><td class="grade-percent">${fmt(item.percentages?.grade_a, 1)}%</td><td>${fmt(item.percentages?.urs, 1)}%</td><td>${fmt(item.percentages?.reject, 1)}%</td><td>${item.sample_size}</td><td>${esc(item.rule_set_id || '—')}</td><td>${badge(item.summary?.manual_review ? 'MANUAL_REVIEW' : 'GRADE_A', item.summary?.manual_review ? `${item.summary.manual_review} review` : 'Complete')}</td></tr>`).join('')}</tbody></table></div>` : emptyState('Your inspection ledger starts here', 'Scan a photo to create a saved lot assessment, visual inspection map and verifiable report.', '<button class="btn btn-secondary btn-small" data-nav="new-inspection">Open photo scanner</button>');
  const recentTrend = (data.grade_a_trend || []).slice(-5);
  const bars = recentTrend.map((item) => `<div class="pipeline-row"><span class="pipeline-check">${icon('check', 10)}</span><div><div class="pipeline-label">${esc(item.lot_id)}</div><div class="pipeline-note">Grade A share · ${fmt(item.percentage, 1)}%</div></div><span class="pipeline-time">${Math.round(item.percentage || 0)}%</span></div>`).join('');
  return `${heading('FIELD OPERATIONS / OVERVIEW', 'AI-powered onion procurement intelligence', 'Standardize external visual quality assessment, reduce grading subjectivity, and create transparent digital inspection records.', '<button class="btn btn-primary" data-nav="new-inspection">'+icon('plus', 15)+' Start inspection</button>')}
    <section class="dashboard-hero"><div class="hero-copy"><div class="hero-kicker"><span></span>Evidence-led procurement</div><h2>One photo. Clear evidence. A decision you can explain.</h2><p>Measure each bulb, surface visible defects and apply a versioned buyer rule set — with manual review when evidence is uncertain.</p><div class="hero-actions"><button class="btn btn-primary" data-nav="new-inspection">${icon('image', 15)} Scan from photo</button><button class="btn btn-secondary" data-action="start-camera">${icon('camera', 15)} Take a photo</button></div></div><div class="hero-art" aria-hidden="true"><span class="hero-ring"></span><span class="hero-onion"></span></div></section>
    <section class="grid kpi-grid">${statCard('INSPECTIONS TODAY', String(data.today_inspections ?? 0), 'Saved inspection records', 'list')}${statCard('ONIONS ASSESSED', String(data.onions_inspected ?? 0), 'Across saved inspections', 'onion')}${statCard('AVERAGE GRADE A', average, data.total_inspections ? 'Mean lot percentage' : 'No inspection data yet', 'gauge')}${statCard('MANUAL REVIEW', review, data.total_inspections ? 'Mean lot percentage' : 'No review data yet', 'alert')}</section>
    <section class="grid dashboard-lower"><div class="card table-card"><div class="card-heading"><div><div class="card-title">Recent inspections</div><p class="card-caption">Latest saved lot assessments · click a row to review its evidence</p></div><button class="understated-link" data-nav="inspections">View all ${icon('arrow', 12)}</button></div>${table}</div><aside class="card side-insight-card"><div class="insight-headline"><div><div class="card-title">Lot quality pulse</div><p class="card-caption">Grade A share from recent inspections</p></div><span class="badge badge-green">${rows.length ? `${rows.length} lots` : 'No data'}</span></div><div class="pipeline">${bars || `<div class="empty-state" style="padding:30px 8px 17px"><div class="empty-icon">${icon('gauge', 22)}</div><p class="empty-title">No lot results yet</p><p class="empty-copy">Your real inspection records will appear here.</p></div>`}</div></aside></section>`;
}

function fieldPhotoTiles(images, mode) {
  return images.map((item) => {
    const facts = [`${item.width || '?'} × ${item.height || '?'} px`, item.orientation === 'portrait' ? 'portrait' : 'landscape', item.detections_expected ? `~${item.detections_expected} bulb region${item.detections_expected === 1 ? '' : 's'}` : 'regions vary'].join(' · ');
    const inspectButton = `<button class="btn ${mode === 'dataset' ? 'btn-secondary' : 'btn-primary'} btn-small" data-action="scan-field-photo" data-id="${esc(item.id)}">${icon('image', 12)} Inspect</button>`;
    const queueButton = `<button class="btn ${mode === 'dataset' ? 'btn-primary' : 'btn-secondary'} btn-small" data-action="queue-field-photo" data-id="${esc(item.id)}">${icon('dataset', 12)} ${mode === 'dataset' ? 'Annotate' : 'Label'}</button>`;
    return `<div class="photo-tile"><button type="button" class="photo-tile-image" data-action="scan-field-photo" data-id="${esc(item.id)}" title="Inspect ${esc(item.id)}"><img loading="lazy" src="${esc(item.thumbnail_url)}" alt="Field photograph ${esc(item.id)} · ${esc(item.title)}" /></button><div class="photo-tile-body"><div class="photo-tile-title"><strong>${esc(item.id)}</strong><span>${esc(item.health || 'unclassified')}</span></div><div class="photo-tile-class">${esc(item.title)}</div><div class="photo-tile-note">${esc(facts)}</div><div class="photo-tile-actions">${inspectButton}${queueButton}</div></div></div>`;
  }).join('');
}
function fieldPhotoPanel(mode = 'inspect') {
  const data = state.fieldPhotos;
  if (!data) return '';
  const images = data.images || [];
  // Without an import, only the dataset page explains how to get the pack; the capture page stays clean.
  if (data.status !== 'ready' && mode !== 'dataset') return '';
  const source = data.source || {};
  const ready = data.status === 'ready' && images.length;
  const headingCopy = ready
    ? `${images.length} of ${(source.reported_total_images || 0).toLocaleString('en-IN')} published photographs · imported ${humanDate(data.generated_at)} · no calibration marker, no polygons yet`
    : 'Optional real-photo set for the demo and the annotation queue';
  const badge = ready
    ? `<span class="badge badge-blue">${esc(source.licence || 'CC BY 4.0')} · Zenodo ${esc(source.record_id || '')}</span>`
    : '<span class="badge badge-gray">Not imported</span>';
  const body = ready
    ? `<div class="photo-grid">${fieldPhotoTiles(images, mode)}</div>
      <div class="photo-grid-foot">${mode === 'dataset' ? `<button class="btn btn-secondary btn-small" data-action="queue-all-field-photos" data-limit="${Math.min(images.length, 100)}">${icon('dataset', 12)} Queue all ${images.length} for annotation</button>` : `<button class="btn btn-secondary btn-small" data-action="queue-all-field-photos" data-limit="${Math.min(images.length, 100)}">${icon('dataset', 12)} Add all to the annotation queue</button>`}<span>Attribution required when shown or exported: <em>${esc(data.attribution || '')}</em></span></div>`
    : `<div class="notice">${icon('alert', 14)}<span><strong>The published onion photo pack is not on this machine.</strong> Upload images manually, or import real photographs once and they appear here and on the capture page. To add the pack, download <code>Onion Image Dataset.zip</code> from <a href="https://zenodo.org/records/20254934" target="_blank" rel="noopener">Zenodo record 20254934</a> (CC BY 4.0, ~1.5 GB), then run:<div class="photo-command"><code>python data/demo/import_zenodo_onions.py --zip "&lt;path to the archive&gt;"</code><span>The script copies a small attributed subset into <code>data/demo/zenodo/</code>; the app reads it on the next page load.</span></div></span></div>`;
  return `<section class="card content-block field-photo-card"><div class="card-heading"><div><h2>Field photographs</h2><p>${headingCopy}</p></div>${badge}</div>${body}</section>`;
}

function inspectionMetaForm() {
  return `<div class="card scan-context"><div class="card-heading"><div><div class="card-title">Inspection context</div><p class="card-caption">Recorded with the image evidence and rule snapshot</p></div><span class="label-badge">Required for audit</span></div><div class="form-grid" style="margin-top:13px"><div class="field"><label for="lot-id">LOT ID</label><input id="lot-id" maxlength="64" value="LOT-${todayKey()}" placeholder="e.g. LOT-NASIK-042" /></div><div class="field"><label for="centre">PROCUREMENT CENTRE</label><input id="centre" maxlength="120" value="Nashik · Demo procurement centre" placeholder="Centre / mandi name" /></div><div class="field"><label for="operator">OPERATOR</label><input id="operator" maxlength="120" value="Kavita Officer" placeholder="Inspector name" /></div></div></div>`;
}
function capturePanel() {
  const cameraMode = state.scanMode === 'camera';
  const cameraActive = cameraMode && state.cameraStream;
  return `<div class="capture-card"><div class="capture-head"><span class="capture-head-title">${cameraMode ? 'Camera capture' : 'Photo inspection'}</span><span class="badge badge-gray">Step 01 / 03 · Capture</span></div><div class="capture-stage" id="capture-stage">
    ${cameraActive ? `<video id="camera-video" class="camera-preview" autoplay muted playsinline></video><div class="capture-buttons" style="margin-top:13px"><button class="btn btn-primary" data-action="capture-camera">${icon('camera', 14)} Capture & assess</button><button class="btn btn-secondary" data-action="close-camera">Close camera</button></div><div class="support-line">The camera takes one still image; inference runs after capture.</div>` : `<span class="upload-glyph">${icon(cameraMode ? 'camera' : 'upload', 24)}</span><div class="capture-title">${cameraMode ? 'Ready to inspect with your camera?' : 'Bring the inspection image into focus'}</div><p class="capture-copy">${cameraMode ? 'Use your phone’s rear camera, spread the onions apart, and capture a single still frame for analysis.' : 'Choose a well-lit overhead photo with onions separated on a plain, contrasting surface. A visible 50 mm blue-square reference enables an estimated millimetre scale.'}</p><div class="capture-buttons">${cameraMode ? `<button class="btn btn-primary" data-action="open-camera">${icon('camera', 14)} Open camera</button>` : `<label class="btn btn-primary" for="photo-file">${icon('image', 14)} Choose photo</label><input id="photo-file" data-kind="scan" data-mode="photo" type="file" accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp" hidden /><button class="btn btn-secondary" data-action="load-demo">${icon('onion', 14)} Load demo image</button>`}<button class="btn btn-secondary" data-action="${cameraMode ? 'load-demo' : 'start-camera'}">${icon(cameraMode ? 'image' : 'camera', 14)} ${cameraMode ? 'Use demo photo' : 'Take a photo'}</button></div><div class="support-line">JPG · PNG · WEBP · Up to 12 MB · HEIC conversion is not enabled</div>`}
  </div></div>`;
}
function newInspectionPage() {
  const sample = state.inspection;
  return `${heading('FIELD INSPECTION / CAPTURE', 'New inspection', 'Capture a representative sample and turn visible evidence into an explainable, versioned lot record.', '<button class="btn btn-secondary" data-action="load-demo">'+icon('onion', 14)+' Load demo image</button>')}
    <div class="scan-layout"><div class="scan-main"><div class="scan-mode-tabs"><button class="mode-tab ${state.scanMode === 'photo' ? 'active' : ''}" data-action="scan-mode" data-mode="photo">${icon('image', 14)} Scan from photo</button><button class="mode-tab ${state.scanMode === 'camera' ? 'active' : ''}" data-action="scan-mode" data-mode="camera">${icon('camera', 14)} Camera scan</button></div>${capturePanel()}${inspectionMetaForm()}${fieldPhotoPanel('inspect')}${sample ? `<div class="notice notice-green">${icon('check', 14)}<span><strong>Previous inspection saved:</strong> ${esc(sample.inspection_id)} · ${sample.sample_size} onions. <button class="understated-link" data-action="open-inspection" data-id="${esc(sample.inspection_id)}">Open result</button></span></div>` : ''}</div><aside class="scan-sidebar"><div class="card context-list"><div class="card-title">Capture conditions</div><p class="card-caption">Small improvements make the evidence more useful.</p><div class="tip-row"><span class="tip-icon">1</span><span class="tip-text"><strong>Use a plain background.</strong> Separate bulbs from the table colour and each other.</span></div><div class="tip-row"><span class="tip-icon">2</span><span class="tip-text"><strong>Keep light even.</strong> Avoid hard shadows, glare and coloured lighting.</span></div><div class="tip-row"><span class="tip-icon">3</span><span class="tip-text"><strong>Place the reference square.</strong> A 50 mm blue marker enables a rough scale estimate.</span></div></div><div class="card checklist"><div class="card-title">What this scan can do</div><div class="tip-row"><span class="tip-icon">✓</span><span class="tip-text">Find separated bulb regions and draw a numbered inspection map.</span></div><div class="tip-row"><span class="tip-icon">✓</span><span class="tip-text">Measure pixels; report millimetres only when the reference is visible.</span></div><div class="tip-row"><span class="tip-icon">✓</span><span class="tip-text">Surface sprout-like green growth and dark-patch cues for review.</span></div><div class="tip-row"><span class="tip-icon">!</span><span class="tip-text"><strong>Not an internal quality test.</strong> RGB imagery cannot establish firmness, internal rot or maturity.</span></div></div></aside></div>`;
}

function formatDefects(onion) {
  const checks = onion.defect_assessments || {};
  return ['sprouted', 'rotten', 'damaged', 'undersized'].map((name) => {
    const item = checks[name] || {};
    const active = !!item.detected;
    const confidence = item.confidence == null ? '—' : `${(Number(item.confidence) * 100).toFixed(0)}%`;
    return `<div class="defect-check ${active ? 'detected' : ''}"><strong>${name[0].toUpperCase() + name.slice(1)}</strong><span>${active ? 'Detected' : 'Not seen'} · ${confidence}</span></div>`;
  }).join('');
}
function selectedOnionCard(onion, inspection) {
  if (!onion) return `<div class="card onion-detail-card">${emptyState('Select an onion', 'Choose a numbered bulb on the map to inspect its size, evidence scores and decision reasons.')}</div>`;
  const diameter = onion.diameter_mm == null ? `${fmt(onion.diameter_px, 0)} <small>px · estimated</small>` : `${fmt(onion.diameter_mm, 1)} <small>mm</small>`;
  const reasonTitle = onion.grade === 'REJECT' ? 'WHY REJECTED?' : onion.grade === 'MANUAL_REVIEW' ? 'MANUAL REVIEW REQUIRED' : onion.grade === 'URS' ? 'WHY URS?' : 'DECISION BASIS';
  const typeClass = onion.grade === 'MANUAL_REVIEW' ? 'manual' : onion.grade === 'URS' ? 'urs' : '';
  const reasons = (onion.decision_reasons || []).map((reason) => `<li>${esc(reason)}</li>`).join('');
  const defects = (onion.defects || []).length ? onion.defects.map((item) => `<li>${esc(item.type.replaceAll('_', ' '))} evidence score ${(Number(item.confidence) * 100).toFixed(1)}%</li>`).join('') : '<li>No visible defect cue crossed the current heuristic threshold.</li>';
  const bandLabel = onion.confidence_band === 'high' ? 'High evidence band' : onion.confidence_band === 'assisted' ? 'Assisted evidence band' : onion.confidence_band === 'manual_review' ? 'Manual review band' : 'Officer-reviewed';
  const reviewActions = onion.grade === 'MANUAL_REVIEW' ? `<div class="review-actions"><button class="btn btn-soft btn-small" data-action="manual-grade" data-grade="GRADE_A" data-onion="${onion.onion_id}">Grade A</button><button class="btn btn-soft btn-small" data-action="manual-grade" data-grade="URS" data-onion="${onion.onion_id}">URS</button><button class="btn btn-danger btn-small" data-action="manual-grade" data-grade="REJECT" data-onion="${onion.onion_id}">Reject</button></div>` : '';
  const human = onion.human_decision ? `<div class="notice notice-green" style="margin:11px 0 0;padding:8px">${icon('check', 12)}<span>Officer decision recorded · ${esc(onion.human_decision.reviewer || 'Reviewer')}</span></div>` : '';
  return `<div class="card onion-detail-card"><div class="selected-top"><div class="selected-number"><span class="id-circle">#${String(onion.onion_id).padStart(2, '0')}</span><div><h3>Onion ${String(onion.onion_id).padStart(2, '0')}</h3><p>Object evidence detail</p></div></div><span class="decision-pill decision-${onion.grade.toLowerCase()}">${friendlyGrade(onion.grade)}</span></div><div class="measure-grid"><div class="measure-box"><div class="measure-label">DIAMETER</div><div class="measure-value">${diameter}</div></div><div class="measure-box"><div class="measure-label">DETECTION EVIDENCE</div><div class="measure-value">${(Number(onion.detection_confidence || 0) * 100).toFixed(1)}% <small>heuristic</small></div></div></div><div class="defect-checks">${formatDefects(onion)}</div><p class="evidence-note">${bandLabel} · scores are heuristic image evidence, not calibrated probabilities. Inspect the physical bulb before using this record for a purchase decision.</p><div class="reason-box ${typeClass}"><p class="reason-title">${reasonTitle}</p><ul class="reason-list">${reasons || defects}</ul>${onion.grade === 'REJECT' ? `<ul class="reason-list" style="margin-top:5px">${defects}</ul>` : ''}</div>${reviewActions}${human}</div>`;
}
function mapClass(grade) { return `grade-${String(grade || 'MANUAL_REVIEW').toLowerCase()}`; }
function imageMap(inspection) {
  const width = inspection.image?.width || inspection.image_width || 1000;
  const height = inspection.image?.height || inspection.image_height || 700;
  const onions = inspection.onions || [];
  const overlays = onions.map((onion) => {
    const box = onion.bbox || {};
    const selected = Number(state.selectedOnion) === Number(onion.onion_id);
    const left = (Number(box.x || 0) / width) * 100;
    const top = (Number(box.y || 0) / height) * 100;
    const w = (Number(box.width || 0) / width) * 100;
    const h = (Number(box.height || 0) / height) * 100;
    return `<button class="map-target ${mapClass(onion.grade)} ${selected ? 'selected' : ''}" data-action="select-onion" data-onion="${onion.onion_id}" data-title="Onion ${onion.onion_id} · ${friendlyGrade(onion.grade)}" aria-label="Open onion ${onion.onion_id}, ${friendlyGrade(onion.grade)}" style="left:${left}%;top:${top}%;width:${w}%;height:${h}%"></button>`;
  }).join('');
  return `<div class="image-stage" style="aspect-ratio:${width}/${height}"><img src="${esc(inspection.image?.url || `/api/inspection/${encodeURIComponent(inspection.inspection_id)}/image`)}" alt="Uploaded onion lot photo with per-onion inspection overlays" />${overlays}</div>`;
}
function donutMarkup(inspection) {
  const p = inspection.percentages || {};
  const a = Number(p.grade_a || 0), u = Number(p.urs || 0), r = Number(p.reject || 0), m = Number(p.manual_review || 0);
  const c = a + u, d = c + r;
  return `<div class="donut-wrap"><div class="donut" style="--a:${a}%;--b:${a}%;--c:${c}%;--d:${d}%"><div class="donut-center"><strong>${inspection.sample_size}</strong><span>ONIONS</span></div></div><div class="donut-legend"><div class="donut-legend-row"><i class="legend-dot" style="background:#3d8a59"></i><span>Grade A</span><b>${fmt(a, 1)}%</b></div><div class="donut-legend-row"><i class="legend-dot" style="background:#d48b3e"></i><span>URS</span><b>${fmt(u, 1)}%</b></div><div class="donut-legend-row"><i class="legend-dot" style="background:#c45449"></i><span>Reject</span><b>${fmt(r, 1)}%</b></div><div class="donut-legend-row"><i class="legend-dot" style="background:#5b84b5"></i><span>Review</span><b>${fmt(m, 1)}%</b></div></div></div>`;
}
function diameterHistogram(inspection) {
  const values = (inspection.onions || []).map((item) => item.diameter_mm).filter((value) => value != null).map(Number);
  const ranges = [{ label: '<40', count: 0, min: -Infinity, max: 40 }, { label: '40–45', count: 0, min: 40, max: 45 }, { label: '45–55', count: 0, min: 45, max: 55 }, { label: '55–65', count: 0, min: 55, max: 65 }, { label: '>65', count: 0, min: 65, max: Infinity }];
  values.forEach((value) => { const range = ranges.find((item) => value >= item.min && value < item.max); if (range) range.count += 1; });
  const largest = Math.max(1, ...ranges.map((item) => item.count));
  return `<div class="histogram">${ranges.map((range) => `<div class="hist-col"><span class="hist-bar" data-count="${range.count}" style="height:${Math.max(3, range.count / largest * 75)}%"></span><span class="hist-label">${range.label}</span></div>`).join('')}</div><p class="card-caption">Calibrated diameters only · ${values.length} measured · millimetres</p>`;
}
function defectBars(inspection) {
  const distribution = inspection.defect_distribution || {};
  const labels = { sprouted: 'Sprouted cue', rotten: 'Rot cue', damaged: 'Damage cue', undersized: 'Undersized', discoloration: 'Discoloration' };
  const entries = Object.entries(labels).map(([key, label]) => [key, label, Number(distribution[key] || 0)]);
  const max = Math.max(1, ...entries.map((item) => item[2]));
  return `<div class="defect-bars">${entries.map(([key, label, count]) => `<div class="defect-bar-row"><span class="defect-bar-name">${label}</span><span class="defect-bar-track"><span class="defect-bar-fill" style="display:block;width:${count ? Math.max(4, count / max * 100) : 0}%"></span></span><span class="defect-bar-count">${count}</span></div>`).join('')}</div>`;
}
function inspectionDetailPage() {
  const inspection = state.inspection;
  if (!inspection) return `${heading('INSPECTION', 'Inspection detail', 'Open an inspection from your saved ledger.')}${emptyState('Inspection not loaded', 'Return to the inspection ledger and choose a saved lot.', '<button class="btn btn-secondary btn-small" data-nav="inspections">Go to inspections</button>')}`;
  const s = inspection.summary || {};
  const selected = (inspection.onions || []).find((item) => Number(item.onion_id) === Number(state.selectedOnion)) || inspection.onions?.[0];
  const flags = (inspection.warnings || []).map((warning) => `<div class="notice">${icon('alert', 14)}<span>${esc(warning)}</span></div>`).join('');
  const uncalibrated = !inspection.calibration?.calibrated ? `<div class="notice notice-blue">${icon('alert', 14)}<span><strong>Estimated size only.</strong> No 50 mm calibration marker was detected. Pixel measurements are not presented as millimetres, and affected size decisions may need officer review.</span></div>` : '';
  const prov = inspection.provenance || {};
  const provenanceNotice = prov.source && prov.source !== 'operator_upload'
    ? `<div class="notice notice-blue">${icon('book', 14)}<span><strong>Image source:</strong> ${esc(prov.dataset || 'imported subset')} · ${esc(prov.source_path || prov.record_id || '')} · licence ${esc(prov.licence || '—')}${prov.doi ? ` · <a href="https://doi.org/${esc(prov.doi)}" target="_blank" rel="noopener">DOI ${esc(prov.doi)}</a>` : ''}. ${esc(prov.note || '')}</span></div>`
    : '';
  const titleActions = `<button class="btn btn-secondary" data-nav="inspections">${icon('list', 14)} Back to lots</button><button class="btn btn-primary" data-action="generate-report" data-id="${esc(inspection.inspection_id)}">${icon('report', 14)} Generate report</button>`;
  const mapLegend = [['#3d965d', 'Grade A'], ['#d48a3c', 'URS'], ['#c34f45', 'Reject'], ['#4c7fb7', 'Manual review']].map(([color, label]) => `<span class="legend-item"><i class="legend-dot" style="background:${color}"></i>${label}</span>`).join('');
  const auditRows = (inspection.audit_trail || []).map((item) => `<div class="rule-history-row"><span><strong>${esc(item.action.replaceAll('_', ' '))}</strong><div class="card-caption" style="margin-top:4px">${esc(item.actor)}${item.payload?.report_id ? ` · ${esc(item.payload.report_id)}` : ''}${item.payload?.decision ? ` · Onion #${item.payload.onion_id}: ${esc(item.payload.decision)}` : ''}</div></span><span>${humanDate(item.created_at, true)}</span></div>`).join('');
  const auditSection = `<section class="card content-block" style="margin-top:15px"><div class="card-heading"><div><h2>Inspection audit trail</h2><p>Recorded creation, officer changes and generated report events.</p></div><span class="badge badge-gray">${(inspection.audit_trail || []).length} event${(inspection.audit_trail || []).length === 1 ? '' : 's'}</span></div><div class="rule-history">${auditRows || '<p class="card-caption">No audit events recorded.</p>'}</div></section>`;
  return `${heading('SAVED INSPECTION / LOT RESULT', `${esc(inspection.lot_id)} quality assessment`, `${esc(inspection.procurement_centre)} · ${humanDate(inspection.captured_at, true)} · ${esc(inspection.operator)}`, titleActions)}
    <div class="result-idline"><span>${esc(inspection.inspection_id)}</span><span>·</span><span>${inspection.sample_size} onions inspected</span><span>·</span><span>${esc(inspection.rules?.rule_set_id || '—')} v${esc(inspection.rules?.version || '—')}</span><span>·</span><span>${esc(inspection.model?.version || '—')}</span>${badge('GRADE_A', 'Saved record')}</div>
    ${flags}${uncalibrated}${provenanceNotice}
    <section class="result-overview"><div class="card result-stat"><div class="result-stat-label">GRADE A</div><div class="result-stat-value">${fmt(inspection.percentages?.grade_a, 1)}%</div><div class="result-stat-sub">${s.grade_a || 0} bulbs · ${badge('GRADE_A', 'In range')}</div></div><div class="card result-stat urs"><div class="result-stat-label">URS</div><div class="result-stat-value">${fmt(inspection.percentages?.urs, 1)}%</div><div class="result-stat-sub">${s.urs || 0} bulbs · ${badge('URS', 'Outside A profile')}</div></div><div class="card result-stat reject"><div class="result-stat-label">REJECT</div><div class="result-stat-value">${fmt(inspection.percentages?.reject, 1)}%</div><div class="result-stat-sub">${s.reject || 0} bulbs · ${badge('REJECT', 'Visible concern')}</div></div><div class="card result-stat review"><div class="result-stat-label">MANUAL REVIEW</div><div class="result-stat-value">${fmt(inspection.percentages?.manual_review, 1)}%</div><div class="result-stat-sub">${s.manual_review || 0} bulbs · ${badge('MANUAL_REVIEW', 'Human decision')}</div></div></section>
    <section class="result-grid"><div class="card map-card"><div class="card-heading"><div><div class="card-title">Visual inspection map</div><p class="card-caption">Select a numbered bulb to review its evidence and decision reasons</p></div><div class="map-legend">${mapLegend}</div></div>${imageMap(inspection)}<div class="map-footer"><span>Boxes are candidate image regions · not certified grading boundaries</span><span>${inspection.image?.width || 0} × ${inspection.image?.height || 0} px</span></div></div>${selectedOnionCard(selected, inspection)}</section>
    <section class="analytics-grid"><div class="card analytics-card"><div class="card-heading"><div><div class="card-title">Lot grade distribution</div><p class="card-caption">Each inspected onion receives one mutually exclusive outcome</p></div></div>${donutMarkup(inspection)}</div><div class="card analytics-card"><div class="card-heading"><div><div class="card-title">Diameter distribution</div><p class="card-caption">Measured size with the photographed reference scale</p></div></div>${diameterHistogram(inspection)}</div><div class="card analytics-card"><div class="card-heading"><div><div class="card-title">Visible defect indicators</div><p class="card-caption">Heuristic surface evidence; not a probability of internal quality</p></div></div>${defectBars(inspection)}</div><div class="card analytics-card"><div class="card-heading"><div><div class="card-title">Diameter statistics</div><p class="card-caption">${esc(inspection.statistics?.size_basis || 'No calibrated size available')}</p></div></div><div class="metric-grid"><div class="metric-box"><span>MEAN</span><strong>${fmt(inspection.statistics?.mean_diameter_mm)} mm</strong></div><div class="metric-box"><span>MEDIAN</span><strong>${fmt(inspection.statistics?.median_diameter_mm)} mm</strong></div><div class="metric-box"><span>RANGE</span><strong>${fmt(inspection.statistics?.minimum_diameter_mm)}–${fmt(inspection.statistics?.maximum_diameter_mm)} mm</strong></div></div><p class="evidence-note">${inspection.statistics?.measured_count || 0} of ${inspection.sample_size} objects have calibrated millimetre measurements. Rule profile: ${esc(inspection.rules?.rule_set_id || '—')} · v${esc(inspection.rules?.version || '—')}.</p></div></section>${auditSection}`;
}

function inspectionsPage() {
  const items = state.inspections;
  const rows = items.length ? `<div class="table-scroll"><table><thead><tr><th>Lot / inspection</th><th>Centre</th><th>Captured</th><th>Sample</th><th>Grade A</th><th>URS</th><th>Reject</th><th>Review</th><th></th></tr></thead><tbody>${items.map((item) => `<tr class="clickable" data-action="open-inspection" data-id="${esc(item.inspection_id)}" data-search="${esc(`${item.lot_id} ${item.inspection_id} ${item.procurement_centre}`.toLowerCase())}"><td><span class="lot-id">${esc(item.lot_id)}</span><div class="card-caption" style="margin-top:4px">${esc(item.inspection_id)}</div></td><td>${esc(item.procurement_centre || '—')}</td><td>${humanDate(item.captured_at, true)}</td><td>${item.sample_size}</td><td class="grade-percent">${fmt(item.percentages?.grade_a, 1)}%</td><td>${fmt(item.percentages?.urs, 1)}%</td><td>${fmt(item.percentages?.reject, 1)}%</td><td>${item.summary?.manual_review || 0}</td><td>${icon('chevron', 14)}</td></tr>`).join('')}</tbody></table></div>` : emptyState('No inspection records yet', 'Create a lot inspection from a field photo or run the clearly-labelled synthetic software fixture.', '<button class="btn btn-primary btn-small" data-nav="new-inspection">'+icon('plus', 13)+' New inspection</button>');
  return `${heading('FIELD OPERATIONS / LEDGER', 'Inspection ledger', 'Every saved lot keeps its image evidence, per-onion decisions, rule snapshot, model version and audit events.', '<button class="btn btn-primary" data-nav="new-inspection">'+icon('plus', 14)+' New inspection</button>')}
    <div class="card table-card"><div class="card-heading"><div><div class="card-title">Saved lot inspections</div><p class="card-caption">${items.length} record${items.length === 1 ? '' : 's'} · stored locally in the SQLite demo database</p></div>${items.length ? `<div class="inspections-filter"><label class="search-box">${icon('search', 13)}<input id="inspection-search" placeholder="Search lots" /></label></div>` : ''}</div>${rows}</div>`;
}

function researchPage() {
  const sources = state.sources || [];
  const sourceCards = sources.map((source, index) => `<article class="card research-card"><div class="source-type">${esc(source.type)} · ${esc(source.organization)}</div><div class="research-number">${String(index + 1).padStart(2, '0')}</div><h3>${esc(source.title)}</h3><p>${esc(source.description)}</p><a href="${esc(source.url)}" target="_blank" rel="noopener noreferrer">Open source ${icon('external', 11)}</a></article>`).join('');
  return `${heading('RESEARCH / MODEL DEVELOPMENT', 'Research & model development', 'Sourced, transparent and intentionally honest about what one RGB camera can — and cannot — say about an onion.', '<button class="btn btn-secondary" data-nav="dataset">'+icon('dataset', 14)+' Dataset status</button>')}
    <div class="notice notice-blue">${icon('book', 14)}<span><strong>Evidence labels are explicit.</strong> Official standards, research papers, institutional references and engineering assumptions are not treated as interchangeable.</span></div>
    <section class="card content-block"><h2>Procurement quality is more than a colour label</h2><p>Buyers assess size, maturity, firmness, shape, curing, visible condition, acceptable tolerances and representative lot sampling under a specific written specification. This prototype records external evidence from an RGB photograph, then applies a separate configurable rule profile. It is not a certifying inspection and the illustrative 45–65 mm rule set is not presented as a universal government standard.</p><div class="approach-grid"><div class="approach-step"><b>01 · Research</b><span>Read the applicable specification, provenance and date; flag contextual references.</span></div><div class="approach-step"><b>02 · Dataset</b><span>Upload images and explicit labels; document field, variety, camera and lighting.</span></div><div class="approach-step"><b>03 · Annotation</b><span>Adjudicate bulb instances and visible defects; use polygons for segmentation.</span></div><div class="approach-step"><b>04 · Train & evaluate</b><span>Use held-out lots/sites, report per-class metrics and size error; never invent scores.</span></div></div></section>
    <section class="card content-block"><h2>Current computer-vision method</h2><p>The active <strong>HSV-CONTOUR-DEMO-0.1</strong> engine is an explainable classical-image-processing fallback, not a trained AI model. It segments warm-coloured regions, estimates each contour's diameter, checks green pixels above a bulb and dark local surface patches, and publishes heuristic evidence scores. A detected high-contrast 50 mm blue square provides a single-reference scale estimate. Without it, physical size remains unavailable and size-dependent outcomes can abstain to manual review.</p><div class="approach-grid"><div class="approach-step"><b>Image quality</b><span>Resolution, focus proxy, contrast and lighting warnings.</span></div><div class="approach-step"><b>Instance candidates</b><span>Per-bulb boxes and contours, numbered on the original photograph.</span></div><div class="approach-step"><b>Evidence scores</b><span>Heuristic visible cues; not calibrated probabilities or field accuracy.</span></div><div class="approach-step"><b>Decision rules</b><span>Independent versioned profile; low-confidence cases stay reviewable.</span></div></div></section>
    <section class="card content-block"><h2>Dataset and evaluation status</h2><p>There is no authentic labelled field dataset bundled and no model evaluation run. The included synthetic fixture is a repeatable software test image, explicitly excluded from training/evaluation counts. Precision, recall, F1, mAP, confusion matrices and diameter MAE remain unavailable until a real, adjudicated dataset is evaluated.</p></section>
    <section class="card content-block"><h2>Known limitations & future sensing</h2><p>RGB imagery cannot reliably inspect internal rot, firmness, maturity, moisture, mass, smell, pesticide residue or hidden damage. Illumination, cultivar, skin colour, overlap and camera processing affect visual cues. A one-marker scale is approximate and perspective sensitive. Future work should validate calibrated instance segmentation across centres and seasons; X-ray, hyperspectral, firmness and weight sensing require independent hardware and validation.</p></section>
    <div class="card content-block"><div class="card-heading"><div><h2>Source library</h2><p>Real source URLs are kept in <code>research/sources.json</code>. Jurisdiction and document date matter.</p></div><span class="badge badge-gray">${sources.length} references</span></div><div class="grid research-grid" style="margin-top:14px">${sourceCards || emptyState('Source file unavailable', 'Check research/sources.json and reload.')}</div></div>`;
}

function datasetPage() {
  const data = state.dataset || { class_counts: {}, splits: {} };
  const counts = data.class_counts || {};
  const items = data.items || [];
  const labels = ['healthy', 'damaged', 'rotten', 'sprouted', 'undersized'];
  const stats = `<div class="dataset-stat-grid"><div class="dataset-stat"><span>UPLOADED IMAGES</span><strong>${data.image_count ?? 0}</strong></div>${labels.map((label) => `<div class="dataset-stat"><span>${label.toUpperCase()} · IMAGE LEVEL</span><strong>${counts[label] || 0}</strong></div>`).join('')}</div><div class="approach-grid dataset-annotation-summary"><div class="approach-step"><b>${data.annotated_images || 0} complete images</b><span>Reviewed per-image polygon sets.</span></div><div class="approach-step"><b>${data.annotated_onions || 0} onion polygons</b><span>Latest saved annotation revisions.</span></div><div class="approach-step"><b>${data.splits?.train || 0} train · ${data.splits?.validation || 0} validation</b><span>${data.splits?.test || 0} held-out test · ${data.splits?.unassigned || 0} unassigned.</span></div><div class="approach-step"><b>Lot leakage guard</b><span>Export blocks a lot being split across subsets.</span></div></div>`;
  const splitName = (split) => split === 'unassigned' ? 'Unassigned' : split[0].toUpperCase() + split.slice(1);
  const imageRows = items.length ? `<div class="dataset-list dataset-image-list"><div class="dataset-list-row header"><span>Image</span><span>Image label</span><span>Split · lot</span><span>Annotation</span><span></span></div>${items.map((item) => `<div class="dataset-list-row"><span class="dataset-file"><strong>${esc(item.file_name)}</strong><small>${item.width || '—'} × ${item.height || '—'} px${item.source && item.source !== 'operator_upload' ? ' · imported field photo' : ''}</small></span><span><span class="label-badge">${esc(item.label)}</span></span><span>${esc(splitName(item.split))}<small>${esc(item.lot_id || 'No lot assigned')}</small></span><span>${badge(item.annotation_status === 'complete' ? 'GRADE_A' : item.annotation_status === 'draft' ? 'URS' : 'MANUAL_REVIEW', item.annotation_status === 'complete' ? `${item.annotation_count} polygons · v${item.annotation_version}` : item.annotation_status === 'draft' ? `${item.annotation_count} polygons · draft` : 'Needs annotation')}</span><span><button class="btn btn-secondary btn-small" data-action="open-annotator" data-id="${esc(item.id)}">${icon('dataset', 12)} ${item.annotation_status === 'unannotated' ? 'Annotate' : 'Edit'}</button></span></div>`).join('')}</div>` : emptyState('No operator images in the dataset', 'Upload real images to begin annotation. Synthetic demo fixtures are excluded from the dataset and export.');
  const archives = (data.archives || []).map((archive) => `<div class="dataset-list-row"><span class="dataset-file"><strong>${esc(archive.file_name)}</strong><small>${archive.image_count} images</small></span><span>${archive.contains_yolo_config ? 'YOLO config found' : 'Staged only'}</span><span>${humanDate(archive.created_at)}</span><span>${archive.download_url ? `<a class="btn btn-secondary btn-small" href="${esc(archive.download_url)}" download>Download</a>` : ''}</span></div>`).join('');
  const latestExport = state.lastDatasetExport ? `<div class="notice notice-green dataset-export-notice">${icon('check', 14)}<span><strong>${esc(state.lastDatasetExport.file_name)}</strong> · ${state.lastDatasetExport.image_count} images · train ${state.lastDatasetExport.split_counts.train}, validation ${state.lastDatasetExport.split_counts.validation}, test ${state.lastDatasetExport.split_counts.test}. <a href="${esc(state.lastDatasetExport.download_url)}" download>Download again</a></span></div>` : '';
  const actions = `<button class="btn btn-primary" data-action="export-dataset">${icon('download', 14)} Export annotated YOLO-seg</button><span class="badge badge-blue">${data.demo_fixture_images || 0} synthetic fixture · excluded</span>`;
  return `${heading('MODEL DEVELOPMENT / DATA', 'Dataset & annotation', 'Draw visible onion boundaries, record multiple surface labels, and save a versioned, lot-aware dataset.', actions)}
    ${latestExport}<div class="notice">${icon('alert', 14)}<span><strong>${(state.fieldPhotos?.status === 'ready') ? 'Imported photographs carry no polygons.' : 'No field dataset is bundled.'}</strong> ${state.fieldPhotos?.status === 'ready' ? 'The subset below is real photography without instance labels; annotate it before it can support any training claim.' : 'Upload grounded images before training.'} Labels are operator annotations, not verified ground truth. YOLO-seg expands multi-label polygons into repeated class rows; native labels are retained in the export manifest.</span></div>
    <section class="card content-block"><div class="card-heading"><div><h2>Dataset overview</h2><p>Counts below reflect uploaded operator records only; synthetic demo images and fabricated metrics are excluded.</p></div><span class="badge badge-gray">${data.evaluation_note || 'No evaluation run yet'}</span></div>${stats}<div class="approach-grid"><div class="approach-step"><b>Train · ${data.splits?.train || 0}</b><span>Images assigned to training.</span></div><div class="approach-step"><b>Validation · ${data.splits?.validation || 0}</b><span>Validation images recorded.</span></div><div class="approach-step"><b>Test · ${data.splits?.test || 0}</b><span>Held-out test images recorded.</span></div><div class="approach-step"><b>Unassigned · ${data.splits?.unassigned || 0}</b><span>Not assigned to a split.</span></div></div></section>
    <section class="dataset-upload-grid"><div class="card upload-tool"><h3>Upload image · begin curation</h3><p>Each file is a source photograph. Add polygons, labels, annotator, procurement centre, lot, and split in the annotation studio.</p><div class="field" style="margin-bottom:10px"><label for="dataset-label">INITIAL IMAGE LABEL</label><select id="dataset-label">${labels.map((label) => `<option value="${label}">${label}</option>`).join('')}</select></div><label class="file-pick">${icon('upload', 14)} Choose source image<input id="dataset-image-file" data-kind="dataset-image" type="file" accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp" /></label><div class="field-hint" style="margin-top:8px">JPG · PNG · WEBP · Up to 12 MB</div></div><div class="card upload-tool"><h3>Upload prepared YOLO-seg dataset ZIP</h3><p>Stage an existing dataset containing a valid <code>data.yaml</code>, image files, and per-instance segmentation polygons. Archive paths are validated.</p><label class="file-pick">${icon('upload', 14)} Choose dataset ZIP<input id="dataset-zip-file" data-kind="dataset-zip" type="file" accept=".zip,application/zip" /></label><div class="field-hint" style="margin-top:8px">Maximum 50 MB compressed · imported archives are staged separately from native annotations</div></div></section>
    ${fieldPhotoPanel('dataset')}
    <section class="card content-block" style="margin-top:14px"><div class="card-heading"><div><h2>Image curation queue</h2><p>Latest revisions, source split, and per-image status. Choose Annotate to open the polygon studio.</p></div><span class="badge badge-gray">${items.length} image${items.length === 1 ? '' : 's'}</span></div>${imageRows}</section>${archives ? `<section class="card content-block"><div class="card-heading"><div><h2>Dataset exports & staged archives</h2><p>Generated YOLO-seg exports can be downloaded again here.</p></div></div><div class="dataset-list">${archives}</div></section>` : ''}`;
}

const annotationClassLabels = [
  { id: 'healthy', label: 'Healthy appearance', color: '#45a66d' },
  { id: 'damaged', label: 'Visible damage', color: '#df9140' },
  { id: 'rotten', label: 'Rot / decay cue', color: '#cf5149' },
  { id: 'sprouted', label: 'Sprout visible', color: '#7e6acb' },
  { id: 'undersized', label: 'Undersized (contextual)', color: '#4d83bf' },
];

function annotationStudioPage() {
  const image = state.annotation;
  if (!image) return `${heading('DATASET / POLYGON ANNOTATION', 'Polygon annotation studio', 'Load an uploaded source image to start drawing.')}${emptyState('Loading image', 'Fetching source pixels and the latest saved annotation revision.')}`;
  const savedObjects = image.annotations?.objects || [];
  const classColor = (label) => annotationClassLabels.find((item) => item.id === label)?.color || '#4d83bf';
  const objectMarkup = savedObjects.map((object) => `<div class="annotation-object"><span class="annotation-object-number">${String(object.onion_id).padStart(2, '0')}</span><div class="annotation-object-meta"><strong>Onion #${String(object.onion_id).padStart(2, '0')}</strong><span>${object.labels.map((label) => `<i style="--label-color:${classColor(label)}"></i>${esc(label)}`).join('')}</span></div><button class="icon-button annotation-remove" data-action="remove-annotation" data-onion="${object.onion_id}" aria-label="Remove onion ${object.onion_id}">${icon('close', 13)}</button></div>`).join('');
  const draftPoints = state.annotationDraft.length;
  const split = image.split || 'unassigned';
  const labelOptions = annotationClassLabels.map((item) => `<label class="annotation-label-option"><input type="checkbox" data-ann-label="${item.id}" ${state.annotationLabels.includes(item.id) ? 'checked' : ''}/><span class="annotation-label-dot" style="--label-color:${item.color}"></span><span>${item.label}</span></label>`).join('');
  const titleActions = `<button class="btn btn-secondary" data-action="back-dataset">${icon('arrow', 13)} Dataset queue</button><span class="badge badge-${image.annotation_status === 'complete' ? 'green' : image.annotation_status === 'draft' ? 'orange' : 'gray'}">${image.annotation_status === 'complete' ? `Complete · v${image.annotation_version}` : image.annotation_status === 'draft' ? `Draft · v${image.annotation_version}` : 'Unannotated'}</span>`;
  const savedAt = image.annotations?.created_at ? `Last saved ${humanDate(image.annotations.created_at, true)} by ${esc(image.annotations.annotator)}` : 'No annotation revision saved yet.';
  const historyMarkup = image.annotation_history?.length ? `<div class="annotation-revisions"><strong>Revision history</strong>${image.annotation_history.map((revision) => `<div><span>v${revision.version} · ${esc(revision.status)} · ${revision.object_count} polygon${revision.object_count === 1 ? '' : 's'}</span><small>${esc(revision.annotator)} · ${humanDate(revision.created_at, true)}</small></div>`).join('')}</div>` : '';
  return `${heading('DATASET / POLYGON ANNOTATION', 'Annotate source image', `${esc(image.file_name)} · ${image.width} × ${image.height} px · ${esc(savedAt)}`, titleActions)}
    <div class="notice notice-blue annotation-instructions">${icon('alert', 14)}<span><strong>Click around one onion boundary.</strong> Add at least three points, then finish polygon. Select every visible class that applies. The image is human-reviewed training data, not a model prediction or official grade.</span></div>
    <div class="annotator-layout"><section class="card annotator-stage-card"><div class="annotator-stage-toolbar"><span>${icon('image', 14)} ${esc(image.file_name)}</span><span>${draftPoints ? `${draftPoints} point${draftPoints === 1 ? '' : 's'} · click to continue` : 'Click image to add polygon vertices'}</span></div><div class="annotator-viewport" id="annotation-viewport"><img id="annotation-image" src="${esc(image.image_url)}?v=${image.annotation_version}" alt="Source image for polygon annotation" draggable="false" /><canvas id="annotation-canvas" aria-label="Polygon drawing surface"></canvas></div><div class="annotator-stage-footer"><span>Coordinates are stored in source-image pixels.</span><span>${savedObjects.length} saved polygon${savedObjects.length === 1 ? '' : 's'}</span></div></section>
      <aside class="card annotator-controls"><section class="annotation-control-section"><div class="control-section-heading"><span class="control-step">1</span><div><strong>Visible onion classes</strong><small>Select all that apply to the next polygon.</small></div></div><div class="annotation-label-list">${labelOptions}</div></section>
        <section class="annotation-control-section"><div class="control-section-heading"><span class="control-step">2</span><div><strong>Draw an instance mask</strong><small>${draftPoints ? `${draftPoints} vertices added` : 'Click around an onion boundary'}</small></div></div><div class="annotation-button-row"><button class="btn btn-secondary btn-small" data-action="undo-annotation-point" ${draftPoints ? '' : 'disabled'}>Undo point</button><button class="btn btn-secondary btn-small" data-action="clear-annotation-polygon" ${draftPoints ? '' : 'disabled'}>Clear</button></div><button class="btn btn-primary annotation-finish-button" data-action="finish-annotation-polygon" ${draftPoints >= 3 && state.annotationLabels.length ? '' : 'disabled'}>${icon('check', 13)} Finish polygon · ${draftPoints} points</button></section>
        <section class="annotation-control-section"><div class="control-section-heading"><span class="control-step">3</span><div><strong>Onion instances</strong><small>${savedObjects.length} polygon${savedObjects.length === 1 ? '' : 's'} in this revision</small></div></div><div class="annotation-object-list">${objectMarkup || '<div class="annotation-empty">No polygons yet. Draw one bulb at a time.</div>'}</div></section>
        <section class="annotation-control-section annotation-metadata"><div class="control-section-heading"><span class="control-step">4</span><div><strong>Data provenance</strong><small>Keep a lot together across all dataset splits.</small></div></div><div class="field"><label for="annotation-annotator">ANNOTATOR · REQUIRED</label><input id="annotation-annotator" maxlength="120" required value="${esc(state.annotationForm?.annotator ?? image.annotations?.annotator ?? '')}" placeholder="Name or operator ID" /></div><div class="form-grid annotation-meta-grid"><div class="field"><label for="annotation-lot">LOT ID · REQUIRED TO COMPLETE</label><input id="annotation-lot" maxlength="64" value="${esc(state.annotationForm?.lot_id ?? image.lot_id ?? '')}" placeholder="e.g. LOT-2026-014" /></div><div class="field"><label for="annotation-centre">PROCUREMENT CENTRE · REQUIRED TO COMPLETE</label><input id="annotation-centre" maxlength="120" value="${esc(state.annotationForm?.procurement_centre ?? image.procurement_centre ?? '')}" placeholder="Centre / market" /></div></div><div class="field"><label for="annotation-split">DATASET SPLIT</label><select id="annotation-split">${[['unassigned', 'Unassigned'], ['train', 'Train'], ['validation', 'Validation'], ['test', 'Test']].map(([value, label]) => `<option value="${value}" ${(state.annotationForm?.split ?? split) === value ? 'selected' : ''}>${label}</option>`).join('')}</select><span class="field-hint">Choose one split for every image from the same lot.</span></div></section>
        <div class="annotation-save-actions"><button class="btn btn-secondary" data-action="save-annotation-draft">Save draft</button><button class="btn btn-primary" data-action="complete-annotation">Mark complete & save</button></div><p class="annotation-history-note">${savedAt} · every save adds an immutable revision.</p>${historyMarkup}
      </aside></div>`;
}

function drawAnnotationCanvas() {
  const imageEl = document.getElementById('annotation-image');
  const canvas = document.getElementById('annotation-canvas');
  if (!imageEl || !canvas || !imageEl.naturalWidth || !imageEl.naturalHeight) return;
  canvas.width = imageEl.naturalWidth;
  canvas.height = imageEl.naturalHeight;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const objects = state.annotation?.annotations?.objects || [];
  const colorFor = (labels) => annotationClassLabels.find((item) => labels?.includes(item.id))?.color || '#4d83bf';
  const drawPolygon = (points, color, close, alpha = 0.14) => {
    if (!points?.length) return;
    ctx.beginPath();
    ctx.moveTo(points[0][0], points[0][1]);
    points.slice(1).forEach((point) => ctx.lineTo(point[0], point[1]));
    if (close) ctx.closePath();
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(2, Math.min(canvas.width, canvas.height) / 350);
    ctx.setLineDash(close ? [] : [ctx.lineWidth * 2, ctx.lineWidth * 1.2]);
    if (close) { ctx.fillStyle = color; ctx.globalAlpha = alpha; ctx.fill(); ctx.globalAlpha = 1; }
    ctx.stroke();
    ctx.setLineDash([]);
    points.forEach(([x, y], index) => {
      ctx.beginPath(); ctx.arc(x, y, Math.max(3, ctx.lineWidth * 1.5), 0, Math.PI * 2);
      ctx.fillStyle = index === 0 ? '#fff' : color; ctx.fill(); ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.stroke();
    });
  };
  objects.forEach((object) => {
    const color = colorFor(object.labels);
    drawPolygon(object.polygon, color, true, 0.16);
    const point = object.polygon?.[0];
    if (point) {
      ctx.font = `bold ${Math.max(14, Math.min(canvas.width, canvas.height) / 32)}px sans-serif`;
      ctx.lineWidth = 4; ctx.strokeStyle = 'rgba(255,255,255,.95)'; ctx.strokeText(String(object.onion_id), point[0] + 5, point[1] - 6);
      ctx.fillStyle = color; ctx.fillText(String(object.onion_id), point[0] + 5, point[1] - 6);
    }
  });
  if (state.annotationDraft.length) drawPolygon(state.annotationDraft, '#f2a83d', state.annotationDraft.length >= 3, 0.12);
}

function setupAnnotationCanvas() {
  const imageEl = document.getElementById('annotation-image');
  const viewport = document.getElementById('annotation-viewport');
  const canvas = document.getElementById('annotation-canvas');
  if (!imageEl || !viewport || !canvas) return;
  imageEl.onload = drawAnnotationCanvas;
  imageEl.onerror = () => toast('Source image could not be displayed. Return to the dataset queue and retry.', 'error');
  const resize = () => {
    const bounds = imageEl.getBoundingClientRect();
    if (bounds.width && bounds.height) {
      viewport.style.width = `${bounds.width}px`;
      viewport.style.height = `${bounds.height}px`;
    }
    drawAnnotationCanvas();
  };
  if (imageEl.complete && imageEl.naturalWidth) resize();
  else imageEl.addEventListener('load', resize, { once: true });
  if (window.ResizeObserver) new ResizeObserver(resize).observe(imageEl);
}

function confirmLeaveAnnotation() {
  if (state.page !== 'dataset-annotate' || (!state.annotationDirty && !state.annotationDraft.length)) return true;
  const leave = window.confirm('You have unsaved annotation edits or polygon points. Leave and discard these local edits?');
  if (leave) {
    state.annotationDirty = false;
    state.annotationDraft = [];
  }
  return leave;
}

function openAnnotator(id) {
  state.annotationId = id;
  state.annotation = null;
  state.annotationDraft = [];
  state.annotationLabels = ['healthy'];
  state.annotationForm = null;
  state.annotationDirty = false;
  return loadPage('dataset-annotate');
}

async function savePolygonAnnotations(status) {
  const image = state.annotation;
  if (!image) return;
  const annotator = document.getElementById('annotation-annotator')?.value.trim() || '';
  state.annotationForm = {
    annotator,
    split: document.getElementById('annotation-split')?.value || 'unassigned',
    lot_id: document.getElementById('annotation-lot')?.value.trim() || '',
    procurement_centre: document.getElementById('annotation-centre')?.value.trim() || '',
  };
  if (!annotator) { toast('Enter an annotator name or operator ID before saving.', 'error'); return; }
  if (status === 'complete' && (!state.annotationForm.lot_id || !state.annotationForm.procurement_centre)) {
    toast('Complete annotations need a lot ID and procurement centre for split provenance.', 'error');
    return;
  }
  const payload = {
    annotator,
    status,
    split: state.annotationForm.split,
    lot_id: state.annotationForm.lot_id,
    procurement_centre: state.annotationForm.procurement_centre,
    objects: image.annotations?.objects || [],
  };
  try {
    const result = await api(`/api/dataset/images/${encodeURIComponent(image.id)}/annotations`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    state.annotationDraft = [];
    state.annotationDirty = false;
    state.annotation = await api(`/api/dataset/images/${encodeURIComponent(image.id)}`);
    toast(`Saved annotation revision v${result.version} · ${result.object_count} polygon${result.object_count === 1 ? '' : 's'}.`);
    render();
  } catch (error) { toast(error.message, 'error'); }
}

async function exportAnnotatedDataset() {
  try {
    const result = await api('/api/dataset/export', { method: 'POST' });
    state.lastDatasetExport = result;
    const anchor = document.createElement('a');
    anchor.href = result.download_url;
    anchor.download = result.file_name;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    toast(`${result.image_count} annotated images exported. Review the multi-label conversion notes before training.`);
    await loadPage('dataset');
  } catch (error) { toast(error.message, 'error'); }
}

function trainingPage() {
  const dataset = state.dataset || {};
  const models = state.models || {};
  const status = state.trainingStatus;
  const statusCard = status ? `<div class="notice ${status.status === 'failed' ? '' : 'notice-green'}">${icon(status.status === 'failed' ? 'alert' : 'clock', 14)}<span><strong>${esc(status.training_id || status.id || 'Training job')} · ${esc(status.status)}</strong><br/>${esc(status.message || '')}${status.log_tail ? `<pre class="training-command" style="max-height:140px">${esc(status.log_tail.slice(-1500))}</pre>` : ''}</span></div>` : `<div class="notice notice-blue">${icon('alert', 14)}<span><strong>Training is gated on real data.</strong> No field annotations are bundled. An image-level class label is not a segmentation polygon.</span></div>`;
  return `${heading('MODEL DEVELOPMENT / TRAINING', 'Train a replaceable vision model', 'The UI validates train/validation paths and class names before starting training; the optional trainer and dataset must both be available.', '<button class="btn btn-secondary" data-nav="dataset">'+icon('dataset', 14)+' Review dataset</button>')}
    ${statusCard}<div class="training-layout"><section class="card training-form"><div class="card-heading"><div><div class="card-title">Training configuration</div><p class="card-caption">Small YOLO instance-segmentation starting point · replaceable architecture</p></div><span class="badge badge-gray">No metrics claimed</span></div><div class="form-grid" style="margin-top:15px"><div class="field"><label for="train-epochs">EPOCHS</label><input id="train-epochs" type="number" min="1" max="300" value="50" /></div><div class="field"><label for="train-size">IMAGE SIZE</label><input id="train-size" type="number" min="128" max="1280" step="32" value="640" /></div><div class="field"><label for="train-batch">BATCH SIZE</label><input id="train-batch" type="number" min="1" max="128" value="16" /></div><div class="field"><label for="train-lr">LEARNING RATE</label><input id="train-lr" type="number" min="0.00001" max="0.1" step="0.0001" value="0.001" /></div></div><div class="training-preview"><div class="training-preview-line"><span>Backbone start</span><strong>yolo11n-seg.pt · optional</strong></div><div class="training-preview-line"><span>Dataset config</span><strong>${dataset.trainable_dataset_yaml ? 'Manifest staged · validate on start' : 'No data.yaml found'}</strong></div><div class="training-preview-line"><span>Current inference</span><strong>${esc(models.active_version || 'HSV-CONTOUR-DEMO-0.1')}</strong></div></div><button class="btn btn-primary" data-action="start-training">${icon('training', 14)} Start training</button><div class="field-hint" style="margin-top:9px">The optional <code>ultralytics</code> dependency may download its starting checkpoint. Training is a separate offline-capable script, not live phone inference.</div></section><aside class="card training-form"><div class="card-title">Training lifecycle</div><p class="card-caption">Configuration routes to <code>training/train.py</code> when prerequisites are met.</p><div class="pipeline"><div class="pipeline-row"><span class="pipeline-check">1</span><div><div class="pipeline-label">Collect and label</div><div class="pipeline-note">Upload real images; annotate polygons</div></div></div><div class="pipeline-row"><span class="pipeline-check">2</span><div><div class="pipeline-label">Prepare manifest</div><div class="pipeline-note">Review manifest, paths and lot splits</div></div></div><div class="pipeline-row"><span class="pipeline-check">3</span><div><div class="pipeline-label">Train & version</div><div class="pipeline-note">Run optional small segmentation model</div></div></div><div class="pipeline-row"><span class="pipeline-check">4</span><div><div class="pipeline-label">Evaluate & export</div><div class="pipeline-note">Use held-out lots, ONNX/TFLite later</div></div></div></div><pre class="training-command">python training/prepare_dataset.py --data /path/to/data.yaml
python training/train.py --data /path/to/data.yaml \
  --epochs 50 --image-size 640 --batch-size 16
python training/evaluate.py --weights best.pt --data /path/to/data.yaml</pre></aside></div>`;
}

function modelsPage() {
  const data = state.models || {};
  const items = data.items || [];
  const evaluation = data.evaluation || {};
  const metrics = evaluation.metrics;
  const confusion = evaluation.confusion_matrix;
  const confusionTable = confusion?.matrix?.length ? `<div class="matrix"><table><thead><tr><th>Actual ↓ / Predicted →</th>${confusion.labels.map((label) => `<th>${esc(label)}</th>`).join('')}</tr></thead><tbody>${confusion.matrix.map((row, index) => `<tr><th>${esc(confusion.labels[index] || `Class ${index}`)}</th>${row.map((value) => `<td>${esc(value)}</td>`).join('')}</tr>`).join('')}</tbody></table><p class="card-caption">Counts from the recorded offline evaluation run; background row/column may be present.</p></div>` : `<div class="matrix"><table><thead><tr><th>Actual ↓ / Predicted →</th><th>Healthy</th><th>Damage</th><th>Rot</th><th>Sprout</th></tr></thead><tbody><tr><th>Healthy</th><td>—</td><td>—</td><td>—</td><td>—</td></tr><tr><th>Damage</th><td>—</td><td>—</td><td>—</td><td>—</td></tr><tr><th>Rot</th><td>—</td><td>—</td><td>—</td><td>—</td></tr><tr><th>Sprout</th><td>—</td><td>—</td><td>—</td><td>—</td></tr></tbody></table><p class="card-caption">No confusion matrix has been generated; cells are intentionally not populated with placeholder results.</p></div>`;
  const modelCards = items.length ? items.map((model) => `<div class="card content-block"><div class="card-heading"><div><h2>${esc(model.version)}</h2><p>${esc(model.engine)}</p></div>${model.trained_model ? '<span class="badge badge-green">Trained</span>' : '<span class="badge badge-orange">Demo engine</span>'}</div><div class="metric-grid"><div class="metric-box"><span>MODEL TYPE</span><strong>${model.trained_model ? 'Trained model' : 'Classical CV'}</strong></div><div class="metric-box"><span>INSPECTION USES</span><strong>${(data.usage || {})[model.version] || 0}</strong></div><div class="metric-box"><span>EVALUATION</span><strong>${esc(model.evaluation_status || 'Not run')}</strong></div></div></div>`).join('') : emptyState('No model registry entries', 'Model versions appear here when available.');
  return `${heading('MODEL DEVELOPMENT / DEPLOYMENT', 'Models & evaluation', 'Separate model evidence from policy decisions. Metrics appear only after a real evaluation run.', '<button class="btn btn-secondary" data-nav="training">'+icon('training', 14)+' Training setup</button>')}
    <div class="notice notice-blue">${icon('model', 14)}<span><strong>Active engine: ${esc(data.active_version || 'HSV-CONTOUR-DEMO-0.1')}.</strong> It uses classical image processing, not trained weights. Evidence scores are heuristic, and no accuracy or field performance is claimed.</span></div>
    ${modelCards}<section class="card content-block"><div class="card-heading"><div><h2>Evaluation report</h2><p>Confusion matrix, precision, recall, F1, mAP and IoU require a genuine held-out labelled set.</p></div><span class="badge badge-gray">${esc(evaluation.status || 'No evaluation run yet')}</span></div>${evaluation.weights ? `<div class="notice notice-blue">${icon('model', 13)}<span>Latest evaluation checkpoint: <strong>${esc(evaluation.weights)}</strong><br/>Dataset: ${esc(evaluation.dataset || '—')} · Evaluated ${humanDate(evaluation.evaluated_at, true)}</span></div>` : ''}${metrics ? `<div class="metric-grid">${Object.entries(metrics).map(([key, value]) => `<div class="metric-box"><span>${esc(key.replaceAll('_', ' ').toUpperCase())}</span><strong>${value == null ? '—' : esc(value)}</strong></div>`).join('')}</div>` : `<div class="empty-state" style="padding:20px"><div class="empty-icon">${icon('gauge', 20)}</div><p class="empty-title">No evaluation run yet</p><p class="empty-copy">Evaluation values and confusion matrices will be shown only when generated from an actual held-out dataset.</p></div>`}${confusionTable}</section>`;
}

function toggleField(id, title, note, checked) {
  return `<div class="toggle-row"><div class="toggle-copy"><strong>${title}</strong><span>${note}</span></div><input class="toggle" id="${id}" type="checkbox" ${checked ? 'checked' : ''} aria-label="${title}" /></div>`;
}
function rulesPage() {
  const active = state.rules?.active || {};
  const history = state.rules?.history || [];
  return `${heading('GOVERNANCE / RULE ENGINE', 'Procurement rules', 'Rules decide the grade independently of image inference. Each saved inspection freezes the exact rule-set ID and version used.', '<span class="badge badge-orange">Buyer profile · editable</span>')}
    <div class="notice">${icon('alert', 14)}<span><strong>Illustrative default only.</strong> The 45–65 mm interval is an engineering demo assumption, not an approved or universal NAFED/NCCF/AGMARK specification. Confirm the buyer’s current written tender rules before use.</span></div>
    <div class="rule-layout"><section class="card rule-form"><div class="card-heading"><div><div class="card-title">Active rule profile</div><p class="card-caption">Changes create a new policy version; saved inspections are not rewritten.</p></div>${active.version ? `<span class="badge badge-green">v${esc(active.version)}</span>` : ''}</div><div class="form-grid" style="margin-top:15px"><div class="field"><label for="rule-id">RULE SET ID</label><input id="rule-id" value="${esc(active.rule_set_id || 'DEMO_45_65')}" maxlength="64" /></div><div class="field"><label for="rule-name">PROFILE NAME</label><input id="rule-name" value="${esc(active.name || 'Illustrative buyer profile')}" maxlength="120" /></div><div class="field"><label for="rule-min">MINIMUM DIAMETER · MM</label><input id="rule-min" type="number" min="1" max="499" step="0.1" value="${active.diameter_min_mm ?? 45}" /></div><div class="field"><label for="rule-max">MAXIMUM DIAMETER · MM</label><input id="rule-max" type="number" min="2" max="500" step="0.1" value="${active.diameter_max_mm ?? 65}" /></div><div class="field"><label for="threshold-review">MANUAL REVIEW THRESHOLD</label><input id="threshold-review" type="number" min="0.5" max="0.99" step="0.01" value="${active.manual_review_threshold ?? 0.6}" /></div><div class="field"><label for="threshold-high">HIGH EVIDENCE THRESHOLD</label><input id="threshold-high" type="number" min="0.51" max="1" step="0.01" value="${active.high_confidence_threshold ?? 0.9}" /></div></div><div style="margin-top:13px">${toggleField('rule-sprout', 'Allow visible sprouting', 'If disabled, a detected sprout cue is a reject condition.', !!active.sprouting_allowed)}${toggleField('rule-rot', 'Allow visible rot', 'If disabled, a detected dark rot cue is a reject condition.', !!active.rotten_allowed)}${toggleField('rule-damage', 'Allow mechanical damage', 'If disabled, the damage cue is treated as a reject condition.', !!active.mechanical_damage_allowed)}${toggleField('rule-calibration', 'Require calibrated diameter', 'Uncalibrated or missing size evidence abstains to manual review.', active.require_calibration !== false)}</div><div class="field" style="margin-top:12px"><label for="rule-notes">POLICY NOTE / SOURCE</label><textarea id="rule-notes" maxlength="1000">${esc(active.notes || '')}</textarea></div><div style="display:flex;justify-content:flex-end;margin-top:13px"><button class="btn btn-primary" data-action="save-rules">${icon('check', 14)} Save new rule version</button></div></section>
      <aside><div class="card rule-card"><div class="card-title">Current decision logic</div><p class="card-caption">Policy is applied after visual evidence extraction.</p><div class="rule-fact"><span>Diameter in configured range</span><strong>Grade A*</strong></div><div class="rule-fact"><span>Out-of-range diameter</span><strong>URS</strong></div><div class="rule-fact"><span>Disallowed visible cue</span><strong>Reject</strong></div><div class="rule-fact"><span>Low evidence / missing scale</span><strong>Manual review</strong></div><div class="context-note">* Subject to other disallowed defects and the selected profile. These demo outcomes do not replace contract-specific lot tolerances or officer approval.</div></div><div class="card rule-card" style="margin-top:13px"><div class="card-title">Version history</div><p class="card-caption">New inspections use the active profile only.</p><div class="rule-history">${history.map((item) => `<div class="rule-history-row"><span>${esc(item.rule_set_id)} · v${esc(item.version)}</span><span>${item.active ? 'Active' : humanDate(item.updated_at)}</span></div>`).join('') || '<p class="card-caption">No saved versions yet.</p>'}</div></div></aside></div>`;
}

function reportsPage() {
  const reports = state.reports || [];
  return `${heading('RECORDS / REPORT INTEGRITY', 'Reports & verification', 'Download signed-off inspection PDFs and verify the SHA-256 hash of each canonical report-data snapshot.', '<button class="btn btn-secondary" data-nav="inspections">'+icon('list', 14)+' Open inspections</button>')}
    <div class="notice notice-blue">${icon('shield', 14)}<span>QR verification checks the stored report-data hash. This is a tamper-evident record inside this application — not blockchain, an independent trusted timestamp, or a digitally signed legal certificate.</span></div>
    <section class="card table-card"><div class="card-heading"><div><div class="card-title">Generated quality reports</div><p class="card-caption">${reports.length} report${reports.length === 1 ? '' : 's'} · report hashes are recalculated during verification</p></div></div>${reports.length ? reports.map((report) => `<div class="report-row"><span><strong class="lot-id">${esc(report.report_id)}</strong><div class="card-caption" style="margin-top:4px">${esc(report.inspection_id)}</div></span><span>${humanDate(report.generated_at, true)}</span><span class="report-hash">${esc(report.report_hash)}</span><button class="btn btn-secondary btn-small" data-action="verify-report" data-id="${esc(report.report_id)}">${icon('shield', 12)} Verify</button></div>`).join('') : emptyState('No quality reports yet', 'Generate a PDF from an inspection to create a hash, QR verification link and audit event.', '<button class="btn btn-secondary btn-small" data-nav="inspections">Open saved inspections</button>')}</section>`;
}

function settingsPage() {
  return `${heading('GOVERNANCE / FIELD GUIDANCE', 'Limitations & setup', 'Designed for a credible visual-assessment demo. Review these conditions before interpreting any result.', '<a class="btn btn-secondary" href="/assets/calibration-sheet.svg" target="_blank" rel="noopener">'+icon('print', 14)+' Calibration sheet</a>')}
    <div class="notice notice-blue">${icon('alert', 14)}<span><strong>External visual quality assessment.</strong> AI-assisted evidence supports an officer’s judgement; this MVP is not a food-safety test, statutory certificate or autonomous payment decision.</span></div>
    <section class="card content-block"><h2>Known limitations</h2><p>RGB smartphone imagery cannot reliably identify internal defects or establish firmness, maturity, moisture, weight, smell or chemical residues. The current fallback uses classical colour/contour rules, not a trained detector. Heuristic evidence scores are not calibrated probabilities.</p><div class="limitation-list"><div class="limitation"><i></i><span>Lighting, focus, camera white balance, cultivar colour, soil and compression can affect colour segmentation.</span></div><div class="limitation"><i></i><span>Overlapping bulbs can merge; spread onions apart and verify the detected count.</span></div><div class="limitation"><i></i><span>Physical diameter is shown only with a detected 50 mm reference marker; one marker does not correct perspective.</span></div><div class="limitation"><i></i><span>Lot percentages describe the photographed sample. They are not a statistically representative lot estimate without a sampling protocol.</span></div><div class="limitation"><i></i><span>Visible dark spots or green pixels are cues for officer review, not confirmed disease or sprouting diagnoses.</span></div><div class="limitation"><i></i><span>Check the buyer’s current written rule profile; the bundled 45–65 mm interval is illustrative, not a universal standard.</span></div></div></section>
    <section class="grid dashboard-lower"><div class="card content-block"><h2>Physical calibration reference</h2><p>Print the calibration sheet at 100% / actual size. Measure the blue square with a ruler before use. Position it flat in the same plane as bulbs; keep the phone nearly perpendicular. The image pipeline estimates scale from the observed square side and labels this an approximation. If the marker is absent, pixel measurements remain pixels and size rules abstain.</p><div style="margin-top:13px"><a class="btn btn-secondary btn-small" href="/assets/calibration-sheet.svg" target="_blank" rel="noopener">${icon('external', 12)} Open printable 50 mm square</a></div></div><div class="card content-block"><h2>Runtime data & offline behaviour</h2><p>Uploads, reports and inspection records are stored in server-side SQLite/files. Local and container deployments can use persistent storage; serverless hosts such as Vercel use temporary per-instance storage, so data may disappear after an instance restart. Use managed database/object storage for durable records. A true offline on-device ONNX/TFLite model, encrypted sync queue, user authentication and production retention controls are future work.</p><p style="margin-top:9px">Environment configuration: copy <code>.env.example</code>. Runtime secrets are not required for this local MVP.</p></div></section>`;
}

function verificationPage() {
  const data = state.verification;
  if (!data) return `${heading('REPORT INTEGRITY', 'Report verification', 'The QR code or report link points to this local verification record.')}${emptyState('Checking report record', 'Verifying the report-data hash against the stored manifest.')}`;
  const valid = !!data.verified;
  return `<div class="verify-shell"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px"><div class="eyebrow" style="margin:0">REPORT INTEGRITY / ${esc(data.report_id)}</div><button class="btn btn-secondary btn-small" data-nav="reports">${icon('list', 12)} All reports</button></div><div class="verify-banner"><div class="verification-layout"><div><div class="verify-icon ${valid ? '' : 'invalid'}">${icon(valid ? 'check' : 'alert', 20)}</div><h2>${valid ? 'Report verified' : 'Verification failed'}</h2><p>${valid ? 'The stored canonical report-data snapshot matches its recorded SHA-256 hash.' : 'The report hash does not match the stored report data. Do not rely on this record until reviewed.'}</p></div><img class="verify-qr" src="/api/reports/${encodeURIComponent(data.report_id)}/qr" alt="QR code for report verification" /></div></div><div class="card verify-details"><div class="verify-field"><div class="verify-label">INSPECTION ID</div><div class="verify-value">${esc(data.inspection_id)}</div></div><div class="verify-field"><div class="verify-label">REPORT-DATA SHA-256</div><div class="verify-value" style="font-family:ui-monospace,monospace">${esc(data.report_hash)}</div></div><div class="verify-field"><div class="verify-label">RECALCULATED HASH</div><div class="verify-value" style="font-family:ui-monospace,monospace">${esc(data.computed_hash || 'Unavailable')}</div></div><div class="verify-field"><div class="verify-label">SOURCE IMAGE SHA-256 · ${data.image_verified ? 'MATCH' : 'MISMATCH / UNAVAILABLE'}</div><div class="verify-value" style="font-family:ui-monospace,monospace">${esc(data.image_evidence_sha256 || 'Unavailable')}</div></div><div class="verify-field"><div class="verify-label">RULE SET / VERSION</div><div class="verify-value">${esc(data.rule_set_id || '—')} · ${esc(data.rule_version || '—')}</div></div><div class="verify-field"><div class="verify-label">MODEL VERSION</div><div class="verify-value">${esc(data.model_version || '—')}</div></div><div class="verify-field"><div class="verify-label">GENERATED</div><div class="verify-value">${humanDate(data.generated_at, true)}</div></div><div class="verify-field"><div class="verify-label">INTEGRITY SCOPE</div><div class="verify-value">SHA-256 over canonical JSON report data; not a PDF-byte signature, blockchain proof, or independent trusted timestamp.</div></div><div style="margin-top:14px"><a class="btn btn-primary" href="/api/reports/${encodeURIComponent(data.report_id)}/pdf" download>${icon('download', 14)} Download PDF</a></div></div></div>`;
}

function renderReportModal() {
  const report = state.report;
  return `<div class="modal-backdrop" data-action="modal-backdrop"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="report-modal-title"><div class="modal-head"><div><h2 id="report-modal-title">Quality report generated</h2><p class="card-caption">The report and audit event are saved locally.</p></div><button class="modal-close" data-action="close-modal" aria-label="Close">×</button></div><div class="modal-report-body"><div><div class="modal-meta"><span>Report ID · <strong>${esc(report.report_id)}</strong></span><span>Generated · <strong>${humanDate(report.generated_at, true)}</strong></span><span>Verification URL · <strong>same-origin local record</strong></span></div><div class="modal-hash">SHA-256 · ${esc(report.report_hash)}</div></div><img class="verify-qr" src="${esc(report.qr_url)}" alt="Scan to verify this report" /></div><div class="modal-actions"><a class="btn btn-primary" href="${esc(report.pdf_url)}" download>${icon('download', 14)} Download PDF</a><button class="btn btn-secondary" data-action="open-verification" data-id="${esc(report.report_id)}">${icon('shield', 14)} Verify hash</button><button class="btn btn-ghost" data-action="close-modal">Close</button></div></section></div>`;
}

function render() {
  let page;
  switch (state.page) {
    case 'dashboard': page = dashboardPage(); break;
    case 'new-inspection': page = newInspectionPage(); break;
    case 'inspections': page = inspectionsPage(); break;
    case 'inspection-detail': page = inspectionDetailPage(); break;
    case 'research': page = researchPage(); break;
    case 'dataset': page = datasetPage(); break;
    case 'dataset-annotate': page = annotationStudioPage(); break;
    case 'training': page = trainingPage(); break;
    case 'models': page = modelsPage(); break;
    case 'rules': page = rulesPage(); break;
    case 'reports': page = reportsPage(); break;
    case 'settings': page = settingsPage(); break;
    case 'verify': page = verificationPage(); break;
    default: page = dashboardPage();
  }
  root.innerHTML = shell(page);
  if (state.page === 'new-inspection' && state.cameraStream) {
    const video = document.getElementById('camera-video');
    if (video) { video.srcObject = state.cameraStream; video.play().catch(() => {}); }
  }
  if (state.page === 'dataset-annotate') setupAnnotationCanvas();
}

async function loadPage(page) {
  state.page = page;
  state.error = null;
  if (page !== 'new-inspection') stopCamera();
  render();
  try {
    if (page === 'dashboard') state.dashboard = await api('/api/dashboard');
    if (page === 'inspections') state.inspections = (await api('/api/inspections')).items || [];
    if (page === 'inspection-detail' && state.inspection?.inspection_id) state.inspection = await api(`/api/inspection/${encodeURIComponent(state.inspection.inspection_id)}`);
    if (page === 'research') state.sources = (await api('/api/research/sources')).items || [];
    if (page === 'dataset' || page === 'training') state.dataset = await api('/api/dataset');
    if (page === 'new-inspection' || page === 'dataset') state.fieldPhotos = await api('/api/demo/field-photos');
    if (page === 'dataset-annotate' && state.annotationId) {
      state.annotation = await api(`/api/dataset/images/${encodeURIComponent(state.annotationId)}`);
      if (!state.annotationForm) state.annotationForm = { annotator: state.annotation.annotations?.annotator || '', lot_id: state.annotation.lot_id || '', procurement_centre: state.annotation.procurement_centre || '', split: state.annotation.split || 'unassigned' };
    }
    if (page === 'training') state.models = await api('/api/models');
    if (page === 'training' && state.trainingStatus?.training_id) state.trainingStatus = await api(`/api/training/${encodeURIComponent(state.trainingStatus.training_id)}`);
    if (page === 'models') state.models = await api('/api/models');
    if (page === 'rules') state.rules = await api('/api/rules');
    if (page === 'reports') state.reports = (await api('/api/reports')).items || [];
    if (page === 'verify' && state.verifyId) state.verification = await api(`/api/reports/${encodeURIComponent(state.verifyId)}/verify`);
  } catch (error) {
    state.error = error.message;
  }
  render();
  if (state.error) toast(state.error, 'error');
  if (page === 'training' && state.trainingStatus?.status === 'running') pollTraining(state.trainingStatus.training_id);
}

function setBusy(value) {
  state.busy = value;
  render();
}
function currentMeta() {
  return {
    lot_id: document.getElementById('lot-id')?.value || `LOT-${todayKey()}`,
    procurement_centre: document.getElementById('centre')?.value || 'Unspecified procurement centre',
    operator: document.getElementById('operator')?.value || 'Field officer',
  };
}
async function scanPhoto(file, mode = 'photo') {
  if (!file) return;
  const meta = currentMeta();
  const form = new FormData();
  form.append('file', file, file.name || 'capture.png');
  form.append('lot_id', meta.lot_id);
  form.append('procurement_centre', meta.procurement_centre);
  form.append('operator', meta.operator);
  setBusy(true);
  try {
    const result = await api(mode === 'camera' ? '/api/scan/camera' : '/api/scan/image', { method: 'POST', body: form });
    state.inspection = result;
    state.selectedOnion = result.onions?.find((onion) => onion.grade === 'REJECT')?.onion_id || result.onions?.find((onion) => onion.grade === 'MANUAL_REVIEW')?.onion_id || result.onions?.[0]?.onion_id || null;
    state.busy = false;
    await loadPage('inspection-detail');
    toast(`${result.sample_size} onion regions assessed · ${result.rules?.rule_set_id} v${result.rules?.version}`);
  } catch (error) {
    state.busy = false;
    render();
    toast(error.message, 'error');
  }
}
async function loadDemo() {
  try {
    const response = await fetch('/demo/onion-lot.png');
    if (!response.ok) throw new Error('Synthetic demo image is not available.');
    const blob = await response.blob();
    const file = new File([blob], 'pyaazscan-synthetic-demo.png', { type: 'image/png' });
    await scanPhoto(file, 'photo');
  } catch (error) { toast(error.message, 'error'); }
}
async function fetchFieldPhoto(id, variant = 'full') {
  const response = await fetch(`/api/demo/field-photos/${encodeURIComponent(id)}/image${variant === 'thumb' ? '?variant=thumb' : ''}`);
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || 'That field photograph is not available.');
  const blob = await response.blob();
  return new File([blob], `${id}.jpg`, { type: blob.type || 'image/jpeg' });
}
async function scanFieldPhoto(id) {
  try {
    await scanPhoto(await fetchFieldPhoto(id), 'photo');
  } catch (error) { toast(error.message, 'error'); }
}
async function queueFieldPhotos(body) {
  try {
    const result = await api('/api/demo/field-photos/to-dataset', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const failed = (result.failed || []).length ? ` · ${result.failed.length} skipped` : '';
    toast(`Queued ${result.imported} photograph(s)${failed}. Draw polygons before trusting any label.`);
    await loadPage('dataset');
  } catch (error) { toast(error.message, 'error'); }
}
async function openCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    toast('Camera access is not available here. Choose a photo or use the synthetic demo image.', 'error');
    return;
  }
  try {
    state.scanMode = 'camera';
    state.cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false });
    await loadPage('new-inspection');
  } catch (error) {
    stopCamera();
    toast(`Camera could not open: ${error.message || 'permission denied'}. Use Scan from photo instead.`, 'error');
  }
}
async function captureCamera() {
  const video = document.getElementById('camera-video');
  if (!video || !video.videoWidth) { toast('Camera is still starting. Please wait a moment.', 'error'); return; }
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.92));
  if (!blob) { toast('Could not capture a still frame. Try again.', 'error'); return; }
  const file = new File([blob], `camera-${Date.now()}.jpg`, { type: 'image/jpeg' });
  stopCamera();
  await scanPhoto(file, 'camera');
}
async function openInspection(id) {
  try {
    state.inspection = await api(`/api/inspection/${encodeURIComponent(id)}`);
    state.selectedOnion = state.inspection.onions?.find((onion) => onion.grade === 'REJECT')?.onion_id || state.inspection.onions?.[0]?.onion_id || null;
    await loadPage('inspection-detail');
  } catch (error) { toast(error.message, 'error'); }
}
async function generateReport(id) {
  try {
    const report = await api('/api/reports/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ inspection_id: id }) });
    if (state.inspection?.inspection_id === id) state.inspection = await api(`/api/inspection/${encodeURIComponent(id)}`);
    state.report = report;
    render();
    toast('PDF report saved with a report-data hash.');
  } catch (error) { toast(error.message, 'error'); }
}
async function submitManualDecision(button) {
  const decision = button.dataset.grade;
  const onionId = Number(button.dataset.onion);
  const note = window.prompt(`Record an optional note for Onion #${String(onionId).padStart(2, '0')}:`, '') ?? null;
  if (note === null) return;
  try {
    const result = await api('/api/manual-review', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ inspection_id: state.inspection.inspection_id, onion_id: onionId, decision, reviewer: 'Kavita Officer', note }) });
    state.inspection = await api(`/api/inspection/${encodeURIComponent(state.inspection.inspection_id)}`);
    state.selectedOnion = onionId;
    render();
    toast(`Officer decision saved: ${friendlyGrade(decision)}.`);
  } catch (error) { toast(error.message, 'error'); }
}
async function saveRules() {
  const payload = {
    rule_set_id: document.getElementById('rule-id')?.value,
    name: document.getElementById('rule-name')?.value,
    version: state.rules?.active?.version || '1.0.0',
    diameter_min_mm: Number(document.getElementById('rule-min')?.value),
    diameter_max_mm: Number(document.getElementById('rule-max')?.value),
    manual_review_threshold: Number(document.getElementById('threshold-review')?.value),
    high_confidence_threshold: Number(document.getElementById('threshold-high')?.value),
    sprouting_allowed: !!document.getElementById('rule-sprout')?.checked,
    rotten_allowed: !!document.getElementById('rule-rot')?.checked,
    mechanical_damage_allowed: !!document.getElementById('rule-damage')?.checked,
    require_calibration: !!document.getElementById('rule-calibration')?.checked,
    notes: document.getElementById('rule-notes')?.value || '',
  };
  try {
    const result = await api('/api/rules', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    toast(`Saved rule profile v${result.active.version}. Existing inspections are unchanged.`);
    await loadPage('rules');
  } catch (error) { toast(error.message, 'error'); }
}
async function uploadDatasetImage(file) {
  const label = document.getElementById('dataset-label')?.value || 'healthy';
  const form = new FormData(); form.append('file', file, file.name); form.append('label', label);
  try {
    const result = await api('/api/dataset/images', { method: 'POST', body: form });
    toast(`${result.file_name} added with label “${result.label}”.`);
    await loadPage('dataset');
  } catch (error) { toast(error.message, 'error'); }
}
async function uploadDatasetZip(file) {
  const form = new FormData(); form.append('file', file, file.name);
  try {
    const result = await api('/api/dataset/upload', { method: 'POST', body: form });
    toast(`Staged ${result.file_name} · ${result.image_count} image files. Review the labels before training.`);
    await loadPage('dataset');
  } catch (error) { toast(error.message, 'error'); }
}
async function startTraining() {
  const payload = {
    epochs: Number(document.getElementById('train-epochs')?.value || 50),
    image_size: Number(document.getElementById('train-size')?.value || 640),
    batch_size: Number(document.getElementById('train-batch')?.value || 16),
    learning_rate: Number(document.getElementById('train-lr')?.value || 0.001),
  };
  try {
    const result = await api('/api/training/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    state.trainingStatus = { ...result, training_id: result.training_id };
    render();
    toast('Training subprocess started.');
    pollTraining(result.training_id);
  } catch (error) { toast(error.message, 'error'); }
}
async function pollTraining(trainingId) {
  if (state.trainingTimer) clearTimeout(state.trainingTimer);
  if (state.page !== 'training' || !trainingId) return;
  try {
    const status = await api(`/api/training/${encodeURIComponent(trainingId)}`);
    state.trainingStatus = status;
    if (state.page === 'training') render();
    if (status.status === 'running' && state.page === 'training') {
      state.trainingTimer = setTimeout(() => pollTraining(trainingId), 2500);
    }
  } catch (error) {
    state.trainingStatus = { training_id: trainingId, status: 'unavailable', message: error.message };
    if (state.page === 'training') render();
  }
}
async function openVerification(id) {
  state.report = null;
  state.verifyId = id;
  state.verification = null;
  await loadPage('verify');
}

root.addEventListener('click', async (event) => {
  if (event.target instanceof HTMLCanvasElement && event.target.id === 'annotation-canvas' && state.page === 'dataset-annotate') {
    const canvas = event.target;
    const bounds = canvas.getBoundingClientRect();
    if (bounds.width && bounds.height) {
      state.annotationDraft.push([(event.clientX - bounds.left) / bounds.width * canvas.width, (event.clientY - bounds.top) / bounds.height * canvas.height]);
      render();
    }
    return;
  }
  const nav = event.target.closest('[data-nav]');
  if (nav) {
    event.preventDefault();
    const target = nav.dataset.nav;
    if (target !== 'dataset-annotate' && !confirmLeaveAnnotation()) return;
    state.mobileMenuOpen = false;
    if (target === 'new-inspection') state.inspection = null;
    await loadPage(target);
    return;
  }
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const action = button.dataset.action;
  if (action === 'open-mobile-menu') { state.mobileMenuOpen = true; render(); return; }
  if (action === 'close-mobile-menu') { state.mobileMenuOpen = false; render(); return; }
  if (action === 'load-demo') { await loadDemo(); return; }
  if (action === 'scan-field-photo') { await scanFieldPhoto(button.dataset.id); return; }
  if (action === 'queue-field-photo') { await queueFieldPhotos({ ids: [button.dataset.id] }); return; }
  if (action === 'queue-all-field-photos') { await queueFieldPhotos({ limit: Number(button.dataset.limit) || 24 }); return; }
  if (action === 'start-camera' || action === 'open-camera') { await openCamera(); return; }
  if (action === 'capture-camera') { await captureCamera(); return; }
  if (action === 'close-camera') { stopCamera(); state.scanMode = 'photo'; render(); return; }
  if (action === 'scan-mode') {
    const mode = button.dataset.mode;
    if (mode === 'camera') { await openCamera(); }
    else { stopCamera(); state.scanMode = 'photo'; render(); }
    return;
  }
  if (action === 'open-inspection') { await openInspection(button.dataset.id); return; }
  if (action === 'open-annotator') { await openAnnotator(button.dataset.id); return; }
  if (action === 'back-dataset') { if (confirmLeaveAnnotation()) await loadPage('dataset'); return; }
  if (action === 'export-dataset') { await exportAnnotatedDataset(); return; }
  if (action === 'undo-annotation-point') { state.annotationDraft.pop(); render(); return; }
  if (action === 'clear-annotation-polygon') { state.annotationDraft = []; render(); return; }
  if (action === 'finish-annotation-polygon') {
    if (state.annotationDraft.length < 3 || !state.annotationLabels.length) return;
    const objects = [...(state.annotation?.annotations?.objects || [])];
    const nextId = Math.max(0, ...objects.map((item) => Number(item.onion_id) || 0)) + 1;
    objects.push({ onion_id: nextId, labels: [...state.annotationLabels], polygon: state.annotationDraft.map(([x, y]) => [Number(x.toFixed(2)), Number(y.toFixed(2))]), notes: '' });
    state.annotation.annotations = { ...(state.annotation.annotations || {}), objects, status: 'draft' };
    state.annotationDirty = true;
    state.annotationDraft = [];
    render();
    return;
  }
  if (action === 'remove-annotation') {
    const onionId = Number(button.dataset.onion);
    state.annotation.annotations = { ...(state.annotation.annotations || {}), objects: (state.annotation?.annotations?.objects || []).filter((item) => Number(item.onion_id) !== onionId), status: 'draft' };
    state.annotationDirty = true;
    render();
    return;
  }
  if (action === 'save-annotation-draft') { await savePolygonAnnotations('draft'); return; }
  if (action === 'complete-annotation') { await savePolygonAnnotations('complete'); return; }
  if (action === 'select-onion') { state.selectedOnion = Number(button.dataset.onion); render(); return; }
  if (action === 'generate-report') { await generateReport(button.dataset.id); return; }
  if (action === 'manual-grade') { await submitManualDecision(button); return; }
  if (action === 'save-rules') { await saveRules(); return; }
  if (action === 'start-training') { await startTraining(); return; }
  if (action === 'verify-report') { await openVerification(button.dataset.id); return; }
  if (action === 'open-verification') { await openVerification(button.dataset.id); return; }
  if (action === 'close-modal') { state.report = null; render(); return; }
  if (action === 'modal-backdrop' && event.target === button) { state.report = null; render(); }
});

root.addEventListener('change', async (event) => {
  const input = event.target;
  if (input instanceof HTMLSelectElement && input.id === 'annotation-split') {
    state.annotationForm = { ...(state.annotationForm || {}), split: input.value };
    state.annotationDirty = true;
    return;
  }
  if (!(input instanceof HTMLInputElement)) return;
  if (input.dataset.annLabel) {
    const label = input.dataset.annLabel;
    state.annotationLabels = input.checked ? [...new Set([...state.annotationLabels, label])] : state.annotationLabels.filter((item) => item !== label);
    render();
    return;
  }
  const file = input.files?.[0];
  if (!file) return;
  const kind = input.dataset.kind;
  if (kind === 'scan') { await scanPhoto(file, input.dataset.mode || 'photo'); }
  if (kind === 'dataset-image') { await uploadDatasetImage(file); }
  if (kind === 'dataset-zip') { await uploadDatasetZip(file); }
  input.value = '';
});
root.addEventListener('input', (event) => {
  const fieldMap = { 'annotation-annotator': 'annotator', 'annotation-lot': 'lot_id', 'annotation-centre': 'procurement_centre' };
  const field = fieldMap[event.target.id];
  if (field) {
    state.annotationForm = { ...(state.annotationForm || {}), [field]: event.target.value };
    state.annotationDirty = true;
    return;
  }
  if (event.target.id !== 'inspection-search') return;
  const query = event.target.value.trim().toLowerCase();
  root.querySelectorAll('[data-search]').forEach((row) => { row.style.display = row.dataset.search.includes(query) ? '' : 'none'; });
});

const verifyOnLoad = new URLSearchParams(window.location.search).get('verify');
if (verifyOnLoad) {
  state.page = 'verify';
  state.verifyId = verifyOnLoad;
  loadPage('verify');
} else {
  loadPage('dashboard');
}
