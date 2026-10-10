from sqlalchemy import Column, String, Integer, Float, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.core.database import Base

class SilverCrash(Base):
    __tablename__ = "silver_crashes"
    
    crash_record_id = Column(String, primary_key=True, index=True)
    crash_date = Column(DateTime, index=True)
    posted_speed_limit = Column(Integer)
    traffic_control_device = Column(String)
    device_condition = Column(String)
    weather_condition = Column(String)
    lighting_condition = Column(String)
    first_crash_type = Column(String)
    trafficway_type = Column(String)
    alignment = Column(String)
    roadway_surface_cond = Column(String)
    road_defect = Column(String)
    report_type = Column(String)
    crash_type = Column(String)
    damage = Column(String)
    date_police_notified = Column(DateTime)
    prim_contributory_cause = Column(String)
    sec_contributory_cause = Column(String)
    street_no = Column(String)
    street_direction = Column(String)
    street_name = Column(String)
    beat_of_occurrence = Column(String)
    num_units = Column(Integer)
    most_severe_injury = Column(String)
    injuries_total = Column(Integer, default=0)
    injuries_fatal = Column(Integer, default=0)
    injuries_incapacitating = Column(Integer, default=0)
    injuries_non_incapacitating = Column(Integer, default=0)
    injuries_reported_not_evident = Column(Integer, default=0)
    injuries_no_indication = Column(Integer, default=0)
    injuries_unknown = Column(Integer, default=0)
    crash_hour = Column(Integer)
    crash_day_of_week = Column(Integer)
    crash_month = Column(Integer)
    latitude = Column(Float)
    longitude = Column(Float)
    
    # PostGIS geometry column using SRID 4326 (WGS 84)
    geom = Column(Geometry('POINT', srid=4326, spatial_index=True))
    # Projected geometry column using SRID 3435 (Illinois East) for metric distance calculations
    geom_3435 = Column(Geometry('POINT', srid=3435, spatial_index=True))

    vehicles = relationship("SilverVehicle", back_populates="crash", cascade="all, delete")
    people = relationship("SilverPerson", back_populates="crash", cascade="all, delete")

class SilverVehicle(Base):
    __tablename__ = "silver_vehicles"
    
    crash_record_id = Column(String, ForeignKey("silver_crashes.crash_record_id", ondelete="CASCADE"), primary_key=True)
    vehicle_id = Column(String, primary_key=True)
    unit_no = Column(Integer)
    unit_type = Column(String)
    make = Column(String)
    model = Column(String)
    vehicle_year = Column(Integer)
    vehicle_defect = Column(String)
    vehicle_type = Column(String)
    vehicle_use = Column(String)
    travel_direction = Column(String)
    maneuver = Column(String)
    occupant_cnt = Column(Integer)
    first_contact_point = Column(String)

    crash = relationship("SilverCrash", back_populates="vehicles")

class SilverPerson(Base):
    __tablename__ = "silver_people"
    
    crash_record_id = Column(String, ForeignKey("silver_crashes.crash_record_id", ondelete="CASCADE"), primary_key=True)
    person_id = Column(String, primary_key=True)
    vehicle_id = Column(String) # Can be null for pedestrians
    person_type = Column(String)
    seat_no = Column(String)
    city = Column(String)
    state = Column(String)
    zipcode = Column(String)
    sex = Column(String)
    age = Column(Integer)
    safety_equipment = Column(String)
    airbag_deployed = Column(String)
    ejection = Column(String)
    injury_classification = Column(String)
    driver_action = Column(String)
    driver_vision = Column(String)
    physical_condition = Column(String)

    crash = relationship("SilverCrash", back_populates="people")

class SilverTrafficCount(Base):
    __tablename__ = "silver_traffic_counts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    traffic_volume_count_location_address = Column(String)
    street = Column(String)
    date_of_count = Column(DateTime)
    total_passing_vehicle_volume = Column(Integer)
    vehicle_volume_by_each_direction_of_traffic = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    
    geom = Column(Geometry('POINT', srid=4326, spatial_index=True))
    geom_3435 = Column(Geometry('POINT', srid=3435, spatial_index=True))

class SilverRoadPermit(Base):
    __tablename__ = "silver_road_permits"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    permit_number = Column(String, index=True)
    work_type = Column(String)
    application_start_date = Column(DateTime)
    issue_date = Column(DateTime)
    application_end_date = Column(DateTime)
    street_number = Column(String)
    street_direction = Column(String)
    street_name = Column(String)
    work_description = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    
    geom = Column(Geometry('POINT', srid=4326, spatial_index=True))
    geom_3435 = Column(Geometry('POINT', srid=3435, spatial_index=True))
