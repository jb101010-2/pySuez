import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta

from pysuez.const import BASE_URI
from pysuez.suez_client import SuezClient, TelemetryMode

_LOGGER = logging.getLogger(__name__)


async def main():
    """Main function"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", required=True, help="Suez username")
    parser.add_argument("-p", "--password", required=True, help="Password")
    parser.add_argument("-c", "--counter_id", required=False, help="Counter Id")
    parser.add_argument(
        "-url", "--url", required=False, help=f"Endpoint url: default to {BASE_URI}"
    )
    parser.add_argument("-l", "--log-level", required=False, help="Log level")
    parser.add_argument(
        "-m",
        "--mode",
        required=False,
        help="Retrieval mode: alerts / data / test (all functions called)",
    )

    args = parser.parse_args()

    log_level = logging.INFO
    if args.log_level is not None:
        log_level = getattr(logging, args.log_level.upper(), None)

    logging.basicConfig(level=log_level)

    client = SuezClient(args.username, args.password, args.counter_id)
    try:
        if args.counter_id is None:
            await client.find_counter()

        if args.mode == "telemetry":
            _LOGGER.info("Getting telemetry for 90 days")
            start = datetime.now().date() - timedelta(days=90)

            telemetry = await client.fetch_telemetry(
                mode=TelemetryMode.DAILY, start=start
            )
            _LOGGER.info("Got telemetry result: ")
            _LOGGER.info(telemetry)
        elif args.mode == "alerts":
            _LOGGER.info("getting alerts")
            alerts = await client.get_alerts()
            _LOGGER.info("leak=", alerts.leak, ", consumption=", alerts.overconsumption)
        elif args.mode == "test":
            _LOGGER.debug("Starting test mode")
            _LOGGER.info(await client.contract_data())
            _LOGGER.info(await client.get_alerts())
            _LOGGER.info(await client.get_price())
            _LOGGER.info(await client.get_interventions())
            _LOGGER.info(await client.get_water_quality())
            _LOGGER.info(await client.get_limestone())
            _LOGGER.info(await client.fetch_yesterday_data())
            _LOGGER.info(
                await client.fetch_all_daily_data(
                    since=(datetime.now() - timedelta(weeks=4)).date()
                )
            )
            _LOGGER.info(await client.fetch_aggregated_data())
        else:
            _LOGGER.info(await client.fetch_aggregated_data())
    except BaseException:
        _LOGGER.exception()
        return 1
    finally:
        await client.close_session()


if __name__ == "__main__":
    res = asyncio.run(main())
    sys.exit(res)
