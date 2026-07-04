"""Render the vision-suite fixture images (deterministic PIL drawings, checked in as PNGs).

    uv run --group eval python -m suites.vision_assets.generate

Regenerate only when a task changes (and bump the suite VERSION if the change alters what
a model must read). Homelab-monitor flavor throughout: dashboards, terminals, charts —
the surfaces the future controller will actually look at."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
DEJAVU = "/usr/share/fonts/truetype/dejavu"

BG = (18, 22, 29)
PANEL = (26, 32, 41)
LINE = (42, 50, 64)
FG = (232, 228, 218)
MUT = (139, 147, 161)
GREEN = (95, 191, 127)
YELLOW = (224, 169, 61)
RED = (209, 96, 94)
BLUE = (127, 168, 208)


def font(size: int, mono: bool = False, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = ("DejaVuSansMono" if mono else "DejaVuSans") + ("-Bold" if bold else "")
    return ImageFont.truetype(f"{DEJAVU}/{name}.ttf", size)


def canvas(w: int = 880, h: int = 520) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (w, h), BG)
    return img, ImageDraw.Draw(img)


def panel(d, x, y, w, h, title):
    d.rounded_rectangle([x, y, x + w, y + h], 6, fill=PANEL, outline=LINE)
    d.text((x + 12, y + 8), title, font=font(14), fill=MUT)


def v1_dashboard_down():
    """Six service panels; exactly one is DOWN."""
    img, d = canvas()
    d.text((20, 14), "homelab — service status", font=font(20, bold=True), fill=FG)
    services = [
        ("kvllm", "UP", GREEN),
        ("postgresql", "UP", GREEN),
        ("backup-sync", "DOWN", RED),
        ("kvllm-helper", "UP", GREEN),
        ("cron", "UP", GREEN),
        ("nginx", "UP", GREEN),
    ]
    for i, (name, state, col) in enumerate(services):
        x, y = 20 + (i % 3) * 285, 60 + (i // 3) * 220
        panel(d, x, y, 265, 200, name)
        d.text(
            (x + 132, y + 95), state, font=font(34, bold=True), fill=col, anchor="mm"
        )
        d.ellipse([x + 118, y + 140, x + 146, y + 168], fill=col)
    img.save(HERE / "v1-dashboard-down.png")


def v2_gauge_disk():
    """Three disk gauges; /var is the high one at 87%."""
    img, d = canvas()
    d.text((20, 14), "disk usage", font=font(20, bold=True), fill=FG)
    for i, (mount, pct, col) in enumerate(
        [("/", 34, GREEN), ("/var", 87, RED), ("/data", 12, GREEN)]
    ):
        x = 25 + i * 285
        panel(d, x, 60, 265, 380, mount)
        d.arc([x + 40, 130, x + 225, 315], 135, 405, fill=LINE, width=18)
        d.arc(
            [x + 40, 130, x + 225, 315],
            135,
            135 + int(270 * pct / 100),
            fill=col,
            width=18,
        )
        d.text(
            (x + 132, 222), f"{pct}%", font=font(40, bold=True), fill=FG, anchor="mm"
        )
        d.text((x + 132, 360), f"{mount} used", font=font(16), fill=MUT, anchor="mm")
    img.save(HERE / "v2-gauge-disk.png")


def v3_chart_peak():
    """GPU temperature by weekday; Thursday peaks at 83 °C."""
    img, d = canvas()
    d.text((20, 14), "GPU temp (°C) — last 7 days", font=font(20, bold=True), fill=FG)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    temps = [62, 66, 71, 83, 68, 58, 61]
    x0, y0, x1, y1 = 80, 70, 840, 440
    for t in (50, 60, 70, 80, 90):
        y = y1 - (t - 50) * (y1 - y0) / 40
        d.line([x0, y, x1, y], fill=LINE)
        d.text((x0 - 12, y), str(t), font=font(14), fill=MUT, anchor="rm")
    pts = []
    for i, (day, t) in enumerate(zip(days, temps)):
        x = x0 + 40 + i * (x1 - x0 - 80) / 6
        y = y1 - (t - 50) * (y1 - y0) / 40
        pts.append((x, y))
        d.text((x, y1 + 18), day, font=font(15), fill=MUT, anchor="mm")
    d.line(pts, fill=BLUE, width=3)
    for i, (x, y) in enumerate(pts):
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=RED if i == 3 else BLUE)
    img.save(HERE / "v3-chart-peak.png")


def _terminal(lines: list[tuple[str, tuple]], name: str, title: str):
    img, d = canvas(880, 400)
    d.rounded_rectangle([10, 10, 870, 390], 8, fill=(12, 14, 18), outline=LINE)
    d.text((24, 20), title, font=font(14, mono=True), fill=MUT)
    y = 56
    for text, col in lines:
        d.text((24, y), text, font=font(16, mono=True), fill=col)
        y += 26
    img.save(HERE / name)


def v4_terminal_df():
    """df -h output; /data is the fullest at 91%."""
    rows = [
        ("ken@kai:~$ df -h", FG),
        ("Filesystem      Size  Used Avail Use% Mounted on", MUT),
        ("/dev/nvme0n1p2  916G  312G  558G  36% /", FG),
        ("/dev/nvme1n1p1  916G  794G   76G  91% /data", FG),
        ("/dev/sda1       3.6T  1.3T  2.2T  38% /tank", FG),
        ("tmpfs            63G  2.1M   63G   1% /run", FG),
    ]
    _terminal(rows, "v4-terminal-df.png", "kai — terminal")


def v5_journal_error():
    """Journal excerpt; the 02:14 event is an OOM kill of postgres."""
    rows = [
        ("ken@kai:~$ journalctl --since 02:00 --until 03:00", FG),
        ("02:03:11 kai sshd[81211]: Accepted publickey for ken from 192.168.1.77", MUT),
        ("02:10:02 kai CRON[87554]: (root) CMD (/usr/local/bin/healthping.sh)", MUT),
        ("02:14:03 kai kernel: Out of memory: Killed process 88123 (postgres)", RED),
        ("02:14:04 kai systemd[1]: postgresql.service: Main process exited", RED),
        ("02:14:09 kai systemd[1]: postgresql.service: Scheduled restart job", YELLOW),
        ("02:14:14 kai postgres[88342]: database system is ready", GREEN),
        ("02:25:01 kai CRON[89001]: (ken) CMD (/usr/local/bin/healthping.sh)", MUT),
    ]
    _terminal(rows, "v5-journal-error.png", "kai — journal")


def v6_table_registry():
    """Model registry table; qwen3.6-27b-awq row reads 20 GB."""
    img, d = canvas(880, 420)
    d.text((20, 14), "model registry", font=font(20, bold=True), fill=FG)
    rows = [
        ("model", "est VRAM", "tok/s", "verdict"),
        ("qwen2.5-7b-instruct", "17 GB", "105", "has issues"),
        ("gemma-4-12b-it", "27 GB", "62", "worth trying"),
        ("qwen3.6-27b-awq", "20 GB", "45", "worth trying"),
        ("glm-4.7-flash-awq", "24 GB", "197", "has issues"),
        ("gemma-4-31b-it-awq", "25 GB", "73", "worth trying"),
    ]
    for r, cells in enumerate(rows):
        y = 70 + r * 52
        if r:
            d.line([20, y - 6, 860, y - 6], fill=LINE)
        for c, (text, x) in enumerate(zip(cells, (30, 380, 560, 690))):
            f = font(17, bold=(r == 0))
            d.text((x, y), text, font=f, fill=MUT if r == 0 else FG)
    img.save(HERE / "v6-table-registry.png")


def v7_count_warnings():
    """Nine panels; exactly 3 show WARN (yellow)."""
    img, d = canvas()
    d.text((20, 14), "overnight checks", font=font(20, bold=True), fill=FG)
    states = ["OK", "OK", "WARN", "OK", "WARN", "OK", "OK", "OK", "WARN"]
    names = ["disk", "raid", "backup", "certs", "smart", "ups", "dns", "ntp", "temps"]
    for i, (name, st) in enumerate(zip(names, states)):
        x, y = 20 + (i % 3) * 285, 55 + (i // 3) * 150
        panel(d, x, y, 265, 135, name)
        col = YELLOW if st == "WARN" else GREEN
        d.text((x + 132, y + 82), st, font=font(26, bold=True), fill=col, anchor="mm")
    img.save(HERE / "v7-count-warnings.png")


def v8_diagram_backup():
    """Network diagram; kai's backup arrow goes to nas-01."""
    img, d = canvas(880, 460)
    d.text((20, 14), "homelab topology", font=font(20, bold=True), fill=FG)
    boxes = {
        "kai": (60, 180, "GPU box"),
        "ksandbox": (370, 60, "eval sandbox"),
        "nas-01": (650, 180, "storage"),
        "kubsdb": (370, 320, "k8s + dashboards"),
    }
    for name, (x, y, sub) in boxes.items():
        d.rounded_rectangle([x, y, x + 170, y + 80], 8, fill=PANEL, outline=BLUE)
        d.text((x + 85, y + 30), name, font=font(19, bold=True), fill=FG, anchor="mm")
        d.text((x + 85, y + 58), sub, font=font(13), fill=MUT, anchor="mm")

    def arrow(a, b, label, ly):
        d.line([a[0], a[1], b[0], b[1]], fill=MUT, width=2)
        d.polygon(
            [(b[0], b[1]), (b[0] - 12, b[1] - 6), (b[0] - 12, b[1] + 6)], fill=MUT
        )
        d.text(((a[0] + b[0]) // 2, ly), label, font=font(14), fill=YELLOW, anchor="mm")

    arrow((230, 220), (650, 220), "nightly backup (rsync)", 205)
    arrow((230, 250), (370, 360), "docker over ssh", 320)
    arrow((540, 360), (650, 250), "metrics", 330)
    img.save(HERE / "v8-diagram-backup.png")


def _flowchart(name: str, broken: bool):
    """Deploy-pipeline flowchart; the broken variant's third box has text overflowing
    its border (the render-defect the model must detect — or NOT invent on the clean one)."""
    img, d = canvas(880, 460)
    d.text((20, 14), "deploy pipeline", font=font(20, bold=True), fill=FG)
    steps = ["build", "unit tests", "integration suite", "deploy"]
    y = 200
    for i, label in enumerate(steps):
        x = 40 + i * 215
        d.rounded_rectangle([x, y, x + 160, y + 70], 8, fill=PANEL, outline=BLUE)
        if broken and i == 2:
            # text drawn wider than its box, spilling past the right border
            d.text(
                (x + 12, y + 24),
                "integration test suite (nightly)",
                font=font(17),
                fill=FG,
            )
        else:
            d.text((x + 80, y + 35), label, font=font(17), fill=FG, anchor="mm")
        if i < 3:
            d.line([x + 160, y + 35, x + 215, y + 35], fill=MUT, width=2)
            d.polygon(
                [(x + 215, y + 35), (x + 203, y + 29), (x + 203, y + 41)], fill=MUT
            )
    img.save(HERE / name)


def v9_render_broken():
    _flowchart("v9-render-broken.png", broken=True)


def v10_render_clean():
    _flowchart("v10-render-clean.png", broken=False)


def main() -> None:
    for fn in (
        v1_dashboard_down,
        v2_gauge_disk,
        v3_chart_peak,
        v4_terminal_df,
        v5_journal_error,
        v6_table_registry,
        v7_count_warnings,
        v8_diagram_backup,
        v9_render_broken,
        v10_render_clean,
    ):
        fn()
    print(f"rendered 10 fixtures into {HERE}")


if __name__ == "__main__":
    main()
