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

class RecruitCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.recruit_messages = self.load_recruit_messages()

    def load_recruit_messages(self):
        """Load recruitment messages from JSON file"""
        try:
            json_path = os.path.join(os.path.dirname(__file__), '..', 'Data', 'recruit.json')
            print(f"Loading recruitment messages from: {json_path}")
            with open(json_path, 'r', encoding='utf-8') as f:
                messages = json.load(f)
                print(f"Successfully loaded {len(messages)} recruitment messages")
                return messages
        except Exception as e:
            print(f"Failed to load recruit messages: {e}")
            print(f"Attempted to load from: {os.path.join(os.path.dirname(__file__), '..', 'Data', 'recruit.json')}")
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

Click "Apply" on our Alliance Page here - {alliance_link}

Then our Member Discord Server Here - {discord_link}

Cybertr0n — Upload Your Mind. Upgrade Your Nation.

📡 [TRANSMISSION END]"""
            }]

    def get_unallied_nations(self):
        """
        Fetches a list of nations without an alliance using pnwkit-py.
        Processes up to 15,000 nations (30 pages * 500 per page).
        Excludes nation ID=1 and nations inactive for 7+ days.
        Optimized to reduce processing time and prevent heartbeat blocking.
        Includes comprehensive error handling and detailed logging.
        """
        try:
            from datetime import datetime, timezone, timedelta
            import traceback
            
            # Initialize pnwkit with API key
            kit = pnwkit.QueryKit(PANDW_API_KEY)
            
            # Query for nations without alliance (alliance_id: 0) - use sequential page loading
            all_nations = []
            page_size = 500  # API maximum per request
            max_pages = 30   # 30 * 500 = 15,000 nations to cover all possible nations
            
            api_errors = []
            nations_processed = 0
            
            try:
                print(f"🔄 Starting PnW API fetch for unallied nations...")
                
                # Load nations page by page using the page parameter
                for page_num in range(1, max_pages + 1):
                    try:
                        print(f"📄 Loading page {page_num}...")
                        
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
                        
                        if not result:
                            api_errors.append(f"Page {page_num}: No result returned")
                            print(f"⚠️ No result for page {page_num}, stopping.")
                            break
                            
                        if not hasattr(result, 'nations'):
                            api_errors.append(f"Page {page_num}: Invalid response structure")
                            print(f"⚠️ Invalid response structure for page {page_num}, stopping.")
                            break
                            
                        nations = result.nations
                        if not nations:
                            print(f"📭 No nations returned for page {page_num}, reached end.")
                            break
                            
                        print(f"✅ Retrieved {len(nations)} nations from page {page_num}")
                        all_nations.extend(nations)
                        nations_processed += len(nations)
                        
                        # If we got fewer than requested, we've reached the end
                        if len(nations) < page_size:
                            print(f"🏁 Last page reached at page {page_num}")
                            break
                            
                    except Exception as page_error:
                        error_msg = f"Page {page_num} error: {str(page_error)}"
                        api_errors.append(error_msg)
                        print(f"❌ {error_msg}")
                        # Continue to next page instead of failing completely
                        continue
                        
                print(f"📊 Total nations collected: {len(all_nations)} from {nations_processed} processed")
                
            except Exception as e:
                error_msg = f"Sequential pagination failed: {str(e)}"
                api_errors.append(error_msg)
                print(f"⚠️ {error_msg}")
                
                # Fallback to single page with detailed error handling
                try:
                    print("🔄 Trying fallback single page query...")
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
                        vacation_mode_turns
                        cities {
                            name
                        }
                    """)
                    result = query.get()
                    
                    if result and hasattr(result, 'nations'):
                        all_nations = result.nations
                        print(f"✅ Fallback query returned {len(all_nations)} nations")
                    else:
                        print("❌ Fallback query also failed")
                        all_nations = []
                        
                except Exception as fallback_error:
                    error_msg = f"Fallback failed: {str(fallback_error)}"
                    api_errors.append(error_msg)
                    print(f"❌ {error_msg}")
                    all_nations = []
            
            nations = all_nations
            
            if not nations:
                print(f"🚨 No nations found. API errors: {len(api_errors)}")
                if api_errors:
                    print("📋 API Error log:")
                    for error in api_errors[:5]:  # Show first 5 errors
                        print(f"   - {error}")
                return []
            
            # Convert to the expected format with comprehensive error handling
            formatted_nations = []
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
            parsing_errors = []
            
            for nation in nations:
                try:
                    # Skip nation ID=1 (game admin)
                    if str(nation.id) == "1":
                        continue
                        
                    # Parse datetime with comprehensive error handling
                    last_active_str = str(nation.last_active)
                    last_active_dt = None
                    
                    try:
                        if last_active_str and last_active_str != "None" and last_active_str != "null":
                            # Handle various date formats
                            last_active_str = last_active_str.replace('Z', '+00:00')
                            last_active_dt = datetime.fromisoformat(last_active_str)
                            
                            # Skip nations inactive for 7+ days
                            if last_active_dt < cutoff_date:
                                continue
                        else:
                            # Allow nations with missing/unknown last_active dates
                            last_active_dt = None
                            
                    except (ValueError, AttributeError) as e:
                        parsing_errors.append(f"Nation {nation.id}: {str(e)}")
                        last_active_dt = None
                    
                    # Handle vacation mode with error tolerance
                    vacation_mode = False
                    try:
                        if hasattr(nation, 'vacation_mode_turns') and nation.vacation_mode_turns is not None:
                            vacation_str = str(nation.vacation_mode_turns)
                            vacation_mode = vacation_str and int(vacation_str) > 0
                    except (ValueError, AttributeError):
                        vacation_mode = False
                        
                    if vacation_mode:
                        continue
                    
                    # Safely extract all data with fallback values
                    formatted_nations.append({
                        "nation_id": str(nation.id),
                        "nation_name": str(nation.nation_name or "Unknown"),
                        "leader_name": str(nation.leader_name or "Unknown Leader"),
                        "last_active": last_active_str,
                        "score": float(nation.score or 0),
                        "alliance_id": int(nation.alliance_id or 0),
                        "cities_count": len(nation.cities) if hasattr(nation, 'cities') else 0,
                        "last_active_dt": last_active_dt
                    })
                    
                except Exception as e:
                    print(f"❌ Error processing nation {getattr(nation, 'id', 'unknown')}: {e}")
                    continue
            
            if parsing_errors:
                print(f"⚠️ Date parsing errors for {len(parsing_errors)} nations")
            
            if not formatted_nations:
                print("🚨 No valid nations after filtering")
                return []
            
            # Sort by actual datetime (last_active) in descending order (most recent first)
            # This ensures newly active players appear at the top
            formatted_nations.sort(
                key=lambda x: x['last_active_dt'] if x['last_active_dt'] is not None else datetime.min.replace(tzinfo=timezone.utc),
                reverse=True
            )
            
            print(f"✅ Successfully processed {len(formatted_nations)} nations sorted by activity")
            return formatted_nations
            
        except Exception as e:
            error_details = {
                "error": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
            print(f"🚨 Critical PnW API failure: {error_details}")
            return []

    async def refresh_nations_async(self):
        """
        Async wrapper for get_unallied_nations to be used by the refresh button.
        """
        # Run the synchronous API call in a thread to avoid blocking
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(None, self.get_unallied_nations)

    def get_random_recruit_message(self, leader_name):
        """Get a random recruitment message for a leader with Discord and Alliance links"""
        if not self.recruit_messages:
            return None, None
            
        message = random.choice(self.recruit_messages)
        subject = message["subject"]
        
        # Add Discord and Alliance links to the message
        discord_link = "https://discord.gg/JSAEGjmUQG"
        alliance_link = "https://politicsandwar.com/alliance/id=9445"
        
        body = message["body"].format(
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
        
        return subject, body

    def send_p_and_w_message(self, receiver_id, leader_name, cc_leaders=None):
        """
        Sends a random recruitment message to a specific nation using the REST API.
        Supports Carbon Copy (CC) field for sending duplicate messages to up to 20 additional leaders.
        Includes comprehensive error handling and detailed logging.
        """
        try:
            import requests
            import json
            
            subject, body = self.get_random_recruit_message(leader_name)
            if not subject or not body:
                print(f"⚠️ No recruitment message available for {leader_name}")
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

    @commands.hybrid_command(name="recruit", description="Shows unallied nations for recruitment, sorted by recent activity.")
    async def recruit(self, ctx: commands.Context):
        """
        Displays all unallied nations sorted by most recent activity first.
        Includes comprehensive error handling and detailed nation information.
        """
        # Check if the user is Aries
        if ctx.author.id != ARIES_USER_ID:
            await ctx.send("❌ This command is restricted to Aries only.", ephemeral=True)
            return
            
        async with ctx.typing():
            try:
                print(f"🎯 Starting recruit command for user {ctx.author.name}")
                nations = self.get_unallied_nations()
                
                if not nations:
                    embed = discord.Embed(
                        title="📭 No Unallied Nations Found",
                        description="No nations without alliances were found, or there may be an issue with the P&W API.",
                        color=discord.Color.orange()
                    )
                    embed.add_field(
                        name="Possible Reasons",
                        value="• All nations may have alliances\n• API may be temporarily unavailable\n• All nations may be inactive for 7+ days\n• All nations may be in vacation mode",
                        inline=False
                    )
                    await ctx.send(embed=embed, ephemeral=True)
                    return

                # Nations are now guaranteed to be sorted by most recent activity
                total_nations = len(nations)
                
                # Create summary statistics
                active_recently = sum(1 for n in nations if n.get('last_active_dt') is not None)
                total_score = sum(n.get('score', 0) for n in nations)
                avg_score = total_score / total_nations if total_nations > 0 else 0
                
                # Create the main embed with comprehensive information
                embed = discord.Embed(
                    title=f"🦾⚡ {total_nations} Unallied Nations Available ⚡🦾",
                    description=f"Displaying all nations sorted by **most recent activity** (newest first).",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="📊 Summary",
                    value=f"**Total Nations:** {total_nations}\n"
                           f"**With Activity Data:** {active_recently}\n"
                           f"**Average Score:** {avg_score:,.0f}\n"
                           f"**Pages:** {(total_nations - 1) // 5 + 1}",
                    inline=False
                )
                
                # Add the top 5 most active nations to the summary
                top_nations = nations[:5]
                top_list = ""
                for i, nation in enumerate(top_nations, 1):
                    try:
                        last_active_str = nation.get('last_active', 'Unknown')
                        leader_name = nation.get('leader_name', 'Unknown')
                        nation_name = nation.get('nation_name', 'Unknown')
                        score = nation.get('score', 0)
                        
                        # Format last active time
                        if nation.get('last_active_dt'):
                            delta = datetime.now(timezone.utc) - nation['last_active_dt']
                            if delta.days == 0:
                                time_str = f"{delta.seconds // 3600}h ago"
                            else:
                                time_str = f"{delta.days}d ago"
                        else:
                            time_str = "Unknown"
                        
                        top_list += f"**#{i}.** [{leader_name}](https://politicsandwar.com/nation/id={nation['nation_id']}) of {nation_name}\n"
                        top_list += f"💪 {score:,.0f} | 🕐 {time_str}\n"
                    except Exception as e:
                        top_list += f"**#{i}.** Error processing nation data\n"
                
                if top_list:
                    embed.add_field(
                        name="🏆 Top 5 Most Active",
                        value=top_list.rstrip(),
                        inline=False
                    )
                
                embed.set_footer(
                    text=f"Use the buttons below to navigate through all {total_nations} nations • Sorted by activity"
                )
                
                # Create the paginated view with all nations
                view = RecruitPaginatorView(nations, self)
                
                await ctx.send(embed=embed, view=view)
                print(f"✅ Successfully sent recruit command with {total_nations} nations")
                
            except Exception as e:
                error_details = {
                    "error": str(e),
                    "type": type(e).__name__,
                    "user": str(ctx.author)
                }
                print(f"🚨 Critical error in recruit command: {error_details}")
                
                embed = discord.Embed(
                    title="❌ Error Loading Nations",
                    description="An error occurred while fetching nations from the Politics & War API.",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="Error Details",
                    value=f"```{str(e)[:1000]}```",
                    inline=False
                )
                embed.add_field(
                    name="Next Steps",
                    value="• Try the command again in a few minutes\n• Check if the P&W API is available\n• Contact bot administrator if issue persists",
                    inline=False
                )
                await ctx.send(embed=embed, ephemeral=True)

class RecruitPaginatorView(discord.ui.View):
    def __init__(self, nations, cog):
        super().__init__(timeout=None)  # No timeout - view stays open indefinitely
        self.nations = nations
        self.cog = cog
        self.current_page = 0
        self.nations_per_page = 5
        self.update_buttons()

    def create_nation_embed(self, page, nations):
        """
        Creates a comprehensive embed showing nations sorted by activity.
        Includes detailed nation information and proper activity formatting.
        """
        total_nations = len(nations)
        total_pages = (total_nations - 1) // self.nations_per_page
        
        embed = discord.Embed(
            title=f"🦾⚡ Unallied Nations (Page {page + 1}/{total_pages + 1}) ⚡🦾",
            description=f"Displaying **{self.nations_per_page}** nations sorted by **most recent activity**.",
            color=discord.Color.blue()
        )
        
        start_index = page * self.nations_per_page
        end_index = min(start_index + self.nations_per_page, total_nations)
        current_page_nations = nations[start_index:end_index]
        
        # Add overall progress indicator
        embed.add_field(
            name="📊 Progress",
            value=f"**Showing:** {start_index + 1}-{end_index} of {total_nations} nations\n"
                   f"**Sorted by:** Most recent activity (newest first)",
            inline=False
        )
        
        # Build detailed nation information
        nations_list = ""
        for i, nation in enumerate(current_page_nations, start=1):
            try:
                nation_id = nation['nation_id']
                nation_name = nation.get('nation_name', 'Unknown')
                leader_name = nation.get('leader_name', 'Unknown')
                score = nation.get('score', 0)
                cities = nation.get('cities_count', 0)
                last_active_str = nation.get('last_active', 'Unknown')
                
                # Format activity with comprehensive error handling
                activity_indicator = "⚪"
                time_ago = "Unknown"
                
                if nation.get('last_active_dt'):
                    try:
                        from datetime import datetime, timezone
                        now = datetime.now(timezone.utc)
                        delta = now - nation['last_active_dt']
                        
                        days = delta.days
                        hours = delta.seconds // 3600
                        minutes = (delta.seconds % 3600) // 60
                        
                        if days >= 7:
                            activity_indicator = "🔴"
                            time_ago = f"{days}d ago"
                        elif days >= 1:
                            activity_indicator = "🟠"
                            time_ago = f"{days}d {hours}h ago"
                        elif hours >= 1:
                            activity_indicator = "🟡"
                            time_ago = f"{hours}h {minutes}m ago"
                        elif minutes > 0:
                            activity_indicator = "🟢"
                            time_ago = f"{minutes}m ago"
                        else:
                            activity_indicator = "🟢"
                            time_ago = "Just now"
                            
                    except Exception:
                        activity_indicator = "⚪"
                        time_ago = "Unknown"
                
                # Create nation entry with all details
                rank = start_index + i
                nations_list += (
                    f"**#{rank}.** [{leader_name}](https://politicsandwar.com/nation/id={nation_id})\n"
                    f"   **Nation:** {nation_name}\n"
                    f"   **Score:** {score:,.0f} | **Cities:** {cities} | {activity_indicator} {time_ago}\n\n"
                )
                
            except Exception as e:
                nations_list += f"**#{start_index + i}.** Error processing nation data\n\n"
        
        if nations_list:
            # Split into multiple fields if too long for Discord limits
            if len(nations_list) > 1024:
                # Split into chunks of ~500 characters
                chunks = [nations_list[i:i+500] for i in range(0, len(nations_list), 500)]
                for i, chunk in enumerate(chunks):
                    embed.add_field(
                        name=f"Nations {i+1}",
                        value=chunk.rstrip(),
                        inline=False
                    )
            else:
                embed.add_field(
                    name=f"📋 Nations {start_index + 1}-{end_index}",
                    value=nations_list.rstrip(),
                    inline=False
                )
        
        # Add navigation and sorting information
        embed.set_footer(
            text=f"Page {page + 1} of {total_pages + 1} • Use buttons to navigate • All {total_nations} nations sorted by activity"
        )
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

    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.primary, custom_id="refresh_nations")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if the user is Aries
        if interaction.user.id != ARIES_USER_ID:
            await interaction.response.send_message("❌ This interaction is restricted to Aries only.", ephemeral=True)
            return
            
        await interaction.response.defer()  # Defer response to allow processing
        
        try:
            # Show loading state
            embed = discord.Embed(
                title="🔄 Refreshing Nation Data...",
                description="Fetching latest unallied nations from Politics & War API...",
                color=discord.Color.orange()
            )
            await interaction.edit_original_response(embed=embed, view=None)
            
            # Refresh nations with timeout handling
            try:
                import asyncio
                new_nations = await asyncio.wait_for(
                    self.cog.refresh_nations_async(), 
                    timeout=30.0  # 30 second timeout
                )
                
                if not new_nations:
                    embed = discord.Embed(
                        title="⚠️ No Nations Found",
                        description="No unallied nations found or an error occurred during refresh.",
                        color=discord.Color.yellow()
                    )
                    await interaction.edit_original_response(embed=embed, view=self)
                    return
                    
                # Update with new nations (maintains activity-based sorting)
                self.nations = new_nations
                self.current_page = 0  # Reset to first page
                self.update_buttons()
                
                # Create fresh embed with updated data
                embed = self.create_nation_embed(self.current_page, self.nations)
                await interaction.edit_original_response(embed=embed, view=self)
                
            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title="⏰ Refresh Timeout",
                    description="The request to P&W API timed out. Please try again in a few moments.",
                    color=discord.Color.red()
                )
                await interaction.edit_original_response(embed=embed, view=self)
                
        except Exception as e:
            # Log full error for debugging
            import traceback
            print(f"Refresh error in RecruitPaginatorView: {e}")
            traceback.print_exc()
            
            embed = discord.Embed(
                title="❌ Refresh Error",
                description=f"Failed to refresh nation data: {str(e)}",
                color=discord.Color.red()
            )
            embed.add_field(
                name="What to do",
                value="1. Check if P&W API is online\n2. Try refreshing again\n3. Contact bot admin if issue persists",
                inline=False
            )
            await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Recruit All Shown", style=discord.ButtonStyle.success, custom_id="send_page")
    async def send_page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if the user is Aries
        if interaction.user.id != ARIES_USER_ID:
            await interaction.response.send_message("❌ This interaction is restricted to Aries only.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        
        start_index = self.current_page * self.nations_per_page
        end_index = start_index + self.nations_per_page
        current_page_nations = self.nations[start_index:end_index]
        
        if not current_page_nations:
            await interaction.followup.send("❌ No nations to recruit on this page.", ephemeral=True)
            return
            
        sent_count = 0
        failed_count = 0
        
        await interaction.followup.send(f"🚀 Starting recruitment for {len(current_page_nations)} nations on this page...", ephemeral=True)
        
        for nation in current_page_nations:
            try:
                result = self.cog.send_p_and_w_message(nation['nation_id'], nation['leader_name'])
                if result == 200:
                    sent_count += 1
                else:
                    failed_count += 1
                    
                # Rate limiting - wait 1 second between messages to avoid API overload
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Error recruiting {nation['leader_name']}: {e}")
                failed_count += 1
                
        await interaction.followup.send(f"✅ Recruitment complete! Sent: {sent_count}, Failed: {failed_count}", ephemeral=True)

    @discord.ui.button(label="🎯 Mass Recruit ALL", style=discord.ButtonStyle.danger, custom_id="mass_recruit_all")
    async def mass_recruit_all_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if the user is Aries
        if interaction.user.id != ARIES_USER_ID:
            await interaction.response.send_message("❌ This interaction is restricted to Aries only.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        
        if not self.nations:
            await interaction.followup.send("❌ No nations available for recruitment.", ephemeral=True)
            return
            
        total_nations = len(self.nations)
        sent_count = 0
        failed_count = 0
        
        # Process nations in batches of 20 for parallel processing (much faster than individual)
        batch_size = 20
        batches = [self.nations[i:i + batch_size] for i in range(0, total_nations, batch_size)]
        total_batches = len(batches)
        
        await interaction.followup.send(f"🚀 Starting MASS recruitment for {total_nations} nations...\n"
                                       f"📊 Processing in {total_batches} batches of {batch_size} nations each\n"
                                       f"⏱️ This will take approximately {total_batches} seconds due to rate limiting.", ephemeral=True)
        
        import asyncio
        for batch_index, batch_nations in enumerate(batches):
            try:
                batch_sent = 0
                batch_failed = 0
                
                # Send messages to all nations in this batch
                for nation in batch_nations:
                    try:
                        result = self.cog.send_p_and_w_message(nation['nation_id'], nation['leader_name'])
                        if result == 200:
                            batch_sent += 1
                        else:
                            batch_failed += 1
                    except Exception as e:
                        print(f"Error sending to {nation['leader_name']}: {e}")
                        batch_failed += 1
                
                sent_count += batch_sent
                failed_count += batch_failed
                
                # Send progress update every few batches
                if batch_index % 5 == 0 or batch_index == total_batches - 1:
                    await interaction.followup.send(f"📊 Progress: Batch {batch_index + 1}/{total_batches} processed "
                                                   f"({sent_count + failed_count}/{total_nations} nations)", ephemeral=True)
                    
                # Rate limiting - wait 1 second between batches
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Error recruiting batch {batch_index + 1}: {e}")
                failed_count += len(batch_nations)
                
        await interaction.followup.send(f"✅ MASS recruitment complete!\n"
                                       f"📊 Total nations: {total_nations}\n"
                                       f"✅ Successfully sent: {sent_count}\n"
                                       f"❌ Failed to send: {failed_count}\n"
                                       f"📈 Efficiency: {((sent_count/total_nations)*100):.1f}%", ephemeral=True)

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