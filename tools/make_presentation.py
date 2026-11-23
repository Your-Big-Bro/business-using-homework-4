"""Builds Homework_4_presentation.docx — a slide deck in Word format (16:9).

One slide per page: accent bar, big title, bullets, screenshots/tables.
Rendered with python-docx only, so it opens in Word/LibreOffice as a deck.
"""
from __future__ import annotations

import json
import os
from datetime import date

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ART = os.path.join(ROOT, "artifacts")
FIG = os.path.join(ART, "figures")
SHOTS = os.path.join(ART, "screenshots")

ACCENT = "1F4E79"
ACCENT_RGB = RGBColor(0x1F, 0x4E, 0x79)
GREY = RGBColor(0x59, 0x59, 0x59)
ORANGE = RGBColor(0xC0, 0x50, 0x2A)

SLIDE_W = 33.87      # cm, 16:9
SLIDE_H = 19.05
CONTENT_W = SLIDE_W - 3.2   # минус поля


def load_metrics() -> dict:
    with open(os.path.join(ART, "metrics.json"), encoding="utf-8") as f:
        return json.load(f)


def shade(cell, color: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tc_pr.append(shd)


def accent_bar(doc, color: str = ACCENT, width_cm: float = CONTENT_W, height_cm: float = 0.18) -> None:
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    cell = table.rows[0].cells[0]
    cell.width = Cm(width_cm)
    shade(cell, color)
    row = table.rows[0]
    row.height = Cm(height_cm)
    cell.paragraphs[0].paragraph_format.space_after = Pt(0)
    cell.paragraphs[0].paragraph_format.space_before = Pt(0)
    run = cell.paragraphs[0].add_run("")
    run.font.size = Pt(1)


def slide(doc, title: str, subtitle: str | None = None, first: bool = False, number: int | None = None) -> None:
    if not first:
        doc.add_page_break()
    if number is not None:
        num = doc.add_paragraph()
        num.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        num.paragraph_format.space_after = Pt(0)
        num.paragraph_format.space_before = Pt(0)
        run = num.add_run(f"ДЗ 4 · слайд {number}")
        run.font.size = Pt(8)
        run.font.color.rgb = GREY
    accent_bar(doc)
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(title)
    run.bold = True
    run.font.size = Pt(30)
    run.font.color.rgb = ACCENT_RGB
    if subtitle:
        sp = doc.add_paragraph()
        sp.paragraph_format.space_after = Pt(10)
        run = sp.add_run(subtitle)
        run.font.size = Pt(14)
        run.font.color.rgb = GREY
        run.italic = True



def bullets(doc, items: list[str], size: int = 15, space: int = 6) -> None:
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(space)
        run = p.add_run(item)
        run.font.size = Pt(size)


def paragraph(doc, text: str, size: int = 15, bold: bool = False, color: RGBColor | None = None,
              space_after: int = 8) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def code_block(doc, text: str, size: int = 11) -> None:
    table = doc.add_table(rows=1, cols=1)
    cell = table.rows[0].cells[0]
    shade(cell, "F2F5F9")
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    for i, line in enumerate(text.split("\n")):
        run = p.add_run(line)
        run.font.name = "Consolas"
        run.font.size = Pt(size)
        if i < len(text.split("\n")) - 1:
            run.add_break()


def picture(doc, path: str, max_w: float = CONTENT_W, max_h: float = 11.0) -> None:
    if not os.path.exists(path):
        paragraph(doc, f"[нет файла: {os.path.basename(path)}]", 11)
        return
    with Image.open(path) as im:
        w_px, h_px = im.size
    ratio = h_px / w_px
    width = max_w
    height = width * ratio
    if height > max_h:
        height = max_h
        width = height / ratio
    doc.add_picture(path, width=Cm(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


def table(doc, headers: list[str], rows: list[list[str]], widths: list[float], size: int = 12):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.width = Cm(widths[i])
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        run.bold = True
        run.font.size = Pt(size)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for row in rows:
        cells = t.add_row().cells
        for i, value in enumerate(row):
            cells[i].width = Cm(widths[i])
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(str(value))
            run.font.size = Pt(size)
            cells[i].paragraphs[0].alignment = (
                WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.CENTER
            )
    return t


def two_columns(doc, left_items: list[str], right_items: list[str], size: int = 14) -> None:
    t = doc.add_table(rows=1, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    left, right = t.rows[0].cells
    left.width = Cm(CONTENT_W / 2)
    right.width = Cm(CONTENT_W / 2)
    for cell, items in ((left, left_items), (right, right_items)):
        cell.text = ""
        first = True
        for item in items:
            p = cell.paragraphs[0] if first else cell.add_paragraph()
            first = False
            p.paragraph_format.space_after = Pt(4)
            run = p.add_run("• " + item)
            run.font.size = Pt(size)


def stats_row(doc, items: list[tuple[str, str]], height: float = 2.6) -> None:
    """Ряд крупных цифр: [(значение, подпись), ...]."""
    t = doc.add_table(rows=1, cols=len(items))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (value, label) in enumerate(items):
        cell = t.rows[0].cells[i]
        cell.width = Cm(CONTENT_W / len(items))
        shade(cell, "EEF3F8")
        cell.text = ""
        p1 = cell.paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p1.paragraph_format.space_before = Pt(8)
        p1.paragraph_format.space_after = Pt(0)
        run = p1.add_run(value)
        run.bold = True
        run.font.size = Pt(26)
        run.font.color.rgb = ACCENT_RGB
        p2 = cell.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.space_after = Pt(8)
        run = p2.add_run(label)
        run.font.size = Pt(10)
        run.font.color.rgb = GREY
    t.rows[0].height = Cm(height)


def build() -> str:
    m = load_metrics()
    b, d = m["baseline"], m["drifted"]
    fb, fd = m["fairness_baseline"], m["fairness_drifted"]
    ev = m["drift"]["evidently"]
    sim = m["drift"]["simulated"]

    doc = Document()
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Cm(SLIDE_W)
    section.page_height = Cm(SLIDE_H)
    section.top_margin = Cm(1.0)
    section.bottom_margin = Cm(0.8)
    section.left_margin = Cm(1.6)
    section.right_margin = Cm(1.6)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(15)

    # ---------------------------------------------------------------- 1 титул
    accent_bar(doc, ACCENT, CONTENT_W, 0.5)
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(60)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Система мониторинга ML-модели")
    run.bold = True
    run.font.size = Pt(50)
    run.font.color.rgb = ACCENT_RGB

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("кредитный скоринг · CatBoost · Evidently · Prometheus")
    run.font.size = Pt(22)
    run.font.color.rgb = GREY

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(40)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Домашняя работа № 4")
    run.bold = True
    run.font.size = Pt(26)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Курс «Бизнес-применение машинного обучения»")
    run.font.size = Pt(16)
    run.italic = True

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(24)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"{date.today():%d.%m.%Y}  ·  github.com/Your-Big-Bro/business-using-homework-4")
    run.font.size = Pt(14)
    run.font.color.rgb = GREY

    # --------------------------------------------------------------- 2 задача
    slide(doc, "Задание и результат", "Шесть шагов из практического задания — все выполнены", number=2)
    table(
        doc,
        ["№", "Шаг задания", "Что сделано"],
        [
            ["01", "Взять датасет credit-g", "OpenML id 31, 1000 клиентов, 20 признаков"],
            ["02", "Обучить модель (CatBoost)", f"F1 = {b['f1']:.3f}, ROC AUC = {b['roc_auc']:.3f}"],
            ["03", "Сымитировать дрифт", "age +5 лет, доля bad 30 % → 7.9 %"],
            ["04", "Запустить Evidently", f"дрифт в {ev['drifted_columns']} из {ev['total_columns']} колонок ({ev['drift_share']:.0%})"],
            ["05", "Fairness по sex", f"DPD {fb['demographic_parity_difference']:.3f}, DIR {fb['disparate_impact_ratio']:.3f}"],
            ["06", "Экспорт F1 в Prometheus", "5 алертов, живой сервер, падение F1 в реальном времени"],
        ],
        widths=[1.4, 9.0, 20.0],
        size=13,
    )
    paragraph(doc, "")
    stats_row(doc, [
        (f"{b['f1']:.3f}", "F1 baseline"),
        (f"{d['f1']:.3f}", "F1 после дрифта"),
        (f"{ev['drifted_columns']}/{ev['total_columns']}", "колонок с дрифтом"),
        ("5 / 3", "алертов / сработало"),
    ])
    paragraph(doc, "Сдача: ноутбук с выводами · отчёт Word и PDF · README · "
                   "артефакты Evidently · конфиги Prometheus · скриншоты живого сервера", 12, False, GREY, 2)

    # --------------------------------------------------------------- 3 данные
    slide(doc, "Данные", "credit-g: 1000 клиентов, 20 признаков, 30 % дефолтов", number=3)
    picture(doc, os.path.join(FIG, "eda_overview.png"), max_h=9.6)
    bullets(doc, [
        "Пол восстановлен из personal_status (в датасете отдельной колонки sex нет): 690 мужчин / 310 женщин",
        "Защищённый признак в модель не подаётся — только для аудита справедливости",
    ], size=13)

    # --------------------------------------------------------------- 4 модель
    slide(doc, "Модель", "CatBoost, нативные категориальные признаки, ранняя остановка по F1", number=4)
    table(
        doc,
        ["Метрика", "Baseline (n=300)", "После дрифта (n=228)"],
        [
            ["F1 (класс bad)", f"{b['f1']:.3f}", f"{d['f1']:.3f}"],
            ["Precision", f"{b['precision']:.3f}", f"{d['precision']:.3f}"],
            ["Recall", f"{b['recall']:.3f}", f"{d['recall']:.3f}"],
            ["ROC AUC", f"{b['roc_auc']:.3f}", f"{d['roc_auc']:.3f}"],
            ["Accuracy", f"{b['accuracy']:.3f}", f"{d['accuracy']:.3f}"],
        ],
        widths=[8.0, 9.0, 9.0],
    )
    picture(doc, os.path.join(FIG, "baseline_quality.png"), max_h=6.6)

    # --------------------------------------------------------------- 5 дрифт
    slide(doc, "Симуляция дрифта", "Два сценария деградации, которые встречаются в продакшене", number=5)
    two_columns(
        doc,
        [
            "Ковариатный сдвиг: возраст клиентов +5 лет",
            "Сдвиг классов: down-sampling bad",
            f"Доля дефолтов {sim['target_share_bad_before']:.0%} → {sim['target_share_bad_after']:.1%}",
        ],
        [
            "Дрифтованный набор — из тестовой выборки",
            "Истинные метки известны",
            "Значит, деградация измерена честно, а не «на глаз»",
        ],
        size=14,
    )
    picture(doc, os.path.join(FIG, "drift_simulation.png"), max_h=7.4)

    # ------------------------------------------------------------ 6 evidently
    slide(doc, "Evidently находит дрифт", f"{ev['drifted_columns']} из {ev['total_columns']} колонок уехали (drift share {ev['drift_share']:.0%})", number=6)
    picture(doc, os.path.join(FIG, "evidently_drift_features.png"), max_h=10.6)
    paragraph(doc, "Дрифт по возрасту: p = 8.3e-09 · по целевой переменной: p = 1.6e-11", 13, True, ORANGE, 2)

    # ------------------------------------------------------------ 7 качество
    slide(doc, "Цена дрифта: F1 падает, accuracy растёт", f"F1 {b['f1']:.3f} → {d['f1']:.3f} — это −{((b['f1'] - d['f1']) / b['f1']):.1%} относительно baseline", number=7)
    picture(doc, os.path.join(FIG, "quality_before_after.png"), max_h=9.2)
    bullets(doc, [
        "Класс bad стал редким (7.9 %) — precision упал с 0.714 до 0.387",
        "Accuracy при этом выросла до 0.890: модель «угадывает» большинство, но теряет дефолты",
        "Именно поэтому алерт настроен на F1, а не на accuracy",
    ], size=13, space=4)

    # ------------------------------------------------------------ 8 fairness
    slide(doc, "Fairness по признаку sex", "Разрыв есть, но правило 80 % формально соблюдено", number=8)
    table(
        doc,
        ["Группа", "N", "Selection rate", "TPR", "FPR"],
        [
            ["female", str(fb["groups"]["female"]["n"]), f"{fb['groups']['female']['selection_rate']:.3f}",
             f"{fb['groups']['female']['tpr']:.3f}", f"{fb['groups']['female']['fpr']:.3f}"],
            ["male", str(fb["groups"]["male"]["n"]), f"{fb['groups']['male']['selection_rate']:.3f}",
             f"{fb['groups']['male']['tpr']:.3f}", f"{fb['groups']['male']['fpr']:.3f}"],
        ],
        widths=[5.0, 4.0, 7.0, 5.0, 5.0],
    )
    paragraph(doc, f"DPD = {fb['demographic_parity_difference']:.3f}   ·   "
                   f"EOD = {fb['equal_opportunity_difference']:.3f}   ·   "
                   f"DIR = {fb['disparate_impact_ratio']:.3f}  (> 0.80 — правило 80 % соблюдено)", 14, True, ORANGE, 6)
    picture(doc, os.path.join(FIG, "fairness_by_sex.png"), max_h=7.6)

    # ---------------------------------------------------------- 9 архитектура
    slide(doc, "Архитектура мониторинга", "Ранний контур (дрифт без меток) + поздний контур (качество с метками)", number=9)
    code_block(doc, """  CatBoost / батч-прогон  ──►  artifacts/metrics.json
                                      │
                    src/metrics_exporter.py  (:8000/metrics)
                                      │   scrape каждые 5 секунд
                     Prometheus (:9090)  ──►  alerts.yml  ──►  FIRING""", 11)
    paragraph(doc, "")
    bullets(doc, [
        "Экспортёр отдаёт F1, precision, recall, ROC AUC, drift_share и три fairness-метрики",
        "5 правил: ModelF1Drop, ModelF1Critical, DataDriftDetected, FairnessDegraded, DisparateImpactViolation",
        "Порог F1Drop — относительное падение > 10 % в течение минуты (а не абсолютное значение)",
    ], size=13, space=4)

    # ------------------------------------------------------------ 10 алерты
    slide(doc, "Живой Prometheus: алерты сработали", "ModelF1Drop, ModelF1Critical и DataDriftDetected в состоянии FIRING", number=10)
    picture(doc, os.path.join(SHOTS, "prometheus_alerts_f1.png"), max_h=11.2)

    # ------------------------------------------------------------ 11 график
    slide(doc, "Живой Prometheus: падение F1", "Плато baseline 0.588 → деградация после дрифта → 0.490", number=11)
    picture(doc, os.path.join(SHOTS, "prometheus_graph_f1.png"), max_h=11.2)

    # -------------------------------------------------------- 12 дрифт-график
    slide(doc, "Дрифт в реальном времени", "model_drift_share 0 → 0.190: сработал DataDriftDetected", number=12)
    two_columns(
        doc,
        ["Оба таргета (credit_model, prometheus) в состоянии UP", "Скрейп каждые 5 секунд, ошибок нет"],
        ["Дрифт пересекает порог 0.15", "Алерт висит 30 секунд и уходит в FIRING"],
        size=13,
    )
    picture(doc, os.path.join(SHOTS, "prometheus_graph_drift.png"), max_h=9.6)

    # ------------------------------------------------------------- 13 выводы
    slide(doc, "Выводы", "Что забираем в продакшен", number=13)
    bullets(doc, [
        f"Модель: F1 {b['f1']:.3f} / ROC AUC {b['roc_auc']:.3f} — рабочий уровень для кредитного скоринга",
        f"Дрифт роняет F1 до {d['f1']:.3f}, при этом accuracy растёт — мониторить надо F1",
        "Evidently даёт ранний сигнал без меток, алерт по F1 — точный, но поздний: нужны оба контура",
        "Fairness: DPD 0.101 при DIR 0.877 — правило 80 % соблюдено, но разрыв под контролем алерта",
        "Связка prometheus_client → Prometheus → alerts.yml проверена на живом сервере",
    ], size=15, space=8)
    paragraph(doc, "")
    paragraph(doc, "Репозиторий: github.com/Your-Big-Bro/business-using-homework-4", 15, True, ACCENT_RGB, 4)
    paragraph(doc, "В репозитории: ноутбук, отчёт Word/PDF, эта презентация, артефакты Evidently, "
                   "конфиги Prometheus и скриншоты.", 13, False, GREY, 2)

    out = os.path.join(ROOT, "Homework_4_presentation.docx")
    doc.save(out)
    print("saved:", out)
    return out


if __name__ == "__main__":
    build()




