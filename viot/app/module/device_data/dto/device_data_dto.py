import re
from datetime import datetime, timedelta
from typing import Annotated, Any, NamedTuple, Self

from fastapi import Depends, Query
from pydantic import Field, computed_field, field_validator, model_validator

from app.common.dto import BaseOutDto
from app.common.dto.base import BaseInDto
from app.database.repository.pagination import SortDirection

from ..constants import AggregationType, IntervalType, Timezone
from ..model.device_data import DeviceData
from ..model.device_data_latest import DeviceDataLatest


def keys_comma_separated_values(value: str) -> set[str]:
    result = re.split(r"\s*,\s*", value)
    result = {item for item in result if item}
    if not result:
        raise ValueError("At least one key is required")
    return result


def start_date_value(
    value: datetime = Query(
        alias="startDate",
        description=(
            "A string value representing the start date in ISO format,"
            " any timezone will be removed."
        ),
        example="2021-01-01T00:00:00",
    ),
) -> datetime:
    return value.replace(tzinfo=None)


def end_date_value(
    value: datetime = Query(
        alias="endDate",
        description=(
            "A string value representing the end date in ISO format,"
            " any timezone will be removed."
        ),
        example="2022-01-01T00:00:00",
    ),
) -> datetime:
    return value.replace(tzinfo=None)


KeySetQuery = Annotated[set[str], Depends(keys_comma_separated_values)]


class TimeseriesAggregationQueryDto(BaseInDto):
    keys__: str = Field(
        alias="keys",
        description="A string value representing the comma-separated list of telemetry keys.",
        pattern=r"^[a-zA-Z0-9_,-]+$",
    )
    start_date: datetime = Field(
        alias="startDate",
        description="A string value representing the start date in ISO format, UTC.",
    )
    end_date: datetime = Field(
        alias="endDate", description="A string value representing the end date in ISO format, UTC."
    )
    interval_type: IntervalType | None = Field(
        None, alias="intervalType", description="A string value representing the interval type."
    )
    interval: int = Field(
        0,
        alias="interval",
        description="An integer value representing the interval.",
        ge=0,
    )
    agg: AggregationType | None = Field(
        None,
        alias="agg",
        description=(
            "A string value representing the aggregation type."
            " If the interval type is not provided, the aggregation is not performed."
        ),
    )
    limit: int = Field(
        100,
        alias="limit",
        description=(
            "An integer value that represents a max number of timeseries data points to fetch."
            " This parameter is used only when the `agg` parameter is not provided."
        ),
        ge=0,
        le=500,
    )
    timezone: Timezone | None = Field(
        None,
        description="A string value representing the timezone.",
    )
    order_by: SortDirection | None = Field(
        None,
        alias="orderBy",
        description="Sort order. asc (ascending) or desc (descending).",
    )

    @computed_field
    @property
    def keys(self) -> set[str]:
        return keys_comma_separated_values(self.keys__)

    @computed_field
    @property
    def interval_in_timedelta(self) -> timedelta:
        if self.interval_type is None or self.interval == 0:
            raise ValueError("Interval and interval type must be provided")

        if self.interval_type == IntervalType.MILLISECOND:
            return timedelta(milliseconds=self.interval)
        elif self.interval_type == IntervalType.HOUR:
            return timedelta(hours=self.interval)
        elif self.interval_type == IntervalType.DAY:
            return timedelta(days=self.interval)
        elif self.interval_type == IntervalType.WEEK:
            return timedelta(weeks=self.interval)
        elif self.interval_type == IntervalType.MONTH:
            return timedelta(days=self.interval * 30)
        elif self.interval_type == IntervalType.YEAR:
            return timedelta(days=self.interval * 365)
        else:
            raise ValueError("Invalid interval type")

    @computed_field
    @property
    def is_aggregate_query(self) -> bool:
        return self.interval > 0 and self.interval_type is not None and self.agg is not None

    @field_validator("start_date", mode="before")
    @classmethod
    def transform_start_date(cls, value: str) -> datetime:
        return datetime.fromisoformat(value).replace(tzinfo=None)

    @field_validator("end_date", mode="before")
    @classmethod
    def transform_end_date(cls, value: str) -> datetime:
        return datetime.fromisoformat(value).replace(tzinfo=None)

    @model_validator(mode="after")
    def validate_dto(self) -> Self:
        if self.start_date >= self.end_date:
            raise ValueError("End date must be greater than start date")
        if self.interval == 0 or self.interval_type is None or self.agg is None:
            raise ValueError(
                "When using aggregation, 'interval', 'intervalType', and 'agg' must be provided"
            )
        return self


class LatestDataPointDto(BaseOutDto):
    ts: datetime
    key: str
    value: Any

    @classmethod
    def from_model(cls, model: DeviceDataLatest) -> "LatestDataPointDto":
        return cls(ts=model.ts, key=model.key, value=model.value)


class AggregatedData(NamedTuple):
    ts: datetime
    value: int | float | str | bool | dict[str, Any]


class DataPointDto(BaseOutDto):
    ts: datetime
    value: Any

    @classmethod
    def from_model(cls, model: DeviceData | AggregatedData) -> "DataPointDto":
        return cls(ts=model.ts, value=model.value)
