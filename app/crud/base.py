import math
from typing import Any

from geoalchemy2 import WKBElement
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import func, select


def calculate_distance(db: Session, point_a: WKBElement, point_b: WKBElement) -> float:
    try:
        stmt = select(func.ST_DistanceSphere(point_a, point_b))
        distance = db.execute(stmt).scalar()
        return float(distance)
    except (SQLAlchemyError, DBAPIError) as e:
        raise Exception(f"Failed to calculate distance between {point_a} and {point_b}: {str(e)}")


def paginate(db: Session, query: Any, page: int, size: int) -> dict[str, Any]:
    try:
        page = max(page, 1)
        size = max(size, 1)

        count = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()

        offset = (page - 1) * size
        query = query.limit(size).offset(offset)

        data = db.execute(query).mappings().all()

        return {
            "data": data,
            "meta": {
                "total": count,
                "per_page": size,
                "current_page": page,
                "last_page": max(1, math.ceil(count / size)),
                "start": offset + 1 if count else 0,
                "end": offset + len(data),
            },
        }

    except (SQLAlchemyError, DBAPIError) as e:
        raise Exception(f"Failed to paginate query: {str(e)}")
