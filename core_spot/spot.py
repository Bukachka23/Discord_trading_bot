import math
import os
import logging
from typing import Any, Optional, Dict

from binance.client import Client
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv

from variables.constants import EnvVariables, OrderType

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class SpotClient:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv(EnvVariables.BINANCE_API_KEY.value)
        api_secret = os.getenv(EnvVariables.BINANCE_API_SECRET.value)
        self.client = Client(api_key, api_secret)

    def get_usdt_balance(self) -> float:
        """Get the USDT balance of the account."""
        try:
            balance = self.client.get_asset_balance(asset='USDT')
            return float(balance['free'])
        except BinanceAPIException as e:
            logging.error(f"Error retrieving USDT balance: {e}")
            return 0.0

    def place_spot_order(self, symbol: str, price: float, quantity: float, order_type: OrderType = OrderType.LIMIT) -> (
            Optional)[Dict[str, Any]]:
        """Place a spot order on Binance."""
        try:
            symbol_info = self.client.get_symbol_info(symbol)
            price_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'), None)
            if price_filter:
                tick_size = float(price_filter['tickSize'])
                adjusted_price = round(price / tick_size) * tick_size
                decimal_places = int(abs(math.log10(tick_size)))
                adjusted_price_str = "{:.{}f}".format(adjusted_price, decimal_places)

                if order_type == OrderType.LIMIT:
                    order = self.client.order_limit_buy(
                        symbol=symbol,
                        quantity=quantity,
                        price=adjusted_price_str
                    )
                elif order_type == OrderType.MARKET:
                    order = self.client.order_market_buy(
                        symbol=symbol,
                        quantity=quantity
                    )
                else:
                    raise ValueError("Unsupported order type")

                return order
            else:
                logging.error(f"No PRICE_FILTER found for symbol {symbol}")
                return None
        except BinanceAPIException as e:
            logging.error(f"Error placing spot order: {e}")
            return None

    def calculate_quantity(self, symbol: str, price: float, leverage: int = 1) -> float:
        """Calculate the quantity to buy based on the USDT balance and price."""
        try:
            usdt_balance = self.get_usdt_balance()
            amount_to_use = usdt_balance * 0.05
            initial_quantity = (amount_to_use * leverage) / price
            symbol_info = self.client.get_symbol_info(symbol)
            lot_size_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')
            step_size = float(lot_size_filter['stepSize'])

            notional_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'NOTIONAL')
            min_notional = float(notional_filter['minNotional'])
            max_notional = float(notional_filter['maxNotional']) if 'maxNotional' in notional_filter else float('inf')
            quantity = math.floor(initial_quantity / step_size) * step_size
            total_value = quantity * price
            if total_value < min_notional:
                quantity = math.ceil(min_notional / price / step_size) * step_size
            elif total_value > max_notional:
                quantity = math.floor(max_notional / price / step_size) * step_size

            return round(quantity, 8)
        except BinanceAPIException as e:
            logging.error(f"Error calculating quantity: {e}")
            return 0.0

    def cancel_open_orders(self, symbol: str) -> None:
        """Cancel all open orders for a given symbol."""
        try:
            open_orders = self.client.get_open_orders(symbol=symbol)
            for order in open_orders:
                self.client.cancel_order(symbol=symbol, orderId=order['orderId'])
            logging.info(f"All open orders for {symbol} have been canceled.")
        except BinanceAPIException as e:
            logging.error(f"Error canceling orders: {e}")

    def close_order_at_profit(self, symbol: str, quantity: float, price: float) -> Optional[Dict[str, Any]]:
        """Close an order at a specified profit price."""
        try:
            order = self.client.order_limit_sell(
                symbol=symbol,
                quantity=quantity,
                price=price
            )
            return order
        except BinanceAPIException as e:
            logging.error(f"Error placing sell order: {e}")
            return None
