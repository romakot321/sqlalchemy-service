"""Library for simple management for database connection management and queries build"""

from sqlalchemy_service.base_service.service import BaseService
from sqlalchemy_service.base_db.base import Base

__all__ = ["BaseService", "Base"]
