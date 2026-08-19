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
