from dataclasses import dataclass
from datetime import date
from typing import Any

from pysuez.utils import cubic_meters_to_liters


@dataclass
class AggregatedData:
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
        self.index = cubic_meters_to_liters(index)
        self.keyMode = keyMode
        self.qualiteDernierIndex = qualiteDernierIndex
        self.valeurAncienIndex = cubic_meters_to_liters(valeurAncienIndex)
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


class AlertQueryValueResult:
    def __init__(self, isActive, status, message, buttons):
        self.is_active = isActive
        self.status = status
        self.message = message
        self.buttons = buttons


class AlertQueryContentResult:
    def __init__(self, leak_alert, overconsumption_alert):
        self.leak = AlertQueryValueResult(**leak_alert)
        self.overconsumption = AlertQueryValueResult(**overconsumption_alert)


class AlertQueryResult:
    def __init__(self, content, code, message):
        self.content = AlertQueryContentResult(**content)
        self.code = code
        self.message = message


@dataclass
class AlertResult:
    leak: bool
    overconsumption: bool

    def __str__(self):
        return "AlertResult leak={0}, overconsumption={1}".format(
            self.leak, self.overconsumption
        )
