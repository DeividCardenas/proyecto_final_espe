-- Datos sintéticos reproducibles para las pruebas de integración (sin acceso a la API SODA).
-- Uso (tras `alembic upgrade head`):
--   psql "$SYNC_DATABASE_URL_SIN_DIALECTO" -f tests/fixtures/seed_synthetic.sql
-- Genera ~60 000 siniestros 2023-2025 repartidos en 2 500 cuadras de Chicago, con
-- vehículos, personas, aforos AADT y obras. No sustituye a los datos reales.
SELECT setseed(0.42);

TRUNCATE silver_people, silver_vehicles, silver_crashes, silver_traffic_counts, silver_road_permits CASCADE;

CREATE TEMP TABLE blocks AS
SELECT b AS block_id,
       -87.90 + random() * 0.33 AS lon,
       41.66 + random() * 0.34 AS lat,
       (100 * (1 + floor(random() * 80)))::int AS street_no,
       (ARRAY['N', 'S', 'E', 'W'])[1 + floor(random() * 4)::int] AS street_direction,
       (ARRAY['ASHLAND AVE', 'WESTERN AVE', 'HALSTED ST', 'CICERO AVE', 'PULASKI RD', 'MICHIGAN AVE',
              'STATE ST', 'CLARK ST', 'MADISON ST', 'CHICAGO AVE', 'NORTH AVE', 'FULLERTON AVE',
              'BELMONT AVE', 'IRVING PARK RD', 'LAWRENCE AVE', 'DAMEN AVE', 'KEDZIE AVE', '79TH ST',
              '63RD ST', '47TH ST'])[1 + floor(random() * 20)::int] AS street_name,
       power(random(), 3) AS hazard
FROM generate_series(1, 2500) b;

INSERT INTO silver_crashes (
    crash_record_id, crash_date, posted_speed_limit, traffic_control_device, weather_condition,
    lighting_condition, first_crash_type, trafficway_type, roadway_surface_cond, damage, prim_contributory_cause,
    street_no, street_direction, street_name, beat_of_occurrence, num_units, most_severe_injury,
    injuries_total, injuries_fatal, injuries_incapacitating, injuries_non_incapacitating,
    injuries_reported_not_evident, crash_hour, crash_day_of_week, crash_month, latitude, longitude,
    geom, geom_3435, lane_cnt, intersection_related_i, hit_and_run_i, active_workzone,
    aadt_volume, aadt_distance_m, aadt_imputed)
SELECT 'SYN' || lpad(s::text, 7, '0'),
       d.ts,
       (ARRAY[25, 30, 30, 30, 35, 35, 40, 45])[1 + floor(random() * 8)::int],
       (ARRAY['NO CONTROLS', 'TRAFFIC SIGNAL', 'STOP SIGN/FLASHER', 'UNKNOWN'])[1 + floor(random() * 4)::int],
       (ARRAY['CLEAR', 'CLEAR', 'CLEAR', 'RAIN', 'SNOW', 'CLOUDY/OVERCAST', 'UNKNOWN'])[1 + floor(random() * 7)::int],
       (ARRAY['DAYLIGHT', 'DAYLIGHT', 'DARKNESS, LIGHTED ROAD', 'DARKNESS', 'DUSK', 'DAWN'])[1 + floor(random() * 6)::int],
       (ARRAY['REAR END', 'ANGLE', 'TURNING', 'PARKED MOTOR VEHICLE', 'SIDESWIPE SAME DIRECTION', 'PEDESTRIAN',
              'PEDALCYCLIST', 'FIXED OBJECT'])[1 + floor(random() * 8)::int],
       (ARRAY['NOT DIVIDED', 'DIVIDED - W/MEDIAN (NOT RAISED)', 'ONE-WAY', 'FOUR WAY'])[1 + floor(random() * 4)::int],
       (ARRAY['DRY', 'DRY', 'WET', 'SNOW OR SLUSH'])[1 + floor(random() * 4)::int],
       (ARRAY['OVER $1,500', '$501 - $1,500', '$500 OR LESS'])[1 + floor(random() * 3)::int],
       (ARRAY['FAILING TO YIELD RIGHT-OF-WAY', 'FOLLOWING TOO CLOSELY', 'UNABLE TO DETERMINE',
              'IMPROPER TURNING/NO SIGNAL', 'EXCEEDING SAFE SPEED FOR CONDITIONS'])[1 + floor(random() * 5)::int],
       b.street_no::text, b.street_direction, b.street_name,
       (100 + floor(random() * 2400))::int::text,
       2,
       'NO INDICATION OF INJURY',
       inj.total, inj.fatal, inj.incap, inj.nonincap, inj.notevident,
       extract(hour FROM d.ts)::int, extract(isodow FROM d.ts)::int % 7 + 1, extract(month FROM d.ts)::int,
       p.lat, p.lon,
       ST_SetSRID(ST_MakePoint(p.lon, p.lat), 4326),
       ST_Transform(ST_SetSRID(ST_MakePoint(p.lon, p.lat), 4326), 3435),
       (1 + floor(random() * 4))::int,
       random() < 0.3, random() < 0.1, random() < 0.05,
       (5000 + random() * 40000)::int, random() * 600, random() < 0.4
FROM generate_series(1, 60000) s
CROSS JOIN LATERAL (SELECT 1 + floor(power(random(), 1.6) * 2500 + 0 * s)::int AS block_id) pick
JOIN blocks b USING (block_id)
CROSS JOIN LATERAL (SELECT timestamp '2023-01-01' + (random() + 0 * s) * (timestamp '2025-12-31' - timestamp '2023-01-01') AS ts) d
CROSS JOIN LATERAL (SELECT b.lon + (random() - 0.5) * 0.002 AS lon, b.lat + (random() - 0.5) * 0.002 AS lat) p
CROSS JOIN LATERAL (
    SELECT (random() + 0 * s < 0.002 + 0.01 * b.hazard)::int AS fatal,
           (random() < 0.01 + 0.04 * b.hazard)::int AS incap,
           (random() < 0.08)::int AS nonincap,
           (random() < 0.06)::int AS notevident
) i0
CROSS JOIN LATERAL (SELECT i0.fatal AS fatal, i0.incap AS incap, i0.nonincap AS nonincap,
                           i0.notevident AS notevident,
                           i0.fatal + i0.incap + i0.nonincap + i0.notevident AS total) inj;

UPDATE silver_crashes SET workzone_permit_id = 'SYNP' || (1 + floor(random() * 300))::int WHERE active_workzone;

INSERT INTO silver_vehicles (crash_record_id, vehicle_id, unit_no, unit_type, vehicle_type, maneuver, vehicle_year)
SELECT c.crash_record_id, c.crash_record_id || '-' || u, u,
       CASE WHEN u = 2 AND c.first_crash_type = 'PEDESTRIAN' THEN 'PEDESTRIAN'
            WHEN u = 2 AND c.first_crash_type = 'PEDALCYCLIST' THEN 'BICYCLE' ELSE 'DRIVER' END,
       'PASSENGER', 'STRAIGHT AHEAD', 2010 + floor(random() * 15)::int
FROM silver_crashes c CROSS JOIN generate_series(1, 2) u;

INSERT INTO silver_people (crash_record_id, person_id, vehicle_id, person_type, sex, age, injury_classification)
SELECT c.crash_record_id, 'P' || c.crash_record_id, c.crash_record_id || '-1', 'DRIVER',
       (ARRAY['M', 'F'])[1 + floor(random() * 2)::int], 18 + floor(random() * 60)::int, 'NO INDICATION OF INJURY'
FROM silver_crashes c;

INSERT INTO silver_traffic_counts (id, traffic_volume_count_location_address, street, date_of_count,
                                   total_passing_vehicle_volume, vehicle_volume_by_each_direction_of_traffic,
                                   latitude, longitude, geom, geom_3435)
SELECT s, (100 * s)::text, 'SYNTHETIC ST', timestamp '2006-01-01', (3000 + random() * 50000)::int, 'East Bound: 1',
       p.lat, p.lon, ST_SetSRID(ST_MakePoint(p.lon, p.lat), 4326),
       ST_Transform(ST_SetSRID(ST_MakePoint(p.lon, p.lat), 4326), 3435)
FROM generate_series(1, 1200) s
CROSS JOIN LATERAL (SELECT -87.90 + random() * 0.33 + 0 * s AS lon, 41.66 + random() * 0.34 AS lat) p;

INSERT INTO silver_road_permits (id, permit_number, work_type, work_type_description, street_closure,
                                 application_start_date, application_end_date, street_number, street_direction,
                                 street_name, latitude, longitude, geom, geom_3435)
SELECT s, 'SYNP' || s, 'OPENING', 'Street opening', (ARRAY['Full', 'Partial'])[1 + (s % 2)],
       d.start, d.start + (5 + floor(random() * 60)) * interval '1 day', '100', 'N', 'SYNTHETIC ST',
       p.lat, p.lon, ST_SetSRID(ST_MakePoint(p.lon, p.lat), 4326),
       ST_Transform(ST_SetSRID(ST_MakePoint(p.lon, p.lat), 4326), 3435)
FROM generate_series(1, 300) s
CROSS JOIN LATERAL (SELECT timestamp '2025-06-01' + (random() + 0 * s) * interval '200 days' AS start) d
CROSS JOIN LATERAL (SELECT -87.90 + random() * 0.33 + 0 * s AS lon, 41.66 + random() * 0.34 AS lat) p;

ANALYZE;
