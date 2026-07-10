import fitz
import os

pdfs = [
    r"C:\Users\szh\Desktop\319459894f777b89f8f9eb0c253af680fde8.pdf",
    r"C:\Users\szh\Desktop\Static_axial_overloading_primes_lumbar_caprine_int.pdf",
    r"C:\Users\szh\Desktop\2045-709x-21-13.pdf"
]

out_dir = r"C:\Users\szh\Desktop\quant_learn\pdf_output"
os.makedirs(out_dir, exist_ok=True)

for path in pdfs:
    basename = os.path.splitext(os.path.basename(path))[0]
    out_path = os.path.join(out_dir, basename + ".txt")
    try:
        doc = fitz.open(path)
        lines = []
        lines.append(f"File: {os.path.basename(path)}")
        lines.append(f"Pages: {doc.page_count}")
        lines.append("=" * 60)
        for j, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                lines.append(f"\n--- Page {j+1} ---\n")
                lines.append(text)
        doc.close()
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"OK: {basename} -> {out_path}")
    except Exception as e:
        print(f"FAIL: {basename}: {e}")
