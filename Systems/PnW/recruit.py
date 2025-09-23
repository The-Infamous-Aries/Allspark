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
from config import PANDW_API_KEY, ARIES_USER_ID

# Import the recruitment tracker
from .recruitment_tracker import RecruitmentTracker

class RecruitmentTask:
    """Class to track individual recruitment tasks"""
    def __init__(self, task_id: str, nations: List[Dict], user_id: int):
        self.task_id = task_id
        self.nations = nations
        self.user_id = user_id
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.completed = 0
        self.total = len(nations)
        self.success_count = 0
        self.results = []
        self.status = "running"  # running, completed, cancelled, error
        self.task_handle: Optional[asyncio.Task] = None

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
        
        # Background task management
        self.active_tasks: Dict[str, RecruitmentTask] = {}
        self.task_counter = 0

    async def load_recruit_messages(self):
        """Load recruitment messages using centralized data manager"""
        if not self._messages_loaded:
            try:
                data = await self.bot.user_data_manager.load_json_data('recruit')
                if data:
                    self.recruit_messages = data.get('recruit_messages', [])
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

    async def get_unallied_nations(self, limit: int = 15000):
        """
        Fetches up to 15000 unallied nations, filtered through recruitment tracker.
        Shows most recently active nations first, excluding those on cooldown.
        """
        # Check if pnwkit is available
        if not PNWKIT_AVAILABLE:
            print("⚠️ pnwkit not available - cannot fetch nations from PnW API")
            return []
            
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
                        # Try querying without alliance_id filter first to see if we get any results
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
                            cities {
                                name
                            }
                        """)
                        
                        result = query.get()
                        
                        print(f"🔍 DEBUG: Page {page_num} - Raw result type: {type(result)}")
                        if hasattr(result, '__dict__'):
                            print(f"🔍 DEBUG: Page {page_num} - Result attributes: {list(result.__dict__.keys())}")
                        
                        if not result or not hasattr(result, 'nations'):
                            print(f"🔍 DEBUG: Page {page_num} - No result or no nations attribute")
                            break
                            
                        nations = result.nations
                        print(f"🔍 DEBUG: Page {page_num} - Nations count: {len(nations) if nations else 0}")
                        if not nations:
                            print(f"🔍 DEBUG: Page {page_num} - No nations in result, breaking")
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
            print(f"🔍 DEBUG: Fetched {len(nations)} total nations from API")
            if not nations:
                print("🔍 DEBUG: No nations returned from API")
                return []

            # Convert to the expected format with filtering
            formatted_nations = []
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
            print(f"🔍 DEBUG: Cutoff date for activity: {cutoff_date}")
            
            # Debug counters
            total_processed = 0
            skipped_admin = 0
            skipped_alliance = 0
            skipped_inactive = 0
            skipped_vacation = 0
            processing_errors = 0
            
            for nation in nations:
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
                    
                    # Parse datetime
                    last_active_str = str(nation.last_active)
                    last_active_dt = None
                    
                    try:
                        if last_active_str and last_active_str != "None":
                            last_active_str = last_active_str.replace('Z', '+00:00')
                            last_active_dt = datetime.fromisoformat(last_active_str)
                            
                            # Skip nations inactive for 7+ days
                            if last_active_dt < cutoff_date:
                                skipped_inactive += 1
                                continue
                    except:
                        skipped_inactive += 1
                        continue
                    
                    # Skip vacation mode
                    try:
                        vacation_mode = str(nation.vacation_mode_turns) and int(str(nation.vacation_mode_turns)) > 0
                        if vacation_mode:
                            skipped_vacation += 1
                            continue
                    except:
                        skipped_vacation += 1
                        continue
                    
                    # Add nation to list (cooldown will be checked when actually sending messages)
                    formatted_nations.append({
                        "nation_id": str(nation.id),
                        "nation_name": str(nation.nation_name or "Unknown"),
                        "leader_name": str(nation.leader_name or "Unknown Leader"),
                        "last_active": last_active_str,
                        "score": float(nation.score or 0),
                        "cities_count": len(nation.cities) if hasattr(nation, 'cities') else 0,
                        "last_active_dt": last_active_dt
                    })
                
                except Exception as e:
                    processing_errors += 1
                    continue
            
            # Check recruitment history size
            recruitment_history = await self.tracker._load_history()
            
            # Debug summary
            print(f"🔍 DEBUG: Filtering Summary:")
            print(f"  Total processed: {total_processed}")
            print(f"  Skipped admin: {skipped_admin}")
            print(f"  Skipped alliance: {skipped_alliance}")
            print(f"  Skipped inactive: {skipped_inactive}")
            print(f"  Skipped vacation: {skipped_vacation}")
            print(f"  Processing errors: {processing_errors}")
            print(f"  Final available: {len(formatted_nations)}")
            print(f"  Nations in recruitment history: {len(recruitment_history)}")
            print(f"  Note: Cooldown filtering will be applied when sending messages")

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
        # Call the async function directly since get_unallied_nations is already async
        return await self.get_unallied_nations()

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
                return None
            
            subject, body, message_num = await self.get_random_recruit_message(leader_name, str(receiver_id))
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

    async def start_background_recruitment(self, nations: List[Dict], user_id: int) -> str:
        """Start a background recruitment task and return the task ID"""
        task_id = self.generate_task_id()
        recruitment_task = RecruitmentTask(task_id, nations, user_id)
        
        # Create and start the background task
        recruitment_task.task_handle = asyncio.create_task(
            self._background_recruitment_worker(recruitment_task)
        )
        
        # Store the task
        self.active_tasks[task_id] = recruitment_task
        
        return task_id

    async def _background_recruitment_worker(self, recruitment_task: RecruitmentTask):
        """Worker function that handles the actual recruitment process in the background"""
        try:
            print(f"🚀 Starting background recruitment task {recruitment_task.task_id} for {len(recruitment_task.nations)} nations")
            
            for i, nation in enumerate(recruitment_task.nations, 1):
                # Check if task was cancelled
                if recruitment_task.status == "cancelled":
                    print(f"⏹️ Task {recruitment_task.task_id} was cancelled at nation {i}/{len(recruitment_task.nations)}")
                    break
                
                try:
                    # Add randomized 2-3 second delay between requests to prevent API spam and rate limiting
                    delay = random.uniform(2.0, 3.0)
                    await asyncio.sleep(delay)
                    
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
                    
                    recruitment_task.results.append(result)
                    recruitment_task.completed += 1
                    
                    if success:
                        recruitment_task.success_count += 1
                        print(f"✅ [{recruitment_task.task_id}] {i}/{len(recruitment_task.nations)} - Success: {nation['nation_name']}")
                    else:
                        print(f"❌ [{recruitment_task.task_id}] {i}/{len(recruitment_task.nations)} - Failed: {nation['nation_name']} - {message}")
                        
                    # Log progress every 10 nations or at milestones
                    if i % 10 == 0 or i in [1, 5, len(recruitment_task.nations)]:
                        progress = (recruitment_task.completed / recruitment_task.total * 100)
                        success_rate = (recruitment_task.success_count / recruitment_task.completed * 100) if recruitment_task.completed > 0 else 0
                        print(f"📊 [{recruitment_task.task_id}] Progress: {recruitment_task.completed}/{recruitment_task.total} ({progress:.1f}%) - Success Rate: {success_rate:.1f}%")
                        
                except asyncio.TimeoutError:
                    result = {
                        'nation_name': nation['nation_name'],
                        'nation_id': nation['nation_id'],
                        'success': False,
                        'message': 'Request timeout - Politics & War API is slow',
                        'timestamp': datetime.now()
                    }
                    recruitment_task.results.append(result)
                    recruitment_task.completed += 1
                    print(f"⏰ [{recruitment_task.task_id}] {i}/{len(recruitment_task.nations)} - Timeout: {nation['nation_name']}")
                    
                except Exception as e:
                    result = {
                        'nation_name': nation['nation_name'],
                        'nation_id': nation['nation_id'],
                        'success': False,
                        'message': str(e),
                        'timestamp': datetime.now()
                    }
                    recruitment_task.results.append(result)
                    recruitment_task.completed += 1
                    print(f"🚨 [{recruitment_task.task_id}] {i}/{len(recruitment_task.nations)} - Error: {nation['nation_name']} - {str(e)}")
            
            # Mark task as completed
            recruitment_task.status = "completed"
            recruitment_task.end_time = datetime.now()
            
            # Final summary
            duration = (recruitment_task.end_time - recruitment_task.start_time).total_seconds()
            success_rate = (recruitment_task.success_count / recruitment_task.completed * 100) if recruitment_task.completed > 0 else 0
            print(f"🏁 Task {recruitment_task.task_id} completed!")
            print(f"   📊 Final Stats: {recruitment_task.success_count}/{recruitment_task.completed} successful ({success_rate:.1f}%)")
            print(f"   ⏱️ Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
            
        except asyncio.CancelledError:
            print(f"⏹️ Task {recruitment_task.task_id} was cancelled")
            recruitment_task.status = "cancelled"
            recruitment_task.end_time = datetime.now()
            raise
        except Exception as e:
            print(f"❌ Critical error in background recruitment worker {recruitment_task.task_id}: {e}")
            recruitment_task.status = "error"
            recruitment_task.end_time = datetime.now()
        
        # Schedule cleanup task for 1 hour later (non-blocking)
        asyncio.create_task(self._schedule_cleanup(recruitment_task.task_id, 3600))

    async def _schedule_cleanup(self, task_id: str, delay_seconds: int):
        """Schedule cleanup of a completed task after a delay (non-blocking)"""
        try:
            await asyncio.sleep(delay_seconds)
            if task_id in self.active_tasks:
                print(f"🧹 Cleaning up completed task {task_id}")
                del self.active_tasks[task_id]
        except asyncio.CancelledError:
            # Cleanup was cancelled, which is fine
            pass
        except Exception as e:
            print(f"❌ Error during task cleanup for {task_id}: {e}")

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get the status of a recruitment task"""
        if task_id not in self.active_tasks:
            return None
        
        task = self.active_tasks[task_id]
        
        # Calculate duration and estimates
        current_time = datetime.now()
        duration = (current_time - task.start_time).total_seconds()
        
        # Estimate completion time if still running
        estimated_completion = None
        if task.status == "running" and task.completed > 0:
            avg_time_per_nation = duration / task.completed
            remaining_nations = task.total - task.completed
            estimated_seconds_remaining = remaining_nations * avg_time_per_nation
            estimated_completion = current_time.timestamp() + estimated_seconds_remaining
        
        # Calculate success rate
        success_rate = (task.success_count / task.completed * 100) if task.completed > 0 else 0
        
        return {
            'task_id': task_id,
            'status': task.status,
            'completed': task.completed,
            'total': task.total,
            'success_count': task.success_count,
            'success_rate': success_rate,
            'start_time': task.start_time,
            'end_time': task.end_time,
            'duration_seconds': duration,
            'duration_formatted': f"{int(duration // 60)}m {int(duration % 60)}s",
            'progress_percentage': (task.completed / task.total * 100) if task.total > 0 else 0,
            'estimated_completion': estimated_completion,
            'nations_per_minute': (task.completed / (duration / 60)) if duration > 0 else 0,
            'results': task.results[-5:]  # Return last 5 results for preview
        }

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a recruitment task"""
        if task_id not in self.active_tasks:
            return False
        
        task = self.active_tasks[task_id]
        task.status = "cancelled"
        
        if task.task_handle and not task.task_handle.done():
            task.task_handle.cancel()
        
        return True

    @commands.hybrid_command(name='recruit_status')
    async def recruit_status(self, ctx: commands.Context, task_id: str = None):
        """Check the status of recruitment tasks"""
        if ctx.author.id != ARIES_USER_ID:
            await ctx.send("❌ This command is restricted to Aries only.", ephemeral=True)
            return
        
        if task_id:
            # Get specific task status
            status = self.get_task_status(task_id)
            if not status:
                await ctx.send(f"❌ Task `{task_id}` not found.", ephemeral=True)
                return
            
            # Choose color based on status
            color_map = {
                'running': 0xff9800,
                'completed': 0x4CAF50,
                'cancelled': 0xff6600,
                'error': 0xff0000
            }
            color = color_map.get(status['status'], 0x808080)
            
            # Create progress bar
            progress_pct = status['progress_percentage']
            progress_bar_length = 20
            filled_length = int(progress_bar_length * progress_pct / 100)
            progress_bar = "█" * filled_length + "░" * (progress_bar_length - filled_length)
            
            embed = discord.Embed(
                title=f"📊 Recruitment Task Status",
                description=f"**Task ID:** `{status['task_id']}`\n**Status:** {status['status'].title()}",
                color=color
            )
            
            # Progress section
            embed.add_field(
                name="📈 Progress",
                value=f"`{progress_bar}` {progress_pct:.1f}%\n{status['completed']}/{status['total']} nations",
                inline=False
            )
            
            # Performance metrics
            embed.add_field(
                name="✅ Success Rate",
                value=f"{status['success_rate']:.1f}% ({status['success_count']}/{status['completed']})",
                inline=True
            )
            embed.add_field(
                name="⚡ Speed",
                value=f"{status['nations_per_minute']:.1f} nations/min",
                inline=True
            )
            embed.add_field(
                name="⏱️ Duration",
                value=status['duration_formatted'],
                inline=True
            )
            
            # Time information
            embed.add_field(
                name="🕐 Started",
                value=f"<t:{int(status['start_time'].timestamp())}:R>",
                inline=True
            )
            
            if status['estimated_completion'] and status['status'] == 'running':
                embed.add_field(
                    name="🏁 Est. Completion",
                    value=f"<t:{int(status['estimated_completion'])}:R>",
                    inline=True
                )
            elif status['end_time']:
                embed.add_field(
                    name="🏁 Completed",
                    value=f"<t:{int(status['end_time'].timestamp())}:R>",
                    inline=True
                )
            else:
                embed.add_field(name="\u200b", value="\u200b", inline=True)  # Empty field for alignment
            
            # Recent results
            if status['results']:
                recent_results = []
                for result in status['results']:
                    status_emoji = "✅" if result['success'] else "❌"
                    recent_results.append(f"{status_emoji} {result['nation_name']}")
                
                embed.add_field(
                    name="📝 Recent Results",
                    value="\n".join(recent_results),
                    inline=False
                )
            
            embed.set_footer(text="Use /recruit_cancel <task_id> to stop a running task")
            await ctx.send(embed=embed)
        else:
            # List all active tasks
            if not self.active_tasks:
                embed = discord.Embed(
                    title="📭 No Active Tasks",
                    description="No recruitment tasks are currently running.",
                    color=0x808080
                )
                await ctx.send(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📋 Active Recruitment Tasks",
                description=f"Currently tracking {len(self.active_tasks)} task(s)",
                color=0x4CAF50
            )
            
            for task_id, task in self.active_tasks.items():
                progress = (task.completed / task.total * 100) if task.total > 0 else 0
                status_emoji = {
                    'running': '🔄',
                    'completed': '✅',
                    'cancelled': '⏹️',
                    'error': '❌'
                }.get(task.status, '❓')
                
                duration = (datetime.now() - task.start_time).total_seconds()
                duration_str = f"{int(duration // 60)}m {int(duration % 60)}s"
                
                embed.add_field(
                    name=f"{status_emoji} Task {task_id}",
                    value=f"**Status:** {task.status.title()}\n**Progress:** {task.completed}/{task.total} ({progress:.1f}%)\n**Duration:** {duration_str}",
                    inline=True
                )
            
            embed.set_footer(text="Use /recruit_status <task_id> for detailed information")
            await ctx.send(embed=embed)

    @commands.hybrid_command(name='recruit_cancel')
    async def recruit_cancel(self, ctx: commands.Context, task_id: str):
        """Cancel a recruitment task"""
        if ctx.author.id != ARIES_USER_ID:
            await ctx.send("❌ This command is restricted to Aries only.", ephemeral=True)
            return
        
        if self.cancel_task(task_id):
            await ctx.send(f"✅ Task `{task_id}` has been cancelled.", ephemeral=True)
        else:
            await ctx.send(f"❌ Task `{task_id}` not found or already completed.", ephemeral=True)

    @commands.hybrid_command(name='pnwkit_status')
    async def pnwkit_status(self, ctx: commands.Context):
        """Check the status of pnwkit installation (debug command)."""
        try:
            # Check if the user is Aries
            if ctx.author.id != ARIES_USER_ID:
                await ctx.send("❌ This command is restricted to Aries only.", ephemeral=True)
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
            
            await ctx.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await ctx.send(f"❌ Error checking pnwkit status: {str(e)}", ephemeral=True)

    @commands.hybrid_command(name='recruit')
    async def recruit(self, ctx: commands.Context):
        """Start the recruitment process with paginated view of all filtered unallied nations."""
        try:
            # Check if the user is Aries
            if ctx.author.id != ARIES_USER_ID:
                await ctx.send("❌ This command is restricted to Aries only.", ephemeral=True)
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
                await ctx.send(embed=embed, ephemeral=True)
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
                    value="• All nations are in alliances\n• Nations are inactive (7+ days offline)\n• All nations are in vacation mode\n• Nations on cooldown from previous recruitment\n• API issues with Politics & War",
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

def setup_recruit_commands(bot):
    """Legacy setup for recruit commands"""
    if not hasattr(bot, 'talk_system_loaded'):
        bot.loop.create_task(setup(bot))
        bot.talk_system_loaded = True
        print("✅ PnW recruit commands loaded")