README.md
markdown# Medical Telegram Data Warehouse

End-to-end ELT pipeline scraping Ethiopian medical Telegram channels into a
structured analytical data warehouse.

**Built for:** 10 Academy KAIM Week 8  
**Stack:** Telethon · PostgreSQL · dbt · YOLOv8 · FastAPI · Dagster

---

## Pipeline Overview

Telegram Channels

↓

Telethon scraper → data/raw/ (JSON + images)

↓

load_to_postgres → raw.telegram_messages (PostgreSQL)

↓

dbt staging → staging.stg_telegram_messages

↓

dbt marts → dim_channels · dim_dates · fct_messages

↓

YOLOv8 → fct_image_detections

↓

FastAPI → /api/reports/\* endpoints

## Channels Scraped

| Channel            | Type                |
| ------------------ | ------------------- |
| @lobelia4cosmetics | Cosmetics & Health  |
| @tikvahpharma      | Pharmaceuticals     |
| @CheMed123         | Medical Supplies    |
| @DoctorsET         | Medical Information |

## Project Structure

medical-telegram-warehouse/

├── src/

│ ├── scraper.py # Telegram scraper (Telethon)

│ ├── datalake.py # Data lake read/write utilities

│ ├── load_to_postgres.py # Loads JSON into PostgreSQL

│ └── yolo_detect.py # YOLO enrichment for downloaded images

├── api/ # FastAPI analytical API

│ ├── main.py

│ ├── database.py

│ └── schemas.py

├── medical_warehouse/ # dbt project

│ ├── models/

│ │ ├── staging/ # stg_telegram_messages

│ │ └── marts/ # dim_channels, dim_dates, fct_messages, fct_image_detections

│ └── tests/ # Custom data quality tests

├── workflows/

│ └── dagster_pipeline.py # Dagster orchestration entry point

├── notebooks/

│ ├── task1_scraping.ipynb

│ └── task2_dbt.ipynb

├── data/ # Data lake (gitignored)

├── logs/ # Scrape logs (gitignored)

├── .env # Credentials (never commit)

└── docker-compose.yml # PostgreSQL container

## Quickstart

**1. Clone and install dependencies**

```bash
pip install -r requirements.txt
```

**2. Set up credentials — create a `.env` file:**
Tg_API_ID=your_api_id

Tg_API_HASH=your_api_hash

DB_HOST=localhost

DB_PORT=5432

DB_NAME=telegram_warehouse

DB_USER=postgres

DB_PASSWORD=postgres

**3. Start PostgreSQL**

```bash
docker compose up -d
```

**4. Run demo scraper (no Telegram auth needed)**

```bash
python src/scraper.py --demo --path data --limit 15
```

**5. Load into PostgreSQL**

```bash
python src/load_to_postgres.py --path data
```

**6. Run dbt transformations**

```bash
cd medical_warehouse
dbt run
dbt test
```

**7. Run YOLO enrichment**

```bash
python src/yolo_detect.py --path data --output data/yolo_results.csv
```

**8. Start the FastAPI app**

```bash
uvicorn api.main:app --reload
```

**9. Run the Dagster pipeline**

```bash
python -m dagster dev -f workflows/dagster_pipeline.py
```

## Data Lake Structure

data/raw/

├── telegram_messages/

│ └── YYYY-MM-DD/

│ ├── lobelia4cosmetics.json

│ ├── tikvahpharma.json

│ ├── CheMed123.json

│ ├── DoctorsET.json

│ └── \_manifest.json

├── images/

│ └── {channel_name}/{message_id}.jpg

└── csv/

└── YYYY-MM-DD/telegram_data.csv

## Star Schema

     dim_channels          dim_dates
     (channel_key)         (date_key)
           ↖                  ↗
              fct_messages
              (message_id)
                   ↓
          fct_image_detections
          (from YOLO — Task 3)

## Security

- Never commit `.env`, `*.session`, or `data/` to git
- Your `.gitignore` must include:
  .env

\*.session

data/

logs/
