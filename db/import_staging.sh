#!/bin/bash
set -e

CONTAINER=$(docker-compose ps -q db)

# Copiar el CSV dentro del contenedor
echo "📂 Copiando CSV al contenedor..."
docker cp ./data/train.csv $CONTAINER:/tmp/train.csv

# Importar CSV a tabla staging
echo "📥 Importando CSV a tabla staging..."
docker exec -i $CONTAINER psql -U postgres -d qa -c "\copy staging_raw(question_id,title,question,best_answer) FROM '/tmp/train.csv' CSV HEADER"

# Pasar de staging a qa_records con UPSERT
echo "🔄 Pasando de staging_raw a qa_records..."
docker exec -i $CONTAINER psql -U postgres -d qa -c "
INSERT INTO qa_records (question_id, title, question, best_answer, first_seen, last_seen)
SELECT question_id, title, question, best_answer, now(), now()
FROM staging_raw
ON CONFLICT (question_id) DO UPDATE
  SET title = EXCLUDED.title,
      question = EXCLUDED.question,
      best_answer = EXCLUDED.best_answer,
      last_seen = now();
"

echo "✅ Importación completa"
