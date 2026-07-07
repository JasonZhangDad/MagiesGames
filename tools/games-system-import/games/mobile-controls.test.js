const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = __dirname;

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
