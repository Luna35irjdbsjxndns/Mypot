import telebot
from telebot import types
import json
import os
import time

# ----------------- الإعدادات الأساسية -----------------
TOKEN = "8169778248:AAFd7tm6pu0bOo2W8yRv0kLflvjFHU98VDk"  # توكن البوت الخاص بك
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

# ----------------- دالات إدارة البيانات (JSON) -----------------
def load_products():
    if not os.path.exists(DB_FILE):
        initial_db = {key: [] for key in CATEGORIES_MAP.keys()}
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(initial_db, f, ensure_ascii=False, indent=4)
        return initial_db
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_products(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# تحميل المنتجات عند بدء التشغيل
PRODUCTS = load_products()

# قواميس لحفظ حالة المستخدمين مؤقتاً
user_carts = {}
user_steps = {}
user_orders = {}
admin_data = {}  # لحفظ مؤقت لبيانات المنتج المضاف الجديد
users_list = set()

# ----------------- الكيبوردات الجاهزة -----------------
def get_main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(text=name, callback_data=f"cat_{key}") for key, name in CATEGORIES_MAP.items()]
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

# ----------------- الأوامر الرئيسية -----------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user_id = message.chat.id
        users_list.add(user_id)
        
        welcome_text = (
            "أهلاً وسهلا بك في بوت Nour Beauty 🤩😍\n"
            "نقدم لك أفضل المنتجات التجميلية من ماركات   \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ عالمية 😍\_\_\_\_\_\_\_\_\_\_\_\_ \n"
            "في هذه القائمة ستجدين كل شيء تحتاجينه"
        )
        if user_id == ADMIN_ID:
            welcome_text += "\n\n⚙️ **أنت المالك:** لإدارة المنتجات والأسعار أرسل الأمر: /admin"
            
        bot.send_message(user_id, welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    except Exception as e:
        print(f"خطأ في البدء: {e}")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    try:
        if message.chat.id == ADMIN_ID:
            bot.send_message(ADMIN_ID, "🛠️ **لوحة قيادة المالك الذكية:**\nاختر ماذا تريد أن تفعل بالمنتجات الآن:", reply_markup=get_admin_keyboard())
        else:
            bot.send_message(message.chat.id, "عذراً، هذا الأمر خاص بالمالك فقط.")
    except Exception as e:
        print(f"خطأ في الآدمن: {e}")

# ----------------- معالجة أزرار لوحة القيادة والتصفح -----------------
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    global PRODUCTS
    try:
        user_id = call.message.chat.id
        data = call.data

        # تصفح زبائن
        if data.startswith("cat_"):
            category_key = data.split("_")[1]
            category_name = CATEGORIES_MAP.get(category_key, "القسم")
            products_list = PRODUCTS.get(category_key, [])
            
            if not products_list:
                bot.send_message(user_id, f"⚠️ لا توجد منتجات في قسم {category_name} حالياً.")
                return
                
            bot.send_message(user_id, f"📦 **منتجات قسم {category_name}:**")
            for prod in products_list:
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("🔎 التفاصيل", callback_data=f"view_{prod['id']}"),
                    types.InlineKeyboardButton("🛒 إضافة للسلة", callback_data=f"add_{prod['id']}")
                )
                if prod["image"].startswith("http"):
                    bot.send_photo(user_id, photo=prod["image"], caption=f"🛍️ **{prod['name']}**\n💰 السعر: {prod['price']}", reply_markup=markup, parse_mode="Markdown")
                else:
                    bot.send_message(user_id, f"🛍️ **{prod['name']}**\n💰 السعر: {prod['price']}", reply_markup=markup, parse_mode="Markdown")

        elif data.startswith("view_"):
            prod_id = data.split("_")[1]
            prod = get_product_by_id(prod_id)
            if prod:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🛒 إضافة إلى السلة", callback_data=f"add_{prod_id}"))
                markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
                caption = f"🛍️ **{prod['name']}**\n\n📝 **الوصف:**\n{prod['desc']}\n\n💰 **السعر:** {prod['price']}"
                bot.send_message(user_id, caption, reply_markup=markup, parse_mode="Markdown")

        elif data.startswith("add_"):
            prod_id = data.split("_")[1]
            prod = get_product_by_id(prod_id)
            if prod:
                if user_id not in user_carts: user_carts[user_id] = []
                user_carts[user_id].append(prod)
                bot.answer_callback_query(call.id, f"✅ أضيف {prod['name']} للسلة!", show_alert=True)

        elif data == "view_cart":
            cart = user_carts.get(user_id, [])
            if not cart:
                bot.send_message(user_id, "🛒 سلة المشتريات فارغة حالياً.", reply_markup=get_main_keyboard())
                return
            cart_text = "🛒 **محتويات سلتك الحالية:**\n\n"
            for idx, item in enumerate(cart, 1):
                cart_text += f"{idx}. {item['name']} - ({item['price']})\n"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ تأكيد وشراء الطلب", callback_data="checkout"), types.InlineKeyboardButton("🗑️ تفريغ السلة", callback_data="clear_cart"))
            bot.send_message(user_id, cart_text, reply_markup=markup, parse_mode="Markdown")

        elif data == "clear_cart":
            user_carts[user_id] = []
            bot.send_message(user_id, "🗑️ تم إفراغ سلتك.", reply_markup=get_main_keyboard())

        elif data == "main_menu":
            bot.send_message(user_id, "🎛️ الأقسام الرئيسية:", reply_markup=get_main_keyboard())

        elif data == "checkout":
            bot.send_message(user_id, "📝 الرجاء إرسال **الاسم الكامل** للمستلم:")
            user_steps[user_id] = "get_name"
            user_orders[user_id] = {"items": user_carts.get(user_id, [])}

        # ----- أقسام لوحة قيادة الآدمن -----
        elif data == "adm_add" and user_id == ADMIN_ID:
            markup = types.InlineKeyboardMarkup()
            for key, name in CATEGORIES_MAP.items():
                markup.add(types.InlineKeyboardButton(name, callback_data=f"addto_{key}"))
            bot.send_message(ADMIN_ID, "📁 اختر القسم الذي تريد إضافة المنتج إليه:", reply_markup=markup)

        elif data.startswith("addto_") and user_id == ADMIN_ID:
            cat_target = data.split("_")[1]
            admin_data[ADMIN_ID] = {"category": cat_target}
            bot.send_message(ADMIN_ID, "✍️ حسناً، أرسل الآن **اسم المنتج** الجديد:")
            user_steps[ADMIN_ID] = "adm_get_name"

        elif data == "adm_del" and user_id == ADMIN_ID:
            markup = types.InlineKeyboardMarkup()
            for key, name in CATEGORIES_MAP.items():
                markup.add(types.InlineKeyboardButton(name, callback_data=f"delcat_{key}"))
            bot.send_message(ADMIN_ID, "📁 اختر القسم لحذف منتج منه:", reply_markup=markup)

        elif data.startswith("delcat_") and user_id == ADMIN_ID:
            cat_key = data.split("_")[1]
            markup = types.InlineKeyboardMarkup()
            for prod in PRODUCTS.get(cat_key, []):
                markup.add(types.InlineKeyboardButton(f"❌ {prod['name']}", callback_data=f"execute_del_{prod['id']}"))
            markup.add(types.InlineKeyboardButton("🔙 إلغاء", callback_data="admin_main"))
            bot.send_message(ADMIN_ID, "🗑️ اضغط على المنتج الذي تريد حذفه نهائياً:", reply_markup=markup)

        elif data.startswith("execute_del_") and user_id == ADMIN_ID:
            prod_id = data.split("_")[2]
            for cat in PRODUCTS:
                PRODUCTS[cat] = [p for p in PRODUCTS[cat] if p["id"] != prod_id]
            save_products(PRODUCTS)
            bot.answer_callback_query(call.id, "✅ تم حذف المنتج بنجاح لحظياً!", show_alert=True)
            bot.send_message(ADMIN_ID, "🛠️ تم التحديث الحظي.", reply_markup=get_admin_keyboard())

        elif data == "adm_price" and user_id == ADMIN_ID:
            markup = types.InlineKeyboardMarkup()
            for key, name in CATEGORIES_MAP.items():
                markup.add(types.InlineKeyboardButton(name, callback_data=f"pricecat_{key}"))
            bot.send_message(ADMIN_ID, "📁 اختر القسم لتعديل سعر منتج فيه:", reply_markup=markup)

        elif data.startswith("pricecat_") and user_id == ADMIN_ID:
            cat_key = data.split("_")[1]
            markup = types.InlineKeyboardMarkup()
            for prod in PRODUCTS.get(cat_key, []):
                markup.add(types.InlineKeyboardButton(f"💰 {prod['name']} ({prod['price']})", callback_data=f"editprice_{prod['id']}"))
            bot.send_message(ADMIN_ID, "اختر المنتج الذي ترغب بتغيير سعره:", reply_markup=markup)

        elif data.startswith("editprice_") and user_id == ADMIN_ID:
            prod_id = data.split("_")[1]
            admin_data[ADMIN_ID] = {"edit_price_id": prod_id}
            bot.send_message(ADMIN_ID, "💰 أرسل السعر الجديد الآن (مثال: 50$ أو 250 ليرة):")
            user_steps[ADMIN_ID] = "adm_get_new_price"

        elif data == "admin_broadcast" and user_id == ADMIN_ID:
            bot.send_message(ADMIN_ID, "📢 أرسل نص رسالة الإعلان الجماعي:")
            user_steps[ADMIN_ID] = "get_broadcast_msg"
            
        elif data == "admin_main" and user_id == ADMIN_ID:
            bot.send_message(ADMIN_ID, "🛠️ لوحة قيادة المالك:", reply_markup=get_admin_keyboard())
    except Exception as e:
        print(f"خطأ في الأزرار: {e}")

# ----------------- معالجة المدخلات النصية (زبائن + مالك) -----------------
@bot.message_handler(func=lambda message: True)
def handle_text_inputs(message):
    global PRODUCTS
    try:
        user_id = message.chat.id
        step = user_steps.get(user_id)

        # --- خطوات الشراء للعميل ---
        if step == "get_name":
            user_orders[user_id]["name"] = message.text
            bot.send_message(user_id, "📍 أرسل **العنوان بالتفصيل**:")
            user_steps[user_id] = "get_address"
        elif step == "get_address":
            user_orders[user_id]["address"] = message.text
            bot.send_message(user_id, "📞 أرسل **رقم الهاتف**:")
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
            admin_invoice = f"🚨 **طلب جديد واصل!** 🚨\n\n👤 **العميل:** {order_data['name']}\n📞 **الهاتف:** {order_data['phone']}\n📍 **العنوان:** {order_data['address']}\n💳 **الدفع:** {order_data['payment']}\n\n📦 **المنتجات:**\n{items_text}"
            bot.send_message(ADMIN_ID, admin_invoice, parse_mode="Markdown")
            user_carts[user_id] = []
            user_steps[user_id] = None

        # --- خطوات لوحة القيادة التفاعلية (للمالك فقط) ---
        elif user_id == ADMIN_ID:
            if step == "adm_get_name":
                admin_data[ADMIN_ID]["name"] = message.text
                bot.send_message(ADMIN_ID, "💰 ممتاز، أرسل الآن **السعر** للمنتج:")
                user_steps[ADMIN_ID] = "adm_get_price"
                
            elif step == "adm_get_price":
                admin_data[ADMIN_ID]["price"] = message.text
                bot.send_message(ADMIN_ID, "📝 أرسل الآن **الوصف والشرح** للمنتج:")
                user_steps[ADMIN_ID] = "adm_get_desc"
                
            elif step == "adm_get_desc":
                admin_data[ADMIN_ID]["desc"] = message.text
                bot.send_message(ADMIN_ID, "🖼️ أرسل الآن **رابط صورة** المنتج (إذا لم يتوفر اكتب لا يوجد):")
                user_steps[ADMIN_ID] = "adm_get_img"
                
            elif step == "adm_get_img":
                img = message.text
                admin_data[ADMIN_ID]["image"] = img if img.startswith("http") else "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9"
                
                cat = admin_data[ADMIN_ID]["category"]
                prod_id = f"p_{int(time.time())}"
                
                new_product = {
                    "id": prod_id,
                    "name": admin_data[ADMIN_ID]["name"],
                    "price": admin_data[ADMIN_ID]["price"],
                    "desc": admin_data[ADMIN_ID]["desc"],
                    "image": admin_data[ADMIN_ID]["image"]
                }
                
                PRODUCTS[cat].append(new_product)
                save_products(PRODUCTS)
                
                bot.send_message(ADMIN_ID, f"✅ تم إضافة منتج **({new_product['name']})** بنجاح وتحديث المتجر لحظياً للزبائن!", reply_markup=get_admin_keyboard())
                user_steps[ADMIN_ID] = None
                
            elif step == "adm_get_new_price":
                new_p = message.text
                p_id = admin_data[ADMIN_ID]["edit_price_id"]
                
                for cat in PRODUCTS:
                    for p in PRODUCTS[cat]:
                        if p["id"] == p_id:
                            p["price"] = new_p
                            break
                save_products(PRODUCTS)
                bot.send_message(ADMIN_ID, "✅ تم تعديل السعر بنجاح وتحديثه فوراً!", reply_markup=get_admin_keyboard())
                user_steps[ADMIN_ID] = None

            elif step == "get_broadcast_msg":
                bot.send_message(ADMIN_ID, "⏳ جاري الإرسال...")
                success = 0
                for u_id in list(users_list):
                    try:
                        bot.send_message(u_id, f"📢 **إعلان جديد من المتجر:**\n\n{message.text}", parse_mode="Markdown")
                        success += 1
                    except: pass
                bot.send_message(ADMIN_ID, f"✅ تمت الإذاعة لـ {success} مستخدم.", reply_markup=get_admin_keyboard())
                user_steps[ADMIN_ID] = None
    except Exception as e:
        print(f"خطأ في المدخلات: {e}")

print("⚡ لوحة التحكم الذكية جاهزة للاستخدام اللحظي ياباشا...")

# تم تحديث قيم الـ timeout إلى 60 لضمان استقرار الاتصال في ظروف الشبكة المتقلبة
bot.infinity_polling(timeout=60, long_polling_timeout=60, logger_level=5)
