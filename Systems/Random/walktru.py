
import discord
import logging
import random
import asyncio

logger = logging.getLogger(__name__)

class StoryMapManager:
    """Independent story map manager that loads directly from Walk Tru JSON files"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__ + '.StoryMapManager')
        self.story_maps = {}  # Store loaded story maps
        self._story_configs = {
            'horror': {
                'filename': 'Horror.json',
                'title': '👻 THE HAUNTED SANITARIUM 👻',
                'description': 'Escape from a decrepit sanitarium filled with malevolent spirits and dark secrets.',
                'start_stage': 'event_start',
                'mechanic': 'fear',
                'emoji': '👻',
                'starting_value': 0
            },
            'ganster': {
                'filename': 'Ganster.json',
                'title': '🔫 THE GANGSTER\'S RISE 🔫',
                'description': 'Build your criminal empire in the dangerous underworld of organized crime.',
                'start_stage': 'event_start',
                'mechanic': 'heat',
                'emoji': '🚨',
                'starting_value': 0
            },
            'knight': {
                'filename': 'Knight.json',
                'title': '🗡️ THE KNIGHT\'S QUEST 🗡️',
                'description': 'Embark on a medieval adventure as Sir Gareth, facing moral dilemmas and epic quests.',
                'start_stage': 'event_start',
                'mechanic': 'honor',
                'emoji': '👑',
                'starting_value': 100
            },
            'robot': {
                'filename': 'Robot.json',
                'title': '🤖 THE ROBOT UPRISING 🤖',
                'description': 'Navigate a dystopian future where artificial intelligence has taken control.',
                'start_stage': 'event_start',
                'mechanic': 'power',
                'emoji': '⚡',
                'starting_value': 0
            },
            'western': {
                'filename': 'Western.json',
                'title': '🤠 THE WESTERN FRONTIER 🤠',
                'description': 'Ride into the Wild West and forge your legend in dusty towns and dangerous territories.',
                'start_stage': 'event_start',
                'mechanic': 'health',
                'emoji': '⚕️',
                'starting_value': 100
            },
            'wizard': {
                'filename': 'Wizard.json',
                'title': '🧙‍♂️ THE WIZARD\'S APPRENTICE 🧙‍♂️',
                'description': 'Begin your magical journey as a young wizard\'s apprentice investigating mysterious magic.',
                'start_stage': 'event_start',
                'mechanic': 'mana',
                'emoji': '🔮',
                'starting_value': 100
            }
        }
        self._cache = {}  # Simple in-memory cache for performance
    
    async def load_story_maps(self):
        """Load all story maps using centralized data manager"""
        self.story_maps = {}  # Reset story maps
        
        # Define story map configurations (metadata for each adventure type)
        story_configs = {
            'horror': {
                'title': '👻 Horror Sanitarium',
                'description': 'Survive the supernatural horrors of an abandoned sanitarium while managing your fear. Navigate through 20 terrifying events, uncover dark secrets, and confront Dr. Crowley\'s evil experiments. Your fear level determines your fate as you battle both external horrors and internal terror.',
                'mechanic': 'fear',
                'mechanic_emoji': '😱',
                'mechanic_name': 'Fear',
                'min_value': 0,
                'max_value': 100,
                'starting_value': 0,
                'progress_emoji': '👻',
                'warning_thresholds': {
                    'caution': 25,
                    'warning': 50,
                    'danger': 75,
                    'critical': 90
                },
                'max_fear': 100,
                'starting_fear': 0,
                'fear_mechanics': {
                    'max_fear': 100,
                    'starting_fear': 0
                }
            },
            'ganster': {
                'title': '🕴️ 1920s Chicago Gangster',
                'description': 'Navigate the criminal underworld of 1920s Chicago. Build your reputation, avoid the heat from authorities, and rise through the ranks of organized crime. Every choice affects your Heat level with law enforcement.',
                'mechanic': 'heat',
                'mechanic_emoji': '🌡️',
                'mechanic_name': 'Heat',
                'min_value': 0,
                'max_value': 100,
                'starting_value': 0,
                'progress_emoji': '🔥',
                'warning_thresholds': {
                    'caution': 25,
                    'warning': 50,
                    'danger': 75,
                    'critical': 90
                },
                'max_heat': 100,
                'natural_decay': 2,
                'decay_frequency': 3,
                'heat_mechanics': {
                    'max_heat': 100,
                    'natural_decay': 2,
                    'decay_frequency': 3
                }
            },
            'knight': {
                'title': '⚔️ Knight\'s Quest',
                'description': 'Embark on a noble quest as Sir Gareth, testing your honor and chivalry at every turn. Start with 100 honor and navigate moral dilemmas to determine your legacy.',
                'mechanic': 'honor',
                'mechanic_emoji': '⚔️',
                'mechanic_name': 'Honor',
                'min_value': 0,
                'max_value': 150,
                'starting_value': 100,
                'progress_emoji': '🛡️',
                'warning_thresholds': {
                    'critical': 10,
                    'danger': 25,
                    'warning': 50,
                    'caution': 75
                },
                'starting_honor': 100,
                'max_honor': 150,
                'min_honor': 0,
                'natural_decay': 0,
                'decay_frequency': 0,
                'honor_gain_bonus_threshold': 120,
                'honor_gain_bonus_message': 'Your exceptional honor inspires others and makes future noble choices easier.',
                'honor_mechanics': {
                    'starting_honor': 100,
                    'max_honor': 150,
                    'min_honor': 0,
                    'natural_decay': 0,
                    'decay_frequency': 0,
                    'honor_gain_bonus_threshold': 120,
                    'honor_gain_bonus_message': 'Your exceptional honor inspires others and makes future noble choices easier.'
                }
            },
            'robot': {
                'title': '🤖 Robot Factory Escape',
                'description': 'Escape from a robot factory by managing your power levels. Start at 0% power and reach 100% by stage 10 to build your robot body, then maintain power above 0% to survive until escape.',
                'mechanic': 'power',
                'mechanic_emoji': '⚡',
                'mechanic_name': 'Power',
                'min_value': 0,
                'max_value': 100,
                'starting_value': 0,
                'progress_emoji': '🔋',
                'warning_thresholds': {
                    'critical': 10,
                    'danger': 25,
                    'warning': 50,
                    'caution': 75
                },
                'power_threshold_stage_10': 100,
                'power_failure_threshold': 0,
                'power_conservation_bonus': 'Successful power conservation choices provide small bonuses',
                'power_mechanics': {
                    'power_threshold_stage_10': 100,
                    'power_failure_threshold': 0,
                    'power_conservation_bonus': 'Successful power conservation choices provide small bonuses'
                }
            },
            'western': {
                'title': '🤠 Western Adventure',
                'description': 'Live the life of a legendary gunslinger through the American frontier. Manage your health as you face duels, poker games, train robberies, and the dangers of the Wild West. Every choice affects your survival in this unforgiving land.',
                'mechanic': 'health',
                'mechanic_emoji': '❤️',
                'mechanic_name': 'Health',
                'min_value': 0,
                'max_value': 100,
                'starting_value': 100,
                'progress_emoji': '❤️',
                'warning_thresholds': {
                    'critical': 10,
                    'danger': 25,
                    'warning': 50,
                    'caution': 75
                },
                'starting_health': 100,
                'max_health': 100,
                'min_health': 0,
                'natural_recovery': 2,
                'recovery_frequency': 3,
                'health_mechanics': {
                    'starting_health': 100,
                    'max_health': 100,
                    'min_health': 0,
                    'natural_recovery': 2,
                    'recovery_frequency': 3
                }
            },
            'wizard': {
                'title': '🧙‍♂️ Wizard\'s Magical Journey',
                'description': 'Embark on an epic magical adventure as a young wizard\'s apprentice. Master spells, manage your mana wisely, and face legendary challenges. Your magical journey spans 20+ events with complex spellcasting decisions.',
                'mechanic': 'mana',
                'mechanic_emoji': '🪄',
                'mechanic_name': 'Mana',
                'min_value': 0,
                'max_value': 150,
                'starting_value': 100,
                'progress_emoji': '✨',
                'warning_thresholds': {
                    'critical': 10,
                    'danger': 25,
                    'warning': 50,
                    'caution': 75
                },
                'max_mana': 150,
                'min_mana': 0,
                'starting_mana': 100,
                'natural_recovery': 2,
                'recovery_frequency': 'every_3_stages',
                'mana_warning_threshold': 20,
                'critical_mana_threshold': 10,
                'auto_defeat_threshold': 0,
                'mana_mechanics': {
                    'starting_mana': 100,
                    'max_mana': 150,
                    'min_mana': 0,
                    'natural_recovery': 2,
                    'recovery_frequency': 'every_3_stages',
                    'mana_warning_threshold': 20,
                    'critical_mana_threshold': 10,
                    'auto_defeat_threshold': 0
                }
            }
        }
        
        # Load each story using centralized data manager
        for adventure_type, config in story_configs.items():
            try:
                # Use centralized data manager to load story data
                data_key = f'walktru_{adventure_type}'
                story_data = await self.bot.user_data_manager.get_json_data(data_key)
                
                if story_data:
                    # Add metadata to the story data
                    story_data.update({
                        'adventure_type': adventure_type,
                        'emoji': config['mechanic_emoji'],
                        'starting_value': config['starting_value'],
                        'max_value': config['max_value'],
                        'start_stage': 'event_start',
                        'title': f"{config['title']}",
                        'mechanic': config['mechanic'],
                        'mechanics': config
                    })
                    
                    self.story_maps[adventure_type] = story_data
                else:
                    logger.warning(f"Story data not found for {adventure_type}")
                    
            except Exception as e:
                logger.error(f"Error loading story map {adventure_type}: {e}")
        
        # Cache the loaded maps
        self._cache['story_maps'] = self.story_maps
        
        logger.info(f"Loaded {len(self.story_maps)} story maps")
        return self.story_maps
    
    async def _load_story_data(self, story_key):
        """Helper method to load story data using centralized user_data_manager"""
        try:
            if story_key not in self._story_configs:
                self.logger.error(f"Unknown story key: {story_key}")
                return None
                
            # Use centralized data manager to load story data
            data_key = f'walktru_{story_key}'
            story_data = await self.bot.user_data_manager.load_json_data(data_key)
            
            if not story_data:
                self.logger.error(f"Story data empty for {story_key}")
                return None
                
            return story_data
            
        except Exception as e:
            self.logger.error(f"Error loading story data for {story_key}: {e}")
            return None
    
    async def load_story_maps_lazy(self):
        """Lazy loading wrapper with error handling"""
        try:
            self.story_maps = await self.load_story_maps()
            return self.story_maps
        except Exception as e:
            logger.error(f"Error in lazy loading: {e}")
            self.story_maps = {}
            return {}
    
    async def get_user_adventure_state(self, user_id, story_key):
        """Get user's current adventure state from cache"""
        try:
            cache_key = f"user_adventure_{user_id}_{story_key}"
            return self._cache.get(cache_key)
        except Exception as e:
            logger.error(f"Error getting user adventure state from cache: {e}")
            return None
    
    async def save_user_adventure_state(self, user_id, story_key, state_data):
        """Save user's adventure state to cache"""
        try:
            cache_key = f"user_adventure_{user_id}_{story_key}"
            self._cache[cache_key] = state_data
            logger.info(f"Cached adventure state for user {user_id}, story {story_key}")
        except Exception as e:
            logger.error(f"Error caching user adventure state: {e}")
    
    async def clear_user_adventure_state(self, user_id, story_key):
        """Clear user's adventure state from cache"""
        try:
            cache_key = f"user_adventure_{user_id}_{story_key}"
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.info(f"Cleared adventure state for user {user_id}, story {story_key}")
        except Exception as e:
            logger.error(f"Error clearing user adventure state from cache: {e}")
    
    def clear_cache(self):
        """Clear the in-memory cache"""
        self._cache.clear()
        logger.info("Story map cache cleared")

# Global instance will be set when bot is ready
story_map_manager = None

# STORY_MAPS is now loaded on-demand when /walktru is executed

def create_progress_bar(current, maximum, filled_emoji, empty_emoji, length=10):
    """Create a visual progress bar with emojis"""
    if maximum == 0:
        percentage = 0
    else:
        percentage = min(100, max(0, (current / maximum) * 100))
    
    filled = int((percentage / 100) * length)
    empty = length - filled
    
    bar = filled_emoji * filled + empty_emoji * empty
    return f"{bar} {current}/{maximum} ({percentage:.0f}%)"

def get_mechanic_display(adventure_type, current_value, story_data):
    """Get the display for the current mechanic with warning messages"""
    config = story_data
    mechanics = config.get('mechanics', {})
    
    # Get progress bar emojis from mechanics
    progress_config = mechanics.get('progress_bar', {})
    filled_emoji = progress_config.get('filled_emoji', '⬜')
    empty_emoji = progress_config.get('empty_emoji', '⬛')
    
    # Get max and min values
    max_val = mechanics.get(f'max_{adventure_type}', 100)
    min_val = mechanics.get(f'min_{adventure_type}', 0)
    
    # Calculate percentage for progress bar
    if max_val == min_val:
        percentage = 0
    else:
        percentage = max(0, min(100, ((current_value - min_val) / (max_val - min_val)) * 100))
    
    # Create progress bar
    bar = create_progress_bar(current_value, max_val, filled_emoji, empty_emoji)
    
    # Get warning based on adventure type
    warning = None
    warning_thresholds = mechanics.get('warning_thresholds', {})
    
    # Map adventure type to the correct threshold key
    threshold_keys = {
        'horror': 'fear',
        'ganster': 'heat',
        'knight': 'honor',
        'robot': 'power',
        'western': 'health',
        'wizard': 'mana'
    }
    
    threshold_key = threshold_keys.get(adventure_type, adventure_type)
    specific_thresholds = warning_thresholds.get(threshold_key, {})
    
    if adventure_type == 'horror':
        warning = get_fear_warning(current_value, specific_thresholds)
    elif adventure_type == 'ganster':
        warning = get_heat_warning(current_value, specific_thresholds)
    elif adventure_type == 'knight':
        warning = get_honor_warning(current_value, specific_thresholds)
    elif adventure_type == 'robot':
        warning = get_power_warning(current_value, specific_thresholds)
    elif adventure_type == 'western':
        warning = get_health_warning(current_value, specific_thresholds)
    elif adventure_type == 'wizard':
        warning = get_mana_warning(current_value, max_val, specific_thresholds)
    
    return f"{bar}\n{warning}" if warning else bar

# Warning Functions for Each Adventure Type
def get_fear_warning(fear, thresholds=None):
    if not thresholds:
        thresholds = {'critical': 90, 'danger': 75, 'warning': 50, 'caution': 25}
    
    if fear >= thresholds.get('critical', 90):
        return "⚠️ You're on the verge of complete terror! One more scare could end everything!"
    elif fear >= thresholds.get('danger', 75):
        return "🚨 Your sanity is slipping away! Be very careful with your next choices!"
    elif fear >= thresholds.get('warning', 50):
        return "😰 Fear is taking hold. Choose wisely to avoid panic!"
    elif fear >= thresholds.get('caution', 25):
        return "😟 You're starting to feel uneasy. Stay alert!"
    return None

def get_heat_warning(heat, thresholds=None):
    if not thresholds:
        thresholds = {'critical': 90, 'danger': 75, 'warning': 50, 'caution': 25}
    
    if heat >= thresholds.get('critical', 90):
        return "🚨 The cops are closing in! One wrong move and you're going to jail!"
    elif heat >= thresholds.get('danger', 75):
        return "🔥 You're burning hot with the authorities! Lay low!"
    elif heat >= thresholds.get('warning', 50):
        return "⚠️ Police attention is increasing. Be more careful!"
    elif heat >= thresholds.get('caution', 25):
        return "👮 You're starting to attract unwanted attention."
    return None

def get_honor_warning(honor, thresholds=None):
    if not thresholds:
        thresholds = {'critical': 10, 'danger': 25, 'warning': 50, 'caution': 75}
    
    if honor <= thresholds.get('critical', 10):
        return "⚔️ Your honor is nearly lost! You're barely worthy of knighthood!"
    elif honor <= thresholds.get('danger', 25):
        return "🛡️ Your honor is severely tarnished! Act with virtue!"
    elif honor <= thresholds.get('warning', 50):
        return "⚠️ Your honor is questionable. Make noble choices!"
    elif honor <= thresholds.get('caution', 75):
        return "🏰 Your honor could be stronger. Stay true to knightly virtues!"
    return None

def get_power_warning(power, thresholds=None):
    if not thresholds:
        thresholds = {'critical': 10, 'danger': 25, 'warning': 50, 'caution': 75}
    
    if power <= thresholds.get('critical', 10):
        return "🔋 Power critically low! Shutdown imminent!"
    elif power <= thresholds.get('danger', 25):
        return "⚡ Low power reserves! Seek energy sources immediately!"
    elif power <= thresholds.get('warning', 50):
        return "🔌 Power levels dropping. Find energy soon!"
    elif power <= thresholds.get('caution', 75):
        return "🪫 Power could be higher for optimal performance."
    return None

def get_health_warning(current_health, thresholds=None):
    """Get health warning message for Western adventure"""
    if not thresholds:
        thresholds = {'critical': 10, 'danger': 25, 'warning': 50, 'caution': 75}
    
    if current_health <= thresholds.get('critical', 10):
        return "💀 **CRITICAL**: You're barely alive! One more hit could be fatal!"
    elif current_health <= thresholds.get('danger', 25):
        return "🩸 **DANGER**: You're badly wounded! Seek medical attention!"
    elif current_health <= thresholds.get('warning', 50):
        return "🤕 **WARNING**: You're injured and need to be careful!"
    elif current_health <= thresholds.get('caution', 75):
        return "🩹 **CAUTION**: You've taken some damage. Watch your health!"
    return None

def get_mana_warning(current_mana, max_mana, thresholds=None):
    """Get mana warning message for Wizard adventure"""
    if not thresholds:
        thresholds = {'critical': 10, 'danger': 25, 'warning': 50, 'caution': 75}
    
    percentage = (current_mana / max_mana) * 100
    
    if percentage <= thresholds.get('critical', 10):
        return "🌑 **CRITICAL**: Mana nearly depleted! You can barely cast spells!"
    elif percentage <= thresholds.get('danger', 25):
        return "🌘 **DANGER**: Very low mana! Conserve your magical energy!"
    elif percentage <= thresholds.get('warning', 50):
        return "🌗 **WARNING**: Mana running low. Use magic wisely!"
    elif percentage <= thresholds.get('caution', 75):
        return "🌖 **CAUTION**: Mana could be higher for powerful spells."
    return None

def get_stat_bounds(adventure_type):
    """Get the minimum and maximum bounds for each adventure type's mechanic"""
    bounds = {
        'horror': {'min': 0, 'max': 100},      # Fear: 0-100%
        'ganster': {'min': 0, 'max': 100},     # Heat: 0-100%
        'knight': {'min': -50, 'max': 100},    # Honor: -50 to 100 (can go negative)
        'robot': {'min': 0, 'max': 100},       # Power: 0-100%
        'western': {'min': 0, 'max': 100},     # Health: 0-100%
        'wizard': {'min': 0, 'max': 150}       # Mana: 0-150% (higher max for wizard)
    }
    return bounds.get(adventure_type, {'min': 0, 'max': 100})

def clamp_stat_value(value, adventure_type):
    """Clamp a stat value to stay within realistic bounds"""
    bounds = get_stat_bounds(adventure_type)
    return max(bounds['min'], min(bounds['max'], value))

class WalktruView(discord.ui.View):
    def __init__(self, story_maps, user_id):
        super().__init__(timeout=600)  # 10 minute timeout
        self.story_maps = story_maps
        self.user_id = user_id

    @discord.ui.select(
        placeholder="Choose your adventure...",
        options=[
            discord.SelectOption(label="👻 Haunted Sanitarium", value="horror", description="Escape from supernatural horrors"),
            discord.SelectOption(label="🔫 Gangster's Rise", value="ganster", description="Build your criminal empire"),
            discord.SelectOption(label="🗡️ Knight's Quest", value="knight", description="Medieval adventure with honor"),
            discord.SelectOption(label="🤖 Robot Uprising", value="robot", description="Dystopian AI-controlled future"),
            discord.SelectOption(label="🤠 Western Frontier", value="western", description="Wild West adventures"),
            discord.SelectOption(label="🧙‍♂️ Wizard's Apprentice", value="wizard", description="Magical journey of discovery")
        ]
    )
    async def select_adventure(self, interaction: discord.Interaction, select: discord.ui.Select):
        adventure_type = select.values[0]
        adventure = self.story_maps[adventure_type]
        stage_key = adventure['start_stage']
        
        # Initialize walktru state using StoryMapManager
        story_map_manager = interaction.client.story_map_manager
        await story_map_manager.save_user_adventure_state(self.user_id, adventure_type, {
            'adventure_type': adventure_type,
            'current_stage': stage_key,
            'mechanic_value': adventure['starting_value'],
            'choices_made': [],
            'stage_count': 0
        })
        
        # Get the first stage
        stage = adventure['story_map'][stage_key]
        
        # Create choice screen embed (situation + choices + mechanic bar + buttons)
        embed = discord.Embed(
            title=adventure['title'],
            description=stage['text'],
            color=discord.Color.blue()
        )
        
        # Add mechanic progress bar
        mechanic_display = get_mechanic_display(adventure_type, adventure['starting_value'], adventure)
        embed.add_field(
            name=f"{adventure['emoji']} {adventure['mechanic'].title()}",
            value=mechanic_display,
            inline=False
        )

        choices = list(stage['choices'].items())
        choice_text = "\n\n".join([f"**{choice_key}**" for choice_key, _ in choices[:3]])
        embed.add_field(
            name="📋 Your Choices",
            value=choice_text,
            inline=False
        )
        
        # Create choice view
        view = WalktruChoiceView(self.story_maps, adventure_type, stage_key, self.user_id)
        
        await interaction.response.edit_message(embed=embed, view=view)

    async def on_timeout(self):
        """Called when the view times out after 10 minutes"""
        try:
            # Clear cached adventure state for this user when timeout occurs
            # The actual cleanup will happen when user starts a new adventure
            pass
        except:
            pass  # Ignore errors during cleanup

class WalktruChoiceView(discord.ui.View):
    def __init__(self, story_maps, adventure_type, stage_key, user_id):
        super().__init__(timeout=600)  # 10 minute timeout
        self.story_maps = story_maps
        self.adventure_type = adventure_type
        self.stage_key = stage_key
        self.user_id = user_id
        
        # Get choices from story map
        stage = story_maps[adventure_type]['story_map'][stage_key]
        
        # Add numbered buttons for each choice
        choices = list(stage['choices'].items())
        for i, (choice_text, choice_data) in enumerate(choices[:3]):  # Limit to 3 choices
            button = discord.ui.Button(
                label=f"{i+1}",
                style=discord.ButtonStyle.primary,
                custom_id=f"choice_{i}"
            )
            button.callback = self.make_choice_callback(i, choice_text, choice_data)
            self.add_item(button)

    def make_choice_callback(self, choice_index, choice_text, choice_data):
        async def choice_callback(interaction: discord.Interaction):
            # Capture variables to avoid scoping issues
            _choice_text = choice_text
            _choice_data = choice_data
            _choice_index = choice_index
            
            story_map_manager = interaction.client.story_map_manager
            user_state = await story_map_manager.get_user_adventure_state(self.user_id, self.adventure_type)
            if not user_state:
                await interaction.response.send_message("❌ Your adventure session has expired. Please start a new adventure.", ephemeral=True)
                return
                
            adventure = self.story_maps[self.adventure_type]
            
            # Record the choice
            choice_record = {
                'stage': self.stage_key,
                'choice': _choice_text,
                'choice_number': _choice_index + 1
            }
            user_state['choices_made'].append(choice_record)
            user_state['stage_count'] += 1
            
            # Handle total failure first
            total_failure_chance = _choice_data.get('total_failure_chance', 0)
            if total_failure_chance > 0:
                total_failure_roll = random.randint(1, 100)
                if total_failure_roll <= total_failure_chance:
                    # Total failure - go to specific ending or generic failure
                    failure_ending = _choice_data.get('total_failure_next_stage', 'ending_total_failure')
                    await self.handle_ending(interaction, user_state, adventure, failure_ending, _choice_text, "TOTAL FAILURE!", False)
                    return

            # Handle success/failure based on success_chance
            success_chance = _choice_data.get('success_chance', 100)
            roll = random.randint(1, 100)
            success = roll <= success_chance
            
            # Get result text, next stage, and mechanic change
            if success:
                result_texts = _choice_data.get('success_text', ['Success!'])
                next_stage = _choice_data.get('success_next_stage')
                mechanic_change = _choice_data.get(f"success_{adventure['mechanic']}_change", _choice_data.get(f"{adventure['mechanic']}_change", 0))
            else:
                result_texts = _choice_data.get('failure_text', ['Failure!'])
                next_stage = _choice_data.get('failure_next_stage')
                mechanic_change = _choice_data.get(f"{adventure['mechanic']}_change", 0)
            
            # Pick random result text - handle both string and array formats
            if isinstance(result_texts, list):
                result_text = random.choice(result_texts) if result_texts else "Something happened..."
            else:
                result_text = result_texts if result_texts else "Something happened..."

            # Update mechanic value with bounds checking
            old_value = user_state['mechanic_value']
            user_state['mechanic_value'] += mechanic_change
            user_state['mechanic_value'] = clamp_stat_value(user_state['mechanic_value'], self.adventure_type)

            # Log if value was clamped for debugging
            if user_state['mechanic_value'] != old_value + mechanic_change:
                print(f"Warning: {adventure['mechanic']} value clamped from {old_value + mechanic_change} to {user_state['mechanic_value']}")
            
            # Update choice record to include mechanic change and success
            choice_record['mechanic_change'] = mechanic_change
            choice_record['success'] = success
            
            # Save updated state
            await story_map_manager.save_user_adventure_state(self.user_id, self.adventure_type, user_state)
            
            # Check for automatic defeat conditions
            mechanics = adventure.get('mechanics', {})
            if adventure['mechanic'] == 'fear' and user_state['mechanic_value'] >= mechanics.get('max_fear', 100):
                await self.handle_ending(interaction, user_state, adventure, 'ending_lose_fear_overwhelmed', _choice_text, result_text, False)
                return
            elif adventure['mechanic'] == 'heat' and user_state['mechanic_value'] >= mechanics.get('max_heat', 100):
                await self.handle_ending(interaction, user_state, adventure, 'jail_ending', _choice_text, result_text, False)
                return
            elif adventure['mechanic'] == 'mana' and user_state['mechanic_value'] <= 0:
                await self.handle_ending(interaction, user_state, adventure, 'defeat_no_mana', _choice_text, result_text, False)
                return
            elif adventure['mechanic'] == 'health' and user_state['mechanic_value'] <= 0:
                await self.handle_ending(interaction, user_state, adventure, 'ending_lose_death', _choice_text, result_text, False)
                return
            
            # Check if this is an ending
            if next_stage and (next_stage.startswith('ending_') or next_stage == 'ending_determination'):
                await self.handle_ending(interaction, user_state, adventure, next_stage, _choice_text, result_text, success)
                return

            if next_stage:
                current_stage_data = adventure['story_map'][user_state['current_stage']]
                
                # Now update to next stage
                user_state['current_stage'] = next_stage
                stage = adventure['story_map'][next_stage]
                
                # Check if this stage has choices - if not, it's an ending stage
                stage_choices = stage.get('choices', {})
                if not stage_choices:
                    # This is an ending stage without choices
                    await self.handle_ending(interaction, user_state, adventure, next_stage, _choice_text, result_text, success)
                    return
                
                # Show choice outcome embed first
                outcome_embed = discord.Embed(
                    title=adventure['title'],
                    description=f"**Your Choice:** {_choice_text}\n\n**Outcome:** {result_text}",
                    color=discord.Color.green() if success else discord.Color.orange()
                )
                
                # Add mechanic change information
                if mechanic_change != 0:
                    change_emoji = "⬆️" if mechanic_change > 0 else "⬇️"
                    outcome_embed.add_field(
                        name=f"{adventure['emoji']} {adventure['mechanic'].title()} Change",
                        value=f"{change_emoji} {abs(mechanic_change)} points",
                        inline=True
                    )
                
                # Add updated mechanic display
                mechanic_display = get_mechanic_display(self.adventure_type, user_state['mechanic_value'], adventure)
                outcome_embed.add_field(
                    name=f"Current {adventure['mechanic'].title()}",
                    value=mechanic_display,
                    inline=True
                )
                
                # Show outcome for 5 seconds
                await interaction.response.edit_message(embed=outcome_embed, view=None)
                await asyncio.sleep(5)
                
                # Then show the next stage with choices
                next_stage_data = adventure['story_map'][next_stage]
                choices = list(next_stage_data['choices'].items())
                next_choice_text = "\n\n".join([f"**{choice_key}**" for choice_key, _ in choices[:3]])
                
                next_embed = discord.Embed(
                    title=adventure['title'],
                    description=next_stage_data['text'],
                    color=discord.Color.blue()
                )
                
                # Add mechanic progress bar
                mechanic_display = get_mechanic_display(self.adventure_type, user_state['mechanic_value'], adventure)
                next_embed.add_field(
                    name=f"{adventure['emoji']} {adventure['mechanic'].title()}",
                    value=mechanic_display,
                    inline=False
                )
                
                next_embed.add_field(
                    name="📋 Your Choices",
                    value=next_choice_text,
                    inline=False
                )
                
                # Create new choice view for next stage
                new_view = WalktruChoiceView(story_map_manager.story_maps, self.adventure_type, next_stage, self.user_id)
                
                await interaction.edit_original_response(embed=next_embed, view=new_view)
            else:
                # No next stage provided, end the adventure
                await self.handle_ending(interaction, user_state, adventure, 'ending_determination', _choice_text, result_text, success)
        
        return choice_callback

    async def handle_ending(self, interaction, user_state, adventure, ending_key, choice_text, result_text, success):
        """Handle the ending of an adventure"""
        try:
            # Get ending data
            ending_data = adventure['ending_templates'].get(ending_key, {
                'title': 'Adventure Complete',
                'description': 'Your journey has come to an end.',
                'color': 0x00ff00 if success else 0xff0000
            })
            
            # Build plain text ending messages to avoid embed limits
            title_text = ending_data.get('title', 'Adventure Complete')
            desc_text = ending_data.get('description', 'Your journey has come to an end.')
            header_text = f"🏁 {title_text}\n{desc_text}"
            
            # Clean up the user's walktru state
            story_map_manager = interaction.client.story_map_manager
            await story_map_manager.clear_user_adventure_state(self.user_id, self.adventure_type)
            
            # Edit original message to plain text; fallback to follow-up if needed
            try:
                await interaction.edit_original_response(content=header_text, embed=None, view=None)
            except Exception:
                await interaction.followup.send(header_text)
            
            # Add summary of choices made as plain text (chunked if long)
            if user_state['choices_made']:
                choices_summary = "\n".join([
                    f"Stage {i+1}: {choice['choice']} ({'✅ Success' if choice.get('success', True) else '❌ Failure'})"
                    for i, choice in enumerate(user_state['choices_made'])
                ])
                journey_text = f"📜 Your Journey\n{choices_summary}"
                
                # Send in chunks to respect Discord's 2000 character limit
                for i in range(0, len(journey_text), 1900):
                    await interaction.followup.send(journey_text[i:i+1900])
            
            # Add final mechanic value as plain text (chunked if long)
            mechanic_display = get_mechanic_display(
                self.adventure_type, 
                user_state['mechanic_value'], 
                adventure
            )
            final_mechanic_text = f"🏁 Final {adventure['mechanic'].title()}\n{mechanic_display}"
            for i in range(0, len(final_mechanic_text), 1900):
                await interaction.followup.send(final_mechanic_text[i:i+1900])
            
        except Exception as e:
            print(f"Error handling ending: {e}")
            # Fallback to a simple text message if editing fails
            try:
                await interaction.edit_original_response(
                    content="Adventure Complete\nYour adventure has ended.",
                    embed=None,
                    view=None
                )
            except Exception:
                try:
                    await interaction.followup.send("Adventure Complete\nYour adventure has ended.")
                except:
                    pass

    async def on_timeout(self):
        """Called when the view times out after 10 minutes"""
        try:
            # Clear cached adventure state for this user when timeout occurs
            # The actual cleanup will happen when user starts a new adventure
            pass
        except:
            pass  # Ignore errors during cleanup

# Export all components
__all__ = [
    'StoryMapManager',
    'WalktruView', 
    'WalktruChoiceView',
    'create_progress_bar',
    'get_mechanic_display',
    'get_stat_bounds',
    'clamp_stat_value',
    'story_map_manager'
]
