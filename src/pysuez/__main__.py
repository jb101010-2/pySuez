import argparse
import asyncio
import sys
from datetime import datetime, timedelta

from pysuez.suez_client import SuezClient


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

    client = SuezClient(args.username, args.password, args.counter_id)
    try:
        if args.counter_id is None:
            await client.find_counter()

        if args.mode == "alerts":
            print("getting alerts")
            alerts = await client.get_alerts()
            print("leak=", alerts.leak, ", consumption=", alerts.overconsumption)
        elif args.mode == "test":
            print(await client.contract_data())
            print(await client.get_alerts())
            print(await client.get_price())
            print(await client.get_interventions())
            print(await client.get_water_quality())
            print(await client.get_limestone())
            print(await client.fetch_yesterday_data())
            print(
                await client.fetch_all_daily_data(
                    since=(datetime.now() - timedelta(weeks=4)).date()
                )
            )
            print(await client.fetch_aggregated_data())
        else:
            print(await client.fetch_aggregated_data())
    except BaseException as exp:
        print(exp)
        return 1
    finally:
        await client.close_session()


if __name__ == "__main__":
    res = asyncio.run(main())
    sys.exit(res)
