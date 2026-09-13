from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
import os
import io
import requests
import asyncio
import random
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("TOKEN")
CMC_API_KEY = os.getenv("CMC_API_KEY")


# ============================================================
# PRICES
# ============================================================

BASE_PRICE = 80
DRIVERS_EXTRA = 15

TRACKED_DPD_PRICE = 15


# ============================================================
# TEXT
# ============================================================

START_CAPTION = """
Welcome to <b>FalseCards</b>,

We've been working since 2023, helping people bring their custom ID designs to life. We focus on providing a smooth, discreet, and reliable service from start to finish, with attention to detail and quality in every order.

<b>We live once, why wait?</b>
"""



# ============================================================
# CRYPTO PAYMENT
# ============================================================

CRYPTO_INFO = {
    "BTC": {
        "name": "BITCOIN",
        "network": "Bitcoin",
        "address": "bc1qwkquvd0lzhqju3gu2zmvu83s6y5t78ywxhds06",
    },
    "SOL": {
        "name": "SOLANA",
        "network": "Solana",
        "address": "5GJe2Fwuo7BbpGQqd71ewymioYtfqnYVnrRoWSYmKEf7",
    },
    "ETH": {
        "name": "ETHEREUM",
        "network": "Ethereum",
        "address": "0xc3eA49C73D573f66bba78c3E5B4FFC0a9F74D30F",
    },
    "USDT": {
        "name": "USDT",
        "network": "TRC20",
        "address": "TX9yS2oTBCs9zCuQWZqg6MTgrW32W8gcus",
    },
}


def get_crypto_amount(symbol, eur_amount):
    if not CMC_API_KEY:
        raise RuntimeError("CMC_API_KEY is not configured.")

    url = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"

    headers = {
        "X-CMC_PRO_API_KEY": CMC_API_KEY,
        "Accepts": "application/json",
    }

    params = {
        "symbol": symbol,
        "convert": "EUR",
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()
    price_eur = data["data"][symbol][0]["quote"]["EUR"]["price"]

    return eur_amount / price_eur


def format_crypto_amount(symbol, amount):
    if symbol == "USDT":
        return f"{amount:.2f}"

    if symbol == "BTC":
        return f"{amount:.8f}".rstrip("0").rstrip(".")

    if symbol == "ETH":
        return f"{amount:.6f}".rstrip("0").rstrip(".")

    return f"{amount:.5f}".rstrip("0").rstrip(".")


# ============================================================
# PRICE
# ============================================================

def calculate_price(context):
    price = BASE_PRICE

    card_type = context.user_data.get("card_type")
    shipping_method = context.user_data.get("shipping_method")

    if card_type == "Driver's license":
        price += MEMBERSHIP_EXTRA

    if shipping_method == "Tracked DPD":
        price += TRACKED_DPD_PRICE

    context.user_data["price"] = price

    return price


# ============================================================
# SUMMARY
# ============================================================

def get_summary(context):
    data = context.user_data

    price = calculate_price(context)

    return (
        "<b>Customize your card</b>\n\n"
        f"<b>Country:</b> {data.get('country', '—')}\n"
        f"<b>Card type:</b> {data.get('card_type', '—')}\n"
        f"<b>Photo:</b> {data.get('photo_status', '—')}\n"
        f"<b>Name:</b> {data.get('name', '—')}\n"
        f"<b>Gender:</b> {data.get('gender', '—')}\n"
        f"<b>Birth date:</b> {data.get('birth_date', '—')}\n\n"
        f"💶 <b>Price:</b> €{price:.2f}"
    )


# ============================================================
# KEYBOARDS
# ============================================================

def get_start_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🇪🇺 Pick a country 🇺🇸",
                    callback_data="pick_country"
                )
            ],
            [
                InlineKeyboardButton(
                    "⭐ Reviews ⭐",
                    callback_data="reviews"
                )
            ],
        ]
    )


def get_country_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🇬🇧 Great Britain",
                    callback_data="country_Great Britain"
                ),
                InlineKeyboardButton(
                    "🇺🇸 USA",
                    callback_data="country_USA"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🇪🇸 Spain",
                    callback_data="country_Spain"
                ),
                InlineKeyboardButton(
                    "🇩🇪 Germany",
                    callback_data="country_Germany"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🇳🇱 Netherlands",
                    callback_data="country_Netherlands"
                ),
                InlineKeyboardButton(
                    "🇵🇱 Poland",
                    callback_data="country_Poland"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🇱🇹 Lithuania",
                    callback_data="country_Lithuania"
                ),
                InlineKeyboardButton(
                    "🇱🇻 Latvia",
                    callback_data="country_Latvia"
                ),
            ],
        ]
    )


def get_card_type_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🪪 ID card",
                    callback_data="type_ID card"
                )
            ],
            [
                InlineKeyboardButton(
                    "🚗 Driver's license (+€15)",
                    callback_data="type_Driver's license"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Back",
                    callback_data="pick_country"
                )
            ],
        ]
    )


def get_gender_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "♂️ Male",
                    callback_data="gender_Male"
                ),
                InlineKeyboardButton(
                    "♀️ Female",
                    callback_data="gender_Female"
                ),
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Back",
                    callback_data="back_name"
                )
            ],
        ]
    )


def get_shipping_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✉️ Untracked envelope (FREE)",
                    callback_data="shipping_Untracked envelope"
                )
            ],
            [
                InlineKeyboardButton(
                    "🚚 Tracked DPD (+€15)",
                    callback_data="shipping_Tracked DPD"
                )
            ],
        ]
    )


def get_payment_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "BTC",
                    callback_data="payment_BTC"
                ),
                InlineKeyboardButton(
                    "ETH",
                    callback_data="payment_ETH"
                ),
            ],
            [
                InlineKeyboardButton(
                    "SOL",
                    callback_data="payment_SOL"
                ),
                InlineKeyboardButton(
                    "USDT",
                    callback_data="payment_USDT"
                ),
            ],
        ]
    )


def get_crypto_payment_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Check payment",
                    callback_data="check_payment"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Back",
                    callback_data="proceed_payment"
                )
            ],
        ]
    )



def build_reviews_collage(review_photos):
    """Build one gallery image so reviews can stay in the same Telegram message."""
    thumb_width = 700
    thumb_height = 700
    columns = 2
    padding = 20

    images = []

    for path in review_photos:
        with Image.open(path) as img:
            img = img.convert("RGB")
            fitted = ImageOps.fit(
                img,
                (thumb_width, thumb_height),
                method=Image.Resampling.LANCZOS
            )
            images.append(fitted.copy())

    if not images:
        return None

    rows = (len(images) + columns - 1) // columns

    canvas_width = columns * thumb_width + (columns + 1) * padding
    canvas_height = rows * thumb_height + (rows + 1) * padding

    canvas = Image.new("RGB", (canvas_width, canvas_height), "white")

    for index, img in enumerate(images):
        row = index // columns
        col = index % columns

        x = padding + col * (thumb_width + padding)
        y = padding + row * (thumb_height + padding)

        canvas.paste(img, (x, y))

    # Telegram photos work best when not absurdly tall.
    max_height = 10000

    if canvas.height > max_height:
        ratio = max_height / canvas.height
        canvas = canvas.resize(
            (int(canvas.width * ratio), max_height),
            Image.Resampling.LANCZOS
        )

    output = io.BytesIO()
    output.name = "reviews.jpg"
    canvas.save(output, format="JPEG", quality=88, optimize=True)
    output.seek(0)

    return output


# ============================================================
# START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    context.user_data["price"] = BASE_PRICE

    with open("logo.jpg", "rb") as photo:
        await update.message.reply_photo(
            photo=photo,
            caption=START_CAPTION,
            parse_mode="HTML",
            reply_markup=get_start_keyboard(),
        )


# ============================================================
# QUESTIONS
# ============================================================

async def show_country_selection(query, context):
    await query.edit_message_caption(
        caption=(
            get_summary(context)
            + "\n\n"
            "<b>Choose your country:</b>"
        ),
        parse_mode="HTML",
        reply_markup=get_country_keyboard(),
    )


async def show_card_type(query, context):
    await query.edit_message_caption(
        caption=(
            get_summary(context)
            + "\n\n"
            "<b>Choose your card type:</b>"
        ),
        parse_mode="HTML",
        reply_markup=get_card_type_keyboard(),
    )


async def ask_for_photo(query, context):
    context.user_data["state"] = "waiting_photo"

    await query.edit_message_caption(
        caption=(
            get_summary(context)
            + "\n\n"
            "<b>Upload a photo:</b>\n\n"
            "Send the image you want to use."
        ),
        parse_mode="HTML",
    )


async def ask_for_name(update, context):
    context.user_data["state"] = "waiting_name"

    with open("logo.jpg", "rb") as photo:
        await update.message.reply_photo(
            photo=photo,
            caption=(
                get_summary(context)
                + "\n\n"
                "<b>What name would you like on the card?</b>"
            ),
            parse_mode="HTML",
        )


async def ask_for_gender(update, context):
    context.user_data["state"] = "waiting_gender"

    with open("logo.jpg", "rb") as photo:
        await update.message.reply_photo(
            photo=photo,
            caption=(
                get_summary(context)
                + "\n\n"
                "<b>Choose gender:</b>"
            ),
            parse_mode="HTML",
            reply_markup=get_gender_keyboard(),
        )


async def ask_for_birth_date(query, context):
    context.user_data["state"] = "waiting_birth_date"

    with open("logo.jpg", "rb") as photo:
        await query.message.reply_photo(
            photo=photo,
            caption=(
                get_summary(context)
                + "\n\n"
                "<b>Enter your birth date:</b>\n\n"
                "Example: 2000-01-31"
            ),
            parse_mode="HTML",
        )


async def ask_for_shipping(query, context):
    context.user_data["state"] = "waiting_shipping_details"

    await query.edit_message_caption(
        caption=(
            "<b>Send your shipping details, one item per line:</b>\n\n"
            "1. Name\n"
            "2. Last name\n"
            "3. Phone number\n"
            "4. Country\n"
            "5. City\n"
            "6. ZIP code\n"
            "7. Address"
        ),
        parse_mode="HTML",
    )


# ============================================================
# BUTTON HANDLER
# ============================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    # REVIEWS
    if query.data == "reviews":
        await query.answer()

        reviews_folder = Path("reviews")
        supported_extensions = {".jpg", ".jpeg", ".png", ".webp"}

        if not reviews_folder.exists() or not reviews_folder.is_dir():
            await query.edit_message_caption(
                caption=(
                    "⭐ <b>Customer Reviews</b>\n\n"
                    "No review photos are available right now."
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    [[
                        InlineKeyboardButton(
                            "⬅️ Back",
                            callback_data="back_start"
                        )
                    ]]
                )
            )
            return

        review_photos = sorted(
            [
                path for path in reviews_folder.iterdir()
                if path.is_file()
                and path.suffix.lower() in supported_extensions
            ]
        )

        if not review_photos:
            await query.edit_message_caption(
                caption=(
                    "⭐ <b>Customer Reviews</b>\n\n"
                    "No review photos are available right now."
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    [[
                        InlineKeyboardButton(
                            "⬅️ Back",
                            callback_data="back_start"
                        )
                    ]]
                )
            )
            return

        collage = build_reviews_collage(review_photos)

        await query.edit_message_media(
            media=InputMediaPhoto(
                media=collage,
                caption=(
                    "⭐ <b>Customer Reviews</b>\n\n"
                    "Here are some photos shared by our customers. "
                    "Thank you to everyone who has supported us! ❤️"
                ),
                parse_mode="HTML"
            ),
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton(
                        "⬅️ Back",
                        callback_data="back_start"
                    )
                ]]
            )
        )

        return

    await query.answer()

    # BACK TO START
    if query.data == "back_start":
        context.user_data["state"] = None

        with open("logo.jpg", "rb") as photo:
            await query.edit_message_media(
                media=InputMediaPhoto(
                    media=photo,
                    caption=START_CAPTION,
                    parse_mode="HTML"
                ),
                reply_markup=get_start_keyboard()
            )

        return

    # COUNTRY PAGE
    if query.data == "pick_country":
        context.user_data["state"] = None
        await show_country_selection(query, context)
        return

    # COUNTRY SELECTED
    if query.data.startswith("country_"):
        country = query.data.replace("country_", "", 1)
        context.user_data["country"] = country
        await show_card_type(query, context)
        return

    # CARD TYPE SELECTED
    if query.data.startswith("type_"):
        card_type = query.data.replace("type_", "", 1)
        context.user_data["card_type"] = card_type
        calculate_price(context)
        await ask_for_photo(query, context)
        return

    # BACK FROM GENDER -> NAME
    if query.data == "back_name":
        context.user_data["state"] = "waiting_name"
        context.user_data.pop("name", None)

        with open("logo.jpg", "rb") as photo:
            await query.message.reply_photo(
                photo=photo,
                caption=(
                    get_summary(context)
                    + "\n\n"
                    "<b>What name would you like on the card?</b>"
                ),
                parse_mode="HTML",
            )
        return

    # GENDER SELECTED
    if query.data.startswith("gender_"):
        gender = query.data.replace("gender_", "", 1)
        context.user_data["gender"] = gender

        # Button choice: edit the existing message.
        context.user_data["state"] = "waiting_birth_date"

        await query.edit_message_caption(
            caption=(
                get_summary(context)
                + "\n\n"
                "<b>Enter your birth date:</b>\n\n"
                "Example: 2000-01-31"
            ),
            parse_mode="HTML",
        )
        return

    # PROCEED TO SHIPPING
    if query.data == "proceed_shipping":
        await ask_for_shipping(query, context)
        return

    # SHIPPING METHOD
    if query.data.startswith("shipping_"):
        shipping_method = query.data.replace("shipping_", "", 1)

        context.user_data["shipping_method"] = shipping_method
        context.user_data["state"] = "ready_for_payment"

        price = calculate_price(context)

        country = context.user_data.get("shipping_country", "—")
        city = context.user_data.get("shipping_city", "—")
        zip_code = context.user_data.get("shipping_zip", "—")
        address = context.user_data.get("shipping_address", "—")

        payment_continue_keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "💳 Proceed to payment",
                        callback_data="proceed_payment"
                    )
                ]
            ]
        )

        # Button choice: edit the existing shipping-method message.
        await query.edit_message_caption(
            caption=(
                f"<b>Address:</b> {country}, {city}, {zip_code}, {address}\n"
                f"<b>Shipping method:</b> {shipping_method}\n"
                f"<b>Total Price:</b> €{price:.2f}"
            ),
            parse_mode="HTML",
            reply_markup=payment_continue_keyboard,
        )
        return

    # PROCEED TO PAYMENT
    if query.data == "proceed_payment":
        context.user_data["state"] = "waiting_payment_method"

        price = calculate_price(context)

        card_type = context.user_data.get("card_type", "—")
        country = context.user_data.get("country", "—")
        shipping_method = context.user_data.get("shipping_method", "—")

        await query.edit_message_caption(
            caption=(f"""
💳 <b>Your Custom Card</b>

🪪 <b>Card type:</b> {card_type}
🌍 <b>Country:</b> {country}
📦 <b>Shipping:</b> {shipping_method}
💰 <b>Total price:</b> €{price:.2f}

<b>How to pay:</b>
1️⃣ Choose the cryptocurrency you want to use.
2️⃣ Copy the provided payment address.
3️⃣ Send the exact amount shown to the provided address.
4️⃣ Wait for your payment to be confirmed.

⚠️ Make sure you send the <b>exact amount shown</b> using the <b>correct network</b>. Payment confirmation may take up to 30 minutes.

👇 <b>Choose a cryptocurrency to continue:</b>"""
            ),
            parse_mode="HTML",
            reply_markup=get_payment_keyboard(),
        )
        return

    # CRYPTO PAYMENT
    if query.data.startswith("payment_"):
        symbol = query.data.replace("payment_", "", 1).upper()

        if symbol not in CRYPTO_INFO:
            return

        coin = CRYPTO_INFO[symbol]
        price = calculate_price(context)

        try:
            amount = get_crypto_amount(symbol, price)
            formatted_amount = format_crypto_amount(symbol, amount)

            context.user_data["payment_method"] = symbol
            context.user_data["crypto_amount"] = formatted_amount

            await query.edit_message_caption(
                caption=(
                    f"💳 <b>{coin['name']} payment</b>\n\n"
                    f"🏦 <b>Address:</b>\n"
                    f"<code>{coin['address']}</code>\n\n"
                    f"⚡ <b>Network:</b> {coin['network']}\n\n"
                    f"💵 <b>Amount:</b> {formatted_amount} {symbol}\n"
                    f"💶 <b>Order total:</b> €{price:.2f}\n\n"
                    "Send <b>exactly</b> the amount shown above.\n\n"
                    "After sending the payment, wait at least 10 minutes "
                    "before checking the payment status.\n\n"
                    "The order may be cancelled if payment is not received in time."
                ),
                parse_mode="HTML",
                reply_markup=get_crypto_payment_keyboard(),
            )

        except Exception as e:
            print("CoinMarketCap API error:", e)

            await query.edit_message_caption(
                caption=(
                    "❌ <b>Could not get the current cryptocurrency price.</b>\n\n"
                    "Please try again in a moment."
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "⬅️ Back",
                                callback_data="proceed_payment"
                            )
                        ]
                    ]
                ),
            )

        return

    # CHECK PAYMENT
    if query.data == "check_payment":
        await asyncio.sleep(random.uniform(0.5, 3.0))

        await query.message.reply_text(
            "❌ Transaction not found. Please try again after 5 minutes."
        )
        return


# ============================================================
# PHOTO HANDLER
# ============================================================

async def photo_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if context.user_data.get("state") != "waiting_photo":
        return

    photo = update.message.photo[-1]

    context.user_data["photo_file_id"] = photo.file_id
    context.user_data["photo_status"] = "✅ Uploaded"

    await ask_for_name(
        update,
        context
    )


# ============================================================
# TEXT HANDLER
# ============================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    state = context.user_data.get("state")

    # NAME
    if state == "waiting_name":
        context.user_data["name"] = update.message.text

        # User typed text: send a new message.
        await ask_for_gender(
            update,
            context
        )
        return

    # BIRTH DATE
    if state == "waiting_birth_date":
        context.user_data["birth_date"] = update.message.text
        context.user_data["state"] = "ready_for_shipping"

        shipping_keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📦 Proceed to shipping",
                        callback_data="proceed_shipping"
                    )
                ]
            ]
        )

        # User typed text: send a new message.
        with open("logo.jpg", "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=(
                    get_summary(context)
                    + "\n\n"
                    "✅ <b>All information received.</b>"
                ),
                parse_mode="HTML",
                reply_markup=shipping_keyboard,
            )
        return

    # SHIPPING DETAILS
    if state == "waiting_shipping_details":
        raw_details = update.message.text.strip()
        context.user_data["shipping_details"] = raw_details

        # Each line is assigned by position:
        # 1 Name
        # 2 Last name
        # 3 Phone
        # 4 Country
        # 5 City
        # 6 ZIP
        # 7 Address
        lines = [line.strip() for line in raw_details.splitlines()]

        if len(lines) != 7:
            await update.message.reply_text(
                "Please send exactly 7 lines:\n\n"
                "1. Name\n"
                "2. Last name\n"
                "3. Phone number\n"
                "4. Country\n"
                "5. City\n"
                "6. ZIP code\n"
                "7. Address"
            )
            return

        name, last_name, phone, country, city, zip_code, address = lines

        required = {
            "Name": name,
            "Last name": last_name,
            "Phone number": phone,
            "Country": country,
            "City": city,
            "ZIP code": zip_code,
            "Address": address,
        }

        missing = [
            field_name
            for field_name, value in required.items()
            if not value
        ]

        if missing:
            await update.message.reply_text(
                f"Missing: {', '.join(missing)}"
            )
            return

        context.user_data["shipping_name"] = name
        context.user_data["shipping_last_name"] = last_name
        context.user_data["shipping_phone"] = phone
        context.user_data["shipping_country"] = country
        context.user_data["shipping_city"] = city
        context.user_data["shipping_zip"] = zip_code
        context.user_data["shipping_address"] = address

        context.user_data["state"] = "waiting_shipping_method"

        price = calculate_price(context)

        # User typed text: send a new message.
        with open("logo.jpg", "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=(
                    "<b>Pick a shipping method:</b>\n\n"
                    f"Current price: <b>€{price:.2f}</b>\n\n"
                    "✉️ Untracked envelope: FREE\n"
                    "🚚 Tracked DPD: +€15"
                ),
                parse_mode="HTML",
                reply_markup=get_shipping_keyboard(),
            )
        return


# ============================================================
# MAIN
# ============================================================

def main():

    app = ApplicationBuilder().token(
        BOT_TOKEN
    ).build()

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    app.run_polling()


if __name__ == "__main__":
    main()
