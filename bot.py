import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters, ConversationHandler
)

import database as db
import keyboards as kb
import cloudrun_worker as worker
import vless_helper as vless

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
SSO_LINK = 1
MANUAL_PROJECT_ID, MANUAL_EMAIL, MANUAL_PASSWORD = range(2, 5)
ADMIN_ADD_ID = 5
ADMIN_REMOVE_ID = 6
ADMIN_BROADCAST_MSG = 7

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    # Handle referral
    referred_by = None
    if context.args and context.args[0].startswith("ref_"):
        try:
            referred_by = int(context.args[0].split("_")[1])
        except ValueError:
            pass

    # Initialize user in DB
    db.add_user(user.id, user.username, user.first_name, referred_by)

    is_admin = db.is_admin(user.id)
    keyboard = kb.get_main_menu(is_admin)

    msg = "👋 Bienvenue sur DarkTunnel Bot !\n\nUtilisez le menu ci-dessous pour naviguer."
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=msg, reply_markup=keyboard)
    else:
        await update.message.reply_text(msg, reply_markup=keyboard)

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = update.effective_user.id

    if data == "menu_home":
        is_admin = db.is_admin(user_id)
        keyboard = kb.get_main_menu(is_admin)
        await query.edit_message_text("🏠 Menu Principal :", reply_markup=keyboard)

    elif data == "nav_deploy":
        keyboard = kb.get_deploy_menu()
        await query.edit_message_text("🚀 Choisissez la méthode de déploiement :", reply_markup=keyboard)

    elif data == "nav_profile":
        stats = db.get_user_stats(user_id)
        if stats:
            text = f"👤 **Mon Profil**\n\n💰 Crédits: {stats['credits']}\n🔄 Déploiements gratuits aujourd'hui: {stats['daily_quota_used']}/1\n📅 Dernière réinitialisation: {stats['last_quota_reset']}"
        else:
            text = "Profil introuvable."
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=kb.get_back_button())

    elif data == "nav_referral":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        stats = db.get_referral_stats(user_id)
        text = f"🎁 **Parrainage**\n\nInvitez vos amis et gagnez +2 crédits pour chaque inscription !\n\n🔗 Votre lien : `{ref_link}`\n\n👥 Filleuls: {stats}"
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=kb.get_back_button())

    elif data == "nav_shop":
        text = "🏪 **Boutique**\n\n(Fonctionnalité en cours de développement)"
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=kb.get_back_button())

    elif data == "nav_help":
        text = "📖 **Guide DarkTunnel**\n\nCeci est le guide..."
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=kb.get_back_button())

    elif data == "nav_admin":
        if not db.is_admin(user_id):
            await query.edit_message_text("⛔ Accès refusé.", reply_markup=kb.get_back_button())
            return
        keyboard = kb.get_admin_menu()
        await query.edit_message_text("⚙️ **Espace Admin**", parse_mode='Markdown', reply_markup=keyboard)

# --- ADMIN CONVERSATIONS ---
async def admin_list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not db.is_admin(query.from_user.id):
        return

    admins = db.list_admins()
    # Simple pagination example mapping to keyboard
    page_size = 5
    page = 1

    # We could implement a dynamic callback for admin pages, but for brevity:
    text = f"👥 **Liste des Admins ({len(admins)})**\n\n"
    for admin_id in admins[:page_size]:
        text += f"- `{admin_id}`\n"

    keyboard = kb.get_pagination_keyboard(1, (len(admins) - 1) // page_size + 1, "admin_list", back_callback="nav_admin")
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not db.is_admin(query.from_user.id):
        return

    total_users, total_deployments = db.get_global_stats()
    text = f"📊 **Statistiques Globales**\n\n👥 Utilisateurs totaux: {total_users}\n🚀 Déploiements totaux: {total_deployments}"
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=kb.get_back_button(callback_data="nav_admin"))

async def admin_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not db.is_admin(query.from_user.id):
        return ConversationHandler.END

    await query.edit_message_text("➕ Saisissez l'ID Telegram du nouvel administrateur.\n\nOu /cancel pour annuler.")
    return ADMIN_ADD_ID

async def admin_add_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        new_admin_id = int(update.message.text)
        db.add_admin(new_admin_id, update.effective_user.id)
        await update.message.reply_text(f"✅ Utilisateur {new_admin_id} ajouté comme administrateur.")
    except ValueError:
        await update.message.reply_text("❌ ID invalide. Veuillez entrer un nombre.")
    return ConversationHandler.END

async def admin_remove_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not db.is_admin(query.from_user.id):
        return ConversationHandler.END

    await query.edit_message_text("➖ Saisissez l'ID Telegram de l'administrateur à retirer.\n\nOu /cancel pour annuler.")
    return ADMIN_REMOVE_ID

async def admin_remove_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        admin_id_to_remove = int(update.message.text)
        db.remove_admin(admin_id_to_remove)
        await update.message.reply_text(f"✅ Administrateur {admin_id_to_remove} retiré.")
    except ValueError:
        await update.message.reply_text("❌ ID invalide. Veuillez entrer un nombre.")
    return ConversationHandler.END

async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not db.is_admin(query.from_user.id):
        return ConversationHandler.END

    await query.edit_message_text("📢 Saisissez le message à diffuser à tous les utilisateurs.\n\nOu /cancel pour annuler.")
    return ADMIN_BROADCAST_MSG

async def admin_broadcast_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.text
    users = db.list_users()
    count = 0

    status_msg = await update.message.reply_text(f"⏳ Diffusion en cours à {len(users)} utilisateurs...")

    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            count += 1
        except Exception:
            pass # User might have blocked the bot

    await status_msg.edit_text(f"✅ Diffusion terminée. Message envoyé à {count}/{len(users)} utilisateurs.")
    return ConversationHandler.END

# --- SSO DEPLOYMENT CONVERSATION ---
async def sso_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔗 Envoyez-moi le lien SSO Google Skills Boost.\n\nOu /cancel pour annuler."
    )
    return SSO_LINK

async def sso_receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    sso_url = update.message.text

    can_deploy, msg = db.check_and_use_quota_or_credit(user_id)
    if not can_deploy:
        await update.message.reply_text(f"❌ Impossible de déployer : {msg}")
        return ConversationHandler.END

    status_msg = await update.message.reply_text("⏳ Connexion à Google Cloud via SSO...")

    try:
        cloudrun_url = await worker.deploy_via_sso(sso_url)
        await status_msg.edit_text("✅ Terminé ! Génération du lien VLESS...")

        # Log it
        # Extract project id roughly for logging
        import urllib.parse
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(sso_url).query)
        pid = qs.get('project', ['unknown'])[0]
        db.log_deployment(user_id, 'SSO', pid, cloudrun_url, 1 if "credit" in msg else 0)

        # Send result
        vless_uri = vless.generate_vless_url(cloudrun_url)
        qr_bio = vless.generate_qr_code(vless_uri)

        await update.message.reply_photo(
            photo=qr_bio,
            caption=f"🚀 **Déploiement Réussi!**\n\n`{vless_uri}`",
            parse_mode='Markdown'
        )

    except Exception as e:
        db.refund_credit(user_id)
        await status_msg.edit_text(f"❌ Échec du déploiement: {str(e)}\n\nCrédit remboursé (si utilisé).")

    return ConversationHandler.END

# --- MANUAL DEPLOYMENT CONVERSATION ---
async def manual_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⌨️ Saisissez l'ID du projet GCP.\n\nOu /cancel pour annuler.")
    return MANUAL_PROJECT_ID

async def manual_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['project_id'] = update.message.text
    await update.message.reply_text("📧 Saisissez l'adresse email Google.")
    return MANUAL_EMAIL

async def manual_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['email'] = update.message.text
    await update.message.reply_text("🔑 Saisissez le mot de passe Google.")
    return MANUAL_PASSWORD

async def manual_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    context.user_data['password'] = update.message.text

    can_deploy, msg = db.check_and_use_quota_or_credit(user_id)
    if not can_deploy:
        await update.message.reply_text(f"❌ Impossible de déployer : {msg}")
        return ConversationHandler.END

    status_msg = await update.message.reply_text("⏳ Connexion à Google Cloud (Manuel)...")

    try:
        cloudrun_url = await worker.deploy_via_manual(
            context.user_data['project_id'],
            context.user_data['email'],
            context.user_data['password']
        )
        await status_msg.edit_text("✅ Terminé ! Génération du lien VLESS...")

        db.log_deployment(user_id, 'MANUAL', context.user_data['project_id'], cloudrun_url, 1 if "credit" in msg else 0)

        vless_uri = vless.generate_vless_url(cloudrun_url)
        qr_bio = vless.generate_qr_code(vless_uri)

        await update.message.reply_photo(
            photo=qr_bio,
            caption=f"🚀 **Déploiement Réussi!**\n\n`{vless_uri}`",
            parse_mode='Markdown'
        )

    except Exception as e:
        db.refund_credit(user_id)
        await status_msg.edit_text(f"❌ Échec du déploiement: {str(e)}\n\nCrédit remboursé (si utilisé).")

    # Clear sensitive info
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Action annulée.")
    return ConversationHandler.END

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing!")
        return

    # Initialize DB
    db.init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    sso_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(sso_start, pattern="^mode_sso$")],
        states={
            SSO_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, sso_receive_link)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    manual_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(manual_start, pattern="^mode_manual$")],
        states={
            MANUAL_PROJECT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_project)],
            MANUAL_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_email)],
            MANUAL_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    admin_add_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_start, pattern="^admin_add_admin$")],
        states={
            ADMIN_ADD_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_receive)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    admin_remove_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_remove_start, pattern="^admin_remove_admin$")],
        states={
            ADMIN_REMOVE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_remove_receive)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    admin_broadcast_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_broadcast_start, pattern="^admin_broadcast$")],
        states={
            ADMIN_BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_receive)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(sso_conv_handler)
    app.add_handler(manual_conv_handler)
    app.add_handler(admin_add_conv_handler)
    app.add_handler(admin_remove_conv_handler)
    app.add_handler(admin_broadcast_conv_handler)

    # Handlers for simple callbacks
    app.add_handler(CallbackQueryHandler(admin_list_admins, pattern="^admin_list_admins$"))
    app.add_handler(CallbackQueryHandler(admin_stats, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(menu_handler, pattern="^(menu_home|nav_.*)$"))

    logger.info("Bot is starting...")
    app.run_polling()

if __name__ == '__main__':
    main()
