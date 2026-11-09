# Using it from your phone

The skills drive **ThndrX in Chrome on your computer** (Claude in Chrome). Your phone is the remote control and the place you read the reports.

## Option 1 - chat from the Claude app (simplest)
1. On the computer: Chrome open, Claude in Chrome connected, ThndrX signed in, and the computer **awake**:
   - macOS: System Settings > Battery > Options > *Prevent automatic sleeping on power adapter when the display is off*, or run `caffeinate -dims` in Terminal while you are away.
   - Windows: Settings > System > Power > Screen and sleep > *When plugged in, put my device to sleep after: Never*.
2. On the phone: open the Claude app with the same account and type `Scan` or `check COMI`. The chat runs in the cloud and uses the Chrome on your computer.
3. The report arrives in the chat as a file, and (with a Drive folder set) as a **PDF in your Google Drive folder**: open it from the Drive app on the phone. Drive cannot display the HTML version; open that one in a browser.

## Option 2 - scheduled runs
Ask Claude: *"Every Sunday to Thursday at 09:20 Cairo time run Scan with 10,000 EGP and send me the report"*. It creates a **scheduled task** that needs your computer (Chrome) to be on. You get a notification on the phone when the run finishes; open the report there. Place the orders yourself in the Thndr app.

## Option 3 - memory synced through Drive or GitHub
With a Drive folder set, the memory files (`history.jsonl`, `news.jsonl`, `runs.jsonl`) are uploaded with every report, so a new computer can start from them.

### GitHub
Set `reports_repo` (a **private** repo such as `you/egx-reports`) in `install.py`. Every report, `index.csv` and the memory files are pushed there, so any Claude session - phone, laptop, scheduled - can answer "what did you say about HRHO?". (GitHub shows HTML as code; open the file in the Claude chat or download it to view it.)

## Recap video
Every report starts with an animated recap built with HyperFrames. With Node on the computer, ask for `--video` or run the command the report step prints:
```bash
cd ~/EGX-Reports/video/EGX_Scan_2026-11-08_21-30 && npx hyperframes render --output ../../EGX_Scan_2026-11-08_21-30.mp4
```
and send the MP4 to your phone.

## What cannot work
- Claude in Chrome does not run inside the phone's browser; the computer has to be on.
- The Thndr mobile app cannot be driven by Claude. Orders are always placed by you.
