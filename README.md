# Movie Recommendation Dashboard

Public Streamlit dashboard for movie recommendations. The application reads movie data from Neon PostgreSQL and does not include the Airflow pipeline or local data files.

## Local run

Install the dependencies from `requirements.txt`, configure the Neon variables listed below in a local `.env`, then run:

```bash
python -m streamlit run app/app.py
```

## Configuration

Configure these values as deployment secrets/environment variables. Use a Neon database role with read-only access to `movie_info`, `movie_genres`, and `director_info`; do not use an owner/admin role for a public app.

```toml
NEON_DB_NAME = "..."
NEON_DB_USER = "..."
NEON_DB_PASSWORD = "..."
NEON_DB_HOST = "..."
NEON_DB_PORT = "5432"
NEON_DB_SSLMODE = "require"
```

Never commit `.env` or deployment credentials.
