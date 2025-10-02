git clone https://github.com/diegoclemente0/TAREA1SD.git
cd TAREA1SD

# Colocar CSV crudo
mkdir -p data
cp /ruta/a/train.csv data/train.csv

# Crear .env
cat > .env <<EOF
GEMINI_API_KEY=TU_API_KEY
GEMINI_MODEL=models/gemini-2.5-flash
POSTGRES_USER=postgres
POSTGRES_PASSWORD=examplepass
POSTGRES_DB=qa
EOF

# Levantar servicios
docker compose up -d --build

# Limpiar CSV
docker exec -it $(docker compose ps -q app) \
  python clean_csv.py --in data/train.csv --out data/train_clean.csv

# Importar a DB
docker exec -i $(docker compose ps -q db) \
  psql -U postgres -d qa \
  -c "\COPY staging_raw(question_id,title,question,best_answer) FROM '/app/data/train_clean.csv' CSV HEADER;"

# Generar tráfico (10.000 consultas)
docker exec -it $(docker compose ps -q app) \
  python traffic_generator.py --csv data/train_clean.csv --mode poisson --total 10000

# Copiar resultados
docker cp $(docker compose ps -q app):/app/results_traffic.csv ./results_traffic.csv
