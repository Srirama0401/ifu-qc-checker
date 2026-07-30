"""
Batch runner — drop your PDF(s) into input_pdfs/ and run this script.

    python run.py                # process every PDF in input_pdfs/
    python run.py mydoc.pdf      # process a single PDF (any path)

Reports are printed to console and saved as JSON in output_reports/.
Exit code is non-zero if ANY processed PDF fails its checks
(useful for CI pipelines).
"""

import sys
from pathlib import Path

from config import CONFIG
from src.ifu_qc_checker import IFUQualityChecker

ROOT = Path(__file__).parent
INPUT_DIR = ROOT / "input_pdfs"
OUTPUT_DIR = ROOT / "output_reports"


def process_pdf(pdf_path: Path) -> bool:
    """Run all checks on one PDF, print + save report. Returns True if passed."""
    print(f"\nProcessing: {pdf_path.name}")
    try:
        checker = IFUQualityChecker(pdf_path, CONFIG)
    except Exception as e:
        print(f"  ❌ Could not read PDF: {e}")
        return False

    report = checker.run_all()
    report.print_report()

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"{pdf_path.stem}.qc_report.json"
    report.to_json(out_path)
    print(f"Report saved to: {out_path}")

    return report.passed()


def main():
    if len(sys.argv) > 1:
        # Single file mode — any path given on the command line
        pdf_files = [Path(sys.argv[1])]
    else:
        # Batch mode — everything dropped into input_pdfs/
        INPUT_DIR.mkdir(exist_ok=True)
        pdf_files = sorted(INPUT_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found. Add files to '{INPUT_DIR}/' and re-run,")
        print("or pass a path directly: python run.py path/to/file.pdf")
        sys.exit(1)

    results = {}
    for pdf_path in pdf_files:
        if not pdf_path.exists():
            print(f"File not found: {pdf_path}")
            results[str(pdf_path)] = False
            continue
        results[pdf_path.name] = process_pdf(pdf_path)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, passed in results.items():
        print(f"  {'PASS ✅' if passed else 'FAIL ❌'}  {name}")

    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
