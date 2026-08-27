#!/usr/bin/env python3
"""
HWP to PDF batch converter using Allinpdf via headless Chrome CDP automation.
Supports single-file testing and recursive batch conversion with auto-resume, retries, and process recovery.
"""

import sys
import os
import time
import json
import socket
import struct
import base64
import urllib.request
import subprocess
import argparse
import tempfile
import shutil
from pathlib import Path

CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def discover_hwp_files(target: str) -> list[str]:
    target_path = Path(target).resolve()
    if target_path.is_file():
        if target_path.suffix.lower() in [".hwp", ".hwpx"]:
            return [str(target_path)]
        return []
    
    hwp_files = []
    for root, _, files in os.walk(target_path):
        for f in files:
            if f.lower().endswith((".hwp", ".hwpx")) and not f.startswith("~$"):
                hwp_files.append(os.path.join(root, f))
    return sorted(hwp_files)

def resolve_output_pdf_path(hwp_path: str, base_target: str, output_dir: str | None = None) -> str:
    hwp_p = Path(hwp_path).resolve()
    pdf_filename = hwp_p.stem + ".pdf"
    
    if output_dir is None:
        return str(hwp_p.parent / pdf_filename)
    
    base_p = Path(base_target).resolve()
    if base_p.is_file():
        return str(Path(output_dir).resolve() / pdf_filename)
    
    rel_parent = hwp_p.parent.relative_to(base_p)
    return str(Path(output_dir).resolve() / rel_parent / pdf_filename)

def validate_pdf(pdf_path: str) -> bool:
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) < 100:
        return False
    try:
        with open(pdf_path, "rb") as f:
            header = f.read(1024)
            return b"%PDF-" in header
    except Exception:
        return False

class SimpleWS:
    """Minimal WebSocket client for Chrome DevTools Protocol."""
    def __init__(self, url: str):
        _, rest = url.split("://", 1)
        host_port, path = rest.split("/", 1)
        host, port = host_port.split(":")
        self.sock = socket.create_connection((host, int(port)), timeout=15)
        key = base64.b64encode(os.urandom(16)).decode("utf-8")
        req = (
            f"GET /{path} HTTP/1.1\r\n"
            f"Host: {host_port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode("utf-8"))
        resp = self.sock.recv(4096)
        if b"101 " not in resp:
            raise ConnectionError(f"WS Handshake failed: {resp}")
        self.msg_id = 0

    def send(self, method: str, params: dict | None = None) -> int:
        self.msg_id += 1
        payload = json.dumps({"id": self.msg_id, "method": method, "params": params or {}}).encode("utf-8")
        length = len(payload)
        mask = os.urandom(4)
        header = bytearray([0x81])
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack(">H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack(">Q", length))
        header.extend(mask)
        masked_payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(header + masked_payload)
        return self.msg_id

    def recv(self, timeout: float = 10) -> dict | None:
        self.sock.settimeout(timeout)
        try:
            h = self.sock.recv(2)
            if not h:
                return None
            b1, b2 = h[0], h[1]
            masked = bool(b2 & 0x80)
            length = b2 & 0x7f
            if length == 126:
                length = struct.unpack(">H", self.sock.recv(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self.sock.recv(8))[0]
            mask = self.sock.recv(4) if masked else None
            data = bytearray()
            while len(data) < length:
                chunk = self.sock.recv(length - len(data))
                if not chunk:
                    break
                data.extend(chunk)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            return json.loads(data.decode("utf-8", errors="ignore"))
        except socket.timeout:
            return None

    def call(self, method: str, params: dict | None = None, timeout: float = 20) -> dict | None:
        mid = self.send(method, params)
        start = time.time()
        while time.time() - start < timeout:
            msg = self.recv(timeout=1.0)
            if msg and msg.get("id") == mid:
                return msg.get("result")
        return None

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass

class AllinpdfConverter:
    def __init__(self, user_data_dir: str | None = None, chrome_path: str = CHROME_PATH):
        self.chrome_path = chrome_path
        self.user_data_dir = user_data_dir or tempfile.mkdtemp(prefix="chrome_allinpdf_")
        self.proc = None

    def start(self):
        if self.proc is None:
            self.proc = subprocess.Popen([
                self.chrome_path,
                "--headless=new",
                "--remote-debugging-port=9222",
                "--no-first-run",
                "--no-default-browser-check",
                f"--user-data-dir={self.user_data_dir}"
            ])
            time.sleep(2)

    def stop(self):
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None
        shutil.rmtree(self.user_data_dir, ignore_errors=True)

    def restart(self):
        self.stop()
        self.user_data_dir = tempfile.mkdtemp(prefix="chrome_allinpdf_")
        self.start()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def convert_file(self, hwp_path: str, output_pdf_path: str, timeout_sec: int = 120) -> bool:
        abs_hwp = os.path.abspath(hwp_path)
        abs_out = os.path.abspath(output_pdf_path)
        os.makedirs(os.path.dirname(abs_out), exist_ok=True)
        file_size_mb = os.path.getsize(abs_hwp) / (1024 * 1024)
        dynamic_timeout = max(timeout_sec, int(file_size_mb * 5) + 60)

        target_id = None
        ws = None
        try:
            req = urllib.request.Request("http://127.0.0.1:9222/json/new?https://allinpdf.com/hwp-to-pdf", method="PUT")
            tab_info = json.loads(urllib.request.urlopen(req, timeout=10).read())
            ws_url = tab_info["webSocketDebuggerUrl"]
            target_id = tab_info["id"]

            ws = SimpleWS(ws_url)
            ws.call("Page.enable")
            ws.call("DOM.enable")
            ws.call("Network.enable")

            # 1. Page load
            time.sleep(3)
            doc = ws.call("DOM.getDocument")
            root_id = doc["root"]["nodeId"]
            node_res = ws.call("DOM.querySelector", {"nodeId": root_id, "selector": "input[type=file]"})
            if not node_res or "nodeId" not in node_res or node_res["nodeId"] == 0:
                print("  [-] Could not locate file input.")
                return False

            file_node_id = node_res["nodeId"]

            # 2. Upload file
            print(f"  [*] Uploading {os.path.basename(abs_hwp)} ({file_size_mb:.2f} MB)...")
            ws.call("DOM.setFileInputFiles", {"files": [abs_hwp], "nodeId": file_node_id})

            # 3. Wait for options page
            options_loaded = False
            upload_wait_sec = max(90, int(file_size_mb * 8) + 60)
            start_upload_wait = time.time()
            while time.time() - start_upload_wait < upload_wait_sec:
                time.sleep(1)
                res = ws.call("Runtime.evaluate", {"expression": "location.href"})
                url = res.get("result", {}).get("value", "") if res else ""
                if "pdf-converter-options" in url:
                    options_loaded = True
                    break
                elif "limited-wait" in url or "exception" in url:
                    print(f"  [-] Reached rate limit or error page: {url}")
                    return False

            if not options_loaded:
                print(f"  [-] Options page did not load in time (waited {upload_wait_sec}s).")
                return False

            # 4. Click OK (PDF is checked by default)
            time.sleep(1)
            ws.call("Runtime.evaluate", {"expression": "document.getElementById('ContentPlaceHolder1_m_btnStartFileConvert')?.click()"})

            # 5. Wait for download link
            download_url = None
            start_wait = time.time()
            while time.time() - start_wait < dynamic_timeout:
                time.sleep(2)
                res = ws.call("Runtime.evaluate", {"expression": """
                    (() => {
                        const dl = document.querySelector('a.btn_download, a[href*="download"], a[href*="Download"], #btnDownload, #ContentPlaceHolder1_btnDownload, .btn_blue');
                        const links = Array.from(document.querySelectorAll('a')).map(a => ({href: a.href, text: a.innerText}));
                        return JSON.stringify({
                            url: location.href,
                            dl: dl ? dl.href : null,
                            links: links.filter(l => l.href.includes('File_Download') || l.href.includes('.pdf'))
                        });
                    })()
                """})
                val = json.loads(res["result"]["value"]) if res and "result" in res else {}
                if val.get("dl"):
                    download_url = val["dl"]
                    break
                for l in val.get("links", []):
                    if "File_Download" in l.get("href", "") or "download" in l.get("href", "").lower():
                        download_url = l["href"]
                        break
                if download_url:
                    break

            if not download_url:
                print("  [-] Conversion timed out.")
                return False

            # 6. Download PDF
            cookies_res = ws.call("Network.getCookies")
            cookies = cookies_res.get("cookies", []) if cookies_res else []
            cookie_hdr = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

            dl_req = urllib.request.Request(download_url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Cookie": cookie_hdr,
                "Referer": val.get("url", "https://allinpdf.com/")
            })
            pdf_bytes = urllib.request.urlopen(dl_req, timeout=60).read()
            with open(abs_out, "wb") as f:
                f.write(pdf_bytes)

            if validate_pdf(abs_out):
                print(f"  [+] Saved & Validated: {os.path.basename(abs_out)} ({len(pdf_bytes):,} bytes)")
                return True
            else:
                print(f"  [-] Validation failed for {abs_out}")
                return False
        except Exception as e:
            print(f"  [-] Error during conversion: {e}")
            return False
        finally:
            if ws:
                ws.close()
            if target_id:
                try:
                    close_req = urllib.request.Request(f"http://127.0.0.1:9222/json/close/{target_id}", method="PUT")
                    urllib.request.urlopen(close_req, timeout=3)
                except Exception:
                    pass

def main():
    parser = argparse.ArgumentParser(description="Batch convert HWP/HWPX files to PDF via Allinpdf")
    parser.add_argument("target", help="Target HWP file or directory containing HWP files")
    parser.add_argument("--output-dir", "-o", default=None, help="Optional output directory (default: in-place next to HWP files)")
    parser.add_argument("--force", "-f", action="store_true", help="Force overwrite existing PDF files")
    parser.add_argument("--retries", "-r", type=int, default=2, help="Number of retries per file (default: 2)")
    parser.add_argument("--timeout", "-t", type=int, default=120, help="Base timeout in seconds (default: 120)")
    args = parser.parse_args()

    target_path = os.path.abspath(args.target)
    if not os.path.exists(target_path):
        print(f"Error: Target path does not exist: {target_path}")
        sys.exit(1)

    hwp_files = discover_hwp_files(target_path)
    if not hwp_files:
        print(f"No HWP files found in {target_path}")
        return

    print(f"Found {len(hwp_files)} HWP files in {target_path}")
    print(f"Output mode: {'Mirrored to ' + args.output_dir if args.output_dir else 'In-place (alongside .hwp)'}")

    success_cnt = 0
    skipped_cnt = 0
    failed_files = []

    with AllinpdfConverter() as converter:
        for idx, hwp_file in enumerate(hwp_files, 1):
            out_pdf = resolve_output_pdf_path(hwp_file, target_path, args.output_dir)
            rel_hwp = os.path.relpath(hwp_file, target_path) if os.path.isdir(target_path) else os.path.basename(hwp_file)
            file_sz_kb = os.path.getsize(hwp_file) / 1024

            if not args.force and validate_pdf(out_pdf):
                print(f"[{idx}/{len(hwp_files)}] [SKIPPED - Already converted] {rel_hwp}")
                skipped_cnt += 1
                success_cnt += 1
                continue

            print(f"[{idx}/{len(hwp_files)}] Converting: {rel_hwp} ({file_sz_kb:.1f} KB)...")
            success = False
            for attempt in range(1, args.retries + 2):
                if attempt > 1:
                    print(f"  [*] Retry attempt {attempt - 1}/{args.retries}...")
                    converter.restart()
                    time.sleep(3)
                
                success = converter.convert_file(hwp_file, out_pdf, timeout_sec=args.timeout)
                if success:
                    break

            if success:
                success_cnt += 1
            else:
                failed_files.append((hwp_file, out_pdf))
                print(f"  [!] Failed to convert {rel_hwp}")

            time.sleep(2)

    print("\n" + "=" * 50)
    print(f"Batch Conversion Finished!")
    print(f"Total: {len(hwp_files)} | Converted/Skipped: {success_cnt} | Failed: {len(failed_files)}")
    if failed_files:
        print(f"\nFailed files ({len(failed_files)}):")
        for src, dst in failed_files:
            print(f" - {src}")

if __name__ == "__main__":
    main()
