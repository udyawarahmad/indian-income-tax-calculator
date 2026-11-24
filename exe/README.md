# Windows Executable Output

This folder contains the distributable Windows installer after a successful build.

## Build on Windows

From the repository root in PowerShell:

```powershell
./scripts/build_windows.ps1
```

The installer will be copied here as `Indian-Income-Tax-Calculator-Setup-<version>.exe`.

## Notes

- The `.exe`/installer binaries are not committed to git (ignored by `.gitignore`).
- Build artifacts are produced by PyInstaller (backend) and Electron Builder (desktop).
- For CI-based builds, see `.github/workflows/build-windows.yml`.
