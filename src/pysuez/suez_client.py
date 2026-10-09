import asyncio
import logging
from datetime import date, datetime, timedelta
from enum import Enum
from itertools import chain
from typing import Any

import aiohttp
from aiohttp import ClientSession, ClientTimeout
from aiohttp.client import ClientResponse

from pysuez.const import (
    API_CONSUMPTION_INDEX,
    API_ENDPOINT_ALERT,
    API_ENDPOINT_CONTRACTS,
    API_ENDPOINT_LOGIN,
    API_ENDPOINT_METERS,
    API_ENDPOINT_PRICE,
    API_ENDPOINT_SWITCH_CONTRACT,
    API_ENPOINT_TELEMETRY,
    ATTRIBUTION,
    BASE_URI,
    INFORMATION_ENDPOINT_INTERVENTION,
    INFORMATION_ENDPOINT_LIMESTONE,
    INFORMATION_ENDPOINT_QUALITY,
    MAX_REQUEST_ATTEMPT,
    SWITCH_CONTRACT_REDIRECT,
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
    ErrorResponse,
    InterventionResult,
    LimestoneResult,
    MeterListResult,
    PriceResult,
    QualityResult,
    TelemetryMeasure,
    TelemetryResult,
)
from pysuez.utils import extract_token, next_month

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
        self._contract_ref: str | None = None
        self._contract_resolved = False
        self._selecting_contract = False

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
        ) = await self._fetch_aggregated_statistics(today_year)

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
        json = await self._get(API_ENDPOINT_PRICE)
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
        """Return the current contract of the session.

        Each login switches the session to the contract holding the counter
        (see select_counter_contract), so this is the contract of the counter.
        Falls back to the first contract if none is flagged as current.
        """
        json = await self._get(API_ENDPOINT_CONTRACTS)
        current = next((c for c in json if c.get("isCurrentContract")), json[0])
        return ContractResult(current)

    async def select_counter_contract(self) -> None:
        """Switch the session to the contract holding the configured counter.

        On accounts holding several contracts, the website APIs (telemetry,
        price, meters list...) are scoped to the "current" contract of the
        session, which is reset to the default contract at each login.
        Requesting the telemetry of a counter attached to another contract
        then fails with error code 13 ("Le compteur n'appartient pas à
        l'utilisateur.").

        This is called automatically after each login. It does nothing when
        no counter id is set or when the account holds a single contract.
        """
        if self._counter_id is None:
            return
        self._selecting_contract = True
        try:
            if not self._contract_resolved:
                self._contract_ref = await self._find_counter_contract()
                self._contract_resolved = True
            if self._contract_ref is not None:
                await self._switch_contract(self._contract_ref)
        finally:
            self._selecting_contract = False

    async def _find_counter_contract(self) -> str | None:
        """Return the reference of the contract holding the counter.

        Returns None for single-contract accounts (nothing to switch) or when
        the counter is not found in any contract.
        """
        contracts = await self._get(API_ENDPOINT_CONTRACTS) or []
        if len(contracts) <= 1:
            _LOGGER.debug("Single contract account, no contract switch needed")
            return None

        counter_id = str(self._counter_id)
        initial_ref = None
        for contract in contracts:
            ref = contract.get("fullRefFormat") or contract.get("fullRef")
            if not ref:
                continue
            if contract.get("isCurrentContract"):
                initial_ref = ref
            await self._switch_contract(ref)
            if counter_id in await self._current_contract_counter_ids():
                _LOGGER.debug("Counter %s found in contract %s", counter_id, ref)
                return ref

        _LOGGER.warning(
            "Counter %s not found in any of the %s contracts of this account",
            counter_id,
            len(contracts),
        )
        if initial_ref is not None:
            await self._switch_contract(initial_ref)
        return None

    async def _current_contract_counter_ids(self) -> set[str]:
        """Return the counter ids (idPDS) of the session current contract."""
        json = await self._get(API_ENDPOINT_METERS) or {}
        content = json.get("content") or {}
        return {
            str(meter.get("idPDS"))
            for client in content.get("clientCompteursPro") or []
            for meter in client.get("compteursPro") or []
        }

    async def _switch_contract(self, ref: str) -> None:
        """Switch the session current contract, as the website contract selector does.

        The website answers with a redirection to the dashboard: redirections
        are not followed here (read="text"), a redirection to the login page
        triggers a new login and a retry.
        """
        _LOGGER.debug("Switching session to contract %s", ref)
        await self._get(
            API_ENDPOINT_SWITCH_CONTRACT,
            ref,
            params={"redirect": SWITCH_CONTRACT_REDIRECT},
            read="text",
        )

    async def _fetch_aggregated_statistics(
        self,
        current_year: int,
    ) -> tuple[int, int, int, dict[str, float]]:
        try:

            def map_to_measure(measure: TelemetryMeasure) -> float:
                return measure.volume if measure.volume else 0

            current_year_monthly = await self.fetch_telemetry(
                mode=TelemetryMode.MONTHLY, start=date(current_year, 1, 1)
            )
            last_year_monthly = await self.fetch_telemetry(
                mode=TelemetryMode.MONTHLY,
                start=date(current_year - 1, 1, 1),
                end=date(current_year - 1, 12, 31),
            )

            highest_monthly_consumption = max(
                chain(
                    map(map_to_measure, current_year_monthly),
                    map(map_to_measure, last_year_monthly),
                )
            )
            current_year_total = int(sum(map(map_to_measure, current_year_monthly)))
            last_year_total = sum(map(map_to_measure, last_year_monthly))

            history = {}
            for item in last_year_monthly:
                history[item.date.strftime("%Y-%m")] = int(item.volume)
            for item in current_year_monthly:
                history[item.date.strftime("%Y-%m")] = int(item.volume)
        except ValueError:
            raise PySuezError("Issue with history data")
        return highest_monthly_consumption, last_year_total, current_year_total, history

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
        except Exception:
            raise PySuezConnexionError("Can not submit login form.")

        # Each login resets the session to the default contract: switch back to
        # the contract holding the counter. This must never prevent the login.
        if not self._selecting_contract:
            try:
                await self.select_counter_contract()
            except Exception:
                _LOGGER.warning(
                    "Could not select the contract of counter %s",
                    self._counter_id,
                    exc_info=True,
                )
        return True

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
            if response.status == 204:
                return False
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
