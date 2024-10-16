from datetime import date, datetime
from datetime import timedelta

import logging

from pysuez.client import SuezClient
from pysuez.async_client import SuezAsyncClient
from pysuez.exception import PySuezConnexionError, PySuezDataError, PySuezError

API_ENDPOINT_ALERT = '/public-api/contract/tile/alerts'
INFORMATION_ENDPOINT = '/information/donnee/'
INFORMATION_ENDPOINT_INTERVENTION = INFORMATION_ENDPOINT + 'intervention/'
INFORMATION_ENDPOINT_QUALITY = INFORMATION_ENDPOINT + 'quality/'
INFORMATION_ENDPOINT_PRICE = INFORMATION_ENDPOINT + 'price/'
INFORMATION_ENDPOINT_LIMESTONE = INFORMATION_ENDPOINT + 'limestone/'
API_ENDPOINT_DAY_DATA = '/mon-compte-en-ligne/statJData/'
API_CONSUMPTION_INDEX = '/public-api/contract/tile/consumption'

LOGGER = logging.getLogger(__name__)


class ConsumptionIndexContentResult:
  def __init__(self,
               afficheDate: bool,
               buttons,
               date: str,
               dateAncienIndex: str,
               index: int,
               keyMode: str,
               qualiteDernierIndex: str,
               valeurAncienIndex,
               volume
               ):
    self.afficheDate = afficheDate
    self.buttons = buttons
    self.date = date
    self.dateAncienIndex = dateAncienIndex
    self.index = index * 1000
    self.keyMode = keyMode
    self.qualiteDernierIndex = qualiteDernierIndex
    self.valeurAncienIndex = valeurAncienIndex * 1000
    self.volume = volume


class ConsumptionIndexResult:
  def __init__(self,
               code: str,
               content,
               message: str):
    self.code = code
    self.content = ConsumptionIndexContentResult(**content)
    self.message = message


class DayDataResult:
  def __init__(self,
               date: date,
               day_consumption,
               total_consumption
               ):
    self.date = date
    self.day_consumption = day_consumption
    self.total_consumption = total_consumption

  def __str__(self):
    return "DayDataResult {0}/{1}/{2}, current={3}, total={4}".format(
      self.day, self.month, self.year, self.day_consumption,
      self.total_consumption)


class InterventionResult:
  def __init__(self, ongoingInterventionCount, comingInterventionCount):
    self.ongoingInterventionCount = ongoingInterventionCount
    self.comingInterventionCount = comingInterventionCount

  def __str__(self):
    return "InterventionResult onGoing={0}, incoming={1}".format(
      self.ongoingInterventionCount, self.comingInterventionCount)


class PriceResult:
  def __init__(self, price: str):
    self.price = float(price.replace(",", "."))

  def __str__(self):
    return "PriceResult price={0}€".format(self.price)


class QualityResult:
  def __init__(self, quality):
    self.quality = quality

  def __str__(self):
    return "QualityResult quality={0}".format(self.quality)


class LimestoneResult:
  def __init__(self, limestone, limestoneValue):
    self.limestone = limestone
    self.limestoneValue = limestoneValue

  def __str__(self):
    return "LimestoneResult limestone={0}, value={1}".format(self.limestone,
                                                             self.limestoneValue)


class ContractResult:
  def __init__(self, content: dict):
    self.name = content['name']
    self.inseeCode = content['inseeCode']
    self.brandCode = content['brandCode']
    self.fullRefFormat = content['fullRefFormat']
    self.fullRef = content['fullRef']
    self.addrServed = content['addrServed']
    self.isActif = content['isActif']
    self.website_link = content['website-link']
    self.searchData = content['searchData']
    self.isCurrentContract = content['isCurrentContract']
    self.codeSituation = content['codeSituation']

  def __str__(self):
    return "ContractResult name={0}, inseeCode={1}, addrServed={2}".format(
      self.name,
      self.inseeCode, self.addrServed)


class AlertResult:
  def __init__(self, leak=False, consumption=False):
    self.leak = leak
    self.overconsumption = consumption

  def __str__(self):
    return "AlertResult leak={0}, overconsumption={1}".format(
      self.leak, self.overconsumption)


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


class SuezData:
  def __init__(self, async_client: SuezAsyncClient, client: SuezClient = None):
    self._async_client = async_client
    self._sync_client = client

  async def get_consumption_index(self):
    """Fetch consumption index."""
    LOGGER.debug("getting consumption index")
    async with await self._async_client.get(API_CONSUMPTION_INDEX) as data:
      if data.status != 200:
        raise PySuezConnexionError("Error while getting consumption index")
      json = await data.json()
      response_data = ConsumptionIndexResult(**json)
      LOGGER.debug('Retrieved consumption index')
      return response_data

  async def get_alerts(self) -> AlertResult:
    """Fetch alert data from Suez."""
    LOGGER.debug("getting alert")
    async with await self._async_client.get(API_ENDPOINT_ALERT) as data:
      if data.status != 200:
        raise PySuezConnexionError("Error while requesting alerts")

      json = await data.json()
      alert_response = AlertQueryResult(**json)
      return AlertResult(alert_response.content.leak.status != 'NO_ALERT',
                         alert_response.content.overconsumption.status != 'NO_ALERT')

  async def get_price(self) -> PriceResult:
    """Fetch water price in e/m3"""
    LOGGER.debug("getting price")
    contract = await self.contract_data()
    async with await self._async_client.get(INFORMATION_ENDPOINT_PRICE + contract.inseeCode,
                                            need_connection=False) as data:
      json = await data.json()
      price = PriceResult(**json)
      return price

  async def get_quality(self) -> QualityResult:
    """Fetch water quality"""
    LOGGER.debug("getting quality")
    contract = await self.contract_data()
    data = self._sync_client.get(INFORMATION_ENDPOINT_QUALITY + contract.inseeCode,
                           need_connection=False)
    quality = QualityResult(**data.json())
    return quality

  async def get_interventions(self) -> InterventionResult:
    """Fetch water interventions"""
    LOGGER.debug("getting intervention")
    contract = await self.contract_data()
    data = self._sync_client.get(
      INFORMATION_ENDPOINT_INTERVENTION + contract.inseeCode,
      need_connection=False)
    intervention = InterventionResult(**data.json())
    return intervention

  async def get_limestone(self) -> LimestoneResult:
    """Fetch water limestone values"""
    LOGGER.debug("getting limestone")
    contract = await self.contract_data()
    data = self._sync_client.get(
      INFORMATION_ENDPOINT_LIMESTONE + contract.inseeCode,
      need_connection=False)
    limestone = LimestoneResult(**data.json())
    return limestone

  async def contract_data(self) -> ContractResult:
    LOGGER.debug("getting contract")
    url = '/public-api/user/donnees-contrats'
    async with await self._async_client.get(url) as data:
      json = await data.json()
      contract = ContractResult(json[0])
      return contract

  async def fetch_day_data(self, date: datetime) -> DayDataResult | None:
    LOGGER.debug("getting day data: " + str(date))
    year = date.year
    month = date.month

    result_by_day = await self.fetch_month_data(year, month)
    if len(result_by_day) == 0:
      return None
    return result_by_day[len(result_by_day) - 1]

  async def fetch_yesterday_data(self) -> DayDataResult | None:
    LOGGER.debug("getting yesterday data")
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    result_by_day = await self.fetch_day_data(yesterday)
    if result_by_day is None:
      result_by_day = await self.fetch_day_data(yesterday - timedelta(days=1))
    if result_by_day is None:
      return None
    return result_by_day

  async def fetch_month_data(self, year, month) -> list[DayDataResult]:
    LOGGER.debug('getting month: ' + str(year) + ' / ' + str(month))
    now = datetime.now()

    async with await self._async_client.get(
        API_ENDPOINT_DAY_DATA + ('{}/{}/'.format(year, month)),
        with_counter_id=True, params={
          '_=': now.timestamp()
        }) as data:
      if data.status != 200:
        raise PySuezConnexionError(
          "Error while requesting data: status={}".format(data.status))

      result_by_day = await data.json()
      if result_by_day[0] == 'ERR':
        raise PySuezDataError(
          "Error while requesting data: {}".format(result_by_day[1]))

      result = []
      for day in result_by_day:
        date = datetime.strptime(day[0], '%d/%m/%Y')
        total = float(day[2])
        if total > 0:
          result.append(
            DayDataResult(
              date.date(),
              float(day[1]) * 1000,
              total,
            )
          )
      return result

  def fetch_all_available(self, since: date | None = None) -> list[DayDataResult]:
    LOGGER.debug("getting all available data")
    current = datetime.now().date()
    result = []
    while since is None or current >= since:
      try:
        current = current.replace(day=1, hour=0, minute=0, second=0,
                                  microsecond=0)
        month = self.fetch_month_data(current.year, current.month)
        next_result = []
        next_result.extend(month)
        next_result.extend(result)
        result = next_result
        current = current - timedelta(days=1)
      except PySuezDataError:
        return result

  def get_attribution(self):
    return self._async_client.get_attribution()
