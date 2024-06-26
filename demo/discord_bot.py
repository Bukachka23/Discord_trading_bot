import logging
import os

import discord
from aiohttp import web
from discord.ext import commands
from dotenv import load_dotenv

from core_future.future import FutureClient
from core_parsing.future_parsing import parse_future_message
from core_parsing.spot_parsing import parse_spot_message
from core_spot.spot import SpotClient
from variables.constants import EnvVariables, OrderType, TradingConstants

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class MyBot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.future_client = FutureClient()
        self.spot_client = SpotClient()
        self.app = web.Application()
        self.app.router.add_get('/health', self.health_check)
        self.runner = web.AppRunner(self.app)

    async def setup_hook(self):
        await self.start_health_check_server()

    async def start_health_check_server(self):
        await self.runner.setup()
        site = web.TCPSite(self.runner, '0.0.0.0', 8080)
        await site.start()

    async def health_check(self, _):
        return web.json_response({'status': 'ok'})

    async def on_ready(self):
        logging.info(f'{self.user.name} has connected to Discord!')

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return

        if message.content.startswith('$'):
            if 'LONG' in message.content or 'SHORT' in message.content:
                await self.handle_future_message(message)
            else:
                await self.handle_spot_message(message)

        await self.process_commands(message)

    async def handle_future_message(self, message: discord.Message):
        try:
            command, symbol, side, entry_price, stop_loss_price, target_price = parse_future_message(message.content)

            if command == 'CLOSE_ORDER':
                await message.channel.send(f"Closing all open positions for {symbol}")
                self.future_client.close_order_in_profit(symbol)
                await message.channel.send(f"Closed all open positions for {symbol}")

            elif command == 'CHANGE_STOPLOSS':
                await message.channel.send(f"Changing stop loss for {symbol} to {stop_loss_price}")
                self.future_client.change_stop_loss(symbol, stop_loss_price)
                await message.channel.send(f"Changed stop loss for {symbol} to {stop_loss_price}")

            elif command == 'TRADE_SIGNAL':
                await message.channel.send(f"Canceling open futures orders for {symbol}")
                self.future_client.cancel_open_futures_orders(symbol)

                leverage = TradingConstants.LEVERAGE.value
                portfolio_percentage = TradingConstants.RISK_PERCENTAGE.value

                total_balance = self.future_client.get_account_balance()
                logging.info(f"Total balance: {total_balance}")
                logging.info(f"Trade amount: {total_balance * portfolio_percentage}")

                quantity = self.future_client.calculate_quantity(total_balance, entry_price, leverage, symbol)
                logging.info(f"Calculated quantity: {quantity}")
                logging.info(
                    f"Entry price: {entry_price}, Stop loss price: {stop_loss_price}, Target price: {target_price}")

                self.future_client.set_leverage(symbol, leverage)
                self.future_client.place_order(symbol, side, quantity, entry_price, stop_loss_price, target_price)

                await message.channel.send(f"Placed futures order for {symbol}")

        except Exception as e:
            logging.error(f"Error processing future message: {e}")
            await message.channel.send(f"Error processing message: {str(e)}")

    async def handle_spot_message(self, message: discord.Message):
        try:
            parsed_info = parse_spot_message(message.content)

            if parsed_info['symbol']:
                symbol = parsed_info['symbol']
                entry_prices = parsed_info['entries']

                await message.channel.send(f"Canceling open orders for {symbol}")
                self.spot_client.cancel_open_orders(symbol)

                for price in entry_prices:
                    quantity = self.spot_client.calculate_quantity(symbol, price)
                    order = self.spot_client.place_spot_order(symbol, price, quantity, order_type=OrderType.LIMIT)
                    await message.channel.send(f"Placed order: {order}")

                if parsed_info['final_target_price']:
                    final_target_price = parsed_info['final_target_price']
                    quantity_to_sell = self.spot_client.calculate_quantity(symbol, final_target_price)
                    await message.channel.send(f"Calculated quantity to sell: {quantity_to_sell}")
                    await message.channel.send(f"Intention to sell {quantity_to_sell} {symbol} at {final_target_price}")
                    close_order = self.spot_client.close_order_at_profit(symbol, quantity_to_sell, final_target_price)
                    await message.channel.send(f"Placed sell order: {close_order}")

        except Exception as e:
            logging.error(f"Error processing spot message: {e}")
            await message.channel.send(f"Error processing message: {str(e)}")


if __name__ == "__main__":
    load_dotenv()
    token = os.getenv(EnvVariables.DISCORD_BOT_TOKEN.value)
    intents = discord.Intents.default()
    intents.message_content = True
    bot = MyBot(command_prefix='$', intents=intents)
    bot.run(token)
