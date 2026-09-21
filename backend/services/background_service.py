import asyncio

from backend.database import SessionLocal
from backend.services.procedure_service import (
    refresh_expired_procedures
)
from backend.services.recommendation_service import (
    generate_automatic_recommendation
)


async def background_resource_monitor():

    while True:

        db = SessionLocal()

        try:

            result = refresh_expired_procedures(db)

            if result["completed_procedures"] > 0:

                print(
                    "Background monitor:",
                    result
                )

                for bed_id in result["released_beds"]:

                    recommendation = (
                        generate_automatic_recommendation(
                            db,
                            bed_id
                        )
                    )

                    if recommendation:

                        print(
                            "Automatic recommendation created:",
                            {
                                "recommendation_id":
                                    recommendation.recommendation_id,
                                "patient_id":
                                    recommendation.patient_id,
                                "bed_id":
                                    recommendation.recommended_bed_id
                            }
                        )

                    else:

                        print(
                            "No automatic recommendation created "
                            f"for released bed {bed_id}"
                        )

        except Exception as error:

            print(
                "Background monitor error:",
                error
            )

        finally:

            db.close()

        await asyncio.sleep(10)