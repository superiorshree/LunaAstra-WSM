const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

// ─── Backend Process Management ───────────────────────────────────────────────
let backendProcess = null
const BACKEND_PORT = 8000
const isDev = process.env.NODE_ENV !== 'production'

function startBackend() {
  const backendDir = path.join(__dirname, '..', '..', 'backend')
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'

  console.log('[Electron] Starting FastAPI backend...')
  console.log('[Electron] Backend dir:', backendDir)

  backendProcess = spawn(
    pythonCmd,
    ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT)],
    {
      cwd: backendDir,
      stdio: ['ignore', 'pipe', 'pipe'],
      // Use venv if available
      env: {
        ...process.env,
        PYTHONPATH: backendDir,
        // Try venv python first
        PATH: `${path.join(backendDir, 'venv', 'Scripts')}${path.delimiter}${process.env.PATH}`,
      }
    }
  )

  backendProcess.stdout.on('data', (data) => {
    console.log(`[Backend] ${data.toString().trim()}`)
  })

  backendProcess.stderr.on('data', (data) => {
    console.error(`[Backend ERR] ${data.toString().trim()}`)
  })

  backendProcess.on('exit', (code) => {
    console.log(`[Backend] Process exited with code ${code}`)
    backendProcess = null
  })
}

function stopBackend() {
  if (backendProcess) {
    console.log('[Electron] Stopping backend...')
    backendProcess.kill('SIGTERM')
    backendProcess = null
  }
}

// ─── Window Creation ──────────────────────────────────────────────────────────
function createWindow() {
  const win = new BrowserWindow({
    width: 1600,
    height: 1000,
    minWidth: 1200,
    minHeight: 700,
    backgroundColor: '#0a0e1a',   // match app dark background
    titleBarStyle: 'hiddenInset',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: false,           // allow local file:// assets in production
    },
    icon: path.join(__dirname, '../public/icon.png'),
    title: 'LunaAstra — Lunar Habitat AI Decision Support System',
    show: false,   // Don't show until ready to avoid flash
  })

  // Load the React app
  if (isDev) {
    win.loadURL('http://localhost:5173')
    win.webContents.openDevTools({ mode: 'detach' })
  } else {
    win.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  win.once('ready-to-show', () => {
    win.show()
  })

  return win
}

// ─── App Lifecycle ────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  startBackend()

  // Wait a moment for backend to initialize before creating window
  setTimeout(() => {
    createWindow()
  }, 2000)

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  stopBackend()
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', () => {
  stopBackend()
})

// ─── IPC Handlers ─────────────────────────────────────────────────────────────
ipcMain.handle('get-backend-url', () => {
  return `http://127.0.0.1:${BACKEND_PORT}`
})

ipcMain.handle('get-app-version', () => {
  return app.getVersion()
})
