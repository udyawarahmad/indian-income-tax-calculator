const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');

let backendProcess = null;
let mainWindow = null;

function getBackendCommand() {
  const isWin = process.platform === 'win32';
  const packagedBackend = path.join(process.resourcesPath, 'backend', isWin ? 'tax-calculator-backend.exe' : 'tax-calculator-backend', isWin ? 'tax-calculator-backend.exe' : 'tax-calculator-backend');
  // PyInstaller onedir layout: resources/backend/tax-calculator-backend/tax-calculator-backend(.exe)
  const onedir = path.join(process.resourcesPath, 'backend', 'tax-calculator-backend', isWin ? 'tax-calculator-backend.exe' : 'tax-calculator-backend');
  if (fs.existsSync(onedir)) return { cmd: onedir, args: [], cwd: path.dirname(onedir) };
  if (fs.existsSync(packagedBackend)) return { cmd: packagedBackend, args: [], cwd: path.dirname(packagedBackend) };

  // Dev fallback: run python server.py
  const repoRoot = path.resolve(__dirname, '..');
  const serverPy = path.join(repoRoot, 'backend', 'server.py');
  const python = process.env.PYTHON || (isWin ? 'python' : 'python3');
  return { cmd: python, args: [serverPy], cwd: path.join(repoRoot, 'backend'), dev: true };
}

function waitForHealth(url, timeoutMs = 30000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => {
      if (Date.now() - start > timeoutMs) return reject(new Error('Backend did not become healthy in time'));
      const req = http.get(url, res => {
        if (res.statusCode === 200) { res.resume(); return resolve(); }
        res.resume(); setTimeout(tick, 500);
      });
      req.on('error', () => setTimeout(tick, 500));
      req.setTimeout(2000, () => { req.destroy(); setTimeout(tick, 500); });
    };
    tick();
  });
}

async function startBackend() {
  const port = Number(process.env.TAX_CALC_PORT || 8765);
  const dataDir = path.join(app.getPath('userData'), 'data');
  fs.mkdirSync(dataDir, { recursive: true });
  const { cmd, args, cwd, dev } = getBackendCommand();
  const frontendDist = path.join(process.resourcesPath, 'frontend-dist');
  const devFrontendDist = path.resolve(__dirname, '..', 'frontend', 'dist');

  const env = { ...process.env, PORT: String(port), TAX_CALC_DATA_DIR: dataDir };
  if (fs.existsSync(frontendDist)) env.FRONTEND_DIST = frontendDist;
  else if (fs.existsSync(devFrontendDist)) env.FRONTEND_DIST = devFrontendDist;
  if (dev) env.PYTHONPATH = path.resolve(__dirname, '..', 'backend');

  backendProcess = spawn(cmd, [...args, '--host', '127.0.0.1', '--port', String(port), '--data-dir', dataDir], {
    cwd, env, stdio: ['ignore', 'pipe', 'pipe']
  });
  backendProcess.stdout.on('data', d => console.log(`[backend] ${d}`.trim()));
  backendProcess.stderr.on('data', d => console.error(`[backend] ${d}`.trim()));
  backendProcess.on('exit', (code) => console.log(`Backend exited: ${code}`));

  await waitForHealth(`http://127.0.0.1:${port}/api/health`);
  return port;
}

async function createWindow() {
  try {
    const port = await startBackend();
    mainWindow = new BrowserWindow({
      width: 1400,
      height: 920,
      minWidth: 1100,
      minHeight: 700,
      title: 'Indian Income Tax Calculator',
      webPreferences: {
        preload: path.join(__dirname, 'preload.js'),
        contextIsolation: true,
        nodeIntegration: false,
      }
    });
    await mainWindow.loadURL(`http://127.0.0.1:${port}/`);
  } catch (err) {
    console.error(err);
    dialog.showErrorBox('Startup Error', `Failed to start application.\n\n${err.message}`);
    app.quit();
  }
}

function stopBackend() {
  if (!backendProcess) return;
  try {
    if (process.platform === 'win32') spawn('taskkill', ['/pid', String(backendProcess.pid), '/T', '/F']);
    else backendProcess.kill('SIGTERM');
  } catch {}
  backendProcess = null;
}

app.whenReady().then(createWindow);
app.on('window-all-closed', () => { stopBackend(); if (process.platform !== 'darwin') app.quit(); });
app.on('before-quit', stopBackend);
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
