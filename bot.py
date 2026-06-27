import telebot
from telebot import types
import json
import os
import time

# ----------------- الإعدادات الأساسية -----------------
TOKEN = "8169778248:AAFd7tm6pu0bOo2W8yRv0kLflvjFHU98VDk"
ADMIN_ID = 8047341602

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
        initial_db["coupons"] = {}
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(initial_db, f, ensure_ascii=False, indent=4)
        return initial_db
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except:
            data = {key: [] for key in CATEGORIES_MAP.keys()}
        if "coupons" not in data:
            data["coupons"] = {}
        return data

def save_products(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

PRODUCTS = load_products()

user_carts = {}
user_steps = {}
user_orders = {}
user_applied_coupons = {}
admin_data = {}
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
        types.InlineKeyboardButton("🎟️ إدارة الكوبونات والخصومات", callback_data="adm_coupons"),
        types.InlineKeyboardButton("📢 إرسال إذاعة جماعية للكل", callback_data="admin_broadcast")
    )
    return markup

def get_product_by_id(prod_id):
    global PRODUCTS
    PRODUCTS = load_products()
    for cat, items in PRODUCTS.items():
        if cat == "coupons": continue
        for item in items:
            if item["id"] == prod_id:
                return item, cat
    return None, None

# ----------------- الأوامر الرئيسية -----------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    users_list.add(user_id)
    
    welcome_text = (
        f"أهلاً بك ياباشا في متجرنا الإلكتروني! 🌸✨\n\n"
        f"تصفح أقسامنا واختر ما يناسبك عبر الأزرار أدناه:"
    )
    if user_id == ADMIN_ID:
        welcome_text += "\n\n⚙️ **أنت المالك:** لإدارة المنتجات والأسعار أرسل الأمر: /admin"
        
    bot.send_message(user_id, welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id == ADMIN_ID:
        bot.send_message(ADMIN_ID, "🛠️ **لوحة قيادة المالك الذكية:**\nاختر ماذا تريد أن تفعل بالمنتجات الآن:", reply_markup=get_admin_keyboard())
    else:
        bot.send_message(message.chat.id, "عذراً، هذا الأمر خاص بالمالك فقط.")

# ----------------- معالجة الأزرار والتصفح -----------------
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    global PRODUCTS
    PRODUCTS = load_products()
    user_id = call.message.chat.id
    message_id = call.message.message_id
    data = call.data

    if data.startswith("cat_"):
        category_key = data.split("_")[1]
        category_name = CATEGORIES_MAP.get(category_key, "القسم")
        products_list = PRODUCTS.get(category_key, [])
        
        if not products_list:
            bot.answer_callback_query(call.id, f"⚠️ لا توجد منتجات في قسم {category_name} حالياً.", show_alert=True)
            return
            
        markup = types.InlineKeyboardMarkup(row_width=1)
        for prod in products_list:
            markup.add(types.InlineKeyboardButton(text=f"🛍️ {prod['name']} ({prod['price']})", callback_data=f"view_{prod['id']}"))
        markup.add(types.InlineKeyboardButton("🔙 عودة للقائمة الرئيسية", callback_data="main_menu"))
        
        if call.message.content_type == 'photo':
            try: bot.delete_message(user_id, message_id)
            except: pass
            bot.send_message(user_id, f"📦 **منتجات قسم {category_name}:**\nاختر المنتج لمعاينة التفاصيل:", reply_markup=markup, parse_mode="Markdown")
        else:
            bot.edit_message_text(chat_id=user_id, message_id=message_id, text=f"📦 **منتجات قسم {category_name}:**\nاختر المنتج لمعاينة التفاصيل:", reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("view_"):
        prod_id = data.split("_")[1]
        prod, cat_key = get_product_by_id(prod_id)
        if prod:
            try: bot.delete_message(user_id, message_id)
            except: pass
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("🛒 إضافة إلى السلة", callback_data=f"add_{prod_id}"),
                types.InlineKeyboardButton("🔙 عودة للقسم", callback_data=f"cat_{cat_key}")
            )
            caption = f"🛍️ **{prod['name']}**\n\n📝 **الوصف:**\n{prod['desc']}\n\n💰 **السعر:** {prod['price']}"
            
            if prod["image"].startswith("http"):
                bot.send_photo(user_id, photo=prod["image"], caption=caption, reply_markup=markup, parse_mode="Markdown")
            else:
                bot.send_message(user_id, caption, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("add_"):
        prod_id = data.split("_")[1]
        prod, _ = get_product_by_id(prod_id)
        if prod:
            if user_id not in user_carts: user_carts[user_id] = []
            user_carts[user_id].append(prod)
            bot.answer_callback_query(call.id, f"✅ أضيف {prod['name']} لسلتك!", show_alert=True)

    elif data == "view_cart":
        cart = user_carts.get(user_id, [])
        if not cart:
            bot.answer_callback_query(call.id, "🛒 سلة المشتريات فارغة حالياً ياباشا!", show_alert=True)
            return
            
        cart_text = "🛒 **محتويات سلتك الحالية:**\n\n"
        for idx, item in enumerate(cart, 1):
            cart_text += f"{idx}. {item['name']} - ({item['price']})\n"
            
        cp = user_applied_coupons.get(user_id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تأكيد وشراء الطلب", callback_data="checkout"))
        
        if cp:
            cart_text += f"\n🎟️ **الكوبون النشط:** `{cp['code']}` (خصم {cp['pct']}% 🎉)"
        else:
            markup.add(types.InlineKeyboardButton("🎟️ إضافة كود خصم (كوبون)", callback_data="apply_coupon"))
            
        markup.add(types.InlineKeyboardButton("🗑️ تفريغ السلة", callback_data="clear_cart"))
        markup.add(types.InlineKeyboardButton("🔙 عودة للقائمة الرئيسية", callback_data="main_menu"))
        
        bot.edit_message_text(chat_id=user_id, message_id=message_id, text=cart_text, reply_markup=markup, parse_mode="Markdown")

    elif data == "apply_coupon":
        try: bot.delete_message(user_id, message_id)
        except: pass
        bot.send_message(user_id, "🎟️ اكتب كود الخصم الآن بدقة (مثال: BEAUTY10):")
        user_steps[user_id] = "user_write_coupon"

    elif data == "clear_cart":
        user_carts[user_id] = []
        user_applied_coupons[user_id] = None
        bot.answer_callback_query(call.id, "🗑️ تم إفراغ السلة")
        bot.edit_message_text(chat_id=user_id, message_id=message_id, text="🎛️ الأقسام الرئيسية للمتجر:", reply_markup=get_main_keyboard())

    elif data == "main_menu":
        if call.message.content_type == 'photo':
            try: bot.delete_message(user_id, message_id)
            except: pass
            bot.send_message(user_id, "🎛️ الأقسام الرئيسية للمتجر:", reply_markup=get_main_keyboard())
        else:
            bot.edit_message_text(chat_id=user_id, message_id=message_id, text="🎛️ الأقسام الرئيسية للمتجر:", reply_markup=get_main_keyboard())

    elif data == "checkout":
        try: bot.delete_message(user_id, message_id)
        except: pass
        bot.send_message(user_id, "📝 ننتقل الآن لتثبيت الطلب.\nالرجاء إرسال **الاسم الكامل** للمستلم:")
        user_steps[user_id] = "get_name"
        user_orders[user_id] = {"items": user_carts.get(user_id, [])}

    # ----- أقسام لوحة قيادة الآدمن -----
    elif data == "adm_add" and user_id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        for key, name in CATEGORIES_MAP.items():
            markup.add(types.InlineKeyboardButton(name, callback_data=f"addto_{key}"))
        markup.add(types.InlineKeyboardButton("🔙 عودة للوحة التحكم", callback_data="admin_main"))
        bot.edit_message_text(chat_id=ADMIN_ID, message_id=message_id, text="📁 اختر القسم الذي تريد إضافة المنتج إليه:", reply_markup=markup)

    elif data.startswith("addto_") and user_id == ADMIN_ID:
        cat_target = data.split("_")[1]
        admin_data[ADMIN_ID] = {"category": cat_target}
        try: bot.delete_message(ADMIN_ID, message_id)
        except: pass
        bot.send_message(ADMIN_ID, "✍️ حسناً، أرسل الآن **اسم المنتج** الجديد:")
        user_steps[ADMIN_ID] = "adm_get_name"

    elif data == "adm_del" and user_id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        for key, name in CATEGORIES_MAP.items():
            markup.add(types.InlineKeyboardButton(name, callback_data=f"delcat_{key}"))
        markup.add(types.InlineKeyboardButton("🔙 عودة للوحة التحكم", callback_data="admin_main"))
        bot.edit_message_text(chat_id=ADMIN_ID, message_id=message_id, text="📁 اختر القسم لحذف منتج منه:", reply_markup=markup)

    elif data.startswith("delcat_") and user_id == ADMIN_ID:
        cat_key = data.split("_")[1]
        markup = types.InlineKeyboardMarkup()
        for prod in PRODUCTS.get(cat_key, []):
            markup.add(types.InlineKeyboardButton(f"❌ {prod['name']}", callback_data=f"execute_del_{prod['id']}"))
        markup.add(types.InlineKeyboardButton("🔙 عودة للخلف", callback_data="adm_del"))
        bot.edit_message_text(chat_id=ADMIN_ID, message_id=message_id, text="🗑️ اضغط على المنتج الذي تريد حذفه نهائياً من المتجر:", reply_markup=markup)

    elif data.startswith("execute_del_") and user_id == ADMIN_ID:
        prod_id = data.split("_")[2]
        for cat in PRODUCTS:
            if cat == "coupons": continue
            PRODUCTS[cat] = [p for p in PRODUCTS[cat] if p["id"] != prod_id]
        save_products(PRODUCTS)
        bot.answer_callback_query(call.id, "✅ تم حذف المنتج بنجاح!", show_alert=True)
        bot.edit_message_text(chat_id=ADMIN_ID, message_id=message_id, text="🛠️ تم تحديث البيانات بنجاح في لوحة المالك:", reply_markup=get_admin_keyboard())

    elif data == "adm_price" and user_id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        for key, name in CATEGORIES_MAP.items():
            markup.add(types.InlineKeyboardButton(name, callback_data=f"pricecat_{key}"))
        markup.add(types.InlineKeyboardButton("🔙 عودة للوحة التحكم", callback_data="admin_main"))
        bot.edit_message_text(chat_id=ADMIN_ID, message_id=message_id, text="📁 اختر القسم لتعديل سعر منتج فيه:", reply_markup=markup)

    elif data.startswith("pricecat_") and user_id == ADMIN_ID:
        cat_key = data.split("_")[1]
        markup = types.InlineKeyboardMarkup()
        for prod in PRODUCTS.get(cat_key, []):
            markup.add(types.InlineKeyboardButton(f"💰 {prod['name']} ({prod['price']})", callback_data=f"editprice_{prod['id']}"))
        markup.add(types.InlineKeyboardButton("🔙 عودة للخلف", callback_data="adm_price"))
        bot.edit_message_text(chat_id=ADMIN_ID, message_id=message_id, text="اختر المنتج الذي ترغب بتغيير سعره الحالي:", reply_markup=markup)

    elif data.startswith("editprice_") and user_id == ADMIN_ID:
        prod_id = data.split("_")[1]
        admin_data[ADMIN_ID] = {"edit_price_id": prod_id}
        try: bot.delete_message(ADMIN_ID, message_id)
        except: pass
        bot.send_message(ADMIN_ID, "💰 أرسل السعر الجديد المحدث للبوت الآن (مثال: 50$ أو 250 ليرة):")
        user_steps[ADMIN_ID] = "adm_get_new_price"

    elif data == "adm_coupons" and user_id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("➕ إنشاء كوبون خصم جديد", callback_data="cp_add"),
            types.InlineKeyboardButton("❌ حذف كوبون خصم حالي", callback_data="cp_del"),
            types.InlineKeyboardButton("🔙 عودة للوحة التحكم", callback_data="admin_main")
        )
        bot.edit_message_text(chat_id=ADMIN_ID, message_id=message_id, text="🎟️ **إدارة كوبونات الخصم للمتجر:**\nأنشئ عروضك التسويقية من هنا بكل سهولة:", reply_markup=markup)

    elif data == "cp_add" and user_id == ADMIN_ID:
        try: bot.delete_message(ADMIN_ID, message_id)
        except: pass
        bot.send_message(ADMIN_ID, "✍️ أرسل الرمز أو الكود المراد إنشاؤه (أحرف إنجليزية كبار أو أرقام، مثال: JORY10):")
        user_steps[ADMIN_ID] = "get_cp_name"

    elif data == "cp_del" and user_id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup(row_width=1)
        coupons = PRODUCTS.get("coupons", {})
        if not coupons:
            bot.answer_callback_query(call.id, "⚠️ لا توجد أي كوبونات حالياً بالمتجر!", show_alert=True)
            return
        for name, pct in coupons.items():
            markup.add(types.InlineKeyboardButton(f"❌ الكود: {name} (خصم {pct}%)", callback_data=f"execute_cpdel_{name}"))
        markup.add(types.InlineKeyboardButton("🔙 عودة للخلف", callback_data="adm_coupons"))
        bot.edit_message_text(chat_id=ADMIN_ID, message_id=message_id, text="🗑️ اضغط على الكوبون الذي ترغب بحذفه نهائياً وإيقافه للزبائن:", reply_markup=markup)

    elif data.startswith("execute_cpdel_") and user_id == ADMIN_ID:
        cp_name = data.split("_")[2]
        if "coupons" in PRODUCTS and cp_name in PRODUCTS["coupons"]:
            del PRODUCTS["coupons"][cp_name]
            save_products(PRODUCTS)
        bot.answer_callback_query(call.id, "✅ تم إيقاف وحذف الكوبون فوراً!", show_alert=True)
        bot.edit_message_text(chat_id=ADMIN_ID, message_id=message_id, text="🛠️ لوحة قيادة المالك الذكية:", reply_markup=get_admin_keyboard())

    elif data.startswith("status_") and user_id == ADMIN_ID:
        parts = data.split("_")
        status_key = parts[1]
        client_id = int(parts[2])
        
        client_msg = ""
        admin_badge = ""
        
        if status_key == "shipped":
            client_msg = "🚚 **تحديث لطلبك ياباشا:** تم شحن طلبك بنجاح وهو في طريقه إليك الآن! استعد للاستلام. 🌸✨"
            admin_badge = "🟢 [تم التحديث إلى: تم الشحن 🚚]"
        elif status_key == "delivered":
            client_msg = "✅ **تحديث لطلبك ياباشا:** تم توصيل الطلب إليك بنجاح! شكراً جزيلاً لثقتك بمتجرنا، نأمل أن تنال المنتجات إعجابك. ❤️"
            admin_badge = "🟢 [تم التحديث إلى: تم التوصيل ✅]"
        elif status_key == "canceled":
            client_msg = "❌ **تحديث لطلبك:** نعتذر منك ياباشا، تم إلغاء طلبك الحالي من قبل الإدارة. لمزيد من الاستفسار يرجى مراسلتنا."
            admin_badge = "🔴 [تم التحديث إلى: تم إلغاء الطلب ❌]"
            
        try:
            bot.send_message(client_id, client_msg, parse_mode="Markdown")
        except:
            pass
            
        updated_text = f"{call.message.text}\n\n⚙️ **إجراء المالك الفوري:** {admin_badge}"
        try:
            bot.edit_message_text(chat_id=ADMIN_ID, message_id=message_id, text=updated_text, reply_markup=None)
        except:
            pass
        bot.answer_callback_query(call.id, "✅ تم تحديث حالة الطلب وإرسال إشعار فوري للزبون!")

    elif data == "admin_broadcast" and user_id == ADMIN_ID:
        try: bot.delete_message(ADMIN_ID, message_id)
        except: pass
        bot.send_message(ADMIN_ID, "📢 أرسل نص رسالة الإعلان الجماعي لجميع المشتركين:")
        user_steps[ADMIN_ID] = "get_broadcast_msg"
        
    elif data == "admin_main" and user_id == ADMIN_ID:
        bot.edit_message_text(chat_id=ADMIN_ID, message_id=message_id, text="🛠️ لوحة قيادة المالك الذكية:", reply_markup=get_admin_keyboard())

# ----------------- معالجة المدخلات النصية -----------------
@bot.message_handler(func=lambda message: True)
def handle_text_inputs(message):
    global PRODUCTS
    user_id = message.chat.id
    step = user_steps.get(user_id)

    if step == "user_write_coupon":
        code = message.text.strip().upper()
        PRODUCTS = load_products()
        coupons = PRODUCTS.get("coupons", {})
        
        if code in coupons:
            user_applied_coupons[user_id] = {"code": code, "pct": coupons[code]}
            bot.send_message(user_id, f"🎉 مبروك ياباشا! الكود صحيح وتم تطبيق خصم بمقدار **{coupons[code]}%** بنجاح!")
            user_steps[user_id] = None
            
            cart = user_carts.get(user_id, [])
            cart_text = "🛒 **محتويات سلتك المحدثة:**\n\n"
            for idx, item in enumerate(cart, 1):
                cart_text += f"{idx}. {item['name']} - ({item['price']})\n"
            cart_text += f"\n🎟️ **الكوبون النشط:** `{code}` (خصم {coupons[code]}% 🎉)"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ تأكيد وشراء الطلب", callback_data="checkout"))
            markup.add(types.InlineKeyboardButton("🗑️ تفريغ السلة", callback_data="clear_cart"))
            markup.add(types.InlineKeyboardButton("🔙 عودة للقائمة الرئيسية", callback_data="main_menu"))
            bot.send_message(user_id, cart_text, reply_markup=markup, parse_mode="Markdown")
        else:
            user_steps[user_id] = None
            bot.send_message(user_id, "⚠️ كود الخصم هذا منتهي الصلاحية أو غير صحيح ياباشا.")
            bot.send_message(user_id, "🎛️ القائمة الرئيسية للمتجر:", reply_markup=get_main_keyboard())

    elif step == "get_name":
        user_orders[user_id]["name"] = message.text
        bot.send_message(user_id, "📍 ممتاز، أرسل الآن **العنوان بالتفصيل**:")
        user_steps[user_id] = "get_address"
    elif step == "get_address":
        user_orders[user_id]["address"] = message.text
        bot.send_message(user_id, "📞 ممتاز، أرسل الآن **رقم الهاتف** للتوصيل:")
        user_steps[user_id] = "get_phone"
    elif step == "get_phone":
        user_orders[user_id]["phone"] = message.text
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("💵 الدفع عند الاستلام (COD)", "💳 تحويل إلكتروني")
        bot.send_message(user_id, "💳 اختر طريقة الدفع المفضلة لديك:", reply_markup=markup)
        user_steps[user_id] = "get_payment"
    elif step == "get_payment":
        user_orders[user_id]["payment"] = message.text
        order_data = user_orders[user_id]
        bot.send_message(user_id, "🎉 تم استلام طلبك بنجاح ياباشا! سيتم التواصل معك قريباً لشحن المنتجات.", reply_markup=types.ReplyKeyboardRemove())
        
        items_text = "".join([f"   - {item['name']} ({item['price']})\n" for item in order_data["items"]])
        
        cp = user_applied_coupons.get(user_id)
        coupon_line = ""
        if cp:
            coupon_line = f"🎟️ **كوبون الخصم المستخدم:** {cp['code']} (خصم {cp['pct']}%)\n"
            user_applied_coupons[user_id] = None
            
        admin_invoice = (
            f"🚨 **طلب جديد واصل للمتجر!** 🚨\n\n"
            f"👤 **العميل:** {order_data['name']}\n"
            f"📞 **الهاتف:** {order_data['phone']}\n"
            f"📍 **العنوان:** {order_data['address']}\n"
            f"💳 **الدفع:** {order_data['payment']}\n"
            f"{coupon_line}\n"
            f"📦 **المنتجات المطلوبة:**\n{items_text}"
        )
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🚚 تم الشحن", callback_data=f"status_shipped_{user_id}"),
            types.InlineKeyboardButton("✅ تم التوصيل", callback_data=f"status_delivered_{user_id}")
        )
        markup.add(types.InlineKeyboardButton("❌ إلغاء الطلب", callback_data=f"status_canceled_{user_id}"))
        
        bot.send_message(ADMIN_ID, admin_invoice, reply_markup=markup, parse_mode="Markdown")
        user_carts[user_id] = []
        user_steps[user_id] = None

    elif user_id == ADMIN_ID:
        if step == "adm_get_name":
            admin_data[ADMIN_ID]["name"] = message.text
            bot.send_message(ADMIN_ID, "💰 ممتاز، أرسل الآن **سعر** هذا المنتج:")
            user_steps[ADMIN_ID] = "adm_get_price"
            
        elif step == "adm_get_price":
            admin_data[ADMIN_ID]["price"] = message.text
            bot.send_message(ADMIN_ID, "📝 أرسل الآن **الشرح والوصف** التفصيلي للمنتج:")
            user_steps[ADMIN_ID] = "adm_get_desc"
            
        elif step == "adm_get_desc":
            admin_data[ADMIN_ID]["desc"] = message.text
            bot.send_message(ADMIN_ID, "🖼️ أرسل الآن **رابط الصورة المباشر** للمنتج (إذا لم يتوفر اكتب لا يوجد):")
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
            
            PRODUCTS = load_products()
            PRODUCTS[cat].append(new_product)
            save_products(PRODUCTS)
            
            bot.send_message(ADMIN_ID, f"✅ تم إضافة منتج **({new_product['name']})** بنجاح وتحديث المتجر فوراً للعملاء!", reply_markup=get_admin_keyboard())
            user_steps[ADMIN_ID] = None
            
        elif step == "adm_get_new_price":
            new_p = message.text
            p_id = admin_data[ADMIN_ID]["edit_price_id"]
            
            PRODUCTS = load_products()
            for cat in PRODUCTS:
                if cat == "coupons": continue
                for p in PRODUCTS[cat]:
                    if p["id"] == p_id:
                        p["price"] = new_p
                        break
            save_products(PRODUCTS)
            bot.send_message(ADMIN_ID, "✅ تم تحديث سعر المنتج بنجاح وتعديله في المتجر!", reply_markup=get_admin_keyboard())
            user_steps[ADMIN_ID] = None

        elif step == "get_cp_name":
            admin_data[ADMIN_ID]["cp_name"] = message.text.strip().upper()
            bot.send_message(ADMIN_ID, f"💰 ممتاز، حدد **نسبة الخصم** المئوية لكوبون `{admin_data[ADMIN_ID]['cp_name']}` (أرقام فقط بدون علامة %، مثال: 15):")
            user_steps[ADMIN_ID] = "get_cp_pct"
            
        elif step == "get_cp_pct":
            try:
                pct = int(message.text.strip())
                cp_name = admin_data[ADMIN_ID]["cp_name"]
                PRODUCTS = load_products()
                PRODUCTS["coupons"][cp_name] = pct
                save_products(PRODUCTS)
                bot.send_message(ADMIN_ID, f"✅ تم إنشاء وتفعيل الكوبون `{cp_name}` بخصم **{pct}%** بنجاح للزبائن!", reply_markup=get_admin_keyboard())
                user_steps[ADMIN_ID] = None
            except ValueError:
                bot.send_message(ADMIN_ID, "⚠️ خطأ! الرجاء إدخال أرقام صحيحة فقط لنسبة الخصم (مثال: 20):")

        elif step == "get_broadcast_msg":
            bot.send_message(ADMIN_ID, "⏳ جاري بدء الإرسال الجماعي لجميع الزبائن...")
            success = 0
            for u_id in list(users_list):
                try:
                    bot.send_message(u_id, f"📢 **إعلان جديد من المتجر:**\n\n{message.text}", parse_mode="Markdown")
                    success += 1
                except: pass
            bot.send_message(ADMIN_ID, f"✅ تمت الإذاعة بنجاح لـ {success} مستخدم.", reply_markup=get_admin_keyboard())
            user_steps[ADMIN_ID] = None

print("⚡ لوحة التحكم المتكاملة والمحدثة بالتوكن والآيدي الجديدين تعمل الآن بنجاح ياباشا...")
bot.infinity_polling()
