-- =====================================================================================
-- Ola Ride Insights - analysis queries (SQLite + MySQL 8 compatible)
-- Block format used by the Streamlit app:  -- @query: <id> | <title>
-- Definitions: "Success" = booking_status 'Success'. Fare/distance/ratings exist only for rides that ran.
-- =====================================================================================

-- ------------------------------ A. Required questions (Q1-Q10) ------------------------------

-- @query: Q1 | Retrieve all successful bookings
SELECT *
FROM ola_rides
WHERE booking_status = 'Success'
ORDER BY booking_datetime;

-- @query: Q2 | Average ride distance for each vehicle type
SELECT vehicle_type,
       ROUND(AVG(ride_distance), 2) AS avg_ride_distance_km,
       COUNT(*)                     AS rides
FROM ola_rides
WHERE ride_distance IS NOT NULL
GROUP BY vehicle_type
ORDER BY avg_ride_distance_km DESC;

-- @query: Q3 | Total number of rides cancelled by customers
SELECT COUNT(*) AS cancelled_by_customers
FROM ola_rides
WHERE booking_status = 'Canceled by Customer';

-- @query: Q4 | Top 5 customers by number of rides booked
SELECT customer_id,
       COUNT(*) AS total_rides
FROM ola_rides
GROUP BY customer_id
ORDER BY total_rides DESC, customer_id
LIMIT 5;

-- @query: Q5 | Rides cancelled by drivers for personal & car-related issues
SELECT COUNT(*) AS driver_cancellations_personal_car_issue
FROM ola_rides
WHERE booking_status = 'Canceled by Driver'
  AND driver_cancel_reason = 'Personal & Car related issue';

-- @query: Q6 | Max and min driver ratings for Prime Sedan bookings
SELECT MAX(driver_rating) AS max_driver_rating,
       MIN(driver_rating) AS min_driver_rating
FROM ola_rides
WHERE vehicle_type = 'Prime Sedan'
  AND driver_rating IS NOT NULL;

-- @query: Q7 | All rides paid via UPI
SELECT *
FROM ola_rides
WHERE payment_method = 'UPI'
ORDER BY booking_datetime;

-- @query: Q8 | Average customer rating per vehicle type
SELECT vehicle_type,
       ROUND(AVG(customer_rating), 2) AS avg_customer_rating,
       COUNT(customer_rating)         AS rated_rides
FROM ola_rides
WHERE customer_rating IS NOT NULL
GROUP BY vehicle_type
ORDER BY avg_customer_rating DESC;

-- @query: Q9 | Total booking value of successfully completed rides
SELECT ROUND(SUM(booking_value), 2) AS total_booking_value,
       COUNT(*)                     AS successful_rides
FROM ola_rides
WHERE booking_status = 'Success';

-- @query: Q10 | All incomplete rides with the reason
SELECT booking_id, booking_date, customer_id, vehicle_type,
       pickup_location, drop_location, incomplete_reason
FROM ola_rides
WHERE is_incomplete = 1
ORDER BY booking_date, booking_id;

-- ------------------------------ B. Business insight queries (joins / aggregations / windows) ------------------------------

-- @query: B1 | Peak demand hours (all bookings) with share of day
SELECT booking_hour,
       COUNT(*)                                              AS bookings,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)    AS pct_of_bookings,
       ROUND(100.0 * SUM(is_success) / COUNT(*), 1)          AS success_rate_pct
FROM ola_rides
WHERE booking_hour IS NOT NULL
GROUP BY booking_hour
ORDER BY bookings DESC;

-- @query: B2 | Cancellation / failure rate by vehicle type and class (JOIN dim_vehicle_type)
SELECT v.vehicle_class,
       r.vehicle_type,
       COUNT(*)                                                                    AS bookings,
       SUM(CASE WHEN r.cancelled_by = 'Customer' THEN 1 ELSE 0 END)                AS cancelled_by_customer,
       SUM(CASE WHEN r.cancelled_by = 'Driver' THEN 1 ELSE 0 END)                  AS cancelled_by_driver,
       SUM(CASE WHEN r.booking_status = 'Driver Not Found' THEN 1 ELSE 0 END)      AS driver_not_found,
       ROUND(100.0 * (COUNT(*) - SUM(r.is_success)) / COUNT(*), 1)                 AS failure_rate_pct
FROM ola_rides r
JOIN dim_vehicle_type v ON v.vehicle_type = r.vehicle_type
GROUP BY v.vehicle_class, r.vehicle_type
ORDER BY failure_rate_pct DESC;

-- @query: B3 | Revenue by payment method and mode (JOIN dim_payment_method)
SELECT p.payment_mode,
       r.payment_method,
       COUNT(*)                         AS rides,
       ROUND(SUM(r.booking_value), 2)   AS revenue,
       ROUND(AVG(r.booking_value), 2)   AS avg_fare
FROM ola_rides r
JOIN dim_payment_method p ON p.payment_method = r.payment_method
WHERE r.booking_status = 'Success'
GROUP BY p.payment_mode, r.payment_method
ORDER BY revenue DESC;

-- @query: B4 | Top 5 customers by total booking value (JOIN customer summary view)
SELECT s.customer_id,
       s.total_bookings,
       s.successful_rides,
       s.total_booking_value,
       ROUND(100.0 * s.cancelled_rides / s.total_bookings, 1) AS cancel_rate_pct,
       s.avg_customer_rating
FROM v_customer_summary s
ORDER BY s.total_booking_value DESC
LIMIT 5;

-- @query: B5 | Daily rides with cumulative revenue (window functions, JOIN dim_date)
SELECT d.date,
       d.day_name,
       COUNT(r.booking_id)                                        AS bookings,
       SUM(r.is_success)                                          AS successful_rides,
       ROUND(SUM(CASE WHEN r.booking_status = 'Success' THEN r.booking_value ELSE 0 END), 2) AS revenue,
       ROUND(SUM(SUM(CASE WHEN r.booking_status = 'Success' THEN r.booking_value ELSE 0 END))
             OVER (ORDER BY d.date), 2)                           AS cumulative_revenue
FROM dim_date d
LEFT JOIN ola_rides r ON r.booking_date = d.date
GROUP BY d.date, d.day_name
ORDER BY d.date;

-- @query: B6 | Customer vs driver rating by vehicle type, ranked
SELECT vehicle_type,
       ROUND(AVG(customer_rating), 2) AS avg_customer_rating,
       ROUND(AVG(driver_rating), 2)   AS avg_driver_rating,
       RANK() OVER (ORDER BY AVG(customer_rating) DESC) AS customer_rank,
       RANK() OVER (ORDER BY AVG(driver_rating) DESC)   AS driver_rank
FROM ola_rides
WHERE customer_rating IS NOT NULL AND driver_rating IS NOT NULL
GROUP BY vehicle_type
ORDER BY customer_rank;

-- @query: B7 | Pickup locations with the most failed bookings
SELECT pickup_location,
       COUNT(*)                                                         AS bookings,
       COUNT(*) - SUM(is_success)                                       AS failed_bookings,
       ROUND(100.0 * (COUNT(*) - SUM(is_success)) / COUNT(*), 1)        AS failure_rate_pct
FROM ola_rides
GROUP BY pickup_location
HAVING COUNT(*) >= 100
ORDER BY failure_rate_pct DESC
LIMIT 10;

-- @query: B8 | Cancellation reasons (customers and drivers)
SELECT cancelled_by,
       cancel_reason,
       COUNT(*) AS cancellations,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY cancelled_by), 1) AS pct_within_party
FROM ola_rides
WHERE cancelled_by <> 'Not Applicable'
GROUP BY cancelled_by, cancel_reason
ORDER BY cancelled_by, cancellations DESC;

-- @query: B9 | Possible fare anomalies: fare/km above 2.5x the average for the same vehicle type and distance band (fraud screening)
SELECT r.booking_id, r.customer_id, r.vehicle_type, r.distance_band, r.ride_distance,
       r.booking_value, r.fare_per_km, ROUND(a.avg_fpk, 2) AS peer_avg_fare_per_km
FROM ola_rides r
JOIN (SELECT vehicle_type, distance_band, AVG(fare_per_km) AS avg_fpk
      FROM ola_rides
      WHERE booking_status = 'Success' AND is_value_imputed = 0 AND is_distance_imputed = 0
      GROUP BY vehicle_type, distance_band) a
  ON a.vehicle_type = r.vehicle_type AND a.distance_band = r.distance_band
WHERE r.booking_status = 'Success'
  AND r.fare_per_km > 2.5 * a.avg_fpk
ORDER BY r.fare_per_km / a.avg_fpk DESC;

-- @query: B10 | Weekday vs weekend performance
SELECT CASE WHEN is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS day_type,
       COUNT(*)                                                   AS bookings,
       ROUND(100.0 * SUM(is_success) / COUNT(*), 1)               AS success_rate_pct,
       ROUND(AVG(CASE WHEN is_success = 1 THEN booking_value END), 2) AS avg_fare
FROM ola_rides
GROUP BY CASE WHEN is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END;
