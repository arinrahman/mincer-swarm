#!/usr/bin/env python3
import subprocess, time, re, argparse, os, sys, csv

LDMS_LS = "/opt/ovis/sbin/ldms_ls"

# Match dataset header lines
HEAD_RE = re.compile(r'^([^\s:]+):\s+(consistent|inconsistent)\b.*$', re.M)

def run_ldms_ls(host, port):
    try:
        r = subprocess.run(
            [LDMS_LS, "-l", "-x", "sock", "-h", host, "-p", str(port)],
            capture_output=True, text=True
        )
        return r.stdout or ""
    except:
        return ""

def iter_blocks(raw):
    """Yield (dataset_path, consistency, block_text)."""
    heads = [(m.start(), m.end(), m.group(1), m.group(2))
             for m in HEAD_RE.finditer(raw)]

    for i, (s, e, ds, ok) in enumerate(heads):
        end = heads[i+1][0] if i+1 < len(heads) else len(raw)
        yield ds, ok, raw[e:end]

def split_node_plugin(ds):
    # Extract node name ("client3" from "client3/netmon")
    ds2 = ds.split(':')[0]
    parts = ds2.split('/')
    return parts[0] if len(parts) > 1 else "unknown"

def ensure_csv(path):
    if not os.path.exists(path):
        with open(path, "w", newline="") as f:
            csv.writer(f).writerow(["timestamp", "dataset", "metric", "value"])

def parse_metric_line(line):
    # Metric lines look like:
    #   D u64 <metric> <value>
    parts = line.split()
    if len(parts) < 3:
        return None, None

    metric = parts[2]
    value = " ".join(parts[3:]) if len(parts) > 3 else ""
    return metric, value

def main():
    ap = argparse.ArgumentParser(description="LDMS live viewer + CSV logger")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=10001)
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--match", default="")
    ap.add_argument("--include-inconsistent", action="store_true")
    ap.add_argument("--outdir", default="logs")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    filt = re.compile(args.match) if args.match else None

    try:
        while True:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")

            raw = run_ldms_ls(args.host, args.port)

            # Clear screen
            sys.stdout.write("\x1b[2J\x1b[H")
            print(f"📡 LDMS Live View host={args.host} port={args.port} interval={args.interval}s  {ts}")
            print("-" * 100)

            if not raw.strip():
                print("[WARN] No LDMS output")
                time.sleep(args.interval)
                continue

            shown = 0

            for ds, ok, block in iter_blocks(raw):

                # apply filters
                if ok != "consistent" and not args.include_inconsistent:
                    continue
                if filt and not filt.search(ds):
                    continue

                # Determine node file
                node, _ = split_node_plugin(ds), None
                csv_path = f"{args.outdir}/{node}.csv"
                ensure_csv(csv_path)

                # Print dataset header
                print(f"\n{ds} [{ok}]")
                print("-" * (len(ds) + len(ok) + 4))

                # Store in CSV + print live
                with open(csv_path, "a", newline="") as f:
                    w = csv.writer(f)

                    for ln in block.splitlines():
                        ln = ln.strip()
                        if not ln or ln.startswith("M ") or ln.startswith("----"):
                            continue

                        if ln.startswith("D "):
                            metric, value = parse_metric_line(ln)
                            if metric:
                                # PRINT FULL LIVE METRIC LINE
                                print(f"{metric:40} {value}")
                                # LOG IT
                                w.writerow([ts, ds, metric, value])

                shown += 1

            if shown == 0:
                print("[INFO] No datasets matched filters")

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n🛑 Stopped.")

if __name__ == "__main__":
    main()
