import asyncpg, asyncio, os, csv

DSN = os.getenv("DSN", "postgresql://postgres:examplepass@db:5432/qa")

async def main():
    conn = await asyncpg.connect(dsn=DSN)
    rows = await conn.fetch("""
        SELECT served_from, latency_ms
        FROM request_logs;
    """)
    await conn.close()

    total = len(rows)
    hits = sum(1 for r in rows if r["served_from"] == "cache")
    misses = total - hits
    hit_rate = hits / total if total > 0 else 0.0

    print(f"Total: {total}, Hits: {hits}, Misses: {misses}, HitRate: {hit_rate:.2%}")

    with open("/app/data/metrics.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["served_from", "latency_ms"])
        for r in rows:
            writer.writerow([r["served_from"], r["latency_ms"]])

if __name__ == "__main__":
    asyncio.run(main())
