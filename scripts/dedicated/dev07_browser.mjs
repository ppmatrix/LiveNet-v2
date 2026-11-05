// Real browser/real bundle/real API only. No HTTP route mocks or TLS bypass.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { chromium } from 'playwright-core';

const origin = 'https://livenet-v2.home.arpa:8443';
const db = `sql:${process.env.HOME}/.pki/nssdb`;
mkdirSync(`${process.env.HOME}/.pki/nssdb`, { recursive: true });
execFileSync('certutil', ['-N', '-d', db, '--empty-password']);
const launch = () => chromium.launch({ executablePath: '/usr/bin/chromium', headless: true,
  // Only the disposable client process: Docker namespaces/capabilities/read-only
  // mounts isolate it. This does not change authentication or certificate checks.
  chromiumSandbox: false });
let browser = await launch();
try {
  const page = await browser.newPage({ ignoreHTTPSErrors: false });
  let refused = false;
  try { await page.goto(`${origin}/login`); }
  catch (error) { refused = /ERR_CERT_AUTHORITY_INVALID/.test(String(error)); }
  assert(refused, 'Browser must refuse the untrusted synthetic CA');
} finally { await browser.close(); }
execFileSync('certutil', ['-A', '-d', db, '-n', 'DEV07 temporary Caddy CA', '-t', 'C,,', '-i', '/public/root.crt']);
browser = await launch();
try {
  const context = await browser.newContext({ ignoreHTTPSErrors: false, viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  const responses = [];
  const errors = [];
  page.on('pageerror', () => errors.push('pageerror'));
  page.on('response', response => {
    const u = new URL(response.url());
    if (u.origin === origin) responses.push({ path: u.pathname, status: response.status() });
  });
  await page.goto(`${origin}/inventory`, { waitUntil: 'networkidle' });
  await page.getByRole('heading', { name: 'Iniciar sessão', exact: true }).waitFor();
  assert.equal(new URL(page.url()).pathname, '/login');
  assert(await page.evaluate(() => window.isSecureContext));
  assert(await page.evaluate(() => document.querySelector('#root')?.childElementCount > 0));
  assert(responses.some(r => r.path.startsWith('/assets/') && r.path.endsWith('.js') && r.status === 200));
  assert(responses.some(r => r.path === '/api/v1/auth/me' && r.status === 401));
  assert(!responses.some(r => r.path.startsWith('/api/v1/inventory/')));
  await page.getByLabel('Nome de utilizador', { exact: true }).fill('dev07-synthetic');
  await page.getByLabel('Palavra-passe', { exact: true }).fill('synthetic-not-an-operational-secret');
  const loginResponse = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/auth/login');
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  const response = await loginResponse;
  assert.equal(response.status(), 503);
  const headers = await response.request().allHeaders();
  assert.equal(headers.origin, origin);
  assert(headers['x-csrf-token']);
  await page.getByRole('alert').filter({ hasText: 'O serviço está indisponível.' }).waitFor();
  assert.equal(await page.getByLabel('Palavra-passe', { exact: true }).inputValue(), '');
  assert(await page.getByLabel('Nome de utilizador', { exact: true }).isEnabled());
  const cookies = await context.cookies();
  const csrf = cookies.find(c => c.name === '__Host-livenet_csrf');
  assert(csrf && csrf.secure && csrf.httpOnly && csrf.sameSite === 'Lax');
  assert(!cookies.some(c => c.name === '__Host-livenet_session'));
  assert(!responses.some(r => r.path.startsWith('/api/v1/inventory/')));
  const ready = await page.request.get(`${origin}/api/v1/ready`);
  assert.equal(ready.status(), 503);
  const inventory = await page.request.get(`${origin}/api/v1/inventory/resources`);
  assert.equal(inventory.status(), 401);
  assert(inventory.headers()['content-type'].includes('application/json'));
  assert.equal((await page.request.get(`${origin}/api/v1/health`)).status(), 200);
  await page.screenshot({ path: '/evidence/react-unavailable.png', fullPage: true });
  await page.getByRole('button', { name: 'Tentar novamente', exact: true }).click();
  await page.getByRole('heading', { name: 'Iniciar sessão', exact: true }).waitFor();
  await page.waitForFunction(() => !document.querySelector('[role="alert"]'));
  assert.equal(errors.length, 0);
  console.log(JSON.stringify({ browser: await browser.version(), reactBundle: true, httpsVerified: true,
    untrustedCaRefused: true, protectedRoute: true, loginStatus: 503, csrfCookieSecure: true,
    passwordCleared: true, noSessionIssued: true, noPrivateInventoryFetch: true,
    retryRecovered: true, readiness: 503, pageErrors: errors.length, persistentLogin: false }));
} finally { await browser.close(); }
