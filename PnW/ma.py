import discord
from discord.ext import commands
import sys
import os
from typing import List, Dict, Optional, Any
import asyncio
from datetime import datetime

try:
    import pnwkit
    PNWKIT_AVAILABLE = True
    PNWKIT_ERROR = None
    PNWKIT_SOURCE = "system"

except ImportError as e:
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

import_errors = {}
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import PANDW_API_KEY, CYBERTRON_ALLIANCE_ID, PRIMAL_USER_ID, ARIES_USER_ID, CARNAGE_USER_ID, BENEVOLENT_USER_ID, TECH_USER_ID, get_role_ids
from Systems.user_data_manager import UserDataManager

# MA Module imports with fallback logic
MA_IMPORTS = {
    'alliance_views': {
        'module': 'alliance',
        'items': ['AllianceTotalsView', 'FullMillView'],
        'globals': {}
    },
    'parties_views': {
        'module': 'parties',
        'items': ['PartiesView', 'PartiesManager'],
        'globals': {}
    },
    'blitz_views': {
        'module': 'blitz',
        'items': ['PartyView'],
        'globals': {}
    },
    'nations_views': {
        'module': 'nations',
        'items': ['NationListView'],
        'globals': {}
    },
    'destroy_views': {
        'module': 'destroy',
        'items': ['TargetPartyView'],
        'globals': {}
    },
    'query_system': {
        'module': 'query',
        'items': ['PNWAPIQuery'],
        'globals': {}
    }
}

def safe_import_ma_modules():
    """Safely import MA modules with fallback logic and error tracking."""
    import importlib
    import sys
    
    for import_key, config in MA_IMPORTS.items():
        module_name = config['module']
        items = config['items']
        
        try:
            # Try direct import from MA subdirectory first
            try:
                module = importlib.import_module(f"MA.{module_name}")
                for item in items:
                    if hasattr(module, item):
                        globals()[item] = getattr(module, item)
                        config['globals'][item] = getattr(module, item)
                    else:
                        globals()[item] = None
                        config['globals'][item] = None
                        print(f"⚠️ Warning: {item} not found in {module_name} module")
                import_errors[import_key] = None
                
            except ImportError as e:
                # Try relative import as fallback
                try:
                    # Get the current package name
                    current_package = __name__.rsplit('.', 1)[0] if '.' in __name__ else None
                    if current_package:
                        module = importlib.import_module(f".MA.{module_name}", package=current_package)
                    else:
                        # If no package context, try absolute import
                        module = importlib.import_module(f"Systems.PnW.MA.{module_name}")
                    
                    for item in items:
                        if hasattr(module, item):
                            globals()[item] = getattr(module, item)
                            config['globals'][item] = getattr(module, item)
                        else:
                            globals()[item] = None
                            config['globals'][item] = None
                            print(f"⚠️ Warning: {item} not found in {module_name} module")
                    import_errors[import_key] = None
                    
                except ImportError as e2:
                    # Set items to None if all imports fail
                    for item in items:
                        globals()[item] = None
                        config['globals'][item] = None
                    import_errors[import_key] = f"Direct import: {str(e)}, Relative import: {str(e2)}"
                    print(f"⚠️ Warning: Could not load {module_name} module: {str(e2)}")
                
        except Exception as e:
            # Handle unexpected errors
            for item in items:
                globals()[item] = None
                config['globals'][item] = None
            import_errors[import_key] = f"Unexpected error: {str(e)}"
            print(f"⚠️ Warning: Unexpected error loading {module_name} module: {str(e)}")

# Execute the safe import
safe_import_ma_modules()

class TargetInputTypeSelect(discord.ui.Select):
    """Dropdown for selecting target input type."""
    
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Nation Name",
                description="Search by nation name (e.g., 'United States')",
                emoji="🏛️",
                value="nation_name"
            ),
            discord.SelectOption(
                label="Leader Name", 
                description="Search by leader name (e.g., 'John Smith')",
                emoji="👤",
                value="leader_name"
            ),
            discord.SelectOption(
                label="Nation ID",
                description="Search by nation ID number (e.g., '123456')",
                emoji="🔢",
                value="nation_id"
            ),
            discord.SelectOption(
                label="Nation Link",
                description="Search by P&W nation link",
                emoji="🔗",
                value="nation_link"
            )
        ]
        
        super().__init__(
            placeholder="Select input type...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle input type selection."""
        # Update the modal's selected input type
        self.view.selected_input_type = self.values[0]
        
        # Update the text input placeholder based on selection
        input_type_examples = {
            "nation_name": "Enter nation name (e.g., 'United States')",
            "leader_name": "Enter leader name (e.g., 'John Smith')", 
            "nation_id": "Enter nation ID (e.g., '123456')",
            "nation_link": "Enter P&W nation link"
        }
        
        # Acknowledge the selection
        await interaction.response.send_message(
            f"✅ Selected: **{self.values[0].replace('_', ' ').title()}**\n"
            f"Now enter your target: {input_type_examples[self.values[0]]}",
            
        )

class TargetInputModal(discord.ui.Modal, title="🎯 Target Nation Input"):
    """Enhanced modal for inputting target nation information with type selection."""
    
    def __init__(self, author_id: int, bot: commands.Bot):
        super().__init__()
        self.author_id = author_id
        self.bot = bot
        self.selected_input_type = None
    
    target_input = discord.ui.TextInput(
        label="Target Information",
        placeholder="First select input type above, then enter your target here",
        style=discord.TextStyle.short,
        max_length=200,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle target input submission."""
        try:
            await interaction.response.defer()
            
            target_data = self.target_input.value.strip()
            if not target_data:
                embed = discord.Embed(
                    title="❌ Invalid Input",
                    description="Please provide a valid target identifier.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Check if input type was selected
            if not self.selected_input_type:
                embed = discord.Embed(
                    title="❌ Input Type Not Selected",
                    description="Please select an input type first using the dropdown above the text field.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Get the destroy cog
            destroy_cog = self.bot.get_cog('DestroyCog')
            if not destroy_cog:
                embed = discord.Embed(
                    title="❌ Destroy System Unavailable",
                    description="Destroy system is not available. Please contact an administrator.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Use the selected input type directly instead of parsing
            input_type = self.selected_input_type
            
            # Fetch target nation data using the specified input type
            target_nation = await destroy_cog.fetch_target_nation(target_data, input_type)
            if not target_nation:
                embed = discord.Embed(
                    title="❌ Target Not Found",
                    description=f"Could not find a nation matching: `{target_data}`\n"
                               f"Input type: **{input_type.replace('_', ' ').title()}**\n\n"
                               f"Please check your input and try again.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Load blitz parties
            parties = destroy_cog.load_blitz_parties()
            if not parties:
                embed = discord.Embed(
                    title="❌ No Parties Available",
                    description="No blitz parties found. Please create parties first using the 'Blitz Party Sort' option.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Find suitable parties for the target
            suitable_parties = await destroy_cog.find_suitable_parties(target_nation, parties)
            if not suitable_parties:
                embed = discord.Embed(
                    title="❌ No Suitable Parties",
                    description=f"No parties found that can effectively attack **{target_nation.get('nation_name', 'Unknown')}**.\n\nThis could be due to:\n• Score range incompatibility\n• Insufficient military advantages\n• No strategic capabilities",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create target info embed
            target_embed = destroy_cog.create_target_info_embed(target_nation)
            
            # Create TargetPartyView for displaying suitable parties
            party_view = TargetPartyView(interaction, target_nation, suitable_parties, destroy_cog)
            
            # Send target info and party view
            await interaction.followup.send(embed=target_embed)
            
            # Send the first party embed with navigation
            first_party_embed = party_view.create_party_embed(suitable_parties[0], 1)
            await interaction.followup.send(embed=first_party_embed, view=party_view)
            
        except Exception as e:
            print(f"Error in TargetInputModal.on_submit: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred while processing your request: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

class TargetInputView(discord.ui.View):
    """View containing the input type selector and modal trigger."""
    
    def __init__(self, author_id: int, bot: commands.Bot):
        super().__init__(timeout=300)  # 5 minute timeout
        self.author_id = author_id
        self.bot = bot
        self.selected_input_type = None
        
        # Add the input type selector
        self.input_type_select = TargetInputTypeSelect()
        self.add_item(self.input_type_select)
    
    @discord.ui.button(label="Enter Target", style=discord.ButtonStyle.primary, emoji="🎯")
    async def enter_target_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to open the target input modal."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You cannot use this button.")
            return
        
        # Check if input type was selected
        if not self.selected_input_type:
            await interaction.response.send_message(
                "❌ Please select an input type first using the dropdown above.",
                
            )
            return
        
        # Create and show the modal
        modal = TargetInputModal(self.author_id, self.bot)
        modal.selected_input_type = self.selected_input_type
        await interaction.response.send_modal(modal)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the user can interact with this view."""
        return interaction.user.id == self.author_id
    
    async def on_timeout(self):
        """Handle view timeout."""
        # Disable all items
        for item in self.children:
            item.disabled = True

class MAOperationSelect(discord.ui.Select):
    """Dropdown menu for selecting MA operations."""   
    def __init__(self, author_id: int, bot: commands.Bot, blitz_cog: 'BlitzParties'):
        self.author_id = author_id
        self.bot = bot
        self.blitz_cog = blitz_cog        
        options = [

            discord.SelectOption(
                label="Alliance Totals",
                description="View comprehensive alliance statistics and totals",
                emoji="📊",
                value="alliance_totals"
            ),

            discord.SelectOption(
                label="View Nations",
                description="View all active nations with their capabilities",
                emoji="👁️",
                value="view_nations"
            ),

            discord.SelectOption(
                label="Blitz Party Sort",
                description="Generate strategically balanced blitz parties",
                emoji="🤖",
                value="blitz_sort"
            ),

            discord.SelectOption(
                label="Blitz Party View",
                description="View existing saved blitz parties",
                emoji="👥",
                value="blitz_view"
            ),

            discord.SelectOption(
                label="Destroy Opp",
                description="Find optimal blitz parties to attack a target nation",
                emoji="🎯",
                value="destroy_opp"
            ),

            discord.SelectOption(
                label="Mass Recruit",
                description="Launch recruitment campaign and nation browser",
                emoji="📣",
                value="mass_recruit"
            )

        ]        

        super().__init__(
            placeholder="Select an operation...",
            min_values=1,
            max_values=1,
            options=options
        )   

    async def callback(self, interaction: discord.Interaction):
        """Handle dropdown selection."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You cannot use this menu.")
            return
        
        await interaction.response.defer()        
        try:
            if self.values[0] == "alliance_totals":
                await self._show_alliance_totals(interaction)
            elif self.values[0] == "blitz_sort":
                await self._show_blitz_sort(interaction)
            elif self.values[0] == "blitz_view":
                await self._show_blitz_view(interaction)
            elif self.values[0] == "view_nations":
                await self._show_view_nations(interaction)
            elif self.values[0] == "destroy_opp":
                await self._show_destroy_opp(interaction)
            elif self.values[0] == "mass_recruit":
                try:
                    recruit_cog = self.bot.get_cog('RecruitCog')
                    if not recruit_cog:
                        error_embed = discord.Embed(
                            title="❌ Recruitment System Unavailable",
                            description="Recruitment system is not loaded. Please contact an administrator.",
                            color=discord.Color.red()
                        )
                        await interaction.followup.send(embed=error_embed)
                        return
                    # Start the recruitment flow via interaction
                    await recruit_cog.start_recruit_from_interaction(interaction)
                except Exception as recruit_err:
                    print(f"Error launching Mass Recruit: {recruit_err}")
                    error_embed = discord.Embed(
                        title="❌ Recruitment Error",
                        description=f"An error occurred while starting Mass Recruit: {str(recruit_err)}",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=error_embed)

        except Exception as e:
            print(f"Error in MA dropdown callback: {e}")
            embed = discord.Embed(
                title="❌ Operation Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
    
    async def _show_alliance_totals(self, interaction: discord.Interaction):
        """Show comprehensive alliance statistics using AllianceTotalsView."""
        try:
            # Check if AllianceTotalsView is available
            if not AllianceTotalsView:
                error_details = import_errors.get('alliance_views', 'Unknown import error')
                embed = discord.Embed(
                    title="❌ Alliance System Unavailable",
                    description=f"Alliance Management System could not be loaded. Error: {error_details}",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Get the alliance manager cog for data fetching and view creation
            alliance_cog = self.bot.get_cog('AllianceManager')
            if not alliance_cog:
                embed = discord.Embed(
                    title="❌ Alliance System Unavailable",
                    description="Alliance Management System is not loaded.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Check if cybertron_alliance_id is available
            if not CYBERTRON_ALLIANCE_ID:
                embed = discord.Embed(
                    title="❌ Configuration Error",
                    description="Alliance ID not configured properly.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Fetch alliance data using alliance cog - first try cache, then populate if empty
            try:
                nations = await alliance_cog.get_alliance_nations(str(CYBERTRON_ALLIANCE_ID))
                if not nations:
                    # Cache is empty, populate it using PNWAPIQuery
                    if PNWAPIQuery:
                        # Send loading message
                        loading_embed = discord.Embed(
                            title="⏳ Querying API for Alliance Data",
                            description="Directly querying the P&W API for the most current data...\nThis ensures you see the latest information.\nThis may take a moment.",
                            color=discord.Color.orange()
                        )
                        await interaction.followup.send(embed=loading_embed)
                        
                        # Create query instance and populate cache
                        query_instance = PNWAPIQuery()
                        nations = await query_instance.get_alliance_nations(str(CYBERTRON_ALLIANCE_ID), bot=self.bot, force_refresh=True)
                        
                        # Store in alliance_cache.json with timestamp via UserDataManager
                        try:
                            user_data_manager = UserDataManager()
                            alliance_cache = await user_data_manager.get_json_data('alliance_cache', {})
                            cache_key = f"alliance_data_{CYBERTRON_ALLIANCE_ID}"
                            alliance_cache[cache_key] = {
                                'timestamp': time.time(),
                                'nations': nations
                            }
                            await user_data_manager.save_json_data('alliance_cache', alliance_cache)
                            print(f"Stored alliance data in cache: {len(nations)} nations")
                        except Exception as cache_error:
                            print(f"Error storing alliance data in cache: {cache_error}")
                        
                        if not nations:
                            embed = discord.Embed(
                                title="❌ No Alliance Data",
                                description="Failed to retrieve alliance data from API.",
                                color=discord.Color.red()
                            )
                            await interaction.edit_original_response(embed=embed)
                            return
                    else:
                        embed = discord.Embed(
                            title="❌ Query System Unavailable",
                            description="Cannot populate alliance cache - Query system not available.",
                            color=discord.Color.red()
                        )
                        await interaction.followup.send(embed=embed)
                        return
            except Exception as e:
                print(f"Error fetching alliance nations: {e}")
                embed = discord.Embed(
                    title="❌ Alliance Data Error",
                    description=f"Failed to fetch alliance data: {str(e)}",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Get active nations for statistics
            active_nations = alliance_cog.get_active_nations(nations)
            stats = alliance_cog.calculate_alliance_statistics(active_nations)
            
            # Calculate nation statistics for all nations (including inactive)
            nation_stats = alliance_cog.calculate_nation_statistics(nations)
            
            # Generate alliance totals embed using the method from alliance.py
            embed = await alliance_cog.generate_alliance_totals_embed(nations)
            
            # Create AllianceTotalsView with navigation buttons
            view = AllianceTotalsView(self.author_id, self.bot, alliance_cog, nations)
            
            # Send the Alliance Totals embed immediately with navigation buttons
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"Error showing alliance totals: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to load alliance statistics: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
    
    async def _show_blitz_sort(self, interaction: discord.Interaction):
        """Show blitz party sorting functionality using NationListView."""
        try:
            # Check if blitz_cog is available
            if not self.blitz_cog:
                embed = discord.Embed(
                    title="❌ Blitz System Unavailable",
                    description="Blitz Parties System is not loaded. Please contact an administrator.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Check if cybertron_alliance_id is available
            if not hasattr(self.blitz_cog, 'cybertron_alliance_id'):
                embed = discord.Embed(
                    title="❌ Configuration Error",
                    description="Alliance ID not configured properly.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Fetch alliance data - first try cache, then populate if empty
            nations = await self.blitz_cog.get_alliance_nations(str(self.blitz_cog.cybertron_alliance_id))
            if not nations:
                # Cache is empty, populate it using PNWAPIQuery
                if PNWAPIQuery:
                    # Send loading message
                    loading_embed = discord.Embed(
                        title="⏳ Querying API for Alliance Data",
                        description="Directly querying the P&W API for the most current data...\nThis ensures you see the latest information.\nThis may take a moment.",
                        color=discord.Color.orange()
                    )
                    await interaction.followup.send(embed=loading_embed)
                    
                    # Create query instance and populate cache
                    query_instance = PNWAPIQuery()
                    nations = await query_instance.get_alliance_nations(str(self.blitz_cog.cybertron_alliance_id), bot=self.bot)
                    
                    if not nations:
                        embed = discord.Embed(
                            title="❌ No Alliance Data",
                            description="Failed to retrieve alliance data from API.",
                            color=discord.Color.red()
                        )
                        await interaction.edit_original_response(embed=embed)
                        return
                else:
                    embed = discord.Embed(
                        title="❌ Query System Unavailable",
                        description="Cannot populate alliance cache - Query system not available.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
            
            # Create balanced parties
            parties = self.blitz_cog.create_balanced_parties(nations)
            
            if not parties:
                embed = discord.Embed(
                    title="❌ No Viable Parties",
                    description="Unable to create viable blitz parties.\n\n**Requirements:**\n• Parties of exactly 3 members\n• Compatible score ranges for same-target attacks\n• At least 1 member with Ground, Air, or Naval advantage\n• Preference for strategic capabilities (missiles/nukes)",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Process parties for display and save using centralized method
            party_info_display, party_info_save = self.blitz_cog.process_parties_for_display(parties)
            
            # Save the party data
            await self.blitz_cog.save_blitz_parties(party_info_save)
            
            # Create and send the party view
            party_view = PartyView(parties, interaction.user.id, self.bot, self.blitz_cog)
            first_embed = party_view.create_embed()
            await interaction.followup.send(embed=first_embed, view=party_view)
            
        except Exception as e:
            print(f"Error showing blitz sort: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to create blitz parties: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
    
    async def _show_view_nations(self, interaction: discord.Interaction):
        """View all active nations with their capabilities using NationListView."""
        try:
            # Check if NationsManager cog is available
            nations_cog = self.bot.get_cog('NationsManager')
            if not nations_cog:
                embed = discord.Embed(
                    title="❌ Nations System Unavailable",
                    description="Nations Management System is not loaded. Please contact an administrator.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Check if blitz_cog is available for alliance ID
            if not self.blitz_cog:
                embed = discord.Embed(
                    title="❌ Blitz System Unavailable",
                    description="Blitz Parties System is not loaded. Please contact an administrator.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Check if cybertron_alliance_id is available
            if not hasattr(self.blitz_cog, 'cybertron_alliance_id'):
                embed = discord.Embed(
                    title="❌ Configuration Error",
                    description="Alliance ID not configured properly.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Send loading message
            loading_embed = discord.Embed(
                title="⏳ Loading Alliance Data",
                description="Loading alliance data (using cached data when available)...",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=loading_embed)
            
            # Try to get alliance nations from alliance_cog first (which has caching)
            alliance_cog = self.bot.get_cog('AllianceManager')
            nations = None
            
            if alliance_cog and hasattr(alliance_cog, 'get_alliance_nations'):
                # Use the cached version from alliance_cog
                nations = await alliance_cog.get_alliance_nations(str(self.blitz_cog.cybertron_alliance_id))
            
            # Fallback to direct API query if alliance_cog not available or no cached data
            if not nations and PNWAPIQuery:
                # Create query instance and get fresh data
                query_instance = PNWAPIQuery()
                nations = await query_instance.get_alliance_nations(str(self.blitz_cog.cybertron_alliance_id), bot=self.bot)
                
                if not nations:
                    embed = discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data from API.",
                        color=discord.Color.red()
                    )
                    await interaction.edit_original_response(embed=embed)
                    return
            elif not nations:
                embed = discord.Embed(
                    title="❌ Query System Unavailable",
                    description="Cannot fetch alliance data - Query system not available.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Update loading message to show data was retrieved
            await interaction.edit_original_response(embed=discord.Embed(
                title="✅ Alliance Data Retrieved",
                description=f"Successfully retrieved data for {len(nations)} nations.",
                color=discord.Color.green()
            ))
            
            # Filter out vacation mode and applicant nations
            active_nations = nations_cog.get_active_nations(nations)
            if not active_nations:
                embed = discord.Embed(
                    title="❌ No Active Nations",
                    description="No active nations found (all nations are either in vacation mode or applicants).",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Use NationListView to display the filtered nations in paginated format
            from .nations import NationListView
            nation_view = NationListView(active_nations, interaction.user.id, self.bot, nations_cog)
            
            # Send the first page of nations
            first_embed = nation_view.create_embed()
            await interaction.followup.send(embed=first_embed, view=nation_view)
            
        except Exception as e:
            print(f"Error showing view nations: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to load nations overview: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    async def _show_blitz_view(self, interaction: discord.Interaction):
        """Show saved blitz parties using PartiesView from parties.py."""
        try:
            # Check if PartiesView is available
            if not PartiesView:
                error_details = import_errors.get('parties_views', 'Unknown import error')
                embed = discord.Embed(
                    title="❌ Parties System Unavailable",
                    description=f"Parties system could not be loaded. Error: {error_details}",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Check if blitz_cog is available
            if not self.blitz_cog:
                embed = discord.Embed(
                    title="❌ Blitz System Unavailable",
                    description="Blitz Parties System is not loaded. Please contact an administrator.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create parties view with error handling
            try:
                parties_view = PartiesView(interaction.user.id, self.bot, self.blitz_cog, None)
                
                # Send the first party embed
                first_embed = parties_view.create_embed()
                await interaction.followup.send(embed=first_embed, view=parties_view)
                
            except Exception as e:
                print(f"Error creating PartiesView: {e}")
                embed = discord.Embed(
                    title="❌ Parties View Error",
                    description=f"Failed to create parties view: {str(e)}",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
            
        except Exception as e:
            print(f"Error showing blitz view: {e}")
            import traceback
            traceback.print_exc()
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to load saved parties: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    async def _show_destroy_opp(self, interaction: discord.Interaction):
        """Show destroy opposition functionality with enhanced target input selection."""
        try:
            # Create the target input view with dropdown selection
            view = TargetInputView(interaction.user.id, self.bot)
            
            # Create an informative embed
            embed = discord.Embed(
                title="🎯 Destroy Opposition Target Selection",
                description=(
                    "Select how you want to identify your target nation, then click **Enter Target** to proceed.\n\n"
                    "**Available Input Types:**\n"
                    "🏛️ **Nation Name** - Search by nation name\n"
                    "👤 **Leader Name** - Search by leader name\n"
                    "🔢 **Nation ID** - Search by nation ID number\n"
                    "🔗 **Nation Link** - Search by P&W nation link\n\n"
                    "The system will find suitable blitz parties to attack your target."
                ),
                color=discord.Color.from_rgb(255, 100, 100)
            )
            
            embed.add_field(
                name="📋 Instructions",
                value=(
                    "1️⃣ Select input type from dropdown\n"
                    "2️⃣ Click **Enter Target** button\n"
                    "3️⃣ Enter target information in modal\n"
                    "4️⃣ Review suitable attack parties"
                ),
                inline=False
            )
            
            embed.set_footer(text="⚠️ Target nation will NOT be saved to any database")
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"Error in _show_destroy_opp: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to open target selection interface. Please try again.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

class MAOperationView(discord.ui.View):
    """View for MA operation selection."""
    
    def __init__(self, author_id: int, bot: commands.Bot, blitz_cog: 'BlitzParties'):
        super().__init__(timeout=60)  # 60 second timeout
        self.author_id = author_id
        self.bot = bot
        self.blitz_cog = blitz_cog
        
        # Add the dropdown menu
        self.add_item(MAOperationSelect(author_id, bot, blitz_cog))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is from the command author."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You cannot use this menu.")
            return False
        return True
    
    async def on_timeout(self):
        """Called when the view times out."""
        for item in self.children:
            item.disabled = True

class MilitaryAffairs(commands.Cog):
    """Military Affairs Command Center - Military operations and alliance management."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # Initialize PNWAPIQuery for API calls and caching
        if PNWAPIQuery:
            try:
                self.query_system = PNWAPIQuery()
                print("✅ PNWAPIQuery system initialized successfully")
            except Exception as e:
                self.query_system = None
                print(f"⚠️ Warning: Failed to initialize PNWAPIQuery: {str(e)}")
        else:
            self.query_system = None
            print("⚠️ Warning: PNWAPIQuery not available")
        
        print("Military Affairs cog initialized")
    
    @commands.hybrid_command(name="command_center", aliases=["ma", "ia", "audit"], help="🤖 Cybertr0nian Command Center")
    async def command_center(self, ctx: commands.Context):
        """Cybertr0nian Command Center - Access alliance statistics, blitz party generation, and saved parties."""
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
            # Build role mentions for all leadership roles
            leadership_mentions = ""
            if ctx.guild:
                role_ids = get_role_ids(ctx.guild.id)
                leadership_roles = ['Predaking', 'IA', 'MG', 'HG']
                mentions = []
                
                for role_name in leadership_roles:
                    role_ids_for_role = role_ids.get(role_name, [])
                    if role_ids_for_role:
                        mentions.extend([f"<@&{role_id}>" for role_id in role_ids_for_role])
                
                if mentions:
                    leadership_mentions = " & " + " ".join(mentions)
            
            embed = discord.Embed(
                title="❌ Access Denied",
                description=f"Only Alliance Leadership can access the Cybertr0nian Command Center.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        if not PNWKIT_AVAILABLE:
            print(f"⚠️ pnwkit not available - using direct API calls. Error: {PNWKIT_ERROR}")
        
        # Defer the response to prevent timeout for slash commands
        if hasattr(ctx, 'defer'):
            await ctx.defer()
        
        # Send initial loading message
        loading_embed = discord.Embed(
            title="🤖 Cybertr0nian Command Center",
            description="⚙️ Initializing Military Affairs operations...\n\nPlease select an operation from the dropdown menu.",
            color=discord.Color.from_rgb(0, 150, 255)
        )
        loading_msg = await ctx.send(embed=loading_embed)
        
        try:
            # Get the BlitzParties cog for accessing blitz functionality with error handling
            try:
                blitz_cog = self.bot.get_cog('BlitzParties')
                if not blitz_cog:
                    error_embed = discord.Embed(
                        title="❌ Blitz System Unavailable",
                        description="Blitz Parties System is not loaded. Please contact an administrator.",
                        color=discord.Color.red()
                    )
                    await loading_msg.edit(embed=error_embed)
                    return
            except Exception as e:
                print(f"Error getting BlitzParties cog: {e}")
                error_embed = discord.Embed(
                    title="❌ Blitz System Error",
                    description=f"Error accessing Blitz Parties System: {str(e)}",
                    color=discord.Color.red()
                )
                await loading_msg.edit(embed=error_embed)
                return
                
            # Note: Initial alliance data fetch removed. Data will be fetched per selection.
            pass
            
            # Create MA operation selection view with error handling
            try:
                ma_view = MAOperationView(ctx.author.id, self.bot, blitz_cog)
            except Exception as e:
                print(f"Error creating MAOperationView: {e}")
                error_embed = discord.Embed(
                    title="❌ View Creation Error",
                    description=f"Error creating operation view: {str(e)}",
                    color=discord.Color.red()
                )
                await loading_msg.edit(embed=error_embed)
                return
            
            # Update embed with operation selection
            operation_embed = discord.Embed(
                title="🤖 Cybertr0nian Command Center",
                description="Select an operation from the dropdown menu below:\n\n"
                           "📊 **Alliance Totals** - View comprehensive alliance statistics\n"
                           "👁️ **View Nations** - View all active nations with their capabilities\n"
                           "🤖 **Blitz Party Sort** - Generate strategically balanced blitz parties\n"
                           "👥 **Blitz Party View** - View existing saved blitz parties\n"
                           "🎯 **Destroy Opp** - Find optimal blitz parties to attack a target nation\n"
                           "📣 **Mass Recruit** - Mass Recruit EVERY unallied nation who is less than 14 days inactive\n(May take a moment to show, it's querying 15,000 nations!)",
                color=discord.Color.from_rgb(0, 150, 255)
            )
            operation_embed.set_footer(text="Data will be fetched per selection • Select an operation from the dropdown menu")
            
            await loading_msg.edit(embed=operation_embed, view=ma_view)
            
        except Exception as e:
            print(f"Error in MA command: {e}")
            import traceback
            traceback.print_exc()
            error_embed = discord.Embed(
                title="❌ Error Loading 🤖 Cybertr0nian Command Center",
                description=f"An error occurred while initializing the Cybertr0nian Command Center:\n```{str(e)}```",
                color=discord.Color.red()
            )
            await loading_msg.edit(embed=error_embed)

async def setup(bot: commands.Bot):
    """Setup function for loading the cog with comprehensive error handling."""
    setup_errors = []
    
    # Load Alliance Manager cog
    try:
        from Systems.PnW.MA.alliance import AllianceManager
        await bot.add_cog(AllianceManager(bot))
        print("✅ Alliance Management System loaded successfully!")
    except ImportError as e:
        try:
            from alliance import AllianceManager
            await bot.add_cog(AllianceManager(bot))
            print("✅ Alliance Management System loaded successfully (direct import)!")
        except Exception as e2:
            error_msg = f"AllianceManager: MA import: {str(e)}, Direct import: {str(e2)}"
            setup_errors.append(error_msg)
            print(f"⚠️ Warning: Could not load AllianceManager: {error_msg}")
    except Exception as e:
        error_msg = f"AllianceManager: Unexpected error: {str(e)}"
        setup_errors.append(error_msg)
        print(f"⚠️ Warning: Could not load AllianceManager: {error_msg}")
    
    # Load Blitz Parties cog
    try:
        from Systems.PnW.MA.blitz import BlitzParties
        await bot.add_cog(BlitzParties(bot))
        print("✅ Blitz Parties System loaded successfully!")
    except ImportError as e:
        try:
            from blitz import BlitzParties
            await bot.add_cog(BlitzParties(bot))
            print("✅ Blitz Parties System loaded successfully (direct import)!")
        except Exception as e2:
            error_msg = f"BlitzParties: MA import: {str(e)}, Direct import: {str(e2)}"
            setup_errors.append(error_msg)
            print(f"⚠️ Warning: Could not load BlitzParties: {error_msg}")
    except Exception as e:
        error_msg = f"BlitzParties: Unexpected error: {str(e)}"
        setup_errors.append(error_msg)
        print(f"⚠️ Warning: Could not load BlitzParties: {error_msg}")
    
    # Load Nations Manager cog
    try:
        from Systems.PnW.MA.nations import NationsManager
        await bot.add_cog(NationsManager(bot))
        print("✅ Nations Management System loaded successfully!")
    except ImportError as e:
        try:
            from nations import NationsManager
            await bot.add_cog(NationsManager(bot))
            print("✅ Nations Management System loaded successfully (direct import)!")
        except Exception as e2:
            error_msg = f"NationsManager: MA import: {str(e)}, Direct import: {str(e2)}"
            setup_errors.append(error_msg)
            print(f"⚠️ Warning: Could not load NationsManager: {error_msg}")
    except Exception as e:
        error_msg = f"NationsManager: Unexpected error: {str(e)}"
        setup_errors.append(error_msg)
        print(f"⚠️ Warning: Could not load NationsManager: {error_msg}")
    
    # Load Destroy cog
    try:
        from Systems.PnW.MA.destroy import DestroyCog
        await bot.add_cog(DestroyCog(bot))
        print("✅ Destroy System loaded successfully!")
    except ImportError as e:
        try:
            from destroy import DestroyCog
            await bot.add_cog(DestroyCog(bot))
            print("✅ Destroy System loaded successfully (direct import)!")
        except Exception as e2:
            error_msg = f"DestroyCog: MA import: {str(e)}, Direct import: {str(e2)}"
            setup_errors.append(error_msg)
            print(f"⚠️ Warning: Could not load DestroyCog: {error_msg}")
    except Exception as e:
        error_msg = f"DestroyCog: Unexpected error: {str(e)}"
        setup_errors.append(error_msg)
        print(f"⚠️ Warning: Could not load DestroyCog: {error_msg}")
    
    # Load main Military Affairs cog
    try:
        await bot.add_cog(MilitaryAffairs(bot))
        print("✅ Military Affairs System loaded successfully!")
    except Exception as e:
        error_msg = f"MilitaryAffairs: {str(e)}"
        setup_errors.append(error_msg)
        print(f"⚠️ Warning: Could not load MilitaryAffairs: {error_msg}")
    
    # Report overall setup status
    if setup_errors:
        print(f"\n⚠️ Setup completed with {len(setup_errors)} errors:")
        for error in setup_errors:
            print(f"  - {error}")
    else:
        print("\n✅ All MA systems loaded successfully!")
