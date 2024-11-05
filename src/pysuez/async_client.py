import logging
import re

import aiohttp
from aiohttp import ClientSession
from aiohttp.client import ClientResponse, _BaseRequestContextManager

from .const import API_ENDPOINT_LOGIN, API_HISTORY_CONSUMPTION, BASE_URI, TOKEN_HEADERS
from .exception import PySuezError

_LOGGER = logging.getLogger(__name__)


class SuezAsyncClient:
    """Global variables."""

    def __init__(
        self,
        username,
        password,
        counter_id,
        timeout=None,
    ) -> None:
        """Initialize the client object."""
        self._username = username
        self._password = password
        self._counter_id = counter_id
        self._token = ""
        self._headers = {}
        self._hostname = ""
        self._session: ClientSession | None = None
        self._timeout = timeout
        self.connected = False

    async def _get_token(self) -> None:
        """Get the token"""
        headers = {**TOKEN_HEADERS}
        url = BASE_URI + API_ENDPOINT_LOGIN

        session = self._get_session()
        async with session.get(url, headers=headers, timeout=self._timeout) as response:
            headers["Cookie"] = ""
            cookies = response.cookies
            for key in cookies.keys():
                if headers["Cookie"]:
                    headers["Cookie"] += "; "
                headers["Cookie"] += key + "=" + cookies.get(key).value

            page = await response.text("utf-8")
            self._token = self._extract_token(page)
            _LOGGER.debug("Found token for suez api")
            self._headers = headers

    async def _get_cookie(self) -> bool:
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
                # Get the URL after possible redirect
                self._hostname = response.url.origin().__str__()
                cookies = session.cookie_jar.filter_cookies(response.url.origin())
                session_cookie = cookies.get("eZSESSID")
                if session_cookie is None:
                    raise PySuezError(
                        "Login error: Please check your username/password."
                    )

                self._headers["Cookie"] = ""
                session_id = session_cookie.value
                self._headers["Cookie"] = "eZSESSID=" + session_id
                return True
        except OSError:
            raise PySuezError("Can not submit login form.")

    async def counter_finder(self) -> int:
        page_url = API_HISTORY_CONSUMPTION
        async with await self.get(page_url) as page:
            match = re.search(
                r"'\/mon-compte-en-ligne\/statMData'\s\+\s'/(\d+)'",
                await page.text(),
                re.MULTILINE,
            )
            if match is None:
                raise PySuezError("Counter id not found")
            self._counter_id = int(match.group(1))
            _LOGGER.debug("Found counter {}".format(self._counter_id))
            return self._counter_id

    async def get(
        self, *url: str, with_counter_id=False, need_connection=True, params=None
    ) -> _BaseRequestContextManager[ClientResponse]:
        if need_connection and not self.connected:
            self.connected = await self._get_cookie()

        url = self._get_url(self._hostname, *url, with_counter_id=with_counter_id)
        _LOGGER.debug(f"Request to {url} connected = {self.connected}")
        try:
            return self._get_session().get(url, headers=self._headers, params=params)
        except OSError as ex:
            self.connected = False
            raise PySuezError("Error during get query to " + url) from ex

    async def check_credentials(self) -> bool:
        try:
            await self._get_cookie()
            return True
        except Exception:
            return False
        finally:
            await self.close_session()

    async def close_session(self) -> None:
        """Close current session."""
        _LOGGER.debug("closing suez session")
        if self._session is not None:
            await self._logout()
            await self._get_session().close()
        self._session = None

    def _get_session(self) -> ClientSession:
        if self._session is not None:
            return self._session
        self._session = aiohttp.ClientSession()
        return self._session

    async def _get_credential_query(self):
        await self._get_token()
        data = {
            "_username": self._username,
            "_password": self._password,
            "_csrf_token": self._token,
            "signin[username]": self._username,
            "signin[password]": None,
            "tsme_user_login[_username]": self._username,
            "tsme_user_login[_password]": self._password,
        }
        url = self._get_url(BASE_URI, API_ENDPOINT_LOGIN, with_counter_id=False)
        return data, url

    async def _logout(self) -> None:
        if self._session is not None and self.connected:
            async with await self.get(
                "/mon-compte-en-ligne/deconnexion", need_connection=False
            ) as disconnection:
                if disconnection.status >= 400:
                    raise PySuezError("Disconnection failed")
                _LOGGER.debug("Successfully logged out from suez")
            self.connected = False

    def _extract_token(self, page: str) -> str:
        phrase = re.compile(
            "csrfToken\\\\u0022\\\\u003A\\\\u0022(.*)\\\\u0022,\\\\u0022targetUrl"
        )
        result = phrase.search(page)
        if result is None:
            raise PySuezError("Token not found in query")
        return result.group(1).encode().decode("unicode_escape")

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
