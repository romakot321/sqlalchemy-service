"""Library for simple management for database connection management and queries build"""

from sqlalchemy_service.base_db.base import Base
from sqlalchemy_service.base_service.service import BaseService


__all__ = ["BaseService", "Base"]
