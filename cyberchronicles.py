from Systems.RPG.rpg_system import get_rpg_system

async def add_energon_to_character(character_id: str, amount: int) -> bool:
    """Add energon to a character"""
    try:
        rpg_system = get_rpg_system()
        character = rpg_system.get_character(character_id)
        if character:
            character.energon_earned += amount
            await rpg_system.save_character_async(character_id)
            return True
        return False
    except Exception:
        return False

async def create_character_from_spark(user_id: str, spark_data: dict) -> bool:
    """Create a character from spark data"""
    try:
        rpg_system = get_rpg_system()
        # Basic character creation logic
        name = spark_data.get('name', f'Character_{user_id}')
        faction = spark_data.get('faction', 'autobot')
        class_type = spark_data.get('class', 'warrior')
        
        character = await rpg_system.create_character_async(user_id, name, faction, class_type)
        return character is not None
    except Exception:
        return False