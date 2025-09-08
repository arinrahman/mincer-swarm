# cypapi_ldms_multi.py
import subprocess, time, os, csv, re
# Try to import CyPAPI; if present, we’ll attach the single entry-point to it.
try:
   import cypapi.cypapi as CyPAPI
except Exception:
   CyPAPI = None
# ---- Defaults (tweak if needed) ----
LDMS_LS_PATH_DEFAULT = "/opt/ovis/sbin/ldms_ls"
LDMSD_HOST_DEFAULT   = "localhost"
LDMSD_PORT_DEFAULT   = "412"
OUTFILES_DEFAULT = {
   "procnetdev":    "/data/ldms_procnetdev_full.csv",
   "meminfo":       "/data/ldms_meminfo_full.csv",
   "vmstat":        "/data/ldms_vmstat_full.csv",
   "loadavg":       "/data/ldms_loadavg_full.csv",
   "procdiskstats": "/data/ldms_procdiskstats_full.csv",
}
# ---- Regex helpers ----
# Header lines look like:
#   netmon_instance/eth2: consistent, last update: ...
#   memmon_instance: consistent, last update: ...
_HEAD_RE = re.compile(r'^([^\s:]+):\s+consistent\b.*$', re.M)
# Metric rows look like:
#   D u64 rx_bytes 123
#   D f32 reads_comp.rate#sda 0.000000
#   D char[] device "eth2"
# Allow names with letters/digits/_ . # and quotes for values; numbers may be int or float
_KV_RE = re.compile(
   r'^[ \t]*[MD]\s+\w+(?:\[\])?\s+([A-Za-z0-9_.#]+)\s+(".*?"|-?\d+(?:\.\d+)?)\s*$',
   re.M
)
def _run_ldms_ls(path, host, port):
   try:
       r = subprocess.run(
           [path, "-l", "-x", "sock", "-h", host, "-p", str(port)],
           capture_output=True, text=True
       )
       return r.stdout.strip()
   except Exception as e:
       print(f"[ERROR] ldms_ls failed: {e}")
       return ""
def _iter_blocks(raw_text):
   """
   Yield (dataset_path, block_text) for each dataset in the ldms_ls output.
   dataset_path examples: 'netmon_instance/eth2', 'memmon_instance'
   """
   if not raw_text:
       return
   heads = [(m.start(), m.end(), m.group(1)) for m in _HEAD_RE.finditer(raw_text)]
   for i, (s, e, ds) in enumerate(heads):
       end = heads[i+1][0] if i+1 < len(heads) else len(raw_text)
       yield ds, raw_text[e:end]
def _parse_block(ds_path, text):
   """
   Parse one dataset block into a dict; include dataset and iface (if any).
   """
   row = {"dataset": ds_path}
   # iface is the part after the first '/' (e.g., netmon_instance/eth2)
   if '/' in ds_path:
       base, iface = ds_path.split('/', 1)
       row["instance"] = base
       row["iface"] = iface
   else:
       row["instance"] = ds_path
       row["iface"] = ""  # keep column consistent across CSVs
   for k, v in _KV_RE.findall(text or ""):
       if v.startswith('"') and v.endswith('"'):
           v = v[1:-1]
       row[k] = v
   return row
def _plugin_name_from_dataset(dataset_path: str):
   """
   Map dataset_path (e.g., 'netmon_instance/eth2') to a plugin key.
   Uses your exact instance names from ldms_all.conf.
   """
   ds = dataset_path.split(':', 1)[0]
   base = ds.split('/', 1)[0].lower()
   if base in ("netmon_instance", "netstat_instance"):
       return "procnetdev"
   if base == "memmon_instance":
       return "meminfo"
   if base == "vmmon_instance":
       return "vmstat"
   if base == "loadavg_instance":
       return "loadavg"
   if base == "diskmon_instance":
       return "procdiskstats"
   # Fallback (shouldn’t happen with your conf)
   return base
def _ensure_header(file_path, keys):
   """
   Ensure CSV header exists. If file exists & non-empty, return existing header.
   Otherwise write header (ordered) and return it.
   """
   if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
       with open(file_path, "r", newline="") as fr:
           return next(csv.reader(fr))
   header = sorted(keys, key=lambda x: (x!="timestamp", x!="dataset", x!="instance", x!="iface", x))
   with open(file_path, "w", newline="") as f:
       csv.DictWriter(f, fieldnames=header).writeheader()
   return header
def CyPAPI_ldms_multi(
   interval=2,
   ldms_ls_path=LDMS_LS_PATH_DEFAULT,
   host=LDMSD_HOST_DEFAULT,
   port=LDMSD_PORT_DEFAULT,
   outfiles=None,
   clear_screen=True,
   show_attachment=True,
   pause_before_start=False,
):
   """
   Single entry-point:
     - fetch ldms_ls output
     - split into dataset blocks
     - map each block to a plugin (procnetdev, meminfo, vmstat, loadavg, procdiskstats)
     - append rows to that plugin’s CSV (headers fixed from first write per file)
     - loop every `interval` seconds
   """
   if outfiles is None:
       outfiles = OUTFILES_DEFAULT
   # Monkey-patch visibility (optional)
   if show_attachment and CyPAPI is not None:
       print("[CyPAPI] Before attach:", "CyPAPI_ldms_multi" in dir(CyPAPI))
       setattr(CyPAPI, "CyPAPI_ldms_multi", CyPAPI_ldms_multi)
       print("[CyPAPI] After attach :", "CyPAPI_ldms_multi" in dir(CyPAPI))
       if pause_before_start:
           input("Press Enter to start monitoring...")
   print("📡 Starting LDMS multi-plugin monitoring (Ctrl+C to stop)\n")
   # Cache header per outfile to avoid re-reading every time
   header_cache = {}
   try:
       while True:
           if clear_screen:
               os.system('clear')
           ts = time.strftime('%Y-%m-%d %H:%M:%S')
           print(f"🕒 Timestamp: {ts}")
           raw = _run_ldms_ls(ldms_ls_path, host, port)
           print(raw if raw else "[WARN] No output from ldms_ls (is ldmsd running & reachable?).")
           # Parse blocks → group rows by plugin
           rows_by_plugin = {}
           for ds, blk in _iter_blocks(raw):
               plugin = _plugin_name_from_dataset(ds)
               row = _parse_block(ds, blk)
               row["timestamp"] = ts
               rows_by_plugin.setdefault(plugin, []).append(row)
           # Write each plugin’s rows to its dedicated CSV
           for plugin, rows in rows_by_plugin.items():
               csv_path = outfiles.get(plugin, f"ldms_{plugin}_full.csv")
               # Determine header for this CSV
               if csv_path not in header_cache:
                   # Union of keys from this batch (dataset/instance/iface/timestamp + metrics)
                   key_union = set()
                   for r in rows:
                       key_union.update(r.keys())
                   header = _ensure_header(csv_path, key_union)
                   header_cache[csv_path] = header
               else:
                   header = header_cache[csv_path]
               with open(csv_path, "a", newline="") as f:
                   w = csv.DictWriter(f, fieldnames=header)
                   for r in rows:
                       w.writerow({h: r.get(h, "") for h in header})
           time.sleep(interval)
   except KeyboardInterrupt:
       print("\n🛑 Monitoring stopped.")
# Attach to CyPAPI so you can call CyPAPI.CyPAPI_ldms_multi()
if CyPAPI is not None:
   setattr(CyPAPI, "CyPAPI_ldms_multi", CyPAPI_ldms_multi)
if __name__ == "__main__":
   # Defaults align with your ldms_all.conf on port 412
   CyPAPI_ldms_multi()
