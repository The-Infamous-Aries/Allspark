import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import logging
from groq import Groq
from typing import Dict, List, Any, Union, Optional, Tuple
import json
from datetime import datetime, timedelta
from discord.ui import Button, View
import sys
import os
import re
import shutil

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import GROQ_API_KEY

logger = logging.getLogger("allspark.cybertron_games")

DISCORD_CHAR_LIMIT = 2000

# Helper function to break a long message into chunks
async def _send_long_message_in_chunks(channel: discord.TextChannel, content: str, view: View = None):
    """Sends a message, breaking it into chunks <= 2000 characters if necessary."""
    if not content:
        return
        
    chunks = [content[i:i + DISCORD_CHAR_LIMIT] for i in range(0, len(content), DISCORD_CHAR_LIMIT)]
    
    # Send all chunks
    for i, chunk in enumerate(chunks):
        # Only attach the view to the final chunk
        current_view = view if i == len(chunks) - 1 else None
        
        # Use a minimal separator for continuation, or nothing if the first part
        prefix = ""
        if i > 0:
            prefix = "*(... continuation ...)*\n"
            
        await channel.send(content=prefix + chunk, view=current_view)

class CybertronGamesGenerator:
    """AI-powered Transformers-themed Cybertron Games story generator"""
    
    def __init__(self, api_key: str = None):
        """Initialize the AI Cybertron Games Generator with Groq API"""
        self.game_state: Dict[str, Any] = {}
        self.round_history: List[str] = []
        self.faction_tracker = {}   # Track faction assignments
        self.active_games = {}
        self.active_views = {}
        self.eliminated = set()     # Track eliminated warriors
        self.original_participants = {}  # Store original participants for each game
        self.game_states_dir = os.path.join(os.path.dirname(__file__), 'game_states')
        
        # Create game states directory if it doesn't exist
        os.makedirs(self.game_states_dir, exist_ok=True)
        
        if api_key:
            try:
                self.client = Groq(api_key=api_key)
                self.model = "llama-3.1-8b-instant" # or "mixtral-8x7b-32768"
                self.use_ai = True
                logger.info(f"✅ AI initialized successfully with Groq API for Cybertron Games")
            except Exception as e:
                logger.error(f"❌ Failed to initialize AI: {e}")
                self.use_ai = False
                self.model = None
        else:
            logger.warning("⚠️  No API key provided - using fallback cybertronian narratives")
            self.use_ai = False
            self.model = None

    def _get_game_file_path(self, game_key: str) -> str:
        """Get the file path for a game state JSON file"""
        return os.path.join(self.game_states_dir, f'cybertron_game_{game_key}.json')

    def _save_game_state_to_file(self, game_key: str, game_data: Dict[str, Any]) -> bool:
        """Save game state to JSON file"""
        try:
            file_path = self._get_game_file_path(game_key)
            
            # Convert participants to serializable format
            serializable_data = game_data.copy()
            serializable_data['participants'] = [
                {
                    'id': p.id,
                    'name': p.name,
                    'display_name': p.display_name,
                    'bot': p.bot
                }
                for p in game_data['participants']
            ]
            
            # Convert datetime to string
            if 'start_time' in serializable_data and isinstance(serializable_data['start_time'], datetime):
                serializable_data['start_time'] = serializable_data['start_time'].isoformat()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Game state saved to {file_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save game state: {e}")
            return False

    def _load_game_state_from_file(self, game_key: str) -> Optional[Dict[str, Any]]:
        """Load game state from JSON file"""
        try:
            file_path = self._get_game_file_path(game_key)
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                serializable_data = json.load(f)
            
            # Convert participants back to discord.Member objects (simplified version)
            # Note: This will need to be enhanced when loading from actual Discord context
            game_data = serializable_data.copy()
            
            # Convert datetime string back to datetime object
            if 'start_time' in game_data and isinstance(game_data['start_time'], str):
                game_data['start_time'] = datetime.fromisoformat(game_data['start_time'])
            
            # Restore original participants for validation
            if 'participants' in game_data and game_key not in self.original_participants:
                self.original_participants[game_key] = [p.display_name if hasattr(p, 'display_name') else str(p) 
                                                       for p in game_data['participants']]
            
            logger.info(f"✅ Game state loaded from {file_path}")
            return game_data
        except Exception as e:
            logger.error(f"❌ Failed to load game state: {e}")
            return None

    def _delete_game_state_file(self, game_key: str) -> bool:
        """Delete game state JSON file"""
        try:
            file_path = self._get_game_file_path(game_key)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"✅ Game state file deleted: {file_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete game state file: {e}")
            return False

    def _cleanup_old_game_files(self, max_age_hours: int = 24) -> int:
        """Clean up old game state files older than max_age_hours"""
        try:
            cleaned_count = 0
            current_time = datetime.now()
            
            for filename in os.listdir(self.game_states_dir):
                if filename.startswith('cybertron_game_') and filename.endswith('.json'):
                    file_path = os.path.join(self.game_states_dir, filename)
                    try:
                        file_stat = os.stat(file_path)
                        file_age = current_time - datetime.fromtimestamp(file_stat.st_mtime)
                        
                        if file_age > timedelta(hours=max_age_hours):
                            os.remove(file_path)
                            cleaned_count += 1
                            logger.info(f"Cleaned up old game file: {filename}")
                    except Exception as e:
                        logger.warning(f"Could not process file {filename}: {e}")
            
            logger.info(f"Cleaned up {cleaned_count} old game files")
            return cleaned_count
        except Exception as e:
            logger.error(f"Failed to cleanup old game files: {e}")
            return 0

    async def _generate_champion_summary(self, game_data: Dict[str, Any], champion: str) -> str:
        """Generate AI summary of champion's journey"""
        if not self.use_ai:
            return None
        
        try:
            # Get champion's faction and round history
            assignments = game_data['assignments']
            round_history = game_data['round_history']
            
            champion_faction_data = assignments.get(champion, "Unknown")
            if isinstance(champion_faction_data, dict) and 'faction' in champion_faction_data:
                champion_faction = champion_faction_data['faction']
            elif isinstance(champion_faction_data, str):
                champion_faction = champion_faction_data
            else:
                champion_faction = "Unknown"
            
            # Build detailed champion actions per round
            champion_actions = []
            eliminations_caused = []
            faction_changes = []
            
            for round_num, round_data in enumerate(round_history, 1):
                round_info = f"Round {round_num}: "
                
                # Check faction changes
                if "faction_changes" in round_data:
                    for change in round_data["faction_changes"]:
                        if isinstance(change, dict) and change.get("warrior") == champion:
                            faction_changes.append(f"Round {round_num}: Switched from {change.get('from_faction', 'Unknown')} to {change.get('to_faction', 'Unknown')} - {change.get('reason', 'changed allegiances')}")
                
                # Check eliminations caused by champion
                if "eliminated" in round_data:
                    for elimination in round_data["eliminated"]:
                        if isinstance(elimination, dict) and elimination.get("eliminated_by") == champion:
                            eliminations_caused.append(f"Round {round_num}: Eliminated {elimination.get('warrior', 'Unknown')} via {elimination.get('method', 'unknown method')}")
                
                # Extract champion's role from narrative
                if "narrative" in round_data and isinstance(round_data["narrative"], str):
                    narrative = round_data["narrative"]
                    # Look for champion's name in the narrative to extract their actions
                    if champion in narrative:
                        # Extract sentences mentioning the champion
                        sentences = [s.strip() for s in narrative.split('.') if champion in s]
                        if sentences:
                            champion_actions.append(f"Round {round_num}: {'; '.join(sentences)}")
            
            # Build context about champion's journey with detailed actions
            journey_context = f"""
            Cybertron Games Champion Analysis:
            - Champion: {champion}
            - Final Faction: {champion_faction}
            - Total Rounds: {game_data['current_round']}
            - Total Eliminations: {len(game_data['eliminations'])}
            - Rounds Participated: {len(round_history)}
            
            Champion's Detailed Journey:
            
            FACTION CHANGES ({len(faction_changes)}):
            {chr(10).join(faction_changes) if faction_changes else 'No faction changes'}
            
            ELIMINATIONS CAUSED ({len(eliminations_caused)}):
            {chr(10).join(eliminations_caused) if eliminations_caused else 'No direct eliminations recorded'}
            
            ROUND-BY-ROUND ACTIONS:
            {chr(10).join(champion_actions) if champion_actions else 'No specific actions found in narratives'}
            
            Based on this detailed round-by-round analysis of the champion's actions throughout the Cybertron Games, 
            provide a compelling narrative summary of their journey to victory. Focus on:
            1. Their strategic choices and evolution across rounds
            2. Key faction loyalty shifts and their impact
            3. Specific combat achievements and eliminations they caused
            4. How they adapted their tactics round by round
            5. The defining moments that led to their ultimate triumph on Cybertron
            
            Make the narrative specific to their actual recorded actions, not generic praise."""
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a Cybertronian historian documenting the legendary Cybertron Games. Create a compelling narrative of the champion's journey based on their specific recorded actions, eliminations, and faction changes throughout the games."
                    },
                    {
                        "role": "user", 
                        "content": journey_context
                    }
                ],
                temperature=0.7,
                max_tokens=300,
                top_p=1
            )
            
            champion_summary = completion.choices[0].message.content.strip()
            return f"*{champion_summary}*"
            
        except Exception as e:
            logger.error(f"Failed to generate champion summary: {e}")
            return None

    def has_cybertronian_role(self, member: discord.Member) -> bool:
        """Check if a member has any Cybertronian role using the server-specific role ID system"""
        if not member or not member.roles:
            return False
            
        from config import get_role_ids
        
        guild_id = member.guild.id if member.guild else None
        role_ids_config = get_role_ids(guild_id)
        
        cybertronian_roles = []
        for role_name in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']:
            role_ids = role_ids_config.get(role_name, [])
            if isinstance(role_ids, list):
                cybertronian_roles.extend(role_ids)
            elif role_ids:  # Only add non-None, non-zero values
                cybertronian_roles.append(role_ids)
        
        # Filter out any None or 0 values that might have slipped through
        cybertronian_roles = [role_id for role_id in cybertronian_roles if role_id and role_id != 0]
        
        member_role_ids = [role.id for role in member.roles]
        return any(role_id in member_role_ids for role_id in cybertronian_roles)

    def assign_factions(self, warriors: List[Union[str, discord.Member]], faction_count: int = 2) -> Dict[str, Dict[str, str]]:
        """Assign random factions to warriors for the game"""
        
        faction_names = [
            "Autobot", "Decepticon", "Maximal", "Predacon", "Neutral",
            "Seeker", "Wrecker", "Dinobot", "Guardian", "Titan",
            "Cybertronian Knight", "Technobot", "Monsterbot", "Targetmaster",
            "Headmaster", "Powermaster", "Micromaster", "Action Master",
            "Stunticon", "Combaticon", "Constructicon", "Terrorcon",
            "Protectobot", "Aerialbot", "Technobot", "Seacon",
            "Throttlebot", "Clones", "Delorean", "Omnibot",
            "Sparklings", "Scavengers", "Reflectors", "Junkions",
            "Bounty Hunter", "Gladiators", "Science Division", "Explorers",
            "Peacekeepers", "Rebel Alliance", "Black Ops", "Shadow Syndicate"
        ]
        
        factions = faction_names[:faction_count]
        assignments = {}
        
        for i, warrior in enumerate(warriors):
            warrior_name = warrior.display_name if isinstance(warrior, discord.Member) else str(warrior)
            faction = factions[i % len(factions)]
            
            self.faction_tracker[warrior_name] = faction
            assignments[warrior_name] = {"faction": faction}
        
        return assignments

    def _generate_cybertron_round(self, round_num: int, participants: List[discord.Member], previous_round: str = None) -> Dict[str, Any]:
        """Generate a pure Transformers-themed round using AI with structured output"""
        
        if not self.use_ai or not self.model or not hasattr(self, 'client') or not self.client:
            logger.warning(f"AI not available: use_ai={self.use_ai}, model={self.model}, client={getattr(self, 'client', None)}")
            return self._generate_fallback_cybertron_round_structured(round_num, participants)

        alive_tributes = [p.display_name for p in participants]
        
        # Build faction data for the prompt
        faction_prompt_part = ""
        factions_dict = {}
        for p in participants:
            faction = self.faction_tracker.get(p.display_name, 'Neutral')
            if faction not in factions_dict:
                factions_dict[faction] = []
            factions_dict[faction].append(p.display_name)
        
        faction_prompt_part += "**CURRENT FACTIONS:**\n"
        for faction, members in factions_dict.items():
            faction_prompt_part += f"- **{faction}**: {', '.join(members)}\n"

        # Build simple history context
        history_context = ""
        if previous_round:
            history_context = f"\n**LAST ROUND'S NARRATIVE:**\n{previous_round}\n"
        
        # Add elimination history context
        elimination_context = ""
        if self.eliminated:
            elimination_context = f"\n**PREVIOUSLY ELIMINATED WARRIORS (DO NOT INCLUDE IN SURVIVORS):**\n{', '.join(sorted(list(self.eliminated)))}\n"

        prompt = f"""
        You are the **Oracle of Cybertron**, master storyteller for the **Cybertron Games**.
        Create a narrative for ROUND {round_num} involving the remaining sparks.
        
        **CURRENT IGNITED SPARKS:**
        {", ".join(alive_tributes)}
        
        {faction_prompt_part}
        
        {history_context}
        
        {elimination_context}
        
        Your narrative must describe energon-fueled combat, alliance shifts, faction changes, and eliminations. Do not use human terms.
        
        CRITICAL REQUIREMENTS - YOU MUST INCLUDE ALL OF THESE:
        1. faction_descriptions MUST include descriptions for ALL current factions: {list(factions_dict.keys())}
        2. survivors MUST be a complete list of ALL warriors still alive after this round - DO NOT include any warriors listed in PREVIOUSLY ELIMINATED WARRIORS
        3. eliminated MUST include 1-2 eliminations with specific warrior names, who eliminated them, and creative Transformers-themed methods
        IMPORTANT: eliminated_by MUST be a DIFFERENT warrior name from the warrior being eliminated - NEVER use the same name as the warrior being eliminated. Use another warrior's name, "environmental hazard", "energon explosion", "the arena itself", or similar creative causes if no other warriors are available.
        4. faction_changes should include 0-1 changes with specific warrior names and detailed reasons
        5. narrative must be detailed and engaging, at least 2-3 sentences with specific events
        6. Use actual warrior names from: {alive_tributes}
        7. Make eliminations creative (laser cores, energon weapons, transformation failures, etc.)
        8. DO NOT mention or include ANY warriors from the PREVIOUSLY ELIMINATED WARRIORS list in your narrative or survivors list
        
        Return your response in this exact JSON format:
        {{
            "faction_descriptions": {{
                "faction_name": "detailed description of what this faction did this round",
                "another_faction": "detailed description of their specific actions"
            }},
            "faction_changes": [
                {{
                    "warrior": "warrior_name",
                    "from_faction": "old_faction",
                    "to_faction": "new_faction", 
                    "reason": "specific reason for faction change"
                }}
            ],
            "eliminated": [
                {{
                    "warrior": "warrior_name",
                    "eliminated_by": "killer_name or cause",
                    "method": "creative Transformers-themed elimination method"
                }}
            ],
            "survivors": ["complete", "list", "of", "all", "surviving", "warriors"],
            "narrative": "detailed story text describing specific events and actions"
        }}
        
        Make sure to include ALL warriors in the survivors list who are still alive - EXCLUDE any warriors from PREVIOUSLY ELIMINATED WARRIORS.
        RETURN ONLY VALID JSON - NO MARKDOWN FORMATTING OR ADDITIONAL TEXT.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = response.choices[0].message.content.strip()
            
            if not response_text:
                raise ValueError("Empty response from AI")
            
            try:
                structured_data = json.loads(response_text)
                logger.info(f"AI response parsed successfully: {structured_data}")
                
                # Enhanced validation to prevent raw JSON display
                # Check if the parsed data is still a string (indicates raw JSON was returned)
                if isinstance(structured_data, str):
                    logger.warning(f"AI returned raw JSON string instead of structured data: {structured_data[:200]}...")
                    self._process_narrative(response_text, participants)
                    return self._convert_text_to_structured(response_text, participants)
                
                # Validate the structure of the data
                if not isinstance(structured_data, dict):
                    logger.warning(f"AI response is not a dictionary, falling back to text parsing")
                    self._process_narrative(response_text, participants)
                    return self._convert_text_to_structured(response_text, participants)
                
                # Validate required fields and their types
                required_fields = {
                    'faction_descriptions': dict,
                    'faction_changes': list,
                    'eliminated': list,
                    'survivors': list,
                    'narrative': str
                }
                
                for field, expected_type in required_fields.items():
                    if field in structured_data:
                        if not isinstance(structured_data[field], expected_type):
                            logger.warning(f"Field '{field}' has wrong type: expected {expected_type}, got {type(structured_data[field])}")
                            if field == 'narrative':
                                structured_data[field] = "The battle continues with various warriors taking action."
                            elif field in ['faction_changes', 'eliminated', 'survivors']:
                                structured_data[field] = []
                            elif field == 'faction_descriptions':
                                structured_data[field] = {}
                    else:
                        logger.warning(f"Missing required field '{field}' in AI response")
                        if field == 'narrative':
                            structured_data[field] = "The battle continues with various warriors taking action."
                        elif field in ['faction_changes', 'eliminated', 'survivors']:
                            structured_data[field] = []
                        elif field == 'faction_descriptions':
                            structured_data[field] = {}
                
                # Additional validation for narrative to ensure it doesn't contain raw JSON
                if 'narrative' in structured_data and isinstance(structured_data['narrative'], str):
                    narrative = structured_data['narrative'].strip()
                    if narrative.startswith(('{', '[')) or '```json' in narrative.lower():
                        logger.warning(f"Narrative contains raw JSON: {narrative[:200]}...")
                        structured_data['narrative'] = "The battle continues with various warriors taking action."
                
                # Validate survivors list contains proper strings
                if 'survivors' in structured_data and isinstance(structured_data['survivors'], list):
                    valid_survivors = []
                    for survivor in structured_data['survivors']:
                        if isinstance(survivor, str) and not survivor.startswith(('{', '[')):
                            valid_survivors.append(survivor)
                        else:
                            logger.warning(f"Invalid survivor entry (contains JSON): {survivor}")
                    structured_data['survivors'] = valid_survivors
                
                # Validate faction descriptions don't contain raw JSON
                if 'faction_descriptions' in structured_data and isinstance(structured_data['faction_descriptions'], dict):
                    valid_descriptions = {}
                    for faction, description in structured_data['faction_descriptions'].items():
                        if isinstance(description, str) and not description.startswith(('{', '[')):
                            valid_descriptions[faction] = description
                        else:
                            logger.warning(f"Invalid faction description for {faction} (contains JSON): {description}")
                            valid_descriptions[faction] = f"The {faction} faction acted this round."
                    structured_data['faction_descriptions'] = valid_descriptions
                
                # Ensure eliminations is a list of dictionaries, not raw text
                if "eliminated" in structured_data and not isinstance(structured_data["eliminated"], list):
                    logger.warning(f"Eliminations field is not a list, attempting to fix")
                    structured_data["eliminated"] = []
                
                # Validate each elimination entry
                if "eliminated" in structured_data and isinstance(structured_data["eliminated"], list):
                    valid_eliminations = []
                    for elimination in structured_data["eliminated"]:
                        if isinstance(elimination, dict) and "warrior" in elimination:
                            valid_eliminations.append(elimination)
                        else:
                            logger.warning(f"Invalid elimination entry: {elimination}")
                    structured_data["eliminated"] = valid_eliminations
                
                # Ensure complete data before processing
                structured_data = self._ensure_complete_data(structured_data, participants)
                
                self._process_structured_narrative(structured_data, participants)
                logger.info(f"✅ AI generated structured Cybertron Round {round_num} successfully")
                return structured_data
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed for round {round_num}, falling back to text parsing: {e}")
                self._process_narrative(response_text, participants)
                structured_data = self._convert_text_to_structured(response_text, participants)
                return self._ensure_complete_data(structured_data, participants)
            
        except Exception as e:
            logger.error(f"❌ AI generation failed: {e}, using enhanced cybertronian fallback")
            fallback_data = self._generate_fallback_cybertron_round_structured(round_num, participants)
            return self._ensure_complete_data(fallback_data, participants)

    def _process_structured_narrative(self, structured_data: Dict[str, Any], participants: List[discord.Member]):
        """Process structured narrative data from AI"""
        # Process faction changes
        if "faction_changes" in structured_data:
            for change in structured_data["faction_changes"]:
                warrior = change.get("warrior", "")
                to_faction = change.get("to_faction", "Neutral")
                if warrior:
                    self.faction_tracker[warrior] = to_faction
                    logger.info(f"Faction change: {warrior} -> {to_faction}")
        
        # Process eliminations
        eliminated_this_round = []
        if "eliminated" in structured_data:
            for elimination in structured_data["eliminated"]:
                if isinstance(elimination, dict):
                    warrior = elimination.get("warrior", "")
                    eliminated_by = elimination.get("eliminated_by", "unknown")
                    method = elimination.get("method", "unknown method")
                    
                    if warrior:
                        eliminated_this_round.append(warrior)
                        logger.info(f"Eliminated: {warrior} by {eliminated_by} via {method}")
                else:
                    logger.warning(f"Invalid elimination entry: {elimination}")
        
        # Update participant tracking
        current_participants = [p.display_name for p in participants]
        for warrior in eliminated_this_round:
            if warrior in current_participants:
                self.eliminated.add(warrior)
        
        logger.info(f"Processed structured narrative: {len(structured_data.get('faction_changes', []))} faction changes, {len(eliminated_this_round)} eliminations")

    def _convert_text_to_structured(self, story_text: str, participants: List[discord.Member]) -> Dict[str, Any]:
        """Convert old text format to structured format"""
        # This is a fallback method to convert text to structured format
        structured = {
            "faction_descriptions": {},
            "faction_changes": [],
            "eliminated": [],
            "survivors": [],
            "narrative": story_text
        }
        
        # Try to extract survivors (everyone not eliminated)
        current_names = [p.display_name for p in participants]
        eliminated_names = list(self.eliminated)
        structured["survivors"] = [name for name in current_names if name not in eliminated_names]
        
        # Try to parse faction changes and eliminations from text (basic parsing)
        # This is a simplified version - in production you'd want more sophisticated parsing
        lines = story_text.split('\n')
        for line in lines:
            line = line.strip()
            # Look for elimination patterns
            if any(keyword in line.lower() for keyword in ['eliminated', 'defeated', 'destroyed', 'fallen']):
                # Basic extraction - this could be improved
                for name in current_names:
                    if name in line and name not in eliminated_names:
                        structured["eliminated"].append({
                            "warrior": name,
                            "eliminated_by": "unknown",
                            "method": line
                        })
                        break
        
        return structured

    def _validate_round_data_against_original_participants(self, structured_data: Dict[str, Any], original_participants: List[discord.Member]) -> Dict[str, Any]:
        """Validate that all names in the generated round data are from the original participant list"""
        original_names = [p.display_name for p in original_participants]
        
        # Validate survivors
        if 'survivors' in structured_data and isinstance(structured_data['survivors'], list):
            valid_survivors = []
            for survivor in structured_data['survivors']:
                if isinstance(survivor, str) and survivor in original_names:
                    valid_survivors.append(survivor)
                else:
                    logger.warning(f"Invalid survivor '{survivor}' - not in original participants")
            structured_data['survivors'] = valid_survivors
        
        # Validate eliminations
        if 'eliminated' in structured_data and isinstance(structured_data['eliminated'], list):
            valid_eliminations = []
            for elimination in structured_data['eliminated']:
                if isinstance(elimination, dict) and 'warrior' in elimination:
                    warrior = elimination['warrior']
                    if warrior in original_names:
                        # Also validate eliminated_by field
                        eliminated_by = elimination.get('eliminated_by', 'unknown')
                        if eliminated_by != 'unknown' and eliminated_by not in original_names:
                            logger.warning(f"Invalid eliminated_by '{eliminated_by}' - not in original participants, changing to 'unknown'")
                            elimination['eliminated_by'] = 'unknown'
                        valid_eliminations.append(elimination)
                    else:
                        logger.warning(f"Invalid elimination warrior '{warrior}' - not in original participants")
            structured_data['eliminated'] = valid_eliminations
        
        # Validate faction changes
        if 'faction_changes' in structured_data and isinstance(structured_data['faction_changes'], list):
            valid_changes = []
            for change in structured_data['faction_changes']:
                if isinstance(change, dict) and 'warrior' in change:
                    warrior = change['warrior']
                    if warrior in original_names:
                        valid_changes.append(change)
                    else:
                        logger.warning(f"Invalid faction change warrior '{warrior}' - not in original participants")
            structured_data['faction_changes'] = valid_changes
        
        # Validate faction descriptions (ensure they only mention original participants)
        if 'faction_descriptions' in structured_data and isinstance(structured_data['faction_descriptions'], dict):
            for faction, description in structured_data['faction_descriptions'].items():
                if isinstance(description, str):
                    # Check if description mentions any non-original names
                    for word in description.split():
                        # Remove punctuation
                        clean_word = word.strip('.,!?*•-()[]{}')
                        if clean_word in original_names or clean_word.lower() in [name.lower() for name in original_names]:
                            continue
                        # If it's a capitalized word that might be a name, check if it's in original names
                        elif clean_word.istitle() and len(clean_word) > 2:
                            # Check case-insensitive match
                            name_found = False
                            for orig_name in original_names:
                                if clean_word.lower() in orig_name.lower() or orig_name.lower() in clean_word.lower():
                                    name_found = True
                                    break
                            if not name_found:
                                logger.warning(f"Potential invalid name '{clean_word}' in faction description for {faction}")
        
        return structured_data

    def _ensure_complete_data(self, structured_data: Dict[str, Any], participants: List[discord.Member]) -> Dict[str, Any]:
        """Ensure all required data fields are present and properly formatted"""
        
        # First validate against original participants
        structured_data = self._validate_round_data_against_original_participants(structured_data, participants)
        
        # Ensure all required fields exist
        required_fields = ['faction_descriptions', 'faction_changes', 'eliminated', 'survivors', 'narrative']
        for field in required_fields:
            if field not in structured_data:
                structured_data[field] = {} if field == 'faction_descriptions' else []
                if field == 'narrative':
                    structured_data[field] = "The battle continues with various warriors taking action."
        
        # Ensure faction descriptions exist for all current factions
        current_factions = set()
        for p in participants:
            faction = self.faction_tracker.get(p.display_name, 'Neutral')
            current_factions.add(faction)
        
        if not isinstance(structured_data['faction_descriptions'], dict):
            structured_data['faction_descriptions'] = {}
        
        # Add missing faction descriptions
        for faction in current_factions:
            if faction not in structured_data['faction_descriptions']:
                actions = [
                    "conducted energon reconnaissance",
                    "fortified their position", 
                    "launched a strategic assault",
                    "defended their territory",
                    "searched for allies"
                ]
                structured_data['faction_descriptions'][faction] = f"The {faction} faction {random.choice(actions)} this round."
        
        # Ensure survivors list is accurate
        current_names = [p.display_name for p in participants]
        if not isinstance(structured_data['survivors'], list):
            structured_data['survivors'] = []
        
        # Filter survivors to only include current participants
        valid_survivors = []
        for survivor in structured_data['survivors']:
            if isinstance(survivor, str) and survivor in current_names and survivor not in self.eliminated:
                valid_survivors.append(survivor)
        
        # Add any missing survivors
        for name in current_names:
            if name not in self.eliminated and name not in valid_survivors:
                valid_survivors.append(name)
        
        structured_data['survivors'] = valid_survivors
        
        # Ensure eliminations are properly formatted
        if not isinstance(structured_data['eliminated'], list):
            structured_data['eliminated'] = []
        
        valid_eliminations = []
        for elimination in structured_data['eliminated']:
            if isinstance(elimination, dict) and 'warrior' in elimination:
                warrior = elimination.get('warrior', 'Unknown')
                eliminated_by = elimination.get('eliminated_by', 'unknown')
                method = elimination.get('method', 'unknown method')
                
                # Fix self-eliminations - if eliminated_by is the same as warrior, use a different cause
                if eliminated_by == warrior or eliminated_by.lower() in ['self', 'themselves', warrior.lower()]:
                    # Use environmental causes instead
                    environmental_causes = [
                        "Arena hazards", "Environmental disaster", "Cybertron itself", 
                        "The AllSpark", "Energon explosion", "Transformation malfunction",
                        "Arena trap", "Environmental hazard", "The planet itself"
                    ]
                    eliminated_by = random.choice(environmental_causes)
                
                # Ensure all required fields are present
                valid_elimination = {
                    'warrior': warrior,
                    'eliminated_by': eliminated_by,
                    'method': method
                }
                valid_eliminations.append(valid_elimination)
        structured_data['eliminated'] = valid_eliminations
        
        # Ensure faction changes are properly formatted
        if not isinstance(structured_data['faction_changes'], list):
            structured_data['faction_changes'] = []
        
        valid_changes = []
        for change in structured_data['faction_changes']:
            if isinstance(change, dict) and 'warrior' in change:
                # Ensure all required fields are present
                valid_change = {
                    'warrior': change.get('warrior', 'Unknown'),
                    'from_faction': change.get('from_faction', 'Neutral'),
                    'to_faction': change.get('to_faction', 'Neutral'),
                    'reason': change.get('reason', 'changed allegiances')
                }
                valid_changes.append(valid_change)
        structured_data['faction_changes'] = valid_changes
        
        # Ensure narrative is a proper string
        if not isinstance(structured_data['narrative'], str) or not structured_data['narrative'].strip():
            structured_data['narrative'] = "The battle on Cybertron continues as warriors clash in epic combat."
        
        return structured_data

    def _generate_fallback_cybertron_round_structured(self, round_num: int, participants: List[discord.Member]) -> Dict[str, Any]:
        """Generate structured fallback round when AI is unavailable"""
        # Get current factions
        factions_dict = {}
        for p in participants:
            faction = self.faction_tracker.get(p.display_name, 'Neutral')
            if faction not in factions_dict:
                factions_dict[faction] = []
            factions_dict[faction].append(p.display_name)
        
        # Generate faction descriptions
        faction_descriptions = {}
        for faction, members in factions_dict.items():
            actions = [
                f"conducted energon reconnaissance",
                f"fortified their position",
                f"launched a strategic assault", 
                f"defended their territory",
                f"searched for allies"
            ]
            faction_descriptions[faction] = f"The {faction} faction {random.choice(actions)} this round."
        
        # Generate random eliminations (1-2 per round)
        current_names = [p.display_name for p in participants]
        available_targets = [name for name in current_names if name not in self.eliminated]
        
        eliminated_this_round = []
        if len(available_targets) > 3 and random.random() < 0.7:  # 70% chance of elimination
            num_eliminations = min(random.randint(1, 2), len(available_targets) - 2)
            for _ in range(num_eliminations):
                if available_targets:
                    eliminated = random.choice(available_targets)
                    # Find a valid eliminator (not the same person)
                    potential_eliminators = [name for name in available_targets if name != eliminated]
                    if potential_eliminators:
                        eliminator = random.choice(potential_eliminators)
                    else:
                        # If no other targets available, use environmental causes
                        eliminator = random.choice(["Arena hazards", "Environmental disaster", "Cybertron itself", "The AllSpark"])
                    
                    eliminated_this_round.append({
                        "warrior": eliminated,
                        "eliminated_by": eliminator,
                        "method": random.choice(["energon blast", "melee combat", "tactical maneuver", "faction betrayal", "arena trap", "energon explosion"])
                    })
                    self.eliminated.add(eliminated)
                    available_targets.remove(eliminated)
        
        # Generate faction changes (occasional)
        faction_changes = []
        if random.random() < 0.3:  # 30% chance of faction change
            if available_targets:
                changer = random.choice(available_targets)
                current_faction = self.faction_tracker.get(changer, 'Neutral')
                available_factions = ['Autobots', 'Decepticons', 'Neutral']
                if current_faction in available_factions:
                    available_factions.remove(current_faction)
                if available_factions:
                    new_faction = random.choice(available_factions)
                    self.faction_tracker[changer] = new_faction
                    faction_changes.append({
                        "warrior": changer,
                        "from_faction": current_faction,
                        "to_faction": new_faction,
                        "reason": random.choice(["switched allegiances", "was convinced by allies", "saw the truth", "joined for survival"])
                    })
        
        # Generate comprehensive narrative text with all data
        narrative_parts = []
        narrative_parts.append(f"🌌 **ROUND {round_num} - CYBERTRON GAMES** 🌌")
        
        # Add faction descriptions with potential cooperation language
        if faction_descriptions:
            narrative_parts.append("\n**⚔️ FACTION ACTIONS:**")
            for faction, description in faction_descriptions.items():
                narrative_parts.append(f"• {description}")
        
        # Add faction changes with cooperation indicators
        if faction_changes:
            narrative_parts.append("\n**🔄 FACTION CHANGES:**")
            for change in faction_changes:
                # Add cooperation language for faction changes
                cooperation_phrases = ["joined forces with", "united with", "allied with", "cooperated with"]
                narrative_parts.append(f"• **{change['warrior']}** {change['reason']} and {random.choice(cooperation_phrases)} the **{change['to_faction']}**")
        
        # Add eliminations with cooperation detection potential
        if eliminated_this_round:
            narrative_parts.append("\n**💀 ELIMINATIONS:**")
            for elimination in eliminated_this_round:
                # Use language that can indicate cooperation
                cooperation_methods = [
                    "via combined assault",
                    "through united effort", 
                    "with team coordination",
                    "using joint tactics",
                    "in cooperative strike"
                ]
                if len(available_targets) > 2 and random.random() < 0.3:  # 30% chance of cooperation language
                    method = random.choice(cooperation_methods)
                else:
                    method = elimination['method']
                narrative_parts.append(f"• **{elimination['warrior']}** was eliminated by **{elimination['eliminated_by']}** {method}")
        
        # Add survivors summary with potential peace indicators
        if available_targets:
            peace_phrases = [
                f"\n**🔥 SURVIVORS ({len(available_targets)}):** {', '.join(available_targets)}",
                f"\n**🔥 WARRIORS REMAINING ({len(available_targets)}):** {', '.join(available_targets)}",
                f"\n**🔥 COMBATANTS SURVIVE ({len(available_targets)}):** {', '.join(available_targets)}"
            ]
            narrative_parts.append(random.choice(peace_phrases))
        
        # Add round statistics
        total_participants = len(current_names)
        eliminated_count = len(eliminated_this_round)
        survival_rate = (len(available_targets) / total_participants * 100) if total_participants > 0 else 0
        narrative_parts.append(f"\n**📊 ROUND STATS:** {eliminated_count} eliminated, {len(available_targets)} remaining ({survival_rate:.1f}% survival rate)")
        
        return {
            "faction_descriptions": faction_descriptions,
            "faction_changes": faction_changes,
            "eliminated": eliminated_this_round,
            "survivors": available_targets,
            "narrative": '\n'.join(narrative_parts)
        }

    def _process_narrative(self, story_text: str, participants: List[discord.Member]) -> Dict[str, Any]:
        """Parse AI-generated text to extract all structured data"""
        eliminated = []
        faction_changes = []
        faction_descriptions = {}
        
        # Parse faction descriptions from narrative
        current_section = None
        for line in story_text.split('\n'):
            line = line.strip()
            if 'AUTOBOTS:' in line.upper() or 'AUTOBOT' in line.upper():
                current_section = 'autobots'
                if line and not line.startswith('**'):
                    faction_descriptions['Autobots'] = line.strip('*•- ')
            elif 'DECEPTICONS:' in line.upper() or 'DECEPTICON' in line.upper():
                current_section = 'decepticons'
                if line and not line.startswith('**'):
                    faction_descriptions['Decepticons'] = line.strip('*•- ')
            elif 'NEUTRAL:' in line.upper() or 'NEUTRAL' in line.upper():
                current_section = 'neutral'
                if line and not line.startswith('**'):
                    faction_descriptions['Neutral'] = line.strip('*•- ')
            elif current_section and line and not line.startswith('**'):
                # Continue building faction description
                if current_section == 'autobots' and 'Autobots' in faction_descriptions:
                    faction_descriptions['Autobots'] += ' ' + line.strip('*•- ')
                elif current_section == 'decepticons' and 'Decepticons' in faction_descriptions:
                    faction_descriptions['Decepticons'] += ' ' + line.strip('*•- ')
                elif current_section == 'neutral' and 'Neutral' in faction_descriptions:
                    faction_descriptions['Neutral'] += ' ' + line.strip('*•- ')
        
        # Parse eliminations with detailed information
        elimination_lines = [line.strip() for line in story_text.split('\n') if 'eliminated' in line.lower() or 'defeated' in line.lower() or 'fallen' in line.lower()]
        for line in elimination_lines:
            if any(keyword in line.lower() for keyword in ['eliminated', 'defeated', 'destroyed', 'fallen']):
                # Extract warrior name, method, and eliminated_by
                warrior = ""
                method = ""
                eliminated_by = "unknown"
                
                # Remove formatting characters
                clean_line = line.strip('*•- ')
                
                # Try to extract warrior name (usually first part)
                if ' was ' in clean_line:
                    warrior = clean_line.split(' was ')[0].strip()
                elif ' eliminated ' in clean_line:
                    parts = clean_line.split(' eliminated ')
                    if len(parts) >= 2:
                        warrior = parts[0].strip()
                        method = parts[1].strip()
                
                # Try to extract method and eliminated_by
                if ' by ' in clean_line:
                    parts = clean_line.split(' by ')
                    if len(parts) >= 2:
                        eliminated_by = parts[1].split()[0].strip('.,!*')
                        method = ' '.join(clean_line.split(' ')[-3:]) if len(clean_line.split(' ')) >= 3 else "unknown method"
                
                if warrior and warrior not in [e["warrior"] for e in eliminated]:
                    eliminated.append({
                        "warrior": warrior,
                        "method": method or "unknown method",
                        "eliminated_by": eliminated_by
                    })
        
        # Parse faction changes with detailed information
        faction_lines = [line.strip() for line in story_text.split('\n') if 'joined' in line.lower() or 'faction' in line.lower() or 'switched' in line.lower()]
        for line in faction_lines:
            if any(keyword in line.lower() for keyword in ['joined', 'switched', 'changed']):
                parts = line.split('joined') if 'joined' in line.lower() else line.split('switched')
                if len(parts) >= 2:
                    warrior = parts[0].strip().strip('*•- ')
                    faction_info = parts[1].strip().strip('*•- ')
                    
                    # Extract faction name
                    faction_words = faction_info.split()
                    for word in faction_words:
                        if word.upper() in ['AUTOBOTS', 'DECEPTICONS', 'NEUTRAL']:
                            faction = word.capitalize()
                            from_faction = self.faction_tracker.get(warrior, "Neutral")
                            
                            faction_changes.append({
                                "warrior": warrior,
                                "to_faction": faction,
                                "from_faction": from_faction,
                                "reason": "narrative decision"
                            })
                            self.faction_tracker[warrior] = faction
                            break
        
        # Update eliminated set
        for elimination in eliminated:
            self.eliminated.add(elimination["warrior"])
        
        return {
            "eliminated": eliminated,
            "faction_changes": faction_changes,
            "faction_descriptions": faction_descriptions
        }
        
    def _generate_fallback_cybertron_round(self, round_num: int, participants: List[discord.Member]) -> str:
        """Generate a Transformers-themed fallback round when AI generation fails."""
        eliminations = []
        story_text = f"🌌 **CYBERTRON GAMES - ROUND {round_num}** 🌌\n\n"
        
        if len(participants) > 1:
            num_to_eliminate = random.randint(1, min(2, len(participants) - 1))
            random_eliminated = random.sample(participants, num_to_eliminate)
            
            # Enhanced Transformers-themed elimination methods
            elimination_methods = [
                "was overloaded with a devastating dark energon blast",
                "was caught in a catastrophic plasma conduit explosion", 
                "had their spark core disrupted by a cunning enemy's ion cannon",
                "was crushed by falling debris from a collapsing energon refinery",
                "fell into a pit of molten cybermatter during fierce combat",
                "was short-circuited by an electromagnetic pulse weapon",
                "had their transformation cog damaged beyond repair",
                "was overwhelmed by a swarm of mechanical scraplets",
                "was frozen solid by a cryo-cannon blast",
                "had their energon supply drained by a parasitic techno-virus",
                "was vaporized by a concentrated photon beam",
                "fell victim to a booby-trapped energon cache",
                "was crushed in the gears of a massive mechanical trap",
                "had their neural circuits scrambled by a logic bomb",
                "was consumed by unstable synthetic energon"
            ]
            
            # Get current survivors from game state
            survivors = set(self.game_state.get('survivors', []))
            
            for eliminated_warrior in random_eliminated:
                killer = random.choice([p for p in participants if p != eliminated_warrior])
                method = random.choice(elimination_methods)
                
                story_text += f"⚡ **{eliminated_warrior.display_name}** {method} and was eliminated from the Cybertron Games by **{killer.display_name}**.\n\n"
                
                # Update game state directly
                warrior_name = eliminated_warrior.display_name
                if warrior_name in survivors:
                    survivors.discard(warrior_name)
                    if 'eliminations' in self.game_state and warrior_name not in self.game_state['eliminations']:
                        self.game_state['eliminations'].append(warrior_name)
                
                eliminations.append(eliminated_warrior)
            
            # Update game state survivors
            if 'survivors' in self.game_state:
                self.game_state['survivors'] = list(survivors)
            
            remaining_warriors = [p for p in participants if p not in eliminations]
            
            # Add faction changes randomly for some survivors (10% chance)
            if self.game_state.get('assignments') and len(remaining_warriors) > 0:
                # Get allowed factions from game state
                allowed_factions = []
                for faction_data in self.game_state.get('assignments', {}).values():
                    if isinstance(faction_data, dict) and 'faction' in faction_data:
                        faction = faction_data['faction']
                        if faction not in allowed_factions:
                            allowed_factions.append(faction)
                
                if allowed_factions:
                    for warrior in remaining_warriors:
                        # 10% chance of faction change
                        if random.random() < 0.1:
                            warrior_name = warrior.display_name
                            current_faction = self.faction_tracker.get(warrior_name)
                            available_factions = [f for f in allowed_factions if f != current_faction]
                            
                            if available_factions:
                                new_faction = random.choice(available_factions)
                                self.faction_tracker[warrior_name] = new_faction
                                story_text += f"⚙️ **{warrior_name}** has defected to the **{new_faction}** faction!\n\n"
            
            story_text += f"🤖 **Remaining Cybertronian Warriors:** {', '.join([p.display_name for p in remaining_warriors])}\n"
            story_text += f"💀 **Sparks Extinguished This Round:** {len(eliminations)}"

        else:
            story_text += f"👑 **VICTORY ACHIEVED!** 👑\n\n"
            story_text += f"Only one warrior's spark still burns bright: **{participants[0].display_name}**. "
            story_text += f"They stand triumphant as the ultimate champion of the Cybertron Games, their energon reserves intact and their will unbroken!"
        
        logger.info(f"✅ Fallback Cybertron Round {round_num} generated successfully")
        return story_text

    async def initialize_game(
        self,
        ctx: commands.Context,
        include_bots: bool = False,
        warriors: int = 0,
        factions: int = 5,
        specific_participants: str = None,
        cybertronian_only: bool = False
    ):
        """Handle the /cybertron_games command logic"""
        game_key = str(ctx.channel.id)
        
        if game_key in self.active_games:
            embed = discord.Embed(
                title="⚡ A GAME IS ALREADY IN PROGRESS ⚡",
                description="Please wait for the current Cybertron Games to finish.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        guild_members = ctx.guild.members
        participants = []
        
        if specific_participants:
            user_ids = []
            for part in specific_participants.split():
                try:
                    user_id = int(part.replace('<@!', '').replace('<@', '').replace('>', ''))
                    user_ids.append(user_id)
                except ValueError:
                    pass
            
            participants = [m for m in guild_members if m.id in user_ids]
            
        else:
            participants = [m for m in guild_members if (include_bots or not m.bot)]
        
        if cybertronian_only:
            participants = [m for m in participants if self.has_cybertronian_role(m)]
            if len(participants) == 0:
                embed = discord.Embed(
                    title="⚡ NO CYBERTRONIAN WARRIORS FOUND ⚡",
                    description="No members with Cybertronian roles (Autobot, Decepticon, Maverick, or Cybertronian_Citizen) were found!",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return
            
        if 2 <= warriors <= 50 and warriors <= len(participants):
            participants = random.sample(participants, warriors)
        elif warriors > len(participants):
            await ctx.send(f"Not enough warriors available. Only found {len(participants)}.")
            return
        
        if len(participants) < 2:
            embed = discord.Embed(
                title="⚡ INSUFFICIENT WARRIORS ⚡",
                description="Need at least 2 cybertronian warriors to start the games!",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return

        assignments = self.assign_factions(participants, factions)
        
        self.game_state = {
            'participants': participants,
            'assignments': assignments,
            'survivors': [p.display_name for p in participants],
            'eliminations': [],
            'current_round': 0,
            'round_history': [],
            'start_time': datetime.now()
        }
        self.active_games[game_key] = self.game_state
        
        # Store original participants for validation
        self.original_participants[game_key] = [p.display_name for p in participants]
        
        # Save initial state to JSON file
        self._save_game_state_to_file(game_key, self.game_state)
        
        embed = discord.Embed(
            title="⚡ THE CYBERTRON GAMES HAVE BEEN INITIATED ⚡",
            description="*The ancient Arena of Cybertron stirs to life, its energon-powered systems humming with anticipation. Warriors from across the galaxy prepare for the ultimate test of survival...*\n\n🔥 **Click START GAMES to begin the first round of combat!** 🔥",
            color=0x00aaff
        )
        
        factions_text = "\n".join(
            f"⚔️ **{faction_name}** - {len(faction_participants)} warriors" 
            for faction_name, faction_participants in self._get_factions(participants).items()
        )
        embed.add_field(name="🤖 CYBERTRONIAN FACTIONS", value=factions_text, inline=False)
        embed.add_field(name="⚡ Total Warriors", value=f"**{len(participants)}** brave souls", inline=True)
        embed.add_field(name="🌌 Arena Status", value="**ENERGIZED & READY**", inline=True)
        embed.set_footer(text="May the AllSpark guide the worthy to victory...")
        
        view = CybertronGamesView(self, game_key, game_state="setup")
        self.active_views[game_key] = view
        
        view.message = await ctx.send(embed=embed, view=view)

    async def _advance_cybertron_round(self, game_key: str, interaction: discord.Interaction = None, channel: discord.TextChannel = None):
        """Advance to the next round of the Cybertron Games"""
        try:
            target_channel = interaction.channel if interaction else channel
            
            game_data = self.active_games[game_key]
            game_data['current_round'] += 1

            current_participants = [p for p in game_data['participants'] if p.display_name in game_data['survivors']]
            
            # Check for various ending conditions
            should_end, ending_reason = self._check_ending_conditions(game_data, current_participants)
            
            if should_end or len(current_participants) <= 1:
                await self._end_cybertron_games(game_key, interaction, channel, ending_reason)
                return

            previous_survivors_count = len(game_data['survivors'])
            previous_eliminations_count = len(game_data.get('eliminations', []))

            round_data = self._generate_cybertron_round(
                game_data['current_round'], 
                current_participants, 
                previous_round=game_data['round_history'][-1] if game_data['round_history'] else None
            )

            game_data['round_history'].append(round_data)

            if "eliminated" in round_data and round_data["eliminated"]:
                logger.info(f"Processing eliminations: {len(round_data['eliminated'])} eliminations found")

                if 'eliminations' not in game_data:
                    game_data['eliminations'] = []
                
                for elimination in round_data["eliminated"]:
                    if isinstance(elimination, dict):
                        warrior = elimination.get('warrior', 'Unknown')
                        if warrior and warrior not in game_data['eliminations']:
                            game_data['eliminations'].append(warrior)
                            if warrior in game_data['survivors']:
                                game_data['survivors'].remove(warrior)
                                logger.info(f"Removed {warrior} from survivors list")

            total_eliminations = len(game_data.get('eliminations', []))

            # Calculate remaining warriors AFTER processing eliminations
            remaining_warriors = [p for p in game_data['participants'] if p.display_name in game_data['survivors']]

            new_eliminations_count = previous_survivors_count - len(remaining_warriors)
            
            # Track eliminations that happened specifically in this round
            current_round_eliminations = []
            if "eliminated" in round_data and round_data["eliminated"]:
                for elimination in round_data["eliminated"]:
                    if isinstance(elimination, dict):
                        warrior = elimination.get('warrior', 'Unknown')
                        if warrior:
                            current_round_eliminations.append(warrior)

            view = self.active_views.get(game_key)

            # Build recap text after processing eliminations for accurate counts
            recap_text = f"**Round {game_data['current_round']}** has begun! "
            if new_eliminations_count > 0:
                recap_text += f"**{new_eliminations_count}** warrior{'s' if new_eliminations_count != 1 else ''} fell this round. "
            recap_text += f"**{len(remaining_warriors)}** remain standing from **{len(game_data['participants'])}** original combatants."
            
            if "faction_descriptions" in round_data and round_data["faction_descriptions"]:
                active_factions = len(round_data["faction_descriptions"])
                recap_text += f" **{active_factions}** faction{'s' if active_factions != 1 else ''} took action."
            
            # Initialize text variables for different sections
            faction_desc_text = ""
            faction_change_text = ""
            elimination_text = ""
            narrative_text = ""
            survivor_text = ""
            faction_total_text = ""
            elimination_summary = ""
            
            # Build faction descriptions text
            if "faction_descriptions" in round_data and round_data["faction_descriptions"]:
                if isinstance(round_data["faction_descriptions"], dict):
                    for faction, description in round_data["faction_descriptions"].items():
                        if isinstance(description, str):
                            faction_desc_text += f"• **{faction}**: {description}\n"
                        else:
                            logger.warning(f"Invalid faction description for {faction}: {description}")
                            faction_desc_text += f"• **{faction}**: The {faction} faction acted this round.\n"
                else:
                    logger.warning(f"Faction descriptions is not a dictionary: {round_data['faction_descriptions']}")
            
            # Build faction changes text
            if "faction_changes" in round_data and round_data["faction_changes"]:
                if isinstance(round_data["faction_changes"], list):
                    for change in round_data["faction_changes"]:
                        if isinstance(change, dict) and all(key in change for key in ['warrior', 'from_faction', 'to_faction', 'reason']):
                            faction_change_text += f"• **{change['warrior']}** left {change['from_faction']} for {change['to_faction']} ({change['reason']})\n"
                        else:
                            logger.warning(f"Invalid faction change entry: {change}")
                            if isinstance(change, dict) and 'warrior' in change:
                                faction_change_text += f"• **{change['warrior']}** changed factions\n"
                else:
                    logger.warning(f"Faction changes is not a list: {round_data['faction_changes']}")
            
            # Build eliminations text (eliminations already processed above)
            if "eliminated" in round_data and round_data["eliminated"]:
                logger.info(f"Building elimination text: {len(round_data['eliminated'])} eliminations found")
                
                for elimination in round_data["eliminated"]:
                    logger.info(f"Elimination data: {elimination}")
                    
                    # Ensure elimination is a dictionary and not raw JSON text
                    if isinstance(elimination, dict):
                        warrior = elimination.get('warrior', 'Unknown')
                        eliminated_by = elimination.get('eliminated_by', 'unknown')
                        method = elimination.get('method', 'unknown method')
                        
                        # Ensure we have valid data and format it properly
                        if warrior and method:
                            # Handle self-elimination or unknown eliminator cases
                            if eliminated_by == warrior or eliminated_by.lower() in ['unknown', 'self', 'themselves']:
                                elimination_text += f"• **{warrior}** eliminated themselves via {method}\n"
                            elif eliminated_by and eliminated_by != 'unknown':
                                elimination_text += f"• **{warrior}** eliminated by **{eliminated_by}** via {method}\n"
                            else:
                                elimination_text += f"• **{warrior}** eliminated via {method}\n"
                        else:
                            # Fallback for incomplete data
                            elimination_text += f"• **{warrior}** fell in combat\n"
                    else:
                        # Handle case where elimination data is corrupted (raw text/JSON)
                        logger.warning(f"Corrupted elimination data (not dict): {elimination}")
                        if isinstance(elimination, str):
                            # If it's a string, try to clean it up
                            clean_text = elimination.replace('"', '').replace('{', '').replace('}', '').strip()
                            elimination_text += f"• **{clean_text}** was eliminated\n"
                        else:
                            elimination_text += f"• A warrior fell in combat\n"
            
            # Recalculate remaining_warriors after processing eliminations
            remaining_warriors = [p for p in game_data['participants'] if p.display_name in game_data['survivors']]
            
            # Build narrative text
            if "narrative" in round_data and round_data["narrative"]:
                narrative_text = round_data["narrative"]
                
                # Ensure narrative is a string and doesn't contain raw JSON
                if isinstance(narrative_text, str):
                    # Check if it looks like JSON (starts with { or [)
                    if narrative_text.strip().startswith(('{', '[')):
                        logger.warning(f"Narrative contains raw JSON: {narrative_text[:200]}...")
                        # Try to extract a simple description
                        narrative_text = "The battle continues with various warriors taking action."
                else:
                    logger.warning(f"Narrative is not a string: {narrative_text}")
                    narrative_text = "The battle continues with various warriors taking action."
            
            # Build survivors text
            if game_data['survivors']:
                # Group survivors by faction
                survivor_factions = {}
                
                for survivor_name in game_data['survivors']:
                    if isinstance(survivor_name, str):
                        survivor_participant = next((p for p in remaining_warriors if p.display_name == survivor_name), None)
                        if survivor_participant:
                            faction = self.faction_tracker.get(survivor_name, 'Neutral')
                            if faction not in survivor_factions:
                                survivor_factions[faction] = []
                            survivor_factions[faction].append(survivor_name)
                    else:
                        logger.warning(f"Invalid survivor entry: {survivor_name}")
                
                for faction, members in survivor_factions.items():
                    survivor_text += f"**{faction}**: {', '.join(members)}\n"
            
            # Build end of round faction totals text
            faction_totals = {}
            for participant in remaining_warriors:
                faction = self.faction_tracker.get(participant.display_name, 'Neutral')
                if faction not in faction_totals:
                    faction_totals[faction] = []
                faction_totals[faction].append(participant.display_name)
            
            for faction, members in faction_totals.items():
                faction_total_text += f"**{faction}** ({len(members)}): {', '.join(members)}\n"
            
            # Build elimination summary text (only show current round eliminations)
            if new_eliminations_count > 0 and current_round_eliminations:
                elimination_summary = ", ".join([f"**{name}**" for name in current_round_eliminations])
            
            # Send round results as individual text messages WITH buttons
            view = self.active_views.get(game_key)
            if view:
                view.game_state = "active"  # Update state to show Next Round button
                view._setup_buttons()  # Refresh buttons for active state
                
                # Send each section as individual messages
                await target_channel.send(f"⚡ **ROUND {game_data['current_round']} - CYBERTRON GAMES** ⚡")
                
                # Round recap
                await target_channel.send(f"📋 **ROUND RECAP**: {recap_text}")
                
                # Faction actions
                if faction_desc_text:
                    await target_channel.send(f"🏛️ **FACTION ACTIONS**\n{faction_desc_text}")
                
                # Faction changes
                if faction_change_text:
                    await target_channel.send(f"🔄 **FACTION CHANGES**\n{faction_change_text}")
                
                # Eliminations
                if elimination_text:
                    await target_channel.send(f"💀 **FALLEN WARRIORS**\n{elimination_text}")
                
                # Narrative
                if narrative_text:
                    await target_channel.send(f"📖 **ROUND NARRATIVE**\n{narrative_text}")
                
                # Survivors
                if survivor_text:
                    await target_channel.send(f"🔥 **REMAINING WARRIORS**\n{survivor_text}")
                
                # End of round factions
                if faction_total_text:
                    await target_channel.send(f"⚔️ **END OF ROUND FACTIONS**\n{faction_total_text}")
                
                # Elimination summary
                if new_eliminations_count > 0:
                    await target_channel.send(f"💀 **SPARKS EXTINGUISHED THIS ROUND ({new_eliminations_count})**\n{elimination_summary}")
                
                # Final stats
                await target_channel.send(f"⚰️ **TOTAL FALLEN**: {total_eliminations} warriors have fallen")
                await target_channel.send(f"🔥 **STILL BURNING**: {len(remaining_warriors)} sparks remain")
                
                # Send the buttons
                await target_channel.send("*The AllSpark watches... who will prove worthy?*", view=view)
            else:
                # Fallback if no view available
                await target_channel.send(f"⚡ **ROUND {game_data['current_round']} - CYBERTRON GAMES** ⚡")
                await target_channel.send(f"📋 **ROUND RECAP**: {recap_text}")
                if faction_desc_text:
                    await target_channel.send(f"🏛️ **FACTION ACTIONS**\n{faction_desc_text}")
                if faction_change_text:
                    await target_channel.send(f"🔄 **FACTION CHANGES**\n{faction_change_text}")
                if elimination_text:
                    await target_channel.send(f"💀 **FALLEN WARRIORS**\n{elimination_text}")
                if narrative_text:
                    await target_channel.send(f"📖 **ROUND NARRATIVE**\n{narrative_text}")
                if survivor_text:
                    await target_channel.send(f"🔥 **REMAINING WARRIORS**\n{survivor_text}")
                if faction_total_text:
                    await target_channel.send(f"⚔️ **END OF ROUND FACTIONS**\n{faction_total_text}")
                if new_eliminations_count > 0:
                    await target_channel.send(f"💀 **SPARKS EXTINGUISHED THIS ROUND ({new_eliminations_count})**\n{elimination_summary}")
                await target_channel.send(f"⚰️ **TOTAL FALLEN**: {total_eliminations} warriors have fallen")
                await target_channel.send(f"🔥 **STILL BURNING**: {len(remaining_warriors)} sparks remain")
                await target_channel.send("*The AllSpark watches... who will prove worthy?*")
            
            if len(game_data['survivors']) <= 1:
                await self._end_cybertron_games(game_key, interaction, channel)
            else:
                # Save updated game state to JSON file
                self._save_game_state_to_file(game_key, game_data)

        except Exception as e:
            logger.error(f"Error advancing Cybertron round: {e}")
            # Don't try to respond to interaction since it may already be acknowledged
            try:
                await target_channel.send(f"❌ Failed to advance round: {str(e)}")
            except:
                pass

    def _get_factions(self, participants: List[Union[discord.Member, str]]) -> Dict[str, List[Union[discord.Member, str]]]:
        """Helper to get a dictionary of participants grouped by faction"""
        factions = {}
        for p in participants:
            # Handle both discord.Member objects and string names
            if hasattr(p, 'display_name'):
                participant_name = p.display_name
                participant_obj = p
            else:
                participant_name = str(p)
                participant_obj = p
            
            faction = self.faction_tracker.get(participant_name, "Neutral")
            if faction not in factions:
                factions[faction] = []
            factions[faction].append(participant_obj)
        return factions

    def _analyze_cooperation_patterns(self, game_data: Dict[str, Any], survivors: List[str]) -> Dict[str, Any]:
        """Analyze cooperation patterns among survivors to determine if they should win together"""
        
        cooperation_data = {
            'shared_eliminations': 0,
            'assists_to_each_other': 0,
            'conflicts_between_survivors': 0,
            'peaceful_rounds': 0,
            'faction_cooperation': False,
            'recommend_alliance': False
        }
        
        if len(game_data['round_history']) < 2:
            return cooperation_data
        
        # Analyze last 5 rounds for cooperation patterns
        recent_rounds = game_data['round_history'][-5:] if len(game_data['round_history']) >= 5 else game_data['round_history']
        
        for round_data in recent_rounds:
            if not isinstance(round_data, dict):
                continue
                
            eliminations = round_data.get('eliminated', [])
            narrative = round_data.get('narrative', '').lower()
            
            # Count eliminations by survivors and detect cooperation
            survivor_eliminations = 0
            for elimination in eliminations:
                if isinstance(elimination, dict):
                    eliminated_by = elimination.get('eliminated_by', 'unknown')
                    
                    # Check if eliminated by a survivor
                    if eliminated_by in survivors:
                        survivor_eliminations += 1
                        
                        # Check if narrative suggests cooperation
                        if any(cooperation_word in narrative for cooperation_word in ['together', 'combined', 'united', 'alliance', 'team', 'cooperated', 'joined forces']):
                            cooperation_data['shared_eliminations'] += 1
                        # Check if narrative suggests this was a shared effort
                        elif any(shared_word in narrative for shared_word in ['both', 'together', 'combined attack', 'joint effort']):
                            cooperation_data['shared_eliminations'] += 1
            
            # Count conflicts between survivors in narrative
            survivor_names_in_narrative = [s for s in survivors if s.lower() in narrative]
            if len(survivor_names_in_narrative) > 1:
                # Check if narrative suggests conflict between survivors
                if any(conflict_word in narrative for conflict_word in ['fought', 'battled', 'attacked', 'defeated', 'eliminated', 'clashed', 'duel']):
                    # Check if they fought each other
                    if any(s1.lower() in narrative and s2.lower() in narrative for s1 in survivors for s2 in survivors if s1 != s2):
                        cooperation_data['conflicts_between_survivors'] += 1
                else:
                    cooperation_data['peaceful_rounds'] += 1
            elif len(survivor_names_in_narrative) == 0 and survivor_eliminations == 0:
                # No survivors mentioned and no eliminations by survivors = peaceful round
                cooperation_data['peaceful_rounds'] += 1
        
        # Check faction cooperation
        survivor_factions = {}
        for survivor in survivors:
            faction = self.faction_tracker.get(survivor, 'Neutral')
            if faction not in survivor_factions:
                survivor_factions[faction] = []
            survivor_factions[faction].append(survivor)
        
        # If all survivors are in the same faction, they should win together
        if len(survivor_factions) == 1:
            cooperation_data['faction_cooperation'] = True
            cooperation_data['recommend_alliance'] = True
        
        # Recommend alliance if cooperation patterns are strong
        total_interactions = cooperation_data['shared_eliminations'] + cooperation_data['conflicts_between_survivors']
        if total_interactions > 0:
            cooperation_ratio = cooperation_data['shared_eliminations'] / total_interactions
            if cooperation_ratio >= 0.6 and cooperation_data['peaceful_rounds'] >= 2:
                cooperation_data['recommend_alliance'] = True
        elif cooperation_data['peaceful_rounds'] >= 4 and len(survivors) <= 3:
            # High peaceful rounds with few survivors suggests cooperation
            cooperation_data['recommend_alliance'] = True
        
        return cooperation_data

    def _check_ending_conditions(self, game_data: Dict[str, Any], current_participants: List[discord.Member]) -> Tuple[bool, str]:
        """Check for various ending conditions that could result in multiple winners"""
        
        # Get survivor names for analysis
        survivor_names = []
        for p in current_participants:
            if hasattr(p, 'display_name'):
                survivor_names.append(p.display_name)
            else:
                survivor_names.append(str(p))
        
        # Analyze cooperation patterns first
        cooperation_analysis = self._analyze_cooperation_patterns(game_data, survivor_names)
        
        # Check for alliance victory based on cooperation patterns
        if len(current_participants) > 1:
            factions = self._get_factions(current_participants)
            
            # If only one faction has survivors, they all win together
            if len(factions) == 1:
                faction_name = list(factions.keys())[0]
                return True, f"alliance_victory_{faction_name}"
            
            # Check for cross-faction alliance based on cooperation
            if cooperation_analysis['recommend_alliance'] and len(current_participants) <= 4:
                # Look for cooperation patterns across factions
                if (cooperation_analysis['shared_eliminations'] >= 1 and cooperation_analysis['conflicts_between_survivors'] == 0) or cooperation_analysis['peaceful_rounds'] >= 3:
                    return True, "peaceful_resolution"
        
        # Check for mutual destruction scenario (last round had special events)
        if game_data['current_round'] >= 2 and len(current_participants) <= 3:
            last_round = game_data['round_history'][-1] if game_data['round_history'] else None
            if last_round and isinstance(last_round, dict):
                # Check for mutual elimination events or special endings
                eliminations = last_round.get('eliminated', [])
                if len(eliminations) >= len(current_participants):
                    return True, "mutual_destruction"
                
                # Check for narrative indicating special ending
                narrative = last_round.get('narrative', '')
                if any(keyword in narrative.lower() for keyword in ['truce', 'alliance', 'unity', 'peace', 'surrender']):
                    return True, "peaceful_resolution"
        
        # Check for maximum rounds reached (forced ending)
        if game_data['current_round'] >= 25:  # Hard limit to prevent infinite games
            return True, "maximum_rounds_reached"
        
        # Check for stalemate (no eliminations in last 3 rounds)
        if game_data['current_round'] >= 4:
            recent_eliminations = 0
            for i in range(1, 4):  # Check last 3 rounds
                if i <= len(game_data['round_history']):
                    round_data = game_data['round_history'][-i]
                    if isinstance(round_data, dict):
                        eliminations = round_data.get('eliminated', [])
                        recent_eliminations += len(eliminations)
            
            if recent_eliminations == 0 and len(current_participants) > 1:
                return True, "stalemate"
        
        return False, ""

    def _get_ending_message(self, ending_reason: str, survivors: List[str], factions: Dict[str, List[str]]) -> str:
        """Get appropriate ending message based on the ending condition"""
        
        if ending_reason.startswith("alliance_victory_"):
            faction_name = ending_reason.replace("alliance_victory_", "")
            return f"🏆 **THE {faction_name.upper()} ALLIANCE EMERGES VICTORIOUS!** 🏆\n" \
                   f"All surviving members of the {faction_name} faction have proven their unity and strength!"
        
        elif ending_reason == "mutual_destruction":
            return "💥 **MUTUAL DESTRUCTION ACHIEVED** 💥\n" \
                   "The final battle resulted in mutual annihilation. All remaining warriors perished together!"
        
        elif ending_reason == "peaceful_resolution":
            return "🕊️ **PEACE THROUGH UNITY** 🕊️\n" \
                   "The warriors have chosen unity over conflict. A peaceful resolution has been reached!"
        
        elif ending_reason == "maximum_rounds_reached":
            return "⏰ **MAXIMUM ROUNDS REACHED** ⏰\n" \
                   f"After {len(survivors)} epic rounds, the games conclude with multiple survivors!"
        
        elif ending_reason == "stalemate":
            return "⚖️ **STALEMATE DECLARED** ⚖️\n" \
                   "No warriors have fallen in recent rounds. The AllSpark declares a stalemate!"
        
        else:
            # Default multi-winner message
            return "🏆 **MULTIPLE CHAMPIONS PROVEN WORTHY** 🏆"

    def _generate_multi_champion_summary(self, game_data: Dict[str, Any], survivors: List[str]) -> str:
        """Generate a summary for multiple champions"""
        
        if not self.use_ai or not self.model or not hasattr(self, 'client') or not self.client:
            return self._generate_fallback_multi_champion_summary(game_data, survivors)
        
        try:
            # Analyze cooperation patterns for better narrative
            cooperation_analysis = self._analyze_cooperation_patterns(game_data, survivors)
            
            # Build context for multiple champions
            factions_context = ""
            survivor_factions = {}
            
            for survivor in survivors:
                faction = self.faction_tracker.get(survivor, 'Neutral')
                if faction not in survivor_factions:
                    survivor_factions[faction] = []
                survivor_factions[faction].append(survivor)
            
            for faction, members in survivor_factions.items():
                factions_context += f"- {faction}: {', '.join(members)}\n"
            
            # Build round-by-round context for all survivors
            journey_context = ""
            for i, round_data in enumerate(game_data['round_history'], 1):
                if isinstance(round_data, dict):
                    narrative = round_data.get('narrative', '')
                    eliminations = round_data.get('eliminated', [])
                    faction_changes = round_data.get('faction_changes', [])
                    
                    # Check if any survivors were mentioned in this round
                    survivor_mentions = []
                    for survivor in survivors:
                        if survivor in narrative:
                            survivor_mentions.append(survivor)
                    
                    if survivor_mentions or any(e.get('eliminated_by', '') in survivors for e in eliminations if isinstance(e, dict)):
                        journey_context += f"Round {i}: "
                        if survivor_mentions:
                            journey_context += f"{', '.join(survivor_mentions)} took action. "
                        
                        # Track eliminations caused by survivors
                        survivor_kills = [e for e in eliminations if isinstance(e, dict) and e.get('eliminated_by', '') in survivors]
                        if survivor_kills:
                            journey_context += f"Eliminations: {len(survivor_kills)}. "
                        
                        # Track faction changes involving survivors
                        survivor_faction_changes = [fc for fc in faction_changes if isinstance(fc, dict) and fc.get('warrior', '') in survivors]
                        if survivor_faction_changes:
                            journey_context += f"Faction changes: {len(survivor_faction_changes)}. "
                        
                        journey_context += "\n"
            
            # Determine the type of alliance
            alliance_type = "natural faction unity"
            if len(survivor_factions) > 1 and cooperation_analysis['recommend_alliance']:
                alliance_type = "cross-faction cooperation"
            elif cooperation_analysis['shared_eliminations'] > 0:
                alliance_type = "battle-forged alliance"
            elif cooperation_analysis['peaceful_rounds'] >= 3:
                alliance_type = "peaceful understanding"
            
            prompt = f"""Create an epic narrative summary of the Cybertron Games where multiple warriors survived and proved worthy through {alliance_type}.

Game Details:
- Total Rounds: {game_data['current_round']}
- Multiple Champions: {len(survivors)} warriors
- Champions by Faction:
{factions_context}
- Total Eliminations: {len(game_data.get('eliminations', []))}
- Cooperation Score: {cooperation_analysis['shared_eliminations']} shared eliminations, {cooperation_analysis['peaceful_rounds']} peaceful rounds

Champions' Journey:
{journey_context}

Write a compelling narrative that celebrates how these warriors earned victory together through {alliance_type}. 
Highlight their unique bond, whether through shared faction loyalty, cross-faction cooperation, or battle-forged alliance.
Make it epic, detailed, and Transformers-themed with energon, sparks, factions, and cybertronian lore.
Focus on why the AllSpark chose to honor multiple champions instead of demanding a single victor."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a Transformers lore master creating epic narratives about Cybertronian battles and victories."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.8
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Failed to generate multi-champion summary: {e}")
            return self._generate_fallback_multi_champion_summary(game_data, survivors)

    def _generate_fallback_multi_champion_summary(self, game_data: Dict[str, Any], survivors: List[str]) -> str:
        """Fallback summary for multiple champions when AI is unavailable"""
        
        # Analyze cooperation patterns
        cooperation_analysis = self._analyze_cooperation_patterns(game_data, survivors)
        
        # Group survivors by faction
        survivor_factions = {}
        for survivor in survivors:
            faction = self.faction_tracker.get(survivor, 'Neutral')
            if faction not in survivor_factions:
                survivor_factions[faction] = []
            survivor_factions[faction].append(survivor)
        
        # Determine alliance type
        alliance_type = "natural faction unity"
        if len(survivor_factions) > 1 and cooperation_analysis['recommend_alliance']:
            alliance_type = "cross-faction cooperation"
        elif cooperation_analysis['shared_eliminations'] >= 2:
            alliance_type = "battle-forged alliance"
        elif cooperation_analysis['peaceful_rounds'] >= 3:
            alliance_type = "peaceful understanding"
        
        summary = f"🏆 **MULTIPLE CHAMPIONS CROWNED** 🏆\n"
        summary += f"In this epic {game_data['current_round']}-round battle, {len(survivors)} warriors proved their worth through {alliance_type}!\n\n"
        
        # Alliance description based on type
        if alliance_type == "cross-faction cooperation":
            summary += "These warriors transcended faction boundaries to achieve victory together.\n"
        elif alliance_type == "battle-forged alliance":
            summary += f"Forged through {cooperation_analysis['shared_eliminations']} shared battles, these warriors proved stronger together.\n"
        elif alliance_type == "peaceful understanding":
            summary += f"After {cooperation_analysis['peaceful_rounds']} rounds of peaceful coexistence, these warriors chose harmony over conflict.\n"
        else:
            summary += "United by faction loyalty, these warriors stood together against all challengers.\n"
        
        # Faction breakdown
        summary += "\n**Champions by Faction:**\n"
        for faction, members in survivor_factions.items():
            summary += f"• **{faction}**: {', '.join(members)}\n"
        
        # Statistics
        summary += f"\n**Battle Statistics:**\n"
        summary += f"• Total Eliminations: {len(game_data.get('eliminations', []))}\n"
        summary += f"• Shared Eliminations: {cooperation_analysis['shared_eliminations']}\n"
        summary += f"• Peaceful Rounds: {cooperation_analysis['peaceful_rounds']}\n"
        summary += f"• Survival Rate: {len(survivors)}/{len(game_data.get('participants', []))}\n"
        
        # Victory message
        summary += f"\nTogether, these champions demonstrated that {alliance_type} can be as powerful as individual strength."
        summary += "\n\n*The AllSpark shines brightly upon all who proved worthy in the Arena of Cybertron!*"
        
        return summary

    async def _end_cybertron_games(self, game_key: str, interaction: discord.Interaction = None, channel: discord.TextChannel = None, ending_reason: str = ""):
        """End the Cybertron Games session"""
        # Use channel from interaction if available, otherwise use provided channel
        target_channel = interaction.channel if interaction else channel
        
        game_data = self.active_games.pop(game_key, None)
        
        if not game_data:
            return

        survivors = game_data['survivors']
        eliminations = game_data['eliminations']
        assignments = game_data['assignments']
        
        # Group survivors by faction
        surviving_factions = {}
        for warrior in survivors:
            faction_data = assignments.get(warrior, "Unknown")
            if isinstance(faction_data, dict) and 'faction' in faction_data:
                faction = faction_data['faction']
            elif isinstance(faction_data, str):
                faction = faction_data
            else:
                faction = "Unknown"
            if faction not in surviving_factions:
                surviving_factions[faction] = []
            surviving_factions[faction].append(warrior)
        
        # Send final results as text messages instead of embeds
        await target_channel.send("🏆 **THE CYBERTRON GAMES HAVE CONCLUDED** 🏆")
        
        if len(survivors) == 1:
            champion = survivors[0]
            champion_faction_data = assignments.get(champion, "Unknown")
            if isinstance(champion_faction_data, dict) and 'faction' in champion_faction_data:
                champion_faction = champion_faction_data['faction']
            elif isinstance(champion_faction_data, str):
                champion_faction = champion_faction_data
            else:
                champion_faction = "Unknown"
            
            await target_channel.send(f"🏆 **THE ALLSPARK HAS CHOSEN ITS CHAMPION!** 🏆")
            await target_channel.send(f"**{champion}** of the **{champion_faction}** emerges victorious from the Arena of Cybertron!")
            await target_channel.send("*The ancient energon crystals pulse with approval as the last warrior standing claims the Matrix of Leadership. All other sparks have returned to the AllSpark, their sacrifice honored in the halls of Cybertron.*")
            await target_channel.send("⚡ **TILL ALL ARE ONE!** ⚡")
            
        elif len(survivors) > 1:
            # Multiple survivors - use event-based ending message
            ending_message = self._get_ending_message(ending_reason, survivors, surviving_factions)
            await target_channel.send(ending_message)
            
            # List all champions
            await target_channel.send(f"🏆 **THE ALLSPARK HAS CHOSEN {len(survivors)} CHAMPIONS!** 🏆")
            
            # Show champions by faction
            for faction, warriors in surviving_factions.items():
                if len(warriors) == 1:
                    await target_channel.send(f"**{warriors[0]}** of the **{faction}**")
                else:
                    await target_channel.send(f"**{faction} Alliance**: {', '.join(warriors)}")
            
            await target_channel.send("*The ancient energon crystals pulse with approval as these warriors share the glory of victory. Their unity and strength have proven that sometimes, multiple sparks can burn brightest together.*")
            await target_channel.send("⚡ **TILL ALL ARE ONE!** ⚡")
            
        else:
            await target_channel.send("💀 **THE ARENA CLAIMS ALL SPARKS** 💀")
            await target_channel.send("*The Arena of Cybertron falls silent... No warrior proved worthy of the AllSpark's blessing. All sparks have been extinguished, their energon absorbed into the ancient battleground.*")
            await target_channel.send("🌌 **The Matrix of Leadership remains unclaimed...** 🌌")
        
        # Game statistics
        await target_channel.send(f"\n📊 **GAME STATISTICS**")
        await target_channel.send(f"⚡ Total Rounds of Combat: **{game_data['current_round']}** epic battles")
        await target_channel.send(f"💀 Warriors Fallen: **{len(eliminations)}** sparks extinguished")
        await target_channel.send(f"🏆 Final Champions: **{len(survivors)}** victorious")
        
        # Detailed elimination information
        if eliminations:
            await target_channel.send(f"\n💀 **THE FALLEN**")
            
            # Show first 10 eliminations
            for i, warrior in enumerate(eliminations[:10]):
                warrior_faction_data = assignments.get(warrior, 'Unknown')
                if isinstance(warrior_faction_data, dict) and 'faction' in warrior_faction_data:
                    warrior_faction = warrior_faction_data['faction']
                else:
                    warrior_faction = warrior_faction_data if isinstance(warrior_faction_data, str) else 'Unknown'
                await target_channel.send(f"• **{warrior}** ({warrior_faction})")
            
            if len(eliminations) > 10:
                await target_channel.send(f"*...and {len(eliminations) - 10} more warriors*")
        
        # Surviving factions information
        if surviving_factions:
            await target_channel.send(f"\n🛡️ **SURVIVING FACTIONS**")
            for faction, warriors in surviving_factions.items():
                await target_channel.send(f"• **{faction}**: {', '.join(warriors)}")
        
        # Generate AI champion summary if available
        if self.use_ai and len(survivors) == 1:
            try:
                champion = survivors[0]
                champion_summary = await self._generate_champion_summary(game_data, champion)
                if champion_summary:
                    await target_channel.send(f"\n🤖 **CHAMPION'S JOURNEY**")
                    await target_channel.send(champion_summary)
            except Exception as e:
                logger.error(f"Failed to generate champion summary: {e}")
        
        # Generate multi-champion summary for multiple survivors
        elif self.use_ai and len(survivors) > 1:
            try:
                multi_champion_summary = self._generate_multi_champion_summary(game_data, survivors)
                if multi_champion_summary:
                    await target_channel.send(f"\n🤖 **CHAMPIONS' JOURNEY**")
                    await target_channel.send(multi_champion_summary)
            except Exception as e:
                logger.error(f"Failed to generate multi-champion summary: {e}")
        
        view = self.active_views.get(game_key)
        if view:
            view._setup_buttons(end_game=True)
            await target_channel.send("\n*The champion's name shall be etched in energon for all eternity...*")
            
        if game_key in self.active_views:
            del self.active_views[game_key]
        
        # Clean up JSON file
        self._delete_game_state_file(game_key)
            
class CybertronGamesView(View):
    def __init__(self, bot_cog: Any, game_key: str, game_state: str = "setup"):
        super().__init__(timeout=None)
        self.bot_cog = bot_cog
        self.game_key = game_key
        self.game_state = game_state
        self.message = None
        self._setup_buttons()

    def _setup_buttons(self, end_game=False):
        self.clear_items()
        if not end_game:
            start_button = Button(label="Start Games", style=discord.ButtonStyle.green, custom_id="start_cybertron_games")
            next_round_button = Button(label="Next Round", style=discord.ButtonStyle.blurple, custom_id="next_cybertron_round")
            
            if self.game_state == "setup":
                start_button.callback = self.start_callback
                self.add_item(start_button)
            else:
                next_round_button.callback = self.next_round_callback
                self.add_item(next_round_button)
            
            end_button = Button(label="End Games", style=discord.ButtonStyle.red, custom_id="end_cybertron_games")
            end_button.callback = self.end_callback
            self.add_item(end_button)
        else:
            self.stop()
            
    async def start_callback(self, interaction: discord.Interaction):
        # Defer the interaction to avoid acknowledgment conflicts
        await interaction.response.defer()
        self.game_state = "active"
        self._setup_buttons()
        # Send status message and advance round
        await interaction.channel.send("The games have begun! Processing Round 1...")
        await self.bot_cog._advance_cybertron_round(self.game_key, None, interaction.channel)

    async def next_round_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.bot_cog._advance_cybertron_round(self.game_key, None, interaction.channel)

    async def end_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.bot_cog._end_cybertron_games(self.game_key, interaction, interaction.channel)

class CybertronGames(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.generator = CybertronGamesGenerator(GROQ_API_KEY)
        
    async def cog_load(self) -> None:
        pass  # Commands are automatically registered via decorators

    async def cog_unload(self) -> None:
        pass  
    
    @commands.hybrid_command(name='cybertron_games', description="Initiate the ultimate Transformers deathmatch - The Cybertron Games")
    @app_commands.describe(
        include_bots="Include cybertronian AI units in the games",
        warriors="Number of warriors to select (2-50, default: all)",
        factions="Number of factions (2-5, default: 5)",
        specific_participants="Specific Discord users to include (space-separated names or mentions)",
        cybertronian_only="Only include Cybertronian citizens (Autobot, Decepticon, Maverick, or Cybertronian_Citizen roles)"
    )
    async def cybertron_games(
        self,
        ctx: commands.Context,
        include_bots: bool = False,
        warriors: int = 0,
        factions: int = 5,
        specific_participants: str = None,
        cybertronian_only: bool = False
    ):
        # Acknowledge the command immediately
        await ctx.defer()
        await self.generator.initialize_game(ctx, include_bots, warriors, factions, specific_participants, cybertronian_only)


async def setup(bot):
    await bot.add_cog(CybertronGames(bot))
    logger.info("✅ Cybertron Games cog loaded successfully")