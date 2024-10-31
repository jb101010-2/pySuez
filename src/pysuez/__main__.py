import argparse
import asyncio
import sys
from datetime import datetime, timedelta

from .async_client import SuezAsyncClient
from .suez_data import SuezData


async def main():
    """Main function"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", required=True, help="Suez username")
    parser.add_argument("-p", "--password", required=True, help="Password")
    parser.add_argument("-c", "--counter_id", required=False, help="Counter Id")
    parser.add_argument(
        "-m",
        "--mode",
        required=False,
        help="Retrieval mode: alerts / data / test (all functions called)",
    )

    args = parser.parse_args()

    async_client = SuezAsyncClient(args.username, args.password, args.counter_id)
    if args.counter_id is None:
        await async_client.counter_finder()
    data = SuezData(async_client)

    try:
        if args.mode == "alerts":
            print("getting alerts")
            alerts = await data.get_alerts()
            print("leak=", alerts.leak, ", consumption=", alerts.overconsumption)
        elif args.mode == "test":
            print(await data.contract_data())
            print(await data.get_alerts())
            print(await data.get_price())
            print(await data.get_interventions())
            print(await data.get_quality())
            print(await data.get_limestone())
            print(await data.fetch_yesterday_data())
            print(
                await data.fetch_all_available(
                    since=(datetime.now() - timedelta(weeks=4)).date()
                )
            )
            print(await data.fetch_all_deprecated_data())
        else:
            print(await data.fetch_all_deprecated_data())
    except BaseException as exp:
        print(exp)
        return 1
    finally:
        await async_client.close_session()


if __name__ == "__main__":
    res = asyncio.run(main())
    sys.exit(res)
