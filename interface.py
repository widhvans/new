"""User interface and navigation handlers."""
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def setup_handlers(app: Client):
    """Register interface-related handlers."""
    
    @app.on_message(filters.command("start"))
    async def start_command(client, message):
        """Handle /start command with welcome message and navigation."""
        welcome_text = (
            "Welcome to StorageBot! 📦\n"
            "Your personal media storage and sharing solution.\n"
            "Use the buttons below to begin."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Let's Begin", callback_data="main_menu")],
            [InlineKeyboardButton("Help", callback_data="help_menu")]
        ])
        await message.reply(welcome_text, reply_markup=keyboard)

    @app.on_callback_query(filters.regex("main_menu"))
    async def main_menu(client, query):
        """Display main menu."""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Manage Channels", callback_data="manage_channels")],
            [InlineKeyboardButton("Set Shortener", callback_data="set_shortener")],
            [InlineKeyboardButton("Clone Bot", callback_data="clone_bot")],
            [InlineKeyboardButton("Stats", callback_data="stats")],
            [InlineKeyboardButton("Go Back", callback_data="start")]
        ])
        await query.message.edit("Main Menu:", reply_markup=keyboard)

    @app.on_callback_query(filters.regex("help_menu"))
    async def help_menu(client, query):
        """Display help menu."""
        help_text = (
            "Help:\n"
            "- Upload files to store them.\n"
            "- Connect channels for posting/storage.\n"
            "- Use /shortlink to set shortener.\n"
            "- Search files with /search.\n"
            "- Admins can broadcast with /broadcast."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Go Back", callback_data="start")]
        ])
        await query.message.edit(help_text, reply_markup=keyboard)
