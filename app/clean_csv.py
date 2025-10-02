import csv
import os
import io

INPUT = os.path.join("data", "train.csv")
OUTPUT = os.path.join("data", "train_clean.csv")
EXPECTED_COLS = ["question_id", "title", "question", "best_answer"]

def detect_dialect_and_header(sample_bytes=8192):
    with open(INPUT, "rb") as f:
        sample = f.read(sample_bytes)
    try:
        sample_text = sample.decode("utf-8")
    except Exception:
        sample_text = sample.decode("latin1", errors="replace")
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample_text, delimiters=[",", "\t", ";", "|"])
    except csv.Error:
        dialect = csv.get_dialect("excel")
    has_header = sniffer.has_header(sample_text)
    return dialect, has_header

def sanitize_field(s):
    if s is None:
        return ""
    return s.replace("\r", " ").replace("\n", " ").strip()

def process():
    print("Detectando dialecto y si hay header...")
    dialect, has_header = detect_dialect_and_header()
    print("Dialect detected: delimiter='{}' quoting={} escapechar={}".format(dialect.delimiter, dialect.quotechar, dialect.escapechar))
    print("Header detected by sniffer?:", has_header)
    total_in = 0
    total_out = 0
    total_bad = 0

    with open(INPUT, "r", encoding="utf-8", errors="replace", newline="") as fin, \
         open(OUTPUT, "w", encoding="utf-8", newline="") as fout:
        reader = csv.reader(fin, dialect)
        writer = csv.writer(fout, quoting=csv.QUOTE_ALL)
        writer.writerow(EXPECTED_COLS)
        skip_first = False
        try:
            first_row = next(reader)
            total_in += 1
        except StopIteration:
            print("Archivo vacío.")
            return

        first_row_lc = [c.strip().lower() for c in first_row]
        if has_header:
            skip_first = True
        else:
            for name in EXPECTED_COLS:
                if name in first_row_lc:
                    skip_first = True
        if skip_first:
            print("Se omite la primera fila como header detectado.")
        else:
            pass

        rows_iter = reader
        if not skip_first:
            def gen():
                yield first_row
                for r in reader:
                    yield r
            rows_iter = gen()

        for i, row in enumerate(rows_iter, start=1):
            total_in += 1
            try:
                if len(row) == 0:
                    total_bad += 1
                    continue

                if len(row) >= 4:
                    qid = sanitize_field(row[0])
                    title = sanitize_field(row[1])
                    question = sanitize_field(row[2])
                    if len(row) == 4:
                        best = sanitize_field(row[3])
                    else:
                        best = sanitize_field(dialect.delimiter.join(row[3:]))
                    writer.writerow([qid, title, question, best])
                    total_out += 1
                else:
                    if len(row) == 3:
                        qid = sanitize_field(row[0])
                        title = sanitize_field(row[1])
                        question = ""
                        best = sanitize_field(row[2])
                        writer.writerow([qid, title, question, best])
                        total_out += 1
                    else:
                        total_bad += 1
            except Exception as e:
                total_bad += 1
                if total_bad % 10000 == 0:
                    print(f"Warnings: {total_bad} bad lines so far. Last error: {e}")

    print("Proceso completado.")
    print(f"Filas leídas (estimado): {total_in}")
    print(f"Filas escritas en limpio: {total_out}")
    print(f"Filas omitidas: {total_bad}")
    print("Archivo limpio generado:", OUTPUT)

if __name__ == "__main__":
    process()
