from dataclasses import dataclass
from datetime import date, datetime
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


class TelemetryMeasure:
    def __init__(self, date, index, volume, numberOfDays=None):
        self.date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").date()
        self.index = cubic_meters_to_liters(index)
        self.volume = cubic_meters_to_liters(volume)
        self.number_of_days = numberOfDays

    def __str__(self):
        return "TelemetryMeasure ({0},{1},{2})".format(
            str(self.date),
            self.index,
            self.volume,
        )

    def __repr__(self):
        return self.__str__()


class TelemetryResultContent:
    def __init__(self, measures):
        self.measures: list[TelemetryMeasure] = []
        for measure in measures:
            self.measures.append(TelemetryMeasure(**measure))

    def __str__(self):
        return "TelemetryResultContent ({0})".format(self.measures)


class TelemetryResult:
    def __init__(self, code: str, content, message: str):
        self.code = code
        self.content = TelemetryResultContent(**content)
        self.message = message

    def __str__(self):
        return "TelemetryResult ({0}, {1}, {2})".format(
            self.code, self.message, self.content
        )


@dataclass
class InterventionResult:
    ongoingInterventionCount: int
    comingInterventionCount: int

    def __str__(self):
        return "InterventionResult onGoing={0}, incoming={1}".format(
            self.ongoingInterventionCount, self.comingInterventionCount
        )


@dataclass
class ErrorResponse:
    content: Any
    code: str
    message: str
    trackableMessage: str
    response: Any


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


class MeterPro:
    def __init__(
        self,
        adresseDesserte,
        adresseDesserte1,
        adresseDesserte2,
        adresseDesserte3,
        anneeFabrication,
        calibre,
        causeFermeture,
        codeEmplacement,
        codeEquipement,
        compteurDivisionnaire,
        compteurGeneral,
        cpDesserte,
        etatCompteur,
        etatPDS,
        fluide,
        idAdresse,
        idPDS,
        idSite,
        libelleCodeEmplacement,
        matriculeCompteur,
        numeroBadge,
        typeProprietaire,
        typeRaccordement,
        usage,
        villeDesserte,
    ):
        self.adresseDesserte = adresseDesserte
        self.adresseDesserte1 = adresseDesserte1
        self.adresseDesserte2 = adresseDesserte2
        self.adresseDesserte3 = adresseDesserte3
        self.anneeFabrication = anneeFabrication
        self.calibre = calibre
        self.causeFermeture = causeFermeture
        self.codeEmplacement = codeEmplacement
        self.codeEquipement = codeEquipement
        self.compteurDivisionnaire = compteurDivisionnaire
        self.compteurGeneral = compteurGeneral
        self.cpDesserte = cpDesserte
        self.etatCompteur = etatCompteur
        self.etatPDS = etatPDS
        self.fluide = fluide
        self.idAdresse = idAdresse
        self.idPDS = idPDS
        self.idSite = idSite
        self.libelleCodeEmplacement = libelleCodeEmplacement
        self.matriculeCompteur = matriculeCompteur
        self.numeroBadge = numeroBadge
        self.typeProprietaire = typeProprietaire
        self.typeRaccordement = typeRaccordement
        self.usage = usage
        self.villeDesserte = villeDesserte


class MeterClientPro:
    def __init__(
        self,
        compteursPro,
        dateDebutDerniereConsoRelevee,
        dateFinDerniereConsoRelevee,
        derniereConsoRelevee,
        name,
        nbCompteurTotal,
        nombreCompteurRr,
        nombreCompteurSe,
        nombreCompteurTr,
        reference,
        roles,
    ):
        self.compteursPro = [MeterPro(**compteur) for compteur in compteursPro]
        self.dateDebutDerniereConsoRelevee = dateDebutDerniereConsoRelevee
        self.dateFinDerniereConsoRelevee = dateFinDerniereConsoRelevee
        self.derniereConsoRelevee = derniereConsoRelevee
        self.name = name
        self.nbCompteurTotal = nbCompteurTotal
        self.nombreCompteurRr = nombreCompteurRr
        self.nombreCompteurSe = nombreCompteurSe
        self.nombreCompteurTr = nombreCompteurTr
        self.reference = reference
        self.roles = roles


class MeterListContent:
    def __init__(
        self, clientCompteursPro, nbCodeRef, nbCodeRefFull, nbCompteurFull, nbMeters
    ):
        self.clientCompteursPro = [
            MeterClientPro(**compteur) for compteur in clientCompteursPro
        ]
        self.nbCodeRef = nbCodeRef
        self.nbCodeRefFull = nbCodeRefFull
        self.nbCompteurFull = nbCompteurFull
        self.nbMeters = nbMeters


class MeterListResult:
    def __init__(self, code, content, message):
        self.code = code
        self.content = MeterListContent(**content)
        self.message = message


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
