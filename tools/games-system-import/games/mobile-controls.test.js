const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = __dirname;
const repoRoot = path.join(root, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(root, rel), 'utf8');
}

test('arcade games enable touch controls on touch-capable and narrow devices', () => {
  const inputFiles = [
    ['crazy-bumper-cars', 'crazy-bumper-cars/public/js/input.js'],
    ['bomb-party', 'bomb-party/public/js/input.js'],
    ['ice-climber-arena', 'ice-climber-arena/public/js/main.js'],
    ['neon-arena-fps', 'neon-arena-fps/public/js/game.js'],
  ];

  for (const [name, rel] of inputFiles) {
    const src = read(rel);
    assert.match(src, /maxTouchPoints/, `${name} should detect touch-capable devices`);
    assert.match(src, /pointer:\s*coarse/, `${name} should detect coarse pointers`);
    assert.match(src, /innerWidth\s*<=\s*820/, `${name} should show touch controls on narrow screens`);
  }
});

test('all five arcade games include on-screen mobile controls', () => {
  const pages = [
    ['crazy-bumper-cars', 'crazy-bumper-cars/public/index.html', 'touch-ui'],
    ['arena-brawl', 'arena-brawl/public/index.html', 'mobileControls'],
    ['bomb-party', 'bomb-party/public/index.html', 'touch-controls'],
    ['ice-climber-arena', 'ice-climber-arena/public/index.html', 'touch-controls'],
    ['neon-arena-fps', 'neon-arena-fps/public/index.html', 'touchLayer'],
  ];

  for (const [name, rel, marker] of pages) {
    assert.match(read(rel), new RegExp(`id="${marker}"`), `${name} should render ${marker}`);
  }

  const arenaCss = read('arena-brawl/public/css/style.css');
  assert.match(arenaCss, /#mobileControls/, 'arena-brawl should style mobile controls');
  assert.match(arenaCss, /max-width:680px/, 'arena-brawl should show controls on phone-sized screens');
});

test('arcade shell keeps the lobby button below the phone status bar', () => {
  const src = fs.readFileSync(path.join(repoRoot, 'frontend/src/views/ArcadeView.vue'), 'utf8');
  assert.match(src, /--arcade-bar-height/, 'arcade shell should define one safe toolbar height');
  assert.match(src, /var\(--safe-t\)/, 'arcade toolbar should include the top safe-area inset');
  assert.match(src, /inset:\s*var\(--arcade-bar-height\)/, 'overlays should start below the safe toolbar');
});

test('neon arena menu buttons have touch tap handlers for mobile PWA', () => {
  const src = read('neon-arena-fps/public/js/game.js');
  assert.match(src, /function bindTap/, 'neon arena should share a touch-safe tap binder');
  assert.match(src, /touchend/, 'neon arena should listen for touchend on menu buttons');
  assert.match(src, /bindTap\('btnPlay'/, 'enter battle should use the touch-safe tap binder');
  assert.match(src, /bindTap\('btnSpec'/, 'spectate should use the touch-safe tap binder');
});

test('arcade games cap mobile render pixel ratio', () => {
  const files = [
    ['crazy-bumper-cars', 'crazy-bumper-cars/public/js/render.js'],
    ['bomb-party', 'bomb-party/public/js/render.js'],
    ['arena-brawl', 'arena-brawl/public/js/render.js'],
    ['ice-climber-arena', 'ice-climber-arena/public/js/main.js'],
    ['neon-arena-fps', 'neon-arena-fps/public/js/game.js'],
  ];

  for (const [name, rel] of files) {
    const src = read(rel);
    assert.match(src, /MOBILE_DPR_LIMIT/, `${name} should have a mobile DPR cap`);
    assert.match(src, /1\.25/, `${name} should cap mobile render scale around 1.25x`);
  }
});
