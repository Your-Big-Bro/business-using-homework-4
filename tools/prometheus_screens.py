"""Screenshots of the running Prometheus UI via Playwright + installed Edge.

Unlike plain headless --screenshot this can click "Execute" on the graph page and
expand alert rows, so the images show real data.
"""
from __future__ import annotations

import json
import os
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHOTS = os.path.join(ROOT, "artifacts", "screenshots")
PROM = "http://127.0.0.1:9090"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def main() -> int:
    os.makedirs(SHOTS, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=EDGE, args=["--hide-scrollbars"])
        page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1.5)

        # ---- /alerts: раскрываем алерты, чтобы были видны аннотации ---------
        page.goto(f"{PROM}/alerts", wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        for _ in range(3):
            rows = page.locator("text=/^(ModelF1Drop|ModelF1Critical|DataDriftDetected)$/")
            for i in range(rows.count()):
                try:
                    rows.nth(i).click()
                    page.wait_for_timeout(250)
                except Exception:
                    pass
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(800)
        page.screenshot(path=os.path.join(SHOTS, "prometheus_alerts.png"), full_page=False)
        print("alerts ok")

        # второй кадр: секция model-quality с алертами по F1
        try:
            page.locator("text=DataDriftDetected").first.click()   # свернуть дрифт
            page.wait_for_timeout(700)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(500)
            page.screenshot(path=os.path.join(SHOTS, "prometheus_alerts_f1.png"), full_page=False)
            print("alerts_f1 ok")
        except Exception as exc:
            print("alerts_f1 skip:", exc)

        # ---- /graph: вводим запрос и нажимаем Execute -----------------------
        def graph(expr: str, name: str) -> None:
            page.goto(f"{PROM}/graph?g0.expr={expr}&g0.tab=0&g0.range_input=15m",
                      wait_until="domcontentloaded")
            page.wait_for_timeout(1000)
            try:
                page.get_by_role("button", name="Execute").click(timeout=5000)
            except Exception:
                page.keyboard.press("Enter")
            page.wait_for_timeout(3500)
            page.screenshot(path=os.path.join(SHOTS, name), full_page=False)
            print(name, "ok")

        graph("model_f1_score", "prometheus_graph_f1.png")
        graph("model_drift_share", "prometheus_graph_drift.png")

        # ---- /targets --------------------------------------------------------
        page.goto(f"{PROM}/targets", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.screenshot(path=os.path.join(SHOTS, "prometheus_targets.png"), full_page=False)
        print("targets ok")

        state = {
            "alerts": page.evaluate(
                "fetch('/api/v1/alerts').then(r => r.json()).then(d => d.data.alerts.map(a => ({name: a.labels.alertname, state: a.state, severity: a.labels.severity, summary: a.annotations.summary})))"
            )
        }
        with open(os.path.join(SHOTS, "prometheus_state.json"), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())




