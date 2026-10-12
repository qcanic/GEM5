"""Run hosted raw-fence checks; shared NEMU and CoreMark are unavailable."""

import json
from pathlib import Path
import subprocess


OUT = Path("m5out/fork-ci")
CASES = [
    ("fence-default", "fence_i_raw.bin", [], 0, 0),
    (
        "fence-enabled",
        "fence_i_raw.bin",
        ["--enable-context-flush"],
        1,
        516,
    ),
    (
        "fence-zero-latency",
        "fence_i_raw.bin",
        ["--enable-context-flush", "--flush-latency=0"],
        1,
        0,
    ),
    (
        "fence-wrong-path",
        "fence_i_wrong_path.bin",
        ["--enable-context-flush"],
        0,
        0,
    ),
]


def final_stats(path):
    final = None
    active = False
    for line in path.read_text().splitlines():
        if line.startswith("---------- Begin Simulation Statistics"):
            current = {}
            active = True
        elif line.startswith("---------- End Simulation Statistics"):
            final = current
            active = False
        elif active:
            fields = line.split()
            if len(fields) >= 2:
                try:
                    current[fields[0]] = float(fields[1])
                except ValueError:
                    pass
    assert final is not None and not active, "Incomplete statistics"
    return final


results = []
for name, image, extra, flushes, window in CASES:
    directory = OUT / name
    directory.mkdir(parents=True, exist_ok=True)
    command = [
        "./build/RISCV/gem5.opt",
        f"--outdir={directory}",
        "configs/example/kmhv3.py",
        "--raw-cpt",
        f"--generic-rv-cpt=util/bpu_flush/{image}",
        "--disable-difftest",
        "--mem-type=DDR4_2400_8x8",
        *extra,
    ]
    with (directory / "launcher.log").open("w") as log:
        proc = subprocess.run(
            command, stdout=log, stderr=subprocess.STDOUT, timeout=600
        )
    log = (directory / "launcher.log").read_text(errors="replace")
    assert proc.returncode == 0, (name, proc.returncode)
    assert "m5_exit instruction encountered" in log, name
    assert not any(s in log for s in ["panic:", "fatal:"]), name
    stats = final_stats(directory / "stats.txt")
    prefix = "system.cpu.branchPred."
    assert stats[prefix + "bpuFlushes"] == flushes, name
    assert stats[prefix + "bpuFlushStallCycles"] == window, name
    assert stats[prefix + "bpuFlushBubbles"] == window, name
    for component in [
        "ubtb",
        "abtb",
        "microtage",
        "mbtb",
        "tage",
        "ras",
        "ittage",
        "mgsc",
    ]:
        assert (
            stats[prefix + "bpuComponentFlushes::" + component] == flushes
        ), (name, component)
    predictions = stats[prefix + "bpuFlushUntakenPredictions"]
    assert predictions > 0 if window else predictions == 0, name
    row = dict(
        name=name,
        command=command,
        passed=True,
        difftest=False,
        flushes=flushes,
        window_cycles=window,
        untaken_predictions=predictions,
    )
    results.append(row)
    (OUT / "smoke-summary.json").write_text(
        json.dumps(results, indent=2) + "\n"
    )
    print(json.dumps(row), flush=True)
