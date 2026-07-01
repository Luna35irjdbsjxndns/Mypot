import telebot
from telebot import types
import json
import os
import time

# ----------------- الإعدادات الأساسية -----------------
# ⚠️ مهم جداً: لا تضع التوكن مباشرة في الكود إذا كنت ستشارك الملف أو ترفعه لأي مكان عام.
# الأفضل قراءته من متغير بيئة. إن لم يوجد المتغير، يستخدم القيمة الاحتياطية أدناه (غيّرها بتوكنك).
TOKEN = os.environ.get("BOT_TOKEN", "8169778248:AAFd7tm6pu0bOo2W8yRv0kLflvjFHU98VDk")
ADMIN_ID = 8047341602  # الآيدي الخاص بك كمالك

bot = telebot.TeleBot(TOKEN)
DB_FILE = "products_db.json"

# أسماء الأقسام للتحويل
CATEGORIES_MAP = {
    "makeup": "أدوات تجميل",
    "slimming": "منتجات تنحيف",
    "weight_gain": "منتجات زيادة وزن",
    "skincare": "منتجات العناية بالبشرة",
    "haircare": "منتجات العناية بالشعر",
    "hair_removal": "منتجات إزالة شعر"
}

# ----------------- دوال إدارة البيانات (JSON) -----------------
def load_products():
    if not os.path.exists(DB_FILE):
        initial_db = {key: [] for key in CATEGORIES_MAP.keys()}
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(initial_db, f, ensure_ascii=False, indent=4)
        return initial_db
    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # التأكد من وجود كل الأقسام حتى لو تم تعديل CATEGORIES_MAP لاحقاً
    for key in CATEGORIES_MAP.keys():
        data.setdefault(key, [])
    return data

def save_products(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# تحميل المنتجات عند بدء التشغيل
PRODUCTS = load_products()

# قواميس لحفظ حالة المستخدمين مؤقتاً
user_carts = {}
user_steps = {}
user_orders = {}
admin_data = {}  # لحفظ مؤقت لبيانات المنتج المضاف/المعدّل
users_list = set()

# ----------------- أدوات مساعدة لبناء callback_data بأمان -----------------
# نستخدم "::" كفاصل بدل "_" لأن مفاتيح الأقسام ومعرّفات المنتجات تحتوي على "_"
# (مثال: weight_gain ، hair_removal ، p_1750000000) وهذا كان يكسر split("_") سابقاً.
def cb(prefix, value=""):
    return f"{prefix}::{value}" if value != "" else prefix

def cb_parse(data):
    if "::" in data:
        prefix, _, value = data.partition("::")
        return prefix, value
    return data, ""

# ----------------- الكيبوردات الجاهزة -----------------
def get_main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(text=name, callback_data=cb("cat", key)) for key, name in CATEGORIES_MAP.items()]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton(text="🛒 عرض سلة المشتريات", callback_data="view_cart"))
    return markup

def get_admin_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("➕ إضافة منتج جديد", callback_data="adm_add"),
        types.InlineKeyboardButton("❌ حذف منتج حالي", callback_data="adm_del"),
        types.InlineKeyboardButton("💰 تعديل سعر منتج", callback_data="adm_price"),
        types.InlineKeyboardButton("📢 إرسال إذاعة جماعية للكل", callback_data="admin_broadcast")
    )
    return markup

def get_product_by_id(prod_id):
    for cat, items in PRODUCTS.items():
        for item in items:
            if item["id"] == prod_id:
                return item
    return None

def clean(text):
    """يمنع كسر Markdown عند وجود رموز خاصة داخل نص المنتج (اسم/وصف يكتبه الأدمن)."""
    if text is None:
        return ""
    for ch in ["*", "_", "`", "["]:
        text = text.replace(ch, "")
    return text

# ----------------- الأوامر الرئيسية -----------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user_id = message.chat.id
        users_list.add(user_id)
        user_steps[user_id] = None

        welcome_text = (
            "أهلاً وسهلاً بك في بوت Nour Beauty 🤩😍\n"
            "نقدم لك أفضل المنتجات التجميلية من ماركات عالمية 😍\n"
            "في هذه القائمة ستجدين كل شيء تحتاجينه"
        )
        if user_id == ADMIN_ID:
            welcome_text += "\n\n⚙️ أنت المالك: لإدارة المنتجات والأسعار أرسل الأمر: /admin"

        bot.send_message(user_id, welcome_text, reply_markup=get_main_keyboard())
    except Exception as e:
        print(f"حدث خطأ بسيط وتم تلافيه تلقائياً: {e}")

@bot.message_handler(commands=['cancel'])
def cancel_flow(message):
    try:
        user_id = message.chat.id
        user_steps[user_id] = None
        bot.send_message(user_id, "❎ تم إلغاء العملية الحالية.",
                          reply_markup=get_admin_keyboard() if user_id == ADMIN_ID else get_main_keyboard())
    except Exception as e:
        print(f"حدث خطأ بسيط وتم تلافيه تلقائياً: {e}")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    try:
        if message.chat.id == ADMIN_ID:
            bot.send_message(ADMIN_ID, "🛠️ لوحة قيادة المالك الذكية:\nاختر ماذا تريد أن تفعل بالمنتجات الآن:", reply_markup=get_admin_keyboard())
        else:
            bot.send_message(message.chat.id, "عذراً، هذا الأمر خاص بالمالك فقط.")
    except Exception as e:
        print(f"حدث خطأ بسيط وتم تلافيه تلقائياً: {e}")

# ----------------- معالجة أزرار لوحة القيادة والتصفح -----------------
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    global PRODUCTS
    try:
        user_id = call.message.chat.id
        data = call.data
        prefix, value = cb_parse(data)

        # ---------- تصفح الزبائن ----------
        if prefix == "cat":
            category_key = value
            category_name = CATEGORIES_MAP.get(category_key, "القسم")
            products_list = PRODUCTS.get(category_key, [])

            if not products_list:
                bot.answer_callback_query(call.id)
                bot.send_message(user_id, f"⚠️ لا توجد منتجات في قسم {category_name} حالياً.", reply_markup=get_main_keyboard())
                return

            bot.answer_callback_query(call.id)
            bot.send_message(user_id, f"📦 منتجات قسم {category_name}:")
            for prod in products_list:
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("🔎 التفاصيل", callback_data=cb("view", prod['id'])),
                    types.InlineKeyboardButton("🛒 إضافة للسلة", callback_data=cb("add", prod['id']))
                )
                caption = f"🛍️ {clean(prod['name'])}\n💰 السعر: {clean(prod['price'])}"
                if str(prod.get("image", "")).startswith("http"):
                    try:
                        bot.send_photo(user_id, photo=prod["image"], caption=caption, reply_markup=markup)
                    except Exception:
                        bot.send_message(user_id, caption, reply_markup=markup)
                else:
                    bot.send_message(user_id, caption, reply_markup=markup)

        elif prefix == "view":
            prod = get_product_by_id(value)
            bot.answer_callback_query(call.id)
            if prod:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🛒 إضافة إلى السلة", callback_data=cb("add", value)))
                markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
                caption = f"🛍️ {clean(prod['name'])}\n\n📝 الوصف:\n{clean(prod['desc'])}\n\n💰 السعر: {clean(prod['price'])}"
                bot.send_message(user_id, caption, reply_markup=markup)
            else:
                bot.send_message(user_id, "⚠️ هذا المنتج لم يعد متوفراً.")

        elif prefix == "add":
            prod = get_product_by_id(value)
            if prod:
                user_carts.setdefault(user_id, []).append(prod)
                bot.answer_callback_query(call.id, f"✅ أضيف {prod['name']} للسلة!", show_alert=True)
            else:
                bot.answer_callback_query(call.id, "⚠️ هذا المنتج لم يعد متوفراً.", show_alert=True)

        elif data == "view_cart":
            bot.answer_callback_query(call.id)
            cart = user_carts.get(user_id, [])
            if not cart:
                bot.send_message(user_id, "🛒 سلة المشتريات فارغة حالياً.", reply_markup=get_main_keyboard())
                return
            cart_text = "🛒 محتويات سلتك الحالية:\n\n"
            for idx, item in enumerate(cart, 1):
                cart_text += f"{idx}. {item['name']} - ({item['price']})\n"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ تأكيد وشراء الطلب", callback_data="checkout"))
            markup.add(types.InlineKeyboardButton("🗑️ تفريغ السلة", callback_data="clear_cart"))
            markup.add(types.InlineKeyboardButton("🔙 متابعة التسوق", callback_data="main_menu"))
            bot.send_message(user_id, cart_text, reply_markup=markup)

        elif data == "clear_cart":
            user_carts[user_id] = []
            bot.answer_callback_query(call.id, "تم تفريغ السلة")
            bot.send_message(user_id, "🗑️ تم إفراغ سلتك.", reply_markup=get_main_keyboard())

        elif data == "main_menu":
            bot.answer_callback_query(call.id)
            bot.send_message(user_id, "🎛️ الأقسام الرئيسية:", reply_markup=get_main_keyboard())

        elif data == "checkout":
            if not user_carts.get(user_id):
                bot.answer_callback_query(call.id, "سلتك فارغة!", show_alert=True)
                return
            bot.answer_callback_query(call.id)
            bot.send_message(user_id, "📝 الرجاء إرسال الاسم الكامل للمستلم (أو /cancel للإلغاء):")
            user_steps[user_id] = "get_name"
            user_orders[user_id] = {"items": user_carts.get(user_id, [])}

        # ---------- لوحة قيادة الآدمن ----------
        elif data == "adm_add" and user_id == ADMIN_ID:
            bot.answer_callback_query(call.id)
            markup = types.InlineKeyboardMarkup()
            for key, name in CATEGORIES_MAP.items():
                markup.add(types.InlineKeyboardButton(name, callback_data=cb("addto", key)))
            bot.send_message(ADMIN_ID, "📁 اختر القسم الذي تريد إضافة المنتج إليه:", reply_markup=markup)

        elif prefix == "addto" and user_id == ADMIN_ID:
            bot.answer_callback_query(call.id)
            admin_data[ADMIN_ID] = {"category": value}
            bot.send_message(ADMIN_ID, "✍️ حسناً، أرسل الآن اسم المنتج الجديد (أو /cancel للإلغاء):")
            user_steps[ADMIN_ID] = "adm_get_name"

        elif data == "adm_del" and user_id == ADMIN_ID:
            bot.answer_callback_query(call.id)
            markup = types.InlineKeyboardMarkup()
            for key, name in CATEGORIES_MAP.items():
                count = len(PRODUCTS.get(key, []))
                markup.add(types.InlineKeyboardButton(f"{name} ({count})", callback_data=cb("delcat", key)))
            bot.send_message(ADMIN_ID, "📁 اختر القسم لحذف منتج منه:", reply_markup=markup)

        elif prefix == "delcat" and user_id == ADMIN_ID:
            bot.answer_callback_query(call.id)
            cat_key = value
            products_list = PRODUCTS.get(cat_key, [])
            if not products_list:
                bot.send_message(ADMIN_ID, "⚠️ لا توجد منتجات في هذا القسم لحذفها.", reply_markup=get_admin_keyboard())
                return
            markup = types.InlineKeyboardMarkup()
            for prod in products_list:
                markup.add(types.InlineKeyboardButton(f"❌ {prod['name']}", callback_data=cb("execute_del", prod['id'])))
            markup.add(types.InlineKeyboardButton("🔙 إلغاء", callback_data="admin_main"))
            bot.send_message(ADMIN_ID, "🗑️ اضغط على المنتج الذي تريد حذفه نهائياً:", reply_markup=markup)

        elif prefix == "execute_del" and user_id == ADMIN_ID:
            prod_id = value
            deleted_name = None
            for cat in PRODUCTS:
                for p in PRODUCTS[cat]:
                    if p["id"] == prod_id:
                        deleted_name = p["name"]
                PRODUCTS[cat] = [p for p in PRODUCTS[cat] if p["id"] != prod_id]
            save_products(PRODUCTS)
            bot.answer_callback_query(call.id, "✅ تم حذف المنتج بنجاح لحظياً!", show_alert=True)
            label = f" ({deleted_name})" if deleted_name else ""
            bot.send_message(ADMIN_ID, f"🛠️ تم حذف المنتج{label} وتحديث المتجر.", reply_markup=get_admin_keyboard())

        elif data == "adm_price" and user_id == ADMIN_ID:
            bot.answer_callback_query(call.id)
            markup = types.InlineKeyboardMarkup()
            for key, name in CATEGORIES_MAP.items():
                count = len(PRODUCTS.get(key, []))
                markup.add(types.InlineKeyboardButton(f"{name} ({count})", callback_data=cb("pricecat", key)))
            bot.send_message(ADMIN_ID, "📁 اختر القسم لتعديل سعر منتج فيه:", reply_markup=markup)

        elif prefix == "pricecat" and user_id == ADMIN_ID:
            bot.answer_callback_query(call.id)
            cat_key = value
            products_list = PRODUCTS.get(cat_key, [])
            if not products_list:
                bot.send_message(ADMIN_ID, "⚠️ لا توجد منتجات في هذا القسم.", reply_markup=get_admin_keyboard())
                return
            markup = types.InlineKeyboardMarkup()
            for prod in products_list:
                markup.add(types.InlineKeyboardButton(f"💰 {prod['name']} ({prod['price']})", callback_data=cb("editprice", prod['id'])))
            bot.send_message(ADMIN_ID, "اختر المنتج الذي ترغب بتغيير سعره:", reply_markup=markup)

        elif prefix == "editprice" and user_id == ADMIN_ID:
            bot.answer_callback_query(call.id)
            admin_data[ADMIN_ID] = {"edit_price_id": value}
            bot.send_message(ADMIN_ID, "💰 أرسل السعر الجديد الآن (مثال: 50$ أو 250 ليرة) أو /cancel للإلغاء:")
            user_steps[ADMIN_ID] = "adm_get_new_price"

        elif data == "admin_broadcast" and user_id == ADMIN_ID:
            bot.answer_callback_query(call.id)
            bot.send_message(ADMIN_ID, "📢 أرسل نص رسالة الإعلان الجماعي (أو /cancel للإلغاء):")
            user_steps[ADMIN_ID] = "get_broadcast_msg"

        elif data == "admin_main" and user_id == ADMIN_ID:
            bot.answer_callback_query(call.id)
            bot.send_message(ADMIN_ID, "🛠️ لوحة قيادة المالك:", reply_markup=get_admin_keyboard())

        else:
            bot.answer_callback_query(call.id)

    except Exception as e:
        print(f"حدث خطأ في الأزرار وتم تخطيه تلقائياً: {e}")

# ----------------- معالجة المدخلات النصية (زبائن + مالك) -----------------
@bot.message_handler(func=lambda message: True)
def handle_text_inputs(message):
    global PRODUCTS
    try:
        user_id = message.chat.id
        users_list.add(user_id)
        step = user_steps.get(user_id)

        # --- خطوات الشراء للعميل ---
        if step == "get_name":
            user_orders[user_id]["name"] = message.text
            bot.send_message(user_id, "📍 أرسل العنوان بالتفصيل:")
            user_steps[user_id] = "get_address"

        elif step == "get_address":
            user_orders[user_id]["address"] = message.text
            bot.send_message(user_id, "📞 أرسل رقم الهاتف:")
            user_steps[user_id] = "get_phone"

        elif step == "get_phone":
            user_orders[user_id]["phone"] = message.text
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add("💵 الدفع عند الاستلام (COD)", "💳 تحويل إلكتروني")
            bot.send_message(user_id, "💳 اختر طريقة الدفع:", reply_markup=markup)
            user_steps[user_id] = "get_payment"

        elif step == "get_payment":
            user_orders[user_id]["payment"] = message.text
            order_data = user_orders[user_id]
            bot.send_message(user_id, "🎉 تم استلام طلبك بنجاح ياباشا!", reply_markup=types.ReplyKeyboardRemove())

            items_text = "".join([f"   - {item['name']} ({item['price']})\n" for item in order_data["items"]])
            admin_invoice = (
                f"🚨 طلب جديد واصل! 🚨\n\n"
                f"👤 العميل: {order_data['name']}\n"
                f"📞 الهاتف: {order_data['phone']}\n"
                f"📍 العنوان: {order_data['address']}\n"
                f"💳 الدفع: {order_data['payment']}\n\n"
                f"📦 المنتجات:\n{items_text}"
            )
            bot.send_message(ADMIN_ID, admin_invoice)
            user_carts[user_id] = []
            user_steps[user_id] = None

        # --- خطوات لوحة القيادة التفاعلية (للمالك فقط) ---
        elif user_id == ADMIN_ID and step == "adm_get_name":
            admin_data[ADMIN_ID]["name"] = message.text
            bot.send_message(ADMIN_ID, "💰 ممتاز، أرسل الآن السعر للمنتج:")
            user_steps[ADMIN_ID] = "adm_get_price"

        elif user_id == ADMIN_ID and step == "adm_get_price":
            admin_data[ADMIN_ID]["price"] = message.text
            bot.send_message(ADMIN_ID, "📝 أرسل الآن الوصف والشرح للمنتج:")
            user_steps[ADMIN_ID] = "adm_get_desc"

        elif user_id == ADMIN_ID and step == "adm_get_desc":
            admin_data[ADMIN_ID]["desc"] = message.text
            bot.send_message(ADMIN_ID, "🖼️ أرسل الآن رابط صورة المنتج (إذا لم يتوفر اكتب: لا يوجد):")
            user_steps[ADMIN_ID] = "adm_get_img"

        elif user_id == ADMIN_ID and step == "adm_get_img":
            img = message.text.strip()
            admin_data[ADMIN_ID]["image"] = img if img.startswith("http") else "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9"

            cat = admin_data[ADMIN_ID]["category"]
            prod_id = f"p_{int(time.time()*1000)}"

            new_product = {
                "id": prod_id,
                "name": admin_data[ADMIN_ID]["name"],
                "price": admin_data[ADMIN_ID]["price"],
                "desc": admin_data[ADMIN_ID]["desc"],
                "image": admin_data[ADMIN_ID]["image"]
            }

            PRODUCTS.setdefault(cat, []).append(new_product)
            save_products(PRODUCTS)

            bot.send_message(ADMIN_ID, f"✅ تم إضافة منتج ({new_product['name']}) بنجاح وتحديث المتجر لحظياً للزبائن!", reply_markup=get_admin_keyboard())
            user_steps[ADMIN_ID] = None
            admin_data.pop(ADMIN_ID, None)

        elif user_id == ADMIN_ID and step == "adm_get_new_price":
            new_p = message.text.strip()
            p_id = admin_data.get(ADMIN_ID, {}).get("edit_price_id")

            found = False
            for cat in PRODUCTS:
                for p in PRODUCTS[cat]:
                    if p["id"] == p_id:
                        p["price"] = new_p
                        found = True
                        break
            if found:
                save_products(PRODUCTS)
                bot.send_message(ADMIN_ID, "✅ تم تعديل السعر بنجاح وتحديثه فوراً!", reply_markup=get_admin_keyboard())
            else:
                bot.send_message(ADMIN_ID, "⚠️ تعذر إيجاد المنتج (ربما تم حذفه).", reply_markup=get_admin_keyboard())
            user_steps[ADMIN_ID] = None
            admin_data.pop(ADMIN_ID, None)

        elif user_id == ADMIN_ID and step == "get_broadcast_msg":
            bot.send_message(ADMIN_ID, "⏳ جاري الإرسال...")
            success = 0
            failed = 0
            for u_id in list(users_list):
                try:
                    bot.send_message(u_id, f"📢 إعلان جديد من المتجر:\n\n{message.text}")
                    success += 1
                except Exception:
                    failed += 1
            bot.send_message(ADMIN_ID, f"✅ تمت الإذاعة لـ {success} مستخدم. (فشل: {failed})", reply_markup=get_admin_keyboard())
            user_steps[ADMIN_ID] = None

    except Exception as e:
        print(f"حدث خطأ في المدخلات النصية وتم تخطيه تلقائياً: {e}")

print("⚡ لوحة التحكم الذكية جاهزة للاستخدام اللحظي ياباشا...")

# التعديل المثالي لسرعة الاستجابة وإعادة الاتصال التلقائي الفوري دون توقف
bot.infinity_polling(timeout=15, long_polling_timeout=5)
