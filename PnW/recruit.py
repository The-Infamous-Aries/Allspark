import discord
from discord.ext import commands
import time
from datetime import datetime
import sys
import os
import random
import asyncio
import aiohttp
import traceback
import json
from typing import Dict, List, Optional, Tuple

# Try to import pnwkit, handle gracefully if not available
try:
    import pnwkit
    PNWKIT_AVAILABLE = True
    PNWKIT_ERROR = None
    PNWKIT_SOURCE = "system"
except ImportError as e:
    # Try to use local pnwkit if system version is not available
    try:
        import sys
        import os
        local_packages_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'local_packages')
        if local_packages_dir not in sys.path:
            sys.path.insert(0, local_packages_dir)
        
        import pnwkit
        PNWKIT_AVAILABLE = True
        PNWKIT_ERROR = None
        PNWKIT_SOURCE = "local"
    except ImportError as local_e:
        pnwkit = None
        PNWKIT_AVAILABLE = False
        PNWKIT_ERROR = f"System: {str(e)}, Local: {str(local_e)}"
        PNWKIT_SOURCE = "none"
    except Exception as local_e:
        pnwkit = None
        PNWKIT_AVAILABLE = False
        PNWKIT_ERROR = f"System: {str(e)}, Local unexpected error: {str(local_e)}"
        PNWKIT_SOURCE = "none"
except Exception as e:
    pnwkit = None
    PNWKIT_AVAILABLE = False
    PNWKIT_ERROR = f"Unexpected error: {str(e)}"
    PNWKIT_SOURCE = "none"

# Add the parent directory to the path to import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config import (
    PANDW_API_KEY,
    ARIES_USER_ID,
    PRIMAL_USER_ID,
    CARNAGE_USER_ID,
    BENEVOLENT_USER_ID,
    TECH_USER_ID,
    get_role_ids,
)

# Import the recruitment tracker
from .recruitment_tracker import RecruitmentTracker

class RecruitCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = PANDW_API_KEY
        
        # Initialize pnwkit only if available
        if PNWKIT_AVAILABLE:
            self.kit = pnwkit.QueryKit(self.api_key)
        else:
            self.kit = None
            
        self.recruit_messages = []  # Initialize as empty, will be loaded async
        self._messages_loaded = False
        
        # Initialize recruitment tracker with user_data_manager
        self.tracker = RecruitmentTracker(bot.user_data_manager)
        self.total_messages = 0  # Will be set after loading messages
        
    async def load_recruit_messages(self):
        """Load recruitment messages using centralized data manager"""
        if not self._messages_loaded:
            try:
                data = await self.bot.user_data_manager.load_json_data('recruit')
                if data:
                    self.recruit_messages = data.get('messages', [])
                    self.total_messages = len(self.recruit_messages)
                    print(f"Successfully loaded {len(self.recruit_messages)} recruitment messages")
                else:
                    print("No recruitment messages data found")
                    self.recruit_messages = []
                    self.total_messages = 0
                self._messages_loaded = True
            except Exception as e:
                print(f"Error loading recruitment messages: {e}")
                self.recruit_messages = []
                self.total_messages = 0
                self._messages_loaded = True
        return self.recruit_messages

    async def get_all_filtered_nations(self):
        """
        Fetches ALL nations from PnW API and filters out:
        - Nations in alliances (alliance_id != 0)
        - Nations in vacation mode (vacation_mode_turns > 0)
        - Admin nation (ID = 1)
        Returns them sorted by most recent activity first.
        """
        # Check if pnwkit is available
        if not PNWKIT_AVAILABLE:
            print("⚠️ pnwkit not available - cannot fetch nations from PnW API")
            return []
            
        try:
            from datetime import datetime, timezone, timedelta
            
            # Initialize pnwkit with API key
            kit = pnwkit.QueryKit(PANDW_API_KEY)
            
            # Query for ALL nations - no limit
            all_nations = []
            page_size = 500
            page_num = 1
            
            print(f"🔄 Starting PnW API fetch for ALL nations...")
            
            # Load nations page by page until we get all of them
            while True:
                try:
                    query = kit.query("nations", {
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
                        num_cities
                    """)
                    
                    result = query.get()
                    
                    if not result or not hasattr(result, 'nations'):
                        print(f"🔍 DEBUG: Page {page_num} - No result or no nations attribute")
                        break
                        
                    nations = result.nations
                    nations_count = len(nations) if nations else 0
                    print(f"🔍 DEBUG: Page {page_num} - Nations count: {nations_count}")
                    
                    if not nations or nations_count == 0:
                        print(f"🔍 DEBUG: Page {page_num} - No nations in result, breaking")
                        break
                        
                    all_nations.extend(nations)
                    page_num += 1
                    
                    # Add a small delay to avoid overwhelming the API
                    await asyncio.sleep(0.1)
                        
                except Exception as page_error:
                    print(f"❌ Error on page {page_num}: {str(page_error)}")
                    break
                        
            print(f"🔍 DEBUG: Fetched {len(all_nations)} total nations from API")
            
            if not all_nations:
                print("🔍 DEBUG: No nations returned from API")
                return []

            # Filter nations
            filtered_nations = []
            print(f"🔍 DEBUG: Processing nations without activity cutoff")
            
            # Debug counters
            total_processed = 0
            skipped_admin = 0
            skipped_alliance = 0
            skipped_vacation = 0
            processing_errors = 0
            
            for nation in all_nations:
                try:
                    total_processed += 1
                    
                    # Skip nation ID=1 (game admin)
                    if str(nation.id) == "1":
                        skipped_admin += 1
                        continue
                    
                    # Skip nations that are in alliances (only want unallied nations)
                    if hasattr(nation, 'alliance_id') and nation.alliance_id and str(nation.alliance_id) != "0":
                        skipped_alliance += 1
                        continue
                    
                    # Skip vacation mode
                    try:
                        vacation_mode = hasattr(nation, 'vacation_mode_turns') and nation.vacation_mode_turns and int(str(nation.vacation_mode_turns)) > 0
                        if vacation_mode:
                            skipped_vacation += 1
                            continue
                    except:
                        # If we can't determine vacation mode, skip to be safe
                        skipped_vacation += 1
                        continue
                    
                    # Parse last active datetime and filter by 14-day cutoff
                    last_active_str = str(nation.last_active) if hasattr(nation, 'last_active') else None
                    last_active_dt = None
                    
                    try:
                        if last_active_str and last_active_str != "None":
                            # Handle timezone format
                            if last_active_str.endswith('Z'):
                                last_active_str = last_active_str.replace('Z', '+00:00')
                            elif '+' not in last_active_str and last_active_str.count(':') >= 2:
                                last_active_str += '+00:00'
                                
                            last_active_dt = datetime.fromisoformat(last_active_str)
                    except Exception as date_error:
                        # If we can't parse the date, just continue without it
                        pass
                    
                    # Apply 14-day cutoff - skip nations inactive for 14+ days
                    if last_active_dt:
                        now = datetime.now(timezone.utc)
                        cutoff_date = now - timedelta(days=14)
                        if last_active_dt < cutoff_date:
                            continue
                    
                    # Add nation to filtered list
                    filtered_nations.append({
                        "nation_id": str(nation.id),
                        "nation_name": str(nation.nation_name or "Unknown"),
                        "leader_name": str(nation.leader_name or "Unknown Leader"),
                        "last_active": last_active_str,
                        "score": float(nation.score or 0),
                        "cities_count": int(nation.num_cities or 0) if hasattr(nation, 'num_cities') else 0,
                        "last_active_dt": last_active_dt
                    })
                
                except Exception as e:
                    processing_errors += 1
                    continue
            
            # Debug summary
            print(f"🔍 DEBUG: Filtering Summary:")
            print(f"  Total processed: {total_processed}")
            print(f"  Skipped admin: {skipped_admin}")
            print(f"  Skipped alliance: {skipped_alliance}")
            print(f"  Skipped vacation mode: {skipped_vacation}")
            print(f"  Processing errors: {processing_errors}")
            print(f"  Final filtered nations: {len(filtered_nations)}")

            # Sort by activity (most recent first)
            filtered_nations.sort(
                key=lambda x: x['last_active_dt'] if x['last_active_dt'] is not None else datetime.min.replace(tzinfo=timezone.utc),
                reverse=True
            )

            return filtered_nations
            
        except Exception as e:
            print(f"🚨 Error fetching nations: {e}")
            traceback.print_exc()
            return []

    async def get_unallied_nations(self, limit: int = 15000):
        """
        Legacy method - now calls get_all_filtered_nations and applies limit.
        Maintained for backward compatibility.
        """
        all_nations = await self.get_all_filtered_nations()
        return all_nations[:limit]



    async def get_random_recruit_message(self, leader_name, nation_id: str) -> tuple:
        """Get a random recruitment message for a leader with Discord and Alliance links"""
        # Ensure messages are loaded
        await self.load_recruit_messages()
        
        if not self.recruit_messages:
            return None, None, None
            
        messages = self.recruit_messages
        if not messages:
            return None, None, None
            
        # Get available messages for this nation
        available_messages = await self.tracker.get_available_messages(nation_id, len(messages))
        
        if not available_messages:
            return None, None, "No messages available due to cooldowns"
            
        # Select a random available message
        message_num = random.choice(available_messages)
        message = messages[message_num - 1]  # Convert to 0-based index
        
        subject = message["title"]
        
        # Format the message with leader name
        body = message["message"].format(leader_name=leader_name)
        
        # Add Discord and Alliance links to the message after a line break
        discord_link = "<a href=\"https://discord.gg/JSAEGjmUQG\">Discord Link</a>"
        alliance_link = "<a href=\"https://politicsandwar.com/alliance/id=9445\">Alliance Page</a>"
        
        # Append the links to the message body with line breaks
        body += f"\n\n{discord_link}\n{alliance_link}"
        
        return subject, body, message_num

    async def send_p_and_w_message(self, receiver_id, leader_name, cc_leaders=None):
        """
        Sends a random recruitment message to a specific nation using the REST API.
        Supports Carbon Copy (CC) field for sending duplicate messages to up to 20 additional leaders.
        Includes comprehensive error handling and detailed logging.
        Tracks sent messages to comply with game rules.
        Uses aiohttp for non-blocking HTTP requests to prevent Discord heartbeat timeouts.
        """
        try:
            # Check if message can be sent based on tracking (using nation_id as primary identifier)
            cooldown_info = await self.tracker.get_cooldown_info(str(receiver_id))
            if not cooldown_info['can_send_any']:
                print(f"⏰ Cannot send to Nation {receiver_id} - still in cooldown until {cooldown_info['next_available_at']}")
                return False, f"Nation in cooldown until {cooldown_info['next_available_at']}"
            
            subject, body, message_num = await self.get_random_recruit_message(leader_name, str(receiver_id))
            if not subject or not body:
                print(f"⚠️ No recruitment message available for {leader_name}: {message_num}")
                return False, f"No recruitment message available: {message_num}"
            
            # Validate inputs
            if not receiver_id or not str(receiver_id).isdigit():
                print(f"❌ Invalid receiver ID: {receiver_id}")
                return False, f"Invalid receiver ID: {receiver_id}"
                
            if not leader_name or leader_name.strip() == "":
                print(f"❌ Invalid leader name: {leader_name}")
                return False, f"Invalid leader name: {leader_name}"

            # Validate API key
            if not PANDW_API_KEY or PANDW_API_KEY.strip() == "":
                print(f"❌ PANDW_API_KEY is not configured or empty")
                return False, "API key not configured"
            
            url = "https://politicsandwar.com/api/send-message/"
            
            payload = {
                'key': PANDW_API_KEY,
                'to': receiver_id,
                'subject': subject,
                'message': body
            }
            
            print(f"📤 Sending message to nation {receiver_id} (leader: {leader_name})")
            print(f"📋 Subject: {subject}")
            print(f"🔑 API Key configured: {'Yes' if PANDW_API_KEY else 'No'}")
            
            # Use aiohttp for non-blocking HTTP requests
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    url, 
                    data=payload, 
                    headers={
                        'User-Agent': 'Cybertr0n-Recruitment-Bot/1.0',
                        'Accept': 'application/json',
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                ) as response:
                    
                    print(f"📊 Response status: {response.status}")
                    
                    # Handle different HTTP status codes
                    if response.status == 200:
                        try:
                            result = await response.json()
                            print(f"📋 API Response: {json.dumps(result, indent=2)}")
                            
                            if result.get('success'):
                                print(f"✅ Message sent successfully to {leader_name}")
                                
                                # Record the sent message in tracking
                                await self.tracker.record_message_sent(str(receiver_id), message_num, leader_name)
                                print(f"📊 Tracked message #{message_num} sent to nation {receiver_id}")
                                
                                return True, "Message sent successfully"
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
                                    
                                return False, f"API Error: {error_msg} (Code: {error_code})"
                                
                        except json.JSONDecodeError as json_error:
                            text = await response.text()
                            print(f"❌ JSON parsing error: {json_error}")
                            print(f"📄 Raw response: {text[:1000]}...")
                            return False, "JSON parsing error"
                            
                    elif response.status == 429:
                        print(f"⏰ Rate limit exceeded (429) for {leader_name}")
                        return False, "Rate limit exceeded"
                    elif response.status == 400:
                        text = await response.text()
                        print(f"🔍 Bad request (400) for {leader_name}: {text[:200]}")
                        return False, "Bad request"
                    elif response.status == 401:
                        print(f"🔑 Unauthorized (401) - Check API key")
                        return False, "Unauthorized - Check API key"
                    elif response.status >= 500:
                        print(f"🔧 Server error ({response.status}) for {leader_name}")
                        return False, f"Server error ({response.status})"
                    else:
                        text = await response.text()
                        print(f"❌ HTTP Error {response.status}: {text[:500]}...")
                        return False, f"HTTP Error {response.status}"
                        
        except asyncio.TimeoutError:
             print(f"⏰ Timeout sending message to {leader_name}")
             return False, "Request timeout"
        except aiohttp.ClientConnectionError as e:
             print(f"🔗 Connection failed for {leader_name}: {e}")
             return False, "Connection failed"
        except aiohttp.ClientError as e:
             print(f"❌ Request failed for {leader_name}: {type(e).__name__}: {e}")
             return False, f"Request failed: {type(e).__name__}"
        except Exception as e:
             error_details = {
                 "error": str(e),
                 "type": type(e).__name__,
                 "traceback": traceback.format_exc()
             }
             print(f"🚨 Critical error sending to {receiver_id}: {error_details}")
             return False, f"Critical error: {str(e)}"

    def generate_task_id(self) -> str:
        """Generate a unique task ID"""
        self.task_counter += 1
        return f"recruit_{self.task_counter}_{int(time.time())}"

    async def send_recruitment_messages(self, nations: List[Dict], user_id: int = None, edit_function=None) -> Dict:
        """Send recruitment messages to a list of nations synchronously with progress updates"""
        results = {
            'total': len(nations),
            'completed': 0,
            'success_count': 0,
            'total_tried': 0,
            'total_sent': 0,
            'total_failed': 0,
            'results': [],
            'start_time': datetime.now()
        }
        
        try:
            print(f"🚀 Starting recruitment for {len(nations)} nations")
            
            # Ensure recruitment messages are loaded
            await self.load_recruit_messages()
            if not self.recruit_messages:
                print("❌ No recruitment messages available - cannot send messages")
                return {
                    **results,
                    'end_time': datetime.now(),
                    'duration': 0,
                    'error': 'No recruitment messages available'
                }
            
            print(f"✅ Loaded {len(self.recruit_messages)} recruitment messages")
            
            # Enable batch mode for recruitment tracker to optimize saves
            await self.tracker.start_batch_mode()
            print(f"📊 Batch mode enabled for recruitment tracking optimization")
            
            for i, nation in enumerate(nations, 1):
                try:
                    # Add consistent 2-second delay between requests to prevent API overload
                    if i > 1:  # Don't delay before the first message
                        print(f"⏱️ Waiting 2 seconds before sending to {nation['nation_name']}...")
                        await asyncio.sleep(2.0)
                    
                    print(f"📤 Attempting to send message to {nation['nation_name']} ({i}/{len(nations)})")
                    
                    success, message = await self.send_p_and_w_message(
                        nation['nation_id'],
                        nation['leader_name']
                    )
                    
                    result = {
                        'nation_name': nation['nation_name'],
                        'nation_id': nation['nation_id'],
                        'success': success,
                        'message': message,
                        'timestamp': datetime.now()
                    }
                    
                    results['results'].append(result)
                    results['completed'] += 1
                    results['total_tried'] += 1
                    
                    if success:
                        results['success_count'] += 1
                        results['total_sent'] += 1
                        print(f"✅ {i}/{len(nations)} - SUCCESS: Message sent to {nation['nation_name']}")
                    else:
                        results['total_failed'] += 1
                        print(f"❌ {i}/{len(nations)} - FAILED: {nation['nation_name']} - {message}")
                    
                    # Update progress via edit function if provided
                    if edit_function and i % 5 == 0:  # Update every 5 nations to avoid rate limits
                        progress_embed = discord.Embed(
                            title="🔄 Recruitment in Progress...",
                            description=f"**Progress:** {results['completed']}/{results['total']} nations processed",
                            color=0xff9800
                        )
                        progress_embed.add_field(
                            name="📊 Current Stats", 
                            value=f"📤 Attempted: {results['total_tried']}\n✅ Sent: {results['total_sent']}\n❌ Failed: {results['total_failed']}", 
                            inline=True
                        )
                        progress_embed.add_field(
                            name="🎯 Last Processed", 
                            value=f"{nation['nation_name']}", 
                            inline=True
                        )
                        try:
                            await edit_function(embed=progress_embed)
                        except Exception as e:
                            print(f"⚠️ Failed to update progress: {e}")
                        
                except Exception as e:
                    print(f"❌ Error processing nation {nation['nation_name']}: {e}")
                    results['completed'] += 1
                    results['results'].append({
                        'nation_name': nation['nation_name'],
                        'nation_id': nation['nation_id'],
                        'success': False,
                        'message': f"Processing error: {str(e)}",
                        'timestamp': datetime.now()
                    })
            
            # End batch mode and get the number of deferred saves
            deferred_saves = await self.tracker.end_batch_mode()
            
            # Calculate final statistics
            results['end_time'] = datetime.now()
            duration = (results['end_time'] - results['start_time']).total_seconds()
            success_rate = (results['total_sent'] / results['total_tried'] * 100) if results['total_tried'] > 0 else 0
            
            print(f"✅ Recruitment completed successfully!")
            print(f"📊 Final Stats: {results['total_sent']}/{results['total_tried']} messages sent ({success_rate:.1f}% success rate)")
            print(f"📤 Attempted: {results['total_tried']} | ✅ Sent: {results['total_sent']} | ❌ Failed: {results['total_failed']}")
            print(f"⏱️ Duration: {duration/60:.1f} minutes")
            print(f"💾 Optimized: {deferred_saves} saves batched for performance")
            
            results['duration'] = duration
            results['success_rate'] = success_rate
            results['deferred_saves'] = deferred_saves
            
            return results
            
        except Exception as e:
            print(f"❌ Critical error in recruitment: {e}")
            # Ensure batch mode is ended even if there's an error
            try:
                deferred_saves = await self.tracker.end_batch_mode()
                print(f"💾 Batch mode ended due to error - {deferred_saves} saves were flushed")
            except Exception as batch_error:
                print(f"⚠️ Error ending batch mode during error handling: {batch_error}")
            raise

    async def _schedule_cleanup(self, delay_seconds: int):
        """Schedule cleanup after recruitment completion (non-blocking)"""
        try:
            await asyncio.sleep(delay_seconds)
            
            # Clear recruitment-related caches to free up memory
            try:
                cleared_entries = await self.user_data_manager.clear_recruitment_cache()
                print(f"💾 Post-recruitment cache cleanup: {cleared_entries} entries cleared")
            except Exception as cache_error:
                print(f"⚠️ Error during cache cleanup: {cache_error}")
                
        except asyncio.CancelledError:
            # Cleanup was cancelled, which is fine
            pass
        except Exception as e:
            print(f"❌ Error during cache cleanup: {e}")

    @commands.hybrid_command(name='pnwkit_status')
    async def pnwkit_status(self, ctx: commands.Context):
        """Check the status of pnwkit installation (debug command)."""
        try:
            # Check if the user is Aries
            if ctx.author.id != ARIES_USER_ID:
                await ctx.send("❌ This command is restricted to Aries only.")
                return

            embed = discord.Embed(
                title="🔍 PnW Kit Status",
                color=0x00ff00 if PNWKIT_AVAILABLE else 0xff6b6b
            )
            
            embed.add_field(
                name="Available:",
                value="✅ Yes" if PNWKIT_AVAILABLE else "❌ No",
                inline=True
            )
            
            if PNWKIT_AVAILABLE:
                embed.add_field(
                    name="Source:",
                    value=f"📦 {PNWKIT_SOURCE.title()}",
                    inline=True
                )
            
            if PNWKIT_AVAILABLE:
                try:
                    version = pnwkit.__version__
                    embed.add_field(
                        name="Version:",
                        value=f"`{version}`",
                        inline=True
                    )
                except:
                    embed.add_field(
                        name="Version:",
                        value="Unknown",
                        inline=True
                    )
            
            if PNWKIT_ERROR:
                embed.add_field(
                    name="Import Error:",
                    value=f"```{PNWKIT_ERROR}```",
                    inline=False
                )
            
            # Test basic functionality if available
            if PNWKIT_AVAILABLE:
                try:
                    # Try to create a basic client instance
                    test_client = pnwkit.QueryKit()
                    embed.add_field(
                        name="Basic Test:",
                        value="✅ QueryKit creation successful",
                        inline=False
                    )
                except Exception as e:
                    embed.add_field(
                        name="Basic Test:",
                        value=f"❌ Error: {str(e)}",
                        inline=False
                    )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error checking pnwkit status: {str(e)}")

    @commands.hybrid_command(name='recruit')
    async def recruit(self, ctx: commands.Context):
        """Start the recruitment process with paginated view of all filtered unallied nations."""
        try:
            # Access control aligned with MA Command Center
            authorized_users = [PRIMAL_USER_ID, ARIES_USER_ID, CARNAGE_USER_ID, BENEVOLENT_USER_ID, TECH_USER_ID]
            is_authorized = ctx.author.id in authorized_users

            if not is_authorized and ctx.guild:
                role_ids = get_role_ids(ctx.guild.id)
                leadership_roles = ['Predaking', 'IA', 'MG', 'HG']
                author_roles = [role.id for role in ctx.author.roles]

                for role_name in leadership_roles:
                    role_ids_for_role = role_ids.get(role_name, [])
                    if role_ids_for_role and any(role_id in author_roles for role_id in role_ids_for_role):
                        is_authorized = True
                        break

            if not is_authorized:
                embed = discord.Embed(
                    title="❌ Access Denied",
                    description="Only Alliance Leadership can run recruitment.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return

            # Check if pnwkit is available
            if not PNWKIT_AVAILABLE:
                embed = discord.Embed(
                    title="❌ PnW Kit Not Available",
                    description="The `pnwkit` module is not installed. PnW recruitment features are disabled.",
                    color=0xff6b6b
                )
                embed.add_field(
                    name="To fix this:",
                    value="Install pnwkit with: `pip install pnwkit>=2.6.0`",
                    inline=False
                )
                if PNWKIT_ERROR:
                    embed.add_field(
                        name="Error Details:",
                        value=f"```{PNWKIT_ERROR}```",
                        inline=False
                    )
                await ctx.send(embed=embed)
                return

            # Defer the response to prevent timeout
            await ctx.defer()
            
            # Import the view class
            from .recruit_views import PaginatedRecruitmentView
            
            # Fetch all available nations (up to 15000) and show all filtered results
            all_nations = await self.get_unallied_nations(15000)
            
            if not all_nations:
                embed = discord.Embed(
                    title="🌍 No Nations Available",
                    description="No unallied nations are currently available for recruitment.",
                    color=0xff6b6b
                )
                embed.add_field(
                    name="Possible Reasons:",
                    value="• All nations are in alliances\n• All nations are in vacation mode\n• Nations on cooldown from previous recruitment\n• API issues with Politics & War",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            # Create paginated view with ALL filtered nations for display
            view = PaginatedRecruitmentView(all_nations, self, ctx.author.id)
            embed = view.create_embed()
            
            # Add summary showing all available nations
            embed.description = f"Showing all {len(all_nations)} available nations ready for recruitment"
            
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

    async def start_recruit_from_interaction(self, interaction: discord.Interaction):
        """Start the recruitment process from an interaction (e.g., MA dropdown)."""
        try:
            # If not already deferred by caller, defer here
            try:
                if not interaction.response.is_done():
                    await interaction.response.defer()
            except Exception:
                pass

            # Optional: Access control aligned with MA Command Center
            authorized_users = [PRIMAL_USER_ID, ARIES_USER_ID, CARNAGE_USER_ID, BENEVOLENT_USER_ID, TECH_USER_ID]
            is_authorized = interaction.user.id in authorized_users

            if not is_authorized and interaction.guild:
                role_ids = get_role_ids(interaction.guild.id)
                leadership_roles = ['Predaking', 'IA', 'MG', 'HG']
                author_roles = [role.id for role in interaction.user.roles]

                for role_name in leadership_roles:
                    role_ids_for_role = role_ids.get(role_name, [])
                    if role_ids_for_role and any(role_id in author_roles for role_id in role_ids_for_role):
                        is_authorized = True
                        break

            if not is_authorized:
                embed = discord.Embed(
                    title="❌ Access Denied",
                    description="Only Alliance Leadership can run recruitment.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # Check if pnwkit is available
            if not PNWKIT_AVAILABLE:
                embed = discord.Embed(
                    title="❌ PnW Kit Not Available",
                    description="The `pnwkit` module is not installed. PnW recruitment features are disabled.",
                    color=0xff6b6b
                )
                embed.add_field(
                    name="To fix this:",
                    value="Install pnwkit with: `pip install pnwkit>=2.6.0`",
                    inline=False
                )
                if PNWKIT_ERROR:
                    embed.add_field(
                        name="Error Details:",
                        value=f"```{PNWKIT_ERROR}```",
                        inline=False
                    )
                await interaction.followup.send(embed=embed)
                return

            # Import the view class
            from .recruit_views import PaginatedRecruitmentView

            # Fetch all available nations (up to 15000) and show all filtered results
            all_nations = await self.get_unallied_nations(15000)

            if not all_nations:
                embed = discord.Embed(
                    title="🌍 No Nations Available",
                    description="No unallied nations are currently available for recruitment.",
                    color=0xff6b6b
                )
                embed.add_field(
                    name="Possible Reasons:",
                    value="• All nations are in alliances\n• All nations are in vacation mode\n• Nations on cooldown from previous recruitment\n• API issues with Politics & War",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return

            # Create paginated view with ALL filtered nations for display
            view = PaginatedRecruitmentView(all_nations, self, interaction.user.id)
            embed = view.create_embed()

            # Add summary showing all available nations
            embed.description = f"Showing all {len(all_nations)} available nations ready for recruitment"

            message = await interaction.followup.send(embed=embed, view=view)
            view.message = message

        except Exception as e:
            print(f"❌ Error in start_recruit_from_interaction: {e}")
            embed = discord.Embed(
                title="❌ Recruitment Error",
                description=f"An error occurred while fetching nations: {str(e)}",
                color=0xff6b6b
            )
            try:
                await interaction.followup.send(embed=embed)
            except Exception:
                pass

    @commands.hybrid_command(name='recruitment_stats')
    async def recruitment_stats(self, ctx):
        """Show recruitment statistics and cooldown information."""
        try:
            stats = await self.tracker.get_recruitment_stats()
            
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
            
            embed.set_footer(text="Recruitment tracking via centralized data manager")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"Error loading recruitment statistics: {str(e)}")
            print(f"Error in recruitment_stats: {e}")

async def setup(bot):
    """Setup function for the talk system cog"""
    await bot.add_cog(RecruitCog(bot))
    print("Recruit System loaded successfully!")
