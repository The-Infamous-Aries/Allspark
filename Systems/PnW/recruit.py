import discord
from discord.ext import commands
import pnwkit
import time
from datetime import datetime
import sys
import os
import json
import random

# Add path to import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config import PANDW_API_KEY, ARIES_USER_ID

class RecruitCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.recruit_messages = self.load_recruit_messages()

    def load_recruit_messages(self):
        """Load recruitment messages from JSON file"""
        try:
            json_path = os.path.join(os.path.dirname(__file__), 'recruit.json')
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load recruit messages: {e}")
            # Fallback to original message if JSON fails
            return [{
                "subject": "🦾⚡ TRANSMISSION FROM CYBERTR0N ⚡🦾",
                "body": """"The machine never sleeps. Neither shall your potential."

Greetings, {leader_name}.

This is Cybertr0n, a rising power in the Politics & War multiverse — and we are transmitting across time and space to recruit those brave enough to join a new order.

Are you tired of endless red tape, idle leadership, and alliances that stifle rather than support?
We offer freedom, guidance, and the tools to forge your own destiny in the game of nations.

🚀 Why Cybertr0n?
🧠 Expert Strategy & Advice: From war tactics to economic dominance, our Expert Leadership will help you grow fast and efficiently.

🛰️ Freedom to Rule: Want to build a MEGA-Farm or Raid for your Riches? - EVERYTHING is possible on Cybertr0n.

🛠️ Allegiance = Assistance: Prove your dedication, and you’ll receive prioritized aid, protection, and direct support from our core command.

We're more than an alliance.
We're a network of evolving intelligence, pushing each other beyond the limits of the old world.
Cybertr0n is awakening. Will you awaken with us?

📩 To Apply:

Click "Apply" on our Alliance Page here - https://politicsandwar.com/alliance/id=9445

Then our Member Discord Server Here - https://discord.gg/JSAEGjmUQG

Cybertr0n — Upload Your Mind. Upgrade Your Nation.

📡 [TRANSMISSION END]"""
            }]

    def get_unallied_nations(self):
        """
        Fetches a list of nations without an alliance using pnwkit-py.
        """
        try:
            # Initialize pnwkit with API key
            kit = pnwkit.QueryKit(PANDW_API_KEY)
            
            # Query for nations without alliance (alliance_id: 0)
            query = kit.query("nations", {
                "alliance_id": 0,
                "first": 500
            }, """
                id
                nation_name
                leader_name
                last_active
                score
                alliance_id
                cities {
                    name
                }
            """)
            
            result = query.get()
            nations = result.nations
            
            # Convert to the expected format
            formatted_nations = []
            for nation in nations:
                formatted_nations.append({
                    "nation_id": str(nation.id),
                    "nation_name": nation.nation_name,
                    "leader_name": nation.leader_name,
                    "last_active": str(nation.last_active),
                    "score": float(nation.score),
                    "alliance_id": int(nation.alliance_id),
                    "cities_count": len(nation.cities)
                })
            
            return formatted_nations
            
        except Exception as e:
            print(f"PnW API request failed: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_random_recruit_message(self, leader_name):
        """Get a random recruitment message for a leader"""
        if not self.recruit_messages:
            return None, None
            
        message = random.choice(self.recruit_messages)
        subject = message["subject"]
        body = message["body"].format(leader_name=leader_name)
        return subject, body

    def send_p_and_w_message(self, receiver_id, leader_name):
        """
        Sends a random recruitment message to a specific nation using the REST API.
        """
        try:
            import requests
            
            subject, body = self.get_random_recruit_message(leader_name)
            if not subject or not body:
                return None
            
            # Use the REST API endpoint for sending messages
            url = "https://politicsandwar.com/api/send-message/"
            
            payload = {
                'key': PANDW_API_KEY,
                'to': receiver_id,
                'subject': subject,
                'message': body
            }
            
            response = requests.post(url, data=payload)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return 200
                else:
                    print(f"API Error: {result.get('error', 'Unknown error')}")
                    return None
            else:
                print(f"HTTP Error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Failed to send message to {receiver_id}: {e}")
            return None

    @commands.hybrid_command(name="recruit", description="Shows unallied nations for recruitment.")
    async def recruit(self, ctx: commands.Context):
        # Check if the user is Aries
        if ctx.author.id != ARIES_USER_ID:
            await ctx.send("❌ This command is restricted to Aries only.", ephemeral=True)
            return
            
        async with ctx.typing():
            nations = self.get_unallied_nations()
            
            if not nations:
                await ctx.send("No unallied nations found.")
                return

            # Sort by last active time (most recent first)
            nations.sort(key=lambda x: x['last_active'], reverse=True)
            
            view = RecruitPaginatorView(nations, self)
            embed = view.create_nation_embed(0, nations)
            
            await ctx.send(embed=embed, view=view)

class RecruitPaginatorView(discord.ui.View):
    def __init__(self, nations, cog):
        super().__init__(timeout=None)  # No timeout - view stays open indefinitely
        self.nations = nations
        self.cog = cog
        self.current_page = 0
        self.nations_per_page = 5
        self.update_buttons()

    def create_nation_embed(self, page, nations):
        embed = discord.Embed(
            title="🦾⚡ Unallied Nations for Recruitment ⚡🦾",
            description=f"Displaying nations on page **{page + 1}** of **{(len(nations) - 1) // self.nations_per_page + 1}**.",
            color=discord.Color.blue()
        )
        
        start_index = page * self.nations_per_page
        end_index = start_index + self.nations_per_page
        current_page_nations = nations[start_index:end_index]
        
        for i, nation in enumerate(current_page_nations, start=1):
            nation_id = nation['nation_id']
            nation_name = nation['nation_name']
            leader_name = nation['leader_name']
            last_active_str = nation['last_active']
            
            # Parse ISO datetime string for sorting and display
            try:
                last_active_dt = datetime.fromisoformat(last_active_str.replace('Z', '+00:00'))
                now = datetime.now().replace(tzinfo=last_active_dt.tzinfo)
                delta = now - last_active_dt
                
                days = delta.days
                hours, remainder = divmod(delta.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                # Calculate total hours for sorting
                total_hours = days * 24 + hours
                
                if days > 0:
                    last_active_display = f"🟢 Last active: {days}d {hours}h ago"
                elif hours > 0:
                    last_active_display = f"🟢 Last active: {hours}h {minutes}m ago"
                elif minutes > 0:
                    last_active_display = f"🟢 Last active: {minutes}m ago"
                else:
                    last_active_display = "🟢 Online now"
                    
            except Exception:
                last_active_display = "⚪ Last active: Unknown"
                total_hours = 9999
            
            # Include score and city count for better context
            score = nation.get('score', 0)
            cities = nation.get('cities_count', 0)
            
            # Create the field name with rank and nation info
            field_name = f"**#{start_index + i}. {nation_name} (#{nation_id})**"
            
            # Create the field value with all details and proper link
            details = (
                f"👑 **Leader:** {leader_name}\n"
                f"🏆 **Score:** {score:,.0f} | 🏙️ **Cities:** {cities}\n"
                f"🔗 **Nation:** [{nation_name}](https://politicsandwar.com/nation/id={nation_id})\n"
                f"{last_active_display}"
            )
            
            embed.add_field(
                name=field_name,
                value=details,
                inline=False
            )
        
        # Add footer with sorting info
        embed.set_footer(text="Sorted by most recently active first • Use buttons to navigate pages")
        return embed
    
    def update_buttons(self):
        total_pages = (len(self.nations) - 1) // self.nations_per_page
        self.children[0].disabled = self.current_page == 0
        self.children[1].disabled = self.current_page == total_pages

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, custom_id="previous_page")
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if the user is Aries
        if interaction.user.id != ARIES_USER_ID:
            await interaction.response.send_message("❌ This interaction is restricted to Aries only.", ephemeral=True)
            return
            
        self.current_page -= 1
        self.update_buttons()
        embed = self.create_nation_embed(self.current_page, self.nations)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, custom_id="next_page")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if the user is Aries
        if interaction.user.id != ARIES_USER_ID:
            await interaction.response.send_message("❌ This interaction is restricted to Aries only.", ephemeral=True)
            return
            
        self.current_page += 1
        self.update_buttons()
        embed = self.create_nation_embed(self.current_page, self.nations)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Recruit All Shown", style=discord.ButtonStyle.success, custom_id="send_page")
    async def send_page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if the user is Aries
        if interaction.user.id != ARIES_USER_ID:
            await interaction.response.send_message("❌ This interaction is restricted to Aries only.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        
        start_index = self.current_page * self.nations_per_page
        end_index = start_index + self.nations_per_page
        nations_to_message = self.nations[start_index:end_index]
        
        success_count = 0
        failed_count = 0
        
        for nation in nations_to_message:
            status = self.cog.send_p_and_w_message(nation['nation_id'], nation['leader_name'])
            if status == 200:
                success_count += 1
            else:
                failed_count += 1
            time.sleep(2) # To avoid rate limits
            
        await interaction.followup.send(f"Sent messages: {success_count} | Failed: {failed_count}", ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="close_view")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if the user is Aries
        if interaction.user.id != ARIES_USER_ID:
            await interaction.response.send_message("❌ This interaction is restricted to Aries only.", ephemeral=True)
            return
            
        await interaction.response.defer()
        await interaction.delete_original_response()

async def setup(bot):
    """Setup function for the talk system cog"""
    await bot.add_cog(RecruitCog(bot))
    print("Recruit System loaded successfully!")

def setup_recruit_commands(bot):
    """Legacy setup for recruit commands"""
    if not hasattr(bot, 'talk_system_loaded'):
        bot.loop.create_task(setup(bot))
        bot.talk_system_loaded = True
        print("✅ PnW recruit commands loaded")