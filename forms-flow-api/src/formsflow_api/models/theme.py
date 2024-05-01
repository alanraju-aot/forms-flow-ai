"""This manages theme Database Models."""

from sqlalchemy import JSON

from .audit_mixin import AuditDateTimeMixin, AuditUserMixin
from .base_model import BaseModel
from .db import db


class ThemeCustomization(AuditDateTimeMixin, AuditUserMixin, BaseModel, db.Model):
    """This class manages form process mapper information."""

    id = db.Column(db.Integer, primary_key=True)
    logo_name = db.Column(db.String(50), nullable=False)
    logo_type = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(100), nullable=False)
    application_title = db.Column(db.String(50), nullable=False)
    theme = db.Column(JSON, nullable=False)
    tenant = db.Column(db.String(20), nullable=True)

    @classmethod
    def create_theme(cls, theme_info: dict):
        """Create new theme."""
        if theme_info:
            theme = cls()
            theme.created_by = theme_info["created_by"]
            theme.logo_name = theme_info.get("logo_name")
            theme.logo_type = theme_info.get("logo_type")
            theme.value = theme_info.get("value")
            theme.application_title = theme_info.get("application_title")
            theme.tenant = theme_info.get("tenant")
            theme.theme = theme_info.get("theme")
            theme.save()
            return theme
        return None

    def update(self, theme_info: dict):
        """Update theme."""
        self.update_from_dict(
            [
                "logo_name",
                "logo_type",
                "value",
                "application_title",
                "theme",
            ],
            theme_info,
        )
        self.commit()

    @classmethod
    def get_theme(cls, tenant: str = None):
        """Find application that matches the provided id."""
        # For multi tenant setup there would be multiple records in this table,
        # so match with tenant and return the record.
        # For a non-multi tenant setup there SHOULD be only one record in this table, so return the record
        if tenant:
            return cls.query.filter(cls.tenant == tenant).one_or_none()
        return cls.query.one_or_none()
