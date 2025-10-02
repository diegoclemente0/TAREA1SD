import csv, time, random, argparse
import requests
import numpy as np
from datetime import datetime
import json

API_URL = "http://127.0.0.1:8000/query"

def load_questions(path, limit=None):
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i,row in enumerate(reader):
            qid = row.get("question_id") or str(i)
            rows.append({
                "question_id": qid,
                "title": row.get("title",""),
                "question": row.get("question",""),
                "best_answer": row.get("best_answer","")
            })
            if limit and len(rows) >= limit:
                break
    return rows

def send_request(q):
    t0 = time.time()
    try:
        r = requests.post(API_URL, json=q, timeout=30)
        latency = int((time.time()-t0)*1000)
        r.raise_for_status()
        resp = r.json()
        return True, resp, latency
    except Exception as e:
        latency = int((time.time()-t0)*1000)
        return False, str(e), latency

def poisson_send(questions, writer, lambda_rate=1.0, total_requests=1000):
    for i in range(total_requests):
        q = random.choice(questions)
        ok, resp, latency = send_request(q)
        ts = datetime.utcnow().isoformat()
        if ok:
            writer.writerow([
                i+1,
                q["question_id"],
                resp.get("served_from"),
                latency,
                resp.get("score"),
                resp.get("qa_id"),
                resp.get("response_length") or len(json.dumps(resp)),
                ts
            ])
        else:
            writer.writerow([i+1, q["question_id"], "error", latency, "", "", "", ts])
        wait = np.random.exponential(1.0/lambda_rate)
        time.sleep(wait)

def zipf_send(questions, writer, s=1.2, total_requests=1000):
    n = len(questions)
    ranks = np.arange(1, n+1)
    probs = 1.0/(ranks**s)
    probs /= probs.sum()
    indices = np.random.choice(n, size=total_requests, p=probs)
    for i, idx in enumerate(indices):
        q = questions[idx]
        ok, resp, latency = send_request(q)
        ts = datetime.utcnow().isoformat()
        if ok:
            writer.writerow([
                i+1,
                q["question_id"],
                resp.get("served_from"),
                latency,
                resp.get("score"),
                resp.get("qa_id"),
                resp.get("response_length") or len(json.dumps(resp)),
                ts
            ])
        else:
            writer.writerow([i+1, q["question_id"], "error", latency, "", "", "", ts])
        time.sleep(0.01)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="data/train_clean.csv")
    parser.add_argument("--mode", choices=["poisson","zipf"], default="poisson")
    parser.add_argument("--total", type=int, default=1000)
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--out", default="data/results_traffic.csv")
    args = parser.parse_args()

    qs = load_questions(args.csv, limit=args.limit)

    with open(args.out, "w", newline="", encoding="utf8") as outf:
        writer = csv.writer(outf)
        writer.writerow([
            "iteration","question_id","served_from",
            "latency_ms","score","qa_id","response_length","timestamp"
        ])
        if args.mode == "poisson":
            poisson_send(qs, writer, lambda_rate=1.0, total_requests=args.total)
        else:
            zipf_send(qs, writer, s=1.2, total_requests=args.total)

