import random
import logging
import json
import os
from typing import Dict, Any, Optional, Tuple
import asyncio
import discord

logger = logging.getLogger(__name__)

# Global variables for data loaded from JSON
AUTOBOT_PET_NAMES = []
DECEPTICON_PET_NAMES = []
STAGE_DEFINITIONS = {}
LEVEL_THRESHOLDS = {}
PET_STAGES = {}
MISSION_TYPES = {}
MISSION_DIFFICULTIES = {}
STAGE_EMOJIS = {}
TEAM_NAMES = []

def get_pet_name(faction: str) -> str:
    """Generate a random pet name based on faction."""
    if faction.lower() == "autobot":
        return random.choice(AUTOBOT_PET_NAMES) if AUTOBOT_PET_NAMES else "Optimus"
    elif faction.lower() == "decepticon":
        return random.choice(DECEPTICON_PET_NAMES) if DECEPTICON_PET_NAMES else "Megatron"
    else:
        all_names = AUTOBOT_PET_NAMES + DECEPTICON_PET_NAMES
        return random.choice(all_names) if all_names else "Spark"

def get_team_name() -> str:
    """Generate a random team name."""
    return random.choice(TEAM_NAMES) if TEAM_NAMES else "Team Spark"

def get_stage_for_level(level: int) -> int:
    """Get the stage number for a given level."""
    if level < 1:
        level = 1
    elif level > 500:
        level = 500
    
    for stage_num, stage_info in STAGE_DEFINITIONS.items():
        if stage_info["min_level"] <= level <= stage_info["max_level"]:
            return int(stage_num)
    
    return 50  # Default to final stage

def get_stage_emoji(level: int) -> str:
    """Get the emoji for a pet's current stage based on level."""
    stage = get_stage_for_level(level)
    return STAGE_DEFINITIONS.get(int(stage), {}).get("emoji", "🤖")

def get_stage_name(level: int) -> str:
    """Get the stage name for a pet's current level."""
    stage = get_stage_for_level(level)
    return STAGE_DEFINITIONS.get(int(stage), {}).get("name", f"Level {level}")

def get_level_experience(level: int) -> int:
    """Get the experience required to reach the next level."""
    if level < 1:
        level = 1
    elif level >= 500:
        return 0  # Max level reached
    
    return LEVEL_THRESHOLDS.get(level, 0)

def get_total_experience_for_level(target_level: int) -> int:
    """Get total experience required to reach a specific level from level 1."""
    if target_level <= 1:
        return 0
    
    total_exp = 0
    for level in range(1, target_level):
        total_exp += get_level_experience(level)
    
    return total_exp

def get_all_level_thresholds() -> Dict[int, int]:
    """Get the complete dictionary of level thresholds for external access."""
    return LEVEL_THRESHOLDS.copy()

def get_next_level_xp(current_level: int) -> int:
    """Get the XP needed for the next level with better error handling."""
    if current_level < 1:
        current_level = 1
    elif current_level >= 500:
        return 0
    
    return LEVEL_THRESHOLDS.get(current_level, 1000)  # Default fallback

async def add_experience(user_id: int, amount: int, source: str = "battle", equipment_stats: Optional[Dict[str, int]] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
    from Systems.user_data_manager import user_data_manager
    pet = await user_data_manager.get_pet_data(str(user_id))
    if not pet:
        return False, None
    if equipment_stats is None:
        equipment_stats = {'attack': 0, 'defense': 0, 'energy': 0, 'maintenance': 0, 'happiness': 0}   
    old_level = pet.get("level", 1)
    current_exp = pet.get("experience", pet.get("xp", 0))
    new_exp = current_exp + amount
    pet["experience"] = new_exp
    total_att_gain = 0
    total_def_gain = 0
    total_energy_gain = 0
    total_maintenance_gain = 0
    total_happiness_gain = 0    
    while pet["level"] < 500:
        exp_needed = get_level_experience(pet["level"])
        if exp_needed == 0 or new_exp < exp_needed:
            break
        new_exp -= exp_needed
        pet["level"] += 1
        pet["experience"] = new_exp
        faction = pet.get('faction', '').upper()        
        if pet["level"] <= 100:
            progress_factor = pet["level"] / 100
            target_resources = 900
            target_attack = 100
            target_defense = 100
            if faction == 'DECEPTICON':
                target_attack += 10  
                target_defense -= 10  
            elif faction == 'AUTOBOT':
                target_attack -= 10  
                target_defense += 10             
            base_energy = int(target_resources * 0.35 * progress_factor)
            base_maintenance = int(target_resources * 0.35 * progress_factor)
            base_happiness = int(target_resources * 0.30 * progress_factor)
            base_attack = int(target_attack * progress_factor)
            base_defense = int(target_defense * progress_factor)            
            energy_gain = max(1, base_energy - (pet.get('max_energy', 0) if pet["level"] > 1 else 0))
            maintenance_gain = max(1, base_maintenance - (pet.get('max_maintenance', 0) if pet["level"] > 1 else 0))
            happiness_gain = max(1, base_happiness - (pet.get('max_happiness', 0) if pet["level"] > 1 else 0))            
            att_gain = max(1, base_attack - pet.get('attack', 0) if pet["level"] > 1 else base_attack)
            def_gain = max(1, base_defense - pet.get('defense', 0) if pet["level"] > 1 else base_defense)           
            random_bonus = random.randint(1, 3)
            if random.randint(0, 1) == 0:
                att_gain += random_bonus
            else:
                def_gain += random_bonus               
        elif pet["level"] <= 200:
            progress_factor = (pet["level"] - 100) / 100
            target_resources = 7000
            target_attack = 400
            target_defense = 400
            if faction == 'DECEPTICON':
                target_attack += 40
                target_defense -= 40 
            elif faction == 'AUTOBOT':
                target_attack -= 40
                target_defense += 40           
            level_100_resources = 900
            level_100_attack = 110 if faction == 'DECEPTICON' else (90 if faction == 'AUTOBOT' else 100)
            level_100_defense = 90 if faction == 'DECEPTICON' else (110 if faction == 'AUTOBOT' else 100)            
            additional_energy = int((target_resources - level_100_resources) * 0.35 * progress_factor)
            additional_maintenance = int((target_resources - level_100_resources) * 0.35 * progress_factor)
            additional_happiness = int((target_resources - level_100_resources) * 0.30 * progress_factor)
            additional_attack = int((target_attack - level_100_attack) * progress_factor)
            additional_defense = int((target_defense - level_100_defense) * progress_factor)           
            energy_gain = max(1, additional_energy)
            maintenance_gain = max(1, additional_maintenance)
            happiness_gain = max(1, additional_happiness)
            att_gain = max(1, additional_attack)
            def_gain = max(1, additional_defense)            
            random_bonus = random.randint(2, 5)
            if random.randint(0, 1) == 0:
                att_gain += random_bonus
            else:
                def_gain += random_bonus               
        elif pet["level"] <= 300:
            progress_factor = (pet["level"] - 200) / 100
            target_resources = 25000
            target_attack = 1600
            target_defense = 1600
            if faction == 'DECEPTICON':
                target_attack += 150
                target_defense -= 150 
            elif faction == 'AUTOBOT':
                target_attack -= 150
                target_defense += 150         
            level_200_resources = 7000
            level_200_attack = 440 if faction == 'DECEPTICON' else (360 if faction == 'AUTOBOT' else 400)
            level_200_defense = 360 if faction == 'DECEPTICON' else (440 if faction == 'AUTOBOT' else 400)            
            additional_energy = int((target_resources - level_200_resources) * 0.35 * progress_factor)
            additional_maintenance = int((target_resources - level_200_resources) * 0.35 * progress_factor)
            additional_happiness = int((target_resources - level_200_resources) * 0.30 * progress_factor)
            additional_attack = int((target_attack - level_200_attack) * progress_factor)
            additional_defense = int((target_defense - level_200_defense) * progress_factor)           
            energy_gain = max(1, additional_energy)
            maintenance_gain = max(1, additional_maintenance)
            happiness_gain = max(1, additional_happiness)
            att_gain = max(1, additional_attack)
            def_gain = max(1, additional_defense)            
            random_bonus = random.randint(5, 10)
            if random.randint(0, 1) == 0:
                att_gain += random_bonus
            else:
                def_gain += random_bonus               
        elif pet["level"] <= 400:
            progress_factor = (pet["level"] - 300) / 100
            target_resources = 100000
            target_attack = 7500
            target_defense = 7500
            if faction == 'DECEPTICON':
                target_attack += 750  
                target_defense -= 750 
            elif faction == 'AUTOBOT':
                target_attack -= 750  
                target_defense += 750          
            level_300_resources = 25000
            level_300_attack = 1750 if faction == 'DECEPTICON' else (1450 if faction == 'AUTOBOT' else 1600)
            level_300_defense = 1450 if faction == 'DECEPTICON' else (1750 if faction == 'AUTOBOT' else 1600)           
            additional_energy = int((target_resources - level_300_resources) * 0.35 * progress_factor)
            additional_maintenance = int((target_resources - level_300_resources) * 0.35 * progress_factor)
            additional_happiness = int((target_resources - level_300_resources) * 0.30 * progress_factor)
            additional_attack = int((target_attack - level_300_attack) * progress_factor)
            additional_defense = int((target_defense - level_300_defense) * progress_factor)           
            energy_gain = max(1, additional_energy)
            maintenance_gain = max(1, additional_maintenance)
            happiness_gain = max(1, additional_happiness)
            att_gain = max(1, additional_attack)
            def_gain = max(1, additional_defense)           
            random_bonus = random.randint(10, 20)
            if random.randint(0, 1) == 0:
                att_gain += random_bonus
            else:
                def_gain += random_bonus                
        else:
            progress_factor = (pet["level"] - 400) / 100
            level_400_resources = 100000
            level_400_attack = 8250 if faction == 'DECEPTICON' else (6750 if faction == 'AUTOBOT' else 7500)
            level_400_defense = 6750 if faction == 'DECEPTICON' else (8250 if faction == 'AUTOBOT' else 7500)
            target_resources = level_400_resources * 2 
            target_attack = level_400_attack * 2
            target_defense = level_400_defense * 2           
            additional_energy = int((target_resources - level_400_resources) * 0.35 * progress_factor)
            additional_maintenance = int((target_resources - level_400_resources) * 0.35 * progress_factor)
            additional_happiness = int((target_resources - level_400_resources) * 0.30 * progress_factor)
            additional_attack = int((target_attack - level_400_attack) * progress_factor)
            additional_defense = int((target_defense - level_400_defense) * progress_factor)            
            energy_gain = max(1, additional_energy)
            maintenance_gain = max(1, additional_maintenance)
            happiness_gain = max(1, additional_happiness)
            att_gain = max(1, additional_attack)
            def_gain = max(1, additional_defense)           
            random_bonus = random.randint(15, 30)
            if random.randint(0, 1) == 0:
                att_gain += random_bonus
            else:
                def_gain += random_bonus
        total_att_gain += att_gain
        total_def_gain += def_gain
        total_energy_gain += energy_gain
        total_maintenance_gain += maintenance_gain
        total_happiness_gain += happiness_gain
        pet["attack"] += att_gain
        pet["defense"] += def_gain
        pet['max_energy'] += energy_gain
        pet['max_maintenance'] += maintenance_gain
        pet['max_happiness'] += happiness_gain
        total_max_energy = pet['max_energy'] + equipment_stats.get('energy', 0)
        total_max_maintenance = pet['max_maintenance'] + equipment_stats.get('maintenance', 0)
        total_max_happiness = pet['max_happiness'] + equipment_stats.get('happiness', 0)
        pet['energy'] = min(pet.get('energy', 0) + energy_gain, total_max_energy)
        pet['maintenance'] = min(pet.get('maintenance', 0) + maintenance_gain, total_max_maintenance)
        pet['happiness'] = min(pet.get('happiness', 0) + happiness_gain, total_max_happiness)
        xp_key = f"{source}_xp_earned"
        pet[xp_key] = pet.get(xp_key, 0) + amount      
        await user_data_manager.save_pet_data(str(user_id), f"User_{user_id}", pet)       
        level_gains = {
            "old_level": old_level,
            "new_level": pet["level"],
            "att_gain": total_att_gain,
            "def_gain": total_def_gain,
            "energy_gain": total_energy_gain,
            "maintenance_gain": total_maintenance_gain,
            "happiness_gain": total_happiness_gain,
            "source": source
        }      
        return True, level_gains
    xp_key = f"{source}_xp_earned"
    pet[xp_key] = pet.get(xp_key, 0) + amount    
    await user_data_manager.save_pet_data(str(user_id), f"User_{user_id}", pet)
    return False, None

async def load_data_from_json():
    """Load stage definitions and pet names from pets_level.json, and experience thresholds from pet_xp.json through user_data_manager."""
    global AUTOBOT_PET_NAMES, DECEPTICON_PET_NAMES, STAGE_DEFINITIONS, LEVEL_THRESHOLDS, PET_STAGES, MISSION_TYPES, MISSION_DIFFICULTIES, STAGE_EMOJIS, TEAM_NAMES
    
    # Import user_data_manager to load data through it
    from Systems.user_data_manager import user_data_manager
    
    # Load pets_level.json data through user_data_manager
    pets_data = await user_data_manager.get_pets_level_data()
    if not pets_data:
        logger.error("Failed to load pets_level.json data from user_data_manager")
        return
        
    # Load pet names
    AUTOBOT_PET_NAMES = pets_data.get('AUTOBOT_PET_NAMES', [])
    DECEPTICON_PET_NAMES = pets_data.get('DECEPTICON_PET_NAMES', [])
    TEAM_NAMES = pets_data.get('TEAM_NAMES', [])
    
    # Load stage definitions and convert string keys to integers
    stage_data = pets_data.get('STAGE_DEFINITIONS', {})
    STAGE_DEFINITIONS = {int(k): v for k, v in stage_data.items()}
    
    # Load other pet system data
    PET_STAGES = pets_data.get('PET_STAGES', {})
    
    # Load mission data from pets_mission.json
    mission_data = await user_data_manager.get_pets_mission_data()
    if mission_data:
        MISSION_TYPES = mission_data.get('MISSION_TYPES', {})
        MISSION_DIFFICULTIES = mission_data.get('MISSION_DIFFICULTIES', {})
        logger.info(f"Loaded {len(MISSION_TYPES)} mission types and {len(MISSION_DIFFICULTIES)} difficulties from pets_mission.json")
    else:
        MISSION_TYPES = {}
        MISSION_DIFFICULTIES = {}
        logger.warning("Failed to load mission data from pets_mission.json")
    
    # Populate stage emojis mapping
    STAGE_EMOJIS = {
        stage_info["min_level"]: stage_info["emoji"] 
        for stage_info in STAGE_DEFINITIONS.values()
    }
    
    logger.info("Successfully loaded data from pets_level.json via user_data_manager")
    logger.info(f"Loaded {len(AUTOBOT_PET_NAMES)} Autobot names")
    logger.info(f"Loaded {len(DECEPTICON_PET_NAMES)} Decepticon names")
    logger.info(f"Loaded {len(TEAM_NAMES)} team names")
    logger.info(f"Loaded {len(STAGE_DEFINITIONS)} stage definitions")
    
    # Load experience thresholds from pet_xp.json through user_data_manager
    xp_data = await user_data_manager.get_pet_xp_data()
    if not xp_data:
        logger.error("Failed to load pet_xp.json data from user_data_manager")
        return
        
    # Load level thresholds and convert string keys to integers
    threshold_data = xp_data.get('LEVEL_THRESHOLDS', {})
    LEVEL_THRESHOLDS = {int(k): v for k, v in threshold_data.items()}
    
    logger.info("Successfully loaded experience data from pet_xp.json via user_data_manager")
    logger.info(f"Loaded {len(LEVEL_THRESHOLDS)} level thresholds")

async def create_level_up_embed(pet: Dict[str, Any], level_gains: Dict[str, Any], user_id: int = None) -> discord.Embed:
    """Create a level up embed for a pet"""
    old_level = level_gains["old_level"]
    new_level = level_gains["new_level"]
    
    old_stage = get_stage_for_level(old_level)
    new_stage = get_stage_for_level(new_level)
    
    old_emoji = STAGE_DEFINITIONS.get(old_stage, {}).get("emoji", "🤖")
    new_emoji = STAGE_DEFINITIONS.get(new_stage, {}).get("emoji", "🤖")
    
    embed = discord.Embed(
        title="🎉 Level Up!",
        description=f"**{pet['name']}** has leveled up!",
        color=0x00ff00
    )
    
    embed.add_field(
        name="📈 Level Progress",
        value=f"{old_emoji} Level {old_level} → {new_emoji} Level {new_level}",
        inline=False
    )
    
    # Stage change notification
    if old_stage != new_stage:
        old_stage_name = STAGE_DEFINITIONS.get(old_stage, {}).get("name", f"Stage {old_stage}")
        new_stage_name = STAGE_DEFINITIONS.get(new_stage, {}).get("name", f"Stage {new_stage}")
        embed.add_field(
            name="🌟 Stage Evolution",
            value=f"**{old_stage_name}** → **{new_stage_name}**",
            inline=False
        )
    
    # Stat improvements
    stat_improvements = []
    if level_gains.get("att_gain", 0) > 0:
        stat_improvements.append(f"⚔️ +{level_gains['att_gain']} Attack")
    if level_gains.get("def_gain", 0) > 0:
        stat_improvements.append(f"🛡️ +{level_gains['def_gain']} Defense")
    if level_gains.get("energy_gain", 0) > 0:
        stat_improvements.append(f"⚡ +{level_gains['energy_gain']} Energy")
    if level_gains.get("maintenance_gain", 0) > 0:
        stat_improvements.append(f"🔧 +{level_gains['maintenance_gain']} Maintenance")
    if level_gains.get("happiness_gain", 0) > 0:
        stat_improvements.append(f"😊 +{level_gains['happiness_gain']} Happiness")
    
    if stat_improvements:
        embed.add_field(
            name="📊 Stat Improvements",
            value="\n".join(stat_improvements),
            inline=False
        )
    
    # Current stats
    total_hp = pet.get('max_energy', 0) + pet.get('max_maintenance', 0) + pet.get('max_happiness', 0)
    embed.add_field(
        name="💪 Current Stats",
        value=f"❤️ {total_hp:,} HP | ⚔️ {pet.get('attack', 0)} ATK | 🛡️ {pet.get('defense', 0)} DEF",
        inline=False
    )
    
    # Source information
    source = level_gains.get("source", "unknown")
    source_emojis = {
        "battle": "⚔️",
        "train": "🏋️",
        "mission": "🎯",
        "charge": "🔋",
        "play": "🎮",
        "repair": "🔧"
    }
    source_emoji = source_emojis.get(source, "✨")
    embed.add_field(
        name="📝 Source",
        value=f"{source_emoji} Leveled up from {source}",
        inline=True
    )
    
    return embed

async def send_level_up_embed(user_id: int, level_gains: Dict[str, Any], channel=None) -> None:
    """Send a level up embed to the user"""
    from Systems.user_data_manager import user_data_manager
    
    pet = await user_data_manager.get_pet_data(str(user_id))
    if not pet:
        return
        
    embed = await create_level_up_embed(pet, level_gains, user_id)
    
    try:
        # Try to get the user's DM channel or use provided channel
        if channel:
            await channel.send(embed=embed)
        else:
            # Try to send via DM (would need bot instance)
            pass
    except discord.Forbidden:
        # User has DMs disabled, try to send in a guild channel if possible
        pass
    except Exception as e:
        logger.error(f"Error sending level up embed: {e}")

def calculate_xp_gain(level: int, difficulty: str = "normal", source: str = "battle") -> int:
    """
    Calculate XP gain based on pet level and difficulty.
    
    Args:
        level: Current pet level
        difficulty: Difficulty level (easy, normal, hard, extreme)
        source: Source of XP (battle, mission, train, etc.)
    
    Returns:
        XP amount to award
    """
    base_xp = 50
    
    # Level scaling - higher levels need more XP
    if level <= 50:
        base_xp = 25
    elif level <= 100:
        base_xp = 35
    elif level <= 200:
        base_xp = 50
    elif level <= 300:
        base_xp = 75
    elif level <= 400:
        base_xp = 100
    else:
        base_xp = 150
    
    # Difficulty multiplier
    difficulty_multipliers = {
        "easy": 0.7,
        "normal": 1.0,
        "hard": 1.5,
        "extreme": 2.0,
        "boss": 3.0,
        "titan": 5.0
    }
    
    multiplier = difficulty_multipliers.get(difficulty.lower(), 1.0)
    
    # Source bonus
    source_bonuses = {
        "battle": 1.0,
        "mission": 1.2,
        "train": 0.8,
        "quest": 1.5,
        "pvp": 1.3
    }
    
    source_multiplier = source_bonuses.get(source.lower(), 1.0)
    
    # Random variation (±20%)
    variation = random.uniform(0.8, 1.2)
    
    final_xp = int(base_xp * multiplier * source_multiplier * variation)
    return max(1, final_xp)

async def load_level_data():
    """Initialize the pet leveling system by loading data from JSON files."""
    await load_data_from_json()
    logger.info("Pet leveling system initialized successfully!")
