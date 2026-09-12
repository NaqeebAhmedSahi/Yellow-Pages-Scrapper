# Packaging with PyInstaller

Build a portable desktop app so other PCs can run Yellow Pages Scraper **without Python, pip, or source code**.

> Important: PyInstaller builds are **OS-specific**.
> Build on Windows to get a Windows `.exe`. Build on Linux to get a Linux binary.

## What you get

After a successful build:

```text
dist/YellowPagesScraper/
├── YellowPagesScraper.exe   (Windows)  or  YellowPagesScraper (Linux)
├── _internal/               (required libraries — keep this folder)
└── README_PORTABLE.txt
```

Zip that whole folder and share it. Recipients extract and double-click the app.

## Target PC requirements

| Requirement | Notes |
|-------------|--------|
| Extracted app folder | Keep EXE + `_internal` together |
| Google Chrome | Still required (browser is not bundled) |
| No Python needed | Runtime is inside the package |

## Windows build steps

1. Install **Python 3.10+** from https://www.python.org/downloads/  
   - Enable **Add python.exe to PATH**
2. Install **Google Chrome** on the build PC
3. Open the project folder in File Explorer
4. Double-click **`build_windows.bat`**  
   or run in Command Prompt:

```bat
build_windows.bat
```

5. Wait until you see **BUILD SUCCESS**
6. Open:

```text
dist\YellowPagesScraper\
```

7. Zip the entire `YellowPagesScraper` folder
8. Copy the ZIP to other Windows PCs, extract, run `YellowPagesScraper.exe`

### Manual Windows commands

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-build.txt
pyinstaller --noconfirm --clean YellowPagesScraper.spec
```

## Linux build steps

```bash
chmod +x build_linux.sh
./build_linux.sh
```

Or manually:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-build.txt
pyinstaller --noconfirm --clean YellowPagesScraper.spec
chmod +x dist/YellowPagesScraper/YellowPagesScraper
```

## End-user install (other PC)

1. Extract the ZIP anywhere (Desktop, Documents, USB, etc.)
2. Open the extracted `YellowPagesScraper` folder
3. Run `YellowPagesScraper.exe` (Windows) or `./YellowPagesScraper` (Linux)
4. Confirm Chrome is installed
5. Scraped data appears in `output\` next to the EXE

## Optional: create a Windows Setup installer

PyInstaller creates a portable folder. For a classic `Setup.exe` installer:

1. Build with `build_windows.bat` first
2. Install [Inno Setup](https://jrsoftware.org/isinfo.php)
3. Create an installer that copies `dist\YellowPagesScraper\*` into  
   `C:\Program Files\YellowPagesScraper\`
4. Add a Start Menu shortcut to `YellowPagesScraper.exe`

(Portable ZIP is enough for most users.)

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Antivirus blocks EXE | Allow/unblock; PyInstaller apps are often flagged at first |
| App opens then closes | Check `output\logs\gui.log` next to the EXE |
| Chrome / driver errors | Install/update Google Chrome on that PC |
| Missing `_internal` | You moved only the EXE — copy the whole folder |
| Build works on Linux but not Windows | Rebuild on a Windows PC |

## Notes

- Output paths are next to the executable when frozen (`output/data`, `output/logs`, `output/app`)
- Spec file: `YellowPagesScraper.spec` (onedir GUI build, no console window)
- Rebuild after code changes with `build_windows.bat` / `build_linux.sh`
