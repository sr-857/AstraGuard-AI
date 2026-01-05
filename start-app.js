#!/usr/bin/env node
/**
 * AstraGuard AI - Complete Stack Startup Script
 * 
 * This script starts:
 * 1. Backend API Server (FastAPI on port 8000)
 * 2. Frontend App (Next.js on port 3000)
 * 3. Opens dashboard in browser
 * 
 * Usage:
 *   node start-app.js
 *   npm run app:start
 */

const { spawn } = require('child_process');
const path = require('path');
const http = require('http');
const os = require('os');

const isWindows = os.platform() === 'win32';
const isLinux = os.platform() === 'linux';

let apiProcess = null;
let appProcess = null;

console.log(`
╔═══════════════════════════════════════════════════════════╗
║    AstraGuard AI - Complete Stack Startup                 ║
╚═══════════════════════════════════════════════════════════╝
`);

/**
 * Wait for a server to be ready
 */
function waitForServer(port, maxAttempts = 30) {
  return new Promise((resolve) => {
    let attempts = 0;

    const check = () => {
      attempts++;
      const req = http.get(`http://localhost:${port}`, (res) => {
        console.log(`✅ Server on port ${port} is ready!`);
        resolve(true);
      });

      req.on('error', () => {
        if (attempts < maxAttempts) {
          setTimeout(check, 1000);
        } else {
          console.warn(`⚠️  Server on port ${port} not ready after ${maxAttempts}s`);
          resolve(false);
        }
      });
    };

    check();
  });
}

/**
 * Open browser
 */
function openBrowser(url) {
  const start = isWindows ? 'start' : isLinux ? 'xdg-open' : 'open';
  spawn(start, [url], { stdio: 'ignore' });
}

/**
 * Start backend API
 */
async function startBackend() {
  console.log('📡 Starting Backend API Server...');

  return new Promise((resolve) => {
    const python = isWindows ? 'python' : 'python3';
    apiProcess = spawn(python, ['run_api.py'], {
      cwd: path.join(__dirname),
      stdio: 'pipe',
    });

    apiProcess.stdout.on('data', (data) => {
      const output = data.toString();
      if (output.includes('Application startup complete')) {
        console.log('✅ Backend API Server is running on http://localhost:8000');
        console.log('📚 API Docs: http://localhost:8000/docs');
        resolve(true);
      }
    });

    apiProcess.stderr.on('data', (data) => {
      console.log(data.toString());
    });

    setTimeout(() => resolve(true), 5000);
  });
}

/**
 * Start frontend app
 */
async function startFrontend() {
  console.log('🎨 Starting Frontend App (Next.js)...');

  return new Promise((resolve) => {
    const cmd = isWindows ? 'npm.cmd' : 'npm';
    appProcess = spawn(cmd, ['run', 'dev'], {
      cwd: path.join(__dirname, 'frontend', 'astraguard-ai.site'),
      stdio: 'pipe',
    });

    appProcess.stdout.on('data', (data) => {
      const output = data.toString();
      if (output.includes('ready - started server') || output.includes('compiled')) {
        console.log('✅ Frontend App is running on http://localhost:3000');
        resolve(true);
      }
    });

    appProcess.stderr.on('data', (data) => {
      console.log(data.toString());
    });

    setTimeout(() => resolve(true), 8000);
  });
}

/**
 * Main startup sequence
 */
async function main() {
  try {
    // Start backend
    await startBackend();
    await waitForServer(8000);

    console.log('');

    // Start frontend
    await startFrontend();
    await waitForServer(3000);

    console.log(`
╔═══════════════════════════════════════════════════════════╗
║              🚀 AstraGuard AI is Running!                 ║
╚═══════════════════════════════════════════════════════════╝

🌐 Frontend App: http://localhost:3000
📡 Backend API:  http://localhost:8000
📚 API Docs:     http://localhost:8000/docs
📊 Metrics:      http://localhost:9090/metrics

🎯 Opening dashboard in browser...
    `);

    // Open browser
    openBrowser('http://localhost:3000');

    // Handle shutdown
    process.on('SIGINT', () => {
      console.log('\n\n🛑 Shutting down AstraGuard AI...');
      if (apiProcess) apiProcess.kill();
      if (appProcess) appProcess.kill();
      process.exit(0);
    });
  } catch (error) {
    console.error('❌ Error starting AstraGuard AI:', error);
    process.exit(1);
  }
}

main();
