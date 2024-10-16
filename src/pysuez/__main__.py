import asyncio
import argparse
import sys

from pysuez import SuezClient
from pysuez.async_client import SuezAsyncClient
from pysuez.suez_data import SuezData


async def main():
  """Main function"""
  parser = argparse.ArgumentParser()
  parser.add_argument('-u', '--username',
                      required=True, help='Suez username')
  parser.add_argument('-p', '--password',
                      required=True, help='Password')
  parser.add_argument('-c', '--counter_id',
                      required=False, help='Counter Id')
  parser.add_argument('-m', '--mode',
                      required=False,
                      help='Retrieval mode: alerts / data / test (all functions called)')

  args = parser.parse_args()

  client = SuezClient(args.username, args.password, args.counter_id)
  if args.counter_id is None:
    client.counter_finder()
  async_client = SuezAsyncClient(args.username, args.password, args.counter_id)
  data = SuezData(async_client, client)

  try:
    if args.mode == 'alerts':
      print('getting alerts')
      alerts = await data.get_alerts()
      print("leak=", alerts.leak, ", consumption=", alerts.overconsumption)
    elif args.mode == 'test':
      print(await data.contract_data())
      print(await data.get_alerts())
      print(await data.get_price())
      print(await data.get_interventions())
      print(await data.get_quality())
      print(await data.get_limestone())
      print(await data.fetch_yesterday_data())
    else:
      client.update()
      print(client.attributes)
  except BaseException as exp:
    print(exp)
    return 1
  finally:
    client.close_session()


if __name__ == '__main__':
  res = asyncio.run(main())
  sys.exit(res)
