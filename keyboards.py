from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_pagination_keyboard(current_page, total_pages, prefix, back_callback="menu_home"):
    buttons = []
    nav_row = []
    if current_page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Précédent", callback_data=f"{prefix}_page_{current_page - 1}"))

    nav_row.append(InlineKeyboardButton(f"📄 {current_page}/{total_pages}", callback_data="noop"))

    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton("Suivant ➡️", callback_data=f"{prefix}_page_{current_page + 1}"))

    buttons.append(nav_row)
    buttons.append([
        InlineKeyboardButton("🔙 Retour", callback_data=back_callback),
        InlineKeyboardButton("🏠 Accueil", callback_data="menu_home")
    ])

    return InlineKeyboardMarkup(buttons)

def get_main_menu(is_admin=False):
    keyboard = [
        [InlineKeyboardButton("🚀 Déployer mon tunnel", callback_data="nav_deploy")],
        [InlineKeyboardButton("👤 Mon Profil & Quotas", callback_data="nav_profile"),
         InlineKeyboardButton("🎁 Parrainage & Bonus", callback_data="nav_referral")],
        [InlineKeyboardButton("🏪 Boutique de Crédits", callback_data="nav_shop"),
         InlineKeyboardButton("📖 Guide DarkTunnel", callback_data="nav_help")]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("⚙️ Espace Admin", callback_data="nav_admin")])
    return InlineKeyboardMarkup(keyboard)

def get_deploy_menu():
    keyboard = [
        [InlineKeyboardButton("🔗 Par Lien SSO", callback_data="mode_sso")],
        [InlineKeyboardButton("⌨️ Saisie Manuelle", callback_data="mode_manual")],
        [InlineKeyboardButton("🔙 Retour", callback_data="menu_home")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_menu():
    keyboard = [
        [InlineKeyboardButton("👥 Liste des Admins", callback_data="admin_list_admins"),
         InlineKeyboardButton("➕ Ajouter un Admin", callback_data="admin_add_admin")],
        [InlineKeyboardButton("➖ Retirer un Admin", callback_data="admin_remove_admin"),
         InlineKeyboardButton("💰 Gérer les Crédits", callback_data="admin_manage_credits")],
        [InlineKeyboardButton("📊 Statistiques Globales", callback_data="admin_stats"),
         InlineKeyboardButton("📢 Diffuser un Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔙 Retour", callback_data="menu_home")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_button(callback_data="menu_home"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data=callback_data)]])
