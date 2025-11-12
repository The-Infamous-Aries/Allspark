
import discord
from discord.ext import commands
import requests
import json
import os
from collections import defaultdict
from typing import List, Dict, Optional, Any
import asyncio
from datetime import datetime
import sys
import random
import logging
import traceback
import time
from pathlib import Path
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
try:
    from .query import create_query_instance
except ImportError:
    try:
        from Systems.PnW.MA.query import create_query_instance
    except ImportError:
        create_query_instance = None

# Import AERO_ALLIANCES and leadership role check
try:
    from .bloc import AERO_ALLIANCES
except ImportError:
    try:
        from Systems.PnW.MA.bloc import AERO_ALLIANCES
    except ImportError:
        AERO_ALLIANCES = {}

try:
    from Systems.PnW.snipe import leadership_role_check
except Exception:
    try:
        from snipe import leadership_role_check
    except Exception:
        def leadership_role_check():
            return commands.check(lambda ctx: True)

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))

# Add the project root to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Also add the current directory in case config is there
current_dir_parent = os.path.dirname(current_dir)
if current_dir_parent not in sys.path:
    sys.path.insert(0, current_dir_parent)

try:
    from config import PANDW_API_KEY, CYBERTRON_ALLIANCE_ID, PRIME_BANK_ALLIANCE_ID, ARIES_NATION_ID, CARNAGE_NATION_ID, PRIMAL_NATION_ID, TECH_NATION_ID, BENEVOLENT_NATION_ID
except ImportError as e:
    print(f"Failed to import config: {e}")
    print(f"Python path: {sys.path}")
    print(f"Current directory: {current_dir}")
    print(f"Project root: {project_root}")
    raise
from Systems.user_data_manager import UserDataManager
from .sorter import BlitzPartySorter
from .calc import AllianceCalculator

class NationListView(discord.ui.View):
    def __init__(self, nations: List[Dict[str, Any]], author_id: int, bot: commands.Bot, blitz_cog):
        super().__init__(timeout=300) 
        
        # Validate nations input
        if not isinstance(nations, list):
            print(f"Warning: NationListView received non-list nations: {type(nations)}")
            nations = []
        
        # Filter out any non-dictionary items and validate each nation
        valid_nations = []
        for i, nation in enumerate(nations):
            if isinstance(nation, dict):
                valid_nations.append(nation)
            else:
                print(f"Warning: Skipping non-dictionary nation at index {i}: {type(nation)} - {str(nation)[:100]}")
        # Enforce alliance-only view: Cybertron or Prime Banking
        try:
            allowed_ids = {str(CYBERTRON_ALLIANCE_ID)}
            if 'PRIME_BANK_ALLIANCE_ID' in globals() and PRIME_BANK_ALLIANCE_ID:
                allowed_ids.add(str(PRIME_BANK_ALLIANCE_ID))
            valid_nations = [n for n in valid_nations if str(n.get('alliance_id')) in allowed_ids]
            # Further restrict to Members only (exclude applicants)
            def _is_member(n: Dict[str, Any]) -> bool:
                pos = str(n.get('alliance_position', '') or '').lower()
                return pos == 'member'
            def _not_in_vacation(n: Dict[str, Any]) -> bool:
                try:
                    turns = n.get('vacation_mode_turns', 0)
                    turns_val = int(turns) if isinstance(turns, (int, str)) and str(turns).isdigit() else (turns or 0)
                except Exception:
                    turns_val = 0
                return (turns_val or 0) == 0
            valid_nations = [n for n in valid_nations if _is_member(n) and _not_in_vacation(n)]
        except Exception as e:
            print(f"Warning: Failed to filter nations by alliance: {e}")

        self.nations = valid_nations
        self.current_page = 0
        self.author_id = author_id
        self.bot = bot
        self.blitz_cog = blitz_cog
        self.nations_per_page = 1  # Changed to 1 nation per page for comprehensive view
        
        # Safe sorting with error handling
        try:
            self.nations.sort(key=lambda n: n.get('score', 0) if isinstance(n, dict) else 0, reverse=True)
        except Exception as e:
            print(f"Warning: Error sorting nations: {e}")
        
        self.total_pages = max(1, (len(self.nations) + self.nations_per_page - 1) // self.nations_per_page)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensures only the person who triggered the command can use the buttons."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("⚠️ Only the command initiator can use these buttons!")
            return False
        return True

    def _format_last_active_time(self, last_active_str: str) -> str:
        if not last_active_str or last_active_str == 'Unknown':
            return 'Unknown'        
        try:
            from datetime import datetime, timezone
            last_active_dt = datetime.fromisoformat(last_active_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            diff = now - last_active_dt
            total_days = diff.days
            months = total_days // 30
            remaining_days = total_days % 30
            weeks = remaining_days // 7
            days = remaining_days % 7
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            parts = []       
            if months > 0:
                parts.append(f"{months} month{'s' if months != 1 else ''}")           
            if weeks > 0:
                parts.append(f"{weeks} week{'s' if weeks != 1 else ''}")            
            if days > 0:
                parts.append(f"{days} day{'s' if days != 1 else ''}")           
            if hours > 0 and not months and not weeks: 
                parts.append(f"{hours} hour{'s' if hours != 1 else ''}")           
            if minutes > 0 and not months and not weeks and not days: 
                parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")           
            if not parts: 
                return "Just now"            
            return " ".join(parts)            
        except (ValueError, AttributeError):
            return last_active_str

    def calculate_nation_improvements(self, nation: Dict[str, Any]) -> Dict[str, int]:
        """Calculate improvements data for a single nation by summing up all city improvements."""
        improvements = {
            'coalpower': 0,
            'oilpower': 0,
            'nuclearpower': 0,
            'windpower': 0,
        }
        
        cities = nation.get('cities', [])
        for city in cities:
            if not isinstance(city, dict):
                continue
                
            # Sum up power plant improvements from each city
            improvements['coalpower'] += city.get('coal_power', 0) or 0
            improvements['oilpower'] += city.get('oil_power', 0) or 0
            improvements['nuclearpower'] += city.get('nuclear_power', 0) or 0
            improvements['windpower'] += city.get('wind_power', 0) or 0
        
        return improvements

    def create_comprehensive_nation_embed(self, nation: Dict[str, Any]) -> discord.Embed:
        # Validate nation input
        if not isinstance(nation, dict):
            embed = discord.Embed(
                title="⚠️ Invalid Nation Data",
                description=f"Expected dictionary for nation, got {type(nation).__name__}: {str(nation)[:100]}",
                color=discord.Color.red()
            )
            return embed
        
        nation_name = nation.get('nation_name', 'Unknown Nation')
        leader_name = nation.get('leader_name', 'Unknown Leader')
        nation_id = nation.get('id')
        vacation_turns = nation.get('vacation_mode_turns', 0)
        beige_turns = nation.get('beige_turns', 0)
        last_active_raw = nation.get('last_active', 'Unknown')
        last_active = self._format_last_active_time(last_active_raw)
        safe_spies = nation.get('spies', 0) or 0
        safe_ground_capacity = nation.get('ground_capacity') or 0
        safe_air_capacity = nation.get('air_capacity') or 0
        safe_naval_capacity = nation.get('naval_capacity') or 0
        safe_ground_cost = nation.get('ground_cost') or 0
        safe_air_cost = nation.get('air_cost') or 0
        safe_naval_cost = nation.get('naval_cost') or 0
        wars_won = nation.get('wars_won', 0)
        wars_lost = nation.get('wars_lost', 0)
        total_wars = wars_won + wars_lost
        war_ratio = (wars_won / total_wars * 100) if total_wars > 0 else 0
        safe_money_looted = nation.get('money_looted') or 0
        safe_money = nation.get('money', 0) or 0
        safe_credits = nation.get('credits', 0) or 0
        nation_improvements = self.calculate_nation_improvements(nation)
        safe_coalpower = nation_improvements['coalpower']
        safe_oilpower = nation_improvements['oilpower']
        safe_windpower = nation_improvements['windpower']
        safe_nuclearpower = nation_improvements['nuclearpower']
        safe_gasoline = nation.get('gasoline', 0) or 0
        safe_munitions = nation.get('munitions', 0) or 0
        safe_steel = nation.get('steel', 0) or 0
        safe_aluminum = nation.get('aluminum', 0) or 0
        safe_food = nation.get('food', 0) or 0
        safe_coal = nation.get('coal', 0) or 0
        safe_oil = nation.get('oil', 0) or 0
        safe_uranium = nation.get('uranium', 0) or 0
        safe_iron = nation.get('iron', 0) or 0
        safe_bauxite = nation.get('bauxite', 0) or 0
        safe_lead = nation.get('lead', 0) or 0
        building_ratios = self.blitz_cog.calculator.calculate_building_ratios(nation) or {}
        mmr_string = building_ratios.get('mmr_string', 'Unknown')
        cities = nation.get('cities', [])
        flag_url = nation.get('flag')
        total_infra = 0
        avg_city_infra = 0
        powered_cities = 0
        infra_tier = 'Unknown'
        if cities:
            total_infra = sum((city.get('infrastructure', 0) or 0) for city in cities if isinstance(city, dict))
            avg_city_infra = total_infra / len(cities) if cities else 0
            powered_cities = sum(1 for city in cities if isinstance(city, dict) and city.get('powered', False))
            infra_tier = self.blitz_cog.calculator._get_infrastructure_tier(avg_city_infra)

        embed = discord.Embed(
            title=f"🏛️ {nation_name}",
            description=f"**Leader:** {leader_name}",
            color=discord.Color.from_rgb(0, 150, 255)
        )
        if nation_id:
            embed.url = f"https://politicsandwar.com/nation/id={nation_id}"
            if flag_url:
                embed.set_thumbnail(url=flag_url)
            else:
                embed.set_thumbnail(url=f"https://politicsandwar.com/nation/id={nation_id}/image")
        discord_info = ""
        discord_username = nation.get('discord_username')
        if discord_username:
            discord_info = discord_username
        elif nation.get('discord_id'):
            discord_info = f"<@{nation.get('discord_id')}>"
        else:
            discord_info = "Not linked"
        turns_since_city = nation.get('turns_since_last_city', 0)
        turns_since_project = nation.get('turns_since_last_project', 0)
        city_cooldown_remaining = max(0, 120 - turns_since_city)
        project_cooldown_remaining = max(0, 120 - turns_since_project)       
        city_status = "✅ Available" if city_cooldown_remaining == 0 else f"❌ {city_cooldown_remaining} turns"
        project_status = "✅ Available" if project_cooldown_remaining == 0 else f"❌ {project_cooldown_remaining} turns"

        basic_stats = (
            f"**Position:** {nation.get('alliance_position', 'Unknown').title()}\n"
            f"**Vacation Mode:** {'Yes' if vacation_turns > 0 else 'No'}\n"
            f"**Color:** {nation.get('color', 'Unknown')}\n"
            f"{'**Beige Turns:** ' + str(beige_turns) + chr(10) if nation.get('color', '').lower() == 'beige' else ''}"
            f"**Discord:** {discord_info}\n"
            f"**Last Active:** {last_active}\n"
            f"**New Project:** {project_status}\n"            
            f"**New City:** {city_status}\n"
            f"**Cities:** {nation.get('num_cities', 0)}\n"
            f"**Powered Cities:** {powered_cities}/{len(cities)}\n"
            f"**Infra Tier:** {infra_tier}\n"
            f"**Total Infrastructure:** {total_infra:,.0f}\n"
            f"**Avg Infrastructure/City:** {avg_city_infra:,.0f}\n"
            f"**Domestic Policy:** {nation.get('domestic_policy', 'Unknown')}"
        )
        embed.add_field(name="📊 Basic Statistics", value=basic_stats, inline=False)
        
        resources_and_materials = (
            f"**Money:** ${safe_money:,}\n"
            f"**Credits:** {safe_credits:,}\n"
            f"**Gasoline:** {safe_gasoline:,}\n"
            f"**Munitions:** {safe_munitions:,}\n"
            f"**Steel:** {safe_steel:,}\n"
            f"**Aluminum:** {safe_aluminum:,}\n"
            f"**Food:** {safe_food:,}\n"
            f"**Coal:** {safe_coal:,}\n"
            f"**Oil:** {safe_oil:,}\n"
            f"**Uranium:** {safe_uranium:,}\n"
            f"**Iron:** {safe_iron:,}\n"
            f"**Bauxite:** {safe_bauxite:,}\n"
            f"**Lead:** {safe_lead:,}"
        )
        embed.add_field(name="Current Resources", value=resources_and_materials, inline=False)

        specializations = []
        nation_id = nation.get('nation_id') or nation.get('id', '')
        if not nation_id:
            print(f"Warning: Nation '{nation_name}' (leader: {leader_name}) has no ID field")
        else:
            nation_id_str = str(nation_id)
            print(f"Debug: Nation '{nation_name}' has ID: {nation_id_str}")   
        if self.blitz_cog.calculator.has_project(nation, 'Missile Launch Pad'):
            specializations.append(f"🚀 Missile")
        if self.blitz_cog.calculator.has_project(nation, 'Nuclear Research Facility'):
            specializations.append(f"☢️ Nuke")
        if nation_id and str(nation_id) == str(ARIES_NATION_ID):  # ARIES
            specializations.append("🪓 Psycho")        
        if nation_id and str(nation_id) == str(CARNAGE_NATION_ID):  # CARNAGE
            specializations.append("💀 Scary")       
        if nation_id and str(nation_id) == str(PRIMAL_NATION_ID):  # PRIMAL
            specializations.append("👑 Primal")
        if nation_id and str(nation_id) == str(TECH_NATION_ID):  # TECH
            specializations.append("🧑‍⚖️ Judge")
        if nation_id and str(nation_id) == str(BENEVOLENT_NATION_ID):  # BENEVOLENT
            specializations.append("👔 Professional")
        if safe_money_looted >= 2_500_000_000:
            specializations.append("🏴‍☠️ Taxman")
        elif safe_money_looted >= 1_000_000_000:
            specializations.append("🏴 Pirate")
        elif safe_money_looted >= 750_000_000:
            specializations.append("☠️ Pillager")
        elif safe_money_looted >= 500_000_000:
            specializations.append("💀 Bandit")
        elif safe_money_looted >= 250_000_000:
            specializations.append("💰 Thief")
        elif safe_money_looted >= 100_000_000:
            specializations.append("💳 Scammer")
        if wars_won >= 500:
            specializations.append("🪦 Reaper")
        elif wars_won >= 250:
            specializations.append("⚰️ Murderer")
        elif wars_won >= 100:
            specializations.append("⚱️ Fighter")
        if safe_credits >= 5:
            specializations.append("🧠 Planner")
        elif safe_credits >= 1:
            specializations.append("🤔 Thinker")
        if safe_spies >= 60:
            specializations.append("🥷 Shadow")
        commendations = nation.get('commendations', 0)
        if commendations >= 500:
            specializations.append("🙇 Worshipped")
        elif commendations >= 200:
            specializations.append("🦸 Idolized")
        elif commendations >= 100:
            specializations.append("❤️ Loved")
        elif commendations >= 50:
            specializations.append("👍 Liked")
        denouncements = nation.get('denouncements', 0)
        if denouncements >= 500:
            specializations.append("🖕 Despised")
        elif denouncements >= 200:
            specializations.append("🦹 Nemesis")
        elif denouncements >= 100:
            specializations.append("💔 Hated")
        elif denouncements >= 50:
            specializations.append("👎 Disliked")
        military_analysis = self.blitz_cog.calculator.calculate_military_advantage(nation)
        if military_analysis:
            is_special_nation = (
                (nation_id and str(nation_id) == str(ARIES_NATION_ID)) or
                (nation_id and str(nation_id) == str(CARNAGE_NATION_ID)) or
                (nation_id and str(nation_id) == str(PRIMAL_NATION_ID)) or
                (nation_id and str(nation_id) == str(TECH_NATION_ID)) or
                (nation_id and str(nation_id) == str(BENEVOLENT_NATION_ID))
            )       
            if is_special_nation:
                military_composition = military_analysis.get('military_composition', {})
                if military_composition.get('high_ground_purchase', False):
                    specializations.append("🪖 Ground")  
                if military_composition.get('high_air_purchase', False):
                    specializations.append("✈️ Air")
                if military_composition.get('high_naval_purchase', False):
                    specializations.append("🚢 Naval")
            else:
                if military_analysis.get('has_ground_advantage', False):
                    specializations.append("🪖 Ground")
                if military_analysis.get('has_air_advantage', False):
                    specializations.append("✈️ Air")
                if military_analysis.get('has_naval_advantage', False):
                    specializations.append("🚢 Naval")
        specialization_text = "\n".join(specializations) if specializations else "⚔️ Standard"
        embed.add_field(name="⚜️ Specializations", value=specialization_text, inline=False)

        military_info = (
            f"**War Policy:** {nation.get('war_policy', 'Unknown')}\n"
            f"**Score:** {nation.get('score', 0):,}\n"
            f"**MMR:** {building_ratios['mmr_string']}\n"
            f"**Espionage Available:** {'✅ Yes' if nation.get('espionage_available', False) else '❌ No'}\n"
            f"**Money Looted:** ${safe_money_looted:,}\n"
            f"**Wars Won:** {wars_won}\n"
            f"**Wars Lost:** {wars_lost}\n"
            f"**Win Rate:** {war_ratio:.1f}%\n"
            f"**Ground Capacity:** {safe_ground_capacity:,}\n"
            f"**Air Capacity:** {safe_air_capacity:,}\n"
            f"**Naval Capacity:** {safe_naval_capacity:,}\n"
            f"**Ground Cost:** {safe_ground_cost:,}\n"
            f"**Air Cost:** {safe_air_cost:,}\n"
            f"**Naval Cost:** {safe_naval_cost:,}"
        )
        embed.add_field(name="⚔️ War Stats", value=military_info, inline=False)
    
        project_categories = {
            '⚔️ War': [
                ('Advanced Pirate Economy', 'advanced_pirate_economy'),
                ('Central Intelligence Agency', 'central_intelligence_agency'),
                ('Fallout Shelter', 'fallout_shelter'),
                ('Guiding Satellite', 'guiding_satellite'),
                ('Iron Dome', 'iron_dome'),
                ('Military Doctrine', 'military_doctrine'),
                ('Military Research Center', 'military_research_center'),
                ('Military Salvage', 'military_salvage'),
                ('Missile Launch Pad', 'missile_launch_pad'),
                ('Nuclear Launch Facility', 'nuclear_launch_facility'),
                ('Nuclear Research Facility', 'nuclear_research_facility'),
                ('Pirate Economy', 'pirate_economy'),
                ('Propaganda Bureau', 'propaganda_bureau'),
                ('Space Program', 'space_program'),
                ('Spy Satellite', 'spy_satellite'),
                ('Surveillance Network', 'surveillance_network'),
                ('Vital Defense System', 'vital_defense_system')
            ],
            '🏭 Industry': [
                ('Arms Stockpile', 'arms_stockpile'),
                ('Bauxite Works', 'bauxite_works'),
                ('Clinical Research Center', 'clinical_research_center'),
                ('Emergency Gasoline Reserve', 'emergency_gasoline_reserve'),
                ('Green Technologies', 'green_technologies'),
                ('International Trade Center', 'international_trade_center'),
                ('Iron Works', 'iron_works'),
                ('Mass Irrigation', 'mass_irrigation'),
                ('Recycling Initiative', 'recycling_initiative'),
                ('Specialized Police Training Program', 'specialized_police_training_program'),
                ('Telecommunications Satellite', 'telecommunications_satellite'),
                ('Uranium Enrichment Program', 'uranium_enrichment_program')
            ],
            '🏛️ Government': [
                ('Activity Center', 'activity_center'),
                ('Advanced Engineering Corps', 'advanced_engineering_corps'),
                ('Arable Land Agency', 'arable_land_agency'),
                ('Bureau of Domestic Affairs', 'bureau_of_domestic_affairs'),
                ('Center Civil Engineering', 'center_for_civil_engineering'),
                ('Government Support Agency', 'government_support_agency'),
                ('Research & Development Center', 'research_and_development_center')
            ],
            '👽 Alien': [
                ('Mars Landing', 'mars_landing'),
                ('Moon Landing', 'moon_landing')
            ]
        }
        
        strategic_parts = []
        for category_key, projects in project_categories.items():
            category_projects = []
            for project_name, field_name in projects:
                if self.blitz_cog.calculator.has_project(nation, project_name):
                    initials = ''.join(word[0] for word in project_name.split())
                    category_projects.append(initials)
            
            if category_projects:
                projects_str = ', '.join(category_projects)
                category_mapping = {'⚔️': 'War', '🏭': 'Industry', '🏛️': 'Government', '👽': 'Alien'}
                category_emoji = category_key.split()[0] if ' ' in category_key else category_key
                category_name = category_mapping.get(category_emoji, 'Unknown')
                strategic_parts.append(f"**{category_name}:**\n{projects_str}")
        
        strategic_text = "\n".join(strategic_parts) if strategic_parts else "❌ None"
        embed.add_field(name="🏗️ Strategic Projects", value=strategic_text, inline=False)

        embed.set_footer(
            text=f"Nation {self.current_page + 1} of {self.total_pages} | Generated at {datetime.now().strftime('%H:%M:%S')}"
        )
            
        return embed

    def create_embed(self) -> discord.Embed:
        """Creates the embed for the current page of nations."""
        try:
            if not self.nations:
                embed = discord.Embed(
                    title="⚠️ No Nations Found",
                    description="No alliance nations could be retrieved.",
                    color=discord.Color.red()
                )
                return embed
            
            # Validate nations data
            if not isinstance(self.nations, list):
                embed = discord.Embed(
                    title="⚠️ Invalid Data Format",
                    description=f"Expected list of nations, got {type(self.nations).__name__}",
                    color=discord.Color.red()
                )
                return embed
            
            # Get the single nation for this page
            start_idx = self.current_page * self.nations_per_page
            
            # Check bounds
            if start_idx >= len(self.nations):
                embed = discord.Embed(
                    title="⚠️ Page Out of Range",
                    description=f"Page {self.current_page + 1} exceeds available nations ({len(self.nations)})",
                    color=discord.Color.red()
                )
                return embed
            
            nation = self.nations[start_idx]
            
            # Validate that nation is a dictionary
            if not isinstance(nation, dict):
                embed = discord.Embed(
                    title="⚠️ Invalid Nation Data",
                    description=f"Expected dictionary for nation at index {start_idx}, got {type(nation).__name__}: {str(nation)[:100]}",
                    color=discord.Color.red()
                )
                return embed
            
            # Create comprehensive nation breakdown
            return self.create_comprehensive_nation_embed(nation)
        except Exception as e:
            print(f"Error creating nation embed: {e}")
            print(f"Error type: {type(e)}")
            print(f"Error details: {str(e)}")
            import traceback
            traceback.print_exc()
            
            embed = discord.Embed(
                title="⚠️ Error Creating Nation Embed",
                description=f"Failed to create nation embed: {str(e)}",
                color=discord.Color.red()
            )
            return embed

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.secondary, disabled=True)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)      
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)       
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Military", style=discord.ButtonStyle.secondary, emoji="🏭")
    async def military_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show military analysis for the current nation."""
        try:
            await interaction.response.defer()
            
            if not self.nations or self.current_page >= len(self.nations):
                embed = discord.Embed(
                    title="❌ No Nation Data",
                    description="No nation data available.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            current_nation = self.nations[self.current_page]
            view = NationMilitaryView(self.author_id, self.bot, self.blitz_cog, current_nation)
            embed = await view.generate_nation_military_embed()
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
            
        except Exception as e:
            self.blitz_cog._log_error(f"Error in military_button: {e}", e, "NationListView.military_button")
            embed = discord.Embed(
                title="❌ Military Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    @discord.ui.button(label="Improvements", style=discord.ButtonStyle.secondary, emoji="🏗️")
    async def improvements_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show improvements breakdown for the current nation."""
        try:
            await interaction.response.defer()
            
            if not self.nations or self.current_page >= len(self.nations):
                embed = discord.Embed(
                    title="❌ No Nation Data",
                    description="No nation data available.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            current_nation = self.nations[self.current_page]
            view = NationImprovementsView(self.author_id, self.bot, self.blitz_cog, current_nation)
            embed = await view.generate_nation_improvements_embed()
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
            
        except Exception as e:
            self.blitz_cog._log_error(f"Error in improvements_button: {e}", e, "NationListView.improvements_button")
            embed = discord.Embed(
                title="❌ Improvements Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    async def on_timeout(self):
        """Called when the view times out."""
        for item in self.children:
            item.disabled = True

class PartyView(discord.ui.View):
    def __init__(self, parties: List[Dict], blitz_cog):
        super().__init__(timeout=300)
        self.parties = parties
        self.current_page = 0
        self.blitz_cog = blitz_cog
        self.total_pages = len(parties)
        if self.total_pages <= 1:
            self.previous_button.disabled = True
            self.next_button.disabled = True
        else:
            self.next_button.disabled = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensures only the person who triggered the command can use the buttons."""
        return True

    def create_embed(self) -> discord.Embed:
        """Creates the embed for the current party using simplified sorting calculations."""
        if not self.parties:
            embed = discord.Embed(
                title="⚠️ No Blitz Parties Generated",
                description="No valid parties could be created with the current alliance data.",
                color=discord.Color.red()
            )
            return embed
        party = self.parties[self.current_page]
        if isinstance(party, list):
            party_members = party
            party_name = f"Party {self.current_page + 1}"
            total_score = sum(member.get('score', 0) for member in party_members)
            member_count = len(party_members)
            avg_score = total_score / member_count if member_count > 0 else 0
            strategic_count = sum(1 for member in party_members if member.get('has_strategic', False))
            war_range_data = self.blitz_cog.calculate_party_war_range(party_members)
            if not isinstance(war_range_data, dict):
                overlapping_min = overlapping_max = war_avg = 0
                has_overlap = False
            else:
                overlapping_min = war_range_data.get('overlapping_min', 0)
                overlapping_max = war_range_data.get('overlapping_max', 0)
                war_avg = war_range_data.get('avg_score', avg_score)
                has_overlap = war_range_data.get('has_overlap', False)
        elif isinstance(party, dict):
            party_members = party.get('members', [])
            party_name = party.get('party_name', f"Party {self.current_page + 1}")
            total_score = party.get('total_score', sum(member.get('score', 0) for member in party_members))
            member_count = party.get('member_count', len(party_members))
            avg_score = total_score / member_count if member_count > 0 else 0
            strategic_count = party.get('strategic_count', sum(1 for member in party_members if member.get('has_strategic', False)))
            attack_range = party.get('attack_range', {})
            # Use correct keys for war range data
            overlapping_min = attack_range.get('overlapping_min', 0)
            overlapping_max = attack_range.get('overlapping_max', 0)
            war_avg = attack_range.get('avg_score', avg_score)
            has_overlap = attack_range.get('has_overlap', False)
        else:
            party_members = []
            party_name = f"Party {self.current_page + 1}"
            total_score = 0
            member_count = 0
            avg_score = 0
            strategic_count = 0
            overlapping_min = overlapping_max = war_avg = 0
            has_overlap = False
            party_avg_infra = 0
            military_advantage = 0      
        
        # Calculate infrastructure and military statistics
        total_infra = 0
        total_advantage_score = 0
        for member in party_members:
            member_infra_stats = self.blitz_cog.calculator.calculate_infrastructure_stats(member)
            total_infra += member_infra_stats.get('average_infrastructure', 0)
            member_advantages = self.blitz_cog.calculator.calculate_military_advantage(member)
            # Calculate advantage score based on number of advantages (0-5 max: Ground, Air, Naval, Missile, Nuke)
            advantage_count = len(member_advantages.get('advantages', []))
            total_advantage_score += advantage_count
        party_avg_infra = total_infra / len(party_members) if party_members else 0
        military_advantage = total_advantage_score / len(party_members) if party_members else 0
        
        # Calculate military specializations for the party
        missile_count = 0
        nuke_count = 0
        ground_advantage_count = 0
        air_advantage_count = 0
        naval_advantage_count = 0
        psycho_count = 0
        scary_count = 0
        primal_count = 0
        
        for member in party_members:
            member_advantages = self.blitz_cog.calculator.calculate_military_advantage(member)
            advantages = member_advantages.get('advantages', [])
            military_composition = member_advantages.get('military_composition', {})
            
            if 'Missile Capable' in advantages:
                missile_count += 1
            if 'Nuclear Capable' in advantages:
                nuke_count += 1
            if 'Ground Advantage' in advantages:
                ground_advantage_count += 1
            if 'Air Advantage' in advantages:
                air_advantage_count += 1
            if 'Naval Advantage' in advantages:
                naval_advantage_count += 1
            
            # Special handling for 🪓 Psycho advantage - unique advantage, doesn't count toward regular military totals
            if military_composition.get('is_psycho', False):
                psycho_count += 1
            
            # Special handling for 💀 Scary advantage - unique advantage, doesn't count toward regular military totals
            if military_composition.get('is_scary', False):
                scary_count += 1
            
            # Special handling for 👑 Primal advantage - unique advantage, doesn't count toward regular military totals
            if military_composition.get('is_primal', False):
                primal_count += 1
        
        specializations = []
        if missile_count > 0:
            specializations.append(f"🚀 Missile ({missile_count})")
        if nuke_count > 0:
            specializations.append(f"☢️ Nuke ({nuke_count})")
        if psycho_count > 0:
            specializations.append(f"🪓 Psycho ({psycho_count})")
        if scary_count > 0:
            specializations.append(f"💀 Scary ({scary_count})")
        if primal_count > 0:
            specializations.append(f"👑 Primal ({primal_count})")
        if ground_advantage_count > 0:
            specializations.append(f"🪖 Ground ({ground_advantage_count})")
        if air_advantage_count > 0:
            specializations.append(f"✈️ Air ({air_advantage_count})")
        if naval_advantage_count > 0:
            specializations.append(f"🚢 Naval ({naval_advantage_count})")
        specialization_text = " | ".join(specializations) if specializations else "⚔️ Standard"        
        infra_breakdown = []
        infra_tiers = []        
        for member in party_members:
            member_infra_stats = self.blitz_cog.calculator.calculate_infrastructure_stats(member)
            infra_tier = member_infra_stats.get('infrastructure_tier', 'Unknown')
            infra_tiers.append(infra_tier)        
        for tier in ['Perfect', 'Great', 'Good', 'Average', 'Bad', 'Horrible', 'Terrible']:
            count = infra_tiers.count(tier)
            if count > 0:
                infra_breakdown.append(f"{tier}: {count}")        
        # Create war range display text
        safe_overlapping_min = overlapping_min or 0
        safe_overlapping_max = overlapping_max or 0
        safe_war_avg = war_avg or 0
        safe_total_score = total_score or 0
        safe_party_avg_infra = party_avg_infra or 0
        safe_military_advantage = military_advantage or 0
        
        if has_overlap and overlapping_min > 0 and overlapping_max > 0:
            war_range_text = f"**War Range:** {safe_overlapping_min:,.0f} - {safe_overlapping_max:,.0f} (Avg Score: {safe_war_avg:,.1f})\n"
        else:
            war_range_text = f"**War Range:** No overlap (Avg Score: {safe_war_avg:,.1f})\n"
        
        embed = discord.Embed(
            title=f"🎯 {party_name}",
            description=(
                f"{war_range_text}"
                f"**Military Specializations:** {specialization_text}\n"
                f"**Total Party Score:** {safe_total_score:,} | **Members:** {member_count}/3\n"
            f"**Avg Infrastructure:** {safe_party_avg_infra:,.0f} | **Military Advantage:** {safe_military_advantage:.1f}\n"
                f"**Infrastructure Tiers:** {' | '.join(infra_breakdown) if infra_breakdown else 'N/A'}"
            ),
            color=discord.Color.from_rgb(0, 150, 255)
        )       
        embed.set_footer(
            text=f"Party {self.current_page + 1} of {len(self.parties)} | "
                 f"Generated at {datetime.now().strftime('%H:%M:%S')}"
        )       
        for i, member in enumerate(party_members, 1):
            nation_name = member.get('nation_name', member.get('name', 'Unknown'))
            nation_id = member.get('nation_id', member.get('id', 0))
            nation_score = member.get('score', 0)
            
            combat_score = self.blitz_cog.calculator.calculate_combat_score(member)
            specialty = self.blitz_cog.calculator.get_nation_specialty(member)
            
            member_infra_stats = self.blitz_cog.calculator.calculate_infrastructure_stats(member)
            infra_tier = member_infra_stats.get('infrastructure_tier', 'Unknown')
            infra_average = member_infra_stats.get('average_infrastructure', 0) or 0
            has_missile = self.blitz_cog.calculator.has_project(member, 'Missile Launch Pad')
            has_nuke = self.blitz_cog.calculator.has_project(member, 'Nuclear Research Facility')
            has_strategic = has_missile or has_nuke
            
            leader_name = member.get('leader_name', member.get('leader', 'Unknown'))
            if nation_id and leader_name != 'Unknown':
                leader_link = f"[{leader_name}](https://politicsandwar.com/nation/id={nation_id})"
            else:
                leader_link = leader_name
            
            # Create strategic display showing both missile and nuke capabilities
            strategic_display = []
            if has_missile:
                strategic_display.append("🚀")
            if has_nuke:
                strategic_display.append("☢️")
            strategic_text = "".join(strategic_display) if strategic_display else "❌"
            
            # Calculate military limits for daily and max units
            military_limits = self.blitz_cog.calculator.calculate_military_purchase_limits(member)
            
            # Calculate building ratios for MMR display
            building_ratios = self.blitz_cog.calculator.calculate_building_ratios(member)
            
            # Get current military units
            soldiers = member.get('soldiers', 0) or 0
            tanks = member.get('tanks', 0) or 0
            aircraft = member.get('aircraft', 0) or 0
            ships = member.get('ships', 0) or 0
            
            # Safe military limits handling
            mil_limits = military_limits or {}
            soldiers_daily = mil_limits.get('soldiers_daily', 0) or 0
            soldiers_max = mil_limits.get('soldiers_max', 0) or 0
            tanks_daily = mil_limits.get('tanks_daily', 0) or 0
            tanks_max = mil_limits.get('tanks_max', 0) or 0
            aircraft_daily = mil_limits.get('aircraft_daily', 0) or 0
            aircraft_max = mil_limits.get('aircraft_max', 0) or 0
            ships_daily = mil_limits.get('ships_daily', 0) or 0
            ships_max = mil_limits.get('ships_max', 0) or 0
            
            # Safe formatting variables
            safe_nation_score = nation_score or 0
            safe_infra_average = infra_average or 0
            
            field_value = (
                f"**Leader:** {leader_link}\n"
                f"**Score:** {safe_nation_score:,}\n**MMR:** {building_ratios.get('mmr_string', '0/0/0/0')}\n"
                f"**Specialty:** {specialty or 'Unknown'}\n"
                f"**Infrastructure:** {safe_infra_average:,.0f} ({infra_tier})\n"
                f"**Strategic:** {strategic_text}\n"
                f"**Units (Current/Max/Daily):**\n"
                f"👥 {soldiers:,}/{soldiers_max:,}/{soldiers_daily:,}\n"
                f"🚗 {tanks:,}/{tanks_max:,}/{tanks_daily:,}\n"
                f"✈️ {aircraft:,}/{aircraft_max:,}/{aircraft_daily:,}\n"
                f"🚢 {ships:,}/{ships_max:,}/{ships_daily:,}"
            )
            embed.add_field(
                name=f"{i}. {nation_name}",
                value=field_value,
                inline=True
            )           
        return embed

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.secondary, disabled=True)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)  
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🔄 Resort Parties", style=discord.ButtonStyle.primary, emoji="🔄")
    async def resort_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Re-sort nations into new balanced parties."""
        await interaction.response.defer()       
        try:
            alliance_id = str(interaction.guild.id)
            nations = await self.blitz_cog.get_alliance_nations(alliance_id)           
            if not nations:
                embed = discord.Embed(
                    title="❌ No Nations Found",
                    description="No nations found for this alliance.",
                    color=discord.Color.red()
                )
                await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=None)
                return
            parties = self.blitz_cog.create_balanced_parties(nations)            
            if not parties:
                embed = discord.Embed(
                    title="❌ No Viable Parties",
                    description="Unable to create viable blitz parties.\n\n**Requirements:**\n• Parties of exactly 3 members\n• Compatible score ranges for same-target attacks\n• At least 1 member with Ground, Air, or Naval advantage\n• Preference for strategic capabilities (missiles/nukes)",
                    color=discord.Color.red()
                )
                await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=None)
                return
            team_names = self.blitz_cog._load_team_names()
            random.shuffle(team_names)
            party_info_display = []           
            for i, party in enumerate(parties):
                party_name = team_names[i % len(team_names)] if team_names else f"Party {i+1}"
                total_score = sum(nation.get('score', 0) for nation in party)
                strategic_count = sum(1 for nation in party if nation.get('has_strategic', False))
                scores = [nation.get('score', 0) for nation in party]
                min_score = min(scores)
                max_score = max(scores)
                
                # Calculate proper war range using the calculator
                war_range_data = self.blitz_cog.calculate_party_war_range(party)
                if isinstance(war_range_data, dict):
                    overlapping_min = war_range_data.get('overlapping_min', 0)
                    overlapping_max = war_range_data.get('overlapping_max', 0)
                    avg_score = war_range_data.get('avg_score', total_score / len(party) if party else 0)
                    has_overlap = war_range_data.get('has_overlap', False)
                else:
                    # Fallback to simplified calculation
                    overlapping_min = max_score * 0.75
                    overlapping_max = min_score * 2.5
                    avg_score = total_score / len(party) if party else 0
                    has_overlap = overlapping_min > 0 and overlapping_max > 0
                
                specialities = [nation.get('speciality', 'Generalist') for nation in party]
                ground_count = specialities.count('Ground')
                air_count = specialities.count('Air')
                naval_count = specialities.count('Naval')
                
                # Calculate average infrastructure for sorting
                avg_infra = sum(nation.get('infra_average', 0) for nation in party) / len(party) if party else 0
                
                member_data_display = []                
                for nation in party:
                    # Calculate military limits for this nation
                    military_limits = self.blitz_cog.calculator.calculate_military_purchase_limits(nation)
                    
                    member_display = {
                        'nation_name': nation.get('nation_name', 'Unknown'),
                        'leader_name': nation.get('leader_name', 'Unknown'),
                        'score': nation.get('score', 0),
                        'speciality': nation.get('speciality', 'Generalist'),
                        'infra_average': nation.get('infra_average', 0),
                        'infra_tier': nation.get('infra_tier', 'Medium'),
                        'has_strategic': nation.get('has_strategic', False),
                        'missile_launch_pad': nation.get('missile_launch_pad', False),
                        'nuclear_research_facility': nation.get('nuclear_research_facility', False),
                        'nation_id': nation.get('id'),
                        'soldiers': nation.get('soldiers', 0),
                        'tanks': nation.get('tanks', 0),
                        'aircraft': nation.get('aircraft', 0),
                        'ships': nation.get('ships', 0),
                        'military_limits': military_limits
                    }
                    member_data_display.append(member_display)
                party_display = {
                    'party_name': party_name,
                    'members': member_data_display,
                    'total_score': total_score,
                    'strategic_count': strategic_count,
                    'member_count': len(party),
                    'avg_infra': avg_infra,
                    'attack_range': {
                        'overlapping_min': overlapping_min,
                        'overlapping_max': overlapping_max,
                        'min_score': min_score,
                        'max_score': max_score,
                        'avg_score': avg_score,
                        'has_overlap': has_overlap
                    },
                    'military_advantages': {
                        'ground': ground_count,
                        'air': air_count,
                        'naval': naval_count
                    }
                }
                party_info_display.append(party_display)
            
            # Sort parties by average infrastructure (ascending - lower infra first)
            party_info_display.sort(key=lambda party: party.get('avg_infra', 0))
            
            self.parties = party_info_display
            self.total_pages = len(party_info_display)
            self.current_page = 0
            self.previous_button.disabled = True
            self.next_button.disabled = (self.total_pages <= 1)           
            embed = self.create_embed()
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=self)           
        except Exception as e:
            self.blitz_cog._log_error(f"Error in resort_button: {str(e)}", e, "PartyView.resort_button")
            embed = discord.Embed(
                title="❌ Resort Error",
                description=f"An error occurred while resorting parties: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=None)

    async def on_timeout(self):
        """Called when the view times out."""
        for item in self.children:
            item.disabled = True


class NationMilitaryView(discord.ui.View):
    """View for displaying military analysis for a single nation."""
    
    def __init__(self, author_id, bot, blitz_cog, nation):
        super().__init__()
        self.author_id = author_id
        self.bot = bot
        self.blitz_cog = blitz_cog
        self.nation = nation
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is from the author."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You are not authorized to use this menu.", ephemeral=True)
            return False
        return True
    
    async def generate_nation_military_embed(self):
        """Generate military analysis embed for a single nation."""
        try:
            # Calculate military data using the blitz_cog's calculator
            purchase_limits = self.blitz_cog.calculator.calculate_military_purchase_limits(self.nation)
            combat_score = self.blitz_cog.calculator.calculate_combat_score(self.nation)
            military_advantage = self.blitz_cog.calculator.calculate_military_advantage(self.nation)
            
            # Get nation specialty
            specialty = self.blitz_cog.calculator.get_nation_specialty(self.nation)
            
            # Calculate infrastructure stats for context
            infra_stats = self.blitz_cog.calculator.calculate_infrastructure_stats(self.nation)
            
            embed = discord.Embed(
                title=f"🏭 Military Analysis - {self.nation['nation_name']}",
                description=f"**{specialty}** • Score: {combat_score:,.0f}",
                color=discord.Color.from_rgb(255, 140, 0)
            )
            
            # Get current military values (same as used in military advantage calculation)
            current_military = {
                'soldiers': max(0, int(self.nation.get('soldiers', 0) or 0)),
                'tanks': max(0, int(self.nation.get('tanks', 0) or 0)),
                'aircraft': max(0, int(self.nation.get('aircraft', 0) or 0)),
                'ships': max(0, int(self.nation.get('ships', 0) or 0))
            }
            
            # Military Units - Current/Max (matching alliance format)
            embed.add_field(
                name="⚔️ Military Units",
                value=(
                    f"🪖 **Soldiers:** {current_military['soldiers']:,}/{purchase_limits.get('soldiers_max', 0):,}\n"
                    f"🛡️ **Tanks:** {current_military['tanks']:,}/{purchase_limits.get('tanks_max', 0):,}\n"
                    f"✈️ **Aircraft:** {current_military['aircraft']:,}/{purchase_limits.get('aircraft_max', 0):,}\n"
                    f"🚢 **Ships:** {current_military['ships']:,}/{purchase_limits.get('ships_max', 0):,}"
                ),
                inline=False
            )
            
            # Daily Production (if available, otherwise show gaps)
            if hasattr(self.blitz_cog.calculator, 'calculate_daily_production'):
                daily_prod = self.blitz_cog.calculator.calculate_daily_production(self.nation)
                embed.add_field(
                    name="🏭 Daily Production",
                    value=(
                        f"🪖 **Soldiers:** {daily_prod.get('soldiers', 0):,}/day\n"
                        f"🛡️ **Tanks:** {daily_prod.get('tanks', 0):,}/day\n"
                        f"✈️ **Aircraft:** {daily_prod.get('aircraft', 0):,}/day\n"
                        f"🚢 **Ships:** {daily_prod.get('ships', 0):,}/day\n"
                        f"🚀 **Missiles:** {daily_prod.get('missiles', 0):,}/day\n"
                        f"☢️ **Nukes:** {daily_prod.get('nukes', 0):,}/day"
                    ),
                    inline=False
                )
            else:
                # Calculate gaps (units needed to reach max)
                soldier_gap = max(0, purchase_limits.get('soldiers_max', 0) - current_military['soldiers'])
                tank_gap = max(0, purchase_limits.get('tanks_max', 0) - current_military['tanks'])
                aircraft_gap = max(0, purchase_limits.get('aircraft_max', 0) - current_military['aircraft'])
                ship_gap = max(0, purchase_limits.get('ships_max', 0) - current_military['ships'])
                
                embed.add_field(
                    name="⚔️ Units Needed to Max",
                    value=(
                        f"🪖 **Soldiers:** {soldier_gap:,}\n"
                        f"🛡️ **Tanks:** {tank_gap:,}\n"
                        f"✈️ **Aircraft:** {aircraft_gap:,}\n"
                        f"🚢 **Ships:** {ship_gap:,}"
                    ),
                    inline=False
                )
            
            # Advanced military info (missiles/nukes with capabilities)
            missile_info = f"🚀 **Missiles:** {self.nation.get('missiles', 0):,}"
            if self.nation.get('missiles', 0) > 0:
                missile_info += f" (Max: {purchase_limits.get('missiles', 0):,})"
            
            nuke_info = f"☢️ **Nukes:** {self.nation.get('nukes', 0):,}"
            if self.nation.get('nukes', 0) > 0:
                nuke_info += f" (Max: {purchase_limits.get('nukes', 0):,})"
            
            embed.add_field(
                name="🚀 Advanced Military",
                value=f"{missile_info}\n{nuke_info}",
                inline=False
            )
            
            # Military advantage with detailed breakdown
            if isinstance(military_advantage, dict):
                # If it's a detailed advantage object
                advantage_score = military_advantage.get('advantage_score', 0)
                advantages = military_advantage.get('advantages', [])
                
                advantage_text = f"**Score:** {advantage_score:,.0f}\n"
                if advantages:
                    advantage_text += "**Advantages:** " + ", ".join(advantages)
                
                embed.add_field(
                    name="🎯 Military Advantage",
                    value=advantage_text,
                    inline=False
                )
            else:
                # If it's just a number
                embed.add_field(
                    name="🎯 Military Advantage",
                    value=f"**Score:** {military_advantage:,.0f}",
                    inline=False
                )
            
            # Footer with nation info and timestamp
            nation_name = self.nation.get('nation_name', 'Unknown Nation')
            cities_list = self.nation.get('cities', [])
            cities = len(cities_list) if isinstance(cities_list, list) else 0
            score = self.nation.get('score', 0)
            
            # Truncate nation name if too long to prevent footer overflow
            if len(nation_name) > 50:
                nation_name = nation_name[:47] + "..."
            
            footer_text = f"{nation_name} • Cities: {cities} • Score: {score:,.2f}"
            
            # Ensure footer text doesn't exceed Discord limits
            if len(footer_text) > 2048:
                footer_text = f"{nation_name} • Score: {score:,.2f}"
                if len(footer_text) > 2048:
                    footer_text = nation_name[:2048]
            
            embed.set_footer(
                text=footer_text,
                icon_url=self.nation.get('flag_url', '') if len(self.nation.get('flag_url', '')) < 1000 else None
            )
            
            return embed
            
        except Exception as e:
            self.blitz_cog._log_error(f"Error generating nation military embed: {e}", e, "NationMilitaryView.generate_nation_military_embed")
            embed = discord.Embed(
                title="❌ Military Error",
                description=f"Failed to generate military analysis: {str(e)}",
                color=discord.Color.red()
            )
            return embed
    
    @discord.ui.button(label="Back to Nation", style=discord.ButtonStyle.primary, emoji="🏠")
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to the nation list view."""
        try:
            await interaction.response.defer()
            
            # Create a new NationListView with just this nation
            view = NationListView([self.nation], self.author_id, self.bot, self.blitz_cog)
            embed = view.create_embed()
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
            
        except Exception as e:
            self.blitz_cog._log_error(f"Error in back_button: {e}", e, "NationMilitaryView.back_button")
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)


class NationImprovementsView(discord.ui.View):
    """View for displaying improvements breakdown for a single nation."""
    
    def __init__(self, author_id, bot, blitz_cog, nation):
        super().__init__()
        self.author_id = author_id
        self.bot = bot
        self.blitz_cog = blitz_cog
        self.nation = nation
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is from the author."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You are not authorized to use this menu.", ephemeral=True)
            return False
        return True
    
    async def generate_nation_improvements_embed(self):
        """Generate improvements breakdown embed for a single nation."""
        try:
            # Calculate improvements data
            improvements_data = self.blitz_cog.calculate_nation_improvements(self.nation)
            
            embed = discord.Embed(
                title=f"🏗️ Improvements Breakdown - {self.nation['nation_name']}",
                description=f"**Total Improvements:** {improvements_data['total']:,}",
                color=discord.Color.green()
            )
            
            # Power improvements
            power_value = f"Power Plants: {improvements_data['power_plants']:,}"
            if improvements_data['power_plants'] > 0:
                power_value += f" ({improvements_data['power_plants'] * 500:,} MW)"
            embed.add_field(name="⚡ Power", value=power_value, inline=True)
            
            # Resource improvements
            resource_improvements = []
            if improvements_data['bauxite_mines'] > 0:
                resource_improvements.append(f"Bauxite Mines: {improvements_data['bauxite_mines']:,}")
            if improvements_data['coal_mines'] > 0:
                resource_improvements.append(f"Coal Mines: {improvements_data['coal_mines']:,}")
            if improvements_data['iron_mines'] > 0:
                resource_improvements.append(f"Iron Mines: {improvements_data['iron_mines']:,}")
            if improvements_data['lead_mines'] > 0:
                resource_improvements.append(f"Lead Mines: {improvements_data['lead_mines']:,}")
            if improvements_data['oil_wells'] > 0:
                resource_improvements.append(f"Oil Wells: {improvements_data['oil_wells']:,}")
            if improvements_data['uranium_mines'] > 0:
                resource_improvements.append(f"Uranium Mines: {improvements_data['uranium_mines']:,}")
            if improvements_data['farms'] > 0:
                resource_improvements.append(f"Farms: {improvements_data['farms']:,}")
            
            if resource_improvements:
                embed.add_field(name="⛏️ Resources", value="\n".join(resource_improvements), inline=False)
            
            # Manufacturing improvements
            manufacturing_improvements = []
            if improvements_data['aluminum_refineries'] > 0:
                manufacturing_improvements.append(f"Aluminum Refineries: {improvements_data['aluminum_refineries']:,}")
            if improvements_data['steel_mills'] > 0:
                manufacturing_improvements.append(f"Steel Mills: {improvements_data['steel_mills']:,}")
            if improvements_data['gasoline_refineries'] > 0:
                manufacturing_improvements.append(f"Gasoline Refineries: {improvements_data['gasoline_refineries']:,}")
            if improvements_data['munitions_factories'] > 0:
                manufacturing_improvements.append(f"Munitions Factories: {improvements_data['munitions_factories']:,}")
            
            if manufacturing_improvements:
                embed.add_field(name="🏭 Manufacturing", value="\n".join(manufacturing_improvements), inline=False)
            
            # Military improvements
            military_improvements = []
            if improvements_data['barracks'] > 0:
                military_improvements.append(f"Barracks: {improvements_data['barracks']:,}")
            if improvements_data['factories'] > 0:
                military_improvements.append(f"Factories: {improvements_data['factories']:,}")
            if improvements_data['hangars'] > 0:
                military_improvements.append(f"Hangars: {improvements_data['hangars']:,}")
            if improvements_data['drydocks'] > 0:
                military_improvements.append(f"Drydocks: {improvements_data['drydocks']:,}")
            
            if military_improvements:
                embed.add_field(name="⚔️ Military", value="\n".join(military_improvements), inline=False)
            
            # Civil improvements
            civil_improvements = []
            if improvements_data['subway_stations'] > 0:
                civil_improvements.append(f"Subway Stations: {improvements_data['subway_stations']:,}")
            if improvements_data['supermarkets'] > 0:
                civil_improvements.append(f"Supermarkets: {improvements_data['supermarkets']:,}")
            if improvements_data['banks'] > 0:
                civil_improvements.append(f"Banks: {improvements_data['banks']:,}")
            if improvements_data['shopping_malls'] > 0:
                civil_improvements.append(f"Shopping Malls: {improvements_data['shopping_malls']:,}")
            if improvements_data['stadiums'] > 0:
                civil_improvements.append(f"Stadiums: {improvements_data['stadiums']:,}")
            
            if civil_improvements:
                embed.add_field(name="🏢 Civil", value="\n".join(civil_improvements), inline=False)
            
            # Footer with nation info
            nation_name = str(self.nation.get('nation_name', 'Unknown Nation'))
            cities_list = self.nation.get('cities', [])
            cities = len(cities_list) if isinstance(cities_list, list) else 0
            score = self.nation.get('score', 0)
            
            # Ensure cities is a reasonable number
            try:
                cities = int(cities) if cities is not None else 0
            except (ValueError, TypeError):
                cities = 0
            
            # Ensure score is a reasonable number
            try:
                score = float(score) if score is not None else 0.0
            except (ValueError, TypeError):
                score = 0.0
            
            # Truncate nation name if too long to prevent footer overflow
            if len(nation_name) > 50:
                nation_name = nation_name[:47] + "..."
            
            footer_text = f"{nation_name} • Cities: {cities} • Score: {score:,.2f}"
            
            # Ensure footer text doesn't exceed Discord limits
            if len(footer_text) > 2048:
                footer_text = f"{nation_name} • Score: {score:,.2f}"
                if len(footer_text) > 2048:
                    footer_text = nation_name[:2048]
            
            embed.set_footer(
                text=footer_text,
                icon_url=self.nation.get('flag_url', '') if len(self.nation.get('flag_url', '')) < 1000 else None
            )
            
            return embed
            
        except Exception as e:
            self.blitz_cog._log_error(f"Error generating nation improvements embed: {e}", e, "NationImprovementsView.generate_nation_improvements_embed")
            embed = discord.Embed(
                title="❌ Improvements Error",
                description=f"Failed to generate improvements breakdown: {str(e)}",
                color=discord.Color.red()
            )
            return embed
    
    @discord.ui.button(label="Back to Nation", style=discord.ButtonStyle.primary, emoji="🏠")
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to the nation list view."""
        try:
            await interaction.response.defer()
            
            # Create a new NationListView with just this nation
            view = NationListView([self.nation], self.author_id, self.bot, self.blitz_cog)
            embed = view.create_embed()
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
            
        except Exception as e:
            self.blitz_cog._log_error(f"Error in back_button: {e}", e, "NationImprovementsView.back_button")
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)


class PartyManagementView(discord.ui.View):
    """View for displaying party information."""
    
    def __init__(self, author_id, bot, blitz_cog, party_data):
        super().__init__()
        self.author_id = author_id
        self.bot = bot
        self.blitz_cog = blitz_cog
        self.party_data = party_data
        self.current_page = 0
        self.nations_per_page = 10
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is from the author."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You are not authorized to use this menu.", ephemeral=True)
            return False
        return True

class BlitzParties(commands.Cog):
    """Cybertr0n Blitz Party Generator - Creates balanced teams for coordinated attacks."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_key = PANDW_API_KEY
        self.user_data_manager = UserDataManager()
        self._cache_expiry_seconds: int = 3600  
        self._alliance_nations_cache: Dict[str, Dict] = {}
        self.logger = logging.getLogger(f"{__name__}.BlitzParties")
        self.error_count = 0
        try:
            if create_query_instance is not None:
                self.query_instance = create_query_instance(api_key=self.api_key, logger=self.logger)
                self.logger.info("Centralized query instance initialized successfully")
            else:
                self.query_instance = None
                self.logger.warning("Query instance creation function not available - import failed")
        except Exception as e:
            self.query_instance = None
            self.logger.error(f"Failed to initialize query instance: {str(e)}")
        if PNWKIT_AVAILABLE:
            self.kit = pnwkit.QueryKit(self.api_key)
            self.logger.info(f"PNWKit initialized successfully from {PNWKIT_SOURCE}")
        else:
            self.kit = None
            self.logger.warning(f"PNWKit not available: {PNWKIT_ERROR}")
        self.cybertron_alliance_id = CYBERTRON_ALLIANCE_ID
        self.party_sorter = BlitzPartySorter(logger=self.logger)       
        self.calculator = AllianceCalculator()
        self.team_names = self._load_team_names()        
        self.logger.info("BlitzParties cog initialized successfully")
    
    def calculate_nation_improvements(self, nation: Dict[str, Any]) -> Dict[str, int]:
        """Calculate comprehensive improvements data for a single nation by summing up all city improvements."""
        improvements = {
            'total': 0,
            'power_plants': 0,
            'bauxite_mines': 0,
            'coal_mines': 0,
            'iron_mines': 0,
            'lead_mines': 0,
            'oil_wells': 0,
            'uranium_mines': 0,
            'farms': 0,
            'aluminum_refineries': 0,
            'steel_mills': 0,
            'gasoline_refineries': 0,
            'munitions_factories': 0,
            'barracks': 0,
            'factories': 0,
            'hangars': 0,
            'drydocks': 0,
            'subway_stations': 0,
            'supermarkets': 0,
            'banks': 0,
            'shopping_malls': 0,
            'stadiums': 0,
        }
        
        cities = nation.get('cities', [])
        for city in cities:
            if not isinstance(city, dict):
                continue
            
            # Power plants (each provides 500 MW)
            coal_power = city.get('coal_power', 0) or 0
            oil_power = city.get('oil_power', 0) or 0
            nuclear_power = city.get('nuclear_power', 0) or 0
            wind_power = city.get('wind_power', 0) or 0
            improvements['power_plants'] += coal_power + oil_power + nuclear_power + wind_power
            
            # Resource improvements
            improvements['bauxite_mines'] += city.get('bauxite_mine', 0) or 0
            improvements['coal_mines'] += city.get('coal_mine', 0) or 0
            improvements['iron_mines'] += city.get('iron_mine', 0) or 0
            improvements['lead_mines'] += city.get('lead_mine', 0) or 0
            improvements['oil_wells'] += city.get('oil_well', 0) or 0
            improvements['uranium_mines'] += city.get('uranium_mine', 0) or 0
            improvements['farms'] += city.get('farm', 0) or 0
            
            # Manufacturing improvements
            improvements['aluminum_refineries'] += city.get('aluminum_refinery', 0) or 0
            improvements['steel_mills'] += city.get('steel_mill', 0) or 0
            improvements['gasoline_refineries'] += city.get('gasoline_refinery', 0) or 0
            improvements['munitions_factories'] += city.get('munitions_factory', 0) or 0
            
            # Military improvements
            improvements['barracks'] += city.get('barracks', 0) or 0
            improvements['factories'] += city.get('factory', 0) or 0
            improvements['hangars'] += city.get('hangar', 0) or 0
            improvements['drydocks'] += city.get('drydock', 0) or 0
            
            # Civil improvements
            improvements['subway_stations'] += city.get('subway', 0) or 0
            improvements['supermarkets'] += city.get('supermarket', 0) or 0
            improvements['banks'] += city.get('bank', 0) or 0
            improvements['shopping_malls'] += city.get('shopping_mall', 0) or 0
            improvements['stadiums'] += city.get('stadium', 0) or 0
        
        # Calculate total improvements
        improvements['total'] = (
            improvements['power_plants'] +
            improvements['bauxite_mines'] + improvements['coal_mines'] + improvements['iron_mines'] + 
            improvements['lead_mines'] + improvements['oil_wells'] + improvements['uranium_mines'] + 
            improvements['farms'] + improvements['aluminum_refineries'] + improvements['steel_mills'] + 
            improvements['gasoline_refineries'] + improvements['munitions_factories'] + 
            improvements['barracks'] + improvements['factories'] + improvements['hangars'] + 
            improvements['drydocks'] + improvements['subway_stations'] + improvements['supermarkets'] + 
            improvements['banks'] + improvements['shopping_malls'] + improvements['stadiums']
        )
        
        return improvements
    
    def _log_error(self, error_msg: str, exception: Exception = None, context: str = ""):
        """Centralized error logging with optional context."""
        self.error_count += 1       
        if exception:
            self.logger.error(f"{error_msg}: {str(exception)}")
            self.logger.debug(f"Exception details: {traceback.format_exc()}")
        else:
            self.logger.error(error_msg)        
        if context:
            self.logger.debug(f"Context: {context}")
    
    def _validate_input(self, data: Any, expected_type: type, field_name: str = "data") -> bool:
        """Validate input data type."""
        if not isinstance(data, expected_type):
            self.logger.warning(f"Invalid {field_name}: expected {expected_type.__name__}, got {type(data).__name__}")
            return False
        return True
    
    def _safe_get(self, data: dict, key: str, default: Any = None, expected_type: type = None) -> Any:
        """Safely get value from dictionary with optional type checking."""
        try:
            value = data.get(key, default)
            if expected_type and value is not None:
                if isinstance(expected_type, tuple):
                    if not isinstance(value, expected_type):
                        self.logger.warning(f"Type mismatch for key '{key}': expected {expected_type}, got {type(value)}")
                        return default
                else:
                    if not isinstance(value, expected_type):
                        if expected_type in (int, float) and isinstance(value, (int, float)):
                            return expected_type(value)
                        self.logger.warning(f"Type mismatch for key '{key}': expected {expected_type.__name__}, got {type(value).__name__}")
                        return default
            return value
        except Exception as e:
            self._log_error(f"Error accessing key '{key}' from data", e)
            return default

    def _load_team_names(self) -> List[str]:
        """Load team names from pets_level.json TEAM_NAMES category."""
        try:
            pets_level_path = os.path.join(os.path.dirname(__file__), '..', '..', 'Data', 'PetsInfo', 'pets_level.json')            
            if not os.path.exists(pets_level_path):
                self.logger.warning(f"pets_level.json not found at {pets_level_path}, using fallback team names")
                return self._get_fallback_team_names()           
            with open(pets_level_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                team_names = data.get('TEAM_NAMES', [])               
                if not team_names:
                    self.logger.warning("No team names found in pets_level.json, using fallback")
                    return self._get_fallback_team_names()               
                self.logger.debug(f"Loaded {len(team_names)} team names from pets_level.json")
                return team_names
                
        except json.JSONDecodeError as e:
            self._log_error("Invalid JSON format in pets_level.json", e)
            return self._get_fallback_team_names()
        except FileNotFoundError as e:
            self._log_error("pets_level.json file not found", e)
            return self._get_fallback_team_names()
        except Exception as e:
            self._log_error("Unexpected error loading team names", e)
            return self._get_fallback_team_names()
    
    def _get_fallback_team_names(self) -> List[str]:
        """Fallback team names if pets_level.json is unavailable."""
        return ["Alpha Squad", "Beta Team", "Gamma Force", "Delta Unit", "Echo Division"]

    async def get_alliance_nations(self, alliance_id: str, force_refresh: bool = False) -> Optional[List[Dict[str, Any]]]:
        """Fetch alliance nations from individual alliance files."""
        if not alliance_id or not str(alliance_id).strip():
            self.logger.warning("get_alliance_nations: Invalid alliance_id provided")
            return None       
        try:
            # Load from individual alliance file instead of alliance_cache
            user_data_manager = UserDataManager()
            alliance_file_key = f"alliance_{alliance_id}"
            alliance_data = await user_data_manager.get_json_data(alliance_file_key, {})
            
            if alliance_data and isinstance(alliance_data, dict) and 'nations' in alliance_data:
                nations = alliance_data.get('nations', [])
                if nations:
                    self.logger.debug(f"get_alliance_nations: Loaded {len(nations)} nations from alliance file {alliance_file_key}")
                    return nations
            
            # If individual file not found, try loading from all alliance files
            bloc_dir = Path(__file__).parent.parent.parent / 'Data' / 'Bloc'
            if bloc_dir.exists():
                all_nations = []
                for alliance_file in bloc_dir.glob('alliance_*.json'):
                    try:
                        file_data = await user_data_manager.get_json_data(alliance_file.stem, {})
                        if isinstance(file_data, dict) and 'nations' in file_data:
                            all_nations.extend(file_data['nations'])
                    except Exception as e:
                        self.logger.warning(f"Error loading {alliance_file.name}: {e}")
                        continue
                
                if all_nations:
                    self.logger.debug(f"get_alliance_nations: Loaded {len(all_nations)} total nations from all alliance files")
                    return all_nations
            cache_key = str(alliance_id)
            if not force_refresh and cache_key in self._alliance_nations_cache:
                entry = self._alliance_nations_cache[cache_key]
                if time.time() - entry.get('timestamp', 0) < self._cache_expiry_seconds:
                    data = entry.get('data') or []
                    if data:
                        self.logger.debug(f"get_alliance_nations: Local cache hit for alliance {alliance_id} ({len(data)} nations)")
                        return data
            if self.query_instance:
                self.logger.debug(f"get_alliance_nations: Using query instance for alliance {alliance_id}")
                nations = await self.query_instance.get_alliance_nations(alliance_id, bot=self.bot, force_refresh=force_refresh)
                if nations:
                    self._alliance_nations_cache[cache_key] = { 'data': nations, 'timestamp': time.time() }
                return nations
            if self.query_instance:
                self.logger.debug(f"get_alliance_nations: Using centralized query instance for alliance {alliance_id}")
                nations = await self.query_instance.get_alliance_nations(alliance_id, bot=self.bot, force_refresh=force_refresh)
                if nations:
                    self._alliance_nations_cache[cache_key] = { 'data': nations, 'timestamp': time.time() }
                return nations
            else:
                error_msg = "Query instance not available and AllianceManager not found"
                self.logger.error(f"get_alliance_nations: {error_msg}")
                raise Exception(error_msg)            
        except ValueError as e:
            raise e
        except AttributeError as e:
            self._log_error(f"AllianceManager cog not available or method missing for alliance {alliance_id}", e, "get_alliance_nations")
            return None
        except Exception as e:
            self._log_error(f"Unexpected error while fetching alliance {alliance_id}", e, "get_alliance_nations")
            raise Exception(f"API error: {str(e)}")

    def create_balanced_parties(self, nations: List[Dict[str, Any]], num_parties: int = 3) -> List[List[Dict[str, Any]]]:
        """Create optimal parties of 3 for coordinated same-target attacks."""
        return self.party_sorter.create_balanced_parties(nations)

    async def create_balanced_parties_multi_alliance(self, alliance_keys: List[str]) -> List[List[Dict[str, Any]]]:
        """Create parties from multiple selected alliances by fetching and combining their nations."""
        try:
            if not alliance_keys:
                return []
            # Build alliance_data mapping concurrently
            tasks = []
            task_keys = []
            for key in alliance_keys:
                if key == 'cybertron_combined':
                    # Fetch both Cybertr0n and Prime Bank
                    cybertron_id = AERO_ALLIANCES.get('cybertron', {}).get('id')
                    prime_bank_id = AERO_ALLIANCES.get('prime_bank', {}).get('id')
                    if cybertron_id:
                        tasks.append(asyncio.wait_for(self.get_alliance_nations(str(cybertron_id)), timeout=8))
                        task_keys.append('cybertron')
                    if prime_bank_id:
                        tasks.append(asyncio.wait_for(self.get_alliance_nations(str(prime_bank_id)), timeout=8))
                        task_keys.append('prime_bank')
                else:
                    alliance_id = AERO_ALLIANCES.get(key, {}).get('id')
                    if alliance_id:
                        tasks.append(asyncio.wait_for(self.get_alliance_nations(str(alliance_id)), timeout=8))
                        task_keys.append(key)
            alliance_data: Dict[str, List[Dict[str, Any]]] = {}
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    k = task_keys[i]
                    if isinstance(result, Exception) or not result:
                        alliance_data[k] = []
                    else:
                        # Filter results to Cybertron or Prime Banking only
                        try:
                            allowed_ids = {str(CYBERTRON_ALLIANCE_ID)}
                            if 'PRIME_BANK_ALLIANCE_ID' in globals() and PRIME_BANK_ALLIANCE_ID:
                                allowed_ids.add(str(PRIME_BANK_ALLIANCE_ID))
                            alliance_data[k] = [n for n in (result or []) if str(n.get('alliance_id')) in allowed_ids]
                        except Exception:
                            alliance_data[k] = result or []
            # Use sorter’s multi-alliance method
            return self.party_sorter.create_balanced_parties_multi_alliance(alliance_data, alliance_keys)
        except Exception as e:
            self._log_error("Error creating multi-alliance parties", e)
            return []

    def process_parties_for_display(self, parties: List[List[Dict[str, Any]]], team_names: List[str] = None) -> tuple:
        """Process parties for display, handling all party statistics and data preparation."""
        try:
            if not parties:
                return [], []
            if team_names is None:
                team_names = self._load_team_names()          
            processed_parties = []          
            for i, party in enumerate(parties):
                if not party:
                    continue        
                total_score = sum(n.get('score', 0) for n in party)
                avg_score = total_score / len(party) if party else 0
                strategic_count = sum(1 for n in party if self._has_missile_or_nuke(n))
                party_name = team_names[i % len(team_names)] if i < len(team_names) else f"Team {i+1}"
                
                # Calculate war range data
                war_range_data = self.calculate_party_war_range(party)
                
                # Calculate average infrastructure for sorting
                total_infra = 0
                for member in party:
                    infra_stats = self.calculator.calculate_infrastructure_stats(member)
                    total_infra += infra_stats.get('average_infrastructure', 0)
                avg_infra = total_infra / len(party) if party else 0
                
                party_data = {
                    'party_name': party_name,
                    'members': party,
                    'member_count': len(party),
                    'total_score': total_score,
                    'avg_score': avg_score,
                    'strategic_count': strategic_count,
                    'war_range': war_range_data,
                    'attack_range': war_range_data,  # Add this key for compatibility with PartyView
                    'avg_infra': avg_infra  # Add infrastructure average for sorting
                }               
                processed_parties.append(party_data)           
            
            # Sort parties by infrastructure quality (lower infrastructure = better for war)
            processed_parties.sort(key=lambda x: x.get('avg_infra', 0))
            
            return processed_parties, team_names           
        except Exception as e:
            self._log_error("Error processing parties for display", e)
            return [], []

    def _has_missile_or_nuke(self, nation: Dict[str, Any]) -> bool:
        """Check if nation can build missiles or nukes."""
        try:
            has_missile_launch = self.calculator.has_project(nation, 'Missile Launch Pad')
            has_nuke_research = self.calculator.has_project(nation, 'Nuclear Research Facility')
            missiles = self._safe_get(nation, 'missiles', 0, int)
            nukes = self._safe_get(nation, 'nukes', 0, int)           
            return has_missile_launch or has_nuke_research or missiles > 0 or nukes > 0            
        except Exception as e:
            self._log_error(f"Error checking missile/nuke capability", e, f"nation: {nation.get('nation_name', 'Unknown')}")
            return False

    def has_project(self, nation: Dict[str, Any], project_name: str) -> bool:
        """Check if a nation has a specific project."""
        try:
            return self.calculator.has_project(nation, project_name)
        except Exception as e:
            self._log_error(f"Error checking project {project_name}", e, f"nation: {nation.get('nation_name', 'Unknown')}")
            return False

    def get_active_nations(self, nations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter active nations from a list."""
        try:
            return self.calculator.get_active_nations(nations)
        except Exception as e:
            self._log_error("Error filtering active nations", e)
            return []

    def _is_active_nation(self, nation: Dict[str, Any]) -> bool:
        """Check if nation is active (not applicant or vacation mode)."""
        try:
            active_nations = self.calculator.get_active_nations([nation])
            return len(active_nations) > 0            
        except Exception as e:
            self._log_error(f"Error checking if nation is active", e, f"nation: {nation.get('nation_name', 'Unknown')}")
            return False

    def calculate_infrastructure_stats(self, nation: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate infrastructure statistics for a nation."""
        try:
            return self.calculator.calculate_infrastructure_stats(nation)           
        except Exception as e:
            self._log_error("Error calculating infrastructure stats", e, f"nation: {nation.get('nation_name', 'Unknown')}")
            return {'total': 0, 'average': 0, 'cities': 1}

    def validate_attack_range(self, attacker_score: float, target_score: float) -> bool:
        """Validate if an attack is within range."""
        try:
            return self.calculator.validate_attack_range(attacker_score, target_score)            
        except Exception as e:
            self._log_error("Error validating attack range", e)
            return False

    def calculate_party_war_range(self, party: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate war range for a party."""
        try:
            return self.calculator.calculate_party_war_range(party)            
        except Exception as e:
            self._log_error("Error calculating party war range", e)
            return {
                'min_range': 0, 
                'max_range': 0, 
                'avg_score': 0, 
                'overlapping_min': 0, 
                'overlapping_max': 0, 
                'has_overlap': False
            }

    def _calculate_strategic_value(self, nation: Dict[str, Any]) -> float:
        """Calculate strategic value for a nation."""
        try:
            return self.calculator._calculate_strategic_value(nation)            
        except Exception as e:
            self._log_error("Error calculating strategic value", e, f"nation: {nation.get('nation_name', 'Unknown')}")
            return 0.0

    def _safe_get(self, data: Dict[str, Any], key: str, default: Any = 0, expected_type: type = None) -> Any:
        """Safely get a value from a dictionary with type checking."""
        try:
            value = data.get(key, default)            
            if value is None:
                return default            
            if expected_type is not None:
                if isinstance(expected_type, tuple):
                    if not isinstance(value, expected_type):
                        for t in expected_type:
                            try:
                                return t(value)
                            except (ValueError, TypeError):
                                continue
                        return default
                else:
                    if not isinstance(value, expected_type):
                        try:
                            return expected_type(value)
                        except (ValueError, TypeError):
                            return default
            return value           
        except Exception as e:
            self._log_error(f"Error safely getting value for key '{key}'", e)
            return default

    @commands.hybrid_command(name='nations', description='Display alliance nations with detailed UI')
    @leadership_role_check()
    async def nations_command(self, ctx: commands.Context):
        """Display alliance nations with page navigation and details."""
        try:
            initial_msg = await ctx.send("🔄 Loading Alliance Nations...")
            # Force refresh Cybertr0n alliance data before proceeding (equivalent to refresh_alliance)
            try:
                if hasattr(self, 'query_instance') and self.query_instance:
                    await self.query_instance.get_alliance_nations(
                        str(self.cybertron_alliance_id), bot=self.bot, force_refresh=True
                    )
                    # Also refresh Prime Bank to ensure combined view is fresh
                    if PRIME_BANK_ALLIANCE_ID:
                        await self.query_instance.get_alliance_nations(
                            str(PRIME_BANK_ALLIANCE_ID), bot=self.bot, force_refresh=True
                        )
            except Exception as e:
                self._log_error("Error refreshing Cybertr0n alliance data before nations", e)
            # Fetch nations from Cybertr0n and Prime Bank only
            cybertron_id = str(self.cybertron_alliance_id)
            prime_bank_id = str(PRIME_BANK_ALLIANCE_ID) if 'PRIME_BANK_ALLIANCE_ID' in globals() and PRIME_BANK_ALLIANCE_ID else AERO_ALLIANCES.get('prime_bank', {}).get('id') and str(AERO_ALLIANCES.get('prime_bank', {}).get('id'))
            cybertron_nations = await self.get_alliance_nations(cybertron_id)
            prime_bank_nations = []
            if prime_bank_id:
                prime_bank_nations = await self.get_alliance_nations(prime_bank_id)
            nations = (cybertron_nations or []) + (prime_bank_nations or [])
            # Filter strictly to the two alliance IDs to avoid accidental leakage
            allowed_ids = {cybertron_id}
            if prime_bank_id:
                allowed_ids.add(str(prime_bank_id))
            nations = [n for n in (nations or []) if str(n.get('alliance_id')) in allowed_ids]
            if not nations:
                await initial_msg.edit(content="❌ No nation data available.")
                return
            view = NationListView(nations=nations, author_id=ctx.author.id, bot=self.bot, blitz_cog=self)
            embed = view.create_embed()
            await initial_msg.edit(content=None, embed=embed, view=view)
        except Exception as e:
            self._log_error("Error in nations command", e)
            await ctx.send(f"❌ An error occurred: {str(e)}")

    @commands.hybrid_command(name='blitz', description='Generate blitz parties and show interactive UI')
    @leadership_role_check()
    async def blitz_command(self, ctx: commands.Context, alliances: Optional[str] = None):
        """Generate blitz parties and display them with navigation.
        Optionally provide a comma-separated list of alliance keys (restricted to "cybertron", "prime_bank", or "cybertron_combined")."""
        try:
            initial_msg = await ctx.send("🔄 Generating Blitz Parties...")
            # Force refresh Cybertr0n alliance data before proceeding (equivalent to refresh_alliance)
            try:
                if hasattr(self, 'query_instance') and self.query_instance:
                    await self.query_instance.get_alliance_nations(
                        str(self.cybertron_alliance_id), bot=self.bot, force_refresh=True
                    )
                    # Also refresh Prime Bank to ensure combined view is fresh
                    if 'PRIME_BANK_ALLIANCE_ID' in globals() and PRIME_BANK_ALLIANCE_ID:
                        await self.query_instance.get_alliance_nations(
                            str(PRIME_BANK_ALLIANCE_ID), bot=self.bot, force_refresh=True
                        )
            except Exception as e:
                self._log_error("Error refreshing Cybertr0n alliance data before blitz", e)
            parties = []
            allowed_ids = {str(self.cybertron_alliance_id)}
            prime_id = str(PRIME_BANK_ALLIANCE_ID) if 'PRIME_BANK_ALLIANCE_ID' in globals() and PRIME_BANK_ALLIANCE_ID else None
            if prime_id:
                allowed_ids.add(prime_id)
            if alliances:
                # Sanitize alliance keys to permitted set only
                input_keys = [k.strip().lower() for k in alliances.split(',') if k.strip()]
                permitted = {'cybertron', 'prime_bank', 'cybertron_combined'}
                alliance_keys = [k for k in input_keys if k in permitted]
                if not alliance_keys or 'cybertron_combined' in alliance_keys or set(alliance_keys) == {'cybertron', 'prime_bank'}:
                    # Combined view from both alliances
                    cybertron_nations = await self.get_alliance_nations(str(self.cybertron_alliance_id)) or []
                    prime_bank_nations = await self.get_alliance_nations(prime_id) if prime_id else []
                    nations = [n for n in (cybertron_nations + (prime_bank_nations or [])) if str(n.get('alliance_id')) in allowed_ids]
                    active_nations = self.get_active_nations(nations)
                    parties = self.create_balanced_parties(active_nations)
                elif alliance_keys == ['cybertron']:
                    nations = await self.get_alliance_nations(str(self.cybertron_alliance_id)) or []
                    nations = [n for n in nations if str(n.get('alliance_id')) in allowed_ids]
                    active_nations = self.get_active_nations(nations)
                    parties = self.create_balanced_parties(active_nations)
                elif alliance_keys == ['prime_bank'] and prime_id:
                    nations = await self.get_alliance_nations(prime_id) or []
                    nations = [n for n in nations if str(n.get('alliance_id')) in allowed_ids]
                    active_nations = self.get_active_nations(nations)
                    parties = self.create_balanced_parties(active_nations)
                else:
                    # Fallback to combined
                    cybertron_nations = await self.get_alliance_nations(str(self.cybertron_alliance_id)) or []
                    prime_bank_nations = await self.get_alliance_nations(prime_id) if prime_id else []
                    nations = [n for n in (cybertron_nations + (prime_bank_nations or [])) if str(n.get('alliance_id')) in allowed_ids]
                    active_nations = self.get_active_nations(nations)
                    parties = self.create_balanced_parties(active_nations)
            else:
                # Default to combined Cybertron + Prime Bank parties
                cybertron_nations = await self.get_alliance_nations(str(self.cybertron_alliance_id)) or []
                prime_bank_nations = await self.get_alliance_nations(prime_id) if prime_id else []
                nations = [n for n in (cybertron_nations + (prime_bank_nations or [])) if str(n.get('alliance_id')) in allowed_ids]
                if not nations:
                    await initial_msg.edit(content="❌ No nation data available for party sorting.")
                    return
                active_nations = self.get_active_nations(nations)
                parties = self.create_balanced_parties(active_nations)
            processed_parties, _ = self.process_parties_for_display(parties)
            if not processed_parties:
                await initial_msg.edit(content="❌ Unable to create parties from current data.")
                return
            view = PartyView(parties=processed_parties, blitz_cog=self)
            embed = view.create_embed()
            await initial_msg.edit(content=None, embed=embed, view=view)
        except Exception as e:
            self._log_error("Error in blitz command", e)
            await ctx.send(f"❌ An error occurred: {str(e)}")

async def setup(bot: commands.Bot):
    """Register the BlitzParties cog with the bot."""
    await bot.add_cog(BlitzParties(bot))