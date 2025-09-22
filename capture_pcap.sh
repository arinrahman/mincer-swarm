#!/usr/bin/env bash
set -euo pipefail
IF="eth0"            # interface to capture on
DUR=60               # seconds to capture
OUT_DIR="/pcap"      # where tar.gz will be written
FILTER=""            # optional tcpdump filter, e.g. 'port 412'
usage() {
 echo "Usage: $0 [-i iface] [-d seconds] [-o out_dir] [-f tcpdump_filter]"
 exit 1
}
while getopts "i:d:o:f:h" opt; do
 case "$opt" in
   i) IF="$OPTARG" ;;
   d) DUR="$OPTARG" ;;
   o) OUT_DIR="$OPTARG" ;;
   f) FILTER="$OPTARG" ;;
   h|*) usage ;;
 esac
done
NODE="${LDMS_NODE:-$(hostname)}"
TS="$(date +%Y%m%d-%H%M%S)"
WORK="${OUT_DIR}/${NODE}/tmp_${TS}"
FINAL_DIR="${OUT_DIR}/${NODE}"
PCAP="${WORK}/${NODE}_${IF}_${TS}.pcap"
TARBALL="${FINAL_DIR}/${NODE}_pcap_${IF}_${TS}.tar.gz"
mkdir -p "$WORK" "$FINAL_DIR"
# ensure tcpdump exists (best-effort install if missing)
if ! command -v tcpdump >/dev/null 2>&1; then
 echo "[INFO] tcpdump not found; attempting install..."
 if command -v apt-get >/dev/null 2>&1; then
   apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y tcpdump
 elif command -v apk >/dev/null 2>&1; then
   apk add --no-cache tcpdump
 elif command -v yum >/dev/null 2>&1; then
   yum install -y tcpdump
 else
   echo "[ERROR] Can't install tcpdump automatically. Please bake it into the image." >&2
   exit 1
 fi
fi
echo "[INFO] Capturing on ${IF} for ${DUR}s; node=${NODE}; out=${TARBALL}"
# -U: packet-buffered; timeout stops after DUR seconds
if [ -n "$FILTER" ]; then
 timeout --preserve-status "${DUR}s" tcpdump -i "$IF" -U -w "$PCAP" $FILTER
else
 timeout --preserve-status "${DUR}s" tcpdump -i "$IF" -U -w "$PCAP"
fi
tar -C "$WORK" -czf "$TARBALL" .
rm -rf "$WORK"
echo "[OK] Wrote: $TARBALL"