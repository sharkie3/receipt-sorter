# receipt-sorter

Sort receipts and invoices locally with an open-weight model (Gemma) running on Ollama.
No cloud, no API key, and client data never leaves your laptop.

Point it at a folder of receipt photos, PDFs, or text files. It extracts the vendor, date, total, currency, and category, then copies each file to `sorted/<category>/<date>_<vendor>_<total>.ext` and writes a `summary.csv` for your accountant.

```
IMG_4412.jpg -> sorted/meals/2026-10-01_blue-bottle_12.50.jpg
inv_0093.pdf -> sorted/services/2026-09-14_acme-design_850.00.pdf
```

## Setup

1. Install [Ollama](https://ollama.com) and pull a vision model:
   ```
   ollama pull gemma3:4b
   ```
2. Python 3.9+ is the only other requirement. For PDFs, also run `pip install pypdf`.

## Usage

```
python3 receipt_sorter.py ~/Receipts -o ~/Receipts/sorted
```

| Option | Default | Meaning |
|---|---|---|
| `-o, --out` | `sorted` | Output folder |
| `-m, --model` | `gemma3:4b` | Any Ollama vision model (e.g. `gemma3:12b` for harder receipts) |
| `--host` | `http://localhost:11434` | Ollama server |

Categories: software, travel, meals, office, equipment, services, utilities, other.

## Notes

- Originals are copied, never modified or moved.
- Model output is validated: bad dates, unknown categories, and malformed totals fall back to safe defaults (`undated`, `other`, `0.00`).
- One unreadable file is reported and skipped; the rest of the batch continues.
- Always spot-check the results before filing taxes. Small local models can misread blurry receipts.
