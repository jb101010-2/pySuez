import argparse
import sys

from pysuez import SuezClient
from pysuez.suez_data import SuezData


def main():
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
  data = SuezData()

  try:
    if args.mode == 'alerts':
      print('getting alerts')
      # alerts = data.get_alerts()
      # print("leak=", alerts.leak, ", consumption=", alerts.overconsumption)
    elif args.mode == 'test':
      print(data.contract_data())
      # print(data.get_alerts())
      print(data.get_price())
      print(data.get_interventions())
      print(data.get_quality())
      print(data.get_limestone())
      print(data.fetch_yesterday_data())
      # print('')
      # all_data = data.fetch_all_available()
      # current = 0
      # for day in all_data:
      #   current = current + 1
      #   print(day, end=' - ')
      #   if current % 30 == 0:
      #     print('')
      # print('')

    else:
      client.update()
      print(client.attributes)
  except BaseException as exp:
    print(exp)
    return 1
  finally:
    client.close_session()


if __name__ == '__main__':
  sys.exit(main())
