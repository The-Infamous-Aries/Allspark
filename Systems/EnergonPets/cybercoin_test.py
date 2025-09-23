"""
Standalone test file for CyberCoin market refresh functionality.
This file can be deleted after testing the market update system.
"""

import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import sys
import os

# Import the necessary classes and functions from energon_system
try:
    # When loaded as a module through allspark.py
    from .energon_system import (
        MarketManager, 
        MarketConfig, 
        HolidayData, 
        EventData,
        create_market_embed,
        get_current_holiday,
        get_holiday_events,
        select_weighted_event
    )
except ImportError:
    # When loaded directly or for testing
    from energon_system import (
        MarketManager, 
        MarketConfig, 
        HolidayData, 
        EventData,
        create_market_embed,
        get_current_holiday,
        get_holiday_events,
        select_weighted_event
    )

class CyberCoinTest(commands.Cog):
    """Test cog for CyberCoin market refresh functionality."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.hybrid_command(
        name="cybercoin_refresh", 
        description="Manually trigger the next CyberCoin market round (price update + events)"
    )
    @app_commands.describe(
        force_event="Force a random market event (optional)",
        force_holiday="Force holiday effects (optional)"
    )
    async def cybercoin_refresh(
        self, 
        ctx: commands.Context,
        force_event: bool = False,
        force_holiday: bool = False
    ):
        """Manually trigger the next market round with price updates and events."""
        
        await ctx.defer()
        
        try:
            market_manager = MarketManager()
            data = market_manager.market_data
            old_price = data['current_price']
            
            # Track what happened in this round
            events_triggered = []
            price_change_info = ""
            
            # Check for active events
            if data['active_event'] and data['event_updates_remaining'] > 0:
                data['event_updates_remaining'] -= 1
                
                # Apply event multiplier to price
                multiplier = data['active_event']['multiplier']
                base_change = random.uniform(-0.05, 0.05)  # Base volatility
                total_change = base_change * multiplier
                
                new_price = max(MarketConfig.MIN_PRICE, 
                               min(MarketConfig.MAX_PRICE, 
                                   data['current_price'] * (1 + total_change)))
                
                data['current_price'] = new_price
                data['price_history'].append(new_price)
                
                if len(data['price_history']) > 50:
                    data['price_history'] = data['price_history'][-50:]
                
                events_triggered.append(f"📊 Active Event: {data['active_event']['message']}")
                
                # Event has ended
                if data['event_updates_remaining'] <= 0:
                    market_manager.add_market_event(f"⚡ Event ended: {data['active_event']['message']}")
                    data['active_event'] = None
                    events_triggered.append("✅ Event concluded")
                    
            else:
                # Normal price movement
                base_change = random.uniform(-0.03, 0.03)
                
                # Holiday effects (forced or natural)
                holiday = get_current_holiday()
                if force_holiday or (holiday and random.random() < MarketConfig.HOLIDAY_EVENT_CHANCE):
                    if holiday:
                        holiday_multiplier = random.uniform(*holiday['multiplier_range'])
                        base_change *= holiday_multiplier
                        
                        holiday_event = random.choice(get_holiday_events(holiday))
                        market_manager.add_market_event(holiday_event)
                        events_triggered.append(f"🎉 Holiday Event: {holiday_event}")
                
                new_price = max(MarketConfig.MIN_PRICE, 
                               min(MarketConfig.MAX_PRICE, 
                                   data['current_price'] * (1 + base_change)))
                
                data['current_price'] = new_price
                data['price_history'].append(new_price)
                
                if len(data['price_history']) > 50:
                    data['price_history'] = data['price_history'][-50:]
                
                # Random events (forced or natural)
                if force_event or random.random() < MarketConfig.EVENT_CHANCE:
                    event_type, event_data = select_weighted_event()
                    event_message = random.choice(event_data["events"])
                    multiplier = random.uniform(*event_data["multiplier_range"])
                    
                    data['active_event'] = {
                        'type': event_type,
                        'message': event_message,
                        'multiplier': multiplier
                    }
                    data['event_updates_remaining'] = event_data["duration"]
                    
                    market_manager.add_market_event(f"⚡ New Event: {event_message}")
                    events_triggered.append(f"🎯 New Event: {event_message}")
            
            # Calculate price change
            price_change = new_price - old_price
            price_change_percent = (price_change / old_price) * 100
            
            if price_change > 0:
                price_change_info = f"📈 Price increased by {price_change:.2f} ({price_change_percent:+.1f}%)"
            elif price_change < 0:
                price_change_info = f"📉 Price decreased by {abs(price_change):.2f} ({price_change_percent:+.1f}%)"
            else:
                price_change_info = f"➡️ Price unchanged at {new_price:.2f}"
            
            # Update market trend
            market_manager.update_market_trend()
            
            # Save the updated market data
            market_manager.save_market_data()
            
            # Create response embed
            embed = discord.Embed(
                title="🚀 CyberCoin Market Round Complete!",
                description=f"Market round triggered successfully",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="💰 Price Update",
                value=f"**Old Price:** {old_price:.2f} Energon\n"
                      f"**New Price:** {new_price:.2f} Energon\n"
                      f"**{price_change_info}**",
                inline=False
            )
            
            embed.add_field(
                name="📊 Market Trend",
                value=f"**Current Trend:** {data['market_trend'].title()}",
                inline=True
            )
            
            if events_triggered:
                embed.add_field(
                    name="🎯 Events Triggered",
                    value="\n".join(events_triggered),
                    inline=False
                )
            
            if data['market_events']:
                recent_events = data['market_events'][-3:]
                embed.add_field(
                    name="📜 Recent Market Events",
                    value="\n".join(recent_events),
                    inline=False
                )
            
            embed.set_footer(text="Use /cybercoin_market to view the updated market dashboard")
            
            await ctx.send(embed=embed)
            
            # Optionally update any existing market dashboard messages
            try:
                from config import CHANNEL_IDS
                market_channel_id = CHANNEL_IDS.get('cybercoin_market')
                
                if market_channel_id:
                    channel = self.bot.get_channel(market_channel_id)
                    if channel:
                        # Find the latest market dashboard message
                        async for message in channel.history(limit=10):
                            if (message.author == self.bot.user and 
                                message.embeds and 
                                "🚀 CyberCoin Market Dashboard" in message.embeds[0].title):
                                new_embed = create_market_embed()
                                await message.edit(embed=new_embed)
                                break
            except Exception as e:
                print(f"Could not update market dashboard: {e}")
                
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Market Refresh Failed",
                description=f"An error occurred while refreshing the market: {str(e)}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await ctx.send(embed=error_embed)
            print(f"Error in cybercoin_refresh: {e}")
            import traceback
            traceback.print_exc()

    @commands.hybrid_command(
        name="cybercoin_test_info", 
        description="Get information about the current market state for testing"
    )
    async def cybercoin_test_info(self, ctx: commands.Context):
        """Display current market information for testing purposes."""
        
        try:
            market_manager = MarketManager()
            data = market_manager.market_data
            
            embed = discord.Embed(
                title="🔍 CyberCoin Market Test Info",
                description="Current market state for testing",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="💰 Current Market Data",
                value=f"**Price:** {data['current_price']:.2f} Energon\n"
                      f"**Trend:** {data['market_trend'].title()}\n"
                      f"**Volume 24h:** {data['total_volume_24h']:.2f}\n"
                      f"**Buy Pressure:** {data['buy_pressure']}\n"
                      f"**Sell Pressure:** {data['sell_pressure']}",
                inline=True
            )
            
            if data['active_event']:
                embed.add_field(
                    name="🎯 Active Event",
                    value=f"**Message:** {data['active_event']['message']}\n"
                          f"**Multiplier:** {data['active_event']['multiplier']:.2f}\n"
                          f"**Updates Remaining:** {data['event_updates_remaining']}",
                    inline=False
                )
            else:
                embed.add_field(
                    name="🎯 Active Event",
                    value="No active events",
                    inline=True
                )
            
            # Check for holidays
            holiday = get_current_holiday()
            if holiday:
                embed.add_field(
                    name="🎉 Holiday Status",
                    value=f"**{holiday['message_prefix']} {holiday['name']}** - Special market conditions active!",
                    inline=False
                )
            
            embed.add_field(
                name="📊 Price History",
                value=f"**History Length:** {len(data['price_history'])} prices\n"
                      f"**Price Range:** {min(data['price_history']):.2f} - {max(data['price_history']):.2f}",
                inline=True
            )
            
            embed.set_footer(text="Use /cybercoin_refresh to trigger the next market round")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Test Info Failed",
                description=f"Could not retrieve market info: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)

async def setup(bot: commands.Bot) -> None:
    """Add the test cog to the bot."""
    await bot.add_cog(CyberCoinTest(bot))
    print("CyberCoin test commands loaded successfully!")

# For standalone testing (if run directly)
if __name__ == "__main__":
    print("CyberCoin test module loaded. This file should be imported as a Discord cog.")
    print("Available commands:")
    print("- /cybercoin_refresh [force_event] [force_holiday]")
    print("- /cybercoin_test_info")