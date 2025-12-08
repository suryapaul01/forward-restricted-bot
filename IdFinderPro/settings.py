import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, UserIsBlocked
from database.db import db
from config import ADMINS

# Store temporary states for multi-step processes
settings_state = {}

# Settings command
@Client.on_message(filters.private & filters.command(["settings"]))
async def settings_menu(client: Client, message: Message):
    """Main settings menu"""
    user_id = message.from_user.id
    settings = await db.get_user_settings(user_id)
    
    # Get current settings status
    destination = settings.get('forward_destination') if settings else None
    caption = settings.get('custom_caption') if settings else None
    thumbnail = settings.get('custom_thumbnail') if settings else None
    suffix = settings.get('filename_suffix') if settings else None
    index_count = settings.get('index_count', 0) if settings else 0
    send_as_document = await db.get_send_as_document(user_id)
    
    # Format status
    dest_status = "✅ Set" if destination else "❌ Not Set"
    caption_status = "✅ Set" if caption else "❌ Not Set"
    thumb_status = "✅ Set" if thumbnail else "❌ Not Set"
    suffix_status = "✅ Set" if suffix else "❌ Not Set"
    upload_type = "📄 Document" if send_as_document else "📤 Media"
    
    # Get replace words settings
    replace_caption = settings.get('replace_caption_words') if settings else None
    replace_filename = settings.get('replace_filename_words') if settings else None
    replace_caption_status = f"✅ {replace_caption[:20]}..." if replace_caption and len(replace_caption) > 20 else (f"✅ {replace_caption}" if replace_caption else "❌ Not Set")
    replace_filename_status = f"✅ {replace_filename[:20]}..." if replace_filename and len(replace_filename) > 20 else (f"✅ {replace_filename}" if replace_filename else "❌ Not Set")
    
    settings_text = f"""**⚙️ Forward Settings**

Configure how your downloaded files are forwarded to your channel.

**Current Settings:**
📤 **Upload Destination:** {dest_status}
✏️ **Custom Caption:** {caption_status}
🖼️ **Custom Thumbnail:** {thumb_status}
📝 **Filename Suffix:** {suffix_status}
🔢 **Index Count:** {index_count}
📦 **Upload Type:** {upload_type}
🔄 **Replace Caption Words:** {replace_caption_status}
📝 **Replace Filename Words:** {replace_filename_status}

**Click a button below to configure:**"""

    # Choose button text based on current setting
    upload_btn_text = "📄 Send as Document" if not send_as_document else "📤 Send as Media"
    
    buttons = [
        [InlineKeyboardButton("📤 Upload Destination", callback_data="set_destination"), InlineKeyboardButton("✏️ Set Caption", callback_data="set_caption")],
        [InlineKeyboardButton(upload_btn_text, callback_data="toggle_upload_type"), InlineKeyboardButton("📝 Set Suffix", callback_data="set_suffix")],
        [InlineKeyboardButton("🔢 Set Index Count", callback_data="reset_index"), InlineKeyboardButton("🖼️ Set Thumbnail", callback_data="set_thumbnail")],
        [InlineKeyboardButton("🔄 Remove/Replace Words", callback_data="replace_words_menu")],
        [InlineKeyboardButton("🗑️ Clear All Settings", callback_data="clear_settings"), InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
    ]
    
    await message.reply(settings_text, reply_markup=InlineKeyboardMarkup(buttons))


# Callback handler for settings
@Client.on_callback_query(filters.regex(r"^(set_|reset_|clear_|back_to_settings|reset_index_to_zero|toggle_upload_type|replace_words_)"))
async def settings_callback_handler(client: Client, query: CallbackQuery):
    """Handle settings button clicks"""
    data = query.data
    user_id = query.from_user.id
    
    if data == "set_destination":
        # Get bot username
        bot = await client.get_me()
        bot_username = bot.username
        
        # Check if user already has a destination set
        current_dest = await db.get_forward_destination(user_id)
        
        # Create links for adding bot to channel/group
        channel_link = f"https://t.me/{bot_username}?startchannel&admin=post_messages+edit_messages+delete_messages"
        group_link = f"https://t.me/{bot_username}?startgroup&admin=post_messages+edit_messages+delete_messages"
        
        if current_dest:
            # Get channel info
            try:
                chat_info = await client.get_chat(current_dest)
                channel_name = chat_info.title
                status_text = f"**Current Destination:** {channel_name}\n**ID:** `{current_dest}`\n\n"
            except:
                status_text = f"**Current Destination:** Set\n**ID:** `{current_dest}`\n\n"
        else:
            status_text = ""
        
        text = f"""**📤 Set Upload Destination**

{status_text}To forward files to your channel/group:

**1️⃣ Add bot as admin** with these permissions:
   • Post Messages
   • Edit Messages  
   • Delete Messages

**2️⃣ Click button below** to add bot to your channel/group

**3️⃣ After adding**, forward any message from that channel/group to me

**Note:** The message must be from the channel/group where you added me as admin."""

        settings_state[user_id] = {'action': 'set_destination'}
        
        # Create buttons
        buttons = [
            [InlineKeyboardButton("➕ Add to Channel", url=channel_link)],
            [InlineKeyboardButton("➕ Add to Group", url=group_link)]
        ]
        
        # Add reset button if destination is already set
        if current_dest:
            buttons.append([InlineKeyboardButton("🗑️ Reset Destination", callback_data="reset_destination")])
        
        buttons.append([InlineKeyboardButton("🔙 Back to Settings", callback_data="back_to_settings")])
        
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "set_caption":
        current_caption = await db.get_custom_caption(user_id)
        
        text = f"""**✏️ Set Custom Caption**

Set a custom caption template for your forwarded files.

**Available Variables:**
• `{{caption}}` - Original file caption
• `{{filename}}` - Name of the file
• `{{IndexCount}}` - Auto-increment counter

**Current Caption:**
{f"`{current_caption}`" if current_caption else "❌ Not set (using original caption)"}

**Example Template:**
```
📁 File: {{filename}}
📝 {{caption}}
🔢 #File{{IndexCount}}

@YourChannel
```

**Send your caption template now:**
(or click Reset to remove custom caption)"""

        settings_state[user_id] = {'action': 'set_caption'}
        
        buttons = [
            [InlineKeyboardButton("🗑️ Reset Caption", callback_data="reset_caption")],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="back_to_settings")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "set_thumbnail":
        current_thumb = await db.get_custom_thumbnail(user_id)
        thumb_status = "✅ Set" if current_thumb else "❌ Not Set"
        
        text = f"""**🖼️ Set Custom Thumbnail**

Upload a custom thumbnail for your videos and PDFs.

**Current Status:** {thumb_status}

**How to set:**
1. Send me an image/photo now
2. I'll save it as your custom thumbnail
3. All videos/PDFs will use this thumbnail when forwarded

**Image Requirements:**
• Format: JPG, PNG
• Recommended: 320x320 or 1280x720
• Size: Under 200KB recommended

**Note:** Thumbnails only work for videos and PDF documents.

**Send your thumbnail image now:**
(or click Reset to remove custom thumbnail)"""

        settings_state[user_id] = {'action': 'set_thumbnail'}
        
        buttons = [
            [InlineKeyboardButton("🗑️ Reset Thumbnail", callback_data="reset_thumbnail")],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="back_to_settings")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "set_suffix":
        current_suffix = await db.get_filename_suffix(user_id)
        
        text = f"""**📝 Set Filename Suffix**

Add a suffix to all filenames (useful for copyright/branding).

**Current Suffix:**
{f"`{current_suffix}`" if current_suffix else "❌ Not set"}

**Example:**
Original: `Movie.mp4`
With suffix `@MyChannel`: `Movie@MyChannel.mp4`

**How it works:**
The suffix is added **before the file extension**.

**Send your suffix now:**
Example: `@YourChannel` or `_backup` etc.

(or click Reset to remove suffix)"""

        settings_state[user_id] = {'action': 'set_suffix'}
        
        buttons = [
            [InlineKeyboardButton("🗑️ Reset Suffix", callback_data="reset_suffix")],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="back_to_settings")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "set_filters":
        # Show filter options
        settings = await db.get_user_settings(user_id)
        
        # Get filter statuses
        filter_text = settings.get('filter_text', True) if settings else True
        filter_doc = settings.get('filter_document', True) if settings else True
        filter_video = settings.get('filter_video', True) if settings else True
        filter_photo = settings.get('filter_photo', True) if settings else True
        filter_audio = settings.get('filter_audio', True) if settings else True
        filter_voice = settings.get('filter_voice', True) if settings else True
        filter_anim = settings.get('filter_animation', True) if settings else True
        filter_sticker = settings.get('filter_sticker', True) if settings else True
        filter_poll = settings.get('filter_poll', True) if settings else True
        
        # Create status emojis
        text_status = "✅" if filter_text else "❌"
        doc_status = "✅" if filter_doc else "❌"
        video_status = "✅" if filter_video else "❌"
        photo_status = "✅" if filter_photo else "❌"
        audio_status = "✅" if filter_audio else "❌"
        voice_status = "✅" if filter_voice else "❌"
        anim_status = "✅" if filter_anim else "❌"
        sticker_status = "✅" if filter_sticker else "❌"
        poll_status = "✅" if filter_poll else "❌"
        
        text = f"""**🎚️ File Type Filters**

Configure which file types to forward to your channel.

**Current Filters:**
✏️ Text: {text_status}
📄 Document: {doc_status}
🎬 Video: {video_status}
📸 Photo: {photo_status}
🎵 Audio: {audio_status}
🎤 Voice: {voice_status}
🎨 Animation: {anim_status}
🎭 Sticker: {sticker_status}
📊 Poll: {poll_status}

**Click to toggle:**"""

        buttons = [
            [InlineKeyboardButton(f"✏️ Text {text_status}", callback_data="toggle_filter_text"), InlineKeyboardButton(f"📄 Document {doc_status}", callback_data="toggle_filter_document")],
            [InlineKeyboardButton(f"🎬 Video {video_status}", callback_data="toggle_filter_video"), InlineKeyboardButton(f"📸 Photo {photo_status}", callback_data="toggle_filter_photo")],
            [InlineKeyboardButton(f"🎵 Audio {audio_status}", callback_data="toggle_filter_audio"), InlineKeyboardButton(f"🎤 Voice {voice_status}", callback_data="toggle_filter_voice")],
            [InlineKeyboardButton(f"🎨 Animation {anim_status}", callback_data="toggle_filter_animation"), InlineKeyboardButton(f"🎭 Sticker {sticker_status}", callback_data="toggle_filter_sticker")],
            [InlineKeyboardButton(f"📊 Poll {poll_status}", callback_data="toggle_filter_poll")],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="back_to_settings")]
        ]
        
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "reset_index":
        text = """**🔢 Set Index Count**

Set a starting number for your {IndexCount} variable.

**Current Count:** Will be shown after you set it

**How it works:**
• You set a starting number (e.g., 100)
• Each file increments by 1
• File 1: 100, File 2: 101, File 3: 102, etc.

**Send your starting number now:**
Example: `1`, `100`, `500`, etc.

Or click Reset to set it back to 0."""

        settings_state[user_id] = {'action': 'set_index'}
        
        buttons = [
            [InlineKeyboardButton("🔄 Reset to 0", callback_data="reset_index_to_zero")],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="back_to_settings")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "clear_settings":
        # Clear all settings
        await db.set_forward_destination(user_id, None)
        await db.set_custom_caption(user_id, None)
        await db.set_custom_thumbnail(user_id, None)
        await db.set_filename_suffix(user_id, None)
        await db.reset_index_count(user_id)
        
        await query.answer("✅ All settings cleared!", show_alert=True)
        # Refresh settings menu
        await show_settings_menu(client, query.message, user_id, edit=True)
    
    elif data == "reset_caption":
        await db.set_custom_caption(user_id, None)
        await query.answer("✅ Caption reset!", show_alert=True)
        if user_id in settings_state:
            del settings_state[user_id]
        await show_settings_menu(client, query.message, user_id, edit=True)
    
    elif data == "reset_thumbnail":
        await db.set_custom_thumbnail(user_id, None)
        await query.answer("✅ Thumbnail reset!", show_alert=True)
        if user_id in settings_state:
            del settings_state[user_id]
        await show_settings_menu(client, query.message, user_id, edit=True)
    
    elif data == "reset_suffix":
        await db.set_filename_suffix(user_id, None)
        await query.answer("✅ Suffix reset!", show_alert=True)
        if user_id in settings_state:
            del settings_state[user_id]
        await show_settings_menu(client, query.message, user_id, edit=True)
    
    elif data == "reset_destination":
        await db.set_forward_destination(user_id, None)
        await query.answer("✅ Destination reset!", show_alert=True)
        if user_id in settings_state:
            del settings_state[user_id]
        await show_settings_menu(client, query.message, user_id, edit=True)
    
    elif data == "reset_index_to_zero":
        await db.reset_index_count(user_id)
        await query.answer("✅ Index count set to 0!", show_alert=True)
        if user_id in settings_state:
            del settings_state[user_id]
        await show_settings_menu(client, query.message, user_id, edit=True)
    
    elif data.startswith("toggle_filter_"):
        # Toggle filter
        filter_name = data.replace("toggle_", "")
        new_value = await db.toggle_filter(user_id, filter_name)
        
        status = "enabled" if new_value else "disabled"
        await query.answer(f"✅ Filter {status}!", show_alert=False)
        
        # Refresh filters page by manually rebuilding it
        settings = await db.get_user_settings(user_id)
        
        # Get filter statuses
        filter_text = settings.get('filter_text', True) if settings else True
        filter_doc = settings.get('filter_document', True) if settings else True
        filter_video = settings.get('filter_video', True) if settings else True
        filter_photo = settings.get('filter_photo', True) if settings else True
        filter_audio = settings.get('filter_audio', True) if settings else True
        filter_voice = settings.get('filter_voice', True) if settings else True
        filter_anim = settings.get('filter_animation', True) if settings else True
        filter_sticker = settings.get('filter_sticker', True) if settings else True
        filter_poll = settings.get('filter_poll', True) if settings else True
        
        # Create status emojis
        text_status = "✅" if filter_text else "❌"
        doc_status = "✅" if filter_doc else "❌"
        video_status = "✅" if filter_video else "❌"
        photo_status = "✅" if filter_photo else "❌"
        audio_status = "✅" if filter_audio else "❌"
        voice_status = "✅" if filter_voice else "❌"
        anim_status = "✅" if filter_anim else "❌"
        sticker_status = "✅" if filter_sticker else "❌"
        poll_status = "✅" if filter_poll else "❌"
        
        text = f"""**🎚️ File Type Filters**

Configure which file types to forward to your channel.

**Current Filters:**
✏️ Text: {text_status}
📄 Document: {doc_status}
🎬 Video: {video_status}
📸 Photo: {photo_status}
🎵 Audio: {audio_status}
🎤 Voice: {voice_status}
🎨 Animation: {anim_status}
🎭 Sticker: {sticker_status}
📊 Poll: {poll_status}

**Click to toggle:**"""

        buttons = [
            [InlineKeyboardButton(f"✏️ Text {text_status}", callback_data="toggle_filter_text"), InlineKeyboardButton(f"📄 Document {doc_status}", callback_data="toggle_filter_document")],
            [InlineKeyboardButton(f"🎬 Video {video_status}", callback_data="toggle_filter_video"), InlineKeyboardButton(f"📸 Photo {photo_status}", callback_data="toggle_filter_photo")],
            [InlineKeyboardButton(f"🎵 Audio {audio_status}", callback_data="toggle_filter_audio"), InlineKeyboardButton(f"🎤 Voice {voice_status}", callback_data="toggle_filter_voice")],
            [InlineKeyboardButton(f"🎨 Animation {anim_status}", callback_data="toggle_filter_animation"), InlineKeyboardButton(f"🎭 Sticker {sticker_status}", callback_data="toggle_filter_sticker")],
            [InlineKeyboardButton(f"📊 Poll {poll_status}", callback_data="toggle_filter_poll")],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="back_to_settings")]
        ]
        
        try:
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        except:
            pass  # Ignore if message didn't change
        return
    
    elif data == "toggle_upload_type":
        # Toggle between sending as document or media
        new_value = await db.toggle_send_as_document(user_id)
        
        if new_value:
            await query.answer("✅ Files will now be sent as documents!", show_alert=True)
        else:
            await query.answer("✅ Files will now be sent as media!", show_alert=True)
        
        # Refresh settings menu
        await show_settings_menu(client, query.message, user_id, edit=True)
    
    elif data == "replace_words_menu":
        #Show replace words submenu
        caption_pattern = await db.get_replace_caption_words(user_id)
        filename_pattern = await db.get_replace_filename_words(user_id)
        
        caption_status = "✅ Set" if caption_pattern else "❌ Not Set"
        filename_status = "✅ Set" if filename_pattern else "❌ Not Set"
        
        text = f"""**🔄 Remove/Replace Words**

Configure word replacements for captions and filenames.

**Current Status:**
✏️ **Caption:** {caption_status}
📝 **Filename:** {filename_status}

**How it works:**
Use pattern: `find1:change1|find2:change2`

• **find**: Word to change
• **change**: Replacement (leave empty to remove)
• **|**: Separator for multiple rules

**Example:**
`apple:banana|the|sun:moon`

This will:
• Change "apple" → "banana"
• Remove "the"
• Change "sun" → "moon"

Works with words separated by space, comma, `-`, or `_`

**Choose what to configure:**"""
        
        buttons = [
            [InlineKeyboardButton("✏️ Caption", callback_data="replace_words_caption"), InlineKeyboardButton("📝 Filename", callback_data="replace_words_filename")],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="back_to_settings")]
        ]
        
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "replace_words_caption":
        current_pattern = await db.get_replace_caption_words(user_id)
        
        text = f"""**✏️ Caption Word Replacement**

Set find:replace rules for captions.

**Current Pattern:**
{f"`{current_pattern}`" if current_pattern else "❌ Not set"}

**Pattern Format:**
`find1:change1|find2:change2|...`

**Examples:**
• `hello:hi` - Replace "hello" with "hi"
• `test` - Remove word "test"
• `old:new|bad:good|spam` - Multiple rules

**Send your pattern now:**
(or click Reset to clear)"""
        
        settings_state[user_id] = {'action': 'set_replace_caption'}
        
        buttons = [
            [InlineKeyboardButton("🗑️ Reset Pattern", callback_data="reset_replace_caption")],
            [InlineKeyboardButton("🔙 Back", callback_data="replace_words_menu")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "replace_words_filename":
        current_pattern = await db.get_replace_filename_words(user_id)
        
        text = f"""**📝 Filename Word Replacement**

Set find:replace rules for filenames.

**Current Pattern:**
{f"`{current_pattern}`" if current_pattern else "❌ Not set"}

**Pattern Format:**
`find1:change1|find2:change2|...`

**Examples:**
• `sample:example` - Replace "sample" with "example"
• `test` - Remove word "test"
• `old:new|bad:good|temp` - Multiple rules

**Note:** Works with separators: space, comma, `-`, `_`

**Send your pattern now:**
(or click Reset to clear)"""
        
        settings_state[user_id] = {'action': 'set_replace_filename'}
        
        buttons = [
            [InlineKeyboardButton("🗑️ Reset Pattern", callback_data="reset_replace_filename")],
            [InlineKeyboardButton("🔙 Back", callback_data="replace_words_menu")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "reset_replace_caption":
        await db.set_replace_caption_words(user_id, None)
        await query.answer("✅ Caption replacement pattern cleared!", show_alert=True)
        if user_id in settings_state:
            del settings_state[user_id]
        await show_settings_menu(client, query.message, user_id, edit=True)
    
    elif data == "reset_replace_filename":
        await db.set_replace_filename_words(user_id, None)
        await query.answer("✅ Filename replacement pattern cleared!", show_alert=True)
        if user_id in settings_state:
            del settings_state[user_id]
        await show_settings_menu(client, query.message, user_id, edit=True)
    
    elif data == "back_to_settings":
        # Clear state and go back to settings menu
        if user_id in settings_state:
            del settings_state[user_id]
        await show_settings_menu(client, query.message, user_id, edit=True)
    
    await query.answer()


async def show_settings_menu(client: Client, message: Message, user_id: int, edit: bool = False):
    """Show settings menu"""
    settings = await db.get_user_settings(user_id)
    
    # Get current settings status
    destination = settings.get('forward_destination') if settings else None
    caption = settings.get('custom_caption') if settings else None
    thumbnail = settings.get('custom_thumbnail') if settings else None
    suffix = settings.get('filename_suffix') if settings else None
    index_count = settings.get('index_count', 0) if settings else 0
    send_as_document = await db.get_send_as_document(user_id)
    
    # Format status
    dest_status = "✅ Set" if destination else "❌ Not Set"
    caption_status = "✅ Set" if caption else "❌ Not Set"
    thumb_status = "✅ Set" if thumbnail else "❌ Not Set"
    suffix_status = "✅ Set" if suffix else "❌ Not Set"
    upload_type = "📄 Document" if send_as_document else "📤 Media"
    
    # Get replace words settings
    replace_caption = settings.get('replace_caption_words') if settings else None
    replace_filename = settings.get('replace_filename_words') if settings else None
    replace_caption_status = f"✅ {replace_caption[:20]}..." if replace_caption and len(replace_caption) > 20 else (f"✅ {replace_caption}" if replace_caption else "❌ Not Set")
    replace_filename_status = f"✅ {replace_filename[:20]}..." if replace_filename and len(replace_filename) > 20 else (f"✅ {replace_filename}" if replace_filename else "❌ Not Set")
    
    settings_text = f"""**⚙️ Forward Settings**

Configure how your downloaded files are forwarded to your channel.

**Current Settings:**
📤 **Upload Destination:** {dest_status}
✏️ **Custom Caption:** {caption_status}
🖼️ **Custom Thumbnail:** {thumb_status}
📝 **Filename Suffix:** {suffix_status}
🔢 **Index Count:** {index_count}
📦 **Upload Type:** {upload_type}
🔄 **Replace Caption Words:** {replace_caption_status}
📝 **Replace Filename Words:** {replace_filename_status}

**Click a button below to configure:**"""

    # Choose button text based on current setting
    upload_btn_text = "📄 Send as Document" if not send_as_document else "📤 Send as Media"
    
    buttons = [
        [InlineKeyboardButton("📤 Upload Destination", callback_data="set_destination"), InlineKeyboardButton("✏️ Set Caption", callback_data="set_caption")],
        [InlineKeyboardButton(upload_btn_text, callback_data="toggle_upload_type"), InlineKeyboardButton("📝 Set Suffix", callback_data="set_suffix")],
        [InlineKeyboardButton("🔢 Set Index Count", callback_data="reset_index"), InlineKeyboardButton("🖼️ Set Thumbnail", callback_data="set_thumbnail")],
        [InlineKeyboardButton("🔄 Remove/Replace Words", callback_data="replace_words_menu")],
        [InlineKeyboardButton("🗑️ Clear All Settings", callback_data="clear_settings"), InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
    ]
    
    if edit:
        try:
            await message.edit_text(settings_text, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception as e:
            # Handle MESSAGE_NOT_MODIFIED error (content is same)
            if "MESSAGE_NOT_MODIFIED" in str(e):
                pass  # Ignore, message is already correct
            else:
                # For other errors, try to send a new message
                try:
                    await message.reply(settings_text, reply_markup=InlineKeyboardMarkup(buttons))
                except:
                    pass
    else:
        await message.reply(settings_text, reply_markup=InlineKeyboardMarkup(buttons))


# Handle incoming messages for settings configuration
@Client.on_message(filters.private & (filters.text | filters.photo | filters.forwarded), group=5)
async def handle_settings_input(client: Client, message: Message):
    """Handle user input for settings configuration"""
    user_id = message.from_user.id
    
    # Check if user is in settings state
    if user_id not in settings_state:
        return  # Not configuring settings, continue to other handlers
    
    state = settings_state[user_id]
    action = state.get('action')
    
    if action == 'set_destination':
        # User should forward a message from their channel
        if not message.forward_from_chat:
            return await message.reply("❌ **Please forward a message from your channel/group** where you added me as admin.\n\n💡 **How to forward:**\n1. Go to your channel/group\n2. Select any message\n3. Click Forward\n4. Send it to me")
        
        chat = message.forward_from_chat
        chat_id = chat.id
        chat_title = chat.title
        chat_type = str(chat.type)
        
        # Debug: Print chat type for troubleshooting
        print(f"[DEBUG] Chat type received: {chat_type}, Chat ID: {chat_id}, Title: {chat_title}")
        
        # Verify chat type - accept both old and new Pyrogram format
        valid_types = ["channel", "supergroup", "ChatType.CHANNEL", "ChatType.SUPERGROUP"]
        if not any(t in chat_type for t in ["channel", "supergroup", "CHANNEL", "SUPERGROUP"]):
            return await message.reply(f"❌ **Invalid chat type!**\n\nReceived: `{chat_type}`\n\nPlease forward from a **channel** or **supergroup** only.\n\n💡 Regular groups are not supported, use supergroups.")
        
        # Check if bot is admin in that channel
        try:
            bot = await client.get_me()
            
            # Try to get bot member info
            try:
                member = await client.get_chat_member(chat_id, bot.id)
                member_status = str(member.status)
                
                print(f"[DEBUG] Bot member status: {member_status}")
                
                # Check status - handle both enum and string formats
                is_admin = any(status in member_status.lower() for status in ["administrator", "creator", "admin", "owner"])
                
                if not is_admin:
                    return await message.reply(f"""❌ **I'm not an admin in {chat_title}!**

**Current Status:** {member_status}

**Solution:**
1. Go to your channel/group
2. Add me as administrator
3. Give me these permissions:
   • Post Messages
   • Edit Messages
   • Delete Messages
4. Try again by forwarding a message to me""")
                
                # Check permissions if available
                if hasattr(member, 'privileges') and member.privileges:
                    if not (member.privileges.can_post_messages or member.privileges.can_edit_messages):
                        return await message.reply(f"""⚠️ **Limited Permissions in {chat_title}!**

I need these permissions:
• ✅ Post Messages
• ✅ Edit Messages
• ✅ Delete Messages

Please update my admin permissions and try again.""")
                
                # Save destination
                await db.set_forward_destination(user_id, chat_id)
                
                # Clear state
                del settings_state[user_id]
                
                await message.reply(f"""✅ **Upload destination set successfully!**

**Channel:** {chat_title}
**ID:** `{chat_id}`
**Bot Status:** Admin ✓

All your downloaded files will now be forwarded to this channel!

Use /settings to configure more options.""")
            
            except UserNotParticipant:
                return await message.reply(f"""❌ **Bot is not in {chat_title}!**

**Solution:**
1. Click the "Add to Channel/Group" button in settings
2. Select your channel/group
3. Make sure to add me as **Administrator**
4. Try again""")
            except ChatAdminRequired:
                return await message.reply(f"""❌ **Cannot verify admin status in {chat_title}!**

**Possible reasons:**
• Bot is not added to the channel yet
• Bot is added but not as admin
• Channel privacy settings

**Solution:**
Add me as administrator with proper permissions and try again.""")
        
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Destination setup failed: {error_msg}")
            return await message.reply(f"""❌ **Error setting destination**

**Error:** `{error_msg}`

**Troubleshooting:**
1. Make sure the channel/group is accessible
2. Add me as admin with proper permissions
3. Try forwarding a different message
4. Contact support if issue persists

Need help? Use /help""")
    
    elif action == 'set_caption':
        # User is sending caption template
        if not message.text:
            return await message.reply("❌ **Please send a text caption template.**")
        
        caption_template = message.text
        
        # Validate template
        if len(caption_template) > 1024:
            return await message.reply("❌ **Caption too long!**\n\nMax 1024 characters allowed.")
        
        # Save caption
        await db.set_custom_caption(user_id, caption_template)
        
        # Clear state
        del settings_state[user_id]
        
        await message.reply(f"""✅ **Custom caption set successfully!**

**Your Template:**
```
{caption_template}
```

**Variables you can use:**
• `{{caption}}` - Original caption
• `{{filename}}` - File name
• `{{IndexCount}}` - Auto counter

This caption will be applied to all forwarded files!

Use /settings to change it anytime.""")
    
    elif action == 'set_thumbnail':
        # User is sending thumbnail image
        if not message.photo:
            return await message.reply("❌ **Please send a photo/image for thumbnail.**")
        
        # Get the largest photo size
        photo = message.photo
        file_id = photo.file_id
        
        # Save thumbnail
        await db.set_custom_thumbnail(user_id, file_id)
        
        # Clear state
        del settings_state[user_id]
        
        await message.reply(f"""✅ **Custom thumbnail set successfully!**

This thumbnail will be used for all videos and PDFs when forwarding!

**Note:** Thumbnails only work for:
• Videos (MP4, MKV, etc.)
• PDF Documents

Use /settings to change it anytime.""")
    
    elif action == 'set_suffix':
        # User is sending suffix text
        if not message.text:
            return await message.reply("❌ **Please send a text suffix.**")
        
        suffix = message.text.strip()
        
        # Validate suffix
        if len(suffix) > 50:
            return await message.reply("❌ **Suffix too long!**\n\nMax 50 characters allowed.")
        
        # Save suffix
        await db.set_filename_suffix(user_id, suffix)
        
        # Clear state
        del settings_state[user_id]
        
        await message.reply(f"""✅ **Filename suffix set successfully!**

**Your Suffix:** `{suffix}`

**Example:**
Original: `Movie.mp4`
With suffix: `Movie{suffix}.mp4`

The suffix will be added to all forwarded files!

Use /settings to change it anytime.""")
    
    elif action == 'set_index':
        # User is sending index count number
        if not message.text:
            return await message.reply("❌ **Please send a number.**")
        
        try:
            index_num = int(message.text.strip())
            
            # Validate number
            if index_num < 0:
                return await message.reply("❌ **Number must be 0 or positive!**")
            
            if index_num > 999999:
                return await message.reply("❌ **Number too large!**\n\nMax 999999 allowed.")
            
            # Save index count
            await db.set_index_count(user_id, index_num)
            
            # Clear state
            del settings_state[user_id]
            
            await message.reply(f"""✅ **Index count set successfully!**

**Starting Number:** `{index_num}`

**How it works:**
• Next file will use: {index_num}
• Then: {index_num + 1}, {index_num + 2}, etc.

The counter will increment automatically with each upload!

Use /settings to change it anytime.""")
        
        except ValueError:
            return await message.reply("❌ **Invalid number!**\n\nPlease send a valid integer number.")
    
    elif action == 'set_replace_caption':
        # User is sending caption replacement pattern
        if not message.text:
            return await message.reply("❌ **Please send a text pattern.**")
        
        pattern = message.text.strip()
        
        # Validate pattern
        if len(pattern) > 500:
            return await message.reply("❌ **Pattern too long!**\n\nMax 500 characters allowed.")
        
        # Save pattern
        await db.set_replace_caption_words(user_id, pattern)
        
        # Clear state
        del settings_state[user_id]
        
        await message.reply(f"""✅ **Caption replacement pattern set!**

**Your Pattern:** `{pattern}`

**Example results:**
If your pattern is `test:demo|old:new|remove`
• "test video" → "demo video"
• "old_file" → "new_file"
• "remove this" → " this"

This will be applied to all future file captions!

Use /settings to change it anytime.""")
    
    elif action == 'set_replace_filename':
        # User is sending filename replacement pattern
        if not message.text:
            return await message.reply("❌ **Please send a text pattern.**")
        
        pattern = message.text.strip()
        
        # Validate pattern
        if len(pattern) > 500:
            return await message.reply("❌ **Pattern too long!**\n\nMax 500 characters allowed.")
        
        # Save pattern
        await db.set_replace_filename_words(user_id, pattern)
        
        # Clear state
        del settings_state[user_id]
        
        await message.reply(f"""✅ **Filename replacement pattern set!**

**Your Pattern:** `{pattern}`

**Example results:**
If your pattern is `sample:example|test|old:new`
• "sample_video.mp4" → "example_video.mp4"
• "test_file.pdf" → "_file.pdf"
• "old-movie.mkv" → "new-movie.mkv"

This will be applied to all future filenames!

Use /settings to change it anytime.""")

