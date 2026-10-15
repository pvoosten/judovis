"""Run a technique script in Blender without the UI and print a short summary of its reports.

    blender -b art_source/blender/judoka.blend --python tools/blender/run_technique.py -- ippon_seoi_nage
        [--draft]      skip motion.avoid (the slow per-frame arm search) while working on poses
        [--no-export]  do not write data/techniques/<technique>.yaml
        [--save]       save the .blend afterwards (not while the same file is open in Blender's UI)
        [--lines=5]    detail lines kept per report section in the summary

The full output goes to build/reports/<technique>.log; the summary keeps every report header and
the first --lines detail lines below it (the reports print the worst cases first).
A draft export is marked in the summary: run without --draft before committing the YAML.
"""
import contextlib
import importlib.util
import io
import os
import sys
import time

import bpy

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(TOOLS, "..", ".."))


def parse(argv):
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    names = [a for a in args if not a.startswith("--")]
    if len(names) != 1:
        sys.exit("usage: blender -b judoka.blend --python run_technique.py -- <technique> [--draft] "
                 "[--no-export] [--save] [--lines=N]")
    opts = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "") for a in args if a.startswith("--"))
    return names[0], opts


def summarize(log, lines):
    """Report headers (unindented lines) plus the first `lines` indented lines under each."""
    out, shown, hidden = [], 0, 0

    def flush():
        if hidden:
            out.append(f"  ... {hidden} more")

    for line in log.splitlines():
        if line.startswith(" "):
            if line.strip().startswith("..."):
                continue
            if shown < lines:
                out.append(line)
                shown += 1
            else:
                hidden += 1
        else:
            flush()
            out.append(line)
            shown = hidden = 0
    flush()
    return "\n".join(out)


def main():
    name, opts = parse(sys.argv)
    sys.path.insert(0, TOOLS)
    spec = importlib.util.spec_from_file_location(f"technique_{name}", os.path.join(TOOLS, "techniques", f"{name}.py"))
    technique = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(technique)  # imports (and reloads) the tools
    if "draft" in opts:
        technique.motion.avoid = lambda *a, **k: {}

    start = time.time()
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        technique.main(export="no-export" not in opts)
    log = buffer.getvalue()

    reports = os.path.join(ROOT, "build", "reports")
    os.makedirs(reports, exist_ok=True)
    path = os.path.join(reports, f"{name}.log")
    with open(path, "w", encoding="utf-8") as f:
        f.write(log)
    if "save" in opts:
        bpy.ops.wm.save_mainfile()

    print(summarize(log, int(opts.get("lines", 5))))
    mode = "DRAFT (no avoid) " if "draft" in opts else ""
    print(f"--- {mode}{name}: {time.time() - start:.0f} s; full log {os.path.relpath(path, ROOT)}"
          + ("; .blend saved" if "save" in opts else ""))


main()
