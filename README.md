# 🚖 Ola Ride Insights

End-to-end ride-sharing analytics: **data cleaning -> SQL -> Power BI -> Streamlit app -> business insights**.

> **Data note:** the assignment document links to the dataset on Google Drive but does not contain it.
> This repo ships a *synthetic sample* with the same columns and realistic quality problems so everything runs out of the box.
> To use the real data, see **"Using the real dataset"** below. All numbers in `docs/insights.md` are from the sample until you do.

## Project structure
```
data/raw/ola_rides_raw.csv        raw input (sample; replace with real file)
data/processed/ola_rides_clean.csv cleaned output
src/generate_sample_data.py       synthetic raw data generator
src/clean_data.py                 cleaning + feature engineering + quality report
src/build_database.py             loads clean data into SQLite (or MySQL)
src/sql_utils.py                  query loader / read-only runner
src/generate_insights.py          data-driven business findings -> docs/insights.md
sql/schema.sql                    tables, indexes, customer view
sql/queries.sql                   Q1-Q10 (required) + B1-B10 (business insights)
app/streamlit_app.py              dashboard + SQL explorer + Power BI embed
powerbi/                          cleaned tables, theme, DAX, Power Query, build guide
docs/                             data_quality_report.md, insights.md
tests/test_pipeline.py            automated checks
```

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make all            # clean -> database -> insights   (or run the 3 python -m commands in the Makefile)
make test           # 7 tests
make app            # streamlit run app/streamlit_app.py
```

## Using the real dataset
1. Download the OLA dataset from the Drive link in the assignment (CSV or XLSX).
2. Save it as `data/raw/ola_rides_raw.csv` (XLSX works too: `python -m src.clean_data --input path/to/file.xlsx`).
3. Delete `data/raw/SAMPLE_DATA.txt`, then run `make all`.
The loader accepts the standard columns (Date, Time, Booking_ID, Booking_Status, Customer_ID, Vehicle_Type, Pickup_Location,
Drop_Location, V_TAT, C_TAT, Canceled_Rides_by_Customer, Canceled_Rides_by_Driver, Incomplete_Rides, Incomplete_Rides_Reason,
Booking_Value, Payment_Method, Ride_Distance, Driver_Ratings, Customer_Rating) and ignores a "Vehicle Images" column.
If your file's status labels differ (e.g. "Cancelled"), add the spelling to `CANONICAL` in `src/clean_data.py`.
If incomplete rides are *inside* the "Success" status in your file, Q9 will include them - filter on `is_incomplete = 0` if needed.

## Cleaning rules (see docs/data_quality_report.md after running)
Nulls normalised, quotes/whitespace stripped, types parsed, duplicates removed, categories standardised, invalid values nulled,
successful rides' missing fare/distance imputed (flagged), ratings never imputed, derived features added
(hour, weekday, time slot, distance band, fare per km, cancel reason/by, flags).

## SQL
`sql/queries.sql` - Q1-Q10 answer the assignment questions; B1-B10 add peak hours, failure rates, joins to dimension tables,
window functions (cumulative revenue, ranking) and a fare-anomaly screen. Standard SQL: runs on SQLite and MySQL 8.
MySQL: `pip install sqlalchemy pymysql`, then `python -m src.build_database --url mysql+pymysql://user:pw@localhost/ola`.

## Power BI
Open `powerbi/POWERBI_GUIDE.md` - cleaned tables, theme, 20+ DAX measures and a visual-by-visual layout for the five pages
(Overall, Vehicle Type, Revenue, Cancellation, Ratings). Then publish and paste the embed link into the app's **Power BI** tab
(`POWERBI_EMBED_URL`).

## Deploy the Streamlit app
Push to GitHub > share.streamlit.io > main file `app/streamlit_app.py`. Commit `db/ola.db` (or run `make all` in a build step).
Add `POWERBI_EMBED_URL` under *Secrets*.



