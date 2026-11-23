"""Builds Homework_4_report.docx (Word report with conclusions and screenshots)."""
from __future__ import annotations

import json
import os
from datetime import date

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ART = os.path.join(ROOT, "artifacts")
FIG = os.path.join(ART, "figures")
SHOTS = os.path.join(ART, "screenshots")

ACCENT = RGBColor(0x1F, 0x4E, 0x79)


def load_metrics() -> dict:
    with open(os.path.join(ART, "metrics.json"), encoding="utf-8") as f:
        return json.load(f)


def caption(doc, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)


def picture(doc, path: str, width_cm: float = 16.0, cap: str | None = None) -> None:
    if not os.path.exists(path):
        doc.add_paragraph(f"[нет файла: {os.path.basename(path)}]")
        return
    doc.add_picture(path, width=Cm(width_cm))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if cap:
        caption(doc, cap)


def table(doc, headers: list[str], rows: list[list[str]], widths: list[float] | None = None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        run = hdr[i].paragraphs[0].add_run(h)
        run.bold = True
        run.font.size = Pt(9.5)
        hdr[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for row in rows:
        cells = t.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(str(value))
            run.font.size = Pt(9.5)
            cells[i].paragraphs[0].alignment = (
                WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.CENTER
            )
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph()
    return t


def bullet(doc, text: str) -> None:
    p = doc.add_paragraph(text, style="List Bullet")
    p.paragraph_format.space_after = Pt(4)


def build() -> str:
    m = load_metrics()
    b, d = m["baseline"], m["drifted"]
    fb, fd = m["fairness_baseline"], m["fairness_drifted"]
    ev = m["drift"]["evidently"]
    sim = m["drift"]["simulated"]

    doc = Document()

    # --- базовые стили -------------------------------------------------------
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.2)
        section.right_margin = Cm(1.8)

    # --- титул ---------------------------------------------------------------
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Домашняя работа № 4")
    run.bold = True
    run.font.size = Pt(24)
    run.font.color.rgb = ACCENT

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Построение системы мониторинга ML-модели")
    run.font.size = Pt(16)
    run.font.color.rgb = ACCENT

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Курс «Бизнес-применение машинного обучения»")
    run.font.size = Pt(11)
    run.italic = True

    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"Кредитный скоринг · CatBoost · Evidently · Prometheus\n{date.today():%d.%m.%Y}")
    run.font.size = Pt(10.5)

    # --- аннотация -----------------------------------------------------------
    doc.add_paragraph()
    doc.add_heading("Краткое резюме", level=1)
    doc.add_paragraph(
        "В работе построен полный контур мониторинга модели кредитного скоринга на датасете "
        "credit-g: обучена модель CatBoost, сымитирован дрифт данных (сдвиг возраста +5 лет "
        "и изменение распределения целевых классов), дрифт найден с помощью Evidently, "
        "посчитаны метрики справедливости по полу и настроен экспорт F1 в Prometheus "
        "с алертами на деградацию качества."
    )
    table(
        doc,
        ["Показатель", "Значение"],
        [
            ["F1 на отложенной выборке (baseline)", f"{b['f1']:.3f}"],
            ["F1 после дрифта", f"{d['f1']:.3f}"],
            ["Относительное падение F1", f"{(b['f1'] - d['f1']) / b['f1']:.1%}"],
            ["Обнаружено дрифта (Evidently)", f"{ev['drifted_columns']} из {ev['total_columns']} колонок ({ev['drift_share']:.0%})"],
            ["Demographic parity difference (sex)", f"{fb['demographic_parity_difference']:.3f}"],
            ["Disparate impact ratio (sex)", f"{fb['disparate_impact_ratio']:.3f}"],
            ["Алертов настроено / сработало", "5 / 3 (F1Drop, F1Critical, DataDrift)"],
        ],
        widths=[9.5, 6.0],
    )

    # --- 1. постановка -------------------------------------------------------
    doc.add_heading("1. Постановка задачи", level=1)
    doc.add_paragraph(
        "Требовалось построить систему мониторинга ML-модели, которая отслеживает "
        "качество предсказаний и дрифт входных данных, а также справедливость модели "
        "по защищённому признаку."
    )
    table(
        doc,
        ["№", "Шаг", "Реализация"],
        [
            ["01", "Датасет", "credit-g (OpenML id 31), 1000 клиентов, 20 признаков"],
            ["02", "Модель", "CatBoostClassifier, F1 = 0.588, ROC AUC = 0.796"],
            ["03", "Дрифт", "age +5 лет; down-sampling класса bad (30 % → 7.9 %)"],
            ["04", "Evidently", "DataDriftPreset, HTML-отчёт, 4 дрифтующих колонки"],
            ["05", "Fairness", "DPD / EOD / DIR по признаку sex"],
            ["06", "Prometheus", "экспорт F1 и дрифта, 5 правил алертов, живой сервер"],
        ],
        widths=[1.2, 3.6, 10.7],
    )

    # --- 2. данные -----------------------------------------------------------
    doc.add_heading("2. Данные", level=1)
    doc.add_paragraph(
        "Датасет credit-g — классическая задача оценки кредитоспособности (German Credit). "
        "1000 наблюдений, 20 признаков: срок кредита, сумма, история платежей, цель кредита, "
        "сбережения, занятость, возраст, семейное положение и др. Целевая переменная class "
        "принимает значения good (кредит возвращён) и bad (дефолт)."
    )
    doc.add_paragraph(
        "Отдельной колонки «пол» в датасете нет: она закодирована в признаке personal_status "
        "(male single, male div/sep, male mar/wid, female div/dep/mar). Для fairness-аудита "
        "признак восстановлен в бинарном виде: 690 мужчин и 310 женщин. В модель защищённый "
        "признак не подаётся — он используется только для анализа."
    )
    picture(doc, os.path.join(FIG, "eda_overview.png"), 16.5,
            "Рис. 1. Баланс классов, распределение возраста и доля дефолтов по полу")

    # --- 3. модель -----------------------------------------------------------
    doc.add_heading("3. Модель и качество", level=1)
    doc.add_paragraph(
        "Выборка разделена на train/test в пропорции 70/30 со стратификацией по целевой "
        "переменной. Категориальные признаки передаются CatBoost нативно (cat_features), "
        "без one-hot-кодирования. Гиперпараметры: 600 итераций, learning_rate 0.05, depth 4, "
        "ранняя остановка по F1 (od_wait = 50). Финальная модель — 244 дерева."
    )
    table(
        doc,
        ["Метрика", "Baseline (test, n=300)", "После дрифта (n=228)", "Изменение"],
        [
            ["F1 (класс bad)", f"{b['f1']:.3f}", f"{d['f1']:.3f}", f"{d['f1'] - b['f1']:+.3f}"],
            ["Precision", f"{b['precision']:.3f}", f"{d['precision']:.3f}", f"{d['precision'] - b['precision']:+.3f}"],
            ["Recall", f"{b['recall']:.3f}", f"{d['recall']:.3f}", f"{d['recall'] - b['recall']:+.3f}"],
            ["ROC AUC", f"{b['roc_auc']:.3f}", f"{d['roc_auc']:.3f}", f"{d['roc_auc'] - b['roc_auc']:+.3f}"],
            ["Accuracy", f"{b['accuracy']:.3f}", f"{d['accuracy']:.3f}", f"{d['accuracy'] - b['accuracy']:+.3f}"],
            ["Доля класса bad", f"{b['positive_rate']:.1%}", f"{d['positive_rate']:.1%}",
             f"{(d['positive_rate'] - b['positive_rate']) * 100:+.1f} п.п."],
        ],
        widths=[4.6, 4.2, 4.2, 2.5],
    )
    picture(doc, os.path.join(FIG, "baseline_quality.png"), 15.5,
            "Рис. 2. Матрица ошибок и ROC-кривая на отложенной выборке")

    # --- 4. дрифт ------------------------------------------------------------
    doc.add_heading("4. Симуляция дрифта", level=1)
    doc.add_paragraph(
        "Дрифт имитируется двумя способами, соответствующими типовым сценариям деградации "
        "в продакшене: (1) ковариатный сдвиг — возраст клиентов увеличен на 5 лет "
        "(портфель «стареет»); (2) сдвиг распределения классов — доля дефолтов снижена "
        f"с {sim['target_share_bad_before']:.1%} до {sim['target_share_bad_after']:.1%} "
        "путём down-sampling класса bad. Дрифтованный набор построен из тестовой выборки, "
        "поэтому истинные метки известны и деградация измерена честно."
    )
    picture(doc, os.path.join(FIG, "drift_simulation.png"), 16.0,
            "Рис. 3. Сдвиг возраста и изменение доли класса bad")

    # --- 5. evidently --------------------------------------------------------
    doc.add_heading("5. Дрифт: результаты Evidently", level=1)
    doc.add_paragraph(
        "Отчёт Evidently сравнивает обучающую выборку (reference) с дрифтованным потоком "
        "(current). Для каждой колонки выполняется статистический тест (K-S для числовых, "
        "Z-test / χ² для категориальных), порог p-value = 0.05."
    )
    per_col = ev["per_column"]
    top = sorted(per_col.items(), key=lambda kv: kv[1]["p_value"])[:8]
    table(
        doc,
        ["Колонка", "p-value", "Дрифт обнаружен"],
        [[col, f"{val['p_value']:.2e}", "да" if val["drifted"] else "нет"] for col, val in top],
        widths=[6.5, 4.5, 4.5],
    )
    doc.add_paragraph(
        f"Итог: дрифт обнаружен в {ev['drifted_columns']} из {ev['total_columns']} колонок "
        f"(drift share = {ev['drift_share']:.1%}), в том числе по возрасту (сдвиг +5 лет) "
        "и по целевой переменной (изменение баланса классов). Полный интерактивный отчёт "
        "сохранён в artifacts/evidently_drift_report.html."
    )
    picture(doc, os.path.join(FIG, "evidently_drift_features.png"), 15.0,
            "Рис. 4. Признаки с наибольшим дрифтом (−log10 p-value)")

    # --- 6. fairness ---------------------------------------------------------
    doc.add_heading("6. Fairness по признаку sex", level=1)
    doc.add_paragraph(
        "Метрики справедливости считаются по двум группам (male / female). Благоприятный "
        "исход — кредит одобрен (предсказание good). Selection rate — доля одобрений в группе; "
        "TPR — доля одобренных среди тех, кто действительно вернул кредит; FPR — доля "
        "одобренных среди дефолтных клиентов."
    )
    groups = fb["groups"]
    table(
        doc,
        ["Группа", "N", "Selection rate", "TPR", "FPR", "F1 (bad)"],
        [
            [g, str(v["n"]), f"{v['selection_rate']:.3f}", f"{v['tpr']:.3f}",
             f"{v['fpr']:.3f}", f"{v['f1_bad']:.3f}"]
            for g, v in groups.items()
        ],
        widths=[3.0, 2.0, 3.4, 2.6, 2.6, 2.6],
    )
    table(
        doc,
        ["Метрика", "Значение", "Интерпретация"],
        [
            ["Demographic parity difference", f"{fb['demographic_parity_difference']:.3f}",
             "разрыв долей одобрений ≈ 10 п.п."],
            ["Equal opportunity difference", f"{fb['equal_opportunity_difference']:.3f}",
             "разрыв TPR между группами"],
            ["Equalized odds (FPR gap)", f"{fb['equalized_odds_fpr_difference']:.3f}",
             "разница ложноположительных одобрений"],
            ["Disparate impact ratio", f"{fb['disparate_impact_ratio']:.3f}",
             "> 0.8 — правило 80 % соблюдено"],
        ],
        widths=[6.2, 3.2, 6.1],
    )
    picture(doc, os.path.join(FIG, "fairness_by_sex.png"), 16.0,
            "Рис. 5. Selection rate, TPR и FPR по полу")
    doc.add_paragraph(
        "Формального нарушения правила 80 % нет (DIR = "
        f"{fb['disparate_impact_ratio']:.3f} > 0.80), однако разрыв в долях одобрений "
        "составляет около 10 п.п. — это зона риска, которая должна отслеживаться алертом "
        "FairnessDegraded (DPD > 0.15). После дрифта разрыв сократился до "
        f"{fd['demographic_parity_difference']:.3f}, но модель стала одобрять больше заявок "
        "в целом, что является уже бизнес-риском, а не только ML-метрикой."
    )

    # --- 7. prometheus -------------------------------------------------------
    doc.add_heading("7. Мониторинг: Prometheus и алерты", level=1)
    doc.add_paragraph(
        "Схема мониторинга: метрики модели и дрифта складываются в artifacts/metrics.json, "
        "экспортёр src/metrics_exporter.py публикует их на :8000/metrics через "
        "prometheus_client, Prometheus скрейпит эндпоинт каждые 5 секунд и вычисляет "
        "правила из prometheus/alerts.yml."
    )
    table(
        doc,
        ["Алерт", "Условие", "Severity"],
        [
            ["ModelF1Drop", "падение F1 более чем на 10 % от baseline, 1 мин", "warning"],
            ["ModelF1Critical", "model_f1_score < 0.52, 30 с", "critical"],
            ["DataDriftDetected", "дрифт > 15 % колонок, 30 с", "warning"],
            ["FairnessDegraded", "DPD > 0.15, 1 мин", "warning"],
            ["DisparateImpactViolation", "DIR < 0.80, 1 мин", "warning"],
        ],
        widths=[4.6, 8.0, 2.6],
    )
    doc.add_paragraph(
        "Для демонстрации экспортёр запускается в режиме replay: 60 секунд модель работает "
        "стабильно, затем качество линейно деградирует до измеренного на дрифтованных данных "
        f"(F1 с {b['f1']:.3f} до {d['f1']:.3f}). Это даёт настоящую кривую падения в Prometheus, "
        "а не статичную цифру."
    )
    picture(doc, os.path.join(SHOTS, "prometheus_alerts.png"), 16.5,
            "Рис. 6. /alerts: DataDriftDetected в состоянии FIRING (значение 0.190)")
    picture(doc, os.path.join(SHOTS, "prometheus_alerts_f1.png"), 16.5,
            "Рис. 7. /alerts: ModelF1Drop FIRING — падение F1 на 16.7 % от baseline")
    picture(doc, os.path.join(SHOTS, "prometheus_graph_f1.png"), 16.5,
            "Рис. 8. /graph: плато baseline 0.588, затем падение F1 до 0.490")
    picture(doc, os.path.join(SHOTS, "prometheus_graph_drift.png"), 16.5,
            "Рис. 9. /graph: рост доли дрифтующих признаков (model_drift_share)")
    picture(doc, os.path.join(SHOTS, "prometheus_targets.png"), 16.5,
            "Рис. 10. /targets: экспортёр и сам Prometheus в состоянии UP")

    # --- 8. выводы -----------------------------------------------------------
    doc.add_heading("8. Выводы", level=1)
    for text in [
        "Модель CatBoost на credit-g показывает F1 = "
        f"{b['f1']:.3f} и ROC AUC = {b['roc_auc']:.3f} — приемлемый уровень для табличных "
        "кредитных данных с сильным дисбалансом классов.",
        "Сдвиг возраста и изменение доли дефолтов роняют F1 до "
        f"{d['f1']:.3f} ({((b['f1'] - d['f1']) / b['f1']):.1%} относительного падения), "
        "при этом accuracy растёт — наглядная демонстрация того, почему мониторить нужно "
        "F1, а не долю верных ответов.",
        "Evidently обнаруживает дрифт автоматически, без меток, — это «ранний» контур "
        "мониторинга; алерт по F1 требует разметки и работает как «поздний», но точный контур. "
        "В продакшене нужны оба.",
        "Аудит fairness выявил разрыв в долях одобрений около 10 п.п. между мужчинами "
        "и женщинами (DIR = "
        f"{fb['disparate_impact_ratio']:.3f}); правило 80 % соблюдено, но разрыв необходимо "
        "держать под алертом FairnessDegraded.",
        "Связка prometheus_client → Prometheus → alerts.yml даёт рабочий контур "
        "оповещения: при деградации F1 срабатывают ModelF1Drop и ModelF1Critical, "
        "при дрифте — DataDriftDetected.",
    ]:
        bullet(doc, text)

    # --- приложение ----------------------------------------------------------
    doc.add_heading("Приложение. Состав артефактов", level=1)
    table(
        doc,
        ["Путь", "Содержимое"],
        [
            ["Homework_4.ipynb", "исполненный ноутбук со всеми шагами"],
            ["Homework_4_presentation.docx / .pdf", "презентация на 13 слайдов (Word, 16:9)"],
            ["artifacts/evidently_drift_report.html", "интерактивный отчёт Evidently"],
            ["artifacts/figures/*.png", "графики для отчёта и презентации"],
            ["artifacts/screenshots/*.png", "скриншоты Prometheus"],
            ["artifacts/metrics.json", "все метрики в машинночитаемом виде"],
            ["artifacts/model/catboost_credit_g.cbm", "обученная модель"],
            ["prometheus/prometheus.yml", "конфиг скрейпинга"],
            ["prometheus/alerts.yml", "5 правил алертов"],
            ["src/metrics_exporter.py", "экспортёр метрик (/metrics)"],
            ["README.md", "инструкция по воспроизведению"],
        ],
        widths=[6.8, 9.5],
    )
    doc.add_paragraph(
        "Воспроизведение: python -m pip install --target .pylibs -r requirements.txt, "
        "затем jupyter nbconvert --to notebook --execute --inplace Homework_4.ipynb и "
        "запуск прометея согласно README."
    )

    out = os.path.join(ROOT, "Homework_4_report.docx")
    doc.save(out)
    print("saved:", out)
    return out


if __name__ == "__main__":
    build()


