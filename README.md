# PowerSplitter PDU Configurator

A small Python/tkinter GUI that configures the **PowerSplitter** app to connect to a PDU over SSH without requiring the Configuration Manager (CM) service, which is EOL.

## Background

PowerSplitter normally discovers its PDU IP and outlet assignments through Intel's CM/Neptune service. When that service is unavailable the app shows *"Cannot retrieve PDU Credentials from CSV or Neptune"* and refuses to work. This tool writes the required CSV mapping file and sets the three environment variables that PowerSplitter's `PDUConfigCSV` path reads directly.

## How it works

PowerSplitter's PDU DLL (`Intel.SSR.Services.PDU.dll`) supports three config sources. When `PDU_MAPPING_PATH` is set it reads a CSV file instead of calling Neptune:

| Env variable | Purpose |
|---|---|
| `PDU_MAPPING_PATH` | Full path to `PDUMapping.csv` |
| `PDU_USERNAME` | PDU SSH username |
| `PDU_ENCRYPTED_PASS` | Base64-encoded SSH password |

CSV format expected by the app:
```
HostName,PduNameOrIP,TargetOutlet
YOUR-PC-HOSTNAME,192.168.x.x,10
```
Outlets support single (`10`), semicolon list (`10;11;12`), or range (`8-12`).

## Requirements

- Windows
- Python 3.x (standard library only — `tkinter`, `winreg`, `csv`, `socket`, `base64`)
- PowerSplitter installed at `C:\SVShare\user_apps\PowerSplitter\`

## Usage

```powershell
python main.py
```

1. **CSV File** — choose where to save `PDUMapping.csv`
2. **PDU Mapping** — your hostname is auto-filled; enter the PDU IP and outlet number(s)
3. **SSH Credentials** — enter the PDU SSH username and password
4. Click **Save & Apply** — writes the CSV and sets the three env vars permanently in your user registry
5. Restart `PowerSplitter.exe` — it now uses the CSV and bypasses CM (Configuration Manager) entirely

## Install PowerSplitter

If PowerSplitter is not yet installed, click **Install PowerSplitter** in the bottom bar. This runs:

```
packman install -n PowerSplitter --force
```

Live output is streamed in a terminal-style window.
