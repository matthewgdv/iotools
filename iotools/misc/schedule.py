from __future__ import annotations

import datetime as dt
from typing import Any, Callable, Optional, List

from apscheduler.schedulers.background import BlockingScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from subtypes import Enum, DateTime
from miscutils import ReprMixin, class_name


class TimeUnit(Enum):
    SECONDS, MINUTES, HOURS, DAYS, WEEKS, MONTHS, YEARS = "seconds", "minutes", "hours", "days", "weeks", "months", "years"


class WeekDay(Enum):
    MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY = 0, 1, 2, 3, 4, 5, 6


Month = DateTime.MonthName


class Schedule(ReprMixin):
    """
    A class used to specify schedules on which specific Python callables will be executed. Event callbacks can be supplied to be invoked on success
    or failure. By default a blocking scheduler is used, which will enter a blocking main loop upon starting.
    """

    scheduler_constructor = BlockingScheduler

    def __init__(self, name: str = "default", on_success: Callable = None, on_failure: Callable = None) -> None:
        self.name = name
        self.scheduler = self.scheduler_constructor()

        if on_success is not None:
            self.scheduler.add_listener(callback=on_success, mask=EVENT_JOB_EXECUTED)

        if on_failure is not None:
            self.scheduler.add_listener(callback=on_failure, mask=EVENT_JOB_ERROR)

        # self.scheduler.add_jobstore(SqlalchemyJobStore, self.name)

    def __enter__(self) -> Schedule:
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        self.scheduler.start()

    @property
    def every(self) -> Fixed.Selector.Start:
        return Fixed.Selector.Start(Fixed.Settings(schedule=self))

    def _register_relative_interval(self, settings: Relative.Settings, func: Callable, args: tuple = None, kwargs: dict = None, job_id: str = None):
        ns = vars(settings)
        self.scheduler.add_job(func, trigger="interval", args=args, kwargs=kwargs, id=job_id or func.__name__, start_date=settings.start_time, end_date=settings.end_time, **{name: val for name in TimeUnit.values if (val := ns[name])})

    def _register_fixed_interval(self, settings: Fixed.Settings, func: Callable, args: tuple = None, kwargs: dict = None, job_id: str = None) -> None:
        if settings.weekday_parts and settings.day_parts:
            raise ValueError(f"Cannot simultaenously provide weekday and ordinal day arguments to a schedule. Use one or the other.")

        year = month = day = week = None

        if settings.interval == TimeUnit.YEARS:
            year = "*"
        elif settings.interval == TimeUnit.MONTHS:
            month = "*"
        elif settings.interval == TimeUnit.WEEKS:
            week = "*"
        elif settings.interval == TimeUnit.DAYS:
            day = "*"
        else:
            raise ValueError(f"Invalid interval value: {settings.interval}.") if isinstance(settings.interval, TimeUnit) else TypeError(f"Invalid interval type: {class_name(settings.interval)}.")

        start_date, end_date = settings.start_date, settings.end_date
        day_of_week = None if not settings.weekday_parts else ",".join([str(weekday) for weekday in settings.weekday_parts])
        month = None if not settings.month_parts else ",".join([str(month) for month in settings.month_parts])
        day = None if not settings.day_parts else ",".join([str(day) for day in settings.day_parts])

        if not settings.time_parts:
            self.scheduler.add_job(func, trigger="cron", args=args, kwargs=kwargs, id=job_id or func.__name__, year=year, month=month, day=day, week=week, day_of_week=day_of_week, hour=None, minute=None, second=None, start_date=start_date, end_date=end_date)
        else:
            for time in settings.time_parts:
                self.scheduler.add_job(func, trigger="cron", args=args, kwargs=kwargs, id=job_id or func.__name__, year=year, month=month, day=day, week=week, day_of_week=day_of_week, hour=time.hour, minute=time.minute, second=time.second, start_date=start_date, end_date=end_date)


class Fixed:
    class Settings(ReprMixin):
        def __init__(self, schedule: Schedule) -> None:
            self.schedule = schedule

            self.interval: Optional[TimeUnit] = None
            self.start_date: Optional[DateTime] = None
            self.end_date: Optional[DateTime] = None

            self.month_parts: List[Month] = []
            self.day_parts: List[int] = []
            self.weekday_parts: List[WeekDay] = []
            self.time_parts: List[dt.time] = []

        def as_dict(self) -> dict:
            return {}

    class Selector:
        class Base(ReprMixin):
            def __init__(self, settings: Fixed.Settings = None) -> None:
                self.settings = settings

        class MonthMixin:
            settings: Fixed.Settings

            @property
            def january(self) -> Fixed.Interval.ChainableMonth:
                self._set_month(Month.JANUARY)
                return Fixed.Interval.ChainableMonth(settings=self.settings)

            @property
            def february(self) -> Fixed.Interval.ChainableMonth:
                self._set_month(Month.FEBRUARY)
                return Fixed.Interval.ChainableMonth(settings=self.settings)

            @property
            def march(self) -> Fixed.Interval.ChainableMonth:
                self._set_month(Month.MARCH)
                return Fixed.Interval.ChainableMonth(settings=self.settings)

            @property
            def april(self) -> Fixed.Interval.ChainableMonth:
                self._set_month(Month.APRIL)
                return Fixed.Interval.ChainableMonth(settings=self.settings)

            @property
            def may(self) -> Fixed.Interval.ChainableMonth:
                self._set_month(Month.MAY)
                return Fixed.Interval.ChainableMonth(settings=self.settings)

            @property
            def june(self) -> Fixed.Interval.ChainableMonth:
                self._set_month(Month.JUNE)
                return Fixed.Interval.ChainableMonth(settings=self.settings)

            @property
            def july(self) -> Fixed.Interval.ChainableMonth:
                self._set_month(Month.JULY)
                return Fixed.Interval.ChainableMonth(settings=self.settings)

            @property
            def august(self) -> Fixed.Interval.ChainableMonth:
                self._set_month(Month.AUGUST)
                return Fixed.Interval.ChainableMonth(settings=self.settings)

            @property
            def september(self) -> Fixed.Interval.ChainableMonth:
                self._set_month(Month.SEPTEMBER)
                return Fixed.Interval.ChainableMonth(settings=self.settings)

            @property
            def october(self) -> Fixed.Interval.ChainableMonth:
                self._set_month(Month.OCTOBER)
                return Fixed.Interval.ChainableMonth(settings=self.settings)

            @property
            def november(self) -> Fixed.Interval.ChainableMonth:
                self._set_month(Month.NOVEMBER)
                return Fixed.Interval.ChainableMonth(settings=self.settings)

            @property
            def december(self) -> Fixed.Interval.ChainableMonth:
                self._set_month(Month.DECEMBER)
                return Fixed.Interval.ChainableMonth(settings=self.settings)

            def _set_month(self, month: Month) -> None:
                self.settings.month_parts.append(month)
                if self.settings.interval is None:
                    self.settings.interval = TimeUnit.YEARS

        class Month(Base, MonthMixin):
            pass

        class WeekdayMixin:
            settings: Fixed.Settings

            @property
            def monday(self) -> Fixed.Interval.ChainableWeekDay:
                self._set_weekday(WeekDay.MONDAY)
                return Fixed.Interval.ChainableWeekDay(settings=self.settings)

            @property
            def tuesday(self) -> Fixed.Interval.ChainableWeekDay:
                self._set_weekday(WeekDay.TUESDAY)
                return Fixed.Interval.ChainableWeekDay(settings=self.settings)

            @property
            def wednesday(self) -> Fixed.Interval.ChainableWeekDay:
                self._set_weekday(WeekDay.WEDNESDAY)
                return Fixed.Interval.ChainableWeekDay(settings=self.settings)

            @property
            def thursday(self) -> Fixed.Interval.ChainableWeekDay:
                self._set_weekday(WeekDay.THURSDAY)
                return Fixed.Interval.ChainableWeekDay(settings=self.settings)

            @property
            def friday(self) -> Fixed.Interval.ChainableWeekDay:
                self._set_weekday(WeekDay.FRIDAY)
                return Fixed.Interval.ChainableWeekDay(settings=self.settings)

            @property
            def saturday(self) -> Fixed.Interval.ChainableWeekDay:
                self._set_weekday(WeekDay.SATURDAY)
                return Fixed.Interval.ChainableWeekDay(settings=self.settings)

            @property
            def sunday(self) -> Fixed.Interval.ChainableWeekDay:
                self._set_weekday(WeekDay.SUNDAY)
                return Fixed.Interval.ChainableWeekDay(settings=self.settings)

            def _set_weekday(self, weekday: WeekDay) -> None:
                self.settings.weekday_parts.append(weekday)
                if self.settings.interval is None:
                    self.settings.interval = TimeUnit.WEEKS

        class Weekday(Base, WeekdayMixin):
            pass

        class Day(Base):
            def __call__(self, day: int) -> Fixed.Interval.ChainableDay:
                self.settings.day_parts.append(day)
                return Fixed.Interval.ChainableDay(settings=self.settings)

        class Time(Base):
            def __call__(self, *time_args) -> Fixed.Interval.ChainableDay:
                time = time_args[0] if len(time_args) == 1 and isinstance(time_args[0], dt.time) else dt.time(*time_args)
                self.settings.time_parts.append(time)
                return Fixed.Interval.ChainableDay(settings=self.settings)

        class Start(Base, MonthMixin, WeekdayMixin):
            def __call__(self, magnitude: int) -> Relative.Selector.Year:
                return Relative.Selector.Year(magnitude=magnitude, settings=Relative.Settings(schedule=self.settings.schedule))

            @property
            def minute(self) -> Relative.Interval.Minute:
                return self(1).minutes

            @property
            def hour(self) -> Relative.Interval.Hour:
                return self(1).hours

            @property
            def day(self) -> Fixed.Interval.Day:
                self.settings.interval = TimeUnit.DAYS
                return Fixed.Interval.Day(settings=self.settings)

            @property
            def week(self) -> Fixed.Interval.Month:
                self.settings.interval = TimeUnit.WEEKS
                return Fixed.Interval.Month(settings=self.settings)

            @property
            def month(self) -> Fixed.Interval.Month:
                self.settings.interval = TimeUnit.MONTHS
                return Fixed.Interval.Month(settings=self.settings)

            @property
            def year(self) -> Fixed.Interval.Year:
                self.settings.interval = TimeUnit.YEARS
                return Fixed.Interval.Year(settings=self.settings)

    class Interval:
        class Final(ReprMixin):
            def __init__(self, settings: Fixed.Settings = None) -> None:
                self.settings = settings

            def do(self, func: Callable, args: tuple = None, kwargs: dict = None, job_id: str = None) -> Callable:
                self.settings.schedule._register_fixed_interval(settings=self.settings, func=func, job_id=job_id, args=args, kwargs=kwargs)
                return func

            def starting(self, datelike: Any) -> Fixed.Interval.Final:
                self.settings.start_date = DateTime.from_datelike(datelike)
                return Fixed.Interval.Final(settings=self.settings)

            def ending(self, datelike: Any) -> Fixed.Interval.Final:
                self.settings.end_date = DateTime.from_datelike(datelike)
                return Fixed.Interval.Final(settings=self.settings)

        class ChainableFinal(Final):
            @property
            def and_(self) -> Fixed.Interval.ChainableFinal:
                return Fixed.Interval.ChainableFinal(settings=self.settings)

        class Day(Final):
            @property
            def at(self) -> Fixed.Selector.Time:
                return Fixed.Selector.Time(settings=self.settings)

        class ChainableDay(Final):
            @property
            def and_(self) -> Fixed.Selector.Time:
                return Fixed.Selector.Time(settings=self.settings)

        class ChainableWeekDay(Day):
            @property
            def and_(self) -> Fixed.Selector.Weekday:
                return Fixed.Selector.Weekday(settings=self.settings)

        class Month(Final):
            @property
            def on_the(self) -> Fixed.Selector.Day:
                return Fixed.Selector.Day(settings=self.settings)

            @property
            def on(self) -> Fixed.Selector.Weekday:
                return Fixed.Selector.Weekday(settings=self.settings)

        class ChainableMonth(Month):
            @property
            def and_(self) -> Fixed.Selector.Month:
                return Fixed.Selector.Month(settings=self.settings)

        class Year(Final):
            @property
            def in_(self) -> Fixed.Selector.Month:
                return Fixed.Selector.Month(settings=self.settings)


class Relative:
    class Settings(ReprMixin):
        def __init__(self, schedule: Schedule, start_time: DateTime = None, end_time: DateTime = None) -> None:
            self.schedule, self.start_time, self.end_time = schedule, start_time, end_time
            self.years = self.months = self.weeks = self.days = self.hours = self.minutes = self.seconds = 0

    class Selector:
        class Base(ReprMixin):
            def __init__(self, magnitude: int, settings: Relative.Settings) -> None:
                self.magnitude, self.settings = magnitude, settings

        class Second(Base):
            @property
            def seconds(self) -> Relative.Interval.Final:
                self.settings.seconds = self.magnitude
                return Relative.Interval.Final(settings=self.settings)

        class Minute(Second):
            @property
            def minutes(self) -> Relative.Interval.Minute:
                self.settings.minutes = self.magnitude
                return Relative.Interval.Minute(settings=self.settings)

        class Hour(Minute):
            @property
            def hours(self) -> Relative.Interval.Hour:
                self.settings.hours = self.magnitude
                return Relative.Interval.Hour(settings=self.settings)

        class Day(Hour):
            @property
            def days(self) -> Relative.Interval.Day:
                self.settings.days = self.magnitude
                return Relative.Interval.Day(settings=self.settings)

        class Month(Day):
            @property
            def months(self) -> Relative.Interval.Month:
                self.settings.months = self.magnitude
                return Relative.Interval.Month(settings=self.settings)

        class Year(Month):
            @property
            def years(self) -> Relative.Interval.Year:
                self.settings.years = self.magnitude
                return Relative.Interval.Year(settings=self.settings)

    class Interval:
        class Final(ReprMixin):
            def __init__(self, settings: Relative.Settings) -> None:
                self.settings = settings

            def do(self, func: Callable, args: tuple = None, kwargs: dict = None, job_id: str = None) -> Callable:
                self.settings.schedule._register_relative_interval(settings=self.settings, func=func, args=args, kwargs=kwargs, job_id=job_id)
                return func

            def starting(self, datelike: Any) -> Relative.Interval.Final:
                self.settings.start_time = DateTime.from_datelike(datelike)
                return Relative.Interval.Final(settings=self.settings)

            def ending(self, datelike: Any) -> Relative.Interval.Final:
                self.settings.end_time = DateTime.from_datelike(datelike)
                return Relative.Interval.Final(settings=self.settings)

        class Minute(Final):
            def and_(self, magnitude: int) -> Relative.Selector.Second:
                return Relative.Selector.Second(magnitude=magnitude, settings=self.settings)

        class Hour(Final):
            def and_(self, magnitude: int) -> Relative.Selector.Minute:
                return Relative.Selector.Minute(magnitude=magnitude, settings=self.settings)

        class Day(Final):
            def and_(self, magnitude: int) -> Relative.Selector.Hour:
                return Relative.Selector.Hour(magnitude=magnitude, settings=self.settings)

        class Month(Final):
            def and_(self, magnitude: int) -> Relative.Selector.Day:
                return Relative.Selector.Day(magnitude=magnitude, settings=self.settings)

        class Year(Final):
            def and_(self, magnitude: int) -> Relative.Selector.Month:
                return Relative.Selector.Month(magnitude=magnitude, settings=self.settings)
