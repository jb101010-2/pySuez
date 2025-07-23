BASE_URI = "https://www.toutsurmoneau.fr"
API_ENDPOINT_LOGIN = "/mon-compte-en-ligne/je-me-connecte"

ATTRIBUTION = "Data provided by toutsurmoneau.fr"

API_ENDPOINT_METERS = "/public-api/cel-consumption/meters-list"
API_ENDPOINT_ALERT = "/public-api/contract/tile/alerts"
_INFORMATION_ENDPOINT = "/information/donnee/"
INFORMATION_ENDPOINT_INTERVENTION = _INFORMATION_ENDPOINT + "intervention/"
INFORMATION_ENDPOINT_QUALITY = _INFORMATION_ENDPOINT + "quality/"
INFORMATION_ENDPOINT_PRICE = _INFORMATION_ENDPOINT + "price/"
INFORMATION_ENDPOINT_LIMESTONE = _INFORMATION_ENDPOINT + "limestone/"
API_CONSUMPTION_INDEX = "/public-api/contract/tile/consumption"

API_ENPOINT_TELEMETRY = "/public-api/cel-consumption/telemetry"


TOKEN_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept-Language": "fr,fr-FR;q=0.8,en;q=0.6",
    "User-Agent": "curl/7.54.0",
    "Connection": "keep-alive",
    "Cookie": "",
}

LITERS_PER_CUBIC_METER = 1000

MAX_REQUEST_ATTEMPT = 2

https://www.toutsurmoneau.fr/public-api/cel-consumption/nontelemetry?id_PDS=5492790162&start_date=2020-01-01&end_date=2025-02-20
{"content":{"measures":[{"date":"23\/09\/2024","index":549,"volume":53,"type":"R","previousDateMeasure":"12\/03\/2024","numberOfDays":195},{"date":"12\/03\/2024","index":496,"volume":57,"type":"R","previousDateMeasure":"27\/09\/2023","numberOfDays":167},{"date":"27\/09\/2023","index":439,"volume":58,"type":"E","previousDateMeasure":"12\/03\/2023","numberOfDays":199},{"date":"12\/03\/2023","index":381,"volume":74,"type":"R","previousDateMeasure":"27\/09\/2022","numberOfDays":166},{"date":"27\/09\/2022","index":307,"volume":50,"type":"E","previousDateMeasure":"17\/03\/2022","numberOfDays":194},{"date":"17\/03\/2022","index":257,"volume":36,"type":"E","previousDateMeasure":"27\/09\/2021","numberOfDays":171},{"date":"27\/09\/2021","index":221,"volume":42,"type":"E","previousDateMeasure":"15\/03\/2021","numberOfDays":196},{"date":"15\/03\/2021","index":179,"volume":60,"type":"R","previousDateMeasure":"25\/09\/2020","numberOfDays":171}],"arrivalDate":"31\/07\/2020"},"code":"00","message":"OK"}