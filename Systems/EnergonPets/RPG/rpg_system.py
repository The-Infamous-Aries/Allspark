# Standard library imports
import json
import random
import asyncio
import math
import uuid
import logging
import sys
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# Third-party imports
import discord
import google.generativeai as genai
from discord.ext import commands
from discord import app_commands

# Local system path setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Local imports
from Systems.user_data_manager import user_data_manager
from Systems.EnergonPets.PetBattles.battle_system import UnifiedBattleView
from Systems.EnergonPets.PetBattles.enemy_selection_view import EnemySelectionView
from Systems.EnergonPets.pet_levels import add_experience, get_next_level_xp
from config import GEMINI_API_KEY

logger = logging.getLogger('rpg_system')

@dataclass
class ResourceCost:
    """Represents resource costs for events"""
    energy: int = 0
    maintenance: int = 0
    happiness: int = 0

@dataclass
class RPGEvent:
    """Represents an RPG event with resource costs"""
    id: str
    name: str
    description: str
    resource_costs: ResourceCost
    success_chance: float
    success_rewards: Dict[str, Any]
    failure_consequences: Dict[str, Any]
    ai_context: str

@dataclass
class StoryMoment:
    """Represents a story moment for continuity"""
    timestamp: datetime
    event_type: str  # 'event', 'battle', 'story'
    description: str
    participants: List[str]
    outcome: str
    location: str

class AIStoryGenerator:
    """AI-powered story generation for the Transformers RPG"""
    
    def __init__(self, api_key: str = None):
        if api_key:
            genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
    def _clean_ai_response(self, text: str) -> str:
        """Clean AI response by removing conversational preambles"""
        # Remove common conversational starters
        cleaned = text.strip()
        
        # Remove phrases like "Of course!", "Here is", "I can help", etc.
        conversational_patterns = [
            r'^Of course![\s]*',
            r'^Here is[\s]*',
            r'^I can help[\s]*',
            r'^Let me create[\s]*',
            r'^I\'ll help[\s]*',
            r'^Here\'s[\s]*',
            r'^Certainly![\s]*',
            r'^Absolutely![\s]*',
        ]
        
        import re
        for pattern in conversational_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # If the response starts with **Event:, **Battle:, etc., it's already formatted correctly
        if cleaned.startswith('**'):
            return cleaned
        
        # If we removed conversational text but the formatted content follows, extract it
        if '**Event:' in cleaned:
            return cleaned[cleaned.find('**Event:'):]
        elif '**Battle Encounter:' in cleaned:
            return cleaned[cleaned.find('**Battle Encounter:'):]
        elif '**Battle Outcome:' in cleaned:
            return cleaned[cleaned.find('**Battle Outcome:'):]
        elif '**Journey Segment:' in cleaned:
            return cleaned[cleaned.find('**Journey Segment:'):]
        
        return cleaned

    async def generate_event_description(self, context: Dict[str, Any]) -> str:
        """Generate AI event description based on context"""
        pet_level = context.get('pet_level', 1)
        pet_stats = context.get('pet_stats', {})
        
        prompt = f"""Create an engaging Transformers-themed RPG event for a pet adventure.
        
Context:
- Location: {context.get('location', 'Cybertron')}
- Pet Names: {', '.join(context.get('pet_names', ['Unknown']))}
- Pet Factions: {', '.join(context.get('pet_factions', ['Unknown']))}
- Previous Event: {context.get('last_moment', 'Starting adventure')}
- Pet Level: {pet_level}
- Pet Stats: Attack {pet_stats.get('attack', 10)}, Defense {pet_stats.get('defense', 10)}, HP {pet_stats.get('health', 100)}/{pet_stats.get('max_health', 100)}
- Available Resources: Energy, Maintenance, Happiness

Generate a compelling event that:
1. Has a clear Transformers theme (Autobots vs Decepticons, energon mining, tech repair, etc.)
2. Requires pets to spend Energy, Maintenance, or Happiness to succeed
3. The challenge difficulty should match the pet's level ({pet_level}) and current condition
4. Has meaningful consequences for success/failure
5. Fits naturally after the previous event
6. Is engaging and atmospheric

The event should feel appropriate for a level {pet_level} pet with the current stats.

Format as:
**Event: [Event Name]**
[Detailed description of the situation]

**Challenge:** [What the pets need to do - make this match their capabilities]
**Cost:** [Which resources are needed and why - Energy for physical effort, Maintenance for repairs, Happiness for social challenges]
**Reward:** [What they gain if successful - should scale with difficulty]
**Risk:** [What happens if they fail or refuse]"""

        try:
            response = await self.model.generate_content_async(prompt)
            return self._clean_ai_response(response.text)
        except Exception as e:
            logger.error(f"AI event generation failed: {e}")
            return self._generate_fallback_event(context)
    
    async def generate_battle_encounter(self, context: Dict[str, Any]) -> str:
        """Generate AI battle encounter description"""
        prompt = f"""Create an exciting Transformers battle encounter description.
        
Context:
- Enemy: {context.get('enemy_name', 'Unknown Enemy')}
- Enemy Type: {context.get('enemy_type', 'Monster')}
- Enemy Rarity: {context.get('enemy_rarity', 'Common')}
- Pet Party: {', '.join(context.get('pet_names', ['Unknown']))}
- Location: {context.get('location', 'Cybertron')}

Generate a vivid battle encounter that:
1. Describes the enemy in Transformers terms
2. Sets up an exciting combat scenario
3. Explains why they're fighting
4. Creates atmosphere and tension

Format as:
**Battle Encounter: [Enemy Name]**
[Detailed description of the enemy and the confrontation]

**The Scene:** [What happens as battle begins]
**Tactical Situation:** [Advantages/disadvantages for both sides]"""

        try:
            response = await self.model.generate_content_async(prompt)
            return self._clean_ai_response(response.text)
        except Exception as e:
            logger.error(f"AI battle encounter generation failed: {e}")
            return self._generate_fallback_battle_encounter(context)
    
    async def generate_battle_outcome(self, context: Dict[str, Any]) -> str:
        """Generate AI battle outcome description"""
        prompt = f"""Create a dramatic Transformers battle outcome description.
        
Context:
- Enemy: {context.get('enemy_name', 'Unknown Enemy')}
- Victory: {context.get('victory', True)}
- Survivors: {', '.join(context.get('survivors', []))}
- Fallen: {', '.join(context.get('fallen', []))}
- Location: {context.get('location', 'Cybertron')}

Generate an outcome description that:
1. Celebrates victory or mourns defeat appropriately
2. Acknowledges the survivors and fallen
3. Sets up the next part of the adventure
4. Maintains Transformers atmosphere

Format as:
**Battle Outcome: [Victory/Defeat]**
[Detailed description of what happened]

**Aftermath:** [Consequences and next steps]
**The Living:** [What the survivors do next]"""

        try:
            response = await self.model.generate_content_async(prompt)
            return self._clean_ai_response(response.text)
        except Exception as e:
            logger.error(f"AI battle outcome generation failed: {e}")
            return self._generate_fallback_battle_outcome(context)
    
    async def generate_story_segment(self, context: Dict[str, Any]) -> str:
        """Generate AI story segment for non-combat activities"""
        prompt = f"""Create an engaging Transformers story segment for traveling or non-combat activities.
        
Context:
- Pet Party: {', '.join(context.get('pet_names', ['Unknown']))}
- Pet Factions: {', '.join(context.get('pet_factions', ['Unknown']))}
- Previous Event: {context.get('last_moment', 'Starting journey')}
- Location: {context.get('location', 'Cybertron')}
- Activity: {context.get('activity', 'Traveling')}

Generate a story segment that:
1. Describes the pets' journey or activity
2. Builds atmosphere and world-building
3. Foreshadows future events
4. Develops the ongoing narrative
5. Is engaging but peaceful (no combat)

Format as:
**Journey Segment: [Location/Activity]**
[Detailed description of what the pets are doing]

**Observations:** [What they notice or learn]
**The Path Ahead:** [What comes next in their journey]"""

        try:
            response = await self.model.generate_content_async(prompt)
            return self._clean_ai_response(response.text)
        except Exception as e:
            logger.error(f"AI story generation failed: {e}")
            return self._generate_fallback_story(context)
    
    async def generate_comprehensive_story_segment(self, context: Dict[str, Any]) -> str:
        """Generate comprehensive D&D-style story segment based on recent events"""
        recent_events = context.get('recent_events', [])
        story_arc = context.get('story_arc', 'Beginning a new adventure')
        character_development = context.get('character_development', 'Starting their journey')
        narrative_threads = context.get('narrative_threads', [])
        current_location = context.get('current_location', 'Cybertron')
        participants = context.get('participants', ['Unknown'])
        
        # Build recent events summary for context
        events_summary = ""
        if recent_events:
            events_summary = "Recent Events:\n"
            for i, event in enumerate(recent_events[-4:], 1):  # Last 4 events
                events_summary += f"{i}. {event['type'].title()}: {event['description'][:100]}... (Outcome: {event['outcome']})\n"
        
        prompt = f"""You are a masterful D&D Game Master creating a comprehensive story segment for a Transformers RPG adventure. 

**Character Context:**
- Party: {', '.join(participants)}
- Current Location: {current_location}
- Character Development: {character_development}
- Story Arc: {story_arc}
- Active Narrative Threads: {', '.join(narrative_threads) if narrative_threads else 'New adventure beginning'}

**Recent Adventure History:**
{events_summary if events_summary else "This is the beginning of their adventure."}

**Your Task:**
Create a rich, immersive story segment that:
1. **Acknowledges the Journey**: Reference and build upon recent events naturally
2. **Develops Character**: Show how recent experiences have shaped the characters
3. **Advances the Plot**: Move the overarching story forward meaningfully
4. **Creates Atmosphere**: Paint a vivid picture of the Transformers universe
5. **Sets Up Future**: Hint at upcoming challenges or opportunities
6. **Maintains Continuity**: Ensure the story flows logically from recent events

**Style Guidelines:**
- Write like a skilled D&D Game Master narrating between encounters
- Use rich, descriptive language that brings the world to life
- Include character moments that show growth and personality
- Balance action, dialogue, and description
- Create hooks for future adventures
- Maintain the epic scope of Transformers lore

Format as:
**Chronicle Entry: [Descriptive Title]**
[Main narrative - 3-4 paragraphs of rich storytelling]

**Character Moments:** [How the recent events have affected the characters]
**The World Around Them:** [Environmental details and world-building]
**Foreshadowing:** [Subtle hints about what may come next]"""

        try:
            response = await self.model.generate_content_async(prompt)
            return self._clean_ai_response(response.text)
        except Exception as e:
            logger.error(f"AI comprehensive story generation failed: {e}")
            return self._generate_fallback_comprehensive_story(context)
    
    def _generate_fallback_event(self, context: Dict[str, Any]) -> str:
        """Generate fallback event when AI fails"""
        return f"""**Event: Energon Cache Discovery**
Your pet party discovers a hidden energon cache while exploring {context.get('location', 'Cybertron')}.

**Challenge:** The cache is protected by ancient Cybertronian security protocols.
**Cost:** Each pet must spend 15 Energy to interface with the security system, or 10 Maintenance to manually bypass it.
**Reward:** Success yields energon crystals and valuable tech components.
**Risk:** Failure triggers security drones that must be fought, or refusal leaves the cache unexplored."""
    
    def _generate_fallback_battle_encounter(self, context: Dict[str, Any]) -> str:
        """Generate fallback battle encounter when AI fails"""
        return f"""**Battle Encounter: {context.get('enemy_name', 'Security Drone')}**
A hostile {context.get('enemy_type', 'monster')} emerges from the shadows of {context.get('location', 'Cybertron')}!

**The Scene:** The enemy charges forward with malicious intent, its weapons systems activating.
**Tactical Situation:** Your pets must work together to overcome this mechanical threat."""
    
    def _generate_fallback_battle_outcome(self, context: Dict[str, Any]) -> str:
        """Generate fallback battle outcome when AI fails"""
        if context.get('victory', True):
            return f"""**Battle Outcome: Victory!**
Your pet party has defeated the {context.get('enemy_name', 'enemy')}!

**Aftermath:** The battlefield falls silent as your pets celebrate their hard-won victory.
**The Living:** The survivors gather their strength and prepare for the next challenge."""
        else:
            return f"""**Battle Outcome: Defeat...**
The {context.get('enemy_name', 'enemy')} has overcome your pet party.

**Aftermath:** The survivors retreat to recover and plan their next move.
**The Living:** Though defeated, your pets learn from this experience and grow stronger."""
    
    def _generate_fallback_story(self, context: Dict[str, Any]) -> str:
        """Generate fallback story when AI fails"""
        return f"""**Journey Segment: {context.get('location', 'Cybertron Wastelands')}**
Your pet party continues their journey through the mechanical landscape.

**Observations:** They notice signs of recent energon mining activity and Decepticon patrol patterns.
**The Path Ahead:** The journey continues toward their ultimate destination, with new challenges awaiting."""

    def _generate_fallback_comprehensive_story(self, context: Dict[str, Any]) -> str:
        """Generate fallback comprehensive story when AI fails"""
        participants = context.get('participants', ['Your pet'])
        location = context.get('location', 'Cybertron Wastelands')
        recent_events = context.get('recent_events', [])
        
        # Create a basic narrative based on available context
        participant_text = ", ".join(participants) if len(participants) > 1 else participants[0]
        
        story = f"""**Chapter: The Continuing Journey**
*Location: {location}*

{participant_text} continues their adventure through the mechanical landscape of Cybertron. """
        
        if recent_events:
            story += f"Drawing from their recent experiences, they remain vigilant and ready for whatever challenges lie ahead. "
        
        story += f"""The energon-rich environment pulses with both opportunity and danger.

**Current Situation:** The party finds themselves at a crossroads, where their past experiences guide their next decisions.
**Character Development:** Each challenge has strengthened their resolve and deepened their understanding of this mechanical world.
**The Path Forward:** New adventures await, building upon the foundation of their previous encounters."""
        
        return story

class ResourceManager:
    """Manages pet resources (Energy, Maintenance, Happiness)"""
    
    @staticmethod
    async def can_afford_cost(pet_data: Dict[str, Any], cost: ResourceCost) -> bool:
        """Check if pet can afford the resource cost"""
        current_energy = pet_data.get('energy', 0)
        current_maintenance = pet_data.get('maintenance', 0)
        current_happiness = pet_data.get('happiness', 0)
        
        return (current_energy >= cost.energy and 
                current_maintenance >= cost.maintenance and 
                current_happiness >= cost.happiness)
    
    @staticmethod
    async def deduct_resources(user_id: str, cost: ResourceCost) -> bool:
        """Deduct resources from pet, return True if successful"""
        try:
            pet_data = await user_data_manager.get_pet_data(user_id)
            if not pet_data:
                return False
            
            # Check if pet can afford
            if not await ResourceManager.can_afford_cost(pet_data, cost):
                return False
            
            # Deduct resources
            pet_data['energy'] = max(0, pet_data.get('energy', 0) - cost.energy)
            pet_data['maintenance'] = max(0, pet_data.get('maintenance', 0) - cost.maintenance)
            pet_data['happiness'] = max(0, pet_data.get('happiness', 0) - cost.happiness)
            
            # Save updated data - use pet name as username if available, otherwise user_id
            username = pet_data.get('name', user_id)
            await user_data_manager.save_pet_data(user_id, username, pet_data)
            return True
            
        except Exception as e:
            logger.error(f"Error deducting resources for user {user_id}: {e}")
            return False
    
    @staticmethod
    async def restore_resources(user_id: str, energy: int = 0, maintenance: int = 0, happiness: int = 0) -> bool:
        """Restore resources to pet"""
        try:
            pet_data = await user_data_manager.get_pet_data(user_id)
            if not pet_data:
                return False
            
            # Get max values
            max_energy = pet_data.get('max_energy', 100)
            max_maintenance = pet_data.get('max_maintenance', 100)
            max_happiness = pet_data.get('max_happiness', 100)
            
            # Restore resources (capped at max)
            pet_data['energy'] = min(max_energy, pet_data.get('energy', 0) + energy)
            pet_data['maintenance'] = min(max_maintenance, pet_data.get('maintenance', 0) + maintenance)
            pet_data['happiness'] = min(max_happiness, pet_data.get('happiness', 0) + happiness)
            
            # Save updated data - use pet name as username if available, otherwise user_id
            username = pet_data.get('name', user_id)
            await user_data_manager.save_pet_data(user_id, username, pet_data)
            return True
            
        except Exception as e:
            logger.error(f"Error restoring resources for user {user_id}: {e}")
            return False

class LootSystem:
    """Handles loot generation and equipment management"""
    
    def __init__(self):
        self.equipment_data = {}
        self._equipment_loaded = False
    
    async def _load_equipment_data(self):
        """Load equipment data from JSON asynchronously"""
        if self._equipment_loaded:
            return
            
        try:
            equipment_path = Path(__file__).parent.parent.parent / 'Data' / 'pet_equipment.json'
            if equipment_path.exists():
                # Use asyncio to run file I/O in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                def load_json():
                    with open(equipment_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                
                self.equipment_data = await loop.run_in_executor(None, load_json)
                self._equipment_loaded = True
        except Exception as e:
            logger.error(f"Error loading equipment data: {e}")
            self.equipment_data = {}
            self._equipment_loaded = True
    
    async def get_loot_by_level(self, level: int, count: int = 1) -> List[Dict[str, Any]]:
        """Get loot based on pet level"""
        # Ensure equipment data is loaded
        await self._load_equipment_data()
        
        if level <= 100:
            rarities = ['common', 'uncommon']
        elif level <= 200:
            rarities = ['rare', 'epic']
        else:
            rarities = ['legendary', 'mythic']
        
        loot = []
        for _ in range(count):
            rarity = random.choice(rarities)
            item = self._get_random_item_by_rarity(rarity)
            if item:
                loot.append(item)
        
        return loot
    
    def _get_random_item_by_rarity(self, rarity: str) -> Optional[Dict[str, Any]]:
        """Get random item by rarity"""
        try:
            all_items = []
            
            # Collect all items of specified rarity
            for category in ['beast_modes', 'transformations', 'weapons', 'armor']:
                if category in self.equipment_data:
                    for item_id, item_data in self.equipment_data[category].items():
                        if item_data.get('rarity', '').lower() == rarity:
                            item_copy = dict(item_data)
                            item_copy['id'] = item_id
                            item_copy['category'] = category
                            all_items.append(item_copy)
            
            # Return random item if available
            if all_items:
                return random.choice(all_items)
            
            # Fallback item
            return {
                'name': f'{rarity.title()} Energon Cube',
                'type': 'consumable',
                'rarity': rarity,
                'value': 10 + (['common', 'uncommon', 'rare', 'epic', 'legendary', 'mythic'].index(rarity) * 5)
            }
            
        except Exception as e:
            logger.error(f"Error getting random item by rarity {rarity}: {e}")
            return None

class StoryContinuityTracker:
    """Tracks story continuity and last moments"""
    
    def __init__(self):
        self.story_moments: Dict[str, List[StoryMoment]] = {}
    
    async def add_moment(self, user_id: str, moment: StoryMoment):
        """Add a story moment for continuity tracking"""
        if user_id not in self.story_moments:
            self.story_moments[user_id] = []
        
        self.story_moments[user_id].append(moment)
        
        # Keep only last 10 moments to prevent memory issues
        if len(self.story_moments[user_id]) > 10:
            self.story_moments[user_id] = self.story_moments[user_id][-10:]
    
    def get_last_moment(self, user_id: str) -> Optional[StoryMoment]:
        """Get the last story moment for continuity"""
        if user_id in self.story_moments and self.story_moments[user_id]:
            return self.story_moments[user_id][-1]
        return None
    
    def get_story_context(self, user_id: str) -> Dict[str, Any]:
        """Get story context for AI generation"""
        last_moment = self.get_last_moment(user_id)
        if last_moment:
            return {
                'last_moment': last_moment.description,
                'last_location': last_moment.location,
                'last_outcome': last_moment.outcome,
                'participants': last_moment.participants
            }
        return {
            'last_moment': 'Starting a new adventure on Cybertron',
            'last_location': 'Cybertron',
            'last_outcome': 'Beginning journey',
            'participants': []
        }
    
    def get_recent_moments(self, user_id: str, count: int = 4) -> List[StoryMoment]:
        """Get the last N story moments for comprehensive storytelling"""
        if user_id in self.story_moments and self.story_moments[user_id]:
            return self.story_moments[user_id][-count:]
        return []
    
    def get_comprehensive_story_context(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive story context for D&D-style storytelling"""
        recent_moments = self.get_recent_moments(user_id, 4)
        
        if not recent_moments:
            return {
                'recent_events': [],
                'story_arc': 'Beginning a new adventure on Cybertron',
                'current_location': 'Cybertron',
                'character_development': 'Starting their journey',
                'narrative_threads': [],
                'participants': []
            }
        
        # Analyze recent events for narrative patterns
        locations = [moment.location for moment in recent_moments]
        outcomes = [moment.outcome for moment in recent_moments]
        event_types = [moment.event_type for moment in recent_moments]
        all_participants = set()
        for moment in recent_moments:
            all_participants.update(moment.participants)
        
        # Create narrative threads
        narrative_threads = []
        if 'victory' in outcomes:
            narrative_threads.append('Growing stronger through victories')
        if 'defeat' in outcomes:
            narrative_threads.append('Learning from setbacks')
        if 'battle' in event_types:
            narrative_threads.append('Facing dangerous enemies')
        if 'event' in event_types:
            narrative_threads.append('Overcoming challenges')
        if 'story' in event_types:
            narrative_threads.append('Exploring the world')
        
        # Determine story arc progression
        recent_outcomes = outcomes[-2:] if len(outcomes) >= 2 else outcomes
        if all(outcome in ['victory', 'success'] for outcome in recent_outcomes):
            story_arc = 'On a successful streak, confidence growing'
        elif all(outcome in ['defeat', 'failure'] for outcome in recent_outcomes):
            story_arc = 'Facing adversity, but determination remains strong'
        else:
            story_arc = 'Experiencing the ups and downs of adventure'
        
        return {
            'recent_events': [
                {
                    'type': moment.event_type,
                    'description': moment.description,
                    'outcome': moment.outcome,
                    'location': moment.location,
                    'timestamp': moment.timestamp.strftime('%Y-%m-%d %H:%M')
                } for moment in recent_moments
            ],
            'story_arc': story_arc,
            'current_location': recent_moments[-1].location,
            'character_development': self._analyze_character_development(recent_moments),
            'narrative_threads': narrative_threads,
            'participants': list(all_participants)
        }
    
    def _analyze_character_development(self, moments: List[StoryMoment]) -> str:
        """Analyze character development from recent events"""
        if not moments:
            return 'Just beginning their journey'
        
        victories = sum(1 for m in moments if m.outcome in ['victory', 'success'])
        defeats = sum(1 for m in moments if m.outcome in ['defeat', 'failure'])
        battles = sum(1 for m in moments if m.event_type == 'battle')
        
        if victories > defeats and battles > 0:
            return 'Becoming a seasoned warrior through trials'
        elif defeats > victories:
            return 'Learning resilience through hardship'
        elif battles == 0:
            return 'Growing through exploration and discovery'
        else:
            return 'Developing balance between caution and courage'

class TransformersAIDnD:
    """Main AI-powered Transformers D&D system"""
    
    def __init__(self, api_key: str = None):
        # Use GEMINI_API_KEY from config if no key provided
        if api_key is None:
            api_key = GEMINI_API_KEY
        self.ai_generator = AIStoryGenerator(api_key)
        self.resource_manager = ResourceManager()
        self.loot_system = LootSystem()
        self.story_tracker = StoryContinuityTracker()
        self.active_events = {}
        self.event_cooldowns = {}
        
        # Event templates for variety
        self.event_templates = [
            {
                'name': 'Energon Cache Discovery',
                'base_cost': ResourceCost(energy=15, maintenance=0, happiness=0),
                'success_chance': 0.7,
                'rewards': {'xp': 50, 'loot': 1},
                'ai_context': 'ancient energon cache'
            },
            {
                'name': 'Mechanical Repair Needed',
                'base_cost': ResourceCost(energy=0, maintenance=20, happiness=0),
                'success_chance': 0.8,
                'rewards': {'xp': 40, 'loot': 1},
                'ai_context': 'damaged machinery'
            },
            {
                'name': 'Social Negotiation',
                'base_cost': ResourceCost(energy=0, maintenance=0, happiness=15),
                'success_chance': 0.6,
                'rewards': {'xp': 60, 'loot': 2},
                'ai_context': 'diplomatic encounter'
            },
            {
                'name': 'Tech Scavenging',
                'base_cost': ResourceCost(energy=10, maintenance=10, happiness=0),
                'success_chance': 0.75,
                'rewards': {'xp': 45, 'loot': 2},
                'ai_context': 'abandoned technology'
            },
            {
                'name': 'Energon Mining',
                'base_cost': ResourceCost(energy=25, maintenance=5, happiness=0),
                'success_chance': 0.65,
                'rewards': {'xp': 55, 'loot': 1, 'resources': {'energy': 20}},
                'ai_context': 'energon extraction'
            }
        ]
    
    def _calculate_dynamic_costs(self, pet_data: Dict[str, Any], base_percentage: float = 0.15) -> ResourceCost:
        """Calculate resource costs based on pet stats and level"""
        # Use effective level that factors in equipment bonuses
        effective_level = self._calculate_effective_level_with_equipment(pet_data)
        
        # Base resource pools scale with effective level
        base_energy_pool = 50 + (effective_level * 5)  # Energy increases with level
        base_maintenance_pool = 40 + (effective_level * 4)  # Maintenance increases with level
        base_happiness_pool = 30 + (effective_level * 3)  # Happiness increases with level
        
        # Calculate costs as percentage of base pools (default 15%)
        energy_cost = int(base_energy_pool * base_percentage)
        maintenance_cost = int(base_maintenance_pool * base_percentage)
        happiness_cost = int(base_happiness_pool * base_percentage)
        
        # Adjust based on pet's current condition (wounded pets need more maintenance)
        current_hp = pet_data.get('hp', 100)
        max_hp = pet_data.get('max_hp', 100)
        
        if current_hp < max_hp * 0.5:  # If pet is wounded
            maintenance_cost = int(maintenance_cost * 1.5)  # 50% more maintenance cost
        
        # Ensure minimum costs
        energy_cost = max(5, energy_cost)
        maintenance_cost = max(5, maintenance_cost)
        happiness_cost = max(3, happiness_cost)
        
        return ResourceCost(energy=energy_cost, maintenance=maintenance_cost, happiness=happiness_cost)
    
    def _calculate_success_chance(self, pet_data: Dict[str, Any], event_difficulty: str = 'medium') -> float:
        """Calculate success chance based on pet stats and level"""
        # Use effective level that factors in equipment bonuses
        effective_level = self._calculate_effective_level_with_equipment(pet_data)
        
        # Also include equipment stat bonuses in attack/defense calculations
        equipment = pet_data.get('equipment', {})
        equipment_attack_bonus = 0
        equipment_defense_bonus = 0
        
        for slot, item in equipment.items():
            if item and isinstance(item, dict):
                stat_bonus = item.get('stat_bonus', {})
                equipment_attack_bonus += stat_bonus.get('attack', 0)
                equipment_defense_bonus += stat_bonus.get('defense', 0)
        
        # Use total stats including equipment bonuses
        base_attack = pet_data.get('attack', 10)
        base_defense = pet_data.get('defense', 10)
        attack = base_attack + equipment_attack_bonus
        defense = base_defense + equipment_defense_bonus
        
        # Base success chance
        base_chance = 0.6
        
        # Level bonus (higher effective level = better chance)
        level_bonus = min(0.2, (effective_level - 1) * 0.02)  # Max 20% bonus at effective level 11+
        
        # Stat bonus (better stats = better chance)
        total_stats = attack + defense
        stat_bonus = min(0.15, total_stats * 0.001)  # Max 15% bonus for high stats
        
        # Difficulty modifier
        difficulty_modifiers = {
            'easy': 0.2,
            'medium': 0.0,
            'hard': -0.15,
            'extreme': -0.3
        }
        difficulty_modifier = difficulty_modifiers.get(event_difficulty, 0.0)
        
        # Calculate final chance
        final_chance = base_chance + level_bonus + stat_bonus + difficulty_modifier
        
        # Clamp between 10% and 95%
        return max(0.1, min(0.95, final_chance))
    
    async def generate_random_event(self, user_id: str, pet_data: Dict[str, Any]) -> RPGEvent:
        """Generate a dynamic event for the user based on pet stats and story context"""
        # Get story context for continuity
        story_context = self.story_tracker.get_story_context(user_id)
        story_context.update({
            'pet_names': [pet_data.get('name', 'Unknown')],
            'pet_factions': [pet_data.get('faction', 'Unknown')],
            'location': story_context.get('last_location', 'Cybertron'),
            'pet_level': pet_data.get('level', 1),
            'pet_stats': {
                'attack': pet_data.get('attack', 10),
                'defense': pet_data.get('defense', 10),
                'health': pet_data.get('health', 100),
                'max_health': pet_data.get('max_health', 100)
            }
        })
        
        # Calculate dynamic costs and success chance
        resource_costs = self._calculate_dynamic_costs(pet_data)
        success_chance = self._calculate_success_chance(pet_data)
        
        # Generate AI event description with dynamic context
        ai_description = await self.ai_generator.generate_event_description(story_context)
        
        # Generate dynamic event name and context using AI
        event_prompt = f"""Generate a short, exciting name for a Transformers-themed RPG event.
        
Context: {story_context}
Current situation: Pet level {pet_data.get('level', 1)}, resources needed: {resource_costs.energy} energy, {resource_costs.maintenance} maintenance, {resource_costs.happiness} happiness

Create a compelling event name that fits the Transformers universe and matches the resource costs."""
        
        try:
            event_name_response = await self.ai_generator.model.generate_content_async(event_prompt)
            event_name = self.ai_generator._clean_ai_response(event_name_response.text).strip()
            # Extract just the name if it contains extra formatting
            if '**' in event_name:
                event_name = event_name.replace('**', '').strip()
            if len(event_name) > 50:  # Keep names reasonable length
                event_name = event_name[:50] + "..."
        except Exception as e:
            logger.error(f"AI event name generation failed: {e}")
            event_name = f"Challenge at Level {pet_data.get('level', 1)}"
        
        # Create event ID
        event_id = f"event_{user_id}_{int(datetime.now().timestamp())}"
        
        # Create dynamic rewards based on difficulty and level
        # Use effective level that factors in equipment bonuses
        effective_level = self._calculate_effective_level_with_equipment(pet_data)
        base_xp = 30 + (effective_level * 5)  # XP scales with effective level
        loot_count = 1 if success_chance > 0.7 else 2  # Harder events give more loot
        
        success_rewards = {
            'xp': int(base_xp * success_chance),  # More XP for higher success chance
            'loot': loot_count,
            'resources': {
                'energy': int(resource_costs.energy * 0.3) if success_chance < 0.6 else 0,  # Refund some energy on hard successes
                'maintenance': 0,
                'happiness': int(resource_costs.happiness * 0.2) if success_chance > 0.8 else 0  # Bonus happiness on easy successes
            }
        }
        
        # Create event
        event = RPGEvent(
            id=event_id,
            name=event_name,
            description=ai_description,
            resource_costs=resource_costs,
            success_chance=success_chance,
            success_rewards=success_rewards,
            failure_consequences={'battle': True, 'resource_loss': 0.3},  # Reduced from 0.5
            ai_context=f"level_{level}_challenge"
        )
        
        return event
    
    async def handle_event_choice(self, user_id: str, event_id: str, choice: str, interaction: discord.Interaction) -> Dict[str, Any]:
        """Handle user's event choice (accept cost or refuse)"""
        if event_id not in self.active_events:
            return {'success': False, 'message': 'Event expired or not found.'}
        
        event = self.active_events[event_id]
        pet_data = await user_data_manager.get_pet_data(user_id)
        
        if not pet_data:
            return {'success': False, 'message': 'Pet not found.'}
        
        if choice == 'accept':
            # Try to deduct resources
            if await self.resource_manager.deduct_resources(user_id, event.resource_costs):
                # Resource deduction successful, determine outcome
                success = random.random() < event.success_chance
                
                if success:
                    # Success - give rewards
                    rewards = event.success_rewards
                    xp_gain = rewards.get('xp', 50)
                    loot_count = rewards.get('loot', 1)
                    
                    # Award XP and check for level up
                    level_result = await add_experience(user_id, xp_gain)
                    
                    # Generate loot based on effective pet level (factoring in equipment)
                    effective_level = self._calculate_effective_level_with_equipment(pet_data)
                    loot = await self.loot_system.get_loot_by_level(effective_level, loot_count)
                    
                    # Add any resource rewards
                    if 'resources' in rewards:
                        resources = rewards['resources']
                        await self.resource_manager.restore_resources(
                            user_id,
                            energy=resources.get('energy', 0),
                            maintenance=resources.get('maintenance', 0),
                            happiness=resources.get('happiness', 0)
                        )
                    
                    # Record story moment
                    moment = StoryMoment(
                        timestamp=datetime.now(),
                        event_type='event',
                        description=f"Successfully completed: {event.name}",
                        participants=[pet_data.get('name', 'Unknown')],
                        outcome='success',
                        location='Cybertron'
                    )
                    await self.story_tracker.add_moment(user_id, moment)
                    
                    # Clean up event
                    del self.active_events[event_id]
                    
                    return {
                        'success': True,
                        'outcome': 'success',
                        'message': f"Success! You completed the {event.name.lower()} and gained {xp_gain} XP!",
                        'level_up': level_result.get('leveled_up', False),
                        'loot': loot
                    }
                else:
                    # Failure - trigger battle
                    del self.active_events[event_id]
                    return {
                        'success': True,
                        'outcome': 'failure',
                        'message': f"You failed the {event.name.lower()} and triggered a hostile encounter!",
                        'battle_triggered': True
                    }
            else:
                # Not enough resources
                return {
                    'success': False,
                    'message': 'Not enough resources to attempt this challenge!',
                    'needed': {
                        'energy': event.resource_costs.energy,
                        'maintenance': event.resource_costs.maintenance,
                        'happiness': event.resource_costs.happiness
                    }
                }
        
        elif choice == 'refuse':
            # Refuse the event - trigger battle
            del self.active_events[event_id]
            
            # Record story moment
            moment = StoryMoment(
                timestamp=datetime.now(),
                event_type='event',
                description=f"Refused to attempt: {event.name}",
                participants=[pet_data.get('name', 'Unknown')],
                outcome='refused',
                location='Cybertron'
            )
            await self.story_tracker.add_moment(user_id, moment)
            
            return {
                'success': True,
                'outcome': 'refused',
                'message': f"You refused the challenge and attracted unwanted attention...",
                'battle_triggered': True
            }
        
        return {'success': False, 'message': 'Invalid choice.'}
    
    async def start_battle_encounter(self, user_id: str, ctx: commands.Context, enemy_type: str = 'monster', enemy_rarity: str = 'common') -> UnifiedBattleView:
        """Start a battle encounter when event fails or is refused"""
        # Get pet data for battle
        pet_data = await user_data_manager.get_pet_data(user_id)
        if not pet_data:
            return None
        
        # Generate AI battle encounter description
        battle_context = {
            'enemy_name': f'{enemy_rarity.title()} {enemy_type.title()}',
            'enemy_type': enemy_type,
            'enemy_rarity': enemy_rarity,
            'pet_names': [pet_data.get('name', 'Unknown')],
            'location': 'Cybertron'
        }
        
        encounter_description = await self.ai_generator.generate_battle_encounter(battle_context)
        
        # Create battle view with selected enemy
        battle_view = await UnifiedBattleView.create_async(
            ctx,
            battle_type='solo',
            selected_enemy_type=enemy_type,
            selected_rarity=enemy_rarity
        )
        
        # Store encounter description for later use
        battle_view.encounter_description = encounter_description
        
        return battle_view
    
    async def generate_story_segment(self, user_id: str) -> str:
        """Generate a story segment for non-combat activities"""
        pet_data = await user_data_manager.get_pet_data(user_id)
        if not pet_data:
            return "Your pet rests and prepares for the next adventure."
        
        # Get story context
        story_context = self.story_tracker.get_story_context(user_id)
        story_context.update({
            'pet_names': [pet_data.get('name', 'Unknown')],
            'pet_factions': [pet_data.get('faction', 'Unknown')],
            'activity': 'Traveling and exploring'
        })
        
        # Generate AI story segment
        story_segment = await self.ai_generator.generate_story_segment(story_context)
        
        # Record story moment
        moment = StoryMoment(
            timestamp=datetime.now(),
            event_type='story',
            description=story_segment,
            participants=[pet_data.get('name', 'Unknown')],
            outcome='story_progression',
            location=story_context.get('last_location', 'Cybertron')
        )
        await self.story_tracker.add_moment(user_id, moment)
        
        return story_segment
    
    def _calculate_effective_level_with_equipment(self, pet_data: Dict[str, Any]) -> int:
        """Calculate effective level factoring in equipment bonuses"""
        base_level = pet_data.get('level', 1)
        
        # Get equipment from pet data
        equipment = pet_data.get('equipment', {})
        total_attack_bonus = 0
        total_defense_bonus = 0
        
        # Calculate total stat bonuses from equipped items
        for slot, item in equipment.items():
            if item and isinstance(item, dict):
                stat_bonus = item.get('stat_bonus', {})
                total_attack_bonus += stat_bonus.get('attack', 0)
                total_defense_bonus += stat_bonus.get('defense', 0)
        
        # Calculate level bonus based on equipment stats
        # Every 50 combined attack/defense bonus = +1 effective level
        combined_bonus = total_attack_bonus + total_defense_bonus
        level_bonus = combined_bonus // 50
        
        # Cap the bonus to prevent excessive level inflation (max +10 levels)
        level_bonus = min(level_bonus, 10)
        
        return base_level + level_bonus
    
    async def get_user_pets(self, user_id: str, username: str = None):
        """Get user's pets in the format expected by the RPG system"""
        # Get pet data asynchronously without blocking
        pet_data = await user_data_manager.get_pet_data(user_id)
        
        if not pet_data:
            return []
        
        # Calculate effective level with equipment bonuses
        effective_level = self._calculate_effective_level_with_equipment(pet_data)
        
        # Create a simple pet object that matches the expected interface
        class SimplePet:
            def __init__(self, data, effective_level):
                self.name = data.get('name', 'Unknown')
                self.level = effective_level  # Use effective level instead of base level
                self.base_level = data.get('level', 1)  # Store base level for reference
                self.data = data  # Store full data for future use
        
        return [SimplePet(pet_data, effective_level)]
    
    async def gain_pet_experience(self, user_id: str, amount: int, source: str = "rpg_activity"):
        """Gain experience for pet - wrapper around add_experience from pet_levels"""
        from Systems.EnergonPets.pet_levels import add_experience
        
        # Call the existing add_experience function
        leveled_up, level_gains = await add_experience(user_id, amount, source)
        
        return {
            'leveled_up': leveled_up,
            'level_gains': level_gains,
            'xp_gained': amount
        }
    
    async def handle_battle_outcome(self, user_id: str, battle_view: UnifiedBattleView, victory: bool) -> str:
        """Handle battle outcome and generate AI description"""
        # Get battle participants
        survivors = []
        fallen = []
        
        for user, pet_data in battle_view.participants:
            if user.id == int(user_id):
                pet_name = pet_data.get('name', 'Unknown')
                # Check if pet survived (simplified check)
                if battle_view.player_data.get(str(user_id), {}).get('alive', True):
                    survivors.append(pet_name)
                else:
                    fallen.append(pet_name)
        
        # Generate AI battle outcome
        outcome_context = {
            'enemy_name': getattr(battle_view, 'enemy_name', 'Unknown Enemy'),
            'victory': victory,
            'survivors': survivors,
            'fallen': fallen,
            'location': 'Cybertron'
        }
        
        outcome_description = await self.ai_generator.generate_battle_outcome(outcome_context)
        
        # Record story moment
        moment = StoryMoment(
            timestamp=datetime.now(),
            event_type='battle',
            description=outcome_description,
            participants=survivors + fallen,
            outcome='victory' if victory else 'defeat',
            location='Cybertron'
        )
        await self.story_tracker.add_moment(user_id, moment)
        
        # Award rewards based on victory
        if victory:
            xp_reward = 75 if victory else 25
            loot_count = 2 if victory else 1
            
            # Award XP
            await add_experience(user_id, xp_reward)
            
            # Generate loot
            pet_data = await user_data_manager.get_pet_data(user_id)
            if pet_data:
                # Use effective level that factors in equipment bonuses
                effective_level = self._calculate_effective_level_with_equipment(pet_data)
                loot = await self.loot_system.get_loot_by_level(effective_level, loot_count)
                # Add loot to pet inventory (implementation depends on your inventory system)
                # This would need to be implemented based on your specific inventory management
        
        return outcome_description
    
    def get_event_cooldown(self, user_id: str) -> int:
        """Get remaining cooldown time for user"""
        if user_id in self.event_cooldowns:
            cooldown_end = self.event_cooldowns[user_id]
            remaining = (cooldown_end - datetime.now()).total_seconds()
            return max(0, int(remaining))
        return 0
    
    def set_event_cooldown(self, user_id: str, cooldown_seconds: int = 300):
        """Set event cooldown for user (default 5 minutes)"""
        self.event_cooldowns[user_id] = datetime.now() + timedelta(seconds=cooldown_seconds)

    async def get_monster_by_rarity(self, monster_type: str, rarity: str) -> Dict[str, Any]:
        """Get a random monster by type and rarity"""
        try:
            # Load monsters data from user_data_manager
            monsters_data = await user_data_manager.get_monsters_and_bosses_data()
            
            # Get the appropriate category
            if monster_type in ["monsters", "monster"]:
                category = monsters_data.get("monsters", {})
            elif monster_type in ["bosses", "boss"]:
                category = monsters_data.get("bosses", {})
            else:
                category = monsters_data.get("monsters", {})
            
            # Get monsters of the specified rarity
            rarity_monsters = category.get(rarity, [])
            
            if not rarity_monsters:
                # Fallback to common monsters if rarity not found
                rarity_monsters = category.get("common", [])
            
            if rarity_monsters:
                import random
                return random.choice(rarity_monsters)
            else:
                # Return a fallback monster
                return {
                    "name": f"Cyber {rarity.title()} {monster_type.title()}",
                    "level": 10,
                    "health": 100,
                    "attack": 15,
                    "defense": 10,
                    "rarity": rarity,
                    "type": monster_type
                }
        except Exception as e:
            logger.error(f"Error getting monster by rarity: {e}")
            # Return fallback monster
            return {
                "name": f"Cyber {rarity.title()} {monster_type.title()}",
                "level": 10,
                "health": 100,
                "attack": 15,
                "defense": 10,
                "rarity": rarity,
                "type": monster_type
            }

    async def get_titan_for_fight(self) -> Dict[str, Any]:
        """Get a titan enemy for battle"""
        try:
            # Load monsters data from user_data_manager
            monsters_data = await user_data_manager.get_monsters_and_bosses_data()
            
            # Try to get titans from bosses
            titans = monsters_data.get("bosses", {}).get("legendary", [])
            
            if titans:
                import random
                titan = random.choice(titans)
                # Ensure it's a proper titan
                titan["type"] = "titan"
                return titan
            else:
                # Return a fallback titan
                return {
                    "name": "Cyber Titan",
                    "level": 50,
                    "health": 500,
                    "attack": 75,
                    "defense": 50,
                    "rarity": "legendary",
                    "type": "titan",
                    "special_abilities": ["Massive Strike", "Energy Drain"]
                }
        except Exception as e:
            logger.error(f"Error getting titan for fight: {e}")
            # Return fallback titan
            return {
                "name": "Cyber Titan",
                "level": 50,
                "health": 500,
                "attack": 75,
                "defense": 50,
                "rarity": "legendary",
                "type": "titan",
                "special_abilities": ["Massive Strike", "Energy Drain"]
            }

# Global instance
_rpg_system_instance = None

def get_rpg_system(api_key: str = None) -> TransformersAIDnD:
    """Get or create the global RPG system instance"""
    global _rpg_system_instance
    if _rpg_system_instance is None:
        _rpg_system_instance = TransformersAIDnD(api_key)
    return _rpg_system_instance


class AIAdventureSetupView(discord.ui.View):
    """Setup view for AI adventures with party formation"""
    
    def __init__(self, rpg_commands, adventure_type: str):
        super().__init__(timeout=120)
        self.rpg_commands = rpg_commands
        self.adventure_type = adventure_type  # "random", "battle", "event", "story"
        self.players = []
        self.pets = []
        self.message = None
        self.setup_complete = False
    
    def get_embed(self):
        """Get the setup embed"""
        adventure_names = {
            "random": "🎲 Random AI Adventure",
            "battle": "⚔️ AI Battle Adventure", 
            "event": "🎯 AI Event Adventure",
            "story": "📖 AI Story Adventure"
        }
        
        embed = discord.Embed(
            title=adventure_names.get(self.adventure_type, "🤖 AI Adventure"),
            description="Form your party for an AI-generated adventure!",
            color=discord.Color.blue()
        )
        
        if self.players:
            party_text = ""
            for i, player in enumerate(self.players):
                if i < len(self.pets):
                    pet = self.pets[i]
                    party_text += f"👤 {player.display_name} ({pet.name} - Lv.{pet.level})\n"
                else:
                    party_text += f"👤 {player.display_name} (No pet selected)\n"
            embed.add_field(name="🤖 Party Members", value=party_text, inline=False)
        else:
            embed.add_field(name="🤖 Party Members", value="No players yet", inline=False)
        
        embed.add_field(name="📋 Instructions", value="Click 'Join' to join the party, then 'Start Adventure' when ready!", inline=False)
        
        return embed
    
    @discord.ui.button(label="Join Party", style=discord.ButtonStyle.green, emoji="➕")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle player joining the party"""
        if interaction.user in self.players:
            await interaction.response.send_message("❌ You're already in the party!", ephemeral=True)
            return
        
        # Get user's pets
        user_id = str(interaction.user.id)
        pets = await self.rpg_commands.rpg_system.get_user_pets(user_id, interaction.user.display_name)
        
        if not pets:
            await interaction.response.send_message("❌ You don't have any pets! Create one with the pet system first.", ephemeral=True)
            return
        
        # For simplicity, use the first pet
        selected_pet = pets[0]
        
        self.players.append(interaction.user)
        self.pets.append(selected_pet)
        
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @discord.ui.button(label="Leave Party", style=discord.ButtonStyle.red, emoji="➖")
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle player leaving the party"""
        if interaction.user not in self.players:
            await interaction.response.send_message("❌ You're not in the party!", ephemeral=True)
            return
        
        # Remove player and their pet
        index = self.players.index(interaction.user)
        self.players.pop(index)
        if index < len(self.pets):
            self.pets.pop(index)
        
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @discord.ui.button(label="Start Adventure", style=discord.ButtonStyle.blurple, emoji="🚀")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle starting the adventure"""
        if interaction.user not in self.players:
            await interaction.response.send_message("❌ You must join the party first!", ephemeral=True)
            return
        
        if len(self.players) == 0:
            await interaction.response.send_message("❌ No players in the party!", ephemeral=True)
            return
        
        self.setup_complete = True
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
        
        # Start the appropriate adventure type
        try:
            if self.adventure_type == "random":
                # Random choice between event, battle, or story
                import random
                choice = random.choice(["event", "battle", "story"])
                if choice == "event":
                    await self.rpg_commands.handle_ai_event(interaction.channel, self.players, self.pets)
                elif choice == "battle":
                    await self.rpg_commands.handle_ai_battle(interaction.channel, self.players, self.pets)
                else:
                    await self.rpg_commands.handle_ai_story(interaction.channel, self.players, self.pets)
            elif self.adventure_type == "battle":
                await self.rpg_commands.handle_ai_battle(interaction.channel, self.players, self.pets)
            elif self.adventure_type == "event":
                await self.rpg_commands.handle_ai_event(interaction.channel, self.players, self.pets)
            elif self.adventure_type == "story":
                await self.rpg_commands.handle_ai_story(interaction.channel, self.players, self.pets)
        except Exception as e:
            logger.error(f"Error starting AI adventure: {e}")
            error_embed = discord.Embed(
                title="❌ Adventure Error",
                description=f"Failed to start adventure: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.channel.send(embed=error_embed)
    
    async def on_timeout(self):
        """Handle timeout"""
        if not self.setup_complete and self.message:
            timeout_embed = discord.Embed(
                title="⏰ Setup Timeout",
                description="Party setup timed out. Create a new adventure to try again!",
                color=discord.Color.red()
            )
            await self.message.edit(embed=timeout_embed, view=None)


class CyberChroniclesSession:
    """Session management for CyberChronicles adventures"""
    
    def __init__(self, channel, rpg_system):
        self.channel = channel
        self.rpg_system = rpg_system
        self.step_participants = {}  # user_id -> pet_name
        self.current_step = 0
        self.story_history = []
        self.active = True
        
    def add_step_participant(self, user_id: str, pet_name: str):
        """Add a participant to the current step"""
        self.step_participants[user_id] = pet_name
        
    def reset_step_participants(self):
        """Reset participants for the next step"""
        # Keep current participants for continuity
        pass
        
    def generate_next_event_preview(self):
        """Generate a preview of the next event"""
        event_types = [
            {"type": "🎲 Random Event", "description": "An unexpected challenge awaits"},
            {"type": "⚔️ Battle Encounter", "description": "Enemies approach on the horizon"},
            {"type": "🔍 Exploration", "description": "New territories to discover"},
            {"type": "🤝 Social Encounter", "description": "Other Cybertronians need assistance"}
        ]
        import random
        return random.choice(event_types)


class CyberChroniclesView(discord.ui.View):
    """Interactive view for CyberChronicles adventures"""
    
    def __init__(self, session: CyberChroniclesSession, show_start_button: bool = False):
        super().__init__(timeout=300)
        self.session = session
        self.show_start_button = show_start_button
        
        if show_start_button:
            self.add_item(discord.ui.Button(
                label="Continue Adventure",
                style=discord.ButtonStyle.green,
                emoji="🚀",
                custom_id="continue_adventure"
            ))
            
        self.add_item(discord.ui.Button(
            label="Check Status",
            style=discord.ButtonStyle.blurple,
            emoji="📊",
            custom_id="check_status"
        ))
        
        self.add_item(discord.ui.Button(
            label="End Adventure",
            style=discord.ButtonStyle.red,
            emoji="🛑",
            custom_id="end_adventure"
        ))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user can interact with this view"""
        user_id = str(interaction.user.id)
        return user_id in self.session.step_participants
    
    async def on_timeout(self):
        """Handle timeout"""
        if hasattr(self, 'message') and self.message:
            timeout_embed = discord.Embed(
                title="⏰ Adventure Timeout",
                description="The adventure session has timed out.",
                color=discord.Color.red()
            )
            await self.message.edit(embed=timeout_embed, view=None)