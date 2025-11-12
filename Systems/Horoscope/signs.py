import json
import re
import asyncio
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

import discord
from discord.ext import commands, tasks
from discord import app_commands
try:
    import aiohttp
except Exception:
    aiohttp = None
from Systems.user_data_manager import UserDataManager

# Actual Chinese New Year dates for each year (coverage: 1900–2027)
CHINESE_NEW_YEAR_DATES = {
    1900: date(1900, 1, 31), 1901: date(1901, 2, 19), 1902: date(1902, 2, 8), 1903: date(1903, 1, 29),
    1904: date(1904, 2, 16), 1905: date(1905, 2, 4), 1906: date(1906, 1, 25), 1907: date(1907, 2, 13),
    1908: date(1908, 2, 2), 1909: date(1909, 1, 22), 1910: date(1910, 2, 10), 1911: date(1911, 1, 30),
    1912: date(1912, 2, 18), 1913: date(1913, 2, 6), 1914: date(1914, 1, 26), 1915: date(1915, 2, 14),
    1916: date(1916, 2, 3), 1917: date(1917, 1, 23), 1918: date(1918, 2, 11), 1919: date(1919, 2, 1),
    1920: date(1920, 2, 20), 1921: date(1921, 2, 8), 1922: date(1922, 1, 28), 1923: date(1923, 2, 16),
    1924: date(1924, 2, 5), 1925: date(1925, 1, 24), 1926: date(1926, 2, 13), 1927: date(1927, 2, 2),
    1928: date(1928, 1, 23), 1929: date(1929, 2, 10), 1930: date(1930, 1, 30), 1931: date(1931, 2, 17),
    1932: date(1932, 2, 6), 1933: date(1933, 1, 26), 1934: date(1934, 2, 14), 1935: date(1935, 2, 4),
    1936: date(1936, 1, 24), 1937: date(1937, 2, 11), 1938: date(1938, 1, 31), 1939: date(1939, 2, 19),
    1940: date(1940, 2, 8), 1941: date(1941, 1, 27), 1942: date(1942, 2, 15), 1943: date(1943, 2, 5),
    1944: date(1944, 1, 25), 1945: date(1945, 2, 13), 1946: date(1946, 2, 2), 1947: date(1947, 1, 22),
    1948: date(1948, 2, 10), 1949: date(1949, 1, 29), 1950: date(1950, 2, 17), 1951: date(1951, 2, 6),
    1952: date(1952, 1, 27), 1953: date(1953, 2, 14), 1954: date(1954, 2, 3), 1955: date(1955, 1, 24),
    1956: date(1956, 2, 12), 1957: date(1957, 1, 31), 1958: date(1958, 2, 18), 1959: date(1959, 2, 8),
    1960: date(1960, 1, 28), 1961: date(1961, 2, 15), 1962: date(1962, 2, 5), 1963: date(1963, 1, 25),
    1964: date(1964, 2, 13), 1965: date(1965, 2, 2), 1966: date(1966, 1, 21), 1967: date(1967, 2, 9),
    1968: date(1968, 1, 30), 1969: date(1969, 2, 17), 1970: date(1970, 2, 6), 1971: date(1971, 1, 27),
    1972: date(1972, 2, 15), 1973: date(1973, 2, 3), 1974: date(1974, 1, 23), 1975: date(1975, 2, 11),
    1976: date(1976, 1, 31), 1977: date(1977, 2, 18), 1978: date(1978, 2, 7), 1979: date(1979, 1, 28),
    1980: date(1980, 2, 16), 1981: date(1981, 2, 5), 1982: date(1982, 1, 25), 1983: date(1983, 2, 13),
    1984: date(1984, 2, 2), 1985: date(1985, 2, 20), 1986: date(1986, 2, 9), 1987: date(1987, 1, 29),
    1988: date(1988, 2, 17), 1989: date(1989, 2, 6), 1990: date(1990, 1, 27), 1991: date(1991, 2, 15),
    1992: date(1992, 2, 4), 1993: date(1993, 1, 23), 1994: date(1994, 2, 10), 1995: date(1995, 1, 31),
    1996: date(1996, 2, 19), 1997: date(1997, 2, 7), 1998: date(1998, 1, 28), 1999: date(1999, 2, 16),
    2000: date(2000, 2, 5), 2001: date(2001, 1, 24), 2002: date(2002, 2, 12), 2003: date(2003, 2, 1),
    2004: date(2004, 1, 22), 2005: date(2005, 2, 9), 2006: date(2006, 1, 29), 2007: date(2007, 2, 18),
    2008: date(2008, 2, 7), 2009: date(2009, 1, 26), 2010: date(2010, 2, 14), 2011: date(2011, 2, 3),
    2012: date(2012, 1, 23), 2013: date(2013, 2, 10), 2014: date(2014, 1, 31), 2015: date(2015, 2, 19),
    2016: date(2016, 2, 8), 2017: date(2017, 1, 28), 2018: date(2018, 2, 16), 2019: date(2019, 2, 5),
    2020: date(2020, 1, 25), 2021: date(2021, 2, 12), 2022: date(2022, 2, 1), 2023: date(2023, 1, 22),
    2024: date(2024, 2, 10), 2025: date(2025, 1, 29), 2026: date(2026, 2, 17), 2027: date(2027, 2, 6),
}


class AstrologyCog(commands.Cog):
    """Slash command to show zodiac info from astrology.json based on birthday."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.udm = UserDataManager()
        self._horoscope_lock = asyncio.Lock()

    async def cog_load(self):
        # Start the scheduler when the cog is loaded
        await self._ensure_user_horoscope_file()
        self.horoscope_scheduler.start()

    def cog_unload(self):
        # Stop the scheduler when the cog is unloaded
        try:
            self.horoscope_scheduler.cancel()
        except Exception:
            pass

    @property
    def _user_horoscope_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / "Data" / "Zodiac" / "user_horoscope.json"

    async def _load_user_horoscope_data(self) -> Dict[str, Any]:
        async with self._horoscope_lock:
            try:
                p = self._user_horoscope_path
                p.parent.mkdir(parents=True, exist_ok=True)
                if not p.exists():
                    p.write_text("{}", encoding="utf-8")
                text = p.read_text(encoding="utf-8")
                data = json.loads(text or "{}")
                return data if isinstance(data, dict) else {}
            except Exception:
                return {}

    async def _ensure_user_horoscope_file(self) -> None:
        """Ensure the user_horoscope.json exists and is a valid JSON object."""
        async with self._horoscope_lock:
            try:
                p = self._user_horoscope_path
                p.parent.mkdir(parents=True, exist_ok=True)
                if not p.exists():
                    p.write_text("{}", encoding="utf-8")
                else:
                    # If file exists but is invalid, reset to empty object
                    try:
                        text = p.read_text(encoding="utf-8")
                        obj = json.loads(text or "{}")
                        if not isinstance(obj, dict):
                            p.write_text("{}", encoding="utf-8")
                    except Exception:
                        p.write_text("{}", encoding="utf-8")
            except Exception:
                # Silently ignore; _load/_save will handle later
                pass

    async def _save_user_horoscope_data(self, data: Dict[str, Any]) -> bool:
        async with self._horoscope_lock:
            try:
                p = self._user_horoscope_path
                p.parent.mkdir(parents=True, exist_ok=True)
                # Atomic write: write to temp then replace
                tmp = p.with_name(p.name + ".tmp")
                tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                tmp.replace(p)
                return True
            except Exception:
                return False

    async def _fetch_daily_horoscope(self, sign: str) -> Optional[str]:
        """Fetch daily horoscope text from Aztro (free, no key)."""
        sign_slug = str(sign).strip().lower()
        url = f"https://aztro.sameerkumar.website/?sign={sign_slug}&day=today"
        try:
            if aiohttp is None:
                return None
            async with aiohttp.ClientSession() as session:
                async with session.post(url, timeout=10) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    return str(data.get("description") or "").strip() or None
        except Exception:
            return None

    async def _fetch_horoscope_stats(self, sign: str) -> Optional[Dict[str, Any]]:
        """Fetch 1-3 extra stats (mood, color, lucky_number, etc.) from Aztro."""
        sign_slug = str(sign).strip().lower()
        url = f"https://aztro.sameerkumar.website/?sign={sign_slug}&day=today"
        try:
            if aiohttp is None:
                return None
            async with aiohttp.ClientSession() as session:
                async with session.post(url, timeout=10) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    stats = {
                        "mood": data.get("mood"),
                        "color": data.get("color"),
                        "lucky_number": data.get("lucky_number"),
                        "lucky_time": data.get("lucky_time"),
                        "compatibility": data.get("compatibility"),
                    }
                    return {k: v for k, v in stats.items() if v}
        except Exception:
            return None

    async def _fetch_aztro_bundle(self, sign: str) -> (Optional[str], Optional[Dict[str, Any]]):
        """Fetch both description and stats from Aztro in one request."""
        sign_slug = str(sign).strip().lower()
        url = f"https://aztro.sameerkumar.website/?sign={sign_slug}&day=today"
        try:
            if aiohttp is None:
                return None, None
            async with aiohttp.ClientSession() as session:
                async with session.post(url, timeout=10) as resp:
                    if resp.status != 200:
                        return None, None
                    data = await resp.json()
                    text = str(data.get("description") or "").strip() or None
                    stats = {
                        "mood": data.get("mood"),
                        "color": data.get("color"),
                        "lucky_number": data.get("lucky_number"),
                        "lucky_time": data.get("lucky_time"),
                        "compatibility": data.get("compatibility"),
                        "date_range": data.get("date_range"),
                        "current_date": data.get("current_date"),
                    }
                    stats = {k: v for k, v in stats.items() if v}
                    return text, (stats or None)
        except Exception:
            return None, None

    async def _fetch_ohmanda_bundle(self, sign: str) -> (Optional[str], Optional[Dict[str, Any]]):
        """Fetch daily horoscope from Ohmanda's public API (no key)."""
        sign_slug = str(sign).strip().lower()
        url = f"https://ohmanda.com/api/horoscope/{sign_slug}"
        try:
            if aiohttp is None:
                return None, None
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        return None, None
                    data = await resp.json()
                    text = str(data.get("horoscope") or "").strip() or None
                    # Ohmanda returns 'date' and 'sign'; include minimal stats
                    stats = {}
                    if data.get("date"):
                        stats["current_date"] = data.get("date")
                    return text, (stats or None)
        except Exception:
            return None, None

    async def _fetch_daily_bundle(self, sign: str) -> (Optional[str], Optional[Dict[str, Any]]):
        """Unified fetch: try Ohmanda first, then fall back to Aztro."""
        # Primary provider: Ohmanda
        text, stats = await self._fetch_ohmanda_bundle(sign)
        if text:
            return text, stats
        # Fallback provider: Aztro
        return await self._fetch_aztro_bundle(sign)

    def _build_horoscope_embed(self, sign: str, text: str, stats: Optional[Dict[str, Any]]) -> discord.Embed:
        """Create a rich embed for daily horoscope with emojis and all available Aztro stats."""
        zodiac_emojis = {
            "Aries": "♈", "Taurus": "♉", "Gemini": "♊", "Cancer": "♋",
            "Leo": "♌", "Virgo": "♍", "Libra": "♎", "Scorpio": "♏",
            "Sagittarius": "♐", "Capricorn": "♑", "Aquarius": "♒", "Pisces": "♓",
        }
        emoji = zodiac_emojis.get(sign, "🔮")
        embed = discord.Embed(
            title=f"{emoji} {sign} Daily Horoscope",
            description=text,
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow(),
        )
        # Add all available stats as separate fields
        if stats:
            if stats.get("current_date"):
                embed.add_field(name="Date", value=f"📅 {stats['current_date']}", inline=True)
            if stats.get("date_range"):
                embed.add_field(name="Date Range", value=f"🗓️ {stats['date_range']}", inline=True)
            if stats.get("mood"):
                embed.add_field(name="Mood", value=f"🧠 {stats['mood']}", inline=True)
            if stats.get("color"):
                embed.add_field(name="Color", value=f"🎨 {stats['color']}", inline=True)
            if stats.get("lucky_number"):
                embed.add_field(name="Lucky Number", value=f"🔢 {stats['lucky_number']}", inline=True)
            if stats.get("lucky_time"):
                embed.add_field(name="Lucky Time", value=f"⏰ {stats['lucky_time']}", inline=True)
            if stats.get("compatibility"):
                embed.add_field(name="Compatibility", value=f"❤️ {stats['compatibility']}", inline=True)
        embed.set_footer(text="Powered by free horoscope APIs")
        return embed

    @tasks.loop(minutes=5)
    async def horoscope_scheduler(self):
        """Periodic task to check and DM daily horoscopes for registered users."""
        try:
            data = await self._load_user_horoscope_data()
            if not data:
                return
            now = datetime.utcnow()
            updated = False
            for user_id, entry in list(data.items()):
                try:
                    sign = entry.get("sign")
                    next_send_at_str = entry.get("next_send_at")
                    if not sign or not next_send_at_str:
                        continue
                    next_dt = datetime.fromisoformat(next_send_at_str)
                    if now >= next_dt:
                        sent_ok = False
                        # Fetch horoscope and stats via unified provider selection
                        text, stats = await self._fetch_daily_bundle(sign)
                        # Try cached user first; if not available, fetch from API
                        user = self.bot.get_user(int(user_id))
                        if user is None:
                            try:
                                user = await self.bot.fetch_user(int(user_id))
                            except Exception:
                                user = None
                        if user:
                            try:
                                # Use fallback text if Aztro returns no description
                                fallback_text = text or "Daily horoscope is unavailable right now."
                                embed = self._build_horoscope_embed(sign, fallback_text, stats)
                                await user.send(embed=embed)
                                entry["last_sent_at"] = now.isoformat()
                                sent_ok = True
                            except Exception:
                                sent_ok = False
                        # Schedule next send based on send outcome
                        if sent_ok:
                            entry["next_send_at"] = (now + timedelta(hours=24)).isoformat()
                        else:
                            # Retry soon if DM failed or user not resolvable
                            entry["next_send_at"] = (now + timedelta(minutes=30)).isoformat()
                        data[user_id] = entry
                        updated = True
                except Exception:
                    continue
            if updated:
                await self._save_user_horoscope_data(data)
        except Exception:
            pass

    @horoscope_scheduler.before_loop
    async def before_horoscope_scheduler(self):
        await self.bot.wait_until_ready()

    # Western signs list for choices
    _WESTERN_SIGNS = [
        "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
        "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
    ]

    @staticmethod
    def _zodiac_for_date(bday: date) -> str:
        """Return the zodiac sign name for given date (month/day boundaries)."""
        m, d = bday.month, bday.day
        if (m == 12 and d >= 22) or (m == 1 and d <= 19):
            return "Capricorn"
        if (m == 1 and d >= 20) or (m == 2 and d <= 18):
            return "Aquarius"
        if (m == 2 and d >= 19) or (m == 3 and d <= 20):
            return "Pisces"
        if (m == 3 and d >= 21) or (m == 4 and d <= 19):
            return "Aries"
        if (m == 4 and d >= 20) or (m == 5 and d <= 20):
            return "Taurus"
        if (m == 5 and d >= 21) or (m == 6 and d <= 20):
            return "Gemini"
        if (m == 6 and d >= 21) or (m == 7 and d <= 22):
            return "Cancer"
        if (m == 7 and d >= 23) or (m == 8 and d <= 22):
            return "Leo"
        if (m == 8 and d >= 23) or (m == 9 and d <= 22):
            return "Virgo"
        if (m == 9 and d >= 23) or (m == 10 and d <= 22):
            return "Libra"
        if (m == 10 and d >= 23) or (m == 11 and d <= 21):
            return "Scorpio"
        # else
        return "Sagittarius"

    async def _find_sign_data(self, sign_name: str) -> Optional[Dict[str, Any]]:
        return await self.udm.find_western_sign_by_name(sign_name)

    def _normalize_chinese_to_primal(self, animal_name: str) -> str:
        """Normalize Chinese animal names to match Primal Astrology combinations."""
        mapping = {"Goat": "Sheep"}
        return mapping.get(animal_name, animal_name)

    def _convert_time_24_to_12(self, t: str) -> str:
        """Convert a single 24-hour time like '15:00' or '5' to '3:00 PM' or '5:00 AM'."""
        m = re.match(r"^\s*(\d{1,2})(?::(\d{2}))?\s*$", t)
        if not m:
            # If it already seems to include AM/PM or is non-standard, return as-is
            return t.strip()
        hour = int(m.group(1))
        minute = m.group(2) or "00"
        hour12 = hour % 12
        if hour12 == 0:
            hour12 = 12
        ampm = "AM" if hour < 12 else "PM"
        return f"{hour12}:{minute} {ampm}"

    def _format_hours_24_to_12(self, hours: str) -> str:
        """Format a 24-hour range like '15:00 – 17:00' or '15:00-17:00' to '3:00 PM – 5:00 PM'."""
        s = hours.strip()
        if not s:
            return hours
        # Try common separators in the dataset
        separators = [" – ", "–", "—", " - ", "-", " to "]
        for sep in separators:
            if sep in s:
                parts = [p.strip() for p in s.split(sep) if p.strip()]
                if len(parts) == 2:
                    start = self._convert_time_24_to_12(parts[0])
                    end = self._convert_time_24_to_12(parts[1])
                    return f"{start} – {end}"
        # If not a range, attempt to convert a single time
        return self._convert_time_24_to_12(s)

    async def _find_primal_entry(self, western_sign: str, chinese_animal: str) -> Optional[Dict[str, Any]]:
        return await self.udm.find_primal_by_combination(western_sign, chinese_animal)

    def _get_chinese_new_year_date(self, year: int) -> Optional[date]:
        return CHINESE_NEW_YEAR_DATES.get(year)

    async def _find_chinese_sign_by_birthday(self, user_birthday: date) -> Optional[Dict[str, Any]]:
        """Determine Chinese zodiac sign accounting for actual Chinese New Year of that year."""
        year = user_birthday.year
        cny = self._get_chinese_new_year_date(year)
        if cny is None:
            # If we don't have the exact date, approximate Chinese New Year around Feb 4
            try:
                cny = date(year, 2, 4)
            except Exception:
                cny = date(year, 2, 1)
        chinese_year = year if user_birthday >= cny else year - 1
        return await self.udm.find_chinese_sign_by_year(chinese_year)


    def _calculate_next_birthday_countdown(self, user_birthday: date) -> str:
        """Calculate time until next birthday in weeks/days/hours format."""
        today = date.today()
        current_year = today.year
        
        # Get this year's birthday
        next_birthday = date(current_year, user_birthday.month, user_birthday.day)
        
        # If birthday already passed this year, use next year
        if next_birthday <= today:
            next_birthday = date(current_year + 1, user_birthday.month, user_birthday.day)
        
        # Calculate difference
        delta = next_birthday - today
        total_days = delta.days
        
        # Convert to weeks, days, hours
        weeks = total_days // 7
        remaining_days = total_days % 7
        hours = 0  # Since we're working with dates, assume start of day
        
        # Format the countdown
        parts = []
        if weeks > 0:
            parts.append(f"{weeks} week{'s' if weeks != 1 else ''}")
        if remaining_days > 0:
            parts.append(f"{remaining_days} day{'s' if remaining_days != 1 else ''}")
        if not parts:  # If it's today
            return "Today!"
        
        return ", ".join(parts)

    def _build_unified_embed(self, western_data: Dict[str, Any], chinese_data: Dict[str, Any], 
                           spirit_data: Optional[Dict[str, Any]], user_birthday: date, 
                           western_sign: str, chinese_animal: str) -> discord.Embed:
        """Build a unified embed containing all three zodiac types."""
        # Get emojis for title
        western_emoji = western_data.get("emoji", "")
        chinese_emoji = chinese_data.get("Emoji", "")
        
        # Create title with both signs
        title = f"{western_emoji} {western_sign} • {chinese_emoji} {chinese_animal}"
        if spirit_data:
            spirit_name = spirit_data.get("Name", "Unknown")
            title += f" • 🌀 {spirit_name}"
        
        embed = discord.Embed(
            title=title,
            description="Your complete astrological profile",
            color=discord.Color.from_rgb(138, 43, 226),  # Blue violet
            timestamp=discord.utils.utcnow(),
        )
        
        # Western Zodiac Field
        western_desc = western_data.get("description", "")
        western_traits = western_data.get("traits", [])
        western_compat = western_data.get("compatibility", [])
        western_date_range = western_data.get("date_range", "")
        
        western_content = []
        if western_desc:
            western_content.append(f"**Description:** {western_desc}")
        if western_date_range:
            western_content.append(f"**Date Range:** {western_date_range}")
        if western_traits:
            traits_str = ", ".join(western_traits) if isinstance(western_traits, list) else str(western_traits)
            western_content.append(f"**Traits:** {traits_str}")
        if western_compat:
            compat_str = ", ".join(western_compat) if isinstance(western_compat, list) else str(western_compat)
            western_content.append(f"**Compatibility:** {compat_str}")
        
        embed.add_field(
            name=f"{western_emoji} Western Zodiac",
            value="\n".join(western_content) if western_content else "No data available",
            inline=False
        )
        
        # Chinese Zodiac Field
        chinese_desc = chinese_data.get("Description", "")
        chinese_hours = chinese_data.get("Hours", "")
        chinese_compat = chinese_data.get("Compatibility", "")
        
        chinese_content = []
        if chinese_desc:
            chinese_content.append(f"**Description:** {chinese_desc}")
        if chinese_hours:
            formatted_hours = self._format_hours_24_to_12(chinese_hours)
            chinese_content.append(f"**Lucky Hours:** {formatted_hours}")
        if chinese_compat:
            compat_str = ", ".join(chinese_compat) if isinstance(chinese_compat, list) else str(chinese_compat)
            chinese_content.append(f"**Compatibility:** {compat_str}")
        
        embed.add_field(
            name=f"{chinese_emoji} Eastern Zodiac",
            value="\n".join(chinese_content) if chinese_content else "No data available",
            inline=False
        )
        
        # Spirit Animal Field
        if spirit_data:
            spirit_desc = spirit_data.get("Description", "")
            spirit_traits = spirit_data.get("Traits", [])
            spirit_compat = spirit_data.get("Compatibility", [])
            
            # Build combination explanation using provided data
            combo_explanation = f"{western_emoji} {western_sign} + {chinese_emoji} {self._normalize_chinese_to_primal(chinese_animal)}"
            
            spirit_content = []
            spirit_content.append(f"**Based on:** {combo_explanation}")
            if spirit_desc:
                spirit_content.append(f"**Description:** {spirit_desc}")
            if spirit_traits:
                traits_str = ", ".join(spirit_traits) if isinstance(spirit_traits, list) else str(spirit_traits)
                spirit_content.append(f"**Traits:** {traits_str}")
            if spirit_compat:
                compat_str = ", ".join(spirit_compat) if isinstance(spirit_compat, list) else str(spirit_compat)
                spirit_content.append(f"**Compatibility:** {compat_str}")
            
            embed.add_field(
                name="🌀 Spirit Animal",
                value="\n".join(spirit_content) if spirit_content else "No data available",
                inline=False
            )
        else:
            embed.add_field(
                name="🌀 Spirit Animal",
                value="**Based on:** Your combination\n**Status:** No matching spirit animal found",
                inline=False
            )
        
        # Footer with birthday countdown
        countdown = self._calculate_next_birthday_countdown(user_birthday)
        embed.set_footer(text=f"Next Birthday: {countdown} • Birthday: {user_birthday.strftime('%B %d, %Y')}")
        
        return embed

    async def year_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[int]]:
        """Autocomplete for year input - shows suggestions after 3 digits are typed."""
        if len(current) < 3:
            return []
        
        try:
            # Get the current year for reasonable suggestions
            current_year = datetime.now().year
            
            # If user typed 3+ digits, suggest years starting with those digits
            if current.isdigit():
                base = int(current)
                suggestions = []
                
                # Generate reasonable year suggestions based on input
                if len(current) == 3:
                    # For 3 digits like "199", suggest 1990-1999
                    for i in range(10):
                        year = base * 10 + i
                        if 1900 <= year <= current_year + 10:
                            suggestions.append(app_commands.Choice(name=str(year), value=year))
                elif len(current) == 4:
                    # For 4 digits, suggest the exact year if valid
                    if 1900 <= base <= current_year + 10:
                        suggestions.append(app_commands.Choice(name=str(base), value=base))
                else:
                    # For longer inputs, try to parse as year
                    if 1900 <= base <= current_year:
                        suggestions.append(app_commands.Choice(name=str(base), value=base))
                
                return suggestions[:25]  # Discord limits to 25 choices
        except ValueError:
            pass
        
        return []

    async def day_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[int]]:
        """Autocomplete for day input - shows dropdown after first digit is typed."""
        s = (current or "").strip()
        if len(s) < 1:
            return []
        if not s.isdigit():
            return []
        try:
            matches: List[app_commands.Choice[int]] = []
            for i in range(1, 32):
                if str(i).startswith(s):
                    matches.append(app_commands.Choice(name=str(i), value=i))
            return matches[:25]
        except Exception:
            return []

    @app_commands.command(name="astrology", description="Show your zodiac sign info based on your birthday")
    @app_commands.describe(
        month="Select your birth month",
        day="Select your birth day (autocomplete after first digit)",
        year="Enter your birth year (autocomplete after 3 digits)"
    )
    @app_commands.choices(month=[
        app_commands.Choice(name="January", value=1),
        app_commands.Choice(name="February", value=2),
        app_commands.Choice(name="March", value=3),
        app_commands.Choice(name="April", value=4),
        app_commands.Choice(name="May", value=5),
        app_commands.Choice(name="June", value=6),
        app_commands.Choice(name="July", value=7),
        app_commands.Choice(name="August", value=8),
        app_commands.Choice(name="September", value=9),
        app_commands.Choice(name="October", value=10),
        app_commands.Choice(name="November", value=11),
        app_commands.Choice(name="December", value=12),
    ])
    @app_commands.autocomplete(day=day_autocomplete, year=year_autocomplete)
    async def astrology(
        self,
        interaction: discord.Interaction,
        month: app_commands.Choice[int],
        day: int,
        year: int,
    ):
        """Slash command to display a rich embed of zodiac info for the provided birthday using separate month/day/year inputs."""
        # Extract values; month is a Choice, day is int via autocomplete
        month_value = month.value
        day_value = day
        
        # Validate year range (must not be in the future)
        current_year = datetime.now().year
        if not (1900 <= year <= current_year):
            await interaction.response.send_message(
                f"❌ Invalid year! Please enter a year between 1900 and {current_year}.",
                ephemeral=True,
            )
            return
        
        # Validate and construct a date (handles month/day constraints including leap years)
        try:
            user_birthday = date(year, month_value, day_value)
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid date. Please check the month/day combination (e.g., February 29 only on leap years).",
                ephemeral=True,
            )
            return

        # Ensure the date is not in the future
        if user_birthday > date.today():
            await interaction.response.send_message(
                "❌ Date cannot be in the future. Please select today or a past date.",
                ephemeral=True,
            )
            return

        # Get Western zodiac data via UserDataManager
        sign_name = self._zodiac_for_date(user_birthday)
        sign_data = await self._find_sign_data(sign_name)
        if not sign_data:
            await interaction.response.send_message(
                f"❌ Could not find data for {sign_name}.", ephemeral=True
            )
            return

        # Get Chinese zodiac accounting for actual Chinese New Year cutoff
        chinese_data = await self._find_chinese_sign_by_birthday(user_birthday)
        
        if not chinese_data:
            await interaction.response.send_message(
                f"❌ Could not find Chinese zodiac data for year {year}.", ephemeral=True
            )
            return

        # Get Spirit Animal data
        spirit_data = await self._find_primal_entry(sign_name, chinese_data.get("Name", ""))
        
        # Build unified embed
        unified_embed = self._build_unified_embed(
            sign_data, 
            chinese_data, 
            spirit_data, 
            user_birthday, 
            sign_name, 
            chinese_data.get("Name", "")
        )
        
        # Send the unified embed (no view needed)
        await interaction.response.send_message(embed=unified_embed)

    @app_commands.command(name="horoscope_start", description="Register for a daily horoscope DM")
    @app_commands.describe(sign="Choose your Western zodiac sign")
    @app_commands.choices(sign=[app_commands.Choice(name=s, value=s) for s in _WESTERN_SIGNS])
    async def horoscope_start(self, interaction: discord.Interaction, sign: app_commands.Choice[str]):
        """Register user for a daily horoscope with immediate DM of today's horoscope."""
        user = interaction.user
        chosen_sign = sign.value

        # Load and update registration
        data = await self._load_user_horoscope_data()
        now = datetime.utcnow()
        entry = {
            "discord_id": str(user.id),
            "username": user.name,
            "sign": chosen_sign,
            "registered_at": now.isoformat(),
            # Schedule next send immediately; scheduler will set +24h after a successful send
            "next_send_at": now.isoformat(),
        }
        data[str(user.id)] = entry
        await self._save_user_horoscope_data(data)

        # Try to fetch today's horoscope and DM immediately (embed via Aztro)
        text, stats = await self._fetch_daily_bundle(chosen_sign)
        try:
            # Use a neutral fallback that doesn't imply near-term retry
            fallback_text = text or "Daily horoscope is unavailable right now."
            embed = self._build_horoscope_embed(chosen_sign, fallback_text, stats)
            await user.send(embed=embed)
            # Update last_sent_at and schedule next send 24h after a successful DM
            data = await self._load_user_horoscope_data()
            if str(user.id) in data:
                data[str(user.id)]["last_sent_at"] = now.isoformat()
                data[str(user.id)]["next_send_at"] = (now + timedelta(hours=24)).isoformat()
                await self._save_user_horoscope_data(data)
        except Exception:
            # Keep next_send_at at now so scheduler will retry on next tick
            pass

        await interaction.response.send_message(
            f"✅ Registered for daily {chosen_sign} horoscopes. I’ll DM you every 24 hours from now.",
            ephemeral=True,
        )

    @app_commands.command(name="horoscope_stop", description="Unregister from daily horoscope DMs")
    async def horoscope_stop(self, interaction: discord.Interaction):
        """Unregister the user and remove their record from the data file."""
        user_id = str(interaction.user.id)
        data = await self._load_user_horoscope_data()
        if user_id in data:
            data.pop(user_id, None)
            await self._save_user_horoscope_data(data)
            await interaction.response.send_message("🛑 You’ve been unregistered from daily horoscopes.", ephemeral=True)
        else:
            await interaction.response.send_message("ℹ️ You’re not currently registered for daily horoscopes.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    # Add the cog and ensure the scheduler is started
    cog = AstrologyCog(bot)
    await bot.add_cog(cog)
    # Ensure data file exists
    try:
        await cog._ensure_user_horoscope_file()
    except Exception:
        pass
    # Start scheduler if not already running
    try:
        if not cog.horoscope_scheduler.is_running():
            cog.horoscope_scheduler.start()
    except Exception:
        pass