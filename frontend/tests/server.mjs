import { spawn } from 'node:child_process';
const test = process.argv[2] === 'test';
const child = spawn(process.execPath, ['node_modules/next/dist/bin/next', 'start', '--hostname', '127.0.0.1', '--port', test ? '3101' : '3102'], {
  stdio: 'inherit', env: { ...process.env, OIL_TEST_MODE: test ? '1' : '0', NEXT_TELEMETRY_DISABLED: '1', OIL_API_URL: process.env.OIL_API_URL || 'http://127.0.0.1:8766' }
});
let stopping=false;
for (const signal of ['SIGINT','SIGTERM']) process.on(signal, () => {stopping=true;child.kill(signal);});
child.on('exit', code => process.exit(stopping?0:(code ?? 1)));
