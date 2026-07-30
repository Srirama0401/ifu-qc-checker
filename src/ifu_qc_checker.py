"""
IFU (Instructions for Use) QC Automation — core checker logic.

Implements the checklist:
  1. Page Number Verification
  2. Manufacturer Information
  3. Regulatory Symbols (label/text presence — see note below)
  4. Date Verification

LIMITATION ON SYMBOLS
----------------------
Regulatory symbols (CE mark, biohazard, "keep dry", temperature
limit icon, etc.) are graphical elements, not text. This checker
detects whether the *text label/caption* near a symbol appears in
the extracted PDF text. True shape-based symbol verification is
provided as an optional stub (check_regulatory_symbols_by_image)
that renders pages to images and does template matching — wire it
up with your own symbol reference images if you need it.
"""

import re
import json
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

import pdfplumber

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib import colors


# ============================================================
# Data structures
# ============================================================

@dataclass
class Issue:
    category: str
    severity: str   # "FAIL" or "WARN"
    message: str
    page: int = None


@dataclass
class QCReport:
    source_file: str = ""
    issues: list = field(default_factory=list)

    def add(self, category, severity, message, page=None):
        self.issues.append(Issue(category, severity, message, page))

    def fails(self):
        return [i for i in self.issues if i.severity == "FAIL"]

    def warns(self):
        return [i for i in self.issues if i.severity == "WARN"]

    def passed(self):
        return len(self.fails()) == 0

    def print_report(self):
        print("\n" + "=" * 60)
        print(f"IFU QC REPORT — {self.source_file}")
        print("=" * 60)
        if not self.issues:
            print("✅ All checks passed — no issues found.")
        else:
            for cat in sorted(set(i.category for i in self.issues)):
                print(f"\n--- {cat} ---")
                for i in [x for x in self.issues if x.category == cat]:
                    mark = "❌" if i.severity == "FAIL" else "⚠️"
                    page_str = f" (page {i.page})" if i.page else ""
                    print(f"  {mark} {i.message}{page_str}")
        print("\n" + "-" * 60)
        print(f"Total: {len(self.fails())} FAIL, {len(self.warns())} WARN")
        print("RESULT:", "PASS ✅" if self.passed() else "FAIL ❌")
        print("=" * 60)

    def to_dict(self):
        return {
            "source_file": self.source_file,
            "generated_at": datetime.now().isoformat(),
            "result": "PASS" if self.passed() else "FAIL",
            "fail_count": len(self.fails()),
            "warn_count": len(self.warns()),
            "issues": [i.__dict__ for i in self.issues],
        }

    def to_json(self, path):
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    def to_pdf(self, path):
        """Generate a formatted, human-readable PDF version of this report."""
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            name="ReportTitle", fontSize=18, leading=22,
            fontName="Helvetica-Bold", spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            name="ReportSubtitle", fontSize=10, leading=14,
            textColor=colors.grey, spaceAfter=16
        )
        section_style = ParagraphStyle(
            name="Section", fontSize=12, leading=16,
            fontName="Helvetica-Bold", spaceBefore=16, spaceAfter=6,
            textColor=colors.HexColor("#1a1a1a")
        )
        body_style = ParagraphStyle(
            name="Body", fontSize=9.5, leading=13
        )
        pass_style = ParagraphStyle(
            name="Pass", fontSize=12, leading=16,
            fontName="Helvetica-Bold", textColor=colors.HexColor("#0a7d32")
        )

        story = []
        story.append(Paragraph("IFU QC Automation Report", title_style))
        story.append(Paragraph(
            f"Source file: {self.source_file}<br/>"
            f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}",
            subtitle_style
        ))

        # Summary box
        result_text = "PASS" if self.passed() else "FAIL"
        result_color = colors.HexColor("#0a7d32") if self.passed() else colors.HexColor("#c0392b")
        summary_table = Table(
            [["Result", "Failures", "Warnings"],
             [result_text, str(len(self.fails())), str(len(self.warns()))]],
            colWidths=[150, 150, 150]
        )
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TEXTCOLOR", (0, 1), (0, 1), result_color),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(summary_table)

        if not self.issues:
            story.append(Spacer(1, 20))
            story.append(Paragraph("All checks passed — no issues found.", pass_style))
        else:
            for cat in sorted(set(i.category for i in self.issues)):
                story.append(Paragraph(cat, section_style))
                cat_issues = [x for x in self.issues if x.category == cat]
                rows = [["Severity", "Page", "Issue"]]
                for i in cat_issues:
                    rows.append([
                        i.severity,
                        str(i.page) if i.page else "—",
                        Paragraph(i.message, body_style)
                    ])
                issue_table = Table(rows, colWidths=[60, 50, 340])
                table_style = [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
                for row_idx, i in enumerate(cat_issues, start=1):
                    color = colors.HexColor("#c0392b") if i.severity == "FAIL" else colors.HexColor("#b8860b")
                    table_style.append(("TEXTCOLOR", (0, row_idx), (0, row_idx), color))
                    table_style.append(("FONTNAME", (0, row_idx), (0, row_idx), "Helvetica-Bold"))
                issue_table.setStyle(TableStyle(table_style))
                story.append(issue_table)

        doc = SimpleDocTemplate(
            str(path), pagesize=A4,
            topMargin=20 * mm, bottomMargin=15 * mm,
            leftMargin=18 * mm, rightMargin=18 * mm,
        )
        doc.build(story)


# ============================================================
# Core checker
# ============================================================

class IFUQualityChecker:
    def __init__(self, pdf_path, config):
        self.pdf_path = str(pdf_path)
        self.config = config
        self.report = QCReport(source_file=Path(pdf_path).name)
        self.pages_text = []
        self._load()

    def _load(self):
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                self.pages_text.append(page.extract_text() or "")
        if not self.pages_text:
            raise ValueError("No pages found / PDF could not be read.")

    # ------------------------------------------------------
    # 1. Page Number Verification
    # ------------------------------------------------------
    def check_page_numbers(self):
        pattern = self.config["page_number_pattern"]
        found = {}
        total_pages = len(self.pages_text)

        for idx, text in enumerate(self.pages_text, start=1):
            match = re.search(pattern, text)
            if not match:
                self.report.add(
                    "1. Page Number Verification", "FAIL",
                    "No page number found matching expected pattern "
                    f"'{pattern}'", page=idx
                )
                continue
            num, total = int(match.group(1)), int(match.group(2))
            found[idx] = (num, total)

            if total != total_pages:
                self.report.add(
                    "1. Page Number Verification", "FAIL",
                    f"Declared total pages ({total}) does not match "
                    f"actual document length ({total_pages})", page=idx
                )

        declared_nums = [v[0] for v in found.values()]
        seen = {}
        for idx, (num, total) in found.items():
            seen.setdefault(num, []).append(idx)

        for num, idxs in seen.items():
            if len(idxs) > 1:
                self.report.add(
                    "1. Page Number Verification", "FAIL",
                    f"Duplicate page number '{num}' found on physical "
                    f"pages {idxs}"
                )

        expected_seq = list(range(1, total_pages + 1))
        missing = sorted(set(expected_seq) - set(declared_nums))
        if missing:
            self.report.add(
                "1. Page Number Verification", "FAIL",
                f"Missing page number(s): {missing}"
            )

        physical_order = [found[i][0] for i in sorted(found)]
        if physical_order != sorted(physical_order):
            self.report.add(
                "1. Page Number Verification", "FAIL",
                "Declared page numbers are out of sequence relative to "
                f"physical page order: {physical_order}"
            )

    # ------------------------------------------------------
    # 2. Manufacturer Information
    # ------------------------------------------------------
    def check_manufacturer_info(self):
        full_text = "\n".join(self.pages_text)
        cfg = self.config

        def fuzzy_present(value):
            if not value:
                return True
            normalized_doc = re.sub(r"\s+", " ", full_text).lower()
            normalized_val = re.sub(r"\s+", " ", value).strip().lower()
            return normalized_val in normalized_doc

        checks = [
            ("manufacturer_name", "Manufacturer name does not match approved master"),
            ("manufacturer_address", "Manufacturer address does not match exactly"),
            ("ec_rep_address", "Authorized Representative (EC REP) address not found / mismatched"),
            ("importer_address", "Importer/Distributor address not found / mismatched"),
        ]

        for key, msg in checks:
            value = cfg.get(key)
            if value is None:
                continue
            if not fuzzy_present(value):
                self.report.add("2. Manufacturer Information", "FAIL", msg)

        emails = set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", full_text))
        phones = set(re.findall(r"\+?\d[\d\s\-()]{7,}\d", full_text))
        if len(emails) > 1:
            self.report.add(
                "2. Manufacturer Information", "WARN",
                f"Multiple distinct email addresses found, verify consistency: {sorted(emails)}"
            )
        if len(phones) > 1:
            self.report.add(
                "2. Manufacturer Information", "WARN",
                f"Multiple distinct phone numbers found, verify consistency: {sorted(phones)}"
            )

    # ------------------------------------------------------
    # 3. Regulatory Symbols (text-label proxy check)
    # ------------------------------------------------------
    def check_regulatory_symbols(self):
        full_text = "\n".join(self.pages_text)
        normalized = re.sub(r"\s+", " ", full_text).lower()

        for label in self.config["required_symbol_labels"]:
            if label.lower() not in normalized:
                self.report.add(
                    "3. Regulatory Symbols", "WARN",
                    f"Label/caption for symbol '{label}' not found in "
                    "extracted text — verify the symbol graphic is present "
                    "manually or via image-based check"
                )

    def check_regulatory_symbols_by_image(self, symbol_templates=None):
        """
        OPTIONAL / STUB: True graphical symbol verification via template
        matching. Requires: pip install pdf2image opencv-python
        (and poppler installed on the system for pdf2image).

        symbol_templates: dict of {symbol_name: path_to_template_png}
        """
        try:
            from pdf2image import convert_from_path
            import cv2
            import numpy as np
        except ImportError:
            self.report.add(
                "3. Regulatory Symbols", "WARN",
                "Image-based symbol check skipped — install pdf2image and "
                "opencv-python to enable it"
            )
            return

        if not symbol_templates:
            return

        images = convert_from_path(self.pdf_path)
        for page_idx, pil_img in enumerate(images, start=1):
            page_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            for symbol_name, template_path in symbol_templates.items():
                template = cv2.imread(template_path)
                if template is None:
                    continue
                result = cv2.matchTemplate(page_cv, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                if max_val < 0.7:
                    self.report.add(
                        "3. Regulatory Symbols", "WARN",
                        f"Symbol '{symbol_name}' not confidently detected "
                        f"(match={max_val:.2f})", page=page_idx
                    )

    # ------------------------------------------------------
    # 4. Date Verification
    # ------------------------------------------------------
    def check_dates(self):
        full_text = "\n".join(self.pages_text)
        normalized = re.sub(r"\s+", " ", full_text)

        for label in self.config["required_date_labels"]:
            if label.lower() not in normalized.lower():
                self.report.add(
                    "4. Date Verification", "FAIL",
                    f"Required date field '{label}' not found in document"
                )

        date_regex = self.config["date_display_regex"]
        all_dates = re.findall(date_regex, normalized)
        if not all_dates:
            self.report.add(
                "4. Date Verification", "WARN",
                f"No dates matching expected format found (pattern: {date_regex})"
            )
        else:
            for d in all_dates:
                if not self._is_valid_date(d):
                    self.report.add(
                        "4. Date Verification", "FAIL",
                        f"Date '{d}' matches format pattern but is not a "
                        "valid calendar date"
                    )

    @staticmethod
    def _is_valid_date(date_str):
        for fmt in ("%d %b %Y", "%d %B %Y"):
            try:
                datetime.strptime(date_str, fmt)
                return True
            except ValueError:
                continue
        return False

    # ------------------------------------------------------
    def run_all(self):
        self.check_page_numbers()
        self.check_manufacturer_info()
        self.check_regulatory_symbols()
        self.check_dates()
        return self.report
