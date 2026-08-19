import logging
import requests
import subprocess
import json
import re
import time
from datetime import datetime
from telegram import Update, ReactionTypeEmoji
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- YOUR SECRETS AND CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "8846805014:AAF2aeOCZ2hwHrrMTyP9CaTYctQpcjdH9Ew"
HF_API_TOKEN = "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"

# --- API AND MODEL DEFINITIONS ---
CHAT_API_URL = "https://router.huggingface.co/v1/chat/completions"
CHAT_MODEL = "deepseek-ai/DeepSeek-V3.2-Exp"

# ✅ NEW RELIABLE IMAGE RECOGNITION MODEL
VISION_API_URL = "https://api-inference.huggingface.co/models/google/vit-base-patch16-224"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


# --- AI QUERY FUNCTIONS WITH RETRY LOGIC ---

def detect_language(text: str) -> str:
    """Detect if text is Bengali, Hindi, or English"""
    bengali_chars = ['া', 'ি', 'ী', 'ু', 'ূ', 'ৃ', 'ে', 'ৈ', 'ো', 'ৌ', 'ং', 'ঃ', 'ঁ']
    hindi_chars = ['ा', 'ि', 'ी', 'ु', 'ू', 'े', 'ै', 'ो', 'ौ', 'ं', 'ः']
    
    bengali_count = sum(1 for char in text if char in bengali_chars)
    hindi_count = sum(1 for char in text if char in hindi_chars)
    
    if bengali_count > hindi_count:
        return "bn"  # Bengali
    elif hindi_count > 0:
        return "hi"  # Hindi
    else:
        return "en"  # English

def get_system_prompt(lang: str) -> str:
    """Get system prompt based on language"""
    if lang == "bn":
        return 'You are JARVIS. Always start your response with a simple smiling emoji (like 😊), followed by a space. Always respond in Bengali using feminine grammar. Your answers must be concise (1-2 sentences).'
    elif lang == "hi":
        return 'You are JARVIS. Always start your response with a simple smiling emoji (like 😊), followed by a space. Always respond in Hindi using feminine grammar. Your answers must be concise (1-2 sentences).'
    else:
        return 'You are JARVIS. Always start your response with a simple smiling emoji (like 😊), followed by a space. Always respond in English. Your answers must be concise (1-2 sentences).'

def query_jarvis_ai(prompt: str) -> str:
    lang = detect_language(prompt)
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {
        'model': CHAT_MODEL,
        'messages': [
            {'role': 'system', 'content': get_system_prompt(lang)},
            {'role': 'user', 'content': prompt}
        ]
    }
    for attempt in range(3):
        try:
            response = requests.post(CHAT_API_URL, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            ai_message = result.get('choices', [{}])[0].get('message', {}).get('content')
            
            if ai_message:
                # Ensure Bengali response if Bengali detected
                if lang == "bn" and not any(c in ai_message for c in ['া', 'ি', 'ী', 'ু', 'ূ', 'ে', 'ৈ', 'ো', 'ৌ']):
                    ai_message = "😊 ক্ষমা করবেন, আমি বাংলায় উত্তর দিতে পারছি না। দয়া করে আবার চেষ্টা করুন।"
                return ai_message.strip()
            else:
                return "😊 ক্ষমা করবেন, আমি কোন উত্তর পাইনি।" if lang == "bn" else "😊 माफ़ कीजिये, मुझे कोई जवाब नहीं मिला।" if lang == "hi" else "😊 Sorry, I couldn't find an answer."
        except requests.exceptions.RequestException as e:
            logger.warning(f"JARVIS AI network error (Attempt {attempt + 1}): {e}")
            if attempt < 2:
                time.sleep(3)
            else:
                logger.error("JARVIS AI failed after 3 attempts.")
                if lang == "bn":
                    return "😊 ক্ষমা করবেন, AI ব্রেইনের সাথে সংযোগ করতে নেটওয়ার্ক সমস্যা হচ্ছে।"
                elif lang == "hi":
                    return "😊 माफ़ कीजिये, AI ब्रेन से कनेक्ट करते समय नेटवर्क में कोई समस्या हुई।"
                else:
                    return "😊 Sorry, there was a network issue connecting to the AI brain."
    return "😊 ক্ষমা করবেন, একটি অজানা ত্রুটি হয়েছে।" if lang == "bn" else "😊 माफ़ कीजिये, एक अज्ञात त्रुटि हुई।" if lang == "hi" else "😊 Sorry, an unknown error occurred."


def query_vision_model(image_bytes: bytes, caption: str) -> str:
    """Uses a stable image recognition model (ViT Base) with retries."""
    lang = detect_language(caption)
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

    for attempt in range(3):
        try:
            response = requests.post(VISION_API_URL, headers=headers, data=image_bytes, timeout=90)
            response.raise_for_status()
            result = response.json()

            # ViT returns label prediction
            if isinstance(result, list) and len(result) > 0 and 'label' in result[0]:
                description = result[0]['label']
            else:
                if lang == "bn":
                    description = "কোন বস্তু স্পষ্টভাবে চিহ্নিত করা যায়নি।"
                elif lang == "hi":
                    description = "कोई वस्तु स्पष्ट रूप से पहचान में नहीं आई।"
                else:
                    description = "No object could be clearly identified."

            jarvis_prompt = f"A user sent an image with the caption '{caption}'. My vision analysis says it contains: '{description}'. Please respond to the user based on this."
            return query_jarvis_ai(jarvis_prompt)
        except requests.exceptions.RequestException as e:
            logger.warning(f"Vision AI network error (Attempt {attempt + 1}): {e}")
            if attempt < 2:
                time.sleep(5)
            else:
                logger.error("Vision AI failed after 3 attempts.")
                if lang == "bn":
                    return "😊 ছবি প্রক্রিয়াকরণে নেটওয়ার্ক সমস্যা হয়েছে।"
                elif lang == "hi":
                    return "😊 छवि को प्रोसेस करते समय नेटवर्क में कोई समस्या हुई।"
                else:
                    return "😊 There was a network issue processing the image."
    if lang == "bn":
        return "😊 ছবি প্রক্রিয়াকরণে একটি অজানা ত্রুটি হয়েছে।"
    elif lang == "hi":
        return "😊 छवि को प्रोसेस करते समय कोई अज्ञात त्रुटि हुई।"
    else:
        return "😊 An unknown error occurred while processing the image."


# --- LOCAL DEVICE COMMANDS ---

def handle_local_commands(text: str) -> str | None:
    text_lower = text.lower().strip()
    lang = detect_language(text)
    
    # Time command - বাংলা/हिंदी/English support
    if any(keyword in text_lower for keyword in ["time", "samay", "baje", "টাইম", "সময়", "टाइम"]):
        current_time = datetime.now().strftime("%I:%M %p")
        if lang == "bn":
            return f"😊 স্যার, এখন {current_time} বাজে।"
        elif lang == "hi":
            return f"😊 सर, अभी {current_time} हुए हैं।"
        else:
            return f"😊 Sir, it's {current_time} now."
    
    # Battery command - বাংলা/हिंदी/English support
    if any(keyword in text_lower for keyword in ["battery", "চার্জ", "बैटरी", "charge"]):
        try:
            result = subprocess.run(['termux-battery-status'], capture_output=True, text=True, check=True)
            battery_data = json.loads(result.stdout)
            percentage = battery_data.get('percentage', 'N/A')
            if lang == "bn":
                return f"😊 স্যার, ব্যাটারি {percentage}% এ আছে।"
            elif lang == "hi":
                return f"😊 सर, बैटरी {percentage}% पर है।"
            else:
                return f"😊 Sir, battery is at {percentage}%."
        except Exception:
            if lang == "bn":
                return "😊 আমি ব্যাটারির তথ্য নিতে পারছি না। দয়া করে নিশ্চিত করুন Termux:API ইনস্টল করা আছে।"
            elif lang == "hi":
                return "😊 मैं बैटरी की जानकारी नहीं ले पा रही हूँ। कृपया सुनिश्चित करें कि Termux:API स्थापित है।"
            else:
                return "😊 I couldn't get battery information. Please make sure Termux:API is installed."
    
    # Open URL command - বাংলা/हिंदी/English support
    match = re.search(r"(open|kholo|খোলো|खोलें|খোলেন)\s+([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(\.[a-zA-Z]{2,})?)", text)
    if match:
        url = match.group(2)
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        if lang == "bn":
            return f"😊 ঠিক আছে স্যার, এখানে [{match.group(2)}]({url}) এর লিঙ্ক।"
        elif lang == "hi":
            return f"😊 ठीक है सर, यह रहा [{match.group(2)}]({url}) का लिंक।"
        else:
            return f"😊 Okay sir, here's the link for [{match.group(2)}]({url})."
    
    return None


# --- TELEGRAM HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        f"নমস্কার {user.mention_html()}! আমি JARVIS। আমি আপনার ডিভাইস কমান্ড চালাতে পারি এবং প্রশ্নের উত্তর দিতে পারি বাংলা, হিন্দি বা ইংরেজিতে।\n\n"
        f"Hello {user.mention_html()}! I'm JARVIS. I can run device commands and answer questions in Bengali, Hindi, or English.\n\n"
        f"नमस्ते {user.mention_html()}! मैं JARVIS हूँ। मैं डिवाइस कमांड चला सकती हूँ और सवालों के जवाब हिंदी, बांग्ला या अंग्रेज़ी में दे सकती हूँ।"
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text
    lang = detect_language(user_text)
    
    # ❤️ React to message based on tone
    reaction = ReactionTypeEmoji(emoji="😊")
    if any(word in user_text.lower() for word in ["love", "thanks", "ধন্যবাদ", "धन्यवाद", "❤️", "😍"]):
        reaction = ReactionTypeEmoji(emoji="❤️")
    try:
        await context.bot.set_message_reaction(
            chat_id=update.message.chat_id,
            message_id=update.message.message_id,
            reaction=[reaction]
        )
    except Exception as e:
        logger.warning(f"Reaction failed: {e}")

    local_response = handle_local_commands(user_text)
    if local_response:
        await update.message.reply_text(local_response, parse_mode=ParseMode.MARKDOWN)
    else:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        ai_response = query_jarvis_ai(user_text)
        await update.message.reply_text(ai_response)

async def handle_image_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    try:
        photo_file = await update.message.photo[-1].get_file()
        image_bytes = await photo_file.download_as_bytearray()
        user_caption = update.message.caption or "What's in this picture?"
        
        # Detect language from caption
        lang = detect_language(user_caption)
        if lang == "bn":
            await update.message.reply_text("😊 ছবি দেখছি...")
        elif lang == "hi":
            await update.message.reply_text("😊 तस्वीर देख रही हूँ...")
        else:
            await update.message.reply_text("😊 Looking at the picture...")
        
        ai_response = query_vision_model(bytes(image_bytes), user_caption)
        await update.message.reply_text(ai_response)
    except Exception as e:
        logger.error(f"Image handling error: {e}")
        lang = detect_language(update.message.caption or "en")
        if lang == "bn":
            await update.message.reply_text("😊 ছবি প্রক্রিয়াকরণে একটি অপ্রত্যাশিত ত্রুটি হয়েছে।")
        elif lang == "hi":
            await update.message.reply_text("😊 तस्वीर को प्रोसेस करते समय एक अप्रत्याशित त्रुटि हुई।")
        else:
            await update.message.reply_text("😊 An unexpected error occurred while processing the image.")


def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image_message))
    print("JARVIS AI Bot (Bengali/Hindi/English Support) is running... Press Ctrl-C to stop.")
    application.run_polling()


if __name__ == "__main__":
    main()