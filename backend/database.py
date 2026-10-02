from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = "postgresql+psycopg://postgres:Rmikn%401117@localhost:5432/hospital_db"


engine = create_engine(
    DATABASE_URL
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


def initialize_database():

    with engine.begin() as connection:

        # -------------------------------------------------
        # BEDS
        # -------------------------------------------------

        connection.execute(
            text("""
                ALTER TABLE beds
                ADD COLUMN IF NOT EXISTS expected_release_at TIMESTAMP
            """)
        )


        # -------------------------------------------------
        # PROCEDURES
        # -------------------------------------------------

        connection.execute(
            text("""
                CREATE TABLE IF NOT EXISTS procedures (
                    procedure_id SERIAL PRIMARY KEY,
                    patient_id VARCHAR(20)
                        REFERENCES patients(patient_id),
                    bed_id VARCHAR(20)
                        REFERENCES beds(bed_id),
                    procedure_name VARCHAR(100) NOT NULL,
                    status VARCHAR(30) NOT NULL,
                    expected_end_at TIMESTAMP
                )
            """)
        )


        # -------------------------------------------------
        # RECOMMENDATIONS
        # -------------------------------------------------

        connection.execute(
            text("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    recommendation_id SERIAL PRIMARY KEY,
                    patient_id VARCHAR(20) NOT NULL
                        REFERENCES patients(patient_id),
                    recommendation_type VARCHAR(50) NOT NULL,
                    recommended_bed_id VARCHAR(20),
                    recommended_staff_id VARCHAR(20),
                    recommended_equipment_id VARCHAR(20),
                    reason TEXT NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        )


        # -------------------------------------------------
        # RECOMMENDATION DECISIONS
        # -------------------------------------------------

        connection.execute(
            text("""
                CREATE TABLE IF NOT EXISTS recommendation_decisions (
                    decision_id SERIAL PRIMARY KEY,
                    patient_id VARCHAR(20) NOT NULL
                        REFERENCES patients(patient_id),
                    recommendation_id INT,
                    decision VARCHAR(20) NOT NULL,
                    recommended_bed_id VARCHAR(20),
                    modified_bed_id VARCHAR(20),
                    modified_staff_id VARCHAR(20),
                    modified_equipment_id VARCHAR(20),
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        )


        # -------------------------------------------------
        # EXISTING COLUMN MIGRATIONS
        # -------------------------------------------------

        connection.execute(
            text("""
                ALTER TABLE recommendation_decisions
                ADD COLUMN IF NOT EXISTS recommendation_id INT
            """)
        )


        connection.execute(
            text("""
                ALTER TABLE recommendation_decisions
                ADD COLUMN IF NOT EXISTS modified_staff_id VARCHAR(20)
            """)
        )


        connection.execute(
            text("""
                ALTER TABLE recommendation_decisions
                ADD COLUMN IF NOT EXISTS modified_equipment_id VARCHAR(20)
            """)
        )


        # -------------------------------------------------
        # USERS
        # -------------------------------------------------

        connection.execute(
            text("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(20) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(150) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(30) NOT NULL DEFAULT 'VIEWER',
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        )


        # -------------------------------------------------
        # AUTHENTICATION / EMAIL OTP
        # -------------------------------------------------

        connection.execute(
            text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS email_verified BOOLEAN
                NOT NULL DEFAULT FALSE
            """)
        )


        connection.execute(
            text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS otp_hash VARCHAR(255)
            """)
        )


        connection.execute(
            text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS otp_expires_at TIMESTAMP
            """)
        )


        connection.execute(
            text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS otp_attempts VARCHAR(10)
                NOT NULL DEFAULT '0'
            """)
        )