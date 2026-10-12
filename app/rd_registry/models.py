from sqlalchemy import func, text

from models import db


class RdRegistryEntry(db.Model):
    """РД, которые операторы вводили при CRM-редактировании карточек товаров или добавили вручную."""

    __tablename__ = "rd_registry"
    __table_args__ = (
        # один и тот же РД в разных категориях или с другим ТНВЭД - разные записи
        db.UniqueConstraint(
            "search_key", "rd_date", "rd_date_to", "category", "subcategory", "tnved_code",
            name="uq_rd_registry_key_dates_category_tnved",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    rd_type = db.Column(db.String(50), nullable=False)
    rd_name = db.Column(db.String(100), nullable=False)
    rd_date = db.Column(db.Date(), nullable=False)
    rd_date_to = db.Column(db.Date(), nullable=False)
    search_key = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False, server_default="", index=True)
    subcategory = db.Column(db.String(64), nullable=False, server_default="")
    tnved_code = db.Column(db.String(50), nullable=False, server_default="", index=True)

    usage_count = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime(), nullable=False, server_default=func.now())
    last_used_at = db.Column(db.DateTime(), nullable=False, server_default=func.now())

    is_archived = db.Column(db.Boolean, nullable=False, default=False, server_default=text("false"))
    # кто и когда последним правил запись вручную (правка или архив/возврат)
    updated_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = db.Column(db.DateTime(), nullable=True)

    created_by = db.relationship("User", foreign_keys=[created_by_id])
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])
