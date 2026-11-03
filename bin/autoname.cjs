#!/usr/bin/env node
'use strict';

// Every distribution entry calls the same Python implementation.
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const helper = path.resolve(__dirname, '..', 'skills', 'autoname', 'scripts', 'autoname.py');
if (!fs.existsSync(helper)) {
  process.stderr.write('AutoName package is incomplete. Reinstall the package.\n');
  process.exit(1);
}

const candidates = process.env.AUTONAME_PYTHON
  ? [[process.env.AUTONAME_PYTHON, []]]
  : process.platform === 'win32'
    ? [['py', ['-3']], ['python3', []], ['python', []]]
    : [['python3', []], ['python', []]];

const interpreter = candidates.find(([command, prefix]) => {
  const probe = spawnSync(command, [...prefix, '-c',
    'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)'], {
    stdio: 'ignore', shell: false, windowsHide: true, timeout: 5000,
  });
  return !probe.error && probe.status === 0;
});

if (!interpreter) {
  process.stderr.write('AutoName requires Python 3.9 or later. Install Python or set AUTONAME_PYTHON to its executable.\n');
  process.exit(1);
}

const [command, prefix] = interpreter;
const result = spawnSync(command, [...prefix, helper, ...process.argv.slice(2)], {
  stdio: 'inherit', shell: false, windowsHide: true,
});
if (result.error) {
  process.stderr.write('AutoName could not start its Python helper. Check the selected interpreter.\n');
  process.exit(1);
}
if (result.signal) {
  process.exit(128 + (os.constants.signals[result.signal] || 1));
}
process.exit(result.status === null ? 1 : result.status);
