# receipt-sorter

Sorts receipts and invoices into `sorted/<category>/<date>_<vendor>_<total>.ext` and writes `summary.csv` for your accountant.
Runs on an open-weight model (Gemma) through Ollama. No cloud, no API key, and client data never leaves your laptop.

## Use
```
ollama pull gemma3:4b
pip install pypdf            # only needed for PDFs
python3 receipt_sorter.py ~/Receipts -o ~/Receipts/sorted
```
Originals are copied, never modified. Swap models with `-m` (any Ollama vision model). Tests: `python3 -m unittest discover -s tests`.
