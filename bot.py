import json
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import asyncio
import uuid # Para generar IDs únicos para los pagos
import nest_asyncio # Importamos la librería para permitir bucles anidados

# --- CONFIGURACIÓN DEL BOT ---
# ¡IMPORTANTE! Reemplaza estos valores con los tuyos.
# Para el BOT_TOKEN, obténlo de @BotFather en Telegram.
BOT_TOKEN = "7698979220:AAE7NzdGdBdPfrICweK2SFA0zJW25AbpUio"
# Para la API_KEY del SMM Panel, obténla de tu proveedor (e.g., fastwaysmm.com)
API_KEY = "2a15c500ac8acc019e7f99268a8a3caf"
API_URL = "https://fastwaysmm.com/api/v2"

# ID del administrador. ¡CÁMBIALO POR TU ID DE USUARIO DE TELEGRAM!
# Puedes obtener tu ID enviando un mensaje a @userinfobot en Telegram.
ADMIN_ID = 8148468413


# Información de los servicios SMM con nueva estructura anidada.
# 'id' es el ID del servicio en tu SMM Panel.
# 'precio_por_unidad' es el coste por cada unidad del servicio (ej. 0.01€ por like).
# 'min_cantidad' y 'max_cantidad' para establecer límites.
SERVICIOS = {
    "INSTAGRAM": {
        "LIKES": {"id": 4705, "precio_por_unidad": 0.010, "min_cantidad": 100, "max_cantidad": 10000},
        "SEGUIDORES": {"id": 755, "precio_por_unidad": 0.015, "min_cantidad": 100, "max_cantidad": 3000},
        "VISTAS": {"id": 2263, "precio_por_unidad": 0.007, "min_cantidad": 200, "max_cantidad": 100000},
        "VISTA_HISTORIAS": {"id": 306, "precio_por_unidad": 0.004, "min_cantidad": 1000, "max_cantidad": 500000},
        "COMENTARIOS": {"id": 662, "precio_por_unidad": 3.80, "min_cantidad": 5, "max_cantidad": 50},
        "GUARDADOS": {"id": 853, "precio_por_unidad": 0.005, "min_cantidad": 100, "max_cantidad": 500000},
        "COMPARTIDOS": {"id": 4150, "precio_por_unidad": 0.003, "min_cantidad": 50, "max_cantidad": 5000}
    },
    "TIKTOK": {
        "LIKES": {"id": 248, "precio_por_unidad": 0.010, "min_cantidad": 100, "max_cantidad": 5000000},
        "SEGUIDORES": {"id": 1857, "precio_por_unidad": 0.015, "min_cantidad": 100, "max_cantidad": 1000000},
        "REPRODUCCIONES": {"id": 1112, "precio_por_unidad": 0.005, "min_cantidad": 500, "max_cantidad": 5000000},
        "VISTAS_LIVE": {"id": 3082, "precio_por_unidad": 0.005, "min_cantidad": 100, "max_cantidad": 10000},
        "COMENTARIOS": {"id": 2231, "precio_por_unidad": 0.009, "min_cantidad": 50, "max_cantidad": 500000},
        "GUARDADOS": {"id": 2275, "precio_por_unidad": 0.010, "min_cantidad": 50, "max_cantidad": 5000},
        "COMPARTIDOS": {"id": 2280, "precio_por_unidad": 0.010, "min_cantidad": 50, "max_cantidad": 5000}
    },
    "FACEBOOK": {
        "PERFIL": {
            "POST_LIKE": {"id": 246, "precio_por_unidad": 0.015, "min_cantidad": 100, "max_cantidad": 1000000},
            "POST_REACCIONES": {"id": 810, "precio_por_unidad": 0.012, "min_cantidad": 100, "max_cantidad": 1000000},
            "POST_COMPARTIR": {"id": 3003, "precio_por_unidad": 0.014, "min_cantidad": 50, "max_cantidad": 500000},
            "SEGUIDORES": {"id": 79, "precio_por_unidad": 0.015, "min_cantidad": 50, "max_cantidad": 500000},
            "VISTAS_VIDEOS": {"id": 2239, "precio_por_unidad": 0.007, "min_cantidad": 200, "max_cantidad": 2000000},
            "VISTAS_LIVE_STREAM": {"id": 4597, "precio_por_unidad": 0.005, "min_cantidad": 100, "max_cantidad": 100000}
        },
        "PAGINAS": {
            "LIKE": {"id": 1222, "precio_por_unidad": 0.015, "min_cantidad": 50, "max_cantidad": 5000},
            "SEGUIDORES": {"id": 222, "precio_por_unidad": 0.0015, "min_cantidad": 50, "max_cantidad": 5000}
        }
    },
    "YOUTUBE": {
        "VISTAS": {"id": 208, "precio_por_unidad": 0.010, "min_cantidad": 500, "max_cantidad": 500000},
        "SUSCRIPTORES": {"id": 1622, "precio_por_unidad": 0.018, "min_cantidad": 100, "max_cantidad": 100000},
        "LIKES": {"id": 228, "precio_por_unidad": 0.015, "min_cantidad": 100, "max_cantidad": 10000000},

        "COMPARTIDOS": {"id": 983, "precio_por_unidad": 0.012, "min_cantidad": 50, "max_cantidad": 5000}
    },
    "TELEGRAM": {
        "MIEMBROS": {"id": 364, "precio_por_unidad": 0.015, "min_cantidad": 100, "max_cantidad": 5000000},
        "REACCIONES": {"id": 4930, "precio_por_unidad": 0.013, "min_cantidad": 100, "max_cantidad": 100000},

        "VISTAS": {"id": 4610, "precio_por_unidad": 0.008, "min_cantidad": 100, "max_cantidad": 500000}
    },
    "TWITTER": {
        "SEGUIDORES": {"id": 2382, "precio_por_unidad": 0.02, "min_cantidad": 10, "max_cantidad": 50000},
        "LIKES": {"id": 2334, "precio_por_unidad": 0.010, "min_cantidad": 100, "max_cantidad": 10000},
        "RETWEETS": {"id": 719, "precio_por_unidad": 0.015, "min_cantidad": 50, "max_cantidad": 5000}
    },
    "THREADS": {
        "SEGUIDORES": {"id": 4336, "precio_por_unidad": 0.016, "min_cantidad": 100, "max_cantidad": 500000},
        "LIKES": {"id": 4335, "precio_por_unidad": 0.015, "min_cantidad": 100, "max_cantidad": 10000},
        "COMPARTIDAS": {"id": 4274, "precio_por_unidad": 0.015, "min_cantidad": 50, "max_cantidad": 5000}
    },
    "TWITCH": {
        "SEGUIDORES": {"id": 2710, "precio_por_unidad": 0.010, "min_cantidad": 50, "max_cantidad": 5000}

    }
}


# --- CONFIGURACIÓN DE PAGOS ---
# Reemplaza con tus datos reales para cada método de pago.
# Para Bizum: Tu número de teléfono asociado a Bizum.
BIZUM_INFO = "673302256" 
# Para PayPal: Tu enlace de PayPal.me.
# Si quieres una integración más avanzada con PayPal (webhooks), necesitarías un servidor web.
PAYPAL_INFO = "https://paypal.me/bartlegado" 
# Para Binance/Crypto: Tu dirección de billetera y la red (ej. USDT TRC20).
BINANCE_INFO = "bc1qr5csg4ahxgrh08g57m6zu6sv839k9u6plpru7t(BTC)" 

# --- RUTAS DE ARCHIVOS DE DATOS ---
SALDO_PATH = "saldos.json"
PENDING_PAYMENTS_PATH = "pagos_pendientes.json"

# --- CARGA INICIAL DE DATOS ---
# Asegura que los archivos JSON existan.
for path in [SALDO_PATH, PENDING_PAYMENTS_PATH]:
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump({}, f)

# Carga los saldos de usuarios y pagos pendientes.
with open(SALDO_PATH, "r") as f:
    saldo_usuarios = json.load(f)

with open(PENDING_PAYMENTS_PATH, "r") as f:
    pagos_pendientes = json.load(f)

# --- FUNCIONES DE UTILIDAD ---
def guardar_saldo():
    """Guarda el diccionario de saldos en el archivo JSON."""
    with open(SALDO_PATH, "w") as f:
        json.dump(saldo_usuarios, f, indent=4)

def guardar_pagos_pendientes():
    """Guarda el diccionario de pagos pendientes en el archivo JSON."""
    with open(PENDING_PAYMENTS_PATH, "w") as f:
        json.dump(pagos_pendientes, f, indent=4)

def get_service_info_from_path(path_list):
    """
    Obtiene la información de un servicio navegando por la estructura anidada de SERVICIOS.
    path_list: Una lista de strings que representa la ruta al servicio (ej. ["INSTAGRAM", "LIKES"]).
               Para Facebook, podría ser ["FACEBOOK", "PERFIL", "POST_LIKE"].
    """
    current_level = SERVICIOS
    for key in path_list:
        if key in current_level:
            current_level = current_level[key]
        else:
            return None # Ruta no encontrada
    return current_level

# --- MANEJO DE ESTADOS DE CONVERSACIÓN ---
# Definimos estados para el flujo de pedido y recarga.
# Usaremos context.user_data para almacenar el estado del usuario.
STATE_NONE = 0
STATE_CHOOSING_PLATFORM = 1 # Nuevo estado: Elegir plataforma (Instagram, TikTok, etc.)
STATE_CHOOSING_FACEBOOK_CATEGORY = 2 # Nuevo estado: Elegir Perfil o Páginas para Facebook
STATE_CHOOSING_SERVICE_TYPE = 3 # Nuevo estado: Elegir el tipo de servicio (Likes, Seguidores, etc.)
STATE_ENTERING_LINK = 4
STATE_ENTERING_QUANTITY = 5
STATE_CONFIRMING_ORDER = 6
STATE_ENTERING_RECHARGE_AMOUNT = 7
STATE_CHOOSING_PAYMENT_METHOD = 8
STATE_WAITING_PAYMENT_PROOF = 9

# --- COMANDOS DEL BOT ---

# --- COMANDOS DEL BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /start. Muestra las plataformas disponibles."""
    context.user_data.clear() # Limpiar datos de usuario al inicio de un nuevo flujo
    context.user_data["state"] = STATE_CHOOSING_PLATFORM
    # Crea botones para cada plataforma principal (claves de SERVICIOS)
    keyboard = [[InlineKeyboardButton(platform, callback_data=f"platform_{platform}")] for platform in SERVICIOS.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 ¡Hola! Soy tu IA de Intereacciones Sociales.\n\n"
                                    "Elige una plataforma para empezar o usa /saldo para ver tu balance.\n"
                                    "Si necesitas recargar, usa /recargar_saldo.", reply_markup=reply_markup)

async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el saldo actual del usuario."""
    user_id = str(update.message.from_user.id)
    saldo_actual = saldo_usuarios.get(user_id, 0.0)
    await update.message.reply_text(f"💰 Tu saldo actual es: {saldo_actual:.2f}€")

async def recargar_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo de recarga de saldo para el usuario."""
    context.user_data["state"] = STATE_ENTERING_RECHARGE_AMOUNT
    await update.message.reply_text("💳 ¿Cuánto saldo deseas recargar? Por favor, ingresa el monto en euros (ej. 10.50).")


# --- MANEJADORES DE CALLBACKS (BOTONES INLINE) ---

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja las pulsaciones de botones inline."""
    query = update.callback_query
    await query.answer() # Siempre responde a la callback query

    user_id = str(query.from_user.id)
    current_state = context.user_data.get("state", STATE_NONE)

    # --- Manejo de botones "Atrás" ---
    if query.data == "back_to_platforms":
        context.user_data.clear() # Limpiar todo para volver al inicio del flujo de selección de servicio
        context.user_data["state"] = STATE_CHOOSING_PLATFORM
        keyboard = [[InlineKeyboardButton(platform, callback_data=f"platform_{platform}")] for platform in SERVICIOS.keys()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Elige una plataforma para empezar:", reply_markup=reply_markup)
        return
    
    elif query.data == "back_to_facebook_categories":
        context.user_data["state"] = STATE_CHOOSING_FACEBOOK_CATEGORY
        context.user_data.pop("facebook_categoria_elegida", None) # Eliminar la categoría de Facebook elegida
        platform_name = context.user_data.get("platform_elegida") # Debería ser "FACEBOOK"
        if platform_name == "FACEBOOK":
            keyboard = [
                [InlineKeyboardButton("PERFIL", callback_data="facebook_category_PERFIL")],
                [InlineKeyboardButton("PAGINAS", callback_data="facebook_category_PAGINAS")],
                [InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_platforms")] # Botón para volver a plataformas
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"Has elegido: *{platform_name}*.\n\n"
                                          "¿Para qué categoría de Facebook deseas el servicio?",
                                          parse_mode='Markdown', reply_markup=reply_markup)
        else: # Esto no debería pasar si el flujo es correcto
            await query.edit_message_text("❌ Error al volver. Por favor, reinicia con /start.")
            context.user_data.clear()
        return

    elif query.data == "back_to_service_type_selection":
        platform_name = context.user_data.get("platform_elegida")
        facebook_category = context.user_data.get("facebook_categoria_elegida")
        
        context.user_data["state"] = STATE_CHOOSING_SERVICE_TYPE
        context.user_data.pop("servicio_elegido_path", None)
        context.user_data.pop("servicio_nombre_display", None)

        if platform_name == "FACEBOOK" and facebook_category:
            service_types = SERVICIOS["FACEBOOK"][facebook_category].keys()
            keyboard = [[InlineKeyboardButton(st, callback_data=f"service_type_{st}")] for st in service_types]
            keyboard.append([InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_facebook_categories")]) # Botón para volver a categorías de Facebook
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"Has elegido *Facebook - {facebook_category}*.\n\n"
                                          "Ahora elige el tipo de servicio:",
                                          parse_mode='Markdown', reply_markup=reply_markup)
        elif platform_name: # No es Facebook, o es Facebook pero sin categoría (error de flujo)
            service_types = SERVICIOS[platform_name].keys()
            keyboard = [[InlineKeyboardButton(st, callback_data=f"service_type_{st}")] for st in service_types]
            keyboard.append([InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_platforms")]) # Botón para volver a plataformas
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"Has elegido: *{platform_name}*.\n\n"
                                          "Ahora elige el tipo de servicio:",
                                          parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await query.edit_message_text("❌ Error al volver. Por favor, reinicia con /start.")
            context.user_data.clear()
        return

    elif query.data == "back_to_link_entry":
        context.user_data["state"] = STATE_ENTERING_LINK
        context.user_data.pop("cantidad_elegida", None) # Eliminar la cantidad elegida
        context.user_data.pop("costo_total_pedido", None) # Eliminar el costo total
        
        servicio_nombre_display = context.user_data.get("servicio_nombre_display")
        link_elegido = context.user_data.get("link_elegido")

        if servicio_nombre_display and link_elegido:
            # Volver a pedir el enlace, con el enlace anterior precargado en el mensaje
            keyboard = [[InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_service_type_selection")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"Has elegido: *{servicio_nombre_display}*.\n\n"
                                          f"🔗 Envía el enlace (URL) al que deseas aplicar el servicio. (Actual: `{link_elegido}`)",
                                          parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await query.edit_message_text("❌ Error al volver. Por favor, reinicia con /start.")
            context.user_data.clear()
        return

    # --- Manejo de la selección de plataforma/servicio ---
    if current_state == STATE_CHOOSING_PLATFORM and query.data.startswith("platform_"):
        platform_name = query.data.replace("platform_", "")
        if platform_name in SERVICIOS:
            context.user_data["platform_elegida"] = platform_name
            if platform_name == "FACEBOOK":
                context.user_data["state"] = STATE_CHOOSING_FACEBOOK_CATEGORY
                # Para Facebook, mostramos las subcategorías (PERFIL, PAGINAS)
                keyboard = [
                    [InlineKeyboardButton("PERFIL", callback_data="facebook_category_PERFIL")],
                    [InlineKeyboardButton("PAGINAS", callback_data="facebook_category_PAGINAS")],
                    [InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_platforms")] # Botón para volver a plataformas
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(f"Has elegido: *{platform_name}*.\n\n"
                                              "¿Para qué categoría de Facebook deseas el servicio?",
                                              parse_mode='Markdown', reply_markup=reply_markup)
            else:
                context.user_data["state"] = STATE_CHOOSING_SERVICE_TYPE
                # Para otras plataformas, mostramos directamente los tipos de servicio
                service_types = SERVICIOS[platform_name].keys()
                keyboard = [[InlineKeyboardButton(st, callback_data=f"service_type_{st}")] for st in service_types]
                keyboard.append([InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_platforms")]) # Botón para volver a plataformas
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(f"Has elegido: *{platform_name}*.\n\n"
                                              "Ahora elige el tipo de servicio:",
                                              parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await query.edit_message_text("❌ Plataforma no válida. Por favor, elige de la lista.")
            context.user_data.clear() # Reiniciar estado
    
    elif current_state == STATE_CHOOSING_FACEBOOK_CATEGORY and query.data.startswith("facebook_category_"):
        facebook_category = query.data.replace("facebook_category_", "")
        platform_name = context.user_data.get("platform_elegida")
        if platform_name == "FACEBOOK" and facebook_category in SERVICIOS["FACEBOOK"]:
            context.user_data["facebook_categoria_elegida"] = facebook_category
            context.user_data["state"] = STATE_CHOOSING_SERVICE_TYPE
            # Mostramos los tipos de servicio dentro de la categoría de Facebook
            service_types = SERVICIOS["FACEBOOK"][facebook_category].keys()
            keyboard = [[InlineKeyboardButton(st, callback_data=f"service_type_{st}")] for st in service_types]
            keyboard.append([InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_facebook_categories")]) # Botón para volver a categorías de Facebook
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"Has elegido *Facebook - {facebook_category}*.\n\n"
                                          "Ahora elige el tipo de servicio:",
                                          parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await query.edit_message_text("❌ Categoría de Facebook no válida. Por favor, elige de la lista.")
            context.user_data.clear()

    elif current_state == STATE_CHOOSING_SERVICE_TYPE and query.data.startswith("service_type_"):
        service_type_name = query.data.replace("service_type_", "")
        platform_name = context.user_data.get("platform_elegida")
        facebook_category = context.user_data.get("facebook_categoria_elegida")

        # Construir la ruta completa al servicio
        service_path = []
        if platform_name:
            service_path.append(platform_name)
            if facebook_category:
                service_path.append(facebook_category)
            service_path.append(service_type_name)
        
        service_info = get_service_info_from_path(service_path)

        if service_info:
            # Almacenar la ruta completa y el nombre a mostrar para fácil recuperación
            context.user_data["servicio_elegido_path"] = service_path
            context.user_data["servicio_nombre_display"] = " ".join(service_path) # Ej: "INSTAGRAM LIKES" o "FACEBOOK PERFIL POST_LIKE"

            context.user_data["state"] = STATE_ENTERING_LINK
            # Cuando pedimos el enlace, añadimos el botón de atrás
            keyboard = [[InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_service_type_selection")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"Has elegido: *{context.user_data['servicio_nombre_display']}*.\n\n"
                                          "🔗 Ahora envía el enlace (URL) al que deseas aplicar el servicio.",
                                          parse_mode='Markdown', reply_markup=reply_markup) # Añadir reply_markup aquí
        else:
            await query.edit_message_text("❌ Tipo de servicio no válido. Por favor, elige de la lista.")
            context.user_data.clear()
    
    elif current_state == STATE_CHOOSING_PAYMENT_METHOD and query.data.startswith("pay_"):
        method = query.data.replace("pay_", "")
        context.user_data["metodo_pago_elegido"] = method
        monto_recarga = context.user_data.get("monto_recarga")

        if not monto_recarga:
            await query.edit_message_text("❌ Error: Monto de recarga no especificado. Por favor, reinicia con /recargar_saldo.")
            context.user_data["state"] = STATE_NONE
            return

        # Generar un ID de pago único para esta transacción
        payment_id = str(uuid.uuid4())
        context.user_data["current_payment_id"] = payment_id

        # Almacenar el pago como pendiente
        pagos_pendientes[payment_id] = {
            "user_id": user_id,
            "username": query.from_user.username or query.from_user.first_name,
            "amount": monto_recarga,
            "method": method,
            "status": "pending_confirmation",
            "timestamp": update.callback_query.message.date.isoformat()
        }
        guardar_pagos_pendientes()

        instructions = ""
        if method == "bizum":
            instructions = (f"Por favor, realiza un Bizum de *{monto_recarga:.2f}€* a este número: `{BIZUM_INFO}`.\n\n"
                            "Una vez hecho, envía una *captura de pantalla* del comprobante de pago o el *ID de la transacción* en el siguiente mensaje. "
                            "Tu pago será revisado por el administrador.")
        elif method == "paypal":
            instructions = (f"Por favor, envía *{monto_recarga:.2f}€* a través de PayPal a este enlace: `{PAYPAL_INFO}`.\n\n"
                            "Una vez hecho, envía una *captura de pantalla* del comprobante de pago o el *ID de la transacción* en el siguiente mensaje. "
                            "Tu pago será revisado por el administrador.")
        elif method == "binance":
            instructions = (f"Por favor, envía *{monto_recarga:.2f} USDT* (o el equivalente en la criptomoneda acordada) "
                            f"a esta dirección y red: `{BINANCE_INFO}`.\n\n"
                            "Una vez hecho, envía una *captura de pantalla* del comprobante de pago o el *ID de la transacción* (TxID) en el siguiente mensaje. "
                            "Tu pago será revisado por el administrador.")
        
        await query.edit_message_text(f"Has elegido *{method.capitalize()}*.\n\n" + instructions, parse_mode='Markdown')
        context.user_data["state"] = STATE_WAITING_PAYMENT_PROOF

    elif query.data == "confirmar_pedido":
        await confirmar_pedido(update, context)
    elif query.data == "cancelar_pedido":
        await query.edit_message_text("❌ Pedido cancelado. Puedes empezar de nuevo con /start.")
        context.user_data.clear() # Limpiar todos los datos de usuario

# --- MANEJADOR DE MENSAJES DE TEXTO ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja todos los mensajes de texto del usuario."""
    user_id = str(update.message.from_user.id)
    text = update.message.text
    current_state = context.user_data.get("state", STATE_NONE)

    if current_state == STATE_ENTERING_LINK:
        context.user_data["link_elegido"] = text
        context.user_data["state"] = STATE_ENTERING_QUANTITY
        
        servicio_nombre_display = context.user_data.get("servicio_nombre_display")
        servicio_path = context.user_data.get("servicio_elegido_path")
        service_info = get_service_info_from_path(servicio_path)
        
        # Asegurarse de que service_info y servicio_nombre_display son válidos antes de usarlos
        if service_info and servicio_nombre_display:
            min_q = service_info['min_cantidad']
            max_q = service_info['max_cantidad']
            
            # Definir reply_markup para este estado (solo botón 'Atrás')
            keyboard = [[InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_service_type_selection")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(f"¿Cuánta cantidad de *{servicio_nombre_display}* deseas? (Mínimo: {min_q}, Máximo: {max_q})", parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await update.message.reply_text("❌ Error: Servicio no encontrado. Por favor, reinicia con /start.")
            context.user_data["state"] = STATE_NONE

    elif current_state == STATE_ENTERING_QUANTITY:
        try:
            quantity = int(text)
            
            servicio_path = context.user_data.get("servicio_elegido_path")
            servicio_nombre_display = context.user_data.get("servicio_nombre_display")

            if not servicio_path or not servicio_nombre_display:
                await update.message.reply_text("❌ Error: Servicio no encontrado. Por favor, reinicia con /start.")
                context.user_data["state"] = STATE_NONE
                return

            service_info = get_service_info_from_path(servicio_path)

            if not service_info:
                await update.message.reply_text("❌ Error: Servicio no encontrado. Por favor, reinicia con /start.")
                context.user_data["state"] = STATE_NONE
                return

            min_q = service_info['min_cantidad']
            max_q = service_info['max_cantidad']

            if not (min_q <= quantity <= max_q):
                # Si la cantidad está fuera de rango, se mantiene en el mismo estado y se le permite volver
                keyboard = [[InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_link_entry")]] # Volver a la entrada de enlace
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(f"❗ Cantidad fuera de rango. Por favor, ingresa una cantidad entre {min_q} y {max_q}.", reply_markup=reply_markup)
                return

            context.user_data["cantidad_elegida"] = quantity
            
            precio_por_unidad = service_info["precio_por_unidad"]
            costo_total = precio_por_unidad * quantity
            context.user_data["costo_total_pedido"] = costo_total

            keyboard = [
                [InlineKeyboardButton("✅ Confirmar Pedido", callback_data="confirmar_pedido")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_pedido")],
                [InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_link_entry")] # Botón para volver a introducir el enlace
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"Resumen del pedido:\n"
                f"Servicio: *{servicio_nombre_display}*\n"
                f"Enlace: `{context.user_data['link_elegido']}`\n"
                f"Cantidad: *{quantity}*\n"
                f"Costo Total: *{costo_total:.2f}€*\n\n"
                f"¿Confirmas el pedido?",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            context.user_data["state"] = STATE_CONFIRMING_ORDER

        except ValueError:
            # Si no es un número válido, se mantiene en el mismo estado y se le permite volver
            keyboard = [[InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_link_entry")]] # Volver a la entrada de enlace
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("❗ Por favor, ingresa una cantidad numérica válida.", reply_markup=reply_markup)


    elif current_state == STATE_ENTERING_RECHARGE_AMOUNT:
        try:
            monto = float(text)
            if monto <= 0:
                await update.message.reply_text("❗ El monto debe ser un número positivo.")
                return
            context.user_data["monto_recarga"] = monto
            context.user_data["state"] = STATE_CHOOSING_PAYMENT_METHOD

            keyboard = [
                [InlineKeyboardButton("Bizum", callback_data="pay_bizum")],
                [InlineKeyboardButton("PayPal", callback_data="pay_paypal")],
                [InlineKeyboardButton("Binance (Crypto)", callback_data="pay_binance")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(f"Has elegido recargar *{monto:.2f}€*.\n\n"
                                            "¿Cómo deseas realizar el pago?", parse_mode='Markdown', reply_markup=reply_markup)
        except ValueError:
            await update.message.reply_text("❗ Por favor, ingresa un monto numérico válido (ej. 10.50).")

    elif current_state == STATE_WAITING_PAYMENT_PROOF:
        payment_id = context.user_data.get("current_payment_id")
        if payment_id and payment_id in pagos_pendientes:
            pagos_pendientes[payment_id]["proof"] = text # Guardar el texto como prueba
            pagos_pendientes[payment_id]["status"] = "awaiting_admin_review"
            guardar_pagos_pendientes()
            await update.message.reply_text(
                "✅ ¡Gracias! Hemos recibido tu confirmación de pago. "
                "El administrador revisará tu solicitud en breve y actualizará tu saldo."
            )
            # Notificar al administrador
            admin_message = (
                f"🔔 *NUEVA SOLICITUD DE RECARGA PENDIENTE*\n"
                f"Usuario: [{update.message.from_user.first_name}](tg://user?id={user_id}) (`{user_id}`)\n"
                f"Monto: *{pagos_pendientes[payment_id]['amount']:.2f}€*\n"
                f"Método: *{pagos_pendientes[payment_id]['method'].capitalize()}*\n"
                f"Prueba enviada: `{text}`\n\n"
                f"Para aprobar: `/aprobar_pago {user_id} {pagos_pendientes[payment_id]['amount']:.2f}`\n"
                f"Para rechazar: `/rechazar_pago {user_id}`"
            )
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message, parse_mode='Markdown')

        else:
            await update.message.reply_text("❌ No hay una solicitud de recarga pendiente para confirmar. Por favor, inicia con /recargar_saldo.")
        context.user_data.clear() # Limpiar estado después de enviar prueba

    else:
        await update.message.reply_text("🤔 No entiendo. Por favor, usa /start para comenzar o /saldo para ver tu balance.")
        context.user_data.clear()


async def confirmar_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirma el pedido y lo envía al SMM panel."""
    user_id = str(update.callback_query.from_user.id)
    
    servicio_path = context.user_data.get("servicio_elegido_path")
    servicio_nombre_display = context.user_data.get("servicio_nombre_display")
    link = context.user_data.get("link_elegido")
    quantity = context.user_data.get("cantidad_elegida")
    costo_total = context.user_data.get("costo_total_pedido")

    if not all([servicio_path, servicio_nombre_display, link, quantity, costo_total is not None]):
        await update.callback_query.edit_message_text("❌ Error: Faltan datos del pedido. Por favor, reinicia con /start.")
        context.user_data.clear()
        return

    saldo_actual = saldo_usuarios.get(user_id, 0.0)

    if saldo_actual < costo_total:
        await update.callback_query.edit_message_text(
            f"💳 Tu saldo actual ({saldo_actual:.2f}€) es insuficiente para este pedido ({costo_total:.2f}€).\n\n"
            "Por favor, recarga tu saldo con /recargar_saldo."
        )
        context.user_data.clear()
        return

    # Restar saldo
    saldo_usuarios[user_id] = saldo_actual - costo_total
    guardar_saldo()

    service_info = get_service_info_from_path(servicio_path)
    if not service_info:
        await update.callback_query.edit_message_text("❌ Error: Servicio no encontrado. Por favor, reinicia con /start.")
        context.user_data.clear()
        return
    
    service_id = service_info["id"]

    payload = {
        "key": API_KEY,
        "action": "add",
        "service": service_id,
        "link": link,
        "quantity": quantity
    }

    await update.callback_query.edit_message_text("⏳ Procesando tu pedido... Esto puede tardar unos segundos.")

    try:
        response = requests.post(API_URL, data=payload)
        res_json = response.json()

        if "order" in res_json:
            await update.callback_query.edit_message_text(
                f"✅ ¡Pedido realizado con éxito!\n"
                f"ID de Pedido: `{res_json['order']}`\n"
                f"Servicio: *{servicio_nombre_display}*\n"
                f"Cantidad: *{quantity}*\n"
                f"Costo: *{costo_total:.2f}€*\n"
                f"Tu nuevo saldo es: *{saldo_usuarios[user_id]:.2f}€*",
                parse_mode='Markdown'
            )
        else:
            error_message = res_json.get("error", "Error desconocido al procesar el pedido.")
            await update.callback_query.edit_message_text(
                f"⚠️ Error al realizar el pedido:\n`{error_message}`\n\n"
                f"Tu saldo ha sido *reembolsado* debido a este error. Saldo actual: *{saldo_usuarios[user_id]:.2f}€*",
                parse_mode='Markdown'
            )
            # Reembolsar saldo si el pedido falla en el panel
            saldo_usuarios[user_id] += costo_total
            guardar_saldo()

    except requests.exceptions.RequestException as e:
        await update.callback_query.edit_message_text(
            f"❌ Error de conexión con el panel SMM. Por favor, inténtalo de nuevo más tarde.\n"
            f"Tu saldo ha sido *reembolsado* debido a este error. Saldo actual: *{saldo_usuarios[user_id]:.2f}€*",
            parse_mode='Markdown'
        )
        # Reembolsar saldo si hay error de conexión
        saldo_usuarios[user_id] += costo_total
        guardar_saldo()
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ Error inesperado: {e}. Por favor, contacta al soporte.")
        # Reembolsar saldo si hay cualquier otro error inesperado
        saldo_usuarios[user_id] += costo_total
        guardar_saldo()

    context.user_data.clear() # Limpiar el estado del usuario


# --- COMANDOS DE ADMINISTRADOR ---

async def ver_pagos_pendientes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """(ADMIN) Muestra todos los pagos pendientes de revisión."""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este comando.")
        return

    if not pagos_pendientes:
        await update.message.reply_text("✅ No hay pagos pendientes de revisión.")
        return

    message_text = "📋 *Pagos Pendientes de Revisión:*\n\n"
    for payment_id, data in pagos_pendientes.items():
        if data.get("status") == "awaiting_admin_review":
            user_id = data.get("user_id", "N/A")
            username = data.get("username", "N/A")
            amount = data.get("amount", 0.0)
            method = data.get("method", "N/A")
            proof = data.get("proof", "No enviada")
            timestamp = data.get("timestamp", "N/A")

            message_text += (
                f"--- ID de Pago: `{payment_id}` ---\n"
                f"Usuario: [{username}](tg://user?id={user_id}) (`{user_id}`)\n"
                f"Monto: *{amount:.2f}€*\n"
                f"Método: *{method.capitalize()}*\n"
                f"Prueba: `{proof}`\n"
                f"Fecha: `{timestamp}`\n"
                f"Comando para aprobar: `/aprobar_pago {user_id} {amount:.2f}`\n"
                f"Para rechazar: `/rechazar_pago {user_id}`\n\n"
            )
    
    if message_text == "📋 *Pagos Pendientes de Revisión:*\n\n": # Si no se encontró ninguno con el status
        await update.message.reply_text("✅ No hay pagos pendientes de revisión.")
    else:
        await update.message.reply_text(message_text, parse_mode='Markdown')


async def aprobar_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """(ADMIN) Aprueba un pago pendiente y añade el saldo al usuario."""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este comando.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Uso: `/aprobar_pago <user_id> <monto>`", parse_mode='Markdown')
        return

    target_user_id = context.args[0]
    try:
        monto = float(context.args[1])
        if monto <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❗ El monto debe ser un número positivo.")
        return

    # Buscar el pago pendiente para este usuario y monto
    found_payment_id = None
    for payment_id, data in pagos_pendientes.items():
        if data.get("user_id") == target_user_id and \
           abs(data.get("amount", 0) - monto) < 0.01 and \
           data.get("status") == "awaiting_admin_review":
            found_payment_id = payment_id
            break
    
    if not found_payment_id:
        await update.message.reply_text(f"❌ No se encontró un pago pendiente para el usuario `{target_user_id}` con el monto `{monto:.2f}€`.", parse_mode='Markdown')
        return

    # Actualizar saldo del usuario
    saldo_usuarios[target_user_id] = saldo_usuarios.get(target_user_id, 0.0) + monto
    guardar_saldo()

    # Marcar el pago como aprobado
    pagos_pendientes[found_payment_id]["status"] = "approved"
    guardar_pagos_pendientes()

    await update.message.reply_text(f"✅ Se añadieron *{monto:.2f}€* al usuario `{target_user_id}`. Pago `{found_payment_id}` aprobado.", parse_mode='Markdown')
    
    # Notificar al usuario
    try:
        await context.bot.send_message(
            chat_id=int(target_user_id),
            text=f"🎉 ¡Tu recarga de *{monto:.2f}€* ha sido aprobada!\n"
                 f"Tu nuevo saldo es: *{saldo_usuarios[target_user_id]:.2f}€*",
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Error al notificar al usuario {target_user_id}: {e}")
        await update.message.reply_text(f"⚠️ No se pudo notificar al usuario {target_user_id} sobre la aprobación.")


async def rechazar_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """(ADMIN) Rechaza un pago pendiente."""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este comando.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Uso: `/rechazar_pago <user_id>`", parse_mode='Markdown')
        return

    target_user_id = context.args[0]
    
    # Buscar el pago pendiente para este usuario
    found_payment_id = None
    for payment_id, data in pagos_pendientes.items():
        if data.get("user_id") == target_user_id and \
           data.get("status") == "awaiting_admin_review":
            found_payment_id = payment_id
            break
    
    if not found_payment_id:
        await update.message.reply_text(f"❌ No se encontró un pago pendiente para el usuario `{target_user_id}`.", parse_mode='Markdown')
        return

    # Marcar el pago como rechazado
    pagos_pendientes[found_payment_id]["status"] = "rejected"
    guardar_pagos_pendientes()

    await update.message.reply_text(f"🗑️ Pago pendiente del usuario `{target_user_id}` (ID: `{found_payment_id}`) rechazado.", parse_mode='Markdown')
    
    # Notificar al usuario
    try:
        await context.bot.send_message(
            chat_id=int(target_user_id),
            text="😔 Lamentamos informarte que tu solicitud de recarga ha sido rechazada. "
                 "Por favor, asegúrate de que la información de pago sea correcta y vuelve a intentarlo. "
                 "Si crees que hay un error, contacta al administrador."
        )
    except Exception as e:
        print(f"Error al notificar al usuario {target_user_id}: {e}")
        await update.message.reply_text(f"⚠️ No se pudo notificar al usuario {target_user_id} sobre el rechazo.")


# --- COMANDO DE ADMINISTRADOR PARA RECARGA MANUAL (EXISTENTE, MEJORADO) ---
async def recargar_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """(ADMIN) Recarga el saldo de un usuario manualmente.
    Uso: /recargar_admin <user_id> <monto>
    O respondiendo a un mensaje: /recargar_admin <monto>
    """
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este comando.")
        return

    target_id = None
    monto = None

    if update.message.reply_to_message:
        target_id = str(update.message.reply_to_message.from_user.id)
        if len(context.args) == 1:
            try:
                monto = float(context.args[0])
            except ValueError:
                await update.message.reply_text("❗ El monto debe ser un número válido.")
                return
        else:
            await update.message.reply_text("Uso: Responde a un usuario con `/recargar_admin <monto>`", parse_mode='Markdown')
            return
    elif len(context.args) == 2:
        target_id = context.args[0]
        try:
            monto = float(context.args[1])
        except ValueError:
            await update.message.reply_text("❗ El monto debe ser un número válido.")
            return
    else:
        await update.message.reply_text("Uso: `/recargar_admin <user_id> <monto>` o responde a un usuario con `/recargar_admin <monto>`", parse_mode='Markdown')
        return

    if monto <= 0:
        await update.message.reply_text("❗ El monto debe ser un número positivo.")
        return

    saldo_usuarios[target_id] = saldo_usuarios.get(target_id, 0.0) + monto
    guardar_saldo()
    await update.message.reply_text(f"✅ Se añadieron *{monto:.2f}€* al usuario `{target_id}`. Saldo actual: *{saldo_usuarios[target_id]:.2f}€*.", parse_mode='Markdown')
    
    # Notificar al usuario recargado (si es diferente al admin)
    if str(update.message.from_user.id) != target_id:
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"🎉 ¡Tu saldo ha sido recargado manualmente con *{monto:.2f}€* por el administrador!\n"
                     f"Tu nuevo saldo es: *{saldo_usuarios[target_id]:.2f}€*",
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Error al notificar al usuario {target_id} sobre la recarga manual: {e}")


# --- FUNCIÓN PRINCIPAL DEL BOT ---
async def main():
    """Función principal para iniciar el bot."""
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Comandos de usuario
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("saldo", saldo))
    application.add_handler(CommandHandler("recargar_saldo", recargar_saldo))

    # Comandos de administrador
    application.add_handler(CommandHandler("recargar_admin", recargar_admin)) # Renombrado para claridad
    application.add_handler(CommandHandler("ver_pagos_pendientes", ver_pagos_pendientes))
    application.add_handler(CommandHandler("aprobar_pago", aprobar_pago))
    application.add_handler(CommandHandler("rechazar_pago", rechazar_pago))

    # Manejadores de callbacks (botones inline)
    application.add_handler(CallbackQueryHandler(button_handler))

    # Manejador de mensajes de texto (filtra para no procesar comandos)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 BOT INICIADO. Esperando actualizaciones...")
    # MODIFICACIÓN CLAVE: close_loop=False para evitar conflictos del bucle de eventos
    await application.run_polling(close_loop=False) 

if __name__ == "__main__":
    # Asegúrate de que el ID del administrador no sea el valor por defecto
    if ADMIN_ID == 8148468413:
        print("⚠️ ¡ADVERTENCIA! Por favor, cambia ADMIN_ID a tu ID de usuario de Telegram real en el código.")
        print("Puedes obtener tu ID enviando un mensaje a @userinfobot en Telegram.")
    
    # Aplicar nest_asyncio para permitir bucles de eventos anidados
    nest_asyncio.apply()
    
    # Ejecuta el bot
    asyncio.run(main())

