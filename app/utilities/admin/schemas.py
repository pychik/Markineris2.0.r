from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime, timedelta
from config import settings
from utilities.categories_data.underwear_data import UNDERWEAR_TYPES


ar_categories_types: dict = {settings.Clothes.CATEGORY: settings.Clothes.TYPES + UNDERWEAR_TYPES,
                             settings.Shoes.CATEGORY: settings.Shoes.TYPES,
                             settings.Linen.CATEGORY: settings.Linen.TYPES,
                             settings.Parfum.CATEGORY: settings.Parfum.TYPES,
                             settings.Socks.CATEGORY: settings.Socks.TYPES
                             }


class AROrdersSchema(BaseModel):

    date_from: datetime = Field(
        default_factory=lambda: datetime.now() - timedelta(days=settings.AR_ORDERS_DAYS_DEFAULT),
        description="Start date for orders"
    )
    date_to: datetime = Field(
        default_factory=lambda: datetime.now() + timedelta(days=1),
        description="End date for orders"
    )
    category: str = Field(default=settings.Clothes.CATEGORY)
    category_pos_type: str = Field(default=settings.ALL_CATEGORY_TYPES)

    @field_validator('date_from', 'date_to', mode='before')
    def parse_dates(cls, value, field):
        if isinstance(value, str):
            if value.strip() == '':
                if field.field_name == 'date_from':
                    return datetime.now() - timedelta(days=settings.AR_ORDERS_DAYS_DEFAULT)
                elif field.field_name == 'date_to':
                    return datetime.now() + timedelta(days=1)
            try:
                return datetime.strptime(value, '%Y-%m-%d')
            except ValueError:
                raise ValueError(f"Invalid datetime format for {field.field_name}: {value}")
        return value

    @field_validator('category_pos_type')
    def validate_category_pos_type(cls, value, values):
        category = values.data.get('category')
        if (category and value and value != settings.ALL_CATEGORY_TYPES
                and value not in ar_categories_types.get(category, settings.Clothes.TYPES)):
            raise ValueError(f'Invalid category_pos_type: {value} for category: {category}')
        if category and not value:
            return settings.ALL_CATEGORY_TYPES
        return value

    @field_validator('category')
    def validate_category(cls, value):
        if value not in ar_categories_types:
            raise ValueError(f'Invalid category: {value}')
        return value
