from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

class RecruitmentTracker:
    """Tracks recruitment messages sent to nations to comply with game rules."""
    
    def __init__(self, user_data_manager):
        self.user_data_manager = user_data_manager
        self.history = {}
        self._history_loaded = False
        self._batch_mode = False
        self._pending_saves = 0
    
    async def _load_history(self) -> Dict:
        """Load recruitment history using user_data_manager."""
        if not self._history_loaded:
            self.history = await self.user_data_manager.get_recruitment_history()
            self._history_loaded = True
        return self.history
    
    async def _save_history(self) -> None:
        """Save recruitment history using user_data_manager."""
        if self._batch_mode:
            self._pending_saves += 1
            return
        await self.user_data_manager.save_recruitment_history(self.history)
    
    async def record_message_sent(self, nation_id: str, message_number: int, leader_name: str = None) -> None:
        """Record that a message was sent to a nation using nation_id as primary key."""
        await self._load_history()
        
        if nation_id not in self.history:
            self.history[nation_id] = {
                'nation_id': nation_id,
                'leader_name': leader_name or f"Nation {nation_id}",
                'messages': []
            }
        else:
            # Update leader name if provided and different
            if leader_name and leader_name != self.history[nation_id]['leader_name']:
                self.history[nation_id]['leader_name'] = leader_name
        
        # Resolve the human-readable title from recruit.json
        message_title = await self._get_message_title_async(message_number)
        self.history[nation_id]['messages'].append({
            'message_number': message_number,
            'sent_at': datetime.now(timezone.utc).isoformat(),
            'message_title': message_title
        })
        
        # Keep only last 100 messages per nation to prevent file bloat
        if len(self.history[nation_id]['messages']) > 100:
            self.history[nation_id]['messages'] = self.history[nation_id]['messages'][-100:]
        
        await self._save_history()
    
    def _get_message_title(self, message_number: int) -> str:
        """Fallback title if recruit.json lookup fails."""
        return f"Message #{message_number}"

    async def _get_message_title_async(self, message_number: int) -> str:
        """Resolve the message title from recruit.json by message_number."""
        try:
            data = await self.user_data_manager.load_json_data('recruit')
            messages = data.get('messages', []) if isinstance(data, dict) else []
            for msg in messages:
                try:
                    if int(msg.get('message_number', -1)) == int(message_number):
                        title = msg.get('title')
                        if isinstance(title, str) and title.strip():
                            return title.strip()
                except Exception:
                    continue
        except Exception:
            pass
        # Fallback to generic title
        return self._get_message_title(message_number)
    
    async def can_send_message(self, nation_id: str, message_number: int) -> bool:
        """
        Check if a message can be sent to a nation based on game rules:
        - Same message: 60 days cooldown
        - Any recruitment message: 60 hours cooldown
        """
        await self._load_history()
        
        if nation_id not in self.history:
            return True
        
        messages = self.history[nation_id]['messages']
        now = datetime.now(timezone.utc)
        
        for msg in messages:
            sent_at = datetime.fromisoformat(msg['sent_at'])
            # Ensure sent_at has timezone info
            if sent_at.tzinfo is None:
                sent_at = sent_at.replace(tzinfo=timezone.utc)
            
            # Check 60-day cooldown for same message number
            if msg['message_number'] == message_number:
                if now - sent_at < timedelta(days=60):
                    return False
            
            # Check 60-hour cooldown for any recruitment message
            if now - sent_at < timedelta(hours=60):
                return False
        
        return True
    
    async def get_available_messages(self, nation_id: str, total_messages: int) -> List[int]:
        """Get list of available message numbers that can be sent to a nation."""
        available = []
        
        for message_num in range(1, total_messages + 1):
            if await self.can_send_message(nation_id, message_num):
                available.append(message_num)
        
        return available
    
    async def get_cooldown_info(self, nation_id: str) -> Dict:
        """Get cooldown information for a nation."""
        await self._load_history()
        
        if nation_id not in self.history:
            return {
                'can_send_any': True,
                'next_available_at': None,
                'last_message': None,
                'blocked_messages': []
            }
        
        messages = self.history[nation_id]['messages']
        if not messages:
            return {
                'can_send_any': True,
                'next_available_at': None,
                'last_message': None,
                'blocked_messages': []
            }
        
        now = datetime.now(timezone.utc)
        last_message = messages[-1]
        last_sent = datetime.fromisoformat(last_message['sent_at'])
        # Ensure last_sent has timezone info
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)
        
        # Calculate next available time (60 hours from last message)
        next_available = last_sent + timedelta(hours=60)
        can_send_any = now >= next_available
        
        # Find blocked messages (same message within 60 days)
        blocked_messages = []
        for msg in messages:
            sent_at = datetime.fromisoformat(msg['sent_at'])
            # Ensure sent_at has timezone info
            if sent_at.tzinfo is None:
                sent_at = sent_at.replace(tzinfo=timezone.utc)
            if now - sent_at < timedelta(days=60):
                blocked_messages.append(msg['message_number'])
        
        return {
            'can_send_any': can_send_any,
            'next_available_at': next_available.isoformat() if not can_send_any else None,
            'last_message': last_message,
            'blocked_messages': list(set(blocked_messages))
        }
    
    async def cleanup_old_entries(self, max_age_days: int = 90) -> int:
        """
        Remove entries older than specified days to keep file size manageable.
        Returns number of entries removed.
        """
        await self._load_history()
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        removed_count = 0
        
        nations_to_remove = []
        for nation_id, data in self.history.items():
            # Remove individual messages older than cutoff
            old_count = len(data['messages'])
            data['messages'] = [
                msg for msg in data['messages']
                if (lambda sent_at: sent_at.replace(tzinfo=timezone.utc) if sent_at.tzinfo is None else sent_at)(
                    datetime.fromisoformat(msg['sent_at'])
                ) >= cutoff_date
            ]
            removed_count += old_count - len(data['messages'])
            
            # If no messages left, mark nation for removal
            if not data['messages']:
                nations_to_remove.append(nation_id)
        
        # Remove nations with no messages
        for nation_id in nations_to_remove:
            del self.history[nation_id]
            removed_count += 1
        
        if removed_count > 0:
            await self._save_history()
        
        return removed_count
    
    async def get_recruitment_stats(self) -> Dict:
        """Get detailed statistics about recruitment history."""
        await self._load_history()
        
        total_sent = sum(len(data['messages']) for data in self.history.values())
        unique_nations = len(self.history)
        
        # Count nations on cooldown
        nations_on_cooldown = 0
        next_available_times = []
        oldest_cooldown = None
        
        for nation_id, data in self.history.items():
            cooldown_info = await self.get_cooldown_info(nation_id)
            if not cooldown_info['can_send_any']:
                nations_on_cooldown += 1
                if cooldown_info['next_available_at']:
                    next_available = datetime.fromisoformat(cooldown_info['next_available_at'])
                    next_available_times.append(next_available)
                    if not oldest_cooldown or next_available < oldest_cooldown:
                        oldest_cooldown = next_available
        
        # Recent activity (last 10 messages)
        all_messages = []
        
        for nation_id, data in self.history.items():
            leader_name = data.get('leader_name', f'Nation {nation_id}')
            for msg in data['messages'][-10:]:  # Last 10 per nation
                sent_at = datetime.fromisoformat(msg['sent_at'])
                # Ensure sent_at has timezone info for consistent sorting
                if sent_at.tzinfo is None:
                    sent_at = sent_at.replace(tzinfo=timezone.utc)
                all_messages.append({
                    'nation_id': nation_id,
                    'leader_name': leader_name,
                    'message_num': msg['message_number'],
                    'sent_at': sent_at
                })
        
        # Sort by most recent and take top 10
        all_messages.sort(key=lambda x: x['sent_at'], reverse=True)
        recent = {}
        
        for msg in all_messages[:10]:
            time_ago = self._format_time_ago(msg['sent_at'])
            recent[msg['nation_id']] = {
                'leader_name': msg['leader_name'],
                'message_num': msg['message_num'],
                'time_ago': time_ago
            }
        
        return {
            'total_sent': total_sent,
            'unique_nations': unique_nations,
            'nations_on_cooldown': nations_on_cooldown,
            'next_available': self._format_next_available(next_available_times),
            'oldest_cooldown': self._format_time_ago(oldest_cooldown) if oldest_cooldown else "None",
            'recent_activity': recent
        }
    
    def _format_time_ago(self, dt: datetime) -> str:
        """Format a datetime as 'X time ago'."""
        if not dt:
            return "Never"
        
        now = datetime.now(timezone.utc)
        # Ensure dt has timezone info
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    
    def _format_next_available(self, times: List[datetime]) -> str:
        """Format the next available time."""
        if not times:
            return "All nations available"
        
        soonest = min(times)
        now = datetime.now(timezone.utc)
        
        # Ensure soonest has timezone info
        if soonest.tzinfo is None:
            soonest = soonest.replace(tzinfo=timezone.utc)
        
        if soonest <= now:
            return "Available now"
        
        diff = soonest - now
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''}"
        else:
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    async def start_batch_mode(self) -> None:
        """Start batch mode to defer saves until flush_batch_saves is called."""
        self._batch_mode = True
        self._pending_saves = 0
    
    async def flush_batch_saves(self):
        """Flush any pending saves and disable batch mode"""
        deferred_count = self._pending_saves
        if self._pending_saves > 0:
            await self._save_history()
            self._pending_saves = 0
        self._batch_mode = False
        return deferred_count
    
    async def end_batch_mode(self):
        """End batch mode and flush any pending saves"""
        return await self.flush_batch_saves()