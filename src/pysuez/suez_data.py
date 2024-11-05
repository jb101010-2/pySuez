import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from .async_client import SuezAsyncClient
from .const import (
    API_CONSUMPTION_INDEX,
    API_ENDPOINT_ALERT,
    API_ENDPOINT_DAY_DATA,
    API_ENDPOINT_MONTH_DATA,
    ATTRIBUTION,
    INFORMATION_ENDPOINT_INTERVENTION,
    INFORMATION_ENDPOINT_LIMESTONE,
    INFORMATION_ENDPOINT_PRICE,
    INFORMATION_ENDPOINT_QUALITY,
)
from .exception import PySuezConnexionError, PySuezDataError, PySuezError
from .utils import cubicMetersToLiters

_LOGGER = logging.getLogger(__name__)


@dataclass
class AggregatedSensorData:
    """Hold suez water aggregated sensor data."""

    value: float
    current_month: dict[date, float]
    previous_month: dict[date, float]
    previous_year: dict[str, float]
    current_year: dict[str, float]
    history: dict[date, float]
    highest_monthly_consumption: float
    attribution: str


class ConsumptionIndexContentResult:
    def __init__(
        self,
        afficheDate: bool,
        buttons,
        date: str,
        dateAncienIndex: str,
        index: int,
        keyMode: str,
        qualiteDernierIndex: str,
        valeurAncienIndex,
        volume,
    ):
        self.afficheDate = afficheDate
        self.buttons = buttons
        self.date = date
        self.dateAncienIndex = dateAncienIndex
        self.index = cubicMetersToLiters(index)
        self.keyMode = keyMode
        self.qualiteDernierIndex = qualiteDernierIndex
        self.valeurAncienIndex = cubicMetersToLiters(valeurAncienIndex)
        self.volume = volume


class ConsumptionIndexResult:
    def __init__(self, code: str, content, message: str):
        self.code = code
        self.content = ConsumptionIndexContentResult(**content)
        self.message = message


@dataclass
class DayDataResult:
    date: date
    day_consumption: float
    total_consumption: float

    def __str__(self):
        return "DayDataResult {0}, current={1}, total={2}".format(
            self.date,
            self.day_consumption,
            self.total_consumption,
        )


@dataclass
class InterventionResult:
    ongoingInterventionCount: int
    comingInterventionCount: int

    def __str__(self):
        return "InterventionResult onGoing={0}, incoming={1}".format(
            self.ongoingInterventionCount, self.comingInterventionCount
        )


class PriceResult:
    def __init__(self, price: str):
        self.price = float(price.replace(",", "."))

    def __str__(self):
        return "PriceResult price={0}€".format(self.price)


@dataclass
class QualityResult:
    quality: Any

    def __str__(self):
        return "QualityResult quality={0}".format(self.quality)


@dataclass
class LimestoneResult:
    limestone: Any
    limestoneValue: int

    def __str__(self):
        return "LimestoneResult limestone={0}, value={1}".format(
            self.limestone, self.limestoneValue
        )


class ContractResult:
    def __init__(self, content: dict):
        self.name = content["name"]
        self.inseeCode = content["inseeCode"]
        self.brandCode = content["brandCode"]
        self.fullRefFormat = content["fullRefFormat"]
        self.fullRef = content["fullRef"]
        self.addrServed = content["addrServed"]
        self.isActif = content["isActif"]
        self.website_link = content["website-link"]
        self.searchData = content["searchData"]
        self.isCurrentContract = content["isCurrentContract"]
        self.codeSituation = content["codeSituation"]

    def __str__(self):
        return "ContractResult name={0}, inseeCode={1}, addrServed={2}".format(
            self.name, self.inseeCode, self.addrServed
        )


@dataclass
class AlertResult:
    leak: bool
    overconsumption: bool

    def __str__(self):
        return "AlertResult leak={0}, overconsumption={1}".format(
            self.leak, self.overconsumption
        )


class _AlertQueryValueResult:
    def __init__(self, isActive, status, message, buttons):
        self.is_active = isActive
        self.status = status
        self.message = message
        self.buttons = buttons


class _AlertQueryContentResult:
    def __init__(self, leak_alert, overconsumption_alert):
        self.leak = _AlertQueryValueResult(**leak_alert)
        self.overconsumption = _AlertQueryValueResult(**overconsumption_alert)


class _AlertQueryResult:
    def __init__(self, content, code, message):
        self.content = _AlertQueryContentResult(**content)
        self.code = code
        self.message = message


class SuezData:
    def __init__(self, async_client: SuezAsyncClient):
        self._async_client = async_client

    async def get_consumption_index(self) -> ConsumptionIndexResult:
        """Fetch consumption index."""
        async with await self._async_client.get(API_CONSUMPTION_INDEX) as data:
            if data.status != 200:
                raise PySuezConnexionError("Error while getting consumption index")
            json = await data.json()
            response_data = ConsumptionIndexResult(**json)
            return response_data

    async def get_alerts(self) -> AlertResult:
        """Fetch alert data from Suez."""
        async with await self._async_client.get(API_ENDPOINT_ALERT) as data:
            if data.status != 200:
                raise PySuezConnexionError("Error while requesting alerts")

            json = await data.json()
            alert_response = _AlertQueryResult(**json)
            return AlertResult(
                alert_response.content.leak.status != "NO_ALERT",
                alert_response.content.overconsumption.status != "NO_ALERT",
            )

    async def get_price(self) -> PriceResult:
        """Fetch water price in e/m3"""
        contract = await self.contract_data()
        async with await self._async_client.get(
            INFORMATION_ENDPOINT_PRICE, contract.inseeCode, need_connection=False
        ) as data:
            json = await data.json()
            return PriceResult(**json)

    async def get_quality(self) -> QualityResult:
        """Fetch water quality"""
        contract = await self.contract_data()
        async with await self._async_client.get(
            INFORMATION_ENDPOINT_QUALITY, contract.inseeCode, need_connection=False
        ) as data:
            json = await data.json()
            return QualityResult(**json)

    async def get_interventions(self) -> InterventionResult:
        """Fetch water interventions"""
        contract = await self.contract_data()
        async with await self._async_client.get(
            INFORMATION_ENDPOINT_INTERVENTION,
            contract.inseeCode,
            need_connection=False,
        ) as data:
            json = await data.json()
            return InterventionResult(**json)

    async def get_limestone(self) -> LimestoneResult:
        """Fetch water limestone values"""
        contract = await self.contract_data()
        async with await self._async_client.get(
            INFORMATION_ENDPOINT_LIMESTONE, contract.inseeCode, need_connection=False
        ) as data:
            json = await data.json()
            limestone = LimestoneResult(**json)
            return limestone

    async def contract_data(self) -> ContractResult:
        url = "/public-api/user/donnees-contrats"
        async with await self._async_client.get(url) as data:
            json = await data.json()
            return ContractResult(json[0])

    async def fetch_day_data(self, date: datetime) -> DayDataResult | None:
        year = date.year
        month = date.month

        result_by_day = await self.fetch_month_data(year, month)
        if len(result_by_day) == 0:
            return None
        return result_by_day[len(result_by_day) - 1]

    async def fetch_yesterday_data(self) -> DayDataResult | None:
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        result_by_day = await self.fetch_day_data(yesterday)
        if result_by_day is None:
            result_by_day = await self.fetch_day_data(yesterday - timedelta(days=1))
        if result_by_day is None:
            return None
        return result_by_day

    async def fetch_month_data(self, year, month) -> list[DayDataResult]:
        now = datetime.now()

        async with await self._async_client.get(
            API_ENDPOINT_DAY_DATA,
            year,
            month,
            with_counter_id=True,
            params={"_=": now.timestamp()},
        ) as data:
            if data.status != 200:
                raise PySuezConnexionError(
                    "Error while requesting data: status={}".format(data.status)
                )

            result_by_day = await data.json()
            if result_by_day[0] == "ERR":
                _LOGGER.debug(
                    "Error while requesting data for {}/{}: {}".format(
                        year, month, result_by_day[1]
                    )
                )
                return []

            result = []
            for day in result_by_day:
                date = datetime.strptime(day[0], "%d/%m/%Y")
                try:
                    total = float(day[2])
                    if total > 0:
                        result.append(
                            DayDataResult(
                                date.date(),
                                cubicMetersToLiters(float(day[1])),
                                total,
                            )
                        )
                except ValueError:
                    _LOGGER.debug(
                        f"Failed to parse consumption value:{day[1]} / {day[0]} "
                    )
                    return result
            return result

    async def fetch_all_available(
        self, since: date | None = None
    ) -> list[DayDataResult]:
        current = datetime.now().date()
        _LOGGER.debug(
            "Getting all available data from suez since %s to %s",
            str(since),
            str(current),
        )
        result = []
        while since is None or current >= since:
            try:
                _LOGGER.debug("Fetch data of " + str(current))
                current = current.replace(day=1)
                month = await self.fetch_month_data(current.year, current.month)
                next_result = []
                next_result.extend(month)
                next_result.extend(result)
                result = next_result
                current = current - timedelta(days=1)
            except PySuezDataError:
                return result
        return result

    def get_attribution(self):
        return self._async_client.get_attribution()

    async def fetch_all_deprecated_data(self) -> AggregatedSensorData:
        """Fetch latest data from Suez."""
        now = datetime.now()
        today_year = now.strftime("%Y")
        today_month = now.strftime("%m")

        yesterday_data = await self.fetch_yesterday_data()
        if yesterday_data is not None:
            state = yesterday_data.day_consumption
        else:
            state = None

        month_data = await self.fetch_month_data(today_year, today_month)
        current_month = {}
        for item in month_data:
            current_month[item.date] = item.day_consumption

        if int(today_month) == 1:
            last_month = 12
            last_month_year = int(today_year) - 1
        else:
            last_month = int(today_month) - 1
            last_month_year = today_year

        previous_month_data = await self.fetch_month_data(last_month_year, last_month)
        previous_month = {}
        for item in previous_month_data:
            previous_month[item.date] = item.day_consumption

        (
            highest_monthly_consumption,
            last_year,
            current_year,
            history,
        ) = await self._fetch_aggregated_statistics()

        return AggregatedSensorData(
            value=state,
            current_month=current_month,
            previous_month=previous_month,
            highest_monthly_consumption=highest_monthly_consumption,
            previous_year=last_year,
            current_year=current_year,
            history=history,
            attribution=ATTRIBUTION,
        )

    async def _fetch_aggregated_statistics(
        self,
    ) -> tuple[int, int, int, dict[date, float]]:
        try:
            statistics_url = API_ENDPOINT_MONTH_DATA
            async with await self._async_client.get(
                statistics_url, with_counter_id=True
            ) as data:
                fetched_data: list = await data.json()
                highest_monthly_consumption = int(
                    cubicMetersToLiters(float(fetched_data[-1]))
                )
                fetched_data.pop()
                last_year = int(cubicMetersToLiters(float(fetched_data[-1])))
                fetched_data.pop()
                current_year = int(cubicMetersToLiters(float(fetched_data[-1])))
                fetched_data.pop()
                history = {}
                for item in fetched_data:
                    history[item[3]] = int(cubicMetersToLiters(float(item[1])))
        except ValueError:
            raise PySuezError("Issue with history data")
        return highest_monthly_consumption, last_year, current_year, history
