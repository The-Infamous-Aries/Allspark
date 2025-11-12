print("DEBUG: UserDataManager module is being loaded!")
import json
import os
import asyncio
import time
import threading
import heapq
import hashlib
import gzip
import random
from typing import Dict, Any, Optional, List, Tuple, Union, Callable
from datetime import datetime, timedelta
from pathlib import Path
import logging
from contextlib import asynccontextmanager
import weakref
from concurrent.futures import ThreadPoolExecutor
from functools import wraps


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff_factor: float = 2.0, 
                    exceptions: Tuple = (OSError, IOError, PermissionError, FileNotFoundError)):
    """
    Decorator for retrying operations with exponential backoff.
    Designed for file operations and network failures in online hosting.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logging.error(f"Operation {func.__name__} failed after {max_retries + 1} attempts: {e}")
                        break
                    
                    # Add jitter to prevent thundering herd
                    jitter = random.uniform(0.1, 0.3) * current_delay
                    sleep_time = current_delay + jitter
                    
                    logging.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
                    current_delay *= backoff_factor
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    logging.error(f"Unexpected error in {func.__name__}: {e}")
                    raise
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logging.error(f"Operation {func.__name__} failed after {max_retries + 1} attempts: {e}")
                        break
                    
                    # Add jitter to prevent thundering herd
                    jitter = random.uniform(0.1, 0.3) * current_delay
                    sleep_time = current_delay + jitter
                    
                    logging.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {sleep_time:.2f}s")
                    time.sleep(sleep_time)
                    current_delay *= backoff_factor
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    logging.error(f"Unexpected error in {func.__name__}: {e}")
                    raise
            
            raise last_exception
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class NetworkResilienceManager:
    """Manages network-related failures and connection issues for online hosting"""
    
    def __init__(self):
        self.connection_failures = 0
        self.last_failure_time = None
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = 60  # seconds
        self.is_circuit_open = False
    
    def record_failure(self):
        """Record a network failure"""
        self.connection_failures += 1
        self.last_failure_time = datetime.now()
        
        if self.connection_failures >= self.circuit_breaker_threshold:
            self.is_circuit_open = True
            logging.warning(f"Circuit breaker opened after {self.connection_failures} failures")
    
    def record_success(self):
        """Record a successful operation"""
        self.connection_failures = 0
        self.is_circuit_open = False
    
    def should_allow_request(self) -> bool:
        """Check if requests should be allowed (circuit breaker pattern)"""
        if not self.is_circuit_open:
            return True
        
        if self.last_failure_time and \
           (datetime.now() - self.last_failure_time).total_seconds() > self.circuit_breaker_timeout:
            self.is_circuit_open = False
            self.connection_failures = 0
            logging.info("Circuit breaker reset - allowing requests")
            return True
        
        return False


class UserDataManager:
    """
    High-performance optimized UserDataManager with advanced caching,
    async I/O optimization, and memory management.
    """
    
    _instance = None
    _initialized = False
    _init_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Thread-safe singleton pattern to ensure only one instance exists"""
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = super(UserDataManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, data_directory: str = "Systems/Data/Users"):
        """Initialize only once - subsequent calls use the same instance"""
        with UserDataManager._init_lock:
            if UserDataManager._initialized:
                return
                
            UserDataManager._initialized = True
        
        # Get the parent directory of the current file (user_data_manager.py)
        # This ensures we use the correct base directory regardless of where the script is run from
        current_file_dir = Path(__file__).parent
        base_systems_dir = current_file_dir  # Since user_data_manager.py is already in Systems/
        
        self.base_path = base_systems_dir / "Data/Users"
        self.global_saves_path = base_systems_dir / "Data/Global Saves"
        self.json_path = base_systems_dir / "Data"
        
        self._loaded_files = set()
        self._loading_in_progress = set()
        self._file_modification_times = {}
        self._compression_enabled = True
        self._thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="UDM")
        # Track last-saved content hashes to skip redundant writes
        self._file_hashes: Dict[str, str] = {}
        # Thresholds for save behaviors
        self._save_compress_threshold_bytes: int = 100 * 1024  # write .json.gz when payload is large
        self._save_verify_threshold_bytes: int = 5 * 1024 * 1024  # verify by reading back when very large
        self._compact_json: bool = True  # write compact JSON to reduce size and time
        
        # Preload critical game data files
        self._critical_files = {'pet_equipment', 'monsters', 'bosses', 'titans', 'pets_level', 'energon_game', 'cybercoin_market_data', 'roasts', 'trivia_transformers_culture', 'trivia_transformers_characters', 'trivia_transformers_factions', 'trivia_transformers_movies', 'trivia_transformers_shows'}

        # Get the base systems directory (same as where user_data_manager.py is located)
        base_systems_dir = Path(__file__).parent
        
        # JSON files dictionary for health checks
        self.json_files = {
            'monsters': self.json_path / "PetsInfo" / "monsters.json",
            'bosses': self.json_path / "PetsInfo" / "bosses.json",
            'titans': self.json_path / "PetsInfo" / "titans.json",
            'pets_level': self.json_path / "PetsInfo" / "pets_level.json",
            'pet_equipment': self.json_path / "PetsInfo" / "pet_equipment.json",
            'energon_game': self.global_saves_path / "energon_game.json",
            'cybercoin_market_data': self.global_saves_path / "cybercoin_market_data.json",
            'roasts': self.json_path / "Talk" / "roasts.json",
            'trivia_transformers_culture': base_systems_dir / "Data/Trivia/transformers_culture.json",
            'trivia_transformers_characters': base_systems_dir / "Data/Trivia/transformers_characters.json",
            'trivia_transformers_factions': base_systems_dir / "Data/Trivia/transformers_factions.json",
            'trivia_transformers_movies': base_systems_dir / "Data/Trivia/transformers_movies.json",
            'trivia_transformers_shows': base_systems_dir / "Data/Trivia/transformers_shows.json",

            # Zodiac data files
            'astrology': base_systems_dir / "Data/Zodiac/astrology.json",
            'chinese_astrology': base_systems_dir / "Data/Zodiac/chinese_astrology.json",
            'primal_astrology': base_systems_dir / "Data/Zodiac/primal_astrology.json"
        }

        self._file_paths = {
            # Core game data files
            'monsters': self.json_path / "PetsInfo" / "monsters.json",
            'bosses': self.json_path / "PetsInfo" / "bosses.json",
            'titans': self.json_path / "PetsInfo" / "titans.json",
            'pets_level': self.json_path / "PetsInfo" / "pets_level.json",
            'pet_xp': self.json_path / "PetsInfo" / "pet_xp.json",
            'pets_mission': self.json_path / "PetsInfo" / "pets_mission.json",
            'pet_equipment': self.json_path / "PetsInfo" / "pet_equipment.json",
            'recruit': self.json_path / "recruit.json",
            'bot_logs': self.json_path / "bot_logs.json",
            'alliance_9445': self.json_path / "Bloc" / "alliance_9445.json",
            'alliance_14110': self.json_path / "Bloc" / "alliance_14110.json",
            'alliance_14036': self.json_path / "Bloc" / "alliance_14036.json",
            'alliance_14177': self.json_path / "Bloc" / "alliance_14177.json",
            'alliance_14147': self.json_path / "Bloc" / "alliance_14147.json",
            'alliance_14230': self.json_path / "Bloc" / "alliance_14230.json",
            
            # Global saves
            'energon_game': self.global_saves_path / "energon_game.json",
            'cybercoin_market_data': self.global_saves_path / "cybercoin_market_data.json",
            'recruitment_history': self.json_path / "recruitment_history.json",
            'global_leaderboards': self.global_saves_path / "global_leaderboards.json",
            'server_analytics': self.global_saves_path / "server_analytics.json",
            'blitz_parties': self.json_path / "blitz_parties.json",
            
            # Random talk data
            'what_talk': base_systems_dir / "Data/Talk/what.json",
            'jokes_talk': base_systems_dir / "Data/Talk/jokes.json",
            'grump_talk': base_systems_dir / "Data/Talk/grump.json",
            'blessings_talk': base_systems_dir / "Data/Talk/blessings.json",
            'user_lore': base_systems_dir / "Data/Talk/user_lore.json",
            'roasts': self.json_path / "Talk" / "roasts.json",
            
            # Walk Tru adventure data
            'walktru_horror': base_systems_dir / "Data/Walk Tru/Horror.json",
            'walktru_ganster': base_systems_dir / "Data/Walk Tru/Ganster.json",
            'walktru_knight': base_systems_dir / "Data/Walk Tru/Knight.json",
            'walktru_robot': base_systems_dir / "Data/Walk Tru/Robot.json",
            'walktru_western': base_systems_dir / "Data/Walk Tru/Western.json",
            'walktru_wizard': base_systems_dir / "Data/Walk Tru/Wizard.json",
            
            # Trivia data files
            'trivia_transformers_culture': base_systems_dir / "Data/Trivia/transformers_culture.json",
            'trivia_transformers_characters': base_systems_dir / "Data/Trivia/transformers_characters.json",
            'trivia_transformers_factions': base_systems_dir / "Data/Trivia/transformers_factions.json",
            'trivia_transformers_movies': base_systems_dir / "Data/Trivia/transformers_movies.json",
            'trivia_transformers_shows': base_systems_dir / "Data/Trivia/transformers_shows.json",

            # Zodiac data files
            'astrology': base_systems_dir / "Data/Zodiac/astrology.json",
            'chinese_astrology': base_systems_dir / "Data/Zodiac/chinese_astrology.json",
            'primal_astrology': base_systems_dir / "Data/Zodiac/primal_astrology.json"
        }
           
        self._cache = {}
        self._cache_locks = {}
        self._cache_timestamps = {}
        self._cache_hits = 0
        # Initialize metrics tracking
        self._metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'reads': 0,
            'writes': 0,
            'errors': 0,
            'corrupted_files': 0,
            'recovery_attempts': 0
        }
        # Optimized caching parameters - increased for better performance
        self._max_cache_size = 2000  # Increased cache size for more data retention
        self._cache_ttl = 600        # Increased TTL for frequently accessed data
        self._lazy_cache_ttl = 1200  # Increased lazy TTL for static game data
        
        # Special cache expiration times for specific files
        self._special_cache_ttl = {
            'alliance_9445': 3600,  # 1 hour expiration for alliance 9445 cache
            'alliance_14110': 3600,  # 1 hour expiration for alliance 14110 cache
            'alliance_14036': 3600,  # 1 hour expiration for alliance 14036 (TCO) cache
            'alliance_14177': 3600,  # 1 hour expiration for alliance 14177 (Northern Concord) cache
            'alliance_14147': 3600,  # 1 hour expiration for alliance 14147 (Eternal Phoenix) cache
            'alliance_14230': 3600  # 1 hour expiration for alliance 14230 (Reclaimed Flame) cache
        }
        self._file_locks = {}
        self._global_lock = asyncio.Lock()
        self._refresh_task = None
        self._shutdown_event = asyncio.Event()
        self._backup_enabled = False  # Backup functionality completely disabled
        self._max_backup_files = 5
        
        # Initialize network resilience and error handling
        self._network_manager = NetworkResilienceManager()
        self._max_retries = 3
        self._retry_delay = 1.0
        self._backoff_factor = 2.0
        
        # Add network failure metrics
        self._metrics['network_failures'] = 0
        self._metrics['circuit_breaker_trips'] = 0
        
        # Auto-clear tracking for alliance files
        self._alliance_auto_clear_tasks = {}  # Track scheduled clear tasks
        self._alliance_clear_delay = 3600  # 1 hour in seconds

        # Auto-delete tracking for temporary war-party files (home/away)
        self._war_party_auto_delete_tasks: Dict[str, asyncio.Task] = {}
        self._war_party_delete_delay: int = 1800  # 30 minutes in seconds
        
        self._ensure_directories()
        
        try:
            asyncio.get_running_loop()
            asyncio.create_task(self._start_background_refresh())
            asyncio.create_task(self._warm_critical_cache())
        except RuntimeError:
            pass
    
    def _ensure_directories(self):
        """Efficiently ensure all required directories exist"""
        # Get the base systems directory (same as where user_data_manager.py is located)
        base_systems_dir = Path(__file__).parent
        
        directories = [
            self.base_path, 
            self.global_saves_path, 
            self.json_path,
            base_systems_dir / "Data/Talk",
            base_systems_dir / "Data/Walk Tru",
            base_systems_dir / "Data/Trivia",
            base_systems_dir / "Data/Zodiac"
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, file_path: Path) -> str:
        """Generate efficient cache key with file modification time"""
        try:
            mod_time = file_path.stat().st_mtime if file_path.exists() else 0
            return f"{file_path.name}_{mod_time}"
        except (OSError, FileNotFoundError):
            return str(file_path.name)
    
    def _should_cache(self, key: str) -> bool:
        """Check if cache entry is still valid"""
        if key not in self._cache_timestamps:
            return False
    
    async def _schedule_alliance_auto_clear(self, alliance_key: str):
        """Schedule automatic clearing of alliance data after 1 hour"""
        logging.info(f"_schedule_alliance_auto_clear called for {alliance_key}")
        try:
            # Cancel any existing scheduled task for this alliance
            if alliance_key in self._alliance_auto_clear_tasks:
                self._alliance_auto_clear_tasks[alliance_key].cancel()
                del self._alliance_auto_clear_tasks[alliance_key]
            
            # Create new auto-clear task
            async def auto_clear_task():
                try:
                    await asyncio.sleep(self._alliance_clear_delay)
                    await self._clear_alliance_data(alliance_key)
                except asyncio.CancelledError:
                    logging.info(f"Auto-clear task cancelled for {alliance_key}")
                except Exception as e:
                    logging.error(f"Error in auto-clear task for {alliance_key}: {e}")
            
            # Schedule the task
            task = asyncio.create_task(auto_clear_task())
            self._alliance_auto_clear_tasks[alliance_key] = task
            
            logging.info(f"Scheduled auto-clear for {alliance_key} in {self._alliance_clear_delay} seconds")
            
        except Exception as e:
            logging.error(f"Error scheduling auto-clear for {alliance_key}: {e}")
    
    async def _clear_alliance_data(self, alliance_key: str):
        """Clear alliance data file and cache"""
        try:
            if alliance_key not in self._file_paths:
                logging.warning(f"Alliance key {alliance_key} not found in file paths")
                return
            
            file_path = self._file_paths[alliance_key]
            
            # Clear the file by writing empty data
            empty_data = {
                'nations': [],
                'alliance_id': alliance_key.replace('alliance_', ''),
                'last_updated': datetime.now().isoformat(),
                'cleared_at': datetime.now().isoformat()
            }
            
            # Save empty data
            success = await self._save_json_optimized(file_path, empty_data)
            
            if success:
                # Remove from cache
                cache_key = self._get_cache_key(file_path)
                self._cache.pop(cache_key, None)
                self._cache_timestamps.pop(cache_key, None)
                
                logging.info(f"Successfully cleared alliance data for {alliance_key}")
            else:
                logging.error(f"Failed to clear alliance data for {alliance_key}")
            
            # Remove the task from tracking
            if alliance_key in self._alliance_auto_clear_tasks:
                del self._alliance_auto_clear_tasks[alliance_key]
                
        except Exception as e:
            logging.error(f"Error clearing alliance data for {alliance_key}: {e}")
    
    def cancel_alliance_auto_clear(self, alliance_key: str):
        """Cancel scheduled auto-clear for a specific alliance"""
        try:
            if alliance_key in self._alliance_auto_clear_tasks:
                self._alliance_auto_clear_tasks[alliance_key].cancel()
                del self._alliance_auto_clear_tasks[alliance_key]
                logging.info(f"Cancelled auto-clear for {alliance_key}")
                return True
            return False
        except Exception as e:
            logging.error(f"Error cancelling auto-clear for {alliance_key}: {e}")
            return False
    
    async def cancel_all_alliance_auto_clears(self):
        """Cancel all scheduled alliance auto-clear tasks"""
        try:
            for alliance_key in list(self._alliance_auto_clear_tasks.keys()):
                self.cancel_alliance_auto_clear(alliance_key)
            logging.info("Cancelled all alliance auto-clear tasks")
        except Exception as e:
            logging.error(f"Error cancelling all alliance auto-clear tasks: {e}")
    
    async def _schedule_war_party_auto_delete(self, war_key: str, delay_seconds: Optional[int] = None):
        """Schedule automatic deletion of war-party data file after a delay (default 30 minutes)."""
        try:
            delay = int(delay_seconds) if delay_seconds is not None else self._war_party_delete_delay
            # Cancel any existing scheduled task for this war_key
            if war_key in self._war_party_auto_delete_tasks:
                try:
                    self._war_party_auto_delete_tasks[war_key].cancel()
                except Exception:
                    pass
                del self._war_party_auto_delete_tasks[war_key]

            async def auto_delete_task():
                try:
                    await asyncio.sleep(delay)
                    await self._delete_war_party_data(war_key)
                except asyncio.CancelledError:
                    logging.info(f"War-party auto-delete task cancelled for {war_key}")
                except Exception as e:
                    logging.error(f"Error in war-party auto-delete task for {war_key}: {e}")

            task = asyncio.create_task(auto_delete_task())
            self._war_party_auto_delete_tasks[war_key] = task
            logging.info(f"Scheduled war-party auto-delete for {war_key} in {delay} seconds")
        except Exception as e:
            logging.error(f"Error scheduling war-party auto-delete for {war_key}: {e}")

    async def _delete_war_party_data(self, war_key: str):
        """Delete war-party file and evict any related cache entries."""
        try:
            if war_key not in self._file_paths:
                # Resolve dynamic path if needed
                file_path = self.json_path / "Bloc" / f"{war_key}.json"
                self._file_paths[war_key] = file_path
            else:
                file_path = self._file_paths[war_key]

            # Remove file if it exists
            try:
                if file_path.exists():
                    file_path.unlink(missing_ok=True)
                    logging.info(f"Deleted war-party data file for {war_key}: {file_path}")
            except Exception as e:
                logging.error(f"Failed to delete war-party file for {war_key}: {e}")

            # Evict cache entries
            cache_key = self._get_cache_key(file_path)
            self._cache.pop(cache_key, None)
            self._cache_timestamps.pop(cache_key, None)

            # Remove scheduled task tracking
            if war_key in self._war_party_auto_delete_tasks:
                del self._war_party_auto_delete_tasks[war_key]
        except Exception as e:
            logging.error(f"Error clearing war-party data for {war_key}: {e}")
    
    def _evict_lru_cache(self):
        """Optimized LRU cache eviction with memory pressure handling"""
        if len(self._cache) <= self._max_cache_size:
            return
        
        to_remove = len(self._cache) - self._max_cache_size + 25
        
        items = list(self._cache_timestamps.items())
        items.sort(key=lambda x: x[1]) 
        
        for key, _ in items[:to_remove]:
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
            self._cache_locks.pop(key, None)
    
    @asynccontextmanager
    async def _acquire_file_lock(self, file_path: Path):
        """Acquire file-specific lock for concurrent access"""
        file_str = str(file_path)
        if file_str not in self._file_locks:
            self._file_locks[file_str] = asyncio.Lock()
        
        async with self._file_locks[file_str]:
            yield
    
    @retry_on_failure(max_retries=3, delay=1.0, backoff_factor=2.0)
    async def _load_json_optimized(self, file_path: Path, default_data: Any = None, lazy: bool = False) -> Any:
        """Optimized JSON loading with caching and error handling"""
        cache_key = self._get_cache_key(file_path)
        
        # First check: if already cached and valid, return immediately
        if cache_key in self._cache and self._should_cache(cache_key):
            self._metrics['cache_hits'] += 1
            return self._cache[cache_key]
        
        # Wait for any ongoing loading of the same file with timeout
        if cache_key in self._loading_in_progress:
            timeout_start = time.time()
            timeout_duration = 30.0  # 30 second timeout
            while cache_key in self._loading_in_progress:
                if time.time() - timeout_start > timeout_duration:
                    logging.warning(f"Timeout waiting for loading of {cache_key}, proceeding with fresh load")
                    self._loading_in_progress.discard(cache_key)  # Remove stale loading flag
                    break
                await asyncio.sleep(0.001)
            # Double-check after waiting
            if cache_key in self._cache and self._should_cache(cache_key):
                self._metrics['cache_hits'] += 1
                return self._cache[cache_key]
        
        self._metrics['cache_misses'] += 1
        self._loading_in_progress.add(cache_key)
        
        try:
            async with self._acquire_file_lock(file_path):
                # Triple-check inside the lock to prevent race conditions
                if cache_key in self._cache and self._should_cache(cache_key):
                    self._metrics['cache_hits'] += 1
                    return self._cache[cache_key]
                
                if file_path.exists():
                    # Use optimized loading with compression support for large files
                    file_size = file_path.stat().st_size
                    if file_size > 50000:  # 50KB threshold for compression
                        data = await self._load_json_with_compression(file_path)
                    else:
                        try:
                            import rapidjson
                            # Use utf-8-sig to gracefully handle files starting with BOM
                            with open(file_path, 'r', encoding='utf-8-sig') as f:
                                data = rapidjson.load(f)
                        except (ImportError, Exception):
                            # Fallback to standard json with utf-8-sig for BOM compatibility
                            with open(file_path, 'r', encoding='utf-8-sig') as f:
                                data = json.load(f)
                else:
                    data = default_data or {}
                    await self._save_json_optimized(file_path, data)
                
                self._cache[cache_key] = data
                ttl = self._lazy_cache_ttl if lazy else self._cache_ttl
                self._cache_timestamps[cache_key] = datetime.now()
                self._loaded_files.add(cache_key)
                self._evict_lru_cache()
                
                return data
                
        except Exception as e:
            self._metrics['errors'] += 1
            logging.error(f"Error loading {file_path}: {e}")
            return default_data if default_data is not None else {}
        finally:
            self._loading_in_progress.discard(cache_key)
    
    @retry_on_failure(max_retries=3, delay=1.0, backoff_factor=2.0)
    async def _save_json_optimized(self, file_path: Path, data: Any) -> bool:
        async with self._acquire_file_lock(file_path):
            try:
                # Validate data integrity before saving
                if not await self.validate_data_integrity(file_path, data):
                    self._metrics['errors'] += 1
                    logging.error(f"Data integrity validation failed for {file_path}")
                    return False
                # Serialize once using fastest available encoder, compact and sorted for stable hashing
                serialized_bytes: bytes
                try:
                    import orjson  # type: ignore
                    opts = orjson.OPT_SORT_KEYS
                    serialized_bytes = orjson.dumps(data, option=opts)
                except Exception:
                    try:
                        import rapidjson  # type: ignore
                        serialized_str = rapidjson.dumps(
                            data,
                            sort_keys=True,
                            ensure_ascii=False,
                            indent=None if self._compact_json else 2,
                        )
                    except Exception:
                        serialized_str = json.dumps(
                            data,
                            sort_keys=True,
                            ensure_ascii=False,
                            separators=(",", ":") if self._compact_json else None,
                            indent=None if self._compact_json else 2,
                        )
                    serialized_bytes = serialized_str.encode('utf-8')

                # Change detection via stable hash to skip redundant writes
                file_key = str(file_path)
                new_hash = hashlib.sha256(serialized_bytes).hexdigest()
                last_hash = self._file_hashes.get(file_key)
                if last_hash == new_hash and file_path.exists():
                    # No changes; update cache timestamp and return quickly
                    cache_key = self._get_cache_key(file_path)
                    self._cache_timestamps[cache_key] = datetime.now()
                    self._metrics['writes'] += 0  # explicit noop
                    return True
                
                # Ensure parent directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Use atomic write with temporary file
                temp_path = file_path.with_suffix('.tmp')
                # Write serialized bytes to temp file
                with open(temp_path, 'wb') as f:
                    f.write(serialized_bytes)
                
                # Verify the written data by reading it back
                try:
                    if temp_path.stat().st_size >= self._save_verify_threshold_bytes:
                        with open(temp_path, 'rb') as f:
                            verify_bytes = f.read()
                        verify_hash = hashlib.sha256(verify_bytes).hexdigest()
                        if verify_hash != new_hash:
                            raise ValueError("Written data verification hash mismatch")
                except Exception as e:
                    temp_path.unlink(missing_ok=True)
                    raise ValueError(f"Data verification failed: {e}")
                
                # Atomic replace
                temp_path.replace(file_path)
                
                # Optional: write compressed version for large files to speed future loads
                try:
                    if self._compression_enabled and len(serialized_bytes) >= self._save_compress_threshold_bytes:
                        compressed_path = file_path.with_suffix('.json.gz')
                        with gzip.open(compressed_path, 'wb') as gz:
                            gz.write(serialized_bytes)
                except Exception as e:
                    logging.warning(f"Compression save failed for {file_path}: {e}")

                # Update cache
                cache_key = self._get_cache_key(file_path)
                self._cache[cache_key] = data
                self._cache_timestamps[cache_key] = datetime.now()
                self._file_hashes[file_key] = new_hash
                
                self._metrics['writes'] += 1
                self._network_manager.record_success()
                return True
                
            except Exception as e:
                self._metrics['errors'] += 1
                
                # Check if this is a network-related failure
                if isinstance(e, (OSError, IOError, PermissionError)):
                    self._metrics['network_failures'] += 1
                    self._network_manager.record_failure()
                    
                    if self._network_manager.is_circuit_open:
                        self._metrics['circuit_breaker_trips'] += 1
                        logging.warning(f"Circuit breaker is open, failing fast for {file_path}")
                        return False
                
                logging.error(f"Error saving {file_path}: {e}")

                return False
    
    async def _start_background_refresh(self):
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(60)
                
                current_time = datetime.now()
                expired_keys = []
                
                for key, timestamp in self._cache_timestamps.items():
                    ttl = self._lazy_cache_ttl if key in self._loaded_files else self._cache_ttl
                    if (current_time - timestamp).total_seconds() > ttl:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    if key not in self._loaded_files or len(self._cache) > self._max_cache_size:
                        self._cache.pop(key, None)
                        self._cache_timestamps.pop(key, None)
                    
            except Exception as e:
                logging.error(f"Background refresh error: {e}")
        
        # Cleanup auto-clear tasks on shutdown
        try:
            await self.cancel_all_alliance_auto_clears()
        except Exception as e:
            logging.error(f"Error cleaning up alliance auto-clear tasks on shutdown: {e}")
    
    async def _warm_critical_cache(self):
        """Preload critical game data files into cache"""
        await asyncio.sleep(1)  # Wait for initialization
        try:
            for file_key in self._critical_files:
                if file_key in self._file_paths:
                    file_path = self._file_paths[file_key]
                    await self._load_json_optimized(file_path, {}, lazy=True)
                    logging.info(f"Warmed cache for critical file: {file_key}")
        except Exception as e:
            logging.error(f"Cache warming error: {e}")


    
    async def _load_json_with_compression(self, file_path: Path) -> Any:
        """Load JSON with optional compression support"""
        compressed_path = file_path.with_suffix('.json.gz')
        
        if compressed_path.exists() and compressed_path.stat().st_mtime > file_path.stat().st_mtime:
            # Use compressed version if newer
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._thread_pool,
                self._load_compressed_json,
                compressed_path
            )
        else:
            # Use regular JSON
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._thread_pool,
                self._load_regular_json,
                file_path
            )


    
    def _load_compressed_json(self, file_path: Path) -> Any:
        """Thread-safe compressed JSON loading"""
        try:
            # Use utf-8-sig to handle potential BOM in compressed JSON
            with gzip.open(file_path, 'rt', encoding='utf-8-sig') as f:
                return json.load(f)
        except Exception:
            # Fallback to regular JSON
            regular_path = file_path.with_suffix('.json')
            return self._load_regular_json(regular_path)
    
    def _load_regular_json(self, file_path: Path) -> Any:
        """Thread-safe regular JSON loading"""
        try:
            import rapidjson
            # Use utf-8-sig to gracefully handle BOM-prefixed files
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                return rapidjson.load(f)
        except (ImportError, Exception):
            # Fallback to standard json with utf-8-sig for BOM compatibility
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
    
    # Generic JSON accessors for named files
    async def get_json_data(self, key: str, default_data: Any = None) -> Any:
        """Get JSON data by key with optional default data - alias for load_json_data"""
        result = await self.load_json_data(key)
        # If load_json_data returns empty dict and default_data is provided, return default_data
        if result == {} and default_data is not None:
            return default_data
        return result
    
    async def save_json_data(self, key: str, data: Any) -> bool:
        """Save JSON data by key - uses _save_json_optimized internally"""
        try:
            if not isinstance(key, str) or key.strip() == "":
                raise ValueError("Invalid key provided to save_json_data")

            # Handle dynamic alliance keys
            if key.startswith('alliance_'):
                # For alliance keys, dynamically create the file path if not in _file_paths
                if key not in self._file_paths:
                    alliance_id = key.replace('alliance_', '')
                    file_path = self.json_path / "Bloc" / f"alliance_{alliance_id}.json"
                    self._file_paths[key] = file_path
                    logging.info(f"Dynamically added alliance key '{key}' with path: {file_path}")
                
                file_path = self._file_paths[key]
                result = await self._save_json_optimized(file_path, data)
                
                # Schedule auto-clear for alliance files if save was successful
                alliance_list = [
                    'alliance_9445', 'alliance_14036', 'alliance_14110', 
                    'alliance_14147', 'alliance_14177', 'alliance_14230'
                ]
                
                if result and key in alliance_list:
                    print(f"DEBUG: Scheduling auto-clear for known alliance key: {key}")
                    await self._schedule_alliance_auto_clear(key)
                
                return result
            # Handle dynamic war party keys (home/away groupings)
            elif key.startswith('war_party_'):
                # Map to Bloc/war_party_<identifier>.json
                if key not in self._file_paths:
                    file_path = self.json_path / "Bloc" / f"{key}.json"
                    self._file_paths[key] = file_path
                    logging.info(f"Dynamically added war party key '{key}' with path: {file_path}")
                file_path = self._file_paths[key]
                result = await self._save_json_optimized(file_path, data)
                # Schedule auto-delete for war-party (home/away) files if save was successful
                if result:
                    await self._schedule_war_party_auto_delete(key)
                return result
            # Handle unified wars-between-parties keys
            elif key.startswith('war_parties_'):
                # Persist combined Home-vs-Away wars into Bloc/war_parties_<home>_vs_<away>.json
                if key not in self._file_paths:
                    file_path = self.json_path / "Bloc" / f"{key}.json"
                    self._file_paths[key] = file_path
                    logging.info(f"Dynamically added war parties key '{key}' with path: {file_path}")
                file_path = self._file_paths[key]
                result = await self._save_json_optimized(file_path, data)
                # Schedule auto-delete in 15 minutes for unified parties files
                if result:
                    try:
                        await self._schedule_war_party_auto_delete(key, delay_seconds=900)
                    except Exception as e:
                        logging.warning(f"Failed to schedule auto-delete for '{key}': {e}")
                return result
            # Handle dynamic treaties keys
            elif key.startswith('treaties_'):
                # Dynamically map treaties to Bloc/treaties_<id>.json
                if key not in self._file_paths:
                    treaties_id = key.replace('treaties_', '')
                    file_path = self.json_path / "Bloc" / f"treaties_{treaties_id}.json"
                    self._file_paths[key] = file_path
                    logging.info(f"Dynamically added treaties key '{key}' with path: {file_path}")
                file_path = self._file_paths[key]
                return await self._save_json_optimized(file_path, data)
            else:
                # For non-alliance keys, use the original logic
                if key not in self._file_paths:
                    logging.warning(f"Unknown data key '{key}' for save_json_data")
                    return False

                file_path = self._file_paths[key]
                return await self._save_json_optimized(file_path, data)
            
        except Exception as e:
            logging.error(f"save_json_data error for key '{key}': {e}")
            return False

    async def load_json_data(self, key: str) -> Any:
        """Load a JSON blob by logical key from _file_paths.
        Example keys: 'recruit', 'bot_logs', etc.
        Returns default structure if file missing or unreadable.
        """
        try:
            if not isinstance(key, str) or key.strip() == "":
                raise ValueError("Invalid key provided to load_json_data")

            # Handle dynamic alliance keys
            if key.startswith('alliance_'):
                # For alliance keys, dynamically create the file path if not in _file_paths
                if key not in self._file_paths:
                    alliance_id = key.replace('alliance_', '')
                    file_path = self.json_path / "Bloc" / f"alliance_{alliance_id}.json"
                    self._file_paths[key] = file_path
                    logging.info(f"Dynamically added alliance key '{key}' with path: {file_path}")
                
                file_path = self._file_paths[key]
                # Use lazy cache for relatively static data
                return await self._load_json_optimized(file_path, default_data={}, lazy=True)
            # Handle dynamic treaties keys
            elif key.startswith('treaties_'):
                if key not in self._file_paths:
                    treaties_id = key.replace('treaties_', '')
                    file_path = self.json_path / "Bloc" / f"treaties_{treaties_id}.json"
                    self._file_paths[key] = file_path
                    logging.info(f"Dynamically added treaties key '{key}' with path: {file_path}")
                file_path = self._file_paths[key]
                return await self._load_json_optimized(file_path, default_data={}, lazy=True)
            # Handle dynamic war party keys (home/away)
            elif key.startswith('war_party_'):
                if key not in self._file_paths:
                    file_path = self.json_path / "Bloc" / f"{key}.json"
                    self._file_paths[key] = file_path
                    logging.info(f"Dynamically added war party key '{key}' with path: {file_path}")
                file_path = self._file_paths[key]
                # Provide a sensible default structure
                return await self._load_json_optimized(file_path, default_data={'nations': []}, lazy=True)
            # Handle unified wars-between-parties keys
            elif key.startswith('war_parties_'):
                if key not in self._file_paths:
                    file_path = self.json_path / "Bloc" / f"{key}.json"
                    self._file_paths[key] = file_path
                    logging.info(f"Dynamically added war parties key '{key}' with path: {file_path}")
                file_path = self._file_paths[key]
                return await self._load_json_optimized(file_path, default_data={'wars': []}, lazy=True)
            else:
                # For non-alliance keys, use the original logic
                if key not in self._file_paths:
                    logging.warning(f"Unknown data key '{key}' requested; returning empty dict")
                    return {}

                file_path = self._file_paths[key]

                # Provide sensible defaults for known schemas
                default_map: Dict[str, Any] = {
                    'recruit': { 'messages': [] },
                    'bot_logs': { 'entries': [] }
                }
                default_data = default_map.get(key, {})

                # Use lazy cache for relatively static data
                return await self._load_json_optimized(file_path, default_data=default_data, lazy=True)
        except Exception as e:
            logging.error(f"load_json_data error for key '{key}': {e}")
            return {}

    # User Data Methods (Optimized)
    def _get_user_file_path(self, user_id: str) -> Path:
        return self.base_path / f"{user_id}.json"
    
    def _create_default_user_data(self, user_id: str, username: str) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        return {
            "user_id": user_id,
            "username": username,
            "created_at": now,
            "last_updated": now,
            "pets": {
                "pet_data": None,
                "combiner_teams": {}
            },
            "energon_rush": {"high_score": 0, "games_played": 0, "total_energon_collected": 0},
            "shooting_range": {
                "high_score": 0, "games_played": 0, "accuracy": 0.0,
                "total_targets_hit": 0, "total_hits": 0, "total_shots": 0,
                "sessions_played": 0,
                "best_records": {"5": {"accuracy": 0, "hits": 0}, "15": {"accuracy": 0, "hits": 0},
                               "25": {"accuracy": 0, "hits": 0}, "50": {"accuracy": 0, "hits": 0},
                               "100": {"accuracy": 0, "hits": 0}},
                "round_attempts": {}
            },
            "mega_fights": {
                "mega_fights_won": 0, "mega_fights_lost": 0,
                "total_energon_won": 0, "total_energon_lost": 0, "total_fights": 0
            },
            "slot_machine": {
                "total_games_played": 0, "total_winnings": 0, "total_losses": 0,
                "jackpots_won": 0, "two_matches_won": 0, "highest_bet": 0,
                "highest_win": 0, "games_by_difficulty": {"easy": 0, "medium": 0, "hard": 0},
                "winnings_by_difficulty": {"easy": 0, "medium": 0, "hard": 0}
            },
            "energon": {"energon": 0},
            "cybercoin_market": {
                "portfolio": {"total_coins": 0, "total_invested": 0, "total_sold": 0, "total_profit": 0, "current_value": 0},
                "transactions": {"purchases": [], "sales": []},
                "holdings": []
            }
        }
    
    async def get_user_data(self, user_id: str, username: str = None) -> Dict[str, Any]:
        """Get user data with username update optimization"""
        file_path = self._get_user_file_path(user_id)
        
        if not file_path.exists():
            return self._create_default_user_data(user_id, username or "Unknown")
        
        data = await self._load_json_optimized(file_path)
        
        # Efficient username update - avoid recursion by not calling save_user_data
        if username and data.get("username") != username:
            data["username"] = username
            data["last_updated"] = datetime.now().isoformat()
            # Save directly without calling save_user_data to avoid recursion
            await self._save_json_optimized(file_path, data)
        
        return data
    
    async def save_user_data(self, user_id: str, username: str, data: Dict[str, Any]) -> bool:
        """Save user data with atomic operations"""
        file_path = self._get_user_file_path(user_id)
        
        # Update timestamp efficiently
        data["last_updated"] = datetime.now().isoformat()
        if username:
            data["username"] = username
        
        return await self._save_json_optimized(file_path, data)
    
    async def get_slot_machine_data(self, player_id: str, username: str = None) -> Dict[str, Any]:
        """Get slot machine statistics for a player"""
        user_data = await self.get_user_data(player_id, username)
        return user_data.get("slot_machine", {
            "total_games_played": 0,
            "total_winnings": 0,
            "total_losses": 0,
            "jackpots_won": 0,
            "two_matches_won": 0,
            "highest_bet": 0,
            "highest_win": 0,
            "games_by_difficulty": {"easy": 0, "medium": 0, "hard": 0},
            "winnings_by_difficulty": {"easy": 0, "medium": 0, "hard": 0}
        })

    async def save_slot_machine_data(self, player_id: str, username: str, data: Dict[str, Any]) -> bool:
        """Save slot machine statistics for a player"""
        user_data = await self.get_user_data(player_id, username)
        user_data["slot_machine"] = data
        return await self.save_user_data(player_id, username, user_data)

    # Theme System Methods (Optimized)
    async def get_theme_system_data(self, user_id: str, username: str) -> Dict[str, Any]:
        """Get theme system data - returns empty dict as theme system is being phased out"""
        # Theme system is being phased out - return empty dict
        return {}
    
    async def get_user_theme_data(self, user_id: str, username: str = None) -> Dict[str, Any]:
        """Get theme system data (alias for get_theme_system_data)"""
        return await self.get_theme_system_data(user_id, username)
    
    async def save_theme_system_data(self, user_id: str, username: str, theme_data: Dict[str, Any]) -> bool:
        """Save theme system data - no longer saves anything as theme system is being phased out"""
        # Theme system is being phased out - do not save any data
        logger.info(f"Theme system save called for user {user_id} but not saving anything - theme system is being phased out")
        return True
   
    # JSON Data Methods (All Optimized)
    async def get_monsters_and_bosses(self) -> Dict[str, Any]:
        """Load monsters, bosses, and titans from separate JSON files and combine them"""
        try:
            # Load from separate files
            monsters = await self._load_json_optimized(self._file_paths['monsters'], {}, lazy=True)
            bosses = await self._load_json_optimized(self._file_paths['bosses'], {}, lazy=True)
            titans = await self._load_json_optimized(self._file_paths['titans'], {}, lazy=True)
            
            # Combine into the expected structure
            combined_data = {
                'rarity_colors': {},  # Will be populated from the first available file
                'monsters': monsters if isinstance(monsters, dict) else {},
                'bosses': bosses if isinstance(bosses, dict) else {},
                'titans': titans if isinstance(titans, dict) else {}
            }
            
            # Try to get rarity_colors from any file that has it
            for data in [monsters, bosses, titans]:
                if isinstance(data, dict) and 'rarity_colors' in data:
                    combined_data['rarity_colors'] = data['rarity_colors']
                    break
            
            return combined_data
            
        except Exception as e:
            logging.error(f"Error loading monsters and bosses from separate files: {e}")
            return {'rarity_colors': {}, 'monsters': {}, 'bosses': {}, 'titans': {}}

    async def save_monsters_and_bosses(self, data: Dict[str, Any]) -> bool:
        """Save to separate JSON files - splits the combined data"""
        try:
            # Split the data by type
            monsters_data = data.get('monsters', {})
            bosses_data = data.get('bosses', {})
            titans_data = data.get('titans', {})
            
            # Add rarity_colors to each file if it exists
            if 'rarity_colors' in data:
                for file_data in [monsters_data, bosses_data, titans_data]:
                    if file_data:  # Only add to non-empty files
                        file_data['rarity_colors'] = data['rarity_colors']
            
            # Save to separate files
            success = True
            if monsters_data:
                success &= await self._save_json_optimized(self._file_paths['monsters'], monsters_data)
            if bosses_data:
                success &= await self._save_json_optimized(self._file_paths['bosses'], bosses_data)
            if titans_data:
                success &= await self._save_json_optimized(self._file_paths['titans'], titans_data)
                
            return success
            
        except Exception as e:
            logging.error(f"Error saving monsters and bosses to separate files: {e}")
            return False
    
    async def get_monster(self, monster_id: str) -> Optional[Dict[str, Any]]:
        monsters = await self.get_monsters_and_bosses()
        return monsters.get(monster_id)
    
    async def add_monster(self, monster_id: str, monster_data: Dict[str, Any]) -> bool:
        monsters = await self.get_monsters_and_bosses()
        monsters[monster_id] = monster_data
        return await self.save_monsters_and_bosses(monsters)
    
    async def get_pets_level_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['pets_level'], {}, lazy=True)
    
    async def get_monsters_and_bosses_data(self) -> Dict[str, Any]:
        """Alias for get_monsters_and_bosses to maintain backward compatibility"""
        return await self.get_monsters_and_bosses()

    async def get_pet_equipment_data(self) -> Dict[str, Any]:
        """Load pet equipment data including chassis_plating, energy_cores, and utility_modules"""
        return await self._load_json_optimized(self._file_paths['pet_equipment'], {}, lazy=True)

    async def get_chassis_plating_by_rarity(self, rarity: str) -> Dict[str, Any]:
        """Get chassis plating items by rarity"""
        equipment_data = await self.get_pet_equipment_data()
        chassis_data = equipment_data.get('chassis_plating', {})
        return chassis_data.get('equipment', {}).get(rarity.lower(), {})

    async def get_energy_cores_by_rarity(self, rarity: str) -> Dict[str, Any]:
        """Get energy cores by rarity"""
        equipment_data = await self.get_pet_equipment_data()
        energy_data = equipment_data.get('energy_cores', {})
        return energy_data.get('equipment', {}).get(rarity.lower(), {})

    async def get_utility_modules_by_rarity(self, rarity: str) -> Dict[str, Any]:
        """Get utility modules by rarity"""
        equipment_data = await self.get_pet_equipment_data()
        utility_data = equipment_data.get('utility_modules', {})
        return utility_data.get('equipment', {}).get(rarity.lower(), {})

    async def get_all_pet_equipment_by_rarity(self, rarity: str) -> Dict[str, Dict[str, Any]]:
        """Get all pet equipment types (chassis_plating, energy_cores, utility_modules) by rarity"""
        return {
            'chassis_plating': await self.get_chassis_plating_by_rarity(rarity),
            'energy_cores': await self.get_energy_cores_by_rarity(rarity),
            'utility_modules': await self.get_utility_modules_by_rarity(rarity)
        }

    async def get_pet_equipment_item(self, item_type: str, rarity: str, item_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific pet equipment item by type, rarity, and ID"""
        equipment_data = await self.get_pet_equipment_data()
        type_data = equipment_data.get(item_type, {})
        return type_data.get('equipment', {}).get(rarity.lower(), {}).get(item_id)

    async def get_pet_equipment_by_type(self, item_type: str) -> Dict[str, Any]:
        """Get all pet equipment of a specific type across all rarities"""
        equipment_data = await self.get_pet_equipment_data()
        type_data = equipment_data.get(item_type, {})
        return type_data.get('equipment', {})

    async def save_pets_level_data(self, data: Dict[str, Any]) -> bool:
        return await self._save_json_optimized(self._file_paths['pets_level'], data)
    
    async def save_monsters_and_bosses_data(self, data: Dict[str, Any]) -> bool:
        return await self._save_json_optimized(self._file_paths['monsters_and_bosses'], data)

    # Pet XP Data Methods
    async def get_pet_xp_data(self) -> Dict[str, Any]:
        """Load pet XP level thresholds data"""
        return await self._load_json_optimized(self._file_paths['pet_xp'], {}, lazy=True)

    async def save_pet_xp_data(self, data: Dict[str, Any]) -> bool:
        """Save pet XP level thresholds data"""
        return await self._save_json_optimized(self._file_paths['pet_xp'], data)

    async def get_level_threshold(self, level: int) -> Optional[int]:
        """Get XP threshold for a specific level"""
        xp_data = await self.get_pet_xp_data()
        level_thresholds = xp_data.get('LEVEL_THRESHOLDS', {})
        return level_thresholds.get(str(level))

    async def get_all_level_thresholds(self) -> Dict[str, int]:
        """Get all level thresholds"""
        xp_data = await self.get_pet_xp_data()
        return xp_data.get('LEVEL_THRESHOLDS', {})

    # Pet Mission Data Methods
    async def get_pets_mission_data(self) -> Dict[str, Any]:
        """Load pet mission types and descriptions"""
        return await self._load_json_optimized(self._file_paths['pets_mission'], {}, lazy=True)

    async def save_pets_mission_data(self, data: Dict[str, Any]) -> bool:
        """Save pet mission types and descriptions"""
        return await self._save_json_optimized(self._file_paths['pets_mission'], data)

    async def get_mission_types(self) -> Dict[str, List[str]]:
        """Get all mission types (easy, medium, hard, etc.)"""
        mission_data = await self.get_pets_mission_data()
        return mission_data.get('MISSION_TYPES', {})

    async def get_missions_by_difficulty(self, difficulty: str) -> List[str]:
        """Get missions for a specific difficulty level"""
        mission_types = await self.get_mission_types()
        return mission_types.get(difficulty.lower(), [])

    async def get_random_mission(self, difficulty: str) -> Optional[str]:
        """Get a random mission for the specified difficulty"""
        missions = await self.get_missions_by_difficulty(difficulty)
        if missions:
            import random
            return random.choice(missions)
        return None

    # Pet Data Management Methods
    async def get_pet_data(self, user_id: str, username: str = None) -> Optional[Dict[str, Any]]:
        """Get a user's pet data from their user file with legacy migration"""
        user_data = await self.get_user_data(user_id, username)
        pet_data = user_data.get("pets", {}).get("pet_data")
        
        if pet_data:
            # Migrate legacy pet data if needed
            pet_data = await self._migrate_legacy_pet_data(pet_data)
            
        return pet_data

    async def save_pet_data(self, user_id: str, username: str, pet_data: Dict[str, Any]) -> bool:
        """Save a user's pet data to their user file"""
        # Ensure equipment format is migrated before saving
        pet_data = await self._migrate_equipment_format(pet_data)
        
        user_data = await self.get_user_data(user_id, username)
        if "pets" not in user_data:
            user_data["pets"] = {}
        user_data["pets"]["pet_data"] = pet_data
        return await self.save_user_data(user_id, username, user_data)

    async def delete_pet_data(self, user_id: str, username: str = None) -> bool:
        """Delete a user's pet data from their user file"""
        user_data = await self.get_user_data(str(user_id), username)
        if "pets" in user_data and "pet_data" in user_data["pets"]:
            del user_data["pets"]["pet_data"]
            return await self.save_user_data(str(user_id), username, user_data)
        return False

    # Pet Combiner Team Methods (Moved from theme system)
    async def add_user_to_pet_combiner_team(self, user_id: str, username: str, team_id: str, role: str, team_data: Dict[str, Any]) -> bool:
        """Add user to pet combiner team - moved from theme system to pet system"""
        user_data = await self.get_user_data(user_id, username)
        
        # Initialize pets section if needed
        if "pets" not in user_data:
            user_data["pets"] = {}
        
        # Initialize combiner team data
        if "combiner_teams" not in user_data["pets"]:
            user_data["pets"]["combiner_teams"] = {}
        
        # Efficient team management - remove from current team first
        current_team = user_data["pets"]["combiner_teams"].get("current_team")
        if current_team and current_team != team_id:
            await self.remove_user_from_pet_combiner_team(user_id, username, current_team)
        
        # Update team data
        teams = user_data["pets"]["combiner_teams"].setdefault("teams", [])
        if team_id not in teams:
            teams.append(team_id)
        
        user_data["pets"]["combiner_teams"].update({
            "current_team": team_id,
            "current_role": role.lower()
        })
        
        # Add to history
        history = user_data["pets"]["combiner_teams"].setdefault("history", [])
        if not any(h.get("team_id") == team_id for h in history):
            history.append({
                "team_id": team_id,
                "role": role.lower(),
                "joined_at": datetime.now().isoformat(),
                "team_data": team_data
            })
        
        return await self.save_user_data(user_id, username, user_data)
    
    async def remove_user_from_pet_combiner_team(self, user_id: str, username: str, team_id: str) -> bool:
        """Remove user from pet combiner team"""
        user_data = await self.get_user_data(user_id, username)
        
        if "pets" not in user_data or "combiner_teams" not in user_data["pets"]:
            return False
        
        teams = user_data["pets"]["combiner_teams"].get("teams", [])
        if team_id in teams:
            teams.remove(team_id)
        
        if user_data["pets"]["combiner_teams"].get("current_team") == team_id:
            user_data["pets"]["combiner_teams"]["current_team"] = None
            user_data["pets"]["combiner_teams"]["current_role"] = None
        
        return await self.save_user_data(user_id, username, user_data)
    
    async def get_user_pet_combiner_team(self, user_id: str, username: str = None) -> Optional[Dict[str, Any]]:
        """Get user pet combiner team"""
        user_data = await self.get_user_data(user_id, username)
        
        if "pets" not in user_data or "combiner_teams" not in user_data["pets"]:
            return None
        
        current_team = user_data["pets"]["combiner_teams"].get("current_team")
        if not current_team:
            return None
        
        # Find most recent team info
        history = user_data["pets"]["combiner_teams"].get("history", [])
        return next((h for h in reversed(history) if h.get("team_id") == current_team), None)

    async def _migrate_legacy_pet_data(self, pet_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate legacy pet data to include inventory and equipment fields"""
        # Check if migration is needed
        if "inventory" not in pet_data or "equipment" not in pet_data:
            # Create backup of original data
            pet_data.setdefault("_legacy_backup", pet_data.copy())
            
            # Ensure inventory exists
            if "inventory" not in pet_data:
                pet_data["inventory"] = []
            
            # Ensure equipment exists with proper structure
            if "equipment" not in pet_data:
                pet_data["equipment"] = {
                    "chassis_plating": None,
                    "energy_cores": None,
                    "utility_modules": None
                }
            elif not isinstance(pet_data["equipment"], dict):
                # Handle case where equipment might be in old format
                pet_data["equipment"] = {
                    "chassis_plating": None,
                    "energy_cores": None,
                    "utility_modules": None
                }
            
            # Ensure all required fields exist
            pet_data.setdefault("attack", 10)
            pet_data.setdefault("defense", 5)
            pet_data.setdefault("max_energy", 100)
            pet_data.setdefault("max_maintenance", 100)
            pet_data.setdefault("max_happiness", 100)
            
            # Migrate from old 'xp' field to 'experience' field if needed
            if "xp" in pet_data and "experience" not in pet_data:
                pet_data["experience"] = pet_data["xp"]
                del pet_data["xp"]
            
        # Always check for equipment format migration
        pet_data = await self._migrate_equipment_format(pet_data)
            
        return pet_data
    
    async def _migrate_equipment_format(self, pet_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate equipment format from old format (equipment_type, flattened stats) to new format (type, stat_bonus)"""
        inventory = pet_data.get("inventory", [])
        migrated_inventory = []
        inventory_changed = False
        
        for item in inventory:
            if isinstance(item, dict):
                # Check if item needs migration (has equipment_type instead of type)
                if "equipment_type" in item and "type" not in item:
                    # Create backup if not already exists
                    if "_equipment_backup" not in pet_data:
                        pet_data["_equipment_backup"] = inventory.copy()
                    
                    # Migrate the item
                    new_item = item.copy()
                    new_item["type"] = item["equipment_type"]
                    del new_item["equipment_type"]
                    
                    # Create stat_bonus object from flattened stats
                    stat_bonus = {}
                    for stat in ["attack", "defense", "energy", "maintenance", "happiness"]:
                        if stat in item:
                            stat_bonus[stat] = item[stat]
                    
                    if stat_bonus:
                        new_item["stat_bonus"] = stat_bonus
                        # Remove flattened stats that are now in stat_bonus
                        for stat in stat_bonus.keys():
                            new_item.pop(stat, None)
                    
                    migrated_inventory.append(new_item)
                    inventory_changed = True
                else:
                    # Item is already in correct format
                    migrated_inventory.append(item)
            else:
                # Non-equipment item, keep as is
                migrated_inventory.append(item)
        
        if inventory_changed:
            pet_data["inventory"] = migrated_inventory
            logging.info(f"Migrated equipment format for pet: {pet_data.get('name', 'Unknown')}")
        
        return pet_data

    async def get_all_pets_data(self) -> Dict[str, Dict[str, Any]]:
        """Get all pets data across all users (for admin/stats purposes)"""
        pets_data = {}
        users_dir = self.base_path

        if not users_dir.exists():
            return pets_data

        for user_file in users_dir.glob("*.json"):
            try:
                user_id = user_file.stem
                user_data = await self._load_json_optimized(user_file)
                pet_data = user_data.get("pets", {}).get("pet_data")
                if pet_data:
                    # Ensure migration happens when getting all pets
                    pet_data = await self._migrate_legacy_pet_data(pet_data)
                    pets_data[user_id] = pet_data
            except Exception as e:
                logging.error(f"Error loading pet data for user {user_file.stem}: {e}")

        return pets_data

    async def migrate_all_pet_data(self) -> Dict[str, Any]:
        """
        Migrate all existing pet data to include inventory and equipment fields
        Returns: Migration summary with counts
        """
        migration_summary = {
            "total_pets": 0,
            "migrated_pets": 0,
            "errors": [],
            "users_processed": []
        }
        
        try:
            users_dir = self.base_path
            if not users_dir.exists():
                return migration_summary

            for user_file in users_dir.glob("*.json"):
                user_id = user_file.stem
                try:
                    user_data = await self._load_json_optimized(user_file)
                    pet_data = user_data.get("pets", {}).get("pet_data")
                    
                    if pet_data:
                        migration_summary["total_pets"] += 1
                        
                        # Check if migration is needed
                        needs_migration = (
                            "inventory" not in pet_data or 
                            "equipment" not in pet_data or
                            not isinstance(pet_data.get("equipment"), dict)
                        )
                        
                        if needs_migration:
                            # Migrate the pet data
                            migrated_pet = await self._migrate_legacy_pet_data(pet_data)
                            user_data["pets"]["pet_data"] = migrated_pet
                            
                            # Save the migrated data
                            username = user_data.get("username", f"user_{user_id}")
                            success = await self.save_pet_data(user_id, username, migrated_pet)
                            
                            if success:
                                migration_summary["migrated_pets"] += 1
                                migration_summary["users_processed"].append(user_id)
                            else:
                                migration_summary["errors"].append(f"Failed to save migrated data for {user_id}")
                        
                except Exception as e:
                    migration_summary["errors"].append(f"Error processing {user_id}: {str(e)}")
                    logging.error(f"Error migrating pet data for {user_id}: {e}")

            logging.info(f"Pet data migration completed: {migration_summary}")
            return migration_summary
            
        except Exception as e:
            migration_summary["errors"].append(f"Migration failed: {str(e)}")
            logging.error(f"Pet data migration failed: {e}")
            return migration_summary

    async def get_pet_level_info(self, pet_type: str) -> Optional[Dict[str, Any]]:
        pets_data = await self.get_pets_level_data()
        return pets_data.get(pet_type)

    async def calculate_pet_level(self, pet: Dict[str, Any]) -> int:
        """
        Calculate pet level based on total experience.
        This method calculates the current level by comparing total experience
        against level thresholds, similar to the RPG system's level calculation.
        
        Args:
            pet: Pet data dictionary containing experience information
            
        Returns:
            Current pet level (1-500)
        """
        try:
            # Get total experience from the pet data (handle both xp and experience fields)
            total_experience = pet.get('experience', pet.get('xp', 0))
            
            # Load level thresholds
            from .EnergonPets.pet_levels import get_level_experience
            
            level = 1
            while level < 500:
                xp_needed = get_level_experience(level)
                if xp_needed == 0 or total_experience < xp_needed:
                    break
                total_experience -= xp_needed
                level += 1
            
            return min(level, 500)
            
        except Exception as e:
            logging.error(f"Error calculating pet level: {e}")
            return pet.get('level', 1)  # Fallback to current level or 1

    # Recruitment Data
    async def get_recruit_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['recruit'], {}, lazy=True)

    async def save_recruit_data(self, data: Dict[str, Any]) -> bool:
        return await self._save_json_optimized(self._file_paths['recruit'], data)

    async def get_recruit_entry(self, recruit_id: str) -> Optional[Dict[str, Any]]:
        recruits = await self.get_recruit_data()
        return recruits.get(recruit_id)

    async def add_recruit_entry(self, recruit_id: str, recruit_data: Dict[str, Any]) -> bool:
        recruits = await self.get_recruit_data()
        recruits[recruit_id] = recruit_data
        return await self.save_recruit_data(recruits)

    # Bot Logs Data
    async def get_bot_logs(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['bot_logs'], {"logs": []}, lazy=True)

    async def save_bot_logs(self, data: Dict[str, Any]) -> bool:
        return await self._save_json_optimized(self._file_paths['bot_logs'], data)

    async def add_bot_log(self, log_entry: Dict[str, Any]) -> bool:
        logs = await self.get_bot_logs()
        logs.setdefault("logs", []).append(log_entry)
        return await self.save_bot_logs(logs)

    # CyberCoin Market Data
    async def get_cybercoin_market_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['cybercoin_market_data'], 
                                           {"market_data": {}, "last_updated": None}, lazy=True)

    async def save_cybercoin_market_data(self, data: Dict[str, Any]) -> bool:
        return await self._save_json_optimized(self._file_paths['cybercoin_market_data'], data)

    # CyberCoin Transaction Functions
    async def get_cybercoin_summary(self, user_id: str) -> dict:
        """Get comprehensive CyberCoin summary for a user."""
        try:
            user_data = await self.get_user_data(user_id)
            cybercoin_data = user_data.get("cybercoin", {})
            
            # Ensure all required fields exist with defaults
            portfolio = cybercoin_data.get("portfolio", {
                "total_coins": 0.0,
                "total_invested": 0.0,
                "total_sold": 0.0,
                "total_profit": 0.0,
                "transactions": []
            })
            
            return {
                "portfolio": portfolio,
                "last_updated": cybercoin_data.get("last_updated", None)
            }
        except Exception as e:
            logging.error(f"Error getting cybercoin summary for {user_id}: {e}")
            return {
                "portfolio": {
                    "total_coins": 0.0,
                    "total_invested": 0.0,
                    "total_sold": 0.0,
                    "total_profit": 0.0,
                    "transactions": []
                },
                "last_updated": None
            }

    def record_cybercoin_purchase(self, user_id: str, amount_invested: float, coins_received: float, price_per_coin: float) -> None:
        """Record a CyberCoin purchase transaction (sync wrapper)."""
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                # If we're already in an event loop, schedule fire-and-forget
                if loop.is_running():
                    asyncio.create_task(self._record_cybercoin_purchase_async(user_id, amount_invested, coins_received, price_per_coin))
                else:
                    asyncio.run(self._record_cybercoin_purchase_async(user_id, amount_invested, coins_received, price_per_coin))
            except RuntimeError:
                # No running loop; safe to run directly
                asyncio.run(self._record_cybercoin_purchase_async(user_id, amount_invested, coins_received, price_per_coin))
        except Exception as e:
            logging.error(f"Error recording cybercoin purchase for {user_id}: {e}")

    async def _record_cybercoin_purchase_async(self, user_id: str, amount_invested: float, coins_received: float, price_per_coin: float) -> None:
        """Async implementation to record a CyberCoin purchase."""
        try:
            user_data = await self.get_user_data(user_id)
            cybercoin_data = user_data.setdefault("cybercoin", {})
            portfolio = cybercoin_data.setdefault("portfolio", {
                "total_coins": 0.0,
                "total_invested": 0.0,
                "total_sold": 0.0,
                "total_profit": 0.0,
                "transactions": []
            })
            
            # Update portfolio
            portfolio["total_coins"] += coins_received
            portfolio["total_invested"] += amount_invested
            
            # Add transaction record
            transaction = {
                "type": "buy",
                "amount": amount_invested,
                "coins": coins_received,
                "price_per_coin": price_per_coin,
                "timestamp": datetime.utcnow().isoformat()
            }
            portfolio["transactions"].append(transaction)
            
            # Keep only last 50 transactions
            if len(portfolio["transactions"]) > 50:
                portfolio["transactions"] = portfolio["transactions"][-50:]
            
            cybercoin_data["last_updated"] = datetime.utcnow().isoformat()
            
            # Save user data
            await self.save_user_data(user_id, None, user_data)
            
        except Exception as e:
            logging.error(f"Error in _record_cybercoin_purchase_async for {user_id}: {e}")

    def record_cybercoin_sale(self, user_id: str, coins_sold: float, sale_amount: float, price_per_coin: float) -> dict:
        """Record a CyberCoin sale transaction (sync wrapper)."""
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    # In a running loop, schedule async task and return acknowledgment
                    asyncio.create_task(self._record_cybercoin_sale_async(user_id, coins_sold, sale_amount, price_per_coin))
                    return {"success": True, "scheduled": True}
                else:
                    return asyncio.run(self._record_cybercoin_sale_async(user_id, coins_sold, sale_amount, price_per_coin))
            except RuntimeError:
                # No running loop; safe to run and get result
                return asyncio.run(self._record_cybercoin_sale_async(user_id, coins_sold, sale_amount, price_per_coin))
        except Exception as e:
            logging.error(f"Error recording cybercoin sale for {user_id}: {e}")
            return {"success": False, "error": str(e)}

    async def _record_cybercoin_sale_async(self, user_id: str, coins_sold: float, sale_amount: float, price_per_coin: float) -> dict:
        """Async implementation to record a CyberCoin sale."""
        try:
            user_data = await self.get_user_data(user_id)
            cybercoin_data = user_data.setdefault("cybercoin", {})
            portfolio = cybercoin_data.setdefault("portfolio", {
                "total_coins": 0.0,
                "total_invested": 0.0,
                "total_sold": 0.0,
                "total_profit": 0.0,
                "transactions": []
            })
            
            # Check if user has enough coins
            if portfolio["total_coins"] < coins_sold:
                return {"success": False, "error": "Insufficient coins"}
            
            # Calculate profit/loss
            avg_buy_price = portfolio["total_invested"] / portfolio["total_coins"] if portfolio["total_coins"] > 0 else 0
            profit_per_coin = price_per_coin - avg_buy_price
            total_profit = profit_per_coin * coins_sold
            
            # Update portfolio
            portfolio["total_coins"] -= coins_sold
            portfolio["total_sold"] += sale_amount
            portfolio["total_profit"] += total_profit
            portfolio["total_invested"] -= (avg_buy_price * coins_sold)  # Reduce invested amount
            
            # Add transaction record
            transaction = {
                "type": "sell",
                "amount": sale_amount,
                "coins": coins_sold,
                "price_per_coin": price_per_coin,
                "profit": total_profit,
                "timestamp": datetime.utcnow().isoformat()
            }
            portfolio["transactions"].append(transaction)
            
            # Keep only last 50 transactions
            if len(portfolio["transactions"]) > 50:
                portfolio["transactions"] = portfolio["transactions"][-50:]
            
            cybercoin_data["last_updated"] = datetime.utcnow().isoformat()
            
            # Save user data
            await self.save_user_data(user_id, None, user_data)
            
            return {
                "success": True,
                "sale_amount": sale_amount,
                "profit": total_profit,
                "remaining_coins": portfolio["total_coins"]
            }
            
        except Exception as e:
            logging.error(f"Error in _record_cybercoin_sale_async for {user_id}: {e}")
            return {"success": False, "error": str(e)}

    def get_cybercoin_portfolio(self, user_id: str) -> dict:
        """Get user's CyberCoin portfolio."""
        try:
            # This is a synchronous wrapper for the async method
            import asyncio
            result = asyncio.run(self.get_cybercoin_summary(user_id))
            return result.get("portfolio", {
                "total_coins": 0.0,
                "total_invested": 0.0,
                "total_sold": 0.0,
                "total_profit": 0.0,
                "transactions": []
            })
        except Exception as e:
            logging.error(f"Error getting cybercoin portfolio for {user_id}: {e}")
            return {
                "total_coins": 0.0,
                "total_invested": 0.0,
                "total_sold": 0.0,
                "total_profit": 0.0,
                "transactions": []
            }



    # Backward compatibility methods

    async def get_what_talk_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['what_talk'], {}, lazy=True)



    async def get_jokes_talk_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['jokes_talk'], {}, lazy=True)

    async def get_grump_talk_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['grump_talk'], {}, lazy=True)

    async def get_blessings_talk_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['blessings_talk'], {}, lazy=True)

    async def get_user_lore_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['user_lore'], {}, lazy=True)

    async def save_user_lore_data(self, data: Dict[str, Any]) -> bool:
        return await self._save_json_optimized(self._file_paths['user_lore'], data)

    async def get_roasts_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['roasts'], {}, lazy=True)

    async def save_roasts_data(self, data: Dict[str, Any]) -> bool:
        return await self._save_json_optimized(self._file_paths['roasts'], data)
    
    # Trivia Data Methods
    async def get_trivia_transformers_culture(self) -> List[Dict[str, Any]]:
        """Get Transformers culture trivia questions"""
        return await self._load_json_optimized(self._file_paths['trivia_transformers_culture'], [], lazy=True)
    
    async def save_trivia_transformers_culture(self, data: List[Dict[str, Any]]) -> bool:
        """Save Transformers culture trivia questions"""
        return await self._save_json_optimized(self._file_paths['trivia_transformers_culture'], data)
    
    async def get_trivia_transformers_characters(self) -> List[Dict[str, Any]]:
        """Get Transformers characters trivia questions"""
        return await self._load_json_optimized(self._file_paths['trivia_transformers_characters'], [], lazy=True)
    
    async def save_trivia_transformers_characters(self, data: List[Dict[str, Any]]) -> bool:
        """Save Transformers characters trivia questions"""
        return await self._save_json_optimized(self._file_paths['trivia_transformers_characters'], data)
    
    async def get_trivia_transformers_factions(self) -> List[Dict[str, Any]]:
        """Get Transformers factions trivia questions"""
        return await self._load_json_optimized(self._file_paths['trivia_transformers_factions'], [], lazy=True)
    
    async def save_trivia_transformers_factions(self, data: List[Dict[str, Any]]) -> bool:
        """Save Transformers factions trivia questions"""
        return await self._save_json_optimized(self._file_paths['trivia_transformers_factions'], data)
    
    async def get_trivia_transformers_movies(self) -> List[Dict[str, Any]]:
        """Get Transformers movies trivia questions"""
        return await self._load_json_optimized(self._file_paths['trivia_transformers_movies'], [], lazy=True)
    
    async def save_trivia_transformers_movies(self, data: List[Dict[str, Any]]) -> bool:
        """Save Transformers movies trivia questions"""
        return await self._save_json_optimized(self._file_paths['trivia_transformers_movies'], data)
    
    async def get_trivia_transformers_shows(self) -> List[Dict[str, Any]]:
        """Get Transformers shows trivia questions"""
        return await self._load_json_optimized(self._file_paths['trivia_transformers_shows'], [], lazy=True)
    
    async def save_trivia_transformers_shows(self, data: List[Dict[str, Any]]) -> bool:
        """Save Transformers shows trivia questions"""
        return await self._save_json_optimized(self._file_paths['trivia_transformers_shows'], data)
    
    async def get_all_trivia_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all trivia data from all categories"""
        return {
            'culture': await self.get_trivia_transformers_culture(),
            'characters': await self.get_trivia_transformers_characters(),
            'factions': await self.get_trivia_transformers_factions(),
            'movies': await self.get_trivia_transformers_movies(),
            'shows': await self.get_trivia_transformers_shows()
        }
    
    async def get_random_trivia_question(self, category: str = None) -> Optional[Dict[str, Any]]:
        """Get a random trivia question from specified category or all categories"""
        if category:
            # Get from specific category
            category_map = {
                'culture': await self.get_trivia_transformers_culture(),
                'characters': await self.get_trivia_transformers_characters(),
                'factions': await self.get_trivia_transformers_factions(),
                'movies': await self.get_trivia_transformers_movies(),
                'shows': await self.get_trivia_transformers_shows()
            }
            if category in category_map:
                questions = category_map[category]
                if questions:
                    question = random.choice(questions)
                    if isinstance(question, dict):
                        question_copy = question.copy()
                        question_copy['selected_category'] = category
                        return question_copy
                    return question
        else:
            # Get from all categories
            all_trivia = await self.get_all_trivia_data()
            all_questions = []
            for cat_name, questions in all_trivia.items():
                for question in questions:
                    if isinstance(question, dict):
                        question_copy = question.copy()
                        question_copy['selected_category'] = cat_name
                        all_questions.append(question_copy)
                    else:
                        all_questions.append(question)
            return random.choice(all_questions) if all_questions else None
        
        return None
    
    # Utility Methods
    async def reload_all_json_data(self) -> bool:
        """Clear all caches"""
        self._cache.clear()
        self._cache_timestamps.clear()
        self._cache_locks.clear()
        return True
    
    async def get_all_json_data(self) -> Dict[str, Any]:
        """Get all JSON data for debugging - optimized for all file types"""
        return {
            "monsters": await self._load_json_optimized(self._file_paths['monsters'], {}, lazy=True),
            "bosses": await self._load_json_optimized(self._file_paths['bosses'], {}, lazy=True),
            "titans": await self._load_json_optimized(self._file_paths['titans'], {}, lazy=True),
            "pets_level": await self.get_pets_level_data(),
            "recruit": await self.get_recruit_data(),
            "bot_logs": await self.get_bot_logs(),
            "cybercoin_market_data": await self.get_cybercoin_market_data(),
            
            # Random talk data
            "what_talk": await self.get_what_talk_data(),
            "jokes_talk": await self.get_jokes_talk_data(),
            "grump_talk": await self.get_grump_talk_data(),
            "blessings_talk": await self.get_blessings_talk_data(),
            "user_lore": await self.get_user_lore_data(),

            # Zodiac data
            "astrology": await self.get_western_astrology(),
            "chinese_astrology": await self.get_chinese_astrology(),
            "primal_astrology": await self.get_primal_astrology()
        }
    
    async def get_energon_data(self, player_id: str, username: str = None) -> Dict[str, Any]:
        """Get energon data for a player - unified across all systems"""
        try:
            user_data = await self.get_user_data(player_id, username)
            energon_data = user_data.get("energon", {})
            
            # Ensure all required fields exist
            default_data = self._get_default_energon_data()
            for key, default_value in default_data.items():
                if key not in energon_data:
                    energon_data[key] = default_value
            
            return energon_data
            
        except Exception as e:
            logging.error(f"Error getting energon data for {player_id}: {e}")
            return self._get_default_energon_data()

    async def save_energon_data(self, player_id: str, energon_data: Dict[str, Any], username: str = None) -> bool:
        """Save energon data for a player"""
        try:
            user_data = await self.get_user_data(player_id, username)
            user_data["energon"] = energon_data
            return await self.save_user_data(player_id, username or user_data.get("username"), user_data)
            
        except Exception as e:
            logging.error(f"Error saving energon data for {player_id}: {e}")
            return False

    async def update_energon_stat(self, player_id: str, stat_name: str, value: Any, username: str = None) -> bool:
        """Update a specific energon stat for a player - maintains backward compatibility"""
        try:
            energon_data = await self.get_energon_data(player_id, username)
            energon_data[stat_name] = value
            return await self.save_energon_data(player_id, energon_data, username)
        except Exception as e:
            logging.error(f"Error updating energon stat {stat_name} for {player_id}: {e}")
            return False

    async def get_energon_stats(self, player_id: str, username: str = None) -> Dict[str, Any]:
        """Get all energon stats for a player - backward compatibility"""
        return await self.get_energon_data(player_id, username)

    async def get_energon_game_state(self, channel_id: str = None) -> Dict[str, Any]:
        """Get energon game state for a channel or global state"""
        try:
            if channel_id is None:
                # Get global energon game state from Global Saves
                return await self._load_json_optimized(
                    self._file_paths['energon_game'], 
                    self._get_default_energon_game_state()
                )
            else:
                # Get per-channel game state (still use user data for channel-specific data)
                user_data = await self.get_user_data(str(channel_id), f"channel_{channel_id}")
                return user_data.get('energon_game_state', self._get_default_energon_game_state())
        except Exception as e:
            logging.error(f"Error getting energon game state for {channel_id}: {e}")
            return self._get_default_energon_game_state()

    async def get_energon_game(self, channel_id: str = None) -> Dict[str, Any]:
        """Alias for get_energon_game_state for consistency with file naming"""
        return await self.get_energon_game_state(channel_id)

    async def save_energon_game_state(self, channel_id: str = None, data: Dict[str, Any] = None) -> bool:
        """Save energon game state for a channel or global state"""
        try:
            if channel_id is None:
                # Save global energon game state to Global Saves
                return await self._save_json_optimized(self._file_paths['energon_game'], data)
            else:
                # Save per-channel game state (still use user data for channel-specific data)
                try:
                    user_data = await self.get_user_data(str(channel_id), f"channel_{channel_id}")
                except:
                    user_data = {}
                
                user_data['energon_game_state'] = data
                return await self.save_user_data(str(channel_id), f"channel_{channel_id}", user_data)
        except Exception as e:
            logging.error(f"Error saving energon game state for {channel_id}: {e}")
            return False

    async def get_global_energon_game_state(self) -> Dict[str, Any]:
        """Get global energon game state (backward compatibility)"""
        return await self.get_energon_game_state()

    async def save_global_energon_game_state(self, data: Dict[str, Any]) -> bool:
        """Save global energon game state (backward compatibility)"""
        return await self.save_energon_game_state(None, data)

    def _get_default_energon_data(self) -> Dict[str, Any]:
        """Get optimized default energon data structure - unified across all game systems"""
        return {
            'energon': 0,           # Current game energon (in-game balance)
            'energon_bank': 0,      # Banked energon (persistent balance)
            'total_earned': 0,      # Lifetime energon earned
            'total_spent': 0,       # Lifetime energon spent
            'games_played': 0,      # Total games played across all systems
            'games_won': 0,         # Total games won
            'games_lost': 0,        # Total games lost
            'last_activity': None,  # Last energon activity timestamp
            'daily_energon_claimed': False,
            'last_daily_claim': None,
            'streak': 0,
            'cybercoins': 0.0,
            'pet_bonus': 0,
            'in_energon_rush': False,
            'pet_energon_earned': 0,     # Energon earned through pet activities
            'battle_energon_earned': 0,  # Energon earned through battles
            'search_energon_earned': 0,   # Energon earned through searches (positive only)
            'pet_search_helps': 0,        # Number of times pet helped in searches
            'pet_search_energon': 0,      # Energon won when pet was present during search
            'slots_energon_earned': 0,    # Energon earned through slots
            'challenge_energon_earned': 0  # Energon earned through challenges
        }

    def _get_default_energon_game_state(self) -> Dict[str, Any]:
        """Get optimized energon game state structure"""
        return {
            'game_data': {},           # Active game sessions by player
            'challenges': {},          # Active challenges
            'cooldowns': {},           # Player cooldowns
            'global_stats': {
                'total_games': 0,
                'total_energon_won': 0,
                'total_energon_lost': 0,
                'active_players': [],
                'last_game_end': None,
                'daily_reset': None
            },
            'leaderboard': {            # Cross-system leaderboard
                'daily': {},
                'weekly': {},
                'all_time': {}
            },
            'system_status': {        # System health tracking
                'last_cleanup': None,
                'active_games': 0,
                'total_players': 0
            },
            'last_updated': None
        }

    async def get_energon_summary(self, player_id: str, username: str = None) -> Dict[str, Any]:
        """Optimized energon summary with concurrent data loading"""
        try:
            energon_data = await self.get_energon_data(player_id, username)
            
            # Pre-calculate values to reduce lookups
            game_energon = energon_data.get('energon', 0)
            banked_energon = energon_data.get('energon_bank', 0)
            games_played = energon_data.get('games_played', 0)
            games_won = energon_data.get('games_won', 0)
            
            return {
                'current_balance': {
                    'game_energon': game_energon,
                    'banked_energon': banked_energon,
                    'total_energon': game_energon + banked_energon
                },
                'lifetime_stats': {
                    'total_earned': energon_data.get('total_earned', 0),
                    'total_spent': energon_data.get('total_spent', 0),
                    'games_played': games_played,
                    'win_rate': (games_won / games_played * 100) if games_played > 0 else 0.0
                },
                'source_breakdown': {
                    'pet_earnings': energon_data.get('pet_energon_earned', 0),
                    'battle_earnings': energon_data.get('battle_energon_earned', 0),
                    'search_earnings': energon_data.get('search_energon_earned', 0),
                    'slots_earnings': energon_data.get('slots_energon_earned', 0),
                    'challenge_earnings': energon_data.get('challenge_energon_earned', 0),
                    'pet_search_helps': energon_data.get('pet_search_helps', 0),
                    'pet_search_energon': energon_data.get('pet_search_energon', 0)
                },
                'last_activity': energon_data.get('last_activity')
            }
            
        except Exception as e:
            logging.error(f"Error getting energon summary for {player_id}: {e}")
            return {}

    async def cleanup_inactive_data(self, days_inactive: int = 30) -> int:
        """Optimized cleanup for inactive player data"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_inactive)
            cleaned_count = 0
            
            # Use pathlib for efficient file operations
            user_files = list(self.base_path.glob("*.json"))
            
            # Process files in batches for better performance
            batch_size = 50
            for i in range(0, len(user_files), batch_size):
                batch = user_files[i:i+batch_size]
                
                # Process batch concurrently
                tasks = []
                for file_path in batch:
                    user_id = file_path.stem
                    if user_id not in ["energon_global", "energon_system"]:
                        tasks.append(self._cleanup_single_user(user_id, cutoff_date))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                cleaned_count += sum(1 for r in results if r is True)
            
            return cleaned_count
            
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
            return 0
    
    async def shutdown(self):
        """Gracefully shutdown the UserDataManager and cleanup resources"""
        try:
            logging.info("Initiating UserDataManager shutdown...")
            
            # Signal shutdown to background tasks
            self._shutdown_event.set()
            
            # Cancel all alliance auto-clear tasks
            await self.cancel_all_alliance_auto_clears()
            
            # Shutdown thread pool
            self._thread_pool.shutdown(wait=True, cancel_futures=True)
            
            # Clear all caches
            self._cache.clear()
            self._cache_timestamps.clear()
            self._cache_locks.clear()
            
            logging.info("UserDataManager shutdown completed successfully")
            
        except Exception as e:
            logging.error(f"Error during UserDataManager shutdown: {e}")
            raise
    
    async def _cleanup_single_user(self, user_id: str, cutoff_date: datetime) -> bool:
        """Clean up a single user's inactive data"""
        try:
            energon_data = await self.get_energon_data(user_id)
            last_activity = energon_data.get('last_activity')
            
            if last_activity:
                last_activity_date = datetime.fromisoformat(last_activity)
                if last_activity_date < cutoff_date:
                    # Clean only game state, preserve balances
                    energon_data.update({
                        'in_energon_rush': False,
                        'daily_energon_claimed': False,
                        'last_daily_claim': None
                    })
                    
                    await self.save_energon_data(user_id, energon_data, None)
                    return True
            
            return False
            
        except Exception:
            return False


    
    async def batch_save_user_data(self, user_updates: List[Tuple[str, str, Dict[str, Any]]]) -> List[bool]:
        """Batch save multiple user data files for better performance"""
        tasks = []
        for user_id, username, data in user_updates:
            tasks.append(self.save_user_data(user_id, username, data))
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def batch_load_user_data(self, user_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Batch load multiple user data files"""
        tasks = []
        for user_id in user_ids:
            tasks.append(self.get_user_data(user_id))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {user_id: result for user_id, result in zip(user_ids, results) if not isinstance(result, Exception)}
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate file hash for integrity checking"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except (OSError, FileNotFoundError):
            return ""
    
    async def verify_file_integrity(self, file_key: str) -> bool:
        """Verify file integrity using checksums"""
        if file_key not in self._file_paths:
            return False
        
        file_path = self._file_paths[file_key]
        if not file_path.exists():
            return False
        
        try:
            # Try to load and parse the JSON
            await self._load_json_optimized(file_path)
            return True
        except Exception:
            return False
    
    async def create_compressed_backup(self, file_key: str) -> bool:
        """Create compressed backup of important files"""
        if file_key not in self._file_paths:
            return False
        
        file_path = self._file_paths[file_key]
        if not file_path.exists():
            return False
        
        try:
            backup_path = file_path.with_suffix('.backup.gz')
            loop = asyncio.get_event_loop()
            
            await loop.run_in_executor(
                self._thread_pool,
                self._create_compressed_file,
                file_path,
                backup_path
            )
            return True
        except Exception as e:
            logging.error(f"Backup creation failed for {file_key}: {e}")
            return False
    
    def _create_compressed_file(self, source_path: Path, dest_path: Path):
        """Thread-safe compressed file creation"""
        with open(source_path, 'rb') as f_in:
            with gzip.open(dest_path, 'wb') as f_out:
                f_out.write(f_in.read())
    
    def _create_backup(self, file_path: Path) -> bool:
        """Create a backup of the file with timestamp"""
        try:
            if not file_path.exists():
                return False
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_{timestamp}.backup{file_path.suffix}"
            backup_path = file_path.parent / "backups" / backup_name
            
            # Ensure backup directory exists
            backup_path.parent.mkdir(exist_ok=True)
            
            # Create backup
            import shutil
            shutil.copy2(file_path, backup_path)
            
            # Cleanup old backups
            self._cleanup_old_backups(file_path)
            
            return True
        except Exception as e:
            logging.error(f"Failed to create backup for {file_path}: {e}")
            return False
    
    def _cleanup_old_backups(self, file_path: Path):
        """Remove old backup files, keeping only the most recent ones"""
        try:
            backup_dir = file_path.parent / "backups"
            if not backup_dir.exists():
                return
            
            # Find all backup files for this specific file
            pattern = f"{file_path.stem}_*.backup{file_path.suffix}"
            backup_files = list(backup_dir.glob(pattern))
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Keep only the most recent backups
            for old_backup in backup_files[self._max_backup_files:]:
                try:
                    old_backup.unlink()
                except Exception as e:
                    logging.warning(f"Failed to remove old backup {old_backup}: {e}")
        except Exception as e:
            logging.error(f"Failed to cleanup old backups for {file_path}: {e}")
    
    def _restore_from_backup(self, file_path: Path) -> bool:
        """Restore file from the most recent backup"""
        try:
            backup_dir = file_path.parent / "backups"
            if not backup_dir.exists():
                return False
            
            # Find the most recent backup
            pattern = f"{file_path.stem}_*.backup{file_path.suffix}"
            backup_files = list(backup_dir.glob(pattern))
            
            if not backup_files:
                return False
            
            # Get the most recent backup
            latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
            
            # Restore from backup
            import shutil
            shutil.copy2(latest_backup, file_path)
            
            logging.info(f"Successfully restored {file_path} from backup {latest_backup}")
            self._metrics['recovery_attempts'] += 1
            return True
        except Exception as e:
            logging.error(f"Failed to restore {file_path} from backup: {e}")
            return False
    
    async def validate_data_integrity(self, file_path: Path, data: Any) -> bool:
        """Comprehensive data integrity validation"""
        try:
            # Basic structure validation
            if data is None:
                return False
            
            # JSON serialization test
            try:
                json.dumps(data)
            except (TypeError, ValueError) as e:
                logging.error(f"Data serialization validation failed for {file_path}: {e}")
                return False
            
            # Size validation (prevent extremely large files)
            data_str = json.dumps(data)
            if len(data_str) > 50 * 1024 * 1024:  # 50MB limit
                logging.warning(f"Data size exceeds limit for {file_path}: {len(data_str)} bytes")
                return False
            
            # Structure-specific validation
            if isinstance(data, dict):
                # Check for required fields based on file type
                if 'user_data' in str(file_path):
                    required_fields = ['user_id', 'username']
                    if not all(field in data for field in required_fields):
                        logging.error(f"Missing required fields in user data: {file_path}")
                        return False
                
                # Check for circular references
                try:
                    json.dumps(data)
                except ValueError as e:
                    if "circular reference" in str(e).lower():
                        logging.error(f"Circular reference detected in {file_path}")
                        return False
            
            return True
        except Exception as e:
            logging.error(f"Data integrity validation failed for {file_path}: {e}")
            return False
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """Comprehensive system health check for online hosting"""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'metrics': self._metrics.copy(),
            'network_status': {
                'circuit_breaker_open': self._network_manager.is_circuit_open,
                'connection_failures': self._network_manager.connection_failures,
                'last_failure': self._network_manager.last_failure_time.isoformat() if self._network_manager.last_failure_time else None
            }
        }
        
        try:
            # Check file system access
            test_file = self.base_path / "health_check.tmp"
            try:
                test_file.write_text("health_check")
                test_file.unlink()
                health_status['checks']['filesystem'] = 'ok'
            except Exception as e:
                health_status['checks']['filesystem'] = f'error: {e}'
                health_status['status'] = 'degraded'
            
            # Check cache performance
            cache_hit_rate = 0
            total_cache_ops = self._metrics['cache_hits'] + self._metrics['cache_misses']
            if total_cache_ops > 0:
                cache_hit_rate = self._metrics['cache_hits'] / total_cache_ops
            
            health_status['checks']['cache_performance'] = {
                'hit_rate': cache_hit_rate,
                'status': 'ok' if cache_hit_rate > 0.7 else 'warning'
            }
            
            # Check error rates
            total_ops = self._metrics['reads'] + self._metrics['writes']
            error_rate = 0
            if total_ops > 0:
                error_rate = self._metrics['errors'] / total_ops
            
            health_status['checks']['error_rate'] = {
                'rate': error_rate,
                'status': 'ok' if error_rate < 0.05 else 'warning' if error_rate < 0.1 else 'critical'
            }
            
            # Check critical file availability
            critical_files_status = {}
            for file_key, file_path in self.json_files.items():
                try:
                    if file_path.exists():
                        critical_files_status[file_key] = 'ok'
                    else:
                        critical_files_status[file_key] = 'missing'
                        health_status['status'] = 'degraded'
                except Exception as e:
                    critical_files_status[file_key] = f'error: {e}'
                    health_status['status'] = 'degraded'
            
            health_status['checks']['critical_files'] = critical_files_status
            
            # Overall status determination
            if health_status['status'] == 'healthy':
                if self._network_manager.is_circuit_open or error_rate > 0.05:
                    health_status['status'] = 'degraded'
            
        except Exception as e:
            health_status['status'] = 'critical'
            health_status['error'] = str(e)
            logging.error(f"Health check failed: {e}")
        
        return health_status
    
    async def optimize_for_high_load(self) -> Dict[str, Any]:
        """Optimize system configuration for high-load online hosting"""
        optimization_results = {
            'cache_optimizations': {},
            'performance_improvements': {},
            'resource_management': {}
        }
        
        try:
            # Increase cache size for high load
            old_cache_size = self._max_cache_size
            self._max_cache_size = min(self._max_cache_size * 2, 10000)
            optimization_results['cache_optimizations']['cache_size_increased'] = {
                'old': old_cache_size,
                'new': self._max_cache_size
            }
            
            # Reduce cache TTL for more frequent updates
            old_cache_ttl = self._cache_ttl
            self._cache_ttl = max(self._cache_ttl * 0.8, 300)  # Minimum 5 minutes
            optimization_results['cache_optimizations']['cache_ttl_optimized'] = {
                'old': old_cache_ttl,
                'new': self._cache_ttl
            }
            
            # Optimize network resilience for high load
            self._network_manager.circuit_breaker_threshold = min(self._network_manager.circuit_breaker_threshold + 2, 10)
            self._network_manager.circuit_breaker_timeout = max(self._network_manager.circuit_breaker_timeout * 0.7, 30)
            
            optimization_results['performance_improvements']['network_resilience'] = {
                'circuit_breaker_threshold': self._network_manager.circuit_breaker_threshold,
                'circuit_breaker_timeout': self._network_manager.circuit_breaker_timeout
            }
            
            # Enable more aggressive caching for critical files
            critical_files = ['user_data', 'energon_data', 'pet_data']
            for file_key in critical_files:
                if file_key in self.json_files:
                    cache_key = self._get_cache_key(self.json_files[file_key])
                    if cache_key not in self._cache:
                        # Pre-load critical files
                        await self._load_json_optimized(self.json_files[file_key], {})
            
            optimization_results['performance_improvements']['critical_files_preloaded'] = len(critical_files)
            
            # Resource management optimizations
            optimization_results['resource_management']['max_concurrent_operations'] = 50
            optimization_results['resource_management']['memory_optimization'] = 'enabled'
            
            logging.info(f"High-load optimizations applied: {optimization_results}")
            
        except Exception as e:
            optimization_results['error'] = str(e)
            logging.error(f"Failed to apply high-load optimizations: {e}")
        
        return optimization_results
    

    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get detailed cache performance statistics"""
        total_ops = self._metrics['cache_hits'] + self._metrics['cache_misses']
        hit_rate = (self._metrics['cache_hits'] / total_ops * 100) if total_ops > 0 else 0
        
        return {
            'cache_size': len(self._cache),
            'max_cache_size': self._max_cache_size,
            'cache_utilization': len(self._cache) / self._max_cache_size * 100,
            'hit_rate': hit_rate,
            'total_operations': total_ops,
            'memory_usage_mb': len(self._cache) * 1024 / 1024 / 1024,  # Rough estimate
            'active_locks': len(self._file_locks),
            'loaded_files': len(self._loaded_files),
            'files_in_progress': len(self._loading_in_progress),
            **self._metrics
        }
    
    async def optimize_cache(self) -> Dict[str, int]:
        """Manually optimize cache by removing least used entries"""
        initial_size = len(self._cache)
        
        # Sort by access time and remove oldest 25%
        if len(self._cache) > self._max_cache_size * 0.75:
            items = list(self._cache_timestamps.items())
            items.sort(key=lambda x: x[1])
            
            remove_count = int(len(items) * 0.25)
            for key, _ in items[:remove_count]:
                if key not in self._critical_files:  # Preserve critical files
                    self._cache.pop(key, None)
                    self._cache_timestamps.pop(key, None)
        
        final_size = len(self._cache)
        return {
            'initial_size': initial_size,
            'final_size': final_size,
            'removed_entries': initial_size - final_size
        }
    
    async def clear_recruitment_cache(self) -> Dict[str, int]:
        """Clear recruitment-related cache entries to reduce memory usage"""
        initial_size = len(self._cache)
        removed_count = 0
        
        # Identify recruitment-related cache keys
        recruitment_keys = []
        for key in list(self._cache.keys()):
            # Clear cache for recruitment_history.json and recruit.json
            if 'recruitment_history.json' in key or 'recruit.json' in key:
                recruitment_keys.append(key)
        
        # Remove recruitment-related cache entries
        for key in recruitment_keys:
            if key in self._cache:
                self._cache.pop(key, None)
                self._cache_timestamps.pop(key, None)
                removed_count += 1
                logging.debug(f"Cleared recruitment cache entry: {key}")
        
        final_size = len(self._cache)
        
        logging.info(f"Cleared {removed_count} recruitment cache entries. Cache size: {initial_size} -> {final_size}")
        
        return {
            'initial_cache_size': initial_size,
            'final_cache_size': final_size,
            'removed_entries': removed_count,
            'recruitment_keys_cleared': recruitment_keys
        }
    
    async def shutdown(self):
        """Graceful shutdown with cleanup"""
        self._shutdown_event.set()
        if self._refresh_task:
            await self._refresh_task
        
        # Shutdown thread pool
        self._thread_pool.shutdown(wait=True)
        
        # Clear caches
        self._cache.clear()
        self._cache_timestamps.clear()
        self._file_locks.clear()
    
    # JSON Data Access Methods
    async def get_json_data(self, file_key: str, default_data: Any = None) -> Any:
        """Get JSON data by logical key.

        Delegates to load_json_data which supports dynamic keys like 'alliance_<id>',
        'war_party_<side>', 'war_parties_<pair>', and 'treaties_<id>'.
        Returns default_data when an empty dict would be returned and default_data is provided.
        """
        try:
            result = await self.load_json_data(file_key)
            if result == {} and default_data is not None:
                return default_data
            return result
        except Exception as e:
            logging.error(f"get_json_data error for key '{file_key}': {e}")
            return default_data if default_data is not None else {}

    # Zodiac Data Methods (Optimized)
    async def get_western_astrology(self) -> List[Dict[str, Any]]:
        """Load Western astrology data (astrology.json) with caching."""
        data = await self._load_json_optimized(self._file_paths['astrology'], [], lazy=True)
        return data if isinstance(data, list) else []

    async def get_chinese_astrology(self) -> List[Dict[str, Any]]:
        """Load Chinese astrology data (chinese_astrology.json) with caching."""
        data = await self._load_json_optimized(self._file_paths['chinese_astrology'], [], lazy=True)
        return data if isinstance(data, list) else []

    async def get_primal_astrology(self) -> List[Dict[str, Any]]:
        """Load Primal astrology data (primal_astrology.json) with caching."""
        data = await self._load_json_optimized(self._file_paths['primal_astrology'], [], lazy=True)
        return data if isinstance(data, list) else []

    # Zodiac Lookup Helpers
    @staticmethod
    def _normalize_chinese_for_primal(name: str) -> str:
        """Normalize Chinese zodiac name for primal combos (Goat→Sheep)."""
        return 'Sheep' if str(name).strip().lower() == 'goat' else str(name).strip()

    @staticmethod
    def _denormalize_primal_to_chinese(name: str) -> str:
        """Map primal Sheep back to Chinese Goat when needed."""
        return 'Goat' if str(name).strip().lower() == 'sheep' else str(name).strip()

    def format_primal_combination(self, western_name: str, chinese_name: str) -> str:
        """Format a Primal astrology combination string consistently (normalizes Goat→Sheep)."""
        return f"{str(western_name).strip()} / {self._normalize_chinese_for_primal(chinese_name)}"

    async def find_western_sign_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find Western zodiac entry by name (case-insensitive)."""
        signs = await self.get_western_astrology()
        target = str(name).strip().lower()
        for entry in signs:
            if isinstance(entry, dict) and str(entry.get('name', '')).strip().lower() == target:
                return entry
        return None

    async def find_chinese_sign_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find Chinese zodiac entry by name; accepts Sheep or Goat (case-insensitive)."""
        signs = await self.get_chinese_astrology()
        target = str(name).strip().lower()
        # Accept both 'goat' and 'sheep' by mapping sheep->goat internally
        if target == 'sheep':
            target = 'goat'
        for entry in signs:
            if isinstance(entry, dict) and str(entry.get('Name', '')).strip().lower() == target:
                return entry
        return None

    async def find_chinese_sign_by_year(self, year: int) -> Optional[Dict[str, Any]]:
        """Find Chinese zodiac entry by Gregorian year using listed years or 12-year cycle anchored at 2020=Rat."""
        signs = await self.get_chinese_astrology()
        # First pass: exact year listed
        for entry in signs:
            years = entry.get('Years')
            if isinstance(years, list) and year in years:
                return entry
        # Fallback: compute via cycle anchored at 2020 Rat
        order = ['Rat','Ox','Tiger','Rabbit','Dragon','Snake','Horse','Goat','Monkey','Rooster','Dog','Pig']
        try:
            idx = (int(year) - 2020) % 12
            target_name = order[idx]
        except Exception:
            return None
        for entry in signs:
            if str(entry.get('Name','')).strip().lower() == target_name.lower():
                return entry
        return None

    async def find_primal_by_combination(self, western_name: str, chinese_name: str) -> Optional[Dict[str, Any]]:
        """Find Primal astrology entry by Sign Combination (e.g., 'Pisces / Sheep')."""
        primal = await self.get_primal_astrology()
        combo = f"{str(western_name).strip()} / {self._normalize_chinese_for_primal(chinese_name)}"
        for entry in primal:
            if isinstance(entry, dict) and str(entry.get('Sign Combination','')).strip() == combo:
                return entry
        # Try case-insensitive match as fallback
        for entry in primal:
            if isinstance(entry, dict) and str(entry.get('Sign Combination','')).strip().lower() == combo.lower():
                return entry
        return None
    


    # Data Validation (Optimized)
    def _validate_structure(self, data: Dict[str, Any], required_fields: List[str]) -> bool:
        """Fast structure validation"""
        return all(field in data for field in required_fields)
    
    async def validate_all_json_files(self) -> Dict[str, bool]:
        """Fast validation of all JSON files with comprehensive coverage"""
        validators = {
            # Core game data - top-level keys
            'monsters': ['rarity_colors','monsters'],
            'bosses': ['rarity_colors','bosses'],
            'titans': ['rarity_colors','titans'],
            'pets_level': ['LEVEL_THRESHOLDS', 'PET_STAGES', 'STAGE_EMOJIS', 'AUTOBOT_PET_NAMES', 'DECEPTICON_PET_NAMES', 'MISSION_TYPES'],
            'pet_xp': ['LEVEL_THRESHOLDS'],
            'pets_mission': ['MISSION_TYPES'],
            'pet_equipment': ['chassis_plating', 'energy_cores', 'utility_modules'],
            'recruit': ['subject', 'body'],  # This is a list, not dict
            'bot_logs': ['logs'],
            'cybercoin_market_data': ['current_price', 'price_history', 'user_portfolios', 'total_volume_24h', 'market_trend', 'last_update'],
            

            
            # Random talk data - top-level keys
            'what_talk': ['Allspark', 'Cybertron', 'Energon', 'Transformer', 'Autobot', 'Decepticon', 'Combiner', 'Primes', 'Unicron', 'Matrix of Leadership', 'Quintessons', 'Space Bridge', 'Seekers', 'Minicons', 'Vector Sigma', 'Omega Supreme', 'Dinobots', 'Wreckers', 'Vector Prime'],
            'jokes_talk': ['transformers_politics_war_jokes'],
            'grump_talk': ['greeting_templates', 'threatening_messages', 'nuclear_messages', 'ultra_nuclear_messages', 'witness_messages', 'threat_messages'],
            'blessings_talk': ['💪 Courage and Strength', '📖 Wisdom and Guidance', '🌈 Hope and Unity', '🛡️ Protection and Longevity', '🏛️ Legacy and Destiny', '💊 Healing and Renewal', '🚀 Exploration and Discovery', '⚖️ Honor and Justice', '🔥 Passion and Innovation', '🌌 Mystery and Fate', '⚡ Misfortune and Warnings', '💀 Bad Fortune and Curses'],
            'user_lore': ['title', 'description', 'author_id', 'timestamp'],

            # Zodiac datasets (list-based) — detailed validation handled below
            'astrology': [],
            'chinese_astrology': [],
            'primal_astrology': []
        }
        
        results = {}
        for file_type, required_keys in validators.items():
            try:
                # Map file types to correct method names
                method_mapping = {
                    'monsters': 'get_monsters_and_bosses_data',
                    'bosses': 'get_monsters_and_bosses_data', 
                    'titans': 'get_monsters_and_bosses_data',
                    'pets_level': 'get_pets_level_data',
                    'pet_xp': 'get_pet_xp_data',
                    'pets_mission': 'get_pets_mission_data',
                    'pet_equipment': 'get_pet_equipment_data',
                    'recruit': 'get_recruit_data',
                    'bot_logs': 'get_bot_logs',
                    'cybercoin_market_data': 'get_cybercoin_market_data',
                    'what_talk': 'get_what_talk_data',
                    'jokes_talk': 'get_jokes_talk_data',
                    'grump_talk': 'get_grump_talk_data',
                    'blessings_talk': 'get_blessings_talk_data',
                    'user_lore': 'get_user_lore_data',

                    # Zodiac datasets
                    'astrology': 'get_western_astrology',
                    'chinese_astrology': 'get_chinese_astrology',
                    'primal_astrology': 'get_primal_astrology'
                }
                
                method_name = method_mapping.get(file_type, f'get_{file_type}')
                data = await getattr(self, method_name)()
                
                # Validate top-level structure
                if isinstance(data, dict):
                    results[file_type] = all(key in data for key in required_keys)
                elif isinstance(data, list):
                    if file_type == 'recruit':
                        # recruit is a list of dicts with subject/body
                        results[file_type] = all(isinstance(item, dict) and all(k in item for k in required_keys) for item in data)
                    elif file_type == 'astrology':
                        # Western astrology entries must have minimal fields
                        required = ['name', 'emoji', 'date_range']
                        results[file_type] = all(isinstance(item, dict) and all(k in item for k in required) for item in data)
                    elif file_type == 'chinese_astrology':
                        # Chinese astrology entries require Name and Years list
                        results[file_type] = all(isinstance(item, dict) and 'Name' in item and isinstance(item.get('Years'), list) for item in data)
                    elif file_type == 'primal_astrology':
                        # Primal astrology entries require Name and Sign Combination
                        results[file_type] = all(isinstance(item, dict) and 'Name' in item and 'Sign Combination' in item for item in data)
                    else:
                        # Generic list should be non-empty
                        results[file_type] = len(data) > 0
                else:
                    results[file_type] = False
            except Exception:
                results[file_type] = False
        
        return results

    async def increment_game_stats(self, player_id: str, won: bool = True, energon_change: int = 0) -> bool:
        """
        Increment game statistics with energon tracking
        Returns: success status
        """
        try:
            energon_data = await self.get_energon_data(player_id)
            
            energon_data['games_played'] += 1
            if won:
                energon_data['games_won'] += 1
            else:
                energon_data['games_lost'] += 1
            
            if energon_change > 0:
                energon_data['total_earned'] += energon_change
            elif energon_change < 0:
                energon_data['total_spent'] += abs(energon_change)
            
            energon_data['last_activity'] = datetime.now().isoformat()
            
            return await self.save_energon_data(player_id, energon_data)
            
        except Exception as e:
            logging.error(f"Error incrementing game stats for {player_id}: {e}")
            return False

    async def get_energon_leaderboard(self, period: str = "all_time", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get energon leaderboard for specified period
        Returns: List of player summaries sorted by energon
        """
        try:
            import glob
            import os
            
            user_files = glob.glob(str(self.base_path / "*.json"))
            players = []
            
            for file_path in user_files:
                try:
                    user_id = Path(file_path).stem
                    if user_id in ["energon_global", "energon_system"]:
                        continue
                    
                    summary = await self.get_energon_summary(user_id)
                    if summary and summary.get('current_balance', {}).get('total_energon', 0) > 0:
                        # Get user data to retrieve the username
                        user_data = await self.get_user_data(user_id)
                        username = user_data.get('username', 'Unknown')
                        
                        players.append({
                            'player_id': user_id,
                            'username': username,
                            'total_energon': summary['current_balance']['total_energon'],
                            'total_earned': summary['lifetime_stats']['total_earned'],
                            'games_played': summary['lifetime_stats']['games_played'],
                            'win_rate': summary['lifetime_stats']['win_rate']
                        })
                        
                except Exception as e:
                    logging.error(f"Error processing leaderboard for {file_path}: {e}")
            
            # Sort by total energon
            players.sort(key=lambda x: x['total_energon'], reverse=True)
            return players[:limit]
            
        except Exception as e:
            logging.error(f"Error generating leaderboard: {e}")
            return []

    async def validate_energon_integrity(self, player_id: str) -> Dict[str, Any]:
        """
        Validate energon data integrity for a player
        Returns: validation report
        """
        try:
            energon_data = await self.get_energon_data(player_id)
            
            issues = []
            
            # Check for negative values
            for field in ['energon', 'energon_bank', 'total_earned', 'total_spent']:
                if energon_data.get(field, 0) < 0:
                    issues.append(f"Negative {field}: {energon_data[field]}")
            
            # Check consistency
            calculated_earned = (
                energon_data.get('pet_energon_earned', 0) +
                energon_data.get('battle_energon_earned', 0) +
                energon_data.get('search_energon_earned', 0) +
                energon_data.get('slots_energon_earned', 0) +
                energon_data.get('challenge_energon_earned', 0)
            )
            
            if calculated_earned > energon_data.get('total_earned', 0):
                issues.append("Source earnings exceed total earned")
            
            # Check game balance consistency
            games_played = energon_data.get('games_played', 0)
            games_won = energon_data.get('games_won', 0)
            games_lost = energon_data.get('games_lost', 0)
            
            if games_won + games_lost != games_played:
                issues.append("Game win/loss count mismatch")
            
            return {
                'valid': len(issues) == 0,
                'issues': issues,
                'data': energon_data
            }
            
        except Exception as e:
            logging.error(f"Error validating energon integrity for {player_id}: {e}")
            return {'valid': False, 'issues': [str(e)]}

    async def migrate_legacy_data(self, player_id: str) -> bool:
        """
        Migrate legacy energon data to new unified structure
        Returns: success status
        """
        try:
            user_data = await self.get_user_data(player_id)
            energon_data = user_data.get("energon", {})
            
            # Migrate from old structure
            legacy_fields = {
                'rush_wins': 'games_won',
                'rush_losses': 'games_lost',
                'search_wins': 'games_won',
                'search_losses': 'games_lost',
                'slots_wins': 'games_won',
                'slots_losses': 'games_lost',
                'challenge_wins': 'games_won',
                'challenge_losses': 'games_lost',
                'total_energon_gained': 'total_earned',
                'total_energon_lost': 'total_spent',
                'search_energon_net': None,  # Remove unused field
                'adventure_state': None  # Remove unused field - walktru uses in-memory cache only
            }
            
            for legacy_field, new_field in legacy_fields.items():
                if legacy_field in energon_data:
                    if new_field is None:
                        # Remove unused field completely
                        del energon_data[legacy_field]
                    elif legacy_field != new_field:
                        if isinstance(energon_data.get(new_field), int):
                            energon_data[new_field] = energon_data.get(new_field, 0) + energon_data[legacy_field]
                        del energon_data[legacy_field]
            
            # Ensure all new fields exist
            default_data = self._get_default_energon_data()
            for key, default_value in default_data.items():
                if key not in energon_data:
                    energon_data[key] = default_value
            
            return await self.save_energon_data(player_id, energon_data)
            
        except Exception as e:
            logging.error(f"Error migrating legacy data for {player_id}: {e}")
            return False
    async def add_energon(self, player_id: str, amount: int, source: str = "general") -> tuple[bool, int, int]:
        """Optimized method to add energon with validation and atomic operations"""
        if amount <= 0:
            return False, 0, 0
            
        try:
            energon_data = await self.get_energon_data(player_id)
            
            # Ensure all fields exist
            energon_data.setdefault('energon_bank', 0)
            energon_data.setdefault('total_earned', 0)
            
            # Atomic updates
            energon_data['energon_bank'] += amount
            energon_data['total_earned'] += amount
            energon_data['last_activity'] = datetime.now().isoformat()
            
            # Source tracking
            source_field = f"{source}_energon_earned"
            energon_data[source_field] = energon_data.get(source_field, 0) + amount
            
            success = await self.save_energon_data(player_id, energon_data)
            return success, energon_data['energon_bank'], energon_data['total_earned']
            
        except Exception as e:
            logging.error(f"Error adding energon for {player_id}: {e}")
            return False, 0, 0

    async def subtract_energon(self, player_id: str, amount: int, source: str = "general") -> tuple[bool, int, int]:
        """Optimized method to subtract energon with balance checking"""
        if amount <= 0:
            return False, 0, 0
            
        try:
            energon_data = await self.get_energon_data(player_id)
            current_balance = energon_data.get('energon_bank', 0)
            current_spent = energon_data.get('total_spent', 0)
            
            if current_balance >= amount:
                energon_data['energon_bank'] = current_balance - amount
                energon_data['total_spent'] = current_spent + amount
                energon_data['last_activity'] = datetime.now().isoformat()
                
                success = await self.save_energon_data(player_id, energon_data)
                return success, energon_data['energon_bank'], energon_data['total_spent']
            
            return False, current_balance, current_spent
            
        except Exception as e:
            logging.error(f"Error subtracting energon for {player_id}: {e}")
            return False, 0, 0

    async def transfer_energon_to_game(self, player_id: str, amount: int) -> tuple[bool, int, int]:
        """Optimized method to transfer energon from bank to game"""
        if amount <= 0:
            return False, 0, 0
            
        try:
            energon_data = await self.get_energon_data(player_id)
            current_bank = energon_data.get('energon_bank', 0)
            current_game = energon_data.get('energon', 0)
            
            if current_bank >= amount:
                energon_data['energon_bank'] = current_bank - amount
                energon_data['energon'] = current_game + amount
                energon_data['last_activity'] = datetime.now().isoformat()
                
                success = await self.save_energon_data(player_id, energon_data)
                return success, energon_data['energon_bank'], energon_data['energon']
            
            return False, current_bank, current_game
            
        except Exception as e:
            logging.error(f"Error transferring energon to game for {player_id}: {e}")
            return False, 0, 0

    async def bank_game_energon(self, player_id: str) -> tuple[bool, int, int]:
        """Optimized method to bank all game energon"""
        try:
            energon_data = await self.get_energon_data(player_id)
            game_balance = energon_data.get('energon', 0)
            bank_balance = energon_data.get('energon_bank', 0)
            
            if game_balance > 0:
                energon_data['energon_bank'] = bank_balance + game_balance
                energon_data['energon'] = 0
                energon_data['last_activity'] = datetime.now().isoformat()
                
                success = await self.save_energon_data(player_id, energon_data)
                return success, energon_data['energon_bank'], game_balance
            
            return True, bank_balance, 0
            
        except Exception as e:
            logging.error(f"Error banking game energon for {player_id}: {e}")
            return False, 0, 0

    # Shooting Range Methods
    async def update_shooting_range_stats(self, user_id: str, username: str, hits: int, total_shots: int, rounds: int) -> Dict[str, Any]:
        """Update shooting range statistics for a user"""
        try:
            user_data = await self.get_user_data(user_id, username)
            shooting_data = user_data.get("shooting_range", {
                "high_score": 0, "games_played": 0, "accuracy": 0.0,
                "total_targets_hit": 0, "total_hits": 0, "total_shots": 0,
                "sessions_played": 0,
                "best_records": {"5": {"accuracy": 0, "hits": 0}, "15": {"accuracy": 0, "hits": 0},
                               "25": {"accuracy": 0, "hits": 0}, "50": {"accuracy": 0, "hits": 0},
                               "100": {"accuracy": 0, "hits": 0}},
                "round_attempts": {}
            })
            
            # Update basic stats
            shooting_data['sessions_played'] += 1
            shooting_data['total_hits'] += hits
            shooting_data['total_shots'] += total_shots
            shooting_data['games_played'] += 1
            
            # Calculate current accuracy
            current_accuracy = (hits / total_shots * 100) if total_shots > 0 else 0
            
            # Update overall accuracy
            if shooting_data['total_shots'] > 0:
                shooting_data['accuracy'] = (shooting_data['total_hits'] / shooting_data['total_shots'] * 100)
            
            # Update best records for this round count
            rounds_key = str(rounds)
            if rounds_key in shooting_data['best_records']:
                current_best = shooting_data['best_records'][rounds_key]
                # Update if this is better accuracy, or same accuracy but more hits
                if (current_accuracy > current_best['accuracy'] or 
                    (current_accuracy == current_best['accuracy'] and hits > current_best['hits'])):
                    shooting_data['best_records'][rounds_key] = {
                        'accuracy': current_accuracy,
                        'hits': hits
                    }
            
            # Update round attempts count
            round_attempts = shooting_data.get('round_attempts', {})
            round_attempts[rounds_key] = round_attempts.get(rounds_key, 0) + 1
            shooting_data['round_attempts'] = round_attempts
            
            # Update user data
            user_data["shooting_range"] = shooting_data
            await self.save_user_data(user_id, username, user_data)
            
            return shooting_data
            
        except Exception as e:
            logging.error(f"Error updating shooting range stats for {user_id}: {e}")
            return {}
    
    async def get_shooting_range_stats(self, user_id: str) -> Dict[str, Any]:
        """Get shooting range statistics for a user"""
        try:
            user_data = await self.get_user_data(user_id)
            shooting_data = user_data.get("shooting_range", {
                "high_score": 0, "games_played": 0, "accuracy": 0.0,
                "total_targets_hit": 0, "total_hits": 0, "total_shots": 0,
                "sessions_played": 0,
                "best_records": {"5": {"accuracy": 0, "hits": 0}, "15": {"accuracy": 0, "hits": 0},
                               "25": {"accuracy": 0, "hits": 0}, "50": {"accuracy": 0, "hits": 0},
                               "100": {"accuracy": 0, "hits": 0}},
                "round_attempts": {}
            })
            
            return shooting_data
            
        except Exception as e:
            logging.error(f"Error getting shooting range stats for {user_id}: {e}")
            return {
                "high_score": 0, "games_played": 0, "accuracy": 0.0,
                "total_targets_hit": 0, "total_hits": 0, "total_shots": 0,
                "sessions_played": 0,
                "best_records": {"5": {"accuracy": 0, "hits": 0}, "15": {"accuracy": 0, "hits": 0},
                               "25": {"accuracy": 0, "hits": 0}, "50": {"accuracy": 0, "hits": 0},
                               "100": {"accuracy": 0, "hits": 0}},
                "round_attempts": {}
            }

    # Recruitment History Management
    async def get_recruitment_history(self) -> Dict[str, Any]:
        """Get recruitment history data"""
        return await self.get_json_data("recruitment_history", {
            "messages": [],
            "stats": {"total_messages": 0, "unique_users": 0}
        })

    async def save_recruitment_history(self, data: Dict[str, Any]) -> bool:
        """Save recruitment history data and clear related cache"""
        result = await self.save_json_data("recruitment_history", data)
        if result:
            # Clear recruitment-related cache to reduce memory usage
            await self.clear_recruitment_cache()
        return result

    async def add_recruitment_message(self, user_id: str, username: str, message_data: Dict[str, Any]) -> bool:
        """Add a recruitment message to history"""
        try:
            history = await self.get_recruitment_history()
            
            # Add timestamp if not present
            if "timestamp" not in message_data:
                message_data["timestamp"] = datetime.now().isoformat()
            
            message_data.update({
                "user_id": user_id,
                "username": username
            })
            
            history["messages"].append(message_data)
            
            # Update stats
            history["stats"]["total_messages"] = len(history["messages"])
            unique_users = set(msg.get("user_id") for msg in history["messages"])
            history["stats"]["unique_users"] = len(unique_users)
            
            return await self.save_recruitment_history(history)
        except Exception as e:
            logging.error(f"Error adding recruitment message: {e}")
            return False

    # Global Leaderboards Management
    async def get_global_leaderboards(self) -> Dict[str, Any]:
        """Get global leaderboards data"""
        return await self.get_json_data("global_leaderboards", {
            "energon": {"daily": [], "weekly": [], "monthly": [], "all_time": []},
            "pets": {"level": [], "battles_won": [], "missions_completed": []},
            "games": {"slot_machine": [], "shooting_range": [], "pvp": []},
            "general": {"messages_sent": [], "commands_used": [], "time_active": []}
        })

    async def save_global_leaderboards(self, data: Dict[str, Any]) -> bool:
        """Save global leaderboards data"""
        return await self.save_json_data("global_leaderboards", data)

    async def update_leaderboard_entry(self, category: str, subcategory: str, user_id: str, username: str, score: int, additional_data: Dict[str, Any] = None) -> bool:
        """Update a leaderboard entry"""
        try:
            leaderboards = await self.get_global_leaderboards()
            
            if category not in leaderboards:
                leaderboards[category] = {}
            if subcategory not in leaderboards[category]:
                leaderboards[category][subcategory] = []
            
            # Create entry
            entry = {
                "user_id": user_id,
                "username": username,
                "score": score,
                "timestamp": datetime.now().isoformat()
            }
            
            if additional_data:
                entry.update(additional_data)
            
            # Remove existing entry for this user
            leaderboards[category][subcategory] = [
                e for e in leaderboards[category][subcategory] 
                if e.get("user_id") != user_id
            ]
            
            # Add new entry
            leaderboards[category][subcategory].append(entry)
            
            # Sort by score (descending) and keep top 100
            leaderboards[category][subcategory].sort(key=lambda x: x["score"], reverse=True)
            leaderboards[category][subcategory] = leaderboards[category][subcategory][:100]
            
            return await self.save_global_leaderboards(leaderboards)
        except Exception as e:
            logging.error(f"Error updating leaderboard entry: {e}")
            return False

    async def get_leaderboard_rank(self, category: str, subcategory: str, user_id: str) -> Optional[int]:
        """Get user's rank in a specific leaderboard"""
        try:
            leaderboards = await self.get_global_leaderboards()
            
            if category not in leaderboards or subcategory not in leaderboards[category]:
                return None
            
            for i, entry in enumerate(leaderboards[category][subcategory]):
                if entry.get("user_id") == user_id:
                    return i + 1  # 1-based ranking
            
            return None
        except Exception as e:
            logging.error(f"Error getting leaderboard rank: {e}")
            return None

    # Server Analytics Management
    async def get_server_analytics(self) -> Dict[str, Any]:
        """Get server analytics data"""
        return await self.get_json_data("server_analytics", {
            "daily_stats": {},
            "weekly_stats": {},
            "monthly_stats": {},
            "command_usage": {},
            "user_activity": {},
            "system_performance": {},
            "error_tracking": {}
        })

    async def save_server_analytics(self, data: Dict[str, Any]) -> bool:
        """Save server analytics data"""
        return await self.save_json_data("server_analytics", data)

    async def record_command_usage(self, command_name: str, user_id: str, success: bool = True) -> bool:
        """Record command usage for analytics"""
        try:
            analytics = await self.get_server_analytics()
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Initialize structures if needed
            if "command_usage" not in analytics:
                analytics["command_usage"] = {}
            if today not in analytics["command_usage"]:
                analytics["command_usage"][today] = {}
            if command_name not in analytics["command_usage"][today]:
                analytics["command_usage"][today][command_name] = {"total": 0, "success": 0, "failed": 0}
            
            # Update counts
            analytics["command_usage"][today][command_name]["total"] += 1
            if success:
                analytics["command_usage"][today][command_name]["success"] += 1
            else:
                analytics["command_usage"][today][command_name]["failed"] += 1
            
            return await self.save_server_analytics(analytics)
        except Exception as e:
            logging.error(f"Error recording command usage: {e}")
            return False

    async def record_user_activity(self, user_id: str, username: str, activity_type: str) -> bool:
        """Record user activity for analytics"""
        try:
            analytics = await self.get_server_analytics()
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Initialize structures if needed
            if "user_activity" not in analytics:
                analytics["user_activity"] = {}
            if today not in analytics["user_activity"]:
                analytics["user_activity"][today] = {}
            if user_id not in analytics["user_activity"][today]:
                analytics["user_activity"][today][user_id] = {
                    "username": username,
                    "activities": {},
                    "total_actions": 0
                }
            
            # Update activity
            if activity_type not in analytics["user_activity"][today][user_id]["activities"]:
                analytics["user_activity"][today][user_id]["activities"][activity_type] = 0
            
            analytics["user_activity"][today][user_id]["activities"][activity_type] += 1
            analytics["user_activity"][today][user_id]["total_actions"] += 1
            analytics["user_activity"][today][user_id]["username"] = username  # Update username
            
            return await self.save_server_analytics(analytics)
        except Exception as e:
            logging.error(f"Error recording user activity: {e}")
            return False

    # Walk Tru Adventure Data Management
    async def get_walk_tru_adventure(self, adventure_type: str) -> Dict[str, Any]:
        """Get Walk Tru adventure data by type"""
        adventure_key = f"walk_tru_{adventure_type.lower()}"
        return await self.get_json_data(adventure_key, {})

    async def save_walk_tru_adventure(self, adventure_type: str, data: Dict[str, Any]) -> bool:
        """Save Walk Tru adventure data"""
        adventure_key = f"walk_tru_{adventure_type.lower()}"
        return await self.save_json_data(adventure_key, data)

    async def get_all_walk_tru_adventures(self) -> Dict[str, Dict[str, Any]]:
        """Get all Walk Tru adventure data"""
        adventures = {}
        adventure_types = ["ganster", "horror", "knight", "robot", "western", "wizard"]
        
        for adventure_type in adventure_types:
            adventures[adventure_type] = await self.get_walk_tru_adventure(adventure_type)
        
        return adventures

    # Data Migration and Maintenance
    async def migrate_external_data_files(self) -> Dict[str, bool]:
        """Migrate external data files into UserDataManager system"""
        results = {}
        
        try:
            # Check for recruitment_history.json in data directory
            external_recruitment_path = Path("data/recruitment_history.json")
            if external_recruitment_path.exists():
                try:
                    with open(external_recruitment_path, 'r', encoding='utf-8') as f:
                        recruitment_data = json.load(f)
                    
                    results["recruitment_history"] = await self.save_recruitment_history(recruitment_data)
                    logging.info("Migrated recruitment_history.json")
                except Exception as e:
                    logging.error(f"Error migrating recruitment_history.json: {e}")
                    results["recruitment_history"] = False
            else:
                results["recruitment_history"] = True  # No file to migrate
            
            # Initialize empty global files if they don't exist
            if not await self.get_global_leaderboards():
                results["global_leaderboards"] = await self.save_global_leaderboards({
                    "energon": {"daily": [], "weekly": [], "monthly": [], "all_time": []},
                    "pets": {"level": [], "battles_won": [], "missions_completed": []},
                    "games": {"slot_machine": [], "shooting_range": [], "pvp": []},
                    "general": {"messages_sent": [], "commands_used": [], "time_active": []}
                })
            else:
                results["global_leaderboards"] = True
            
            if not await self.get_server_analytics():
                results["server_analytics"] = await self.save_server_analytics({
                    "daily_stats": {},
                    "weekly_stats": {},
                    "monthly_stats": {},
                    "command_usage": {},
                    "user_activity": {},
                    "system_performance": {},
                    "error_tracking": {}
                })
            else:
                results["server_analytics"] = True
            
        except Exception as e:
            logging.error(f"Error during data migration: {e}")
            results["migration_error"] = False
        
        return results

    async def cleanup_old_analytics(self, days_to_keep: int = 90) -> int:
        """Clean up old analytics data"""
        try:
            analytics = await self.get_server_analytics()
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cutoff_str = cutoff_date.strftime("%Y-%m-%d")
            
            cleaned_count = 0
            
            # Clean command usage
            if "command_usage" in analytics:
                old_dates = [date for date in analytics["command_usage"].keys() if date < cutoff_str]
                for date in old_dates:
                    del analytics["command_usage"][date]
                    cleaned_count += 1
            
            # Clean user activity
            if "user_activity" in analytics:
                old_dates = [date for date in analytics["user_activity"].keys() if date < cutoff_str]
                for date in old_dates:
                    del analytics["user_activity"][date]
                    cleaned_count += 1
            
            if cleaned_count > 0:
                await self.save_server_analytics(analytics)
            
            return cleaned_count
        except Exception as e:
            logging.error(f"Error cleaning up analytics: {e}")
            return 0

user_data_manager = UserDataManager()

OptimizedUserDataManager = UserDataManager