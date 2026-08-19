import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import csv
import socket
import base64
import winreg
import subprocess
import threading


def _set_user_env(name, value):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)


def _get_user_env(name):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value
    except FileNotFoundError:
        return ""


class PDUConfigurator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PowerSplitter PDU Configurator")
        self.resizable(False, False)

        self.csv_path_var = tk.StringVar()
        self.ip_var = tk.StringVar()
        self.outlets_var = tk.StringVar()
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.show_pass = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready")

        self._load_existing()
        self._build_ui()

    def _load_existing(self):
        path = _get_user_env("PDU_MAPPING_PATH") or os.environ.get("PDU_MAPPING_PATH", "")
        self.csv_path_var.set(path)
        self.username_var.set(_get_user_env("PDU_USERNAME") or os.environ.get("PDU_USERNAME", ""))
        enc = _get_user_env("PDU_ENCRYPTED_PASS") or os.environ.get("PDU_ENCRYPTED_PASS", "")
        if enc:
            try:
                self.password_var.set(base64.b64decode(enc).decode("utf-8"))
            except Exception:
                pass

        csv_file = path if os.path.isfile(path) else os.path.join(path, "PDUMapping.csv")
        if os.path.isfile(csv_file):
            try:
                with open(csv_file, newline="") as f:
                    for row in csv.DictReader(f):
                        if row["HostName"] == socket.gethostname():
                            self.ip_var.set(row["PduNameOrIP"])
                            self.outlets_var.set(row["TargetOutlet"])
                            break
            except Exception:
                pass

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # --- CSV file ---
        f_csv = ttk.LabelFrame(self, text="CSV File", padding=8)
        f_csv.grid(row=0, column=0, padx=12, pady=(12, 4), sticky="ew")
        f_csv.columnconfigure(1, weight=1)
        ttk.Label(f_csv, text="Path:").grid(row=0, column=0, sticky="w")
        ttk.Entry(f_csv, textvariable=self.csv_path_var, width=46).grid(row=0, column=1, padx=6, sticky="ew")
        ttk.Button(f_csv, text="Browse", command=self._browse).grid(row=0, column=2)

        # --- PDU mapping ---
        f_pdu = ttk.LabelFrame(self, text="PDU Mapping", padding=8)
        f_pdu.grid(row=1, column=0, padx=12, pady=4, sticky="ew")
        f_pdu.columnconfigure(1, weight=1)

        ttk.Label(f_pdu, text="Hostname:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Label(f_pdu, text=socket.gethostname(), foreground="#555").grid(row=0, column=1, sticky="w", **pad)

        ttk.Label(f_pdu, text="PDU IP:").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(f_pdu, textvariable=self.ip_var, width=22).grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(f_pdu, text="Outlets:").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(f_pdu, textvariable=self.outlets_var, width=22).grid(row=2, column=1, sticky="w", **pad)
        ttk.Label(f_pdu, text="e.g.  10  or  10;11;12  or  8-12", foreground="gray").grid(row=2, column=2, sticky="w")

        # --- Credentials ---
        f_cred = ttk.LabelFrame(self, text="PDU SSH Credentials", padding=8)
        f_cred.grid(row=2, column=0, padx=12, pady=4, sticky="ew")

        ttk.Label(f_cred, text="Username:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(f_cred, textvariable=self.username_var, width=22).grid(row=0, column=1, sticky="w", **pad)

        ttk.Label(f_cred, text="Password:").grid(row=0, column=2, sticky="w", padx=(20, 8))
        self.pass_entry = ttk.Entry(f_cred, textvariable=self.password_var, width=22, show="*")
        self.pass_entry.grid(row=0, column=3, sticky="w", **pad)
        ttk.Checkbutton(f_cred, text="Show", variable=self.show_pass,
                        command=lambda: self.pass_entry.config(show="" if self.show_pass.get() else "*")
                        ).grid(row=0, column=4, sticky="w")

        # --- Bottom bar ---
        bottom = ttk.Frame(self)
        bottom.grid(row=3, column=0, padx=12, pady=(4, 12), sticky="ew")
        ttk.Button(bottom, text="Save & Apply", command=self._save_all).pack(side="left")
        ttk.Button(bottom, text="Install PowerSplitter", command=self._install).pack(side="left", padx=(8, 0))
        ttk.Label(bottom, textvariable=self.status_var, foreground="blue").pack(side="left", padx=12)

    def _install(self):
        win = tk.Toplevel(self)
        win.title("Installing PowerSplitter")
        win.geometry("640x320")
        win.resizable(True, True)

        txt = tk.Text(win, wrap="word", font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4")
        vsb = ttk.Scrollbar(win, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True, padx=4, pady=4)

        def _stream():
            try:
                proc = subprocess.Popen(
                    ["packman", "install", "-n", "PowerSplitter", "--force"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1
                )
                for line in proc.stdout:
                    win.after(0, lambda l=line: (txt.insert("end", l), txt.see("end")))
                proc.wait()
                end_msg = ("\n[Done — exit code 0]\n" if proc.returncode == 0
                           else f"\n[Failed — exit code {proc.returncode}]\n")
            except FileNotFoundError:
                end_msg = "\n[Error: 'packman' command not found in PATH]\n"
            win.after(0, lambda: (txt.insert("end", end_msg), txt.see("end")))

        threading.Thread(target=_stream, daemon=True).start()

    def _browse(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="PDUMapping.csv",
            title="Choose CSV file location",
        )
        if path:
            self.csv_path_var.set(path)

    def _save_all(self):
        csv_path = self.csv_path_var.get().strip()
        ip = self.ip_var.get().strip()
        outlets = self.outlets_var.get().strip()
        username = self.username_var.get().strip()
        password = self.password_var.get()

        if not csv_path:
            messagebox.showerror("Missing", "Specify a CSV file path.")
            return
        if not ip or not outlets:
            messagebox.showerror("Missing", "PDU IP and Outlets are required.")
            return
        if not username or not password:
            messagebox.showerror("Missing", "Username and password are required.")
            return

        if os.path.isdir(csv_path):
            csv_path = os.path.join(csv_path, "PDUMapping.csv")
            self.csv_path_var.set(csv_path)

        try:
            os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
            with open(csv_path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["HostName", "PduNameOrIP", "TargetOutlet"])
                w.writerow([socket.gethostname(), ip, outlets])
        except Exception as e:
            messagebox.showerror("Save error", f"Could not write CSV:\n{e}")
            return

        enc = base64.b64encode(password.encode("utf-8")).decode("utf-8")
        try:
            _set_user_env("PDU_MAPPING_PATH", csv_path)
            _set_user_env("PDU_USERNAME", username)
            _set_user_env("PDU_ENCRYPTED_PASS", enc)
        except Exception as e:
            messagebox.showerror("Registry error", f"Could not set environment variables:\n{e}")
            return

        self._set_status("Saved. Restart PowerSplitter.exe to apply.")
        messagebox.showinfo(
            "Done",
            f"CSV written to:\n{csv_path}\n\n"
            "Environment variables updated:\n"
            "  PDU_MAPPING_PATH\n  PDU_USERNAME\n  PDU_ENCRYPTED_PASS\n\n"
            "Restart PowerSplitter.exe to apply.",
        )

    def _set_status(self, msg):
        self.status_var.set(msg)
        self.after(6000, lambda: self.status_var.set("Ready"))


if __name__ == "__main__":
    app = PDUConfigurator()
    app.mainloop()



def _set_user_env(name, value):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)


def _get_user_env(name):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value
    except FileNotFoundError:
        return ""


# --- iConsole MCP HTTP client ---

_ICONSOLE_MCP_URL = "https://iconsole-mcp.intel.com/mcp/"
_ICONSOLE_APIKEY_REG = "ICONSOLE_API_KEY"
# read-only key for iConsole inventory lookups
_ICONSOLE_DEFAULT_KEY = ("hMUzSIyDtbdvgRnYEmFWcdFDtJln4eyyKKfF_GhbrCz2tpF_eSFyMnfw4w0Yrex7g"
                         "uOAN_LZw_cbziFeJYhoiV3wh6H0fWDAnqy4taxx1kS4ehrolPjwLck1tXNTbWbz")

def _parse_mcp_response(resp):
    """Extract JSON from an MCP HTTP response (plain JSON or SSE stream)."""
    raw = resp.text.strip()
    if not raw:
        return {}, resp.headers
    ct = resp.headers.get("content-type", "")
    if "text/event-stream" in ct or raw.startswith(("data:", "event:")):
        for line in raw.splitlines():
            if line.startswith("data: "):
                chunk = line[6:].strip()
                if chunk and chunk != "[DONE]":
                    return json.loads(chunk), resp.headers
        return {}, resp.headers
    try:
        return json.loads(raw), resp.headers
    except json.JSONDecodeError:
        # Surface the actual server response so the user can diagnose auth/redirect issues
        preview = raw[:300].replace("\n", " ")
        raise Exception(f"HTTP {resp.status_code} — server returned non-JSON:\n{preview}")


def _mcp_call(api_key, tool_name, arguments):
    """MCP Streamable-HTTP: initialize → initialized → tools/call.
    Uses AuthBase so the Bearer token is re-applied after every redirect."""
    if not _HAS_REQUESTS:
        raise Exception("'requests' package not found. Run: pip install requests")

    class _Bearer(_requests.auth.AuthBase):
        def __call__(self, r):
            r.headers["Authorization"] = f"Bearer {api_key}"
            return r

    session = _requests.Session()
    session.auth = _Bearer()          # re-applied after every redirect automatically
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    })

    def _post(payload):
        # Manual redirect loop so POST method and Authorization header are never dropped
        url = _ICONSOLE_MCP_URL
        for _ in range(10):
            resp = session.post(url, json=payload,
                                verify=False, timeout=30, allow_redirects=False)
            if resp.status_code in (301, 302, 307, 308):
                location = resp.headers.get("Location", "")
                if location.startswith("http"):
                    url = location
                else:
                    from urllib.parse import urljoin
                    url = urljoin(url, location)
                print(f"[DEBUG] Redirect → {url}")
                continue
            break
        resp.raise_for_status()
        return _parse_mcp_response(resp)

    # initialize — capture session ID if server issues one
    _, init_headers = _post({
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "PDUConfigurator", "version": "1.0"}}
    })
    sid = init_headers.get("Mcp-Session-Id") or init_headers.get("mcp-session-id")
    if sid:
        session.headers["Mcp-Session-Id"] = sid

    # initialized notification (fire-and-forget)
    try:
        _post({"jsonrpc": "2.0", "method": "notifications/initialized"})
    except Exception:
        pass

    result, _ = _post({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments}
    })
    return result


def _extract_text_from_mcp(result):
    """Pull the text payload out of a standard MCP tools/call result."""
    content = result.get("result", {}).get("content", [])
    for item in content:
        if item.get("type") == "text":
            return item["text"]
    return None


def _find_pdu_fields(obj, depth=0):
    """
    Recursively search a dict/list for fields that look like a PDU IP
    and outlet/port numbers.  Returns (ip, outlets_str) or (None, None).
    """
    if depth > 10 or not isinstance(obj, (dict, list)):
        return None, None
    items = obj.items() if isinstance(obj, dict) else enumerate(obj)
    ip, outlets = None, None
    for key, val in items:
        key_s = str(key).lower()
        val_s = str(val) if not isinstance(val, (dict, list)) else ""
        # Look for PDU IP
        if not ip and any(t in key_s for t in ("pdu_ip", "pdu ip", "address", "pdu_address")):
            if re.match(r"\d{1,3}(\.\d{1,3}){3}", val_s):
                ip = val_s.strip()
        # Look for outlets
        if not outlets and any(t in key_s for t in ("outlet", "port_index", "pdu_port", "target")):
            outlets = val_s.strip()
        # Recurse into nested structures
        if isinstance(val, (dict, list)):
            sub_ip, sub_out = _find_pdu_fields(val, depth + 1)
            ip = ip or sub_ip
            outlets = outlets or sub_out
    return ip, outlets


class PDUConfigurator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PowerSplitter PDU Configurator")
        self.resizable(False, False)

        self.csv_path_var = tk.StringVar()
        self.ip_var = tk.StringVar()
        self.outlets_var = tk.StringVar()
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.show_pass = tk.BooleanVar(value=False)
        self.apikey_var = tk.StringVar()
        self.show_key = tk.BooleanVar(value=False)
        self.ic_status_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Ready")

        self._load_existing()
        self._build_ui()

    def _load_existing(self):
        path = _get_user_env("PDU_MAPPING_PATH") or os.environ.get("PDU_MAPPING_PATH", "")
        self.csv_path_var.set(path)
        self.username_var.set(_get_user_env("PDU_USERNAME") or os.environ.get("PDU_USERNAME", ""))
        enc = _get_user_env("PDU_ENCRYPTED_PASS") or os.environ.get("PDU_ENCRYPTED_PASS", "")
        if enc:
            try:
                self.password_var.set(base64.b64decode(enc).decode("utf-8"))
            except Exception:
                pass
        self.apikey_var.set(_get_user_env(_ICONSOLE_APIKEY_REG) or _ICONSOLE_DEFAULT_KEY)

        csv_file = path if os.path.isfile(path) else os.path.join(path, "PDUMapping.csv")
        if os.path.isfile(csv_file):
            try:
                with open(csv_file, newline="") as f:
                    for row in csv.DictReader(f):
                        # load only the row matching this host
                        if row["HostName"] == socket.gethostname():
                            self.ip_var.set(row["PduNameOrIP"])
                            self.outlets_var.set(row["TargetOutlet"])
                            break
            except Exception:
                pass

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # --- CSV file ---
        f_csv = ttk.LabelFrame(self, text="CSV File", padding=8)
        f_csv.grid(row=0, column=0, padx=12, pady=(12, 4), sticky="ew")
        f_csv.columnconfigure(1, weight=1)
        ttk.Label(f_csv, text="Path:").grid(row=0, column=0, sticky="w")
        ttk.Entry(f_csv, textvariable=self.csv_path_var, width=46).grid(row=0, column=1, padx=6, sticky="ew")
        ttk.Button(f_csv, text="Browse", command=self._browse).grid(row=0, column=2)

        # --- iConsole ---
        f_ic = ttk.LabelFrame(self, text="iConsole Auto-Fetch", padding=8)
        f_ic.grid(row=1, column=0, padx=12, pady=4, sticky="ew")
        f_ic.columnconfigure(1, weight=1)

        ttk.Label(f_ic, text="API Key:").grid(row=0, column=0, sticky="w", **pad)
        self.key_entry = ttk.Entry(f_ic, textvariable=self.apikey_var, width=38, show="*")
        self.key_entry.grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Checkbutton(f_ic, text="Show", variable=self.show_key,
                        command=lambda: self.key_entry.config(show="" if self.show_key.get() else "*")
                        ).grid(row=0, column=2, padx=2)
        ttk.Button(f_ic, text="Get Key ↗",
                   command=lambda: self._open_url("https://console.intel.com/preferences/api-key")
                   ).grid(row=0, column=3, padx=4)

        ttk.Label(f_ic, text="Status:").grid(row=1, column=0, sticky="w", padx=10)
        ttk.Label(f_ic, textvariable=self.ic_status_var, foreground="#1a6aa0",
                  wraplength=420, justify="left").grid(row=1, column=1, columnspan=3, sticky="w", padx=6)

        # --- PDU mapping ---
        f_pdu = ttk.LabelFrame(self, text="PDU Mapping", padding=8)
        f_pdu.grid(row=2, column=0, padx=12, pady=4, sticky="ew")
        f_pdu.columnconfigure(1, weight=1)

        ttk.Label(f_pdu, text="Hostname:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Label(f_pdu, text=socket.gethostname(), foreground="#555").grid(row=0, column=1, sticky="w", **pad)
        self.fetch_btn = ttk.Button(f_pdu, text="Fetch from iConsole", command=self._fetch_iconsole)
        self.fetch_btn.grid(row=0, column=2, padx=6)

        ttk.Label(f_pdu, text="PDU IP:").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(f_pdu, textvariable=self.ip_var, width=22).grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(f_pdu, text="Outlets:").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(f_pdu, textvariable=self.outlets_var, width=22).grid(row=2, column=1, sticky="w", **pad)
        ttk.Label(f_pdu, text="e.g.  10  or  10;11;12  or  8-12", foreground="gray").grid(row=2, column=2, sticky="w")

        # --- Credentials ---
        f_cred = ttk.LabelFrame(self, text="PDU SSH Credentials", padding=8)
        f_cred.grid(row=3, column=0, padx=12, pady=4, sticky="ew")

        ttk.Label(f_cred, text="Username:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(f_cred, textvariable=self.username_var, width=22).grid(row=0, column=1, sticky="w", **pad)

        ttk.Label(f_cred, text="Password:").grid(row=0, column=2, sticky="w", padx=(20, 8))
        self.pass_entry = ttk.Entry(f_cred, textvariable=self.password_var, width=22, show="*")
        self.pass_entry.grid(row=0, column=3, sticky="w", **pad)
        ttk.Checkbutton(f_cred, text="Show", variable=self.show_pass,
                        command=lambda: self.pass_entry.config(show="" if self.show_pass.get() else "*")
                        ).grid(row=0, column=4, sticky="w")

        # --- Bottom bar ---
        bottom = ttk.Frame(self)
        bottom.grid(row=4, column=0, padx=12, pady=(4, 12), sticky="ew")
        ttk.Button(bottom, text="Save & Apply", command=self._save_all).pack(side="left")
        ttk.Label(bottom, textvariable=self.status_var, foreground="blue").pack(side="left", padx=12)

    # --- iConsole fetch (background thread) ---

    def _open_url(self, url):
        import subprocess
        subprocess.Popen(["rundll32", "url.dll,FileProtocolHandler", url])

    def _fetch_iconsole(self):
        api_key = self.apikey_var.get().strip()
        if not api_key:
            messagebox.showwarning("API Key required",
                                   "Enter your iConsole API key first.\nGet one at: console.intel.com/preferences/api-key")
            return
        self.fetch_btn.config(state="disabled")
        self.ic_status_var.set("Connecting to iConsole…")
        threading.Thread(target=self._do_fetch, args=(socket.gethostname(), api_key), daemon=True).start()

    def _do_fetch(self, hostname, api_key):
        try:
            # Probe the endpoint first to catch auth/redirect issues early
            probe = _requests.get(
                _ICONSOLE_MCP_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                verify=False, timeout=15, allow_redirects=True
            )
            if probe.status_code not in (200, 405):  # 405 = GET not allowed, that's fine
                preview = probe.text.strip()[:200].replace("\n", " ")
                raise Exception(f"HTTP {probe.status_code} on probe: {preview}")

            result = _mcp_call(api_key, "syst_get_detailed_system_inventory_from_iconsole_database",
                               {"system_id": hostname})
            if "error" in result:
                raise Exception(result["error"].get("message", str(result["error"])))

            # isError means the tool ran but the backend returned an error
            if result.get("result", {}).get("isError"):
                err_text = _extract_text_from_mcp(result) or "unknown tool error"
                raise Exception(f"iConsole tool error: {err_text}")

            text = _extract_text_from_mcp(result)
            print(f"[DEBUG] raw result: {json.dumps(result)[:500]}")
            print(f"[DEBUG] extracted text repr: {repr(text)}")

            if not text or not str(text).strip():
                raise Exception("Empty response — system may not be registered in iConsole.")

            try:
                data = json.loads(text.strip()) if isinstance(text, str) else text
            except json.JSONDecodeError:
                raise Exception(f"iConsole returned non-JSON text: {repr(text[:200])}")
            ip, outlets = _find_pdu_fields(data)

            def _update():
                if ip:
                    self.ip_var.set(ip)
                    self.outlets_var.set(outlets or "")
                    self.ic_status_var.set(
                        f"Found — IP: {ip}  Outlets: {outlets or '(not detected, fill manually)'}")
                else:
                    keys = list(data.keys())[:8] if isinstance(data, dict) else []
                    self.ic_status_var.set(
                        f"System found but no PDU fields auto-detected. "
                        f"Fields returned: {', '.join(keys)}. Fill IP/Outlets manually.")
            self.after(0, _update)

        except Exception as exc:
            msg = str(exc)
            traceback.print_exc()  # full trace to terminal for diagnosis
            self.after(0, lambda: self.ic_status_var.set(f"Error: {msg[:140]}"))
        finally:
            self.after(0, lambda: self.fetch_btn.config(state="normal"))

    def _browse(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="PDUMapping.csv",
            title="Choose CSV file location",
        )
        if path:
            self.csv_path_var.set(path)

    def _save_all(self):
        csv_path = self.csv_path_var.get().strip()
        ip = self.ip_var.get().strip()
        outlets = self.outlets_var.get().strip()
        username = self.username_var.get().strip()
        password = self.password_var.get()

        if not csv_path:
            messagebox.showerror("Missing", "Specify a CSV file path.")
            return
        if not ip or not outlets:
            messagebox.showerror("Missing", "PDU IP and Outlets are required.")
            return
        if not username or not password:
            messagebox.showerror("Missing", "Username and password are required.")
            return

        if os.path.isdir(csv_path):
            csv_path = os.path.join(csv_path, "PDUMapping.csv")
            self.csv_path_var.set(csv_path)

        try:
            os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
            with open(csv_path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["HostName", "PduNameOrIP", "TargetOutlet"])
                w.writerow([socket.gethostname(), ip, outlets])
        except Exception as e:
            messagebox.showerror("Save error", f"Could not write CSV:\n{e}")
            return

        enc = base64.b64encode(password.encode("utf-8")).decode("utf-8")
        try:
            _set_user_env("PDU_MAPPING_PATH", csv_path)
            _set_user_env("PDU_USERNAME", username)
            _set_user_env("PDU_ENCRYPTED_PASS", enc)
            api_key = self.apikey_var.get().strip()
            if api_key:
                _set_user_env(_ICONSOLE_APIKEY_REG, api_key)
        except Exception as e:
            messagebox.showerror("Registry error", f"Could not set environment variables:\n{e}")
            return

        self._set_status("Saved. Restart PowerSplitter.exe to apply.")
        messagebox.showinfo(
            "Done",
            f"CSV written to:\n{csv_path}\n\n"
            "Environment variables updated:\n"
            "  PDU_MAPPING_PATH\n  PDU_USERNAME\n  PDU_ENCRYPTED_PASS\n\n"
            "Restart PowerSplitter.exe to apply.",
        )

    def _set_status(self, msg):
        self.status_var.set(msg)
        self.after(6000, lambda: self.status_var.set("Ready"))


if __name__ == "__main__":
    app = PDUConfigurator()
    app.mainloop()
