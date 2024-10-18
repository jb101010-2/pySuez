import re

import logging
import aiohttp

from aiohttp.client import ClientResponse, _BaseRequestContextManager
from aiohttp import ClientSession
from pysuez.client import PySuezError

BASE_URI = 'https://www.toutsurmoneau.fr'
API_ENDPOINT_LOGIN = '/mon-compte-en-ligne/je-me-connecte'

LOGGER = logging.getLogger(__name__)


class SuezAsyncClient:
  """Global variables."""

  def __init__(self,
               username,
               password,
               counter_id,
               session: ClientSession | None = None,
               timeout=None):
    """Initialize the client object."""
    self._username = username
    self._password = password
    self._counter_id = counter_id
    self._token = ''
    self._headers = {}
    self._hostname = ''
    self._session = session
    self._timeout = timeout
    self.connected = False

  async def _get_token(self):
    """Get the token"""
    LOGGER.debug("get token")
    headers = {
      'Accept': "application/json, text/javascript, */*; q=0.01",
      'Content-Type': 'application/x-www-form-urlencoded',
      'Accept-Language': 'fr,fr-FR;q=0.8,en;q=0.6',
      'User-Agent': 'curl/7.54.0',
      'Connection': 'keep-alive',
      'Cookie': ''
    }
    global BASE_URI

    url = BASE_URI + API_ENDPOINT_LOGIN

    session = self._get_session()
    async with session.get(url, headers=headers, timeout=self._timeout) as response:
      headers['Cookie'] = ""
      cookies = response.cookies
      for key in cookies.keys():
        if headers['Cookie']:
          headers['Cookie'] += "; "
        headers['Cookie'] += key + "=" + cookies.get(key).value

      phrase = re.compile(
        'csrfToken\\\\u0022\\\\u003A\\\\u0022(.*)\\\\u0022,\\\\u0022targetUrl')
      page = await response.text('utf-8')
      result = phrase.search(page)
      if result is None:
        raise PySuezError("Token not found in query")
      self._token = result.group(1).encode().decode('unicode_escape')
      self._headers = headers

  async def _get_cookie(self):
    """Connect and get the cookie"""
    LOGGER.debug("getting cookie")
    data, url = await self.__get_credential_query()
    try:
      session = self._get_session()
      async with session.post(url,
                              headers=self._headers,
                              data=data,
                              allow_redirects=True,
                              timeout=self._timeout) as response:
        # Get the URL after possible redirect
        self._hostname = response.url.origin().__str__()
        LOGGER.debug(self._hostname)
        cookies = session.cookie_jar.filter_cookies(response.url.origin())
        session_cookie = cookies.get('eZSESSID')
        if session_cookie is None:
          raise PySuezError("Login error: Please check your username/password.")

        self._headers['Cookie'] = ''
        session_id = session_cookie.value
        self._headers['Cookie'] = 'eZSESSID=' + session_id
        return True
    except OSError:
      raise PySuezError("Can not submit login form.")

  def _get_session(self) -> ClientSession:
    if self._session is not None:
      return self._session
    self._session = aiohttp.ClientSession()
    return self._session

  async def __get_credential_query(self):
    LOGGER.debug("getting credential")
    await self._get_token()
    data = {
      '_username': self._username,
      '_password': self._password,
      '_csrf_token': self._token,
      'signin[username]': self._username,
      'signin[password]': None,
      'tsme_user_login[_username]': self._username,
      'tsme_user_login[_password]': self._password
    }
    url = BASE_URI + API_ENDPOINT_LOGIN
    return data, url

  async def counter_finder(self):
    page_url = '/mon-compte-en-ligne/historique-de-consommation-tr'
    async with await self.get(page_url) as page:
      match = re.search(r"'\/mon-compte-en-ligne\/statMData'\s\+\s'/(\d+)'",
                        await page.text(), re.MULTILINE)
      if match is None:
        raise PySuezError("Counter id not found")
      self._counter_id = int(match.group(1))
      LOGGER.debug("Found counter {}".format(self._counter_id))
      return self._counter_id

  async def get(self, url: str, with_counter_id=False, need_connection=True,
                params=None) -> _BaseRequestContextManager[ClientResponse]:
    if need_connection and not self.connected:
      self.connected = await self._get_cookie()

    url = self._hostname + url + '{}'.format(
      self._counter_id if with_counter_id else '')
    LOGGER.debug(f"Getting something {url} connected = {self.connected}")
    try:
      return self._get_session().get(url, headers=self._headers, params=params)
    except OSError as ex:
      self.connected = False
      raise PySuezError("Error during get query to " + url)

  async def check_credentials(self):
    try:
      await self._get_cookie()
      return True
    except Exception:
      return False

  async def close_session(self) -> None:
    """Close current session."""
    LOGGER.debug('closing session')
    if self._session is not None:
      await self._logout()
      await self._get_session().close()
    self._session = None
  
  async def _logout(self) -> None:
    if self._session is not None and self.connected:
      async with await self.get('/mon-compte-en-ligne/deconnexion', need_connection=False) as disconnection:
        if disconnection.status >= 400:
          raise PySuezError('Disconnection failed')
        LOGGER.debug('Successfully logged out from suez')
      self.connected = False

  def get_attribution(self):
    return "Data provided by toutsurmoneau.fr"
