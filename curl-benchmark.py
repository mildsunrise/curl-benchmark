#!/usr/bin/python3
# Interesting args to pass:
#   --tcp-nodelay --http2 --false-start --compressed
# Own options:
#   --random-path --random-query --columns= --color --fail
# FIXME: parse URL, manipulate columns depending on it
# FIXME: absolute dev, also use big_fallback

import sys
import time
import subprocess
import math
from optparse import OptionParser

# Option parsing
usage = 'Usage: %prog [options] <URL>\n       %prog [options] -- [curl options] <URL>'
parser = OptionParser(usage=usage)
parser.add_option("-n", "--number", type="int", dest="n",
    help="exit after N requests (default: unlimited)")
parser.add_option("-r", "--report", action="store_true", dest="report", default=False,
    help="only print final report")
parser.add_option("-s", "--sleep", type="float", dest="sleep", default=0.3,
    help="how much to sleep between requests, in seconds")

(options, args) = parser.parse_args()
if len(args) < 1:
    print("Error: URL was not passed", file=sys.stderr)
    exit(2)
url = args.pop()
curl_args = args

# Formatting stuff
def colorize(color=None, foreground=True):
    idx = 9; post = ""
    if type(color) is int and 0 <= color < 8: idx = color
    if type(color) is tuple: idx, post = 8, "2;%d;%d;%d" % color
    return "\x1b[%d%d%sm" % (3 if foreground else 4, idx, post)
colorized = lambda color, func: lambda s, l: colorize(color) + func(s, l) + colorize()

format_time = lambda ms: ("%d  " % ms if type(ms) is None else "%.1lf" % ms)
big_fallback = lambda s, l: "BIG  " if len(s) > l else s
time_metric_col_len = lambda label: max(5, max(map(len, label.splitlines())))
time_metric_col = lambda i, label, color: {
    "length": time_metric_col_len(label),
    "render": colorized(color, str.rjust),
    "label": label,
    "value": lambda x: big_fallback(format_time(x["metrics"][i]), time_metric_col_len(label)),
    "dev_value": lambda x: "%.1f%%" % (x["metrics"][i] * 100),
}
time_column_data = [
    ("DNS\nlookup", 6),
    ("TCP\nconnect", 3),
    ("SSL\nhandshake", 5),
    ("Request\nsent", 4),
    ("  TTFB", 2),
    ("Content\ndownload", 4),
    (" Total", 8),
]
time_columns = [ time_metric_col(i, *args) for i, args in enumerate(time_column_data) ]

colspacing = "  "
first_column = {
    "length": 9, "render": str.rjust, "label": "Code", "value": lambda x: x["first"]
}
columns = [ first_column ] + time_columns
ellipsis = lambda text, l: text[:l-1] + "\u2026" if len(text) > l else text
render_row = lambda data: colspacing.join(
    c["render"](ellipsis(text, c["length"]), c["length"]) for text, c in zip(data, columns))
row_length = sum(col["length"] for col in columns) + len(colspacing) * (len(columns)-1)

# Print heading rows
def print_heading():
    labels = [ col["label"].splitlines() for col in columns ]
    heading_lines = max(map(len, labels))
    for label in labels:
        while len(label) < heading_lines:
            label.insert(0, "")
    print("\x1b[1m" + "\n".join(render_row( label[i] for label in labels ) for i in range(heading_lines)) + "\x1b[m")

if not options.report:
    print_heading()
    sys.stdout.flush()

# Calling curl
records = []
requests = 0

def call_curl(url):
    time_metrics = ["namelookup", "connect", "appconnect", "pretransfer", "starttransfer", "total"]
    curl_vars = [ "http_code" ] + [ "time_"+n for n in time_metrics ]
    format_string = "\\n".join("%%{%s}" % v for v in curl_vars)
    args = ["curl", "-sSo", "/dev/null", "-w", format_string] + curl_args + [url]
    try:
        output = subprocess.check_output(args, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as err:
        fail_lines = filter(lambda x: x.startswith("curl"), err.output.decode("utf-8").splitlines())
        print("FAIL (%d): %s" % (err.returncode, ", ".join(fail_lines)))
        return
    vars = dict(zip(curl_vars, output.decode("ascii").splitlines()))
    last_metric = 0
    metrics = []
    for metric in time_metrics:
        metric = int(round(float(vars["time_"+metric].replace(",", "."))*1000))
        if metric == 0: metric = last_metric
        metrics.append(metric - last_metric)
        last_metric = metric
    metrics.append(last_metric) # now, last_metric contains "total"

    records.append(metrics)
    render = { "metrics": metrics, "first": vars["http_code"] }
    if options.report:
        tag_pending = lambda pending: str(requests+1).rjust(len(pending)) + "/" + pending
        tag = requests+1 if options.n is None else tag_pending(str(options.n))
        print("Request [%s], failures %d" % (tag, requests + 1 - len(records)), end="\r")
    else:
        print(render_row( col["value"](render) for col in columns ))

try:
    while options.n is None or requests < options.n:
        call_curl(url)
        requests += 1
        sys.stdout.flush()
        time.sleep(options.sleep)
except KeyboardInterrupt as err:
    pass
print("\x1b[2K")

# Print stats
if not records:
    print("No samples captured, not showing stats :(")
    exit(1)

if options.report: print_heading()
avg = lambda x: sum(x) / len(records)
rms = lambda x: math.sqrt(avg(n**2 for n in x))
dev = lambda x: (lambda a: rms(n - a for n in x) / (a or 1))(avg(x))
med = lambda x: sorted(x)[len(x) // 2]
aggregation_functions = [("min:", min), ("avg:", avg), ("med:", med), ("max:", max), ("dev:", dev)]
for label, func in aggregation_functions:
    metrics = [float(func(x)) for x in zip(*records)]
    render = { "metrics": metrics, "first": label }
    boldIf = lambda s, b: "\x1b[1m%s\x1b[m" % s if b else s
    rf = "dev_value" if func is dev else "value"
    print(boldIf(render_row( (col[rf] if rf in col else col["value"])(render) for col in columns ), func is avg))
print(("requests: %d    samples: %d    failures: %d" % (requests, len(records), requests - len(records))).center(row_length))
print()
