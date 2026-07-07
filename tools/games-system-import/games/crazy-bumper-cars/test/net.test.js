'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function loadNetTestApi() {
  const source = fs.readFileSync(path.join(__dirname, '../public/js/net.js'), 'utf8');
  const sandbox = {
    location: { protocol: 'https:', host: 'games.magies.top', pathname: '/arcade/bumper-cars/' },
    WebSocket: function WebSocket() {},
    setInterval,
    clearInterval,
    setTimeout,
    performance: { now: () => 0 },
  };
  vm.runInNewContext(`${source}\n;globalThis.__netTest = Net.__test;`, sandbox);
  return sandbox.__netTest;
}

test('WebSocket URL keeps arcade sub-path when embedded behind main Nginx', () => {
  const api = loadNetTestApi();
  assert.equal(
    api.urlFor({ protocol: 'https:', host: 'games.magies.top', pathname: '/arcade/bumper-cars/' }),
    'wss://games.magies.top/arcade/bumper-cars/'
  );
});

test('WebSocket URL remains root-based for standalone local server', () => {
  const api = loadNetTestApi();
  assert.equal(
    api.urlFor({ protocol: 'http:', host: 'localhost:3000', pathname: '/' }),
    'ws://localhost:3000/'
  );
});
