# Setup (for you and your friends)

Time: about 10 minutes. You need a **Claude** paid plan (Pro or higher), **Google Chrome**, and a **Thndr** account with **ThndrX** access.

## 1. Get the files
```bash
git clone https://github.com/tarekfouad97/egx-thndrx-trading.git
cd egx-thndrx-trading
```
or download the ZIP from GitHub (Code > Download ZIP) and unzip it.

## 2. Run the installer
| System | How |
|---|---|
| macOS | double-click **Install-Mac.command** (or `bash install.sh` in Terminal) |
| Windows | double-click **Install-Windows.bat** |
| Linux | `bash install.sh` |

The bootstrapper installs Python 3 if it is missing (Homebrew or python.org on macOS, winget on Windows), offers Node.js (optional), then runs `install.py`, which:
- asks your name, report language (ar / en), reports folder, risk % per trade, and the optional trade-log sheet, reports repo and Google Drive folder;
- writes `skills/egx-check/config.json` (never committed);
- creates the reports folder with `index.csv`;
- builds **`dist/egx-thndrx-trading.plugin`** and **`dist/claude-ai-skills/*.zip`**;
- copies the skills into `~/.claude/skills` when Claude Code is installed;
- optionally installs the Apple-design skill and the HyperFrames skills (needs Node).

Run it again any time to change a setting.

## 3. Add the skills to Claude
- **Claude desktop app or claude.ai**: drag `dist/egx-thndrx-trading.plugin` into a chat and accept it, **or** Settings > Capabilities > Skills > upload the three zips in `dist/claude-ai-skills/`.
- **Claude Code**: already done by the installer.

## 4. Connect Chrome
1. Install **Claude in Chrome** from https://claude.ai/chrome and sign in with the same Claude account.
2. In that Chrome, open https://x.thndr.app and sign in to ThndrX (approve 2FA in the Thndr app).
3. In Claude settings, pick **Claude in Chrome** as the preferred browser.

The first time a skill runs it sends a ~20 KB script into the ThndrX tab once and caches it in that tab's local storage; later runs only send a one-line loader.

## 5. Optional: reports in Google Drive
1. In Google Drive make a folder for the reports (e.g. **ThndrX**) and copy its link.
2. Paste the link when `install.py` asks for the Drive folder (or put its id in `drive_folder_id` in `~/.egx-thndrx/config.json`).
3. In Claude, connect **Google Drive**. Every report is then uploaded as HTML + PDF, with the memory files. Chrome on the computer makes the PDF.

## 6. Optional: trade log (Google Sheets)
1. Google Drive > New > File upload > `templates/EGX_Trade_Log_template.xlsx`, then open it with Google Sheets (File > Save as Google Sheets).
2. Fill **Settings** (Thndr plan fee, your Claude plan in USD, equity, risk %).
3. Copy the sheet id from its URL (`docs.google.com/spreadsheets/d/<THIS PART>/edit`) and give it to `install.py`.
4. In Claude, connect **Google Sheets** (and **Gmail** if you want fees read from Thndr e-invoices).

## 7. Use it
| Say | What happens |
|---|---|
| `check COMI` / `افحص COMI` | full scripted analysis, drawings verified on your ThndrX chart, news, verdict, exact order steps, report |
| `check COMI T0` | same-session check on 5-minute bars (10:15-13:30 Cairo, exit by 14:10) |
| `market` | EGX30 regime, breadth, sectors |
| `my positions` / `راجع مراكزي` | hold / tighten / sell / add for each stock you hold |
| `Scan` / `لف على الـ 30` | positions + Top 30 + Hot stocks + Same-day T0 (in session), top 3 per list, allocation of your amount |
| `اشتريت HRHO 226 بـ 22.04` / `بعت EGAL` | logs the trade in your sheet |
| `monthly` | this month's results vs your fixed costs |
| `قلت ايه عن HRHO؟` | Claude's memory of every past call on HRHO, with outcomes |

## Safety
The skills **never place, change or cancel orders**, never type in the order ticket, never log in for you and never call Thndr's servers directly. They read what ThndrX shows and draw lines on your chart. Everything is analysis, not investment advice.
