from pyrogram import Client, filters
from pyrogram.types import Message
from database.db import db
from config import ADMINS
import time as time_module

# Import active_downloads from start.py
from IdFinderPro.start import active_downloads

@Client.on_message(filters.command(["processes"]) & filters.user(ADMINS))
async def show_active_processes(client: Client, message: Message):
    """Admin command to view active download processes"""
    
    if not active_downloads:
        await message.reply("📭 **No Active Downloads**\n\nThere are currently no files being downloaded.")
        return
    
    current_time = time_module.time()
    process_list = []
    
    for user_id, info in active_downloads.items():
        # Get user info
        try:
            user = await db.col.find_one({'id': user_id})
            username = user.get('name', 'Unknown') if user else 'Unknown'
        except:
            username = 'Unknown'
        
        # Calculate duration
        duration = int(current_time - info['started'])
        minutes = duration // 60
        seconds = duration % 60
        
        # Format filename (show only last part)
        filename = info['file'].split('/')[-1]
        
        process_list.append(
            f"**User:** {username} (`{user_id}`)\n"
            f"**File:** `{filename}`\n"
            f"**Duration:** {minutes}m {seconds}s"
        )
    
    processes_text = "\n\n".join(process_list)
    
    response = f"""🔄 **Active Download Processes**

**Total Active:** {len(active_downloads)}

{processes_text}

💡 Use `/cancel` to stop any user's process if needed."""

    await message.reply(response)
