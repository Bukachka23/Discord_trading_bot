import unittest
from unittest.mock import patch, MagicMock

from MAIN.app import place_order, cancel_order, parse_message



class TestParseMessage(unittest.TestCase):

    def test_parse_message_valid(self):
        message = """
        $BTCUSDT LONG
        ENTRY = $50000
        STOPLOSS = $49000
        TARGETS: $51000
        """
        expected_output = {
            'symbol': 'BTCUSDT',
            'entry_prices': [50000.0],
            'stop_loss': 49000.0,
            'final_target': 51000.0
        }
        self.assertEqual(parse_message(message), expected_output)

    def test_parse_message_multiple_entries(self):
        message = """
        $ETHUSDT LONG
        ENTRY = $3000
        ENTRY = $3100
        STOPLOSS = $2900
        TARGETS: $3200
        """
        expected_output = {
            'symbol': 'ETHUSDT',
            'entry_prices': [3000.0, 3100.0],
            'stop_loss': 2900.0,
            'final_target': 3200.0
        }
        self.assertEqual(parse_message(message), expected_output)

    def test_parse_message_no_stop_loss(self):
        message = """
        $BNBUSDT LONG
        ENTRY = $400
        TARGETS: $450
        """
        expected_output = {
            'symbol': 'BNBUSDT',
            'entry_prices': [400.0],
            'stop_loss': None,
            'final_target': 450.0
        }
        self.assertEqual(parse_message(message), expected_output)

    def test_parse_message_no_final_target(self):
        message = """
        $XRPUSDT LONG
        ENTRY = $1
        STOPLOSS = $0.9
        """
        expected_output = {
            'symbol': 'XRPUSDT',
            'entry_prices': [1.0],
            'stop_loss': 0.9,
            'final_target': None
        }
        self.assertEqual(parse_message(message), expected_output)

    def test_parse_message_invalid_format(self):
        message = """
        $BTCUSDT
        """
        with self.assertRaises(ValueError):
            parse_message(message)

    def test_parse_message_empty_message(self):
        message = ""
        with self.assertRaises(ValueError):
            parse_message(message)

class TestPlaceOrder(unittest.TestCase):

    @patch('main.client')
    def test_place_order(self, mock_client):
        mock_client.futures_change_leverage.return_value = {'leverage': 5}
        mock_client.futures_account_balance.return_value = [{'asset': 'USDT', 'balance': '1000'}]
        mock_client.futures_create_order.return_value = {'orderId': '12345'}

        place_order('BTCUSDT', 50000, 49000, 5, 'MARKET')

        mock_client.futures_change_leverage.assert_called_once_with(symbol='BTCUSDT', leverage=5)
        mock_client.futures_account_balance.assert_called_once()
        mock_client.futures_create_order.assert_any_call(
            symbol='BTCUSDT',
            side='BUY',
            type='MARKET',
            quantity=0.001
        )
        mock_client.futures_create_order.assert_any_call(
            symbol='BTCUSDT',
            side='SELL',
            type='MARKET',
            stopPrice=49000,
            quantity=0.001
        )

class TestCancelOrder(unittest.TestCase):

    @patch('main.client')
    def test_cancel_order(self, mock_client):
        mock_client.futures_cancel_order.return_value = {'status': 'CANCELED'}

        cancel_order('BTCUSDT', '12345')

        mock_client.futures_cancel_order.assert_called_once_with(symbol='BTCUSDT', orderId='12345')

if __name__ == '__main__':
    unittest.main()
# Function to close an order in profit
# def close_order_in_profit(symbol, quantity, price):
#     try:
#         order = client.order_limit_sell(
#             symbol=symbol,
#             quantity=quantity,
#             price=price
#         )
#         print(f"Closed order in profit: {order}")
#     except BinanceAPIException as e:
#         print(f"Error closing order in profit: {e}")

# symbol = 'OAXUSDT'
# entry_prices = [0.2573, 0.1946, 0.1710]
# stop_loss_price = 0.1585
# final_target_price = 0.9153
#
#
# cancel_open_orders(symbol)
#
#
# for price in entry_prices:
#     quantity = calculate_quantity(client, symbol, price)
#     order = place_spot_order(client, symbol, price, quantity)
#     print(f"Placed order: {order}")
# Example Discord message