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

# Add parent directories to sys.path for proper module resolution
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
grandparent_dir = os.path.dirname(parent_dir)

# Add necessary paths to sys.path
if grandparent_dir not in sys.path:
    sys.path.insert(0, grandparent_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import required dependencies first
try:
    from config import PANDW_API_KEY, CYBERTRON_ALLIANCE_ID, PRIME_BANK_ALLIANCE_ID, PRIMAL_USER_ID, ARIES_USER_ID, CARNAGE_USER_ID, BENEVOLENT_USER_ID, TECH_USER_ID, TECH_NATION_ID, get_role_ids
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Warning: Could not import config: {e}")
    CONFIG_AVAILABLE = False
    # Set dummy values for config imports
    PANDW_API_KEY = None
    CYBERTRON_ALLIANCE_ID = None
    PRIME_BANK_ALLIANCE_ID = None
    PRIMAL_USER_ID = None
    ARIES_USER_ID = None
    CARNAGE_USER_ID = None
    BENEVOLENT_USER_ID = None
    TECH_USER_ID = None
    TECH_NATION_ID = None
    get_role_ids = lambda: {}

try:
    from Systems.user_data_manager import UserDataManager
    USER_DATA_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Warning: Could not import UserDataManager: {e}")
    USER_DATA_MANAGER_AVAILABLE = False
    # Create a dummy UserDataManager class
    class UserDataManager:
        def __init__(self, *args, **kwargs):
            pass
        def get_user_data(self, *args, **kwargs):
            return {}
        def update_user_data(self, *args, **kwargs):
            return False

# MA Module imports with fallback logic
MA_IMPORTS = {
    'alliance_views': {
        'module': 'alliance',
        'items': ['AllianceTotalsView', 'FullMillView'],
        'globals': {}
    },
    'bloc_views': {
        'module': 'bloc',
        'items': ['BlocTotalsView'],
        'globals': {}
    },
    'blitz_views': {
        'module': 'blitz',
        'items': ['PartyView'],
        'globals': {}
    },
    'nations_views': {
        'module': 'blitz',
        'items': ['NationListView'],
        'globals': {}
    },
    'destroy_views': {
        'module': 'destroy',
        'items': ['OptimalAttackersView'],
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
    import os
    
    # Ensure MA directory is in sys.path
    ma_dir = os.path.join(os.path.dirname(__file__), 'MA')
    if ma_dir not in sys.path:
        sys.path.insert(0, ma_dir)
    
    for import_key, config in MA_IMPORTS.items():
        module_name = config['module']
        items = config['items']
        
        try:
            # Try direct import from MA subdirectory first (most reliable)
            try:
                # Use absolute import with proper path
                full_module_path = f"Systems.PnW.MA.{module_name}"
                module = importlib.import_module(full_module_path)
                
                for item in items:
                    if hasattr(module, item):
                        globals()[item] = getattr(module, item)
                        config['globals'][item] = getattr(module, item)
                        print(f"✅ Successfully imported {item} from {full_module_path}")
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
                        # If no package context, try direct import
                        module = importlib.import_module(module_name)
                    
                    for item in items:
                        if hasattr(module, item):
                            globals()[item] = getattr(module, item)
                            config['globals'][item] = getattr(module, item)
                            print(f"✅ Successfully imported {item} via relative import")
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
                    print(f"❌ Could not load {module_name} module: {str(e2)}")
                
        except Exception as e:
            # Handle unexpected errors
            for item in items:
                globals()[item] = None
                config['globals'][item] = None
            import_errors[import_key] = f"Unexpected error: {str(e)}"
            print(f"❌ Unexpected error loading {module_name} module: {str(e)}")

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
        
        await interaction.response.defer()

class TargetInputModal(discord.ui.Modal, title="⚔️ Find Optimal Attackers"):
    """Enhanced modal for inputting target nation information with type selection."""
    
    def __init__(self, author_id: int, bot: commands.Bot):
        super().__init__()
        self.author_id = author_id
        self.bot = bot
        self.selected_input_type = None
    
    target_input = discord.ui.TextInput(
        label="Target Information",
        placeholder="Enter nation name, leader name, ID, or link based on your selection above",
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
            
            # Find optimal attackers for the target
            optimal_attackers = await destroy_cog.find_optimal_attackers(target_nation)
            if 'error' in optimal_attackers:
                embed = discord.Embed(
                    title="❌ No Optimal Attackers Found",
                    description=f"Could not find optimal attackers for **{target_nation.get('nation_name', 'Unknown')}**.\n\nError: {optimal_attackers['error']}\n\nThis could be due to:\n• No alliance members within war range\n• Insufficient members with required unit coverage\n• No members with missile/nuke capability",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create the paginated view for optimal attackers
            optimal_view = destroy_cog.create_optimal_attackers_view(interaction, target_nation, optimal_attackers)
            
            # Create the initial embed (target info)
            initial_embed = optimal_view.create_target_embed()
            
            # Send the paginated view
            await interaction.followup.send(embed=initial_embed, view=optimal_view)
            
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
    
    @discord.ui.button(label="Find Attackers", style=discord.ButtonStyle.primary, emoji="⚔️")
    async def enter_target_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to open the target input modal."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You cannot use this button.")
            return
        
        # Check if input type was selected
        if not self.selected_input_type:
            await interaction.response.send_message(
                "❌ Please select an input type first using the dropdown above.",
                ephemeral=True
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
                label="Bloc Totals",
                description="View AERO bloc statistics and totals",
                emoji="🏛️",
                value="bloc_totals"
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
            elif self.values[0] == "bloc_totals":
                await self._show_bloc_totals(interaction)
            elif self.values[0] == "blitz_sort":
                await self._show_blitz_sort(interaction)
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
            
            # Fetch alliance data for both Cybertron and Prime Bank - first try cache, then populate if empty
            try:
                nations = await alliance_cog.get_alliance_nations(str(CYBERTRON_ALLIANCE_ID))
                prime_bank_nations = []
                
                # Also fetch Prime Bank alliance data if configured
                if PRIME_BANK_ALLIANCE_ID:
                    try:
                        prime_bank_nations = await alliance_cog.get_alliance_nations(str(PRIME_BANK_ALLIANCE_ID))
                        if not prime_bank_nations:
                            # Cache is empty, populate it using PNWAPIQuery
                            if PNWAPIQuery:
                                query_instance = PNWAPIQuery()
                                prime_bank_nations = await query_instance.get_alliance_nations(str(PRIME_BANK_ALLIANCE_ID), bot=self.bot, force_refresh=True)
                                
                                # Alliance data is now automatically cached in individual alliance files
                                # No manual cache management needed - QuerySystem handles this automatically
                                print(f"Retrieved Prime Bank alliance data: {len(prime_bank_nations)} nations")
                    except Exception as pb_error:
                        print(f"Error fetching Prime Bank alliance nations: {pb_error}")
                        prime_bank_nations = []  # Continue without Prime Bank data
                
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
                        print(f"Retrieved Cybertron alliance data: {len(nations)} nations")
                        
                        if not nations and not prime_bank_nations:
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
                
                # Combine both alliance data if Prime Bank data is available
                if prime_bank_nations:
                    nations = nations + prime_bank_nations
                    print(f"Combined alliance data: {len(nations)} total nations (Cybertron: {len(nations) - len(prime_bank_nations)}, Prime Bank: {len(prime_bank_nations)})")
                    
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
    
    async def _show_bloc_totals(self, interaction: discord.Interaction):
        """Show comprehensive AERO bloc statistics using BlocTotalsView."""
        try:
            # Check if BlocTotalsView is available
            if not BlocTotalsView:
                error_details = import_errors.get('bloc_views', 'Unknown import error')
                embed = discord.Embed(
                    title="❌ Bloc System Unavailable",
                    description=f"AERO Bloc Management System could not be loaded. Error: {error_details}",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Get the bloc manager cog for data fetching and view creation
            bloc_cog = self.bot.get_cog('BlocManager')
            if not bloc_cog:
                embed = discord.Embed(
                    title="❌ Bloc System Unavailable",
                    description="AERO Bloc Management System is not loaded.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Send loading message
            loading_embed = discord.Embed(
                title="⏳ Loading AERO Bloc Data",
                description="Loading bloc alliance data (using cached data when available)...",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=loading_embed)
            
            # Fetch all Eternal Accords alliance data
            try:
                # Get all bloc alliance data using the bloc manager
                bloc_data = await bloc_cog.fetch_all_bloc_data()
                
                if not bloc_data or not any(bloc_data.values()):
                    embed = discord.Embed(
                        title="❌ No Bloc Data",
                        description="Failed to retrieve Eternal Accords bloc data.",
                        color=discord.Color.red()
                    )
                    await interaction.edit_original_response(embed=embed)
                    return
                    
            except Exception as e:
                print(f"Error fetching bloc data: {e}")
                embed = discord.Embed(
                    title="❌ Bloc Data Error",
                    description=f"Failed to fetch Eternal Accords bloc data: {str(e)}",
                    color=discord.Color.red()
                )
                await interaction.edit_original_response(embed=embed)
                return
            
            # Create BlocTotalsView with navigation buttons
            view = BlocTotalsView(self.author_id, self.bot, bloc_cog, bloc_data)
            
            # Generate bloc totals embed for selected alliances
            embed = await view.generate_custom_bloc_embed(view.selected_alliances)
            
            # Send the Bloc Totals embed immediately with navigation buttons
            await interaction.edit_original_response(embed=embed, view=view)
            
        except Exception as e:
            print(f"Error showing bloc totals: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to load Eternal Accords bloc statistics: {str(e)}",
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
            
            nations = await self.blitz_cog.get_alliance_nations(str(self.blitz_cog.cybertron_alliance_id))
            prime_bank_nations = []
            
            if PRIME_BANK_ALLIANCE_ID:
                try:
                    prime_bank_nations = await self.blitz_cog.get_alliance_nations(str(PRIME_BANK_ALLIANCE_ID))
                    if not prime_bank_nations:
                        # Cache is empty, populate it using PNWAPIQuery
                        if PNWAPIQuery:
                            query_instance = PNWAPIQuery()
                            prime_bank_nations = await query_instance.get_alliance_nations(str(PRIME_BANK_ALLIANCE_ID), bot=self.bot)
                except Exception as pb_error:
                    print(f"Error fetching Prime Bank alliance nations for blitz: {pb_error}")
                    prime_bank_nations = []  # Continue without Prime Bank data
            
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
                    
                    if not nations and not prime_bank_nations:
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
            
            # Combine both alliance data if Prime Bank data is available
            if prime_bank_nations:
                nations = nations + prime_bank_nations
                print(f"Combined blitz alliance data: {len(nations)} total nations (Cybertron: {len(nations) - len(prime_bank_nations)}, Prime Bank: {len(prime_bank_nations)})")
            
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
            
            # Create and send the party view using the processed parties
            party_view = PartyView(party_info_display, self.blitz_cog)
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
            # Filter active nations using utility function instead of NationsManager cog
            def get_active_nations(nations):
                """Filter nations to exclude vacation mode and applicant members."""
                if not isinstance(nations, list):
                    return []
                
                active_nations = []
                for nation in nations:
                    if (isinstance(nation, dict) and
                        nation.get('vacation_mode_turns', 0) == 0 and
                        nation.get('alliance_position', '').strip().upper() != 'APPLICANT'):
                        active_nations.append(nation)
                
                return active_nations
            
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
            prime_bank_nations = []
            
            if alliance_cog and hasattr(alliance_cog, 'get_alliance_nations'):
                # Use the cached version from alliance_cog for Cybertron
                nations = await alliance_cog.get_alliance_nations(str(self.blitz_cog.cybertron_alliance_id))
                
                # Also fetch Prime Bank alliance data if configured
                if PRIME_BANK_ALLIANCE_ID:
                    try:
                        prime_bank_nations = await alliance_cog.get_alliance_nations(str(PRIME_BANK_ALLIANCE_ID))
                    except Exception as pb_error:
                        print(f"Error fetching Prime Bank alliance nations for view nations: {pb_error}")
                        prime_bank_nations = []  # Continue without Prime Bank data
            
            # Fallback to direct API query if alliance_cog not available or no cached data
            if not nations and PNWAPIQuery:
                # Create query instance and get fresh data
                query_instance = PNWAPIQuery()
                nations = await query_instance.get_alliance_nations(str(self.blitz_cog.cybertron_alliance_id), bot=self.bot)
                
                # Also fetch Prime Bank alliance data if configured
                if PRIME_BANK_ALLIANCE_ID and not prime_bank_nations:
                    try:
                        prime_bank_nations = await query_instance.get_alliance_nations(str(PRIME_BANK_ALLIANCE_ID), bot=self.bot)
                    except Exception as pb_error:
                        print(f"Error fetching Prime Bank alliance nations via API for view nations: {pb_error}")
                        prime_bank_nations = []  # Continue without Prime Bank data
                
                if not nations and not prime_bank_nations:
                    embed = discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data from API.",
                        color=discord.Color.red()
                    )
                    await interaction.edit_original_response(embed=embed)
                    return
            elif not nations and not prime_bank_nations:
                embed = discord.Embed(
                    title="❌ Query System Unavailable",
                    description="Cannot fetch alliance data - Query system not available.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Combine both alliance data if Prime Bank data is available
            if prime_bank_nations:
                if nations:
                    nations = nations + prime_bank_nations
                else:
                    nations = prime_bank_nations
                print(f"Combined view nations alliance data: {len(nations)} total nations (Cybertron: {len(nations) - len(prime_bank_nations)}, Prime Bank: {len(prime_bank_nations)})")
            
            # Update loading message to show data was retrieved
            await interaction.edit_original_response(embed=discord.Embed(
                title="✅ Alliance Data Retrieved",
                description=f"Successfully retrieved data for {len(nations)} nations.",
                color=discord.Color.green()
            ))
            
            # Filter out vacation mode and applicant nations
            active_nations = get_active_nations(nations)
            
            # Debug: Check what type of data we have
            print(f"Debug: nations type: {type(nations)}, length: {len(nations) if isinstance(nations, list) else 'N/A'}")
            if isinstance(nations, list) and len(nations) > 0:
                print(f"Debug: First nation type: {type(nations[0])}")
                if isinstance(nations[0], dict):
                    print(f"Debug: First nation keys: {list(nations[0].keys())[:5]}")
                else:
                    print(f"Debug: First nation content: {str(nations[0])[:100]}")
            
            print(f"Debug: active_nations type: {type(active_nations)}, length: {len(active_nations) if isinstance(active_nations, list) else 'N/A'}")
            if isinstance(active_nations, list) and len(active_nations) > 0:
                print(f"Debug: First active nation type: {type(active_nations[0])}")
            
            if not active_nations:
                embed = discord.Embed(
                    title="❌ No Active Nations",
                    description="No active nations found (all nations are either in vacation mode or applicants).",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Use NationListView to display the filtered nations in paginated format
            from Systems.PnW.MA.blitz import NationListView
            
            # Debug: Check the first few active nations
            if active_nations:
                print(f"Debug: First active nation keys: {list(active_nations[0].keys()) if isinstance(active_nations[0], dict) else 'Not a dict'}")
                print(f"Debug: First active nation sample data: {str(active_nations[0])[:200]}")
            
            nation_view = NationListView(active_nations, interaction.user.id, self.bot, self.blitz_cog)
            
            # Send the first page of nations
            try:
                first_embed = nation_view.create_embed()
                await interaction.followup.send(embed=first_embed, view=nation_view)
            except Exception as embed_error:
                print(f"Error creating nation embed: {embed_error}")
                print(f"Error type: {type(embed_error)}")
                import traceback
                traceback.print_exc()
                
                embed = discord.Embed(
                    title="❌ Error Creating Nation View",
                    description=f"Failed to create nation view: {str(embed_error)}",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
            
        except Exception as e:
            print(f"Error showing view nations: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to load nations overview: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    async def _show_destroy_opp(self, interaction: discord.Interaction):
        """Show destroy opposition functionality with enhanced target input selection."""
        try:
            # Create the target input view with dropdown selection
            view = TargetInputView(interaction.user.id, self.bot)
            await interaction.followup.send(content="🎯 **Destroy Opposition - Target Selection**", view=view)
            
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

    def ma_role_check():
        async def predicate(ctx):
            # Allow specific authorized users unconditionally
            authorized_users = [
                PRIMAL_USER_ID,
                ARIES_USER_ID,
                CARNAGE_USER_ID,
                BENEVOLENT_USER_ID,
                TECH_USER_ID,
            ]

            is_authorized = ctx.author.id in authorized_users

            # If in a guild, allow leadership roles: Predaking, IA, MG, HG
            if not is_authorized and ctx.guild:
                try:
                    role_map = get_role_ids(ctx.guild.id)
                except Exception:
                    role_map = {}

                leadership_roles = ["Predaking", "IA", "MG", "HG"]
                author_role_ids = {role.id for role in getattr(ctx.author, "roles", [])}

                for role_name in leadership_roles:
                    for role_id in role_map.get(role_name, []) or []:
                        if role_id in author_role_ids:
                            is_authorized = True
                            break
                    if is_authorized:
                        break

            return is_authorized

        return commands.check(predicate) 

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
                           "* Comprehensive breakdown of Members, Military, Improvements and Projects.\n"
                           "🏛️ **Bloc Totals** - View AERO bloc statistics and totals\n"
                           "* Comprehensive breakdown of ALL Alliances; Members, Military, Improvements and Projects.\n"
                           "👁️ **View Nations** - View all active nations with their capabilities\n"
                           "* View *Active Members* and their Military Capabilities.\n"
                           "  * Excludes *Applicants* & *Vacation Mode* nations.\n"
                           "🤖 **Blitz Party Sort** - Generate strategically balanced blitz parties\n"
                           "* Sorts *Active Members* into optimal war parties of 3.\n"
                           "  * Excludes *Applicants* & *Vacation Mode* nations.\n"
                           "🎯 **Destroy Opp** - Find optimal blitz parties to attack a target nation.\n"
                           "* You will be promted to imput *Nation Name, Leader Name, Nation ID* or Link\n"
                           "📣 **Mass Recruit** - Mass Recruit EVERY unallied nation who is less than 14 days inactive\n"
                           "* (May take a moment to show, it's querying 15,000 nations!)\n"
                           "* Buttons 🟢🟡🟠 for *Activity Based* Recruitment\n",
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

    @commands.hybrid_command(name='refresh_alliance', description='Force refresh alliance data')
    @ma_role_check()
    async def refresh_alliance(self, ctx: commands.Context):
        """Force refresh alliance data cache."""
        try:
            # Defer response
            await ctx.defer()
            alliance_cog = self.bot.get_cog('AllianceManager')
            if not alliance_cog:
                await ctx.send("❌ AllianceManager is not loaded.")
                return
            nations = await alliance_cog.get_alliance_nations(CYBERTRON_ALLIANCE_ID, force_refresh=True)
            
            # Also refresh Prime Bank alliance data if configured
            if PRIME_BANK_ALLIANCE_ID:
                try:
                    prime_bank_nations = await alliance_cog.get_alliance_nations(str(PRIME_BANK_ALLIANCE_ID), force_refresh=True)
                    print(f"✅ Prime Bank alliance cache refreshed with {len(prime_bank_nations)} nations.")
                except Exception as pb_error:
                    print(f"⚠️ Warning: Could not refresh Prime Bank alliance cache: {pb_error}")
            if not nations:
                await ctx.send("❌ Failed to refresh alliance data.")
                return
            
            await ctx.send(f"✅ Alliance cache cleared and refreshed with {len(nations)} nations.")
            
        except Exception as e:
            self.logger.error(f"Error in refresh_alliance command: {e}")
            self.logger.error(traceback.format_exc())
            await ctx.send(f"❌ An error occurred: {str(e)}")

async def setup(bot: commands.Bot):
    """Setup function for loading the cog with comprehensive error handling."""
    setup_errors = []
    try:
        from Systems.PnW.MA.alliance import AllianceManager
        await bot.add_cog(AllianceManager(bot))
        print("✅ Alliance Management System loaded successfully!")
    except ImportError as e:
        try:
            from .MA.alliance import AllianceManager
            await bot.add_cog(AllianceManager(bot))
            print("✅ Alliance Management System loaded successfully (relative import)!")
        except Exception as e2:
            error_msg = f"AllianceManager: MA import: {str(e)}, Relative import: {str(e2)}"
            setup_errors.append(error_msg)
            print(f"⚠️ Warning: Could not load AllianceManager: {error_msg}")
    except Exception as e:
        error_msg = f"AllianceManager: Unexpected error: {str(e)}"
        setup_errors.append(error_msg)
        print(f"⚠️ Warning: Could not load AllianceManager: {error_msg}")
    try:
        from Systems.PnW.MA.blitz import BlitzParties
        await bot.add_cog(BlitzParties(bot))
        print("✅ Blitz Parties System loaded successfully!")
    except ImportError as e:
        try:
            from .MA.blitz import BlitzParties
            await bot.add_cog(BlitzParties(bot))
            print("✅ Blitz Parties System loaded successfully (relative import)!")
        except Exception as e2:
            error_msg = f"BlitzParties: MA import: {str(e)}, Relative import: {str(e2)}"
            setup_errors.append(error_msg)
            print(f"⚠️ Warning: Could not load BlitzParties: {error_msg}")
    except Exception as e:
        error_msg = f"BlitzParties: Unexpected error: {str(e)}"
        setup_errors.append(error_msg)
        print(f"⚠️ Warning: Could not load BlitzParties: {error_msg}")
    try:
        from Systems.PnW.MA.destroy import DestroyCog
        await bot.add_cog(DestroyCog(bot))
        print("✅ Destroy System loaded successfully!")
    except ImportError as e:
        try:
            from .MA.destroy import DestroyCog
            await bot.add_cog(DestroyCog(bot))
            print("✅ Destroy System loaded successfully (relative import)!")
        except Exception as e2:
            error_msg = f"DestroyCog: MA import: {str(e)}, Relative import: {str(e2)}"
            setup_errors.append(error_msg)
            print(f"⚠️ Warning: Could not load DestroyCog: {error_msg}")
    except Exception as e:
        error_msg = f"DestroyCog: Unexpected error: {str(e)}"
        setup_errors.append(error_msg)
        print(f"⚠️ Warning: Could not load DestroyCog: {error_msg}")
    try:
        await bot.add_cog(MilitaryAffairs(bot))
        print("✅ Military Affairs System loaded successfully!")
    except Exception as e:
        error_msg = f"MilitaryAffairs: {str(e)}"
        setup_errors.append(error_msg)
        print(f"⚠️ Warning: Could not load MilitaryAffairs: {error_msg}")
    try:
        from Systems.PnW.MA.bloc import BlocManager
        await bot.add_cog(BlocManager(bot))
        print("✅ Eternal Accords Bloc Management System loaded successfully!")
    except ImportError as e:
        try:
            from .MA.bloc import BlocManager
            await bot.add_cog(BlocManager(bot))
            print("✅ Eternal Accords Bloc Management System loaded successfully (relative import)!")
        except Exception as e2:
            error_msg = f"BlocManager: MA import: {str(e)}, Relative import: {str(e2)}"
            setup_errors.append(error_msg)
            print(f"⚠️ Warning: Could not load BlocManager: {error_msg}")
    except Exception as e:
        error_msg = f"BlocManager: Unexpected error: {str(e)}"
        setup_errors.append(error_msg)
        print(f"⚠️ Warning: Could not load BlocManager: {error_msg}")
    if setup_errors:
        print(f"\n⚠️ Setup completed with {len(setup_errors)} errors:")
        for error in setup_errors:
            print(f"  - {error}")
    else:
        print("\n✅ All MA systems loaded successfully!")