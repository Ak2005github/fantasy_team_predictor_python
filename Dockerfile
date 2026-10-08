FROM python:3.11-slim

# Fixed hash seed so set iteration, and therefore every run, is reproducible
ENV PYTHONHASHSEED=0 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fantasy_predictor/ fantasy_predictor/
COPY data/ data/
COPY Final_id_data_all.csv ipl_2025_matches.csv ipl_2025_matches_corrected.csv \
     ipl_2025_points_table.csv ipl_match_dates.csv ./

# Usage: docker run --name ipl30 -e CRICAPI_KEY=<key> fantasy-predictor 30
ENTRYPOINT ["python", "-m", "fantasy_predictor"]
