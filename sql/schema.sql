-- Schema for the Ola Ride Insights database (runs on SQLite and MySQL 8).
-- Loaded by src/build_database.py; statements are separated by ';'.

CREATE TABLE ola_rides (
    booking_id             VARCHAR(20) PRIMARY KEY,
    booking_date           DATE NOT NULL,
    booking_time           VARCHAR(8),
    booking_datetime       VARCHAR(19),
    booking_status         VARCHAR(30) NOT NULL,
    customer_id            VARCHAR(20),
    vehicle_type           VARCHAR(30),
    pickup_location        VARCHAR(80),
    drop_location          VARCHAR(80),
    v_tat                  DECIMAL(10,2),
    c_tat                  DECIMAL(10,2),
    customer_cancel_reason VARCHAR(100),
    driver_cancel_reason   VARCHAR(100),
    incomplete_reason      VARCHAR(100),
    cancelled_by           VARCHAR(20),
    cancel_reason          VARCHAR(100),
    booking_value          DECIMAL(10,2),
    payment_method         VARCHAR(30),
    ride_distance          DECIMAL(8,2),
    driver_rating          DECIMAL(3,1),
    customer_rating        DECIMAL(3,1),
    booking_hour           INT,
    day_name               VARCHAR(10),
    day_of_week_num        INT,
    month_name             VARCHAR(10),
    is_weekend             TINYINT,
    time_slot              VARCHAR(20),
    is_success             TINYINT,
    is_incomplete          TINYINT,
    distance_band          VARCHAR(10),
    fare_per_km            DECIMAL(8,2),
    is_value_imputed       TINYINT,
    is_distance_imputed    TINYINT
);

CREATE TABLE dim_vehicle_type (
    vehicle_type  VARCHAR(30) PRIMARY KEY,
    vehicle_class VARCHAR(20),
    service_tier  VARCHAR(20)
);

CREATE TABLE dim_payment_method (
    payment_method VARCHAR(30) PRIMARY KEY,
    payment_mode   VARCHAR(20)
);

CREATE TABLE dim_date (
    `date`          VARCHAR(10) PRIMARY KEY,
    year            INT,
    month_num       INT,
    month_name      VARCHAR(10),
    day             INT,
    day_name        VARCHAR(10),
    day_of_week_num INT,
    week_of_year    INT,
    is_weekend      TINYINT
);

CREATE INDEX idx_rides_date     ON ola_rides (booking_date);
CREATE INDEX idx_rides_customer ON ola_rides (customer_id);
CREATE INDEX idx_rides_vehicle  ON ola_rides (vehicle_type);
CREATE INDEX idx_rides_status   ON ola_rides (booking_status);

-- One row per customer; used for joins in the analysis queries.
CREATE VIEW v_customer_summary AS
SELECT customer_id,
       COUNT(*)                                                   AS total_bookings,
       SUM(is_success)                                            AS successful_rides,
       SUM(CASE WHEN cancelled_by <> 'Not Applicable' THEN 1 ELSE 0 END) AS cancelled_rides,
       ROUND(SUM(CASE WHEN booking_status = 'Success' THEN booking_value ELSE 0 END), 2) AS total_booking_value,
       ROUND(AVG(customer_rating), 2)                             AS avg_customer_rating
FROM ola_rides
GROUP BY customer_id;
