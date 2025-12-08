import motor.motor_asyncio
from config import DB_NAME, DB_URI

class Database:
    
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users

    def new_user(self, id, name):
        return dict(
            id = id,
            name = name,
            session = None,
            is_premium = False,
            premium_expiry = None,
            downloads_today = 0,
            last_download_date = None,
            # Forward settings
            forward_destination = None,  # Channel ID for forwarding
            custom_caption = None,  # Custom caption template
            custom_thumbnail = None,  # File ID of custom thumbnail
            filename_suffix = None,  # Suffix for filename
            index_count = 0,  # Counter for {IndexCount} variable
            # Send as document toggle
            send_as_document = False,  # If True, send videos/photos/audio as documents
            # Replace words settings
            replace_caption_words = None,  # Pattern: "find1:change1|find2:change2"
            replace_filename_words = None,  # Pattern: "find1:change1|find2:change2"
            # File type filters (all enabled by default)
            filter_text = True,
            filter_document = True,
            filter_video = True,
            filter_photo = True,
            filter_audio = True,
            filter_voice = True,
            filter_animation = True,
            filter_sticker = True,
            filter_poll = True
        )
    
    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user)
    
    async def is_user_exist(self, id):
        user = await self.col.find_one({'id':int(id)})
        return bool(user)
    
    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count

    async def get_all_users(self):
        return self.col.find({})

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})

    async def set_session(self, id, session):
        await self.col.update_one({'id': int(id)}, {'$set': {'session': session}})

    async def get_session(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('session') if user else None
    
    # Premium membership methods
    async def set_premium(self, user_id, is_premium, expiry_timestamp=None):
        """Set premium status for user"""
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {'is_premium': is_premium, 'premium_expiry': expiry_timestamp}}
        )
    
    async def is_premium(self, user_id):
        """Check if user is premium"""
        import time
        user = await self.col.find_one({'id': int(user_id)})
        if not user:
            return False
        
        if user.get('is_premium'):
            expiry = user.get('premium_expiry')
            if expiry is None or expiry > time.time():
                return True
            else:
                # Expired, remove premium
                await self.set_premium(user_id, False, None)
                return False
        return False
    
    async def get_all_premium_users(self):
        """Get all premium users"""
        import time
        cursor = self.col.find({'is_premium': True})
        premium_users = []
        async for user in cursor:
            if user.get('premium_expiry') is None or user.get('premium_expiry') > time.time():
                premium_users.append(user)
        return premium_users
    
    # Download tracking for rate limiting
    async def check_and_update_downloads(self, user_id):
        """Check and update download count for rate limiting"""
        from datetime import datetime, date
        
        user = await self.col.find_one({'id': int(user_id)})
        if not user:
            return False
        
        today = str(date.today())
        last_date = user.get('last_download_date')
        downloads_today = user.get('downloads_today', 0)
        
        # Reset if new day
        if last_date != today:
            downloads_today = 0
        
        # Check limits
        is_premium_user = await self.is_premium(user_id)
        limit = 999999 if is_premium_user else 10  # Premium: Unlimited, Free: 10/day
        
        if downloads_today >= limit:
            return False  # Limit exceeded
        
        # Update count
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {'downloads_today': downloads_today + 1, 'last_download_date': today}}
        )
        return True
    
    async def get_download_count(self, user_id):
        """Get today's download count"""
        from datetime import date
        user = await self.col.find_one({'id': int(user_id)})
        if not user:
            return 0
        
        today = str(date.today())
        if user.get('last_download_date') == today:
            return user.get('downloads_today', 0)
        return 0
    
    # Forward settings methods
    async def set_forward_destination(self, user_id, channel_id):
        """Set forward destination channel"""
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {'forward_destination': channel_id}}
        )
    
    async def get_forward_destination(self, user_id):
        """Get forward destination channel"""
        user = await self.col.find_one({'id': int(user_id)})
        return user.get('forward_destination') if user else None
    
    async def set_custom_caption(self, user_id, caption):
        """Set custom caption template"""
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {'custom_caption': caption}}
        )
    
    async def get_custom_caption(self, user_id):
        """Get custom caption template"""
        user = await self.col.find_one({'id': int(user_id)})
        return user.get('custom_caption') if user else None
    
    async def set_custom_thumbnail(self, user_id, file_id):
        """Set custom thumbnail file ID"""
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {'custom_thumbnail': file_id}}
        )
    
    async def get_custom_thumbnail(self, user_id):
        """Get custom thumbnail file ID"""
        user = await self.col.find_one({'id': int(user_id)})
        return user.get('custom_thumbnail') if user else None
    
    async def set_filename_suffix(self, user_id, suffix):
        """Set filename suffix"""
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {'filename_suffix': suffix}}
        )
    
    async def get_filename_suffix(self, user_id):
        """Get filename suffix"""
        user = await self.col.find_one({'id': int(user_id)})
        return user.get('filename_suffix') if user else None
    
    async def increment_index_count(self, user_id):
        """Get current index count and increment for next use"""
        # Get current value first
        user = await self.col.find_one({'id': int(user_id)})
        current_count = user.get('index_count', 0) if user else 0
        
        # Increment for next time
        await self.col.update_one(
            {'id': int(user_id)},
            {'$inc': {'index_count': 1}}
        )
        
        return current_count
    
    async def reset_index_count(self, user_id):
        """Reset index count to 0"""
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {'index_count': 0}}
        )
    
    async def set_index_count(self, user_id, count):
        """Set index count to specific number"""
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {'index_count': int(count)}}
        )
    
    async def get_index_count(self, user_id):
        """Get current index count"""
        user = await self.col.find_one({'id': int(user_id)})
        return user.get('index_count', 0) if user else 0
    
    async def get_user_settings(self, user_id):
        """Get all user settings"""
        user = await self.col.find_one({'id': int(user_id)})
        if not user:
            return None
        return {
            'forward_destination': user.get('forward_destination'),
            'custom_caption': user.get('custom_caption'),
            'custom_thumbnail': user.get('custom_thumbnail'),
            'filename_suffix': user.get('filename_suffix'),
            'index_count': user.get('index_count', 0),
            # File type filters
            'filter_text': user.get('filter_text', True),
            'filter_document': user.get('filter_document', True),
            'filter_video': user.get('filter_video', True),
            'filter_photo': user.get('filter_photo', True),
            'filter_audio': user.get('filter_audio', True),
            'filter_voice': user.get('filter_voice', True),
            'filter_animation': user.get('filter_animation', True),
            'filter_sticker': user.get('filter_sticker', True),
            'filter_poll': user.get('filter_poll', True)
        }
    
    # Filter methods
    async def toggle_filter(self, user_id, filter_name):
        """Toggle a file type filter on/off"""
        user = await self.col.find_one({'id': int(user_id)})
        if not user:
            return False
        
        current_value = user.get(filter_name, True)
        new_value = not current_value
        
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {filter_name: new_value}}
        )
        return new_value
    
    async def get_filter_status(self, user_id, filter_name):
        """Get status of a specific filter"""
        user = await self.col.find_one({'id': int(user_id)})
        if not user:
            return True  # Default enabled
        return user.get(filter_name, True)
    
    # Send as document toggle methods
    async def toggle_send_as_document(self, user_id):
        """Toggle send as document setting"""
        user = await self.col.find_one({'id': int(user_id)})
        if not user:
            return False
        
        current_value = user.get('send_as_document', False)
        new_value = not current_value
        
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {'send_as_document': new_value}}
        )
        return new_value
    
    async def get_send_as_document(self, user_id):
        """Get send as document status"""
        user = await self.col.find_one({'id': int(user_id)})
        if not user:
            return False  # Default to media
        return user.get('send_as_document', False)
    
    # Replace words methods
    async def set_replace_caption_words(self, user_id, pattern):
        """Set caption word replacement pattern"""
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {'replace_caption_words': pattern}}
        )
    
    async def get_replace_caption_words(self, user_id):
        """Get caption word replacement pattern"""
        user = await self.col.find_one({'id': int(user_id)})
        return user.get('replace_caption_words') if user else None
    
    async def set_replace_filename_words(self, user_id, pattern):
        """Set filename word replacement pattern"""
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {'replace_filename_words': pattern}}
        )
    
    async def get_replace_filename_words(self, user_id):
        """Get filename word replacement pattern"""
        user = await self.col.find_one({'id': int(user_id)})
        return user.get('replace_filename_words') if user else None

db = Database(DB_URI, DB_NAME)
