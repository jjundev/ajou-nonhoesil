const labRoot = document.getElementById('ec2-lab-root');
const themeButton = labRoot.querySelector('.theme-toggle');
const themePreference = matchMedia('(prefers-color-scheme: dark)');
const narrowLayout = matchMedia('(max-width: 1023.98px)');
const scrim = labRoot.querySelector('.scrim');
const topbar = labRoot.querySelector('.topbar');
const panelControls = new Map(Array.from(labRoot.querySelectorAll('[data-drawer-btn]'), toggle => {
  const side = toggle.dataset.drawerBtn;
  const panel = document.getElementById('panel-' + side);
  toggle.setAttribute('aria-controls', panel.id);
  return [side, {panel, toggle, close: panel.querySelector('[data-close-drawer]'), open: true}];
}));
let drawer = null;

function syncPanels() {
  labRoot.dataset.drawer = drawer ?? 'none';
  scrim.classList.toggle('is-on', drawer !== null);
  document.getElementById('stage').inert = drawer !== null;
  topbar.inert = drawer !== null;
  for (const [side, {panel, toggle, open}] of panelControls) {
    const visible = narrowLayout.matches ? drawer === side : open;
    panel.classList.toggle('is-open', visible);
    panel.inert = !visible;
    if (narrowLayout.matches && visible) {
      panel.setAttribute('role', 'dialog');
      panel.setAttribute('aria-modal', 'true');
    } else {
      panel.removeAttribute('role');
      panel.removeAttribute('aria-modal');
    }
    toggle.setAttribute('aria-expanded', visible);
    toggle.setAttribute('aria-pressed', visible);
  }
}

function closeDrawer() {
  if (drawer === null) return;
  const {toggle} = panelControls.get(drawer);
  drawer = null;
  syncPanels();
  toggle.focus();
}

for (const [side, controls] of panelControls) {
  controls.toggle.addEventListener('click', () => {
    if (narrowLayout.matches) {
      if (drawer === side) {
        closeDrawer();
        return;
      }
      drawer = side;
      syncPanels();
      controls.close.focus();
    } else {
      controls.open = !controls.open;
      syncPanels();
    }
  });
  controls.close.addEventListener('click', closeDrawer);
}
scrim.addEventListener('click', closeDrawer);
document.addEventListener('keydown', event => {
  if (drawer === null) return;
  if (event.key === 'Escape') {
    event.preventDefault();
    closeDrawer();
  }
  if (event.key === 'Tab') {
    const panel = panelControls.get(drawer).panel;
    const controls = Array.from(panel.querySelectorAll('button:not(:disabled)'));
    const first = controls[0];
    const last = controls.at(-1);
    if (event.shiftKey ? document.activeElement === first : document.activeElement === last) {
      event.preventDefault();
      (event.shiftKey ? last : first).focus();
    }
  }
});
narrowLayout.addEventListener('change', () => {
  if (drawer !== null) closeDrawer();
  else syncPanels();
});
syncPanels();

function activeTheme() {
  return document.documentElement.dataset.theme ?? (themePreference.matches ? 'dark' : 'light');
}

function syncThemeButton() {
  const label = activeTheme() === 'dark' ? '라이트 모드로 전환' : '다크 모드로 전환';
  themeButton.setAttribute('aria-label', label);
  themeButton.title = label;
}
themeButton.addEventListener('click', () => {
  const theme = activeTheme() === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem('od-theme', theme);
  } catch {
    // File URLs can block storage in some browsers.
  }
  syncThemeButton();
});
themePreference.addEventListener('change', syncThemeButton);
syncThemeButton();
