"""Generate `sample_report.pdf`: a 3-page fictional annual report with one ruled table.

Run from the repo: `uv run --directory backend python tests/fixtures/make_sample_pdf.py`.
Written with raw PDF syntax so the fixture needs no PDF-writing dependency.
"""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).with_name("sample_report.pdf")

PAGE_1 = [
    "Northwind Outdoor Co. Annual Report 2025",
    "",
    "Northwind Outdoor Co. designs and sells hiking footwear and technical apparel.",
    "The company operates 42 retail stores and an online shop serving customers in",
    "North America and Europe.",
    "",
    "Our mission is to make durable gear that lasts a decade of weekend trips.",
]
PAGE_2_INTRO = ["Revenue by segment (in thousands):"]
TABLE = [["Segment", "2025", "2024"], ["Footwear", "12,400", "11,050"],
         ["Apparel", "8,300", "7,900"], ["Total revenue", "20,700", "18,950"]]  # fmt: skip
PAGE_3 = [
    "Risk factors",
    "",
    "The company's largest supplier is located in Portugal. A disruption at this",
    "supplier could delay deliveries of footwear for several months.",
    "",
    "Weather affects demand: an unusually warm winter reduced sales of insulated boots.",
]


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _text(lines: list[str], x: int, y: int, size: int = 11, leading: int = 16) -> str:
    ops = [f"BT /F1 {size} Tf {leading} TL {x} {y} Td"]
    for line in lines:
        ops.append(f"({_escape(line)}) Tj T*")
    ops.append("ET")
    return "\n".join(ops)


def _table(rows: list[list[str]], x: int, top: int) -> str:
    widths, height = [160, 90, 90], 22
    ops = ["0.5 w"]
    total_w = sum(widths)
    for r in range(len(rows) + 1):
        y = top - r * height
        ops.append(f"{x} {y} m {x + total_w} {y} l S")
    cx = x
    for w in [0, *widths]:
        cx += w
        ops.append(f"{cx} {top} m {cx} {top - len(rows) * height} l S")
    for r, row in enumerate(rows):
        cx = x
        for w, cell in zip(widths, row, strict=True):
            ops.append(f"BT /F1 10 Tf {cx + 6} {top - r * height - 15} Td ({_escape(cell)}) Tj ET")
            cx += w
    return "\n".join(ops)


def build() -> bytes:
    contents = [
        _text(PAGE_1, 72, 720),
        _text(PAGE_2_INTRO, 72, 720) + "\n" + _table(TABLE, 72, 690),
        _text(PAGE_3, 72, 720),
    ]
    n_pages = len(contents)
    # Object numbers: 1 catalog, 2 pages, 3 font, then (page, content) pairs.
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (
            "<< /Type /Pages /Kids ["
            + " ".join(f"{4 + 2 * i} 0 R" for i in range(n_pages))
            + f"] /Count {n_pages} >>"
        ).encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    for i, content in enumerate(contents):
        stream = content.encode("latin-1")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {5 + 2 * i} 0 R >>".encode()
        )
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(out)


if __name__ == "__main__":
    OUT.write_bytes(build())
    print(f"wrote {OUT}")
