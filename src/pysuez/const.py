BASE_URI = "https://www.toutsurmoneau.fr"
API_ENDPOINT_LOGIN = "/mon-compte-en-ligne/je-me-connecte"

ATTRIBUTION = "Data provided by toutsurmoneau.fr"

API_ENDPOINT_ALERT = "/public-api/contract/tile/alerts"
_INFORMATION_ENDPOINT = "/information/donnee/"
INFORMATION_ENDPOINT_INTERVENTION = _INFORMATION_ENDPOINT + "intervention/"
INFORMATION_ENDPOINT_QUALITY = _INFORMATION_ENDPOINT + "quality/"
INFORMATION_ENDPOINT_PRICE = _INFORMATION_ENDPOINT + "price/"
INFORMATION_ENDPOINT_LIMESTONE = _INFORMATION_ENDPOINT + "limestone/"
API_ENDPOINT_DAY_DATA = "/mon-compte-en-ligne/statJData/"
API_CONSUMPTION_INDEX = "/public-api/contract/tile/consumption"
API_ENDPOINT_MONTH_DATA = "/mon-compte-en-ligne/statMData/"
API_HISTORY_CONSUMPTION = "/mon-compte-en-ligne/historique-de-consommation-tr"


TOKEN_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept-Language": "fr,fr-FR;q=0.8,en;q=0.6",
    "User-Agent": "curl/7.54.0",
    "Connection": "keep-alive",
    "Cookie": "",
}

LITERS_PER_CUBIC_METER = 1000
