#!/usr/bin/env python3
import subprocess, time, csv, os

# List of events you want to check
PAPI_EVENTS = [
   "PAPI_CA_SNP", "PAPI_CA_SHR", "PAPI_CA_CLN", "PAPI_CA_ITV",
   "PAPI_L3_LDM", "PAPI_TLB_DM", "PAPI_TLB_IM", "PAPI_L1_LDM",
   "PAPI_L1_STM", "PAPI_L2_LDM", "PAPI_L2_STM", "PAPI_PRF_DM",
   "PAPI_MEM_WCY", "PAPI_STL_ICY", "PAPI_FUL_ICY", "PAPI_STL_CCY",
   "PAPI_FUL_CCY", "PAPI_BR_UCN", "PAPI_BR_CN", "PAPI_BR_TKN",
   "PAPI_BR_NTK", "PAPI_BR_MSP", "PAPI_BR_PRC", "PAPI_TOT_INS",
   "PAPI_LD_INS", "PAPI_SR_INS", "PAPI_BR_INS", "PAPI_RES_STL",
   "PAPI_TOT_CYC", "PAPI_LST_INS", "PAPI_L2_DCA", "PAPI_L3_DCA",
   "PAPI_L2_DCR", "PAPI_L3_DCR", "PAPI_L2_DCW", "PAPI_L3_DCW",
   "PAPI_L2_ICH", "PAPI_L2_ICA", "PAPI_L3_ICA", "PAPI_L2_ICR",
   "PAPI_L3_ICR", "PAPI_L2_TCA", "PAPI_L3_TCA", "PAPI_L2_TCR",
   "PAPI_L3_TCR", "PAPI_L2_TCW", "PAPI_L3_TCW", "PAPI_SP_OPS",
   "PAPI_DP_OPS", "PAPI_VEC_SP", "PAPI_VEC_DP", "PAPI_REF_CYC"
]

CSV_FILE = "papi_values.csv"

# Create CSV with header if missing
if not os.path.exists(CSV_FILE):
   with open(CSV_FILE, "w", newline="") as f:
       w = csv.writer(f)
       w.writerow(["timestamp", "event", "value"])

def read_event(ev):
   """Run papi_command_line for one event and return the value or None."""
   try:
       out = subprocess.check_output(
           ["papi_command_line", ev],
           stderr=subprocess.STDOUT,
           text=True
       )
       # Look for a number in output
       for line in out.splitlines():
           line = line.strip()
           if ev in line and ("ERR" not in line):
               # extract number
               parts = line.split()
               val = parts[-1]
               if val.isdigit():
                   return int(val)
       return None
   except:
       return None

def main():
   print("Collecting PAPI counters every second... (Ctrl+C to stop)")
   while True:
       ts = time.strftime("%Y-%m-%d %H:%M:%S")
       rows = []

       for ev in PAPI_EVENTS:
           val = read_event(ev)
           if val is not None:   # Only store real values
               rows.append((ts, ev, val))

       # Append to CSV
       if rows:
           with open(CSV_FILE, "a", newline="") as f:
               w = csv.writer(f)
               for r in rows:
                   w.writerow(r)

       time.sleep(1)

if __name__ == "__main__":
   try:
       main()
   except KeyboardInterrupt:
       print("\nStopped.")