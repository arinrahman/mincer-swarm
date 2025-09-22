#!/usr/bin/env python3
import subprocess, time, re, argparse, os, sys
LDMS_LS = "/opt/ovis/sbin/ldms_ls"
# Header lines look like:
#   client1/vmmon: consistent, last update: ...
HEAD_RE = re.compile(r'^([^\s:]+):\s+(consistent|inconsistent)\b.*$', re.M)
def run_ldms_ls(host: str, port: int) -> str:
   try:
       r = subprocess.run(
           [LDMS_LS, "-l", "-x", "sock", "-h", host, "-p", str(port)],
           capture_output=True, text=True
       )
       return r.stdout or ""
   except Exception as e:
       return f"[ERROR] failed to run {LDMS_LS}: {e}\n"
def iter_blocks(raw: str):
   """Yield (dataset_path, consistency, block_text)."""
   if not raw:
       return
   heads = [(m.start(), m.end(), m.group(1), m.group(2)) for m in HEAD_RE.finditer(raw)]
   for i, (s, e, ds, ok) in enumerate(heads):
       end = heads[i+1][0] if i+1 < len(heads) else len(raw)
       yield ds, ok, raw[e:end]
def split_node_plugin(dataset_path: str):
   """
   Try to split into (node, plugin-ish label) for display.
   Examples:
     'client3/vmmon'         -> ('client3', 'vmmon')
     'client1/netmon/eth0'   -> ('client1', 'netmon/eth0')
     'vmmon_instance'        -> ('-', 'vmmon_instance')
   """
   ds = dataset_path.split(':', 1)[0]
   parts = ds.split('/')
   if len(parts) >= 2:
       return parts[0], "/".join(parts[1:])
   return "-", ds
def main():
   ap = argparse.ArgumentParser(
       description="Live LDMS viewer: prints datasets each second (no storage)."
   )
   ap.add_argument("--host", default="localhost", help="ldmsd host (default: localhost)")
   ap.add_argument("--port", default=10001, type=int, help="ldmsd port (default: 10001)")
   ap.add_argument("--interval", "-i", default=1.0, type=float, help="refresh interval seconds (default: 1)")
   ap.add_argument("--match", "-m", default="", help="show only datasets whose path matches this regex")
   ap.add_argument("--include-inconsistent", action="store_true", help="include inconsistent sets")
   ap.add_argument("--lines", "-n", default=30, type=int, help="max metric lines to show per dataset (default: 30)")
   ap.add_argument("--raw", action="store_true", help="print raw ldms_ls output (no parsing)")
   args = ap.parse_args()
   filt = re.compile(args.match) if args.match else None
   try:
       while True:
           ts = time.strftime("%Y-%m-%d %H:%M:%S")
           raw = run_ldms_ls(args.host, args.port)
           # clear screen
           sys.stdout.write("\x1b[2J\x1b[H")
           print(f"📡 LDMS Live View  host={args.host}  port={args.port}  interval={args.interval}s   {ts}")
           print("-" * 100)
           if args.raw:
               # Just dump the raw output (handy for debugging)
               print(raw if raw else "[WARN] No output from ldms_ls")
               time.sleep(args.interval)
               continue
           if not raw.strip():
               print("[WARN] No output from ldms_ls (is ldmsd on the aggregator listening on that port?)")
               time.sleep(args.interval)
               continue
           shown = 0
           for ds, ok, block in iter_blocks(raw):
               if ok != "consistent" and not args.include_inconsistent:
                   continue
               if filt and not filt.search(ds):
                   continue
               node, label = split_node_plugin(ds)
               hdr = f"{ds}  [{ok}]"
               print(hdr)
               print("-" * len(hdr))
               # print first N metric lines from this block
               lines = [ln for ln in block.strip().splitlines() if ln.strip()]
               for ln in lines[:args.lines]:
                   print(ln)
               if len(lines) > args.lines:
                   print(f"... ({len(lines) - args.lines} more lines)")
               print("")  # spacer
               shown += 1
           if shown == 0:
               msg = "[INFO] Nothing matched your filters." if filt or not args.include_inconsistent else "[INFO] No datasets found."
               print(msg)
           time.sleep(args.interval)
   except KeyboardInterrupt:
       print("\n🛑 Stopped.")
if __name__ == "__main__":
   main()
