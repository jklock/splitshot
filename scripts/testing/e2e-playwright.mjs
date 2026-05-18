import { chromium } from 'playwright';
import os from 'os';

const port = process.env.E2E_PORT || process.argv[2] || '8765';
const baseUrl = `http://127.0.0.1:${port}`;

async function main() {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--disable-software-rasterizer'],
  });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
  });
  const page = await context.newPage();

  await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  console.log('PW: page loaded');

  await page.waitForFunction(() => typeof activeTool !== 'undefined', { timeout: 45000 });
  console.log('PW: app initialized');
  await page.waitForTimeout(1000);

  if (!(await page.evaluate(() => Boolean(state?.project?.path)))) {
    const pp = `${os.tmpdir()}/sshot-e2e-project.ssproj`;
    await page.evaluate((p) => createNewProject(p), pp);
    await page.waitForFunction(() => Boolean(state?.project?.path), { timeout: 15000 });
    await page.waitForTimeout(500);
  }

  const tools = ['project', 'merge', 'scoring', 'timing', 'markers', 'overlay', 'review', 'export', 'metrics', 'settings'];
  for (const t of tools) {
    const btn = page.locator(`button[data-tool="${t}"]`);
    if (await btn.isVisible()) {
      await btn.click({ force: true });
      await page.waitForFunction((tool) => activeTool === tool, t, { timeout: 15000 });
      await page.waitForTimeout(300);
      console.log(`PW: tool ${t} activated`);
    }
  }

  await page.locator('button[data-tool="timing"]').click({ force: true });
  await page.waitForFunction(() => activeTool === 'timing', { timeout: 10000 });
  if ((await page.locator('.waveform-shot-card').count()) > 0) {
    await page.locator('.waveform-shot-card').first().click();
    await page.waitForTimeout(300);
    console.log('PW: waveform selected');
  }

  for (const t of ['markers', 'overlay', 'review', 'settings', 'scoring']) {
    await page.locator(`button[data-tool="${t}"]`).click({ force: true });
    await page.waitForFunction((tool) => activeTool === tool, t, { timeout: 10000 });
    await page.waitForTimeout(300);
  }

  const state = await page.evaluate(() => ({
    shots: state?.project?.analysis?.shots?.length || 0,
    popups: state?.project?.popups?.length || 0,
  }));
  console.log(`PW: final state shots=${state.shots} popups=${state.popups}`);

  await context.close();
  await browser.close();
  console.log('PW: E2E test passed');
  process.exit(0);
}

main().catch(err => {
  console.error('PW: FAILED -', err.message);
  process.exit(1);
});
