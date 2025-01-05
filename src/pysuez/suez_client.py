import asyncio
from enum import Enum
import logging
from datetime import date, datetime, timedelta
from typing import Any

import aiohttp
from aiohttp import ClientSession, ClientTimeout
from aiohttp.client import ClientResponse

from pysuez.const import (
    API_CONSUMPTION_INDEX,
    API_ENDPOINT_ALERT,
    API_ENDPOINT_LOGIN,
    API_ENDPOINT_METERS,
    API_ENDPOINT_MONTH_DATA,
    API_ENPOINT_TELEMETRY,
    ATTRIBUTION,
    BASE_URI,
    INFORMATION_ENDPOINT_INTERVENTION,
    INFORMATION_ENDPOINT_LIMESTONE,
    INFORMATION_ENDPOINT_PRICE,
    INFORMATION_ENDPOINT_QUALITY,
    MAX_REQUEST_ATTEMPT,
    TOKEN_HEADERS,
)
from pysuez.exception import (
    PySuezConnexionError,
    PySuezConnexionNeededException,
    PySuezDataError,
    PySuezError,
)
from pysuez.models import (
    AggregatedData,
    AlertQueryResult,
    AlertResult,
    ConsumptionIndexResult,
    ContractResult,
    InterventionResult,
    LimestoneResult,
    MeterListResult,
    PriceResult,
    QualityResult,
    TelemetryMeasure,
    TelemetryResult,
    ErrorResponse,
)
from pysuez.utils import cubic_meters_to_liters, extract_token, next_month

_LOGGER = logging.getLogger(__name__)


class TelemetryMode(Enum):
    DAILY = "daily"
    MONTHLY = "monthly"


class SuezClient:
    """Client used to interact with suez website."""

    _token: str | None = None
    _headers: dict | None = None
    _session: ClientSession | None = None

    def __init__(
        self,
        username: str,
        password: str,
        counter_id: int | None,
        timeout: ClientTimeout | None = None,
        url: str = BASE_URI,
    ) -> None:
        """Initialize the client object."""

        self._username = username
        self._password = password
        self._counter_id = counter_id
        self._hostname = url
        if timeout is None:
            self._timeout = ClientTimeout(total=60)
        else:
            self._timeout = timeout

    async def check_credentials(self) -> bool:
        try:
            await self._connect()
            return True
        except Exception:
            return False
        finally:
            await self.close_session()

    async def find_counter(self) -> int:
        _LOGGER.debug("Try finding counter")

        meters = await self.get_meters()

        if meters.message != "OK":
            raise PySuezError("Error while fetching meter id")
        self._counter_id = meters.content.clientCompteursPro[0].compteursPro[0].idPDS
        _LOGGER.debug("Found counter {}".format(self._counter_id))
        return self._counter_id

    async def close_session(self) -> None:
        """Close current session."""
        if self._session is not None:
            _LOGGER.debug("Closing suez session")
            try:
                await self._logout()
            finally:
                await self._session.close()

            _LOGGER.debug("Successfully closed suez session")
        self._session = None

    async def fetch_yesterday_data(self) -> TelemetryMeasure | None:
        """Retrieve yesterday consumption if available or none if not."""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        telemetry = await self.fetch_telemetry(
            mode=TelemetryMode.DAILY, start=yesterday.date()
        )
        return telemetry[0] if len(telemetry) > 0 else None

    async def fetch_month_data(self, year: int, month: int) -> list[TelemetryMeasure]:
        now = datetime.now()

        requested_date = now.replace(year=year, month=month, day=1).date()

        return await self.fetch_telemetry(
            TelemetryMode.DAILY, requested_date, next_month(requested_date)
        )

    async def fetch_all_daily_data(
        self, since: date | None = None, timeout: int | None = 60
    ) -> list[TelemetryMeasure]:
        async with asyncio.timeout(timeout):
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
                    if len(month) == 0:
                        return result
                    next_result = []
                    next_result.extend(month)
                    next_result.extend(result)
                    result = next_result
                    current = current - timedelta(days=1)
                except PySuezDataError:
                    return result
            return result

    async def fetch_telemetry(
        self, mode: TelemetryMode, start: date, end: date | None = None
    ) -> list[TelemetryMeasure]:
        _LOGGER.debug("Fetch %s telemetry from %s to %s", mode, start, end)
        if not end:
            end = datetime.now().date()
        telemetry_json = await self._get(
            API_ENPOINT_TELEMETRY,
            params={
                "id_PDS": self._counter_id,
                "mode": mode.value,
                "start_date": start.strftime("%Y-%m-%d"),
                "end_date": end.strftime("%Y-%m-%d"),
            },
            none_error_code="02",
        )
        if telemetry_json:
            return TelemetryResult(**telemetry_json).content.measures
        return []

    async def fetch_aggregated_data(self) -> AggregatedData:
        """Fetch latest data from Suez."""
        now = datetime.now()
        today_year = int(now.strftime("%Y"))
        today_month = int(now.strftime("%m"))

        yesterday_data = await self.fetch_yesterday_data()
        if yesterday_data is not None:
            state = yesterday_data.volume
        else:
            state = None

        month_data = await self.fetch_month_data(today_year, today_month)
        current_month = {}
        for item in month_data:
            current_month[item.date] = item.volume

        if int(today_month) == 1:
            last_month = 12
            last_month_year = today_year - 1
        else:
            last_month = today_month - 1
            last_month_year = today_year

        previous_month_data = await self.fetch_month_data(last_month_year, last_month)
        previous_month = {}
        for item in previous_month_data:
            previous_month[item.date] = item.volume

        (
            highest_monthly_consumption,
            last_year,
            current_year,
            history,
        ) = await self._fetch_aggregated_statistics()

        return AggregatedData(
            value=state,
            current_month=current_month,
            previous_month=previous_month,
            highest_monthly_consumption=highest_monthly_consumption,
            previous_year=last_year,
            current_year=current_year,
            history=history,
            attribution=ATTRIBUTION,
        )

    async def get_consumption_index(self) -> ConsumptionIndexResult:
        """Fetch consumption index."""
        json = await self._get(API_CONSUMPTION_INDEX)
        return ConsumptionIndexResult(**json)

    async def get_alerts(self) -> AlertResult:
        """Fetch alert data from Suez."""
        json = await self._get(API_ENDPOINT_ALERT)
        alert_response = AlertQueryResult(**json)
        return AlertResult(
            alert_response.content.leak.status != "NO_ALERT",
            alert_response.content.overconsumption.status != "NO_ALERT",
        )

    async def get_meters(self) -> MeterListResult:
        json = await self._get(API_ENDPOINT_METERS)
        meter_result = MeterListResult(**json)
        return meter_result

    async def get_price(self) -> PriceResult:
        """Fetch water price in e/m3"""
        contract = await self.contract_data()
        json = await self._get(INFORMATION_ENDPOINT_PRICE, contract.inseeCode)
        return PriceResult(**json)

    async def get_water_quality(self) -> QualityResult:
        """Fetch water quality"""
        contract = await self.contract_data()
        json = await self._get(INFORMATION_ENDPOINT_QUALITY, contract.inseeCode)
        return QualityResult(**json)

    async def get_interventions(self) -> InterventionResult:
        """Fetch water interventions"""
        contract = await self.contract_data()
        json = await self._get(
            INFORMATION_ENDPOINT_INTERVENTION,
            contract.inseeCode,
        )
        return InterventionResult(**json)

    async def get_limestone(self) -> LimestoneResult:
        """Fetch water limestone values"""
        contract = await self.contract_data()
        json = await self._get(INFORMATION_ENDPOINT_LIMESTONE, contract.inseeCode)
        return LimestoneResult(**json)

    async def contract_data(self) -> ContractResult:
        url = "/public-api/user/donnees-contrats"
        json = await self._get(url)
        return ContractResult(json[0])

    async def _fetch_aggregated_statistics(
        self,
    ) -> tuple[int, int, int, dict[date, float]]:
        try:
            statistics_url = API_ENDPOINT_MONTH_DATA
            fetched_data: list = await self._get(statistics_url, with_counter_id=True)
            highest_monthly_consumption = int(
                cubic_meters_to_liters(float(fetched_data[-1]))
            )
            fetched_data.pop()
            last_year = int(cubic_meters_to_liters(float(fetched_data[-1])))
            fetched_data.pop()
            current_year = int(cubic_meters_to_liters(float(fetched_data[-1])))
            fetched_data.pop()
            history = {}
            for item in fetched_data:
                history[item[3]] = int(cubic_meters_to_liters(float(item[1])))
        except ValueError:
            raise PySuezError("Issue with history data")
        return highest_monthly_consumption, last_year, current_year, history

    async def _get_token(self) -> None:
        """Get the token"""
        headers = {**TOKEN_HEADERS}
        url = self._hostname + API_ENDPOINT_LOGIN

        session = self._get_session()
        async with session.get(url, headers=headers, timeout=self._timeout) as response:
            headers["Cookie"] = ""
            cookies = response.cookies
            for key in cookies.keys():
                if headers["Cookie"]:
                    headers["Cookie"] += "; "
                headers["Cookie"] += key + "=" + cookies.get(key).value

            page = await response.text("utf-8")
            self._token = extract_token(page)
            self._headers = headers

    async def _connect(self) -> bool:
        """Connect and get the cookie"""
        data, url = await self._get_credential_query()
        try:
            session = self._get_session()
            async with session.post(
                url,
                headers=self._headers,
                data=data,
                allow_redirects=True,
                timeout=self._timeout,
            ) as response:
                if response.status >= 400:
                    raise PySuezConnexionError(f"Login error: status={response.status}")
                cookies = session.cookie_jar.filter_cookies(response.url.origin())
                session_cookie = cookies.get("eZSESSID")
                if session_cookie is None:
                    raise PySuezConnexionError(
                        "Login error: Please check your username/password."
                    )
                # Get the URL after possible redirection
                self._hostname = response.url.origin().__str__()
                _LOGGER.debug(
                    f"Login successful, redirected from {url} to {self._hostname}"
                )

                self._headers["Cookie"] = ""
                session_id = session_cookie.value
                self._headers["Cookie"] = "eZSESSID=" + session_id
                return True
        except Exception:
            raise PySuezConnexionError("Can not submit login form.")

    async def _get(
        self,
        *url: str,
        with_counter_id=False,
        params: None | dict[str, Any] = None,
        read: str | None = "json",
        none_error_code: None | str = None,
    ) -> None | Any:
        url = self._get_url(self._hostname, *url, with_counter_id=with_counter_id)
        _LOGGER.debug(f"Try requesting {url}")

        remaing_attempt = MAX_REQUEST_ATTEMPT
        while remaing_attempt > 0:
            remaing_attempt -= 1
            try:
                async with self._get_session().get(
                    url,
                    headers=self._headers,
                    params=params,
                    timeout=self._timeout,
                    allow_redirects=not read,
                ) as response:
                    if not await self._check_request_status(
                        response, url, none_error_code
                    ):
                        return None
                    if not read:
                        return
                    if read == "json":
                        return await response.json()
                    return await response.text()
            except PySuezConnexionNeededException as err:
                if remaing_attempt > 0:
                    await self._connect()
                else:
                    raise err
            except Exception as ex:
                # await self.close_session()
                if remaing_attempt == 0:
                    raise PySuezError(f"Error during get query to {url}") from ex
                else:
                    _LOGGER.warning(
                        f"Discarded error during query to {url}", exc_info=True
                    )

    def _get_session(self) -> ClientSession:
        if self._session is not None:
            return self._session
        self._session = aiohttp.ClientSession()
        return self._session

    async def _get_credential_query(self):
        await self._get_token()
        data = {
            "_csrf_token": self._token,
            "tsme_user_login[_username]": self._username,
            "tsme_user_login[_password]": self._password,
        }
        url = self._get_url(self._hostname, API_ENDPOINT_LOGIN, with_counter_id=False)
        return data, url

    async def _logout(self) -> None:
        if self._session is not None:
            await self._get("/mon-compte-en-ligne/deconnexion", read=False)
            _LOGGER.debug("Successfully logged out from suez")

    def _get_url(self, *url: str, with_counter_id: bool) -> str:
        res = ""
        first = True
        for part in url:
            next = str(part)
            if not first and not res.endswith("/") and not next.startswith("/"):
                res += "/"
            res += next
            first = False

        if with_counter_id:
            if not res.endswith("/"):
                res += "/"
            res += str(self._counter_id)
        return res

    async def _check_request_status(
        self, response: ClientResponse, url: str, none_error_code: None | str = None
    ) -> bool:
        _LOGGER.debug(f"{url} responded with {response.status}")
        if response.status >= 200 and response.status < 300:
            return True
        if response.status >= 300 and response.status < 400:
            redirection_target = response.headers.get("Location")
            if redirection_target and API_ENDPOINT_LOGIN in redirection_target:
                raise PySuezConnexionNeededException(
                    f"Redirected to {redirection_target}, should log again"
                )
            else:
                _LOGGER.debug(f"Ignored redirection to {redirection_target}")
                return True
        if none_error_code:
            error = ErrorResponse(**(await response.json()))
            if error.code == none_error_code:
                return False
        raise PySuezError(
            f"Unexpected response status {response.status} for {url} with {await response.text()}"
        )
