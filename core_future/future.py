import logging
import os
from decimal import ROUND_DOWN, Decimal
from typing import Any

from binance.client import Client
from dotenv import load_dotenv

from variables.constants import TradingConstants

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class FutureClient:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        self.client = Client(api_key, api_secret)

    def get_account_balance(self) -> float:
        """
        Retrieve the account balance in USDT.
        """
        balance = self.client.futures_account_balance()
        for asset in balance:
            if asset['asset'] == 'USDT':
                return float(asset['balance'])
        return 0.0

    def set_leverage(self, symbol: str, leverage: int) -> None:
        """
        Set the leverage for a given symbol.
        """
        self.client.futures_change_leverage(symbol=symbol, leverage=leverage)

    def get_symbol_info(self, symbol: str) -> dict[str, Any] | None:
        """
        Retrieve symbol information from the exchange.
        """
        info = self.client.futures_exchange_info()
        for item in info['symbols']:
            if item['symbol'] == symbol:
                return item
        return None

    def __get_trimmed_quantity(self, quantity: Decimal, step_size: Decimal) -> Decimal:
        """
        Truncate the quantity to the correct precision based on step size.
        """
        return (quantity // step_size) * step_size

    def __get_trimmed_price(self, price: Decimal, tick_size: Decimal) -> Decimal:
        """
        Truncate the price to the correct precision based on tick size.
        """
        return (price // tick_size) * tick_size

    def calculate_quantity(self, usdt_balance: float, entry_price: float, leverage: int, symbol: str) -> float:
        """
        Calculate the quantity to trade based on balance, entry price, and leverage.
        """
        symbol_info = self.get_symbol_info(symbol)
        if symbol_info:
            lot_size_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'), None)
            if lot_size_filter:
                step_size = Decimal(lot_size_filter['stepSize'])
                max_precision = len(step_size.as_tuple()[1])

                quantity_decimal = Decimal(
                    (usdt_balance * TradingConstants.RISK_PERCENTAGE.value * leverage) / entry_price).quantize(
                    Decimal('.' + '0' * max_precision), rounding=ROUND_DOWN)

                # Ensure the quantity meets the minimum increment requirement
                min_qty = Decimal(lot_size_filter['minQty'])
                adjusted_quantity = max(min_qty, quantity_decimal)
                return float(self.__get_trimmed_quantity(adjusted_quantity, step_size))
        return 0.0

    def place_order(self, symbol: str, side: str,
                    quantity: float, entry_price: float, stop_loss: float, target: float) -> None:
        """
        Place a futures order with stop loss and take profit.
        """
        account_info = self.client.futures_account()
        available_margin = float(account_info['availableBalance'])
        logging.info(f"Available Margin: {available_margin} USDT")
        print(f"Available margin: {available_margin}")

        estimated_cost = quantity * entry_price
        required_margin = estimated_cost / TradingConstants.LEVERAGE.value
        print(f"Required margin: {required_margin}")

        if estimated_cost > available_margin:
            logging.error("Insufficient margin to place order.")
            return

        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            logging.error(f"Symbol info not found for {symbol}")
            return

        price_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'), None)
        if not price_filter:
            logging.error(f"Price filter not found for {symbol}")
            return

        tick_size = Decimal(price_filter['tickSize'])
        stop_loss = self.__get_trimmed_price(Decimal(stop_loss), tick_size)
        target = self.__get_trimmed_price(Decimal(target), tick_size)

        try:
            logging.debug(f"Placing market order: symbol={symbol}, side={side}, quantity={quantity}")
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            logging.info(f"Order placed: {order}")
        except Exception as e:
            logging.error(f"Failed to place order: {e}")
            return

        try:
            logging.debug(
                f"Placing stop loss order: symbol={symbol}, side={'SELL' if side == 'BUY' else 'BUY'}, "
                f"stopPrice={stop_loss}, quantity={quantity}")
            stop_loss_order = self.client.futures_create_order(
                symbol=symbol,
                side='SELL' if side == 'BUY' else 'BUY',
                type='STOP_MARKET',
                stopPrice=str(stop_loss),
                quantity=quantity
            )
            logging.info(f"Stop loss order placed: {stop_loss_order}")
        except Exception as e:
            logging.error(f"Failed to place stop loss order: {e}")

        try:
            logging.debug(
                f"Placing take profit order: symbol={symbol}, side={'SELL' if side == 'BUY' else 'BUY'}, "
                f"price={target}, quantity={quantity}")
            take_profit_order = self.client.futures_create_order(
                symbol=symbol,
                side='SELL' if side == 'BUY' else 'BUY',
                type='LIMIT',
                price=str(target),
                quantity=quantity,
                timeInForce='GTC'
            )
            logging.info(f"Take profit order placed: {take_profit_order}")
        except Exception as e:
            logging.error(f"Failed to place take profit order: {e}")

    def cancel_open_futures_orders(self, symbol: str) -> None:
        """
        Cancel all open futures orders for a given symbol.
        """
        try:
            open_orders = self.client.futures_get_open_orders(symbol=symbol)
            for order in open_orders:
                self.client.futures_cancel_order(symbol=symbol, orderId=order['orderId'])
            logging.info(f"Canceled all open orders for {symbol}")
        except Exception as e:
            logging.error(f"Failed to cancel open orders: {e}")

    def close_order_in_profit(self, symbol):
        """
        Close all open positions for a given symbol.
        """
        try:
            positions = self.client.futures_position_information()
            for position in positions:
                if position['symbol'] == symbol and float(position['positionAmt']) != 0:
                    side = 'SELL' if float(position['positionAmt']) > 0 else 'BUY'
                    quantity = abs(float(position['positionAmt']))
                    self.client.futures_create_order(
                        symbol=symbol,
                        side=side,
                        type='MARKET',
                        quantity=quantity
                    )
            logging.info(f"Closed all positions for {symbol}")
        except Exception as e:
            logging.error(f"Failed to close positions: {e}")

    def change_stop_loss(self, symbol, new_stop_loss):
        """
        Change the stop loss for an open position.
        """
        try:
            positions = self.client.futures_position_information()
            for position in positions:
                if position['symbol'] == symbol and float(position['positionAmt']) != 0:
                    side = 'SELL' if float(position['positionAmt']) > 0 else 'BUY'
                    quantity = abs(float(position['positionAmt']))
                    self.client.futures_create_order(
                        symbol=symbol,
                        side=side,
                        type='STOP_MARKET',
                        stopPrice=new_stop_loss,
                        quantity=quantity
                    )
            logging.info(f"Changed stop loss for {symbol} to {new_stop_loss}")
        except Exception as e:
            logging.error(f"Failed to change stop loss: {e}")
