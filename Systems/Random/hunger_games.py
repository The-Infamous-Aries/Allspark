import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import logging
import google.generativeai as genai
from typing import Dict, List, Any
import json
from datetime import datetime
from discord.ui import Button, View
import sys
import os

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import GEMINI_API_KEY, ROLE_IDS

logger = logging.getLogger("allspark.cybertron_games")

class CybertronGamesGenerator:
    """AI-powered Transformers-themed Cybertron Games story generator"""
    
    def __init__(self, api_key: str = None):
        """Initialize the AI Cybertron Games Generator with gemini-1.5-pro"""
        self.game_state: Dict[str, Any] = {}
        self.round_history: List[Dict[str, Any]] = []
        self.alliance_tracker = {}  # Track dynamic alliances between warriors
        self.district_tracker = {}  # Track district assignments
        self.faction_tracker = {}   # Track faction assignments
        
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-pro')
                self.use_ai = True
                print(f"✅ AI initialized successfully with gemini-1.5-pro for Cybertron Games")
            except Exception as e:
                print(f"❌ Failed to initialize AI: {e}")
                self.use_ai = False
                self.model = None
        else:
            print("⚠️  No API key provided - using fallback cybertronian narratives")
            self.use_ai = False
            self.model = None
    
    def _create_cybertron_context(self, participants: List[discord.Member]) -> str:
        """Create the pure Transformers/Cybertronian context for the games"""
        total_participants = len(participants)
        
        context = f"""
        🌌 **WELCOME TO THE CYBERTRON GAMES** 🌌
        
        The ancient Arena of Cybertron awakens once more, orbiting the war-torn planet in perpetual twilight. 
        Here, **{total_participants} cybertronian warriors** are summoned to compete in the ultimate trial of survival, 
        where sparks will flicker and die, and only the strongest will claim victory.
        
        ⚡ **THE ARENA OF CYBERTRON** ⚡
        A massive orbital battle station constructed from the remains of the Ark and Nemesis, 
        featuring:
        - Shifting energon crystal formations that pulse with raw power
        - Plasma conduit networks that can incinerate entire sections
        - Transformation inhibitor fields that force robot mode combat
        - Ancient Prime relic chambers containing forbidden technology
        - Gravity wells that simulate planetary destruction
        - Spark extraction chambers for ultimate elimination
        
        🤖 **THE PARTICIPANTS** 🤖
        Each warrior has been selected from across the cybertronian spectrum:
        """
        
        for i, participant in enumerate(participants, 1):
            context += f"Warrior {i}: {participant.display_name} - A cybertronian fighter whose spark burns with determination\n"
        
        context += """
        ⚔️ **RULES OF THE CYBERTRON GAMES** ⚔️
        - All combatants start with basic energon reserves
        - Transformation abilities may be granted or revoked by the arena
        - Alliances can form and shatter in an instant
        - The arena itself is alive and will fight against the warriors
        - Spark cores can be extinguished permanently
        - Only one warrior's spark will remain ignited at the end
        
        🌟 **CYBERTRONIAN TECHNOLOGY** 🌟
        - Energon swords and plasma cannons
        - Spark extractors and core disruptors
        - Ancient Prime relics with unknown powers
        - Space bridge fragments for instant teleportation
        - Dark energon corruption zones
        - Omega Supreme-class defense systems
        
        Each round brings new cybertronian challenges, ancient technology discoveries, 
        and the eternal struggle between Autobot honor and Decepticon ruthlessness.
        """
        return context
    
    def get_current_alliances_text(self, warriors: List[str]) -> str:
        """Get current alliance status for prompt generation"""
        if not self.alliance_tracker:
            return "No alliances formed yet - district and faction loyalty conflicts"
        
        alliances = []
        for warrior, alliance_data in self.alliance_tracker.items():
            if warrior in warriors:
                allies = [ally for ally in alliance_data.get('allies', []) if ally in warriors]
                district = self.district_tracker.get(warrior, "Unknown District")
                faction = self.faction_tracker.get(warrior, "Neutral")
                
                if allies:
                    alliances.append(f"{warrior} ({district}, {faction}): allies with {', '.join(allies)} ({alliance_data.get('trust_level', 'unknown')})")
                else:
                    alliances.append(f"{warrior} ({district}, {faction}): no current allies")
        
        return "; ".join(alliances) if alliances else "District and faction loyalties create complex dynamics"

    def assign_districts_and_factions(self, warriors: List[str], district_count: int = 8, faction_count: int = 5) -> Dict[str, Dict[str, str]]:
        """Assign random districts and factions to warriors for complex allegiance drama"""
        
        # Dynamic district names based on count
        district_names = [
            "Energon Elite", "Plasma Core", "Spark Extractors", "Transformation Masters",
            "Dark Energon", "Space Bridge", "Omega Supreme", "Prime Relics",
            "Maximal Territory", "Predacon Lands"
        ]
        districts = [f"District {i+1} - {name}" for i, name in enumerate(district_names[:district_count])]
        
        # Dynamic faction names based on count
        faction_names = [
            "Autobot", "Decepticon", "Maximal", "Predacon", "Neutral",
            "Seeker", "Wrecker", "Dinobot", "Guardian", "Titan"
        ]
        factions = faction_names[:faction_count]
        
        # Ensure we have enough districts and factions for variety
        if len(warriors) > len(districts) * 2:
            # Add more districts if needed
            for i in range(len(districts), len(warriors)):
                districts.append(f"District {(i % 10) + 1} - Sector {chr(65 + (i % 26))}")
        
        if len(warriors) > len(factions) * 3:
            # Add more factions if needed
            for i in range(len(factions), len(warriors)):
                factions.append(f"Faction {i+1}")
        
        assignments = {}
        
        # Smart assignment to balance districts and factions
        district_assignments = []
        faction_assignments = []
        
        # Distribute warriors across districts
        for i, warrior in enumerate(warriors):
            district = districts[i % len(districts)]
            faction = factions[i % len(factions)]
            
            self.district_tracker[warrior] = district
            self.faction_tracker[warrior] = faction
            
            assignments[warrior] = {
                "district": district,
                "faction": faction
            }
        
        return assignments

    def _generate_cybertron_round(self, round_num: int, participants: List[discord.Member], 
                                previous_round: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate a pure Transformers-themed round using AI"""
        
        if not self.use_ai or not self.model:
            return self._generate_fallback_cybertron_round(round_num, participants, previous_round)
        
        # Create tribute tracking
        tribute_list = []
        for i, participant in enumerate(participants, 1):
            tribute_list.append({
                'name': participant.display_name,
                'warrior_id': i,
                'status': 'spark_ignited',
                'spark_signature': f"SPARK-{participant.id}",
                'faction_affinity': random.choice(['Autobot', 'Decepticon', 'Neutral', 'Maximal', 'Predacon'])
            })
        
        alive_tributes = [t for t in tribute_list if t['status'] == 'spark_ignited']
        total_tributes = len(alive_tributes)
        
        # Build cybertronian history context
        history_context = ""
        if previous_round and previous_round.get('events'):
            recent_events = previous_round['events'][-5:] if len(previous_round['events']) > 5 else previous_round['events']
            recent_eliminations = previous_round.get('eliminations', [])[-3:] if 'eliminations' in previous_round else []
            
            history_context = f"""
            🔄 **CYBERTRON GAMES CONTINUITY - ROUND {round_num-1} LEGACY**
            
            SURVIVING SPARKS: {len(previous_round.get('survivors', []))} warriors remain ignited
            
            RECENT CYBERTRONIAN EVENTS:
            {json.dumps(recent_events, indent=2)}
            
            SPARK CORE ELIMINATIONS:
            {json.dumps(recent_eliminations, indent=2)}
            
            **NARRATIVE CONTINUITY REQUIREMENTS:**
            - Build upon established cybertronian character arcs and motivations
            - Reference specific energon events and technology discoveries
            - Maintain consistent faction behaviors and warrior personalities
            - Show evolution of trust and betrayal based on previous spark interactions
            - Ensure arena transformations feel like consequences of previous battles
            - Each warrior's actions must reflect their established cybertronian nature
            """
        
        prompt = f"""
        You are the **Oracle of Cybertron**, master storyteller for the **Cybertron Games** - the ultimate Transformers deathmatch. 
        Create an EPIC cybertronian narrative for ROUND {round_num} with **{total_tributes} cybertronian warriors**.
        
        🎯 **CURRENT IGNITED SPARKS:**
        {json.dumps(alive_tributes[:15], indent=2)} {f"... and {total_tributes - 15} more sparks" if total_tributes > 15 else ""}
        
        {history_context}
        
        ⚡ **PURE CYBERTRONIAN NARRATIVE REQUIREMENTS:**
        
        1. **🌌 OPENING CYBERTRON SCENE:**
           - Describe the orbital arena's transformation using pure cybertronian technology
           - Energon crystal formations shifting and pulsing with power
           - Ancient Prime relics awakening with mysterious energy signatures
           - The station itself responding to the warriors' presence
        
        2. **🤖 CYBERTRONIAN COMBAT SEQUENCES:**
           - Robot mode battles with energon weapons and plasma cannons
           - Transformation sequences (when arena allows)
           - Spark core struggles and energon depletion
           - Ancient cybertronian martial arts and combat protocols
        
        3. **⚡ ENERGON AND TECHNOLOGY:**
           - Raw energon discovery and consumption
           - Dark energon corruption and its effects
           - Prime relic activation and power surges
           - Space bridge fragment usage for tactical advantage
           - Spark extractor deployment and core disruption
        
        4. **🤝 DYNAMIC CYBERTRONIAN ALLIANCES:**
           - **Alliance Formation:** warriors bonding through energon sharing
           - **Faction Shifts:** Autobot ↔ Decepticon loyalty changes based on survival
           - **Spark Betrayal:** allies turning on spark-bonded companions
           - **Neutral Manipulation:** neutral warriors playing faction politics
           - **Alliance Dissolution:** trust shattering from dark energon corruption
           - **Temporary Pacts:** survival-driven cooperation regardless of faction
        
        5. **💀 EPIC SPARK ELIMINATIONS:**
           - Detailed spark core extinguishing descriptions
           - Final words as energon fades from optics
           - Transformation into cold, lifeless metal
           - Arena claiming the defeated warrior's spark
        
        6. **🌟 ARENA EVOLUTION:**
           - Station defenses activating against warriors
           - Omega Supreme protocols engaging
           - Ancient cybertronian traps springing to life
           - Gravity manipulation and plasma storms
        
        7. **⚙️ PURE CYBERTRONIAN TECHNOLOGY:**
           - Energon sword clashes sending sparks flying
           - Plasma cannon overloads causing explosions
           - Transformation cog malfunctions
           - Spark core resonance between warriors
           - Dark energon weapon corruption
        
        **🤖 DISTRICT & FACTION ALLEGIANCE SYSTEM:**
        - Each warrior belongs to a **DISTRICT** (1-12) and **FACTION** (Autobot/Decepticon/Neutral/Maximal/Predacon)
        - **District Loyalty:** Warriors from same district may form stronger bonds regardless of faction
        - **Faction Betrayal:** Eliminating same-faction warriors creates dramatic tension and potential faction shifts
        - **District vs Faction Conflicts:** Warriors torn between district loyalty and faction duty
        - **Random Initial Assignment:** Factions are assigned randomly at game start for this specific Cybertron Games
        - **Dynamic Allegiance Shifts:** Events can cause warriors to abandon district, faction, or both
        - **Same-Faction Elimination Drama:** When warriors eliminate their own faction members, it triggers deep story consequences
        - **District Betrayal:** Warriors may betray their district for faction or survival
        - **Faction Conversion:** Dark energon or Prime relics can force faction changes
        - **Neutral Manipulation:** Neutral warriors play district and faction politics simultaneously
        
        **FORBIDDEN ELEMENTS TO AVOID:**
        - No human concepts or terminology
        - No loot systems or item collection
        - No faction loading from external sources
        - No non-cybertronian themes
        - No references to organic life
        
        **NARRATIVE STYLE:**
        - Epic cybertronian mythology language
        - Technical descriptions of spark core functions
        - Ancient Prime era terminology
        - Pure mechanical/robotic descriptions
        - Energon-based power systems
        
        **SCALE HANDLING:**
        Focus on **strategic cybertronian warfare** appropriate for {total_tributes} mechanical warriors.
        Balance **individual spark moments** with **large-scale energon conflicts**.
        
        Return PURE CYBERTRONIAN JSON format:
        {{
            "round_number": {round_num},
            "cybertron_events": [
                {{
                    "type": "energon_combat|spark_elimination|prime_relic|dark_energon|transformation|arena_trap|space_bridge|alliance_formation|faction_betrayal|spark_betrayal|district_betrayal|same_faction_elimination",
                    "participants": ["warrior names"],
                    "description": "epic cybertronian narrative with energon and spark cores",
                    "location": "specific cybertronian arena sector",
                    "energon_cost": "spark energy expended",
                    "cybertronian_outcome": "consequences for remaining sparks",
                    "district_conflicts": "describe district vs faction loyalty struggles",
                    "faction_drama": "detail same-faction elimination consequences"
                }}
            ],
            "spark_eliminations": [
                {{
                    "warrior": "name",
                    "warrior_id": number,
                    "eliminated_by": "cybertronian warrior or arena hazard",
                    "method": "detailed spark core extinguishing description",
                    "final_words": "last words as energon fades",
                    "spark_signature": "unique spark identifier",
                    "district": "warrior's district number",
                    "faction": "warrior's faction (Autobot/Decepticon/Neutral/Maximal/Predacon)",
                    "same_faction_killer": "true if eliminated by same faction member",
                    "district_betrayal": "true if betrayed district loyalty"
                }}
            ],
            "cybertron_alliances": [
                {{
                    "sparks": ["warrior names"],
                    "type": "autobot_cooperation|decepticon_cell|neutral_coalition|maximal_pack|predacon_clan|spark_betrayal|faction_shift|energon_bond|temporary_pact|survival_coalition|district_loyalty|district_betrayal",
                    "trust_level": "energon_bonded|temporary|decepticon_treachery|autobot_honor|neutral_manipulation|spark_betrayal_imminent|faction_loyalty_shift|district_betrayal|same_faction_guilt",
                    "energon_pact": "cybertronian alliance description including betrayal triggers",
                    "district_ties": "describe district-based alliance motivations",
                    "faction_consequences": "detail faction loyalty implications"
                }}
            ],
            "ignited_sparks": ["all remaining warrior names"],
            "cybertron_tech_activated": ["list of ancient cybertronian technology"],
            "energon_events": ["major energon surges and depletions"],
            "arena_transformations": ["station evolution descriptions"],
            "alliance_shifts": ["describe any faction changes or alliance betrayals"],
            "district_assignments": {{"warrior_name": "district_number"}},
            "faction_assignments": {{"warrior_name": "faction_name"}},
            "same_faction_eliminations": ["list of same-faction eliminations with drama"],
            "district_betrayals": ["list of district loyalty betrayals"]
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            
            # Clean the response text
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            story_data = json.loads(response_text.strip())
            
            # Ensure we have the required structure
            if 'cybertron_events' not in story_data:
                story_data['cybertron_events'] = []
            if 'spark_eliminations' not in story_data:
                story_data['spark_eliminations'] = []
            if 'cybertron_alliances' not in story_data:
                story_data['cybertron_alliances'] = []
            if 'alliance_shifts' not in story_data:
                story_data['alliance_shifts'] = []
                
            # Update alliance tracker based on round data
            self._update_alliance_tracker(story_data, [p.display_name for p in participants])
            
            print(f"✅ AI generated comprehensive Cybertron Round {round_num} successfully")
            return story_data
            
        except Exception as e:
            print(f"❌ AI generation failed: {e}, using enhanced cybertronian fallback")
            return self._generate_fallback_cybertron_round(round_num, participants, previous_round)
            
    def _update_alliance_tracker(self, round_data: Dict[str, Any], warriors: List[str]):
        """Update alliance tracker based on round events"""
        # Process alliance shifts from the round
        for shift in round_data.get('alliance_shifts', []):
            warrior = shift.get('warrior')
            new_allies = shift.get('new_allies', [])
            trust_level = shift.get('trust_level', 'temporary')
            
            if warrior and warrior in warriors:
                self.alliance_tracker[warrior] = {
                    'allies': new_allies,
                    'trust_level': trust_level,
                    'last_shift': round_data.get('round_num', 0)
                }
    
    def _generate_fallback_cybertron_round(self, round_num: int, participants: List[discord.Member], 
                                        previous_round: Dict[str, Any] = None) -> Dict[str, Any]:
        """Enhanced fallback with district and faction dynamics"""
        
        # Create warrior tracking
        warriors = []
        for i, participant in enumerate(participants, 1):
            warriors.append({
                'name': participant.display_name,
                'warrior_id': i,
                'spark_signature': f"SPARK-{participant.id}",
                'faction': random.choice(['Autobot', 'Decepticon', 'Neutral', 'Maximal', 'Predacon'])
            })
        
        # Determine current survivors
        current_survivors = [w['name'] for w in warriors]
        if previous_round:
            current_survivors = previous_round.get('ignited_sparks', current_survivors)
        
        # Calculate eliminations needed
        total_warriors = len(current_survivors)
        eliminations_needed = max(1, total_warriors // 3) if total_warriors > 3 else (1 if total_warriors > 2 else 0)
        
        # Build cybertronian events with district and faction dynamics
        cybertron_events = []
        spark_eliminations = []
        cybertron_alliances = []
        alliance_shifts = []
        same_faction_eliminations = []
        district_betrayals = []
        
        # Get district and faction assignments from the generator
        district_assignments = getattr(self, 'district_tracker', {})
        faction_assignments = getattr(self, 'faction_tracker', {})
        
        active_warriors = current_survivors
        
        # Dynamic alliance formation with district/factor considerations
        if len(active_warriors) >= 3 and round_num > 1:
            # Form alliance based on district/faction loyalties
            alliance_members = random.sample(active_warriors, 3)
            districts = [district_assignments.get(m, 'Unknown') for m in alliance_members]
            factions = [faction_assignments.get(m, 'Unknown') for m in alliance_members]
            
            district_bond = len(set(districts)) == 1
            faction_bond = len(set(factions)) == 1
            
            if district_bond:
                cybertron_events.append({
                    "type": "alliance_formation",
                    "participants": alliance_members,
                    "description": f"{', '.join(alliance_members)} form a district loyalty bond as warriors from District {districts[0]} unite against common threats",
                    "location": "District Alliance Sector",
                    "energon_cost": "District honor synchronization",
                    "cybertronian_outcome": "District loyalty strengthened",
                    "district_conflicts": f"District {districts[0]} warriors prioritize district over faction loyalty",
                    "faction_drama": "Faction tensions rise as district loyalty overrides faction duty"
                })
            elif faction_bond:
                cybertron_events.append({
                    "type": "alliance_formation",
                    "participants": alliance_members,
                    "description": f"{', '.join(alliance_members)} unite as {factions[0]} warriors, their faction loyalty creating an unbreakable energon bond",
                    "location": "Faction Alliance Chamber",
                    "energon_cost": "Faction loyalty synchronization",
                    "cybertronian_outcome": "Faction unity reinforced",
                    "district_conflicts": "District loyalties tested against faction bonds",
                    "faction_drama": f"{factions[0]} faction demonstrates superior unity"
                })
            else:
                cybertron_events.append({
                    "type": "alliance_formation",
                    "participants": alliance_members,
                    "description": f"{', '.join(alliance_members)} form a temporary survival coalition despite conflicting district and faction loyalties",
                    "location": "Survival Coalition Zone",
                    "energon_cost": "Trust establishment energy",
                    "cybertronian_outcome": "Uneasy alliance formed",
                    "district_conflicts": "District vs faction loyalties create tension",
                    "faction_drama": "Mixed faction alliance challenges traditional loyalties"
                })
            
            alliance_shifts.append({
                "warrior": alliance_members[0],
                "new_allies": alliance_members[1:3],
                "trust_level": "district_bonded" if district_bond else "faction_bonded" if faction_bond else "temporary"
            })
        
        # District vs faction conflict events
        if len(active_warriors) >= 2 and random.random() > 0.6:
            combatants = random.sample(active_warriors, 2)
            warrior1_district = district_assignments.get(combatants[0], 'Unknown')
            warrior2_district = district_assignments.get(combatants[1], 'Unknown')
            warrior1_faction = faction_assignments.get(combatants[0], 'Unknown')
            warrior2_faction = faction_assignments.get(combatants[1], 'Unknown')
            
            same_district = warrior1_district == warrior2_district
            same_faction = warrior1_faction == warrior2_faction
            
            if same_district and not same_faction:
                # District loyalty vs faction conflict
                cybertron_events.append({
                    "type": "district_betrayal",
                    "participants": combatants,
                    "description": f"{combatants[0]} and {combatants[1]}, both from District {warrior1_district}, engage in brutal combat as their faction loyalties override district bonds",
                    "location": "District Betrayal Arena",
                    "energon_cost": "District honor vs faction loyalty",
                    "cybertronian_outcome": "District unity shattered by faction conflict",
                    "district_conflicts": f"District {warrior1_district} torn apart by faction loyalties",
                    "faction_drama": f"{warrior1_faction} vs {warrior2_faction} conflict destroys district bonds"
                })
            elif same_faction and not same_district:
                # Same faction, different districts - faction loyalty test
                cybertron_events.append({
                    "type": "same_faction_elimination",
                    "participants": combatants,
                    "description": f"{combatants[0]} and {combatants[1]}, both loyal to {warrior1_faction}, face the ultimate test as survival demands faction betrayal",
                    "location": "Faction Loyalty Arena",
                    "energon_cost": "Faction honor vs survival instinct",
                    "cybertronian_outcome": "Faction unity tested by district rivalries",
                    "district_conflicts": f"District {warrior1_district} vs District {warrior2_district} rivalry threatens faction bonds",
                    "faction_drama": f"{warrior1_faction} warriors forced to betray their own faction for survival"
                })
            else:
                # Standard combat with district/faction context
                cybertron_events.append({
                    "type": "energon_combat",
                    "participants": combatants,
                    "description": f"{combatants[0]} (District {warrior1_district}, {warrior1_faction}) battles {combatants[1]} (District {warrior2_district}, {warrior2_faction}) as district and faction loyalties collide",
                    "location": "Multi-Allegiance Combat Zone",
                    "energon_cost": "Allegiance conflict energy",
                    "cybertronian_outcome": "District and faction tensions escalate",
                    "district_conflicts": "District rivalries fuel the conflict",
                    "faction_drama": "Faction politics influence the battle"
                })
        
        # Faction conversion events
        if random.random() > 0.8 and active_warriors:
            shifter = random.choice(active_warriors)
            old_faction = faction_assignments.get(shifter, 'Neutral')
            factions = ['Autobot', 'Decepticon', 'Neutral', 'Maximal', 'Predacon']
            if old_faction in factions:
                factions.remove(old_faction)
            new_faction = random.choice(factions)
            
            cybertron_events.append({
                "type": "faction_shift",
                "participants": [shifter],
                "description": f"{shifter} abandons their {old_faction} allegiance, their spark core resonating with {new_faction} ideology through dark energon corruption",
                "location": "Faction Conversion Chamber",
                "energon_cost": "Core reprogramming energy",
                "cybertronian_outcome": f"Faction loyalty shifted from {old_faction} to {new_faction}",
                "district_conflicts": f"District {district_assignments.get(shifter, 'Unknown')} loses a {old_faction} warrior",
                "faction_drama": f"{old_faction} weakened as {shifter} defects to {new_faction}"
            })
            
            alliance_shifts.append({
                "warrior": shifter,
                "new_allies": [],
                "trust_level": f"faction_shift_{new_faction}"
            })
        
        # Spark elimination with district/factor betrayal
        eliminated = []
        if eliminations_needed > 0 and active_warriors:
            eliminated = random.sample(active_warriors, min(eliminations_needed, len(active_warriors)))
            
            for eliminated_warrior in eliminated:
                killer = None
                same_faction_killer = False
                district_betrayal = False
                
                # Find potential killer with district/factor context
                if len(active_warriors) > 1:
                    possible_killers = [w for w in active_warriors if w != eliminated_warrior]
                    if possible_killers:
                        killer = random.choice(possible_killers)
                        
                        # Check for same faction elimination
                        eliminated_faction = faction_assignments.get(eliminated_warrior, 'Unknown')
                        killer_faction = faction_assignments.get(killer, 'Unknown')
                        same_faction_killer = eliminated_faction == killer_faction
                        
                        # Check for district betrayal
                        eliminated_district = district_assignments.get(eliminated_warrior, 'Unknown')
                        killer_district = district_assignments.get(killer, 'Unknown')
                        district_betrayal = eliminated_district == killer_district
                
                if killer:
                    if same_faction_killer:
                        cybertron_events.append({
                            "type": "same_faction_elimination",
                            "participants": [eliminated_warrior, killer],
                            "description": f"{killer} eliminates their own {killer_faction} faction member {eliminated_warrior}, the ultimate betrayal for survival",
                            "location": "Faction Betrayal Execution Zone",
                            "energon_cost": "Faction honor and spark core depletion",
                            "cybertronian_outcome": f"{killer_faction} faction weakened by internal betrayal",
                            "district_conflicts": f"District {district_assignments.get(killer, 'Unknown')} warrior commits faction betrayal",
                            "faction_drama": f"{killer_faction} torn apart by same-faction elimination"
                        })
                        same_faction_eliminations.append(f"{killer} eliminated {eliminated_warrior} (both {killer_faction})")
                    elif district_betrayal:
                        cybertron_events.append({
                            "type": "district_betrayal",
                            "participants": [eliminated_warrior, killer],
                            "description": f"{killer} betrays their District {eliminated_district} companion {eliminated_warrior}, choosing faction or survival over district loyalty",
                            "location": "District Betrayal Execution Zone",
                            "energon_cost": "District honor and spark core depletion",
                            "cybertronian_outcome": f"District {eliminated_district} unity shattered",
                            "district_conflicts": f"District {eliminated_district} loyalty betrayed for faction or survival",
                            "faction_drama": f"District betrayal demonstrates faction loyalty over district bonds"
                        })
                        district_betrayals.append(f"{killer} betrayed District {eliminated_district} by eliminating {eliminated_warrior}")
                    else:
                        cybertron_events.append({
                            "type": "spark_elimination",
                            "participants": [eliminated_warrior, killer],
                            "description": f"{killer} (District {district_assignments.get(killer, 'Unknown')}, {faction_assignments.get(killer, 'Unknown')}) eliminates {eliminated_warrior} (District {eliminated_district}, {eliminated_faction})",
                            "location": "Standard Elimination Zone",
                            "energon_cost": "Complete spark core depletion",
                            "cybertronian_outcome": "Standard elimination with district/factor context",
                            "district_conflicts": "District and faction tensions escalate",
                            "faction_drama": "Faction politics influence the elimination"
                        })
                    
                    spark_eliminations.append({
                        "warrior": eliminated_warrior,
                        "warrior_id": next((w['warrior_id'] for w in warriors if w['name'] == eliminated_warrior), 0),
                        "eliminated_by": killer,
                        "method": f"{eliminated_warrior}'s spark core was extinguished by {killer}",
                        "final_words": f"The betrayal... my spark... fades..." if same_faction_killer or district_betrayal else f"My spark... it grows dark...",
                        "spark_signature": f"SPARK-{next((str(p.id) for p in participants if p.display_name == eliminated_warrior), 'UNKNOWN')}",
                        "district": district_assignments.get(eliminated_warrior, 'Unknown'),
                        "faction": faction_assignments.get(eliminated_warrior, 'Unknown'),
                        "same_faction_killer": same_faction_killer,
                        "district_betrayal": district_betrayal
                    })
                else:
                    cybertron_events.append({
                        "type": "spark_elimination", 
                        "participants": [eliminated_warrior],
                        "description": f"{eliminated_warrior}'s spark core is permanently extinguished by arena hazards",
                        "location": "Arena Hazard Zone",
                        "energon_cost": "Complete spark core failure",
                        "cybertronian_outcome": "Environmental elimination",
                        "district_conflicts": f"District {district_assignments.get(eliminated_warrior, 'Unknown')} loses a warrior",
                        "faction_drama": f"{faction_assignments.get(eliminated_warrior, 'Unknown')} faction weakened"
                    })
                    
                    spark_eliminations.append({
                        "warrior": eliminated_warrior,
                        "warrior_id": next((w['warrior_id'] for w in warriors if w['name'] == eliminated_warrior), 0),
                        "eliminated_by": "Arena hazard",
                        "method": f"{eliminated_warrior}'s spark core was permanently extinguished by concentrated plasma fire",
                        "final_words": f"My spark... it grows dark... the darkness takes me...",
                        "spark_signature": f"SPARK-{next((str(p.id) for p in participants if p.display_name == eliminated_warrior), 'UNKNOWN')}",
                        "district": district_assignments.get(eliminated_warrior, 'Unknown'),
                        "faction": faction_assignments.get(eliminated_warrior, 'Unknown'),
                        "same_faction_killer": False,
                        "district_betrayal": False
                    })
                
                if eliminated_warrior in current_survivors:
                    current_survivors.remove(eliminated_warrior)
        
        # Prime relic discovery affecting alliances
        if active_warriors:
            discoverer = random.choice(active_warriors)
            cybertron_events.append({
                "type": "prime_relic",
                "participants": [discoverer],
                "description": f"{discoverer} discovers ancient Prime technology that could shift faction loyalties and alliance dynamics",
                "location": "Prime Relic Vault",
                "energon_cost": "Relic resonance energy",
                "cybertronian_outcome": "Power balance potentially altered"
            })
        
        # Arena transformation forcing temporary cooperation
        if active_warriors:
            cybertron_events.append({
                "type": "arena_trap",
                "participants": active_warriors,
                "description": "The orbital station reconfigures itself, forcing warriors into temporary alliances against the station's Omega Supreme protocols",
                "location": "Station Reconfiguration Zone",
                "energon_cost": "Arena adaptation energy",
                "cybertronian_outcome": "Environmental hazards increased"
            })
        
        return {
            "round_number": round_num,
            "cybertron_events": cybertron_events,
            "spark_eliminations": spark_eliminations,
            "cybertron_alliances": cybertron_alliances,
            "ignited_sparks": current_survivors,
            "cybertron_tech_activated": ["Energon cores", "Spark transfer protocols", "Transformation inhibitors", "Prime relics", "Dark energon processors"],
            "energon_events": ["Major energon surge detected", "Spark core fluctuations recorded", "Dark energon corruption spreading"],
            "arena_transformations": ["Station defense systems activating", "Omega Supreme protocols engaging"],
            "alliance_shifts": alliance_shifts,
            "district_conflicts": [event.get("district_conflicts") for event in cybertron_events if event.get("district_conflicts")],
            "faction_drama": [event.get("faction_drama") for event in cybertron_events if event.get("faction_drama")],
            "same_faction_eliminations": same_faction_eliminations,
            "district_betrayals": district_betrayals,
            "summary": f"Enhanced cybertronian round {round_num} with {len(cybertron_events)} events, {len(same_faction_eliminations)} same-faction eliminations, and {len(district_betrayals)} district betrayals"
        }

class CybertronGamesView(View):
    """Interactive view with Next Round button for Cybertron Games"""
    
    def __init__(self, cog, game_key, timeout=1800):  # 30 minute timeout
        super().__init__(timeout=timeout)
        self.cog = cog
        self.game_key = game_key
        self.add_item(Button(
            label="⚡ Next Cybertron Round",
            style=discord.ButtonStyle.red,
            custom_id="next_cybertron_round"
        ))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is valid"""
        return True
    
    async def on_timeout(self):
        """Handle timeout by disabling the button"""
        try:
            if hasattr(self, 'message'):
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
        except:
            pass

class CybertronGames(commands.Cog):
    """Cog for AI-powered Transformers-themed Cybertron Games"""
    
    def __init__(self, bot):
        self.bot = bot
        self.ai_generator = CybertronGamesGenerator(api_key=GEMINI_API_KEY)
        self.active_games: Dict[str, Dict[str, Any]] = {}
        self.active_views: Dict[str, CybertronGamesView] = {}
        self.round_cache: Dict[str, Dict[str, Any]] = {}  # In-memory cache for storing previous rounds
    
    def _has_cybertronian_citizen_role(self, member: discord.Member) -> bool:
        """Check if member has any Cybertronian Citizen role"""
        cybertronian_citizen_role_ids = ROLE_IDS.get('Cybertronian_Citizen', [])
        if not cybertronian_citizen_role_ids:
            return False
        
        # Check if member has any of the Cybertronian Citizen roles
        member_role_ids = [role.id for role in member.roles]
        return any(role_id in member_role_ids for role_id in cybertronian_citizen_role_ids)
    
    @commands.hybrid_command(name='cybertron_games', description="Initiate the ultimate Transformers deathmatch - The Cybertron Games")
    @app_commands.describe(
        include_bots="Include cybertronian AI units in the games",
        include_cybertronians="Include cybertronian citizens (non-bot members)",
        warriors="Number of warriors to select (2-50, default: all)",
        districts="Number of districts (2-10, default: 8)",
        factions="Number of factions (2-5, default: 5)",
        specific_participants="Specific Discord users to include (space-separated names or mentions)"
    )
    async def cybertron_games(
        self, 
        ctx, 
        include_bots: bool = False, 
        include_cybertronians: bool = True,
        warriors: int = None, 
        districts: int = 8,
        factions: int = 5,
        specific_participants: str = None
    ):
        """Start the ultimate Transformers-themed deathmatch"""
        try:
            # Create unique game key
            game_key = f"{ctx.guild.id}_{ctx.channel.id}_{ctx.author.id}"
            
            # Check for existing game
            if game_key in self.active_games:
                embed = discord.Embed(
                    title="⚡ CYBERTRON GAMES ACTIVE ⚡",
                    description="A Cybertron Games session is already active in this channel!",
                    color=0xff0000
                )
                embed.add_field(name="Status", value="Use the button below to continue the current game", inline=False)
                return await ctx.send(embed=embed)
            
            # Validate configuration
            districts = max(2, min(10, districts))
            factions = max(2, min(5, factions))
            
            # Parse specific participants first
            specific_users = []
            if specific_participants:
                # Handle mentions and names
                mentions = specific_participants.split()
                for mention in mentions:
                    mention = mention.strip()
                    member = None
                    
                    # Handle Discord mentions
                    if mention.startswith('<@') and mention.endswith('>'):
                        user_id = mention.replace('<@', '').replace('!', '').replace('>', '')
                        try:
                            member = ctx.guild.get_member(int(user_id))
                        except ValueError:
                            continue
                    else:
                        # Handle names
                        for guild_member in ctx.guild.members:
                            if mention.lower() in guild_member.display_name.lower() or mention.lower() in guild_member.name.lower():
                                member = guild_member
                                break
                    
                    if member and member not in specific_users:
                        specific_users.append(member)
            
            # Get all potential participants based on filters
            potential_participants = []
            
            for member in ctx.guild.members:
                if member.bot and not include_bots:
                    continue
                if not member.bot and include_cybertronians:
                    # Check for Cybertronian Citizen role
                    if not self._has_cybertronian_citizen_role(member):
                        continue
                elif not member.bot and not include_cybertronians:
                    continue
                
                potential_participants.append(member)
            
            # Shuffle for randomness
            random.shuffle(potential_participants)
            
            # Build final participant list
            participants = []
            
            # Always include specific users first
            for user in specific_users:
                if user in potential_participants and user not in participants:
                    participants.append(user)
            
            # Fill remaining slots with random users
            remaining_needed = (warriors or 50) - len(participants)
            for user in potential_participants:
                if len(participants) >= (warriors or 50):
                    break
                if user not in participants:
                    participants.append(user)
            
            # Limit to 50 max
            participants = participants[:50]
            
            if len(participants) < 2:
                embed = discord.Embed(
                    title="⚡ INSUFFICIENT WARRIORS ⚡",
                    description="Need at least 2 cybertronian warriors to start the games!",
                    color=0xff0000
                )
                return await ctx.send(embed=embed)
            
            # Assign districts and factions
            self.ai_generator.assign_districts_and_factions(
                participants,
                district_count=districts,
                faction_count=factions
            )
            
            # Initialize game state
            self.active_games[game_key] = {
                'participants': participants,
                'current_round': 0,
                'eliminated': [],
                'survivors': participants.copy(),
                'history': [],
                'started_by': ctx.author,
                'district_count': districts,
                'faction_count': factions,
                'district_assignments': self.ai_generator.district_tracker.copy(),
                'faction_assignments': self.ai_generator.faction_tracker.copy()
            }
            
            # Send initial embed with district and faction info
            embed = discord.Embed(
                title="🌌 **THE CYBERTRON GAMES BEGIN** 🌌",
                description=f"**{len(participants)} cybertronian warriors** have been summoned to the orbital Arena of Cybertron!\n\n**{districts} Districts** • **{factions} Factions**\n**District & Faction assignments are final for this Games**",
                color=0x00ff00
            )
            
            # Build warrior list with district and faction
            warrior_list = ""
            for i, p in enumerate(participants, 1):
                district = self.ai_generator.district_tracker.get(p.display_name, "Unknown")
                faction = self.ai_generator.faction_tracker.get(p.display_name, "Unknown")
                warrior_list += f"⚡ **{i}.** {p.display_name} - **District {district}** | **{faction}**\n"
            
            embed.add_field(name="🤖 **WARRIORS IGNITED**", value=warrior_list, inline=False)
            
            # Add district/faction summary
            district_counts = {}
            faction_counts = {}
            for p in participants:
                d = self.ai_generator.district_tracker[p.display_name]
                f = self.ai_generator.faction_tracker[p.display_name]
                district_counts[d] = district_counts.get(d, 0) + 1
                faction_counts[f] = faction_counts.get(f, 0) + 1
            
            embed.add_field(
                name="🏛️ **ALLEGIANCE BREAKDOWN**", 
                value=f"**Districts:** {len(district_counts)} active\n**Factions:** {', '.join([f'{k} ({v})' for k, v in faction_counts.items()])}", 
                inline=False
            )
            embed.add_field(name="⚡ **SPARK STATUS**", value="All sparks ignited and ready for combat", inline=False)
            embed.set_footer(text="District and faction loyalties will be tested... Who will betray whom?")
            
            # Create view and send message
            view = CybertronGamesView(self, game_key)
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            self.active_views[game_key] = view
            
            # Start first round
            await self._advance_cybertron_round(game_key, ctx)
            
        except Exception as e:
            logger.error(f"Error starting Cybertron Games: {e}")
            embed = discord.Embed(
                title="⚡ CYBERTRON ERROR ⚡",
                description=f"Failed to initialize the Cybertron Games: {str(e)}",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    async def _advance_cybertron_round(self, game_key: str, ctx):
        """Advance to the next round of the Cybertron Games"""
        try:
            game_data = self.active_games[game_key]
            game_data['current_round'] += 1
            
            # Get participants for this round
            current_participants = [p for p in game_data['participants'] 
                                  if p.display_name in [s for s in game_data['survivors']]]
            
            if len(current_participants) <= 1:
                # Game over
                winner = current_participants[0] if current_participants else None
                await self._end_cybertron_games(game_key, ctx, winner)
                return
            
            # Get previous round for context
            previous_round = None
            if game_data['history']:
                previous_round = game_data['history'][-1]
            
            # Generate round story with district and faction context
            game_data['district_assignments'] = self.ai_generator.district_tracker
            game_data['faction_assignments'] = self.ai_generator.faction_tracker
            
            round_story = self.ai_generator._generate_cybertron_round(
                game_data['current_round'], 
                current_participants, 
                previous_round
            )
            
            # Update game state
            game_data['history'].append(round_story)
            
            # Process eliminations
            for elimination in round_story.get('spark_eliminations', []):
                eliminated_name = elimination['warrior']
                game_data['eliminated'].append(elimination)
                if eliminated_name in game_data['survivors']:
                    game_data['survivors'].remove(eliminated_name)
            
            # Create round embed
            embed = discord.Embed(
                title=f"⚡ **CYBERTRON GAMES - ROUND {game_data['current_round']}** ⚡",
                description="The orbital station continues its deadly trial...",
                color=0xff4500
            )
            
            # Add cybertron events
            events_text = ""
            for event in round_story.get('cybertron_events', [])[:3]:
                events_text += f"**{event['type'].replace('_', ' ').title()}**\n"
                events_text += f"📍 {event['description']}\n\n"
            
            if events_text:
                embed.add_field(name="⚡ **CYBERTRON EVENTS**", value=events_text[:1024], inline=False)
            
            # Add alliance shifts if any
            if 'alliance_shifts' in round_story and round_story['alliance_shifts']:
                alliance_text = ""
                for shift in round_story['alliance_shifts']:
                    if shift.get('new_allies'):
                        allies_str = ", ".join(shift['new_allies'])
                        alliance_text += f"🤝 **{shift['warrior']}** allies with {allies_str} ({shift['trust_level']})\n"
                    else:
                        alliance_text += f"💔 **{shift['warrior']}** - alliance dissolved ({shift['trust_level']})\n"
                
                if alliance_text:
                    embed.add_field(name="🤝 **ALLIANCE SHIFTS**", value=alliance_text.strip()[:1024], inline=False)
            
            # Add eliminations with district/faction drama
            if round_story.get('spark_eliminations'):
                elim_text = ""
                for elim in round_story['spark_eliminations']:
                    district = game_data['district_assignments'].get(elim['warrior'], 'Unknown')
                    faction = game_data['faction_assignments'].get(elim['warrior'], 'Unknown')
                    
                    elim_text += f"💀 **{elim['warrior']}** (District {district}, {faction})\n"
                    elim_text += f"*{elim['method']}*\n"
                    
                    # Add same-faction elimination drama
                    if elim.get('same_faction_killer'):
                        elim_text += f"🔥 **SAME FACTION BETRAYAL!**\n"
                    
                    # Add district betrayal drama
                    if elim.get('district_betrayal'):
                        elim_text += f"🏛️ **DISTRICT BETRAYAL!**\n"
                    
                    if elim.get('final_words'):
                        elim_text += f"_\"{elim['final_words']}\"_\n"
                    elim_text += "\n"
                
                embed.add_field(name="💀 **SPARK ELIMINATIONS**", value=elim_text[:1024], inline=False)
            
            # Add survivors with district and faction info
            survivors_text = ""
            for survivor in game_data['survivors']:
                district = game_data['district_assignments'].get(survivor, 'Unknown')
                faction = game_data['faction_assignments'].get(survivor, 'Unknown')
                survivors_text += f"⚡ **{survivor}** (District {district}, {faction})\n"
            
            embed.add_field(name=f"🔥 **IGNITED SPARKS** ({len(game_data['survivors'])})", 
                          value=survivors_text or "No survivors", inline=False)
            
            # Add technology discovered
            if round_story.get('cybertron_tech_activated'):
                tech_text = ", ".join(round_story['cybertron_tech_activated'][:5])
                embed.add_field(name="⚙️ **CYBERTRON TECH ACTIVATED**", value=tech_text, inline=False)
            
            embed.set_footer(text="The games continue... Who's spark will extinguish next?")
            
            # Send or update message
            view = self.active_views.get(game_key)
            if view and hasattr(view, 'message'):
                await view.message.edit(embed=embed, view=view)
            else:
                new_view = CybertronGamesView(self, game_key)
                message = await ctx.send(embed=embed, view=new_view)
                new_view.message = message
                self.active_views[game_key] = new_view
                
        except Exception as e:
            logger.error(f"Error advancing Cybertron round: {e}")
            # Clean up on error
            if game_key in self.active_games:
                del self.active_games[game_key]
            if game_key in self.active_views:
                try:
                    await self.active_views[game_key].message.edit(view=None)
                except:
                    pass
                del self.active_views[game_key]
    
    async def _end_cybertron_games(self, game_key: str, ctx, winner):
        """End the Cybertron Games and announce winner"""
        try:
            game_data = self.active_games[game_key]
            
            embed = discord.Embed(
                title="🏆 **CYBERTRON GAMES COMPLETE** 🏆",
                description="The orbital station falls silent as the final spark remains ignited...",
                color=0xffd700
            )
            
            if winner:
                embed.add_field(
                    name="🏆 **VICTORIOUS SPARK**", 
                    value=f"**{winner.display_name}** - The last cybertronian warrior standing!",
                    inline=False
                )
            else:
                embed.add_field(
                    name="💀 **TOTAL ELIMINATION**", 
                    value="All sparks have been extinguished... The station claims victory",
                    inline=False
                )
            
            # Add final statistics
            total_rounds = game_data['current_round']
            total_eliminated = len(game_data['eliminated'])
            
            stats = f"**Rounds Completed:** {total_rounds}\n"
            stats += f"**Sparks Extinguished:** {total_eliminated}\n"
            stats += f"**Final Arena Status:** Systems powering down"
            
            embed.add_field(name="📊 **FINAL STATISTICS**", value=stats, inline=False)
            
            await ctx.send(embed=embed)
            
            # Clean up
            if game_key in self.active_games:
                del self.active_games[game_key]
            if game_key in self.active_views:
                try:
                    await self.active_views[game_key].message.edit(view=None)
                except:
                    pass
                del self.active_views[game_key]
                
        except Exception as e:
            logger.error(f"Error ending Cybertron Games: {e}")
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions for Cybertron Games"""
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get('custom_id')
            if custom_id == 'next_cybertron_round':
                # Find the game
                for game_key, view in self.active_views.items():
                    if interaction.message.id == view.message.id:
                        if game_key in self.active_games:
                            await interaction.response.defer()
                            await self._advance_cybertron_round(game_key, interaction)
                        break

async def setup(bot):
    """Setup function for the Cybertron Games cog"""
    await bot.add_cog(CybertronGames(bot))
    print("✅ Cybertron Games cog loaded successfully")