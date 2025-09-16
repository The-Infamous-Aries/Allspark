import discord
from discord.ext import commands
import pnwkit
import time
from datetime import datetime
import sys
import os
import json
import random
import asyncio

# Add path to import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config import PANDW_API_KEY, ARIES_USER_ID

# Import the recruitment tracker
from .recruitment_tracker import RecruitmentTracker

class RecruitCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.recruit_messages = self.load_recruit_messages()
        
        # Initialize recruitment tracker
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'Data')
        self.tracker = RecruitmentTracker(data_dir)
        self.total_messages = len(self.recruit_messages)

    def load_recruit_messages(self):
        """Load recruitment messages from JSON file"""
        json_path = os.path.join(os.path.dirname(__file__), '..', 'Data', 'recruit.json')
        print(f"Loading recruitment messages from: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            messages = data.get('recruit_messages', [])
            print(f"Successfully loaded {len(messages)} recruitment messages")
            return messages

    def get_unallied_nations(self, limit: int = 15000):
        """
        Fetches up to 15000 unallied nations, filtered through recruitment tracker.
        Shows most recently active nations first, excluding those on cooldown.
        """
        try:
            from datetime import datetime, timezone, timedelta
            import traceback
            
            # Initialize pnwkit with API key
            kit = pnwkit.QueryKit(PANDW_API_KEY)
            
            # Query for nations without alliance (alliance_id: 0)
            all_nations = []
            page_size = 500
            max_pages = 30  # 30 pages × 500 nations/page = 15,000 nations max

            api_errors = []

            try:
                print(f"🔄 Starting PnW API fetch for {limit} unallied nations...")
                
                # Load nations page by page
                for page_num in range(1, max_pages + 1):
                    try:
                        query = kit.query("nations", {
                            "alliance_id": 0,
                            "first": page_size,
                            "page": page_num
                        }, """
                            id
                            nation_name
                            leader_name
                            last_active
                            score
                            alliance_id
                            vacation_mode_turns
                            cities {
                                name
                            }
                        """)
                        
                        result = query.get()
                        
                        if not result or not hasattr(result, 'nations'):
                            break
                            
                        nations = result.nations
                        if not nations:
                            break
                            
                        all_nations.extend(nations)
                        
                        # Continue fetching until we reach the desired limit or run out of pages
                        if len(all_nations) >= limit:
                            break
                            
                    except Exception as page_error:
                        api_errors.append(f"Page {page_num}: {str(page_error)}")
                        continue
                        
            except Exception as e:
                print(f"⚠️ API fetch failed: {str(e)}")
                return []          
            nations = all_nations
            if not nations:
                return []
            
            # Convert to the expected format with filtering
            formatted_nations = []
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
            
            for nation in nations:
                try:
                    # Skip nation ID=1 (game admin)
                    if str(nation.id) == "1":
                        continue
                    
                    # Parse datetime
                    last_active_str = str(nation.last_active)
                    last_active_dt = None
                    
                    try:
                        if last_active_str and last_active_str != "None":
                            last_active_str = last_active_str.replace('Z', '+00:00')
                            last_active_dt = datetime.fromisoformat(last_active_str)
                            
                            # Skip nations inactive for 7+ days
                            if last_active_dt < cutoff_date:
                                continue
                    except:
                        continue
                    
                    # Skip vacation mode
                    try:
                        vacation_mode = str(nation.vacation_mode_turns) and int(str(nation.vacation_mode_turns)) > 0
                        if vacation_mode:
                            continue
                    except:
                        continue
                    
                    # Check if nation is available for recruitment
                    cooldown_info = self.tracker.get_cooldown_info(str(nation.id))
                    if cooldown_info['can_send_any']:
                        formatted_nations.append({
                            "nation_id": str(nation.id),
                            "nation_name": str(nation.nation_name or "Unknown"),
                            "leader_name": str(nation.leader_name or "Unknown Leader"),
                            "last_active": last_active_str,
                            "score": float(nation.score or 0),
                            "cities_count": len(nation.cities) if hasattr(nation, 'cities') else 0,
                            "last_active_dt": last_active_dt
                        })
                        
                        # Continue processing all nations up to the limit
                
                except Exception as e:
                    continue
            
            # Sort by activity (most recent first)
            formatted_nations.sort(
                key=lambda x: x['last_active_dt'] if x['last_active_dt'] is not None else datetime.min.replace(tzinfo=timezone.utc),
                reverse=True
            )
            
            # Ensure we return exactly the requested limit
            return formatted_nations[:limit]
            
        except Exception as e:
            print(f"🚨 Error fetching nations: {e}")
            return []

    async def refresh_nations_async(self):
        """
        Async wrapper for get_unallied_nations to be used by the refresh button.
        """
        # Run the synchronous API call in a thread to avoid blocking
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(None, self.get_unallied_nations)

    def get_random_recruit_message(self, leader_name, nation_id: str) -> tuple:
        """Get a random recruitment message for a leader with Discord and Alliance links"""
        if not self.recruit_messages:
            return None, None, None
            
        messages = self.recruit_messages
        if not messages:
            return None, None, None
            
        # Get available messages for this nation
        available_messages = self.tracker.get_available_messages(nation_id, len(messages))
        
        if not available_messages:
            return None, None, "No messages available due to cooldowns"
            
        # Select a random available message
        message_num = random.choice(available_messages)
        message = messages[message_num - 1]  # Convert to 0-based index
        
        subject = message["title"]
        
        # Add Discord and Alliance links to the message
        discord_link = "https://discord.gg/JSAEGjmUQG"
        alliance_link = "https://politicsandwar.com/alliance/id=9445"
        
        body = message["message"].format(
            leader_name=leader_name,
            discord_link=discord_link,
            alliance_link=alliance_link
        )
        
        # Ensure links are properly formatted for P&W messages
        body = body.replace(
            "https://discord.gg/JSAEGjmUQG",
            "<a href=\"https://discord.gg/JSAEGjmUQG\">Discord Link</a>"
        ).replace(
            "https://politicsandwar.com/alliance/id=9445",
            "<a href=\"https://politicsandwar.com/alliance/id=9445\">Alliance Page</a>"
        )
        
        return subject, body, message_num

    def send_p_and_w_message(self, receiver_id, leader_name, cc_leaders=None):
        """
        Sends a random recruitment message to a specific nation using the REST API.
        Supports Carbon Copy (CC) field for sending duplicate messages to up to 20 additional leaders.
        Includes comprehensive error handling and detailed logging.
        Tracks sent messages to comply with game rules.
        """
        try:
            import requests
            import json
            
            # Check if message can be sent based on tracking (using nation_id as primary identifier)
            cooldown_info = self.tracker.get_cooldown_info(str(receiver_id))
            if not cooldown_info['can_send_any']:
                print(f"⏰ Cannot send to Nation {receiver_id} - still in cooldown until {cooldown_info['next_available_at']}")
                return None
            
            subject, body, message_num = self.get_random_recruit_message(leader_name, str(receiver_id))
            if not subject or not body:
                print(f"⚠️ No recruitment message available for {leader_name}: {message_num}")
                return None
            
            # Validate inputs
            if not receiver_id or not str(receiver_id).isdigit():
                print(f"❌ Invalid receiver ID: {receiver_id}")
                return None
                
            if not leader_name or leader_name.strip() == "":
                print(f"❌ Invalid leader name: {leader_name}")
                return None

            url = "https://politicsandwar.com/api/send-message/"
            
            payload = {
                'key': PANDW_API_KEY,
                'to': receiver_id,
                'subject': subject,
                'message': body
            }
            
            print(f"📤 Sending message to nation {receiver_id} (leader: {leader_name})")
            print(f"📋 Subject: {subject}")
            
            # Enhanced request with better error handling
            response = requests.post(
                url, 
                data=payload, 
                timeout=30,
                headers={
                    'User-Agent': 'Cybertr0n-Recruitment-Bot/1.0',
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )
            
            print(f"📊 Response status: {response.status_code}")
            
            # Handle different HTTP status codes
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"📋 API Response: {json.dumps(result, indent=2)}")
                    
                    if result.get('success'):
                        print(f"✅ Message sent successfully to {leader_name}")
                        
                        # Record the sent message in tracking
                        self.tracker.record_message_sent(str(receiver_id), message_num, leader_name)
                        print(f"📊 Tracked message #{message_num} sent to nation {receiver_id}")
                        
                        return 200
                    else:
                        error_msg = result.get('error', 'Unknown API error')
                        error_code = result.get('error_code', 'unknown')
                        print(f"❌ API Error for {leader_name}: {error_msg} (Code: {error_code})")
                        
                        # Log specific error types for debugging
                        if 'rate limit' in str(error_msg).lower():
                            print(f"⏰ Rate limit hit for nation {receiver_id}")
                        elif 'blocked' in str(error_msg).lower():
                            print(f"🚫 Nation {receiver_id} has blocked messages")
                        elif 'invalid' in str(error_msg).lower():
                            print(f"🔍 Invalid parameters for nation {receiver_id}")
                            
                        return None
                        
                except json.JSONDecodeError as json_error:
                    print(f"❌ JSON parsing error: {json_error}")
                    print(f"📄 Raw response: {response.text[:1000]}...")
                    return None
                    
            elif response.status_code == 429:
                print(f"⏰ Rate limit exceeded (429) for {leader_name}")
                return None
            elif response.status_code == 400:
                print(f"🔍 Bad request (400) for {leader_name}: {response.text[:200]}")
                return None
            elif response.status_code == 401:
                print(f"🔑 Unauthorized (401) - Check API key")
                return None
            elif response.status_code >= 500:
                print(f"🔧 Server error ({response.status_code}) for {leader_name}")
                return None
            else:
                print(f"❌ HTTP Error {response.status_code}: {response.text[:500]}...")
                return None
                
        except requests.exceptions.Timeout:
            print(f"⏰ Timeout sending message to {leader_name}")
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"🔗 Connection failed for {leader_name}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed for {leader_name}: {type(e).__name__}: {e}")
            return None
        except Exception as e:
            error_details = {
                "error": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
            print(f"🚨 Critical error sending to {receiver_id}: {error_details}")
            return None

    @commands.hybrid_command(name='recruit')
    async def recruit(self, ctx: commands.Context):
        """Start the recruitment process with paginated view of 100 unallied nations."""
        try:
            # Check if the user is Aries
            if ctx.author.id != ARIES_USER_ID:
                await ctx.send("❌ This command is restricted to Aries only.", ephemeral=True)
                return

            # Defer the response to prevent timeout
            await ctx.defer()
            
            # Import the view class
            from .recruit_views import PaginatedRecruitmentView
            
            # Fetch up to 15000 nations but only show 100 in paginated view
            all_nations = self.get_unallied_nations(15000)
            
            # Take top 100 most active nations for display
            display_nations = all_nations[:100]
            
            if not display_nations:
                embed = discord.Embed(
                    title="🌍 No Nations Available",
                    description="No unallied nations are currently available for recruitment.",
                    color=0xff6b6b
                )
                embed.add_field(
                    name="Possible Reasons:",
                    value="• All nations are in alliances\n• Nations are inactive (7+ days offline)\n• All nations are in vacation mode\n• Nations on cooldown from previous recruitment\n• API issues with Politics & War",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            # Create paginated view with the 100 nations for display
            view = PaginatedRecruitmentView(display_nations, self, ctx.author.id)
            embed = view.create_embed()
            
            # Add summary of total nations processed
            embed.description = f"Showing {len(display_nations)} of {len(all_nations)} total available nations"
            
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            
        except Exception as e:
            print(f"❌ Error in recruit command: {e}")
            embed = discord.Embed(
                title="❌ Recruitment Error",
                description=f"An error occurred while fetching nations: {str(e)}",
                color=0xff6b6b
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name='recruitment_stats')
    async def recruitment_stats(self, ctx):
        """Show recruitment statistics and cooldown information."""
        try:
            stats = self.tracker.get_recruitment_stats()
            
            embed = discord.Embed(
                title="Recruitment Statistics",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📊 Message Statistics",
                value=f"**Total Messages Sent:** {stats['total_sent']}\n"
                      f"**Unique Nations Contacted:** {stats['unique_nations']}\n"
                      f"**Nations on Cooldown:** {stats['nations_on_cooldown']}",
                inline=False
            )
            
            embed.add_field(
                name="⏰ Cooldown Status",
                value=f"**Next Available:** {stats['next_available']}\n"
                      f"**Oldest Cooldown:** {stats['oldest_cooldown']}",
                inline=False
            )
            
            # Recent activity
            if stats['recent_activity']:
                recent_text = []
                for nation_id, data in list(stats['recent_activity'].items())[:5]:
                    recent_text.append(
                        f"{data['leader_name']} (#{nation_id}) - "
                        f"Msg #{data['message_num']} ({data['time_ago']})"
                    )
                
                embed.add_field(
                    name="📝 Recent Activity",
                    value="\n".join(recent_text) if recent_text else "No recent activity",
                    inline=False
                )
            
            embed.set_footer(text=f"Tracking file: {stats['tracking_file']}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"Error loading recruitment statistics: {str(e)}")
            print(f"Error in recruitment_stats: {e}")

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