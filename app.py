import hashlib
import io
import random
import sqlite3
from datetime import datetime

import requests
from gtts import gTTS
import speech_recognition as sr
import streamlit as st
from streamlit_lottie import st_lottie

# --- 0. ตั้งค่าหน้าเว็บหลัก ---
st.set_page_config(
    page_title="Chinese Practice 🏮 🐼 🐉",
    page_icon="🏮",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --- ฟังก์ชันโหลด Lottie Animation อย่างปลอดภัย ---
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


# --- 1. ตกแต่ง CSS ขั้นสุด (Chinese Oriental Luxury Theme with Motion Effects) ---
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;600;700&family=Ma+Shan+Zheng&display=swap');

    html, body, [class*="css"] {
        font-family: 'Kanit', sans-serif;
    }

    /* พื้นหลังหลักธีมมังกรทองและสีแดงมงคล */
    .stApp {
        background: radial-gradient(circle, #8B0000 0%, #4A0000 60%, #1A0000 100%);
        color: #FFF8E7;
    }

    /* ตกแต่ง Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #2D0000 0%, #100000 100%) !important;
        border-right: 2px solid #FFD700;
    }

    /* ตกแต่งการ์ดเข้าสู่ระบบ (Login Card) */
    .login-box {
        background: rgba(30, 0, 0, 0.88);
        border: 3px solid #FFD700;
        border-radius: 30px;
        padding: 30px;
        box-shadow: 0 0 40px rgba(255, 215, 0, 0.7), inset 0 0 20px rgba(255, 215, 0, 0.4);
        backdrop-filter: blur(12px);
        text-align: center;
        margin-top: 10px;
        position: relative;
        animation: pulse-glow 3s infinite alternate;
    }

    @keyframes pulse-glow {
        0% { box-shadow: 0 0 25px rgba(255, 215, 0, 0.5), inset 0 0 10px rgba(255, 215, 0, 0.2); }
        100% { box-shadow: 0 0 50px rgba(255, 215, 0, 0.9), inset 0 0 30px rgba(255, 215, 0, 0.6); }
    }

    /* หัวข้อภาษาจีนตัวใหญ่เรืองแสง */
    .chinese-header {
        font-family: 'Ma Shan Zheng', cursive;
        font-size: 4rem !important;
        color: #FFD700 !important;
        text-shadow: 0 0 10px #FF4500, 0 0 20px #FFD700, 0 0 30px #FF0000;
        margin-bottom: 0px;
        letter-spacing: 5px;
    }

    .sub-header {
        color: #FFECB3;
        font-size: 1.25rem;
        letter-spacing: 1px;
    }

    /* ตกแต่งปุ่มกด (Buttons) เป็นสีทองอร่ามเรืองแสง */
    .stButton>button {
        background: linear-gradient(45deg, #FFD700 0%, #FFA500 50%, #FF8C00 100%) !important;
        color: #4A0000 !important;
        font-weight: bold !important;
        font-size: 1.15rem !important;
        border-radius: 50px !important;
        border: 2px solid #FFF8E7 !important;
        box-shadow: 0 4px 20px rgba(255, 215, 0, 0.5) !important;
        transition: all 0.3s ease-in-out !important;
    }

    .stButton>button:hover {
        transform: scale(1.06) !important;
        box-shadow: 0 6px 30px rgba(255, 215, 0, 0.9) !important;
        color: #000000 !important;
    }

    /* ตกแต่ง Tab หน้าจอ */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: rgba(0, 0, 0, 0.4);
        padding: 10px;
        border-radius: 20px;
        border: 1px solid #FFD700;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: rgba(139, 0, 0, 0.6);
        border-radius: 12px;
        color: #FFD700;
        font-weight: bold;
        border: 1px solid #FF8C00;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #FFD700 0%, #FF8C00 100%) !important;
        color: #4A0000 !important;
        border: 2px solid #FFFFFF !important;
    }

    /* โคมไฟขยับได้ */
    .floating-lantern {
        font-size: 2.8rem;
        display: inline-block;
        animation: float 2.5s ease-in-out infinite alternate;
    }

    @keyframes float {
        0% { transform: translateY(0px) rotate(-8deg); }
        100% { transform: translateY(-15px) rotate(8deg); }
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)


# --- 2. จัดการฐานข้อมูล SQLite ---
conn = sqlite3.connect("chinese_ai.db", check_same_thread=False)
cursor = conn.cursor()

# ตารางคำศัพท์
cursor.execute("""
    CREATE TABLE IF NOT EXISTS vocab (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level TEXT, chinese TEXT, pinyin TEXT, thai_read TEXT, meaning TEXT
    )
""")

# อัปเดตโครงสร้างตารางเก่าอัตโนมัติหากไม่มีคอลัมน์ thai_read
try:
    cursor.execute("ALTER TABLE vocab ADD COLUMN thai_read TEXT")
    conn.commit()
except sqlite3.OperationalError:
    pass

# ตารางผู้ใช้ (Users)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
""")

# ตารางเก็บประวัติคะแนน (Scores)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        level TEXT,
        score INTEGER,
        total INTEGER,
        created_at TEXT
    )
""")

# ใส่ข้อมูลคำศัพท์เริ่มต้น (ถ้ายังไม่มีข้อมูลในระบบ)
cursor.execute("SELECT COUNT(*) FROM vocab")
if cursor.fetchone()[0] == 0:
    data = [
        # ================= Level 1 (เริ่มต้น - 20 คำ) =================
        ("Level 1 (เริ่มต้น)", "你好", "nǐ hǎo", "หนี ห่าว", "สวัสดี"),
        ("Level 1 (เริ่มต้น)", "谢谢", "xiè xie", "เซี่ย เซี่ย", "ขอบคุณ"),
        ("Level 1 (เริ่มต้น)", "再见", "zài jiàn", "ไจ้ เจี้ยน", "ลาก่อน"),
        ("Level 1 (เริ่มต้น)", "对不起", "duì bu qǐ", "ตุ้ย บู้ ฉี่", "ขอโทษ"),
        ("Level 1 (เริ่มต้น)", "没关系", "méi guān xi", "เหมย กวาน ซิ", "ไม่เป็นไร"),
        ("Level 1 (เริ่มต้น)", "苹果", "píng guǒ", "ผิง กั่ว", "แอปเปิ้ล"),
        ("Level 1 (เริ่มต้น)", "老师", "lǎo shī", "เหล่า ซือ", "คุณครู"),
        ("Level 1 (เริ่มต้น)", "学生", "xué sheng", "เสวีย เซิง", "นักเรียน"),
        ("Level 1 (เริ่มต้น)", "猫", "māo", "เมา", "แมว"),
        ("Level 1 (เริ่มต้น)", "狗", "gǒu", "โก่ว", "สุนัข"),
        ("Level 1 (เริ่มต้น)", "爸爸", "bà ba", "ป้า ปา", "พ่อ"),
        ("Level 1 (เริ่มต้น)", "妈妈", "mā ma", "มา มา", "แม่"),
        ("Level 1 (เริ่มต้น)", "吃", "chī", "ชือ", "กิน"),
        ("Level 1 (เริ่มต้น)", "喝", "hē", "เฮอ", "ดื่ม"),
        ("Level 1 (เริ่มต้น)", "水", "shuǐ", "สุ่ย", "น้ำ"),
        ("Level 1 (เริ่มต้น)", "米饭", "mǐ fàn", "หมี่ ฟ่าน", "ข้าวสวย"),
        ("Level 1 (เริ่มต้น)", "学校", "xué xiào", "เสวีย เซี่ยว", "โรงเรียน"),
        ("Level 1 (เริ่มต้น)", "朋友", "péng you", "เพิง โหย่ว", "เพื่อน"),
        ("Level 1 (เริ่มต้น)", "书", "shū", "ซู", "หนังสือ"),
        ("Level 1 (เริ่มต้น)", "高兴", "gāo xìng", "เกา ซิ่ง", "ดีใจ / มีความสุข"),

        # ================= Level 2 (ปานกลาง - 20 คำ) =================
        ("Level 2 (ปานกลาง)", "我想吃中国菜", "wǒ xiǎng chī zhōng guó cài", "หวอ เสี่ยง ชือ จง กั๋ว ไฉ่", "ฉันอยากกินอาหารจีน"),
        ("Level 2 (ปานกลาง)", "这个多少钱？", "zhè ge duō shǎo qián？", "เจ้อ เกอ ตัว เส่า เฉียน？", "อันนี้ราคาเท่าไหร่?"),
        ("Level 2 (ปานกลาง)", "很高兴认识你", "hěn gāo xìng rèn shi nǐ", "เหิ่น เกา ซิ่ง เริ่น ซิ หนี่", "ยินดีที่ได้รู้จักคุณ"),
        ("Level 2 (ปานกลาง)", "洗手间在哪里？", "xǐ shǒu jiān zài nǎ lǐ？", "ซี เส่ว เจียน ไจ้ หนา หลี่？", "ห้องน้ำอยู่ที่ไหน?"),
        ("Level 2 (ปานกลาง)", "你可以帮我吗？", "nǐ kě yǐ bāng wǒ ma？", "หนี่ เข่อ อี่ บัง หวอ ม่า？", "คุณช่วยฉันหน่อยได้ไหม?"),
        ("Level 2 (ปานกลาง)", "今天天气很好", "jīn tiān tiān qì hěn hǎo", "จิน เทียน เทียน ฉี่ เหิ่น ห่าว", "วันนี้อากาศดีมาก"),
        ("Level 2 (ปานกลาง)", "我听不懂", "wǒ tīng bù dǒng", "หวอ ทิง บู้ ต๋อง", "ฉันฟังไม่เข้าใจ"),
        ("Level 2 (ปานกลาง)", "请说慢一点", "qǐng shuō màn yī diǎn", "ฉิ่ง ซัว ม่าน อี้ เตี่ยน", "กรุณาพูดช้าหน่อย"),
        ("Level 2 (ปานกลาง)", "你几点回家？", "nǐ jǐ diǎn huí jiā？", "หนี่ จี๋ เตี่ยน หุย เจีย？", "คุณกลับบ้านกี่โมง?"),
        ("Level 2 (ปานกลาง)", "我喜欢学中文", "wǒ xǐ huan xué zhōng wén", "หวอ ซี ฮวน เสวีย จง เวิน", "ฉันชอบเรียนภาษาจีน"),
        ("Level 2 (ปานกลาง)", "明天你有空吗？", "míng tiān nǐ yǒu kòng ma？", "หมิง เทียน หนี่ โหย่ว ข้ง ม่า？", "พรุ่งนี้คุณว่างไหม?"),
        ("Level 2 (ปานกลาง)", "太贵了，便宜一点吧", "tài guì le, pián yi yī diǎn ba", "ไท่ กู้ย เลอ, เพียน ยิ อี้ เตี่ยน ปา", "แพงเกินไป ลดหน่อยได้ไหม"),
        ("Level 2 (ปานกลาง)", "我们需要买什么？", "wǒ men xū yào mǎi shén me？", "หว่อ เมิน ซู เย่า หมัย เสิน เมอะ？", "พวกเราต้องซื้ออะไรบ้าง?"),
        ("Level 2 (ปานกลาง)", "请问，公共汽车站在哪里？", "qǐng wèn, gōng gòng qì chē zhàn zài nǎ lǐ？", "ฉิ่ง เว่น, กง ก้ง ฉี้ เชอ จ้าน ไจ้ หนา หลี่？", "ขอถามหน่อย สถานีรถเมล์อยู่ไหน?"),
        ("Level 2 (ปานกลาง)", "我不舒服，想去医院", "wǒ bù shū fu, xiǎng qù yī yuàn", "หวอ บู้ ซู ฟู, เสี่ยง ฉวี้ อี เยี่ยน", "ฉันไม่สบาย อยากไปโรงพยาบาล"),
        ("Level 2 (ปานกลาง)", "祝你生日快乐", "zhù nǐ shēng rì kuài lè", "จู้ หนี่ เซิง ยี่ คว้าย เล่อ", "สุขสันต์วันเกิด"),
        ("Level 2 (ปานกลาง)", "我们可以刷卡吗？", "wǒ men kě yǐ shuā kǎ ma？", "หว่อ เมิน เข่อ อี่ ซัว ข่า ม่า？", "พวกเรารูดบัตรได้ไหม?"),
        ("Level 2 (ปานกลาง)", "外面的雪下得很大", "wài mian de xuě xià de hěn dà", "เว่ย เมียน เตอะ เสวี่ย เซี่ย เตอะ เหิ่น ต้า", "ข้างนอกหิมะตกหนักมาก"),
        ("Level 2 (ปานกลาง)", "虽然很难，但我不会放弃", "suī rán hěn nán, dàn wǒ bù huì fàng qì", "ซุย รัน เหิ่น นาน, ต้าน หวอ บู้ ห้วย ฟ่าง ฉี้", "แม้ว่ายาก แต่ฉันจะไม่ยอมแพ้"),
        ("Level 2 (ปานกลาง)", "这份工作很有挑战性", "zhè fèn gōng zuò hěn yǒu tiǎo zhàn xìng", "เจ้อ เฟิ่น กง ซั่ว เหิ่น โหย่ว เถี่ยว จ้าน ซิ่ง", "งานนี้ท้าทายมาก"),

        # ================= Level 3 (ขั้นสูง - 20 คำ) =================
        ("Level 3 (ขั้นสูง)", "入乡随俗", "rù xiāng suí sú", "ยู่ เซียง ซุย ซู", "เข้าเมืองตาลิ่วต้องลิ่วตาตาม"),
        ("Level 3 (ขั้นสูง)", "失败是成功之母", "shī bài shì chéng gōng zhī mǔ", "ซือ ไบ่ ซื่อ เฉิง กง จือ หมู่", "ความล้มเหลวคือมารดาแห่งความสำเร็จ"),
        ("Level 3 (ขั้นสูง)", "千里之行，始于足下", "qiān lǐ zhī xíng, shǐ yú zú xià", "เฉียน หลี่ จือ ขิง, สื่อ ยวี่ ซู เซี่ย", "การเดินทางพันลี้เริ่มต้นที่ก้าวแรก"),
        ("Level 3 (ขั้นสูง)", "熟能生巧", "shú néng shēng qiǎo", "ซู เหนิง เซิง เฉี่ยว", "ฝึกฝนจนชำนาญจะเกิดความเชี่ยวชาญ"),
        ("Level 3 (ขั้นสูง)", "欲速则不达", "yù sù zé bù dá", "ยวี่ ซู่ เจ๋อ บู้ ด๋า", "รีบร้อนเกินไปมักไม่สำเร็จ"),
        ("Level 3 (ขั้นสูง)", "知识就是力量", "zhī shi jiù shì lì liàng", "จือ ซิ จิ้ว ซื่อ ลี่ เลี่ยง", "ความรู้คือพลัง"),
        ("Level 3 (ขั้นสูง)", "活到老，学到老", "huó dào lǎo, xué dào lǎo", "หัว เต้า เหล่า, เสวีย เต้า เหล่า", "เรียนรู้ได้ตลอดชีวิตจนแก่"),
        ("Level 3 (ขั้นสูง)", "温故而知新", "wēn gù ér zhī xīn", "เวิน กู้ เอ๋อร์ จือ ซิน", "ทบทวนสิ่งเก่าทำให้รู้สิ่งใหม่"),
        ("Level 3 (ขั้นสูง)", "事实胜于雄辩", "shì shí shèng yú xióng biàn", "ซื่อ ซี เซิ่ง ยวี่ ซง เบี้ยน", "ข้อเท็จจริงมีน้ำหนักมากกว่าคำพูด"),
        ("Level 3 (ขั้นสูง)", "百闻不如一见", "bǎi wén bù rú yī jiàn", "ไป๋ เวิน บู้ หรู อี้ เจี้ยน", "สิบปากว่าไม่เท่าตาเห็น"),
        ("Level 3 (ขั้นสูง)", "一分耕耘，一分收获", "yī fēn gēng yún, yī fēn shōu huò", "อี้ เฟิน เกิง ยว๋น, อี้ เฟิน โชว ฮั่ว", "ความพยายามอยู่ที่ไหน ความสำเร็จอยู่ที่นั่น"),
        ("Level 3 (ขั้นสูง)", "精益求精", "jīng yì qiú jīng", "จิง อี้ ฉิว จิง", "พิถีพิถันเพื่อความสมบูรณ์แบบยิ่งขึ้น"),
        ("Level 3 (ขั้นสูง)", "饮水思源", "yǐn shuǐ sī yuán", "หยิน สุ่ย ซือ หยวน", "กินน้ำให้คิดถึงคนขุดบ่อ (ไม่ลืมบุญคุณ)"),
        ("Level 3 (ขั้นสูง)", "持之以恒", "chí zhī yǐ héng", "ฉือ จือ อี่ เฮิง", "มีความพยายามสม่ำเสมอไม่ท้อถอย"),
        ("Level 3 (ขั้นสูง)", "自强不息", "zì qiáng bù xī", "ซื่อ เฉียง บู้ ซี", "มุ่งมั่นพัฒนาตนเองอย่างไม่หยุดยั้ง"),
        ("Level 3 (ขั้นสูง)", "脚踏实地", "jiǎo tà shí dì", "เจี่ยว ท่า ซี ตี้", "ทำตัวติดดิน/ทำงานด้วยความจริงจังมั่งคง"),
        ("Level 3 (ขั้นสูง)", "开卷有益", "kāi juàn yǒu yì", "ไค จ้วน โหย่ว อี้", "การอ่านหนังสือย่อมได้ประโยชน์เสมอ"),
        ("Level 3 (ขั้นสูง)", "良药苦口", "liáng yào kǔ kǒu", "เหลียง เย่า ขู่ โข่ว", "ยาดีมักมีรสขม (คำเตือนสติมักฟังยาก)"),
        ("Level 3 (ขั้นสูง)", "同舟共济", "tóng zhōu gòng jì", "ถง โจว ก้ง จี้", "ลงเรือลำเดียวกันร่วมมือฟันฝ่าอุปสรรค"),
        ("Level 3 (ขั้นสูง)", "众志成城", "zhòng zhì chéng chéng", "จ้ง จี้ เฉิง เฉิง", "สามัคคีคือพลังรวมใจเป็นกำแพงเหล็ก")
    ]
    cursor.executemany("INSERT INTO vocab (level, chinese, pinyin, thai_read, meaning) VALUES (?,?,?,?,?)", data)
    conn.commit()


# --- 3. ฟังก์ชันช่วยจัดการผู้ใช้และการเข้ารหัส ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

def add_userdata(username, password):
    cursor.execute("INSERT INTO users (username, password) VALUES (?,?)", (username, make_hashes(password)))
    conn.commit()

def login_user(username, password):
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, make_hashes(password)))
    data = cursor.fetchall()
    return data

def save_score(username, level, score, total):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO scores (username, level, score, total, created_at) VALUES (?,?,?,?,?)",
                   (username, level, score, total, now))
    conn.commit()


# --- 4. ฟังก์ชัน AI อ่านออกเสียงและประเมิน ---
def speak_chinese(text):
    tts = gTTS(text=text, lang="zh-CN")
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    return fp

def evaluate_speech(audio_bytes, expected_text):
    recognizer = sr.Recognizer()
    try:
        audio_file = sr.AudioFile(io.BytesIO(audio_bytes))
        with audio_file as source:
            audio_data = recognizer.record(source)

        recognized_text = recognizer.recognize_google(audio_data, language="zh-CN")

        clean_expected = expected_text.replace("？", "").replace("！", "").replace("，", "").replace("、", "").strip()
        correct_count = sum(1 for char in recognized_text if char in clean_expected)
        total_count = max(len(clean_expected), 1)
        accuracy = min(100, int((correct_count / total_count) * 100))

        return recognized_text, accuracy
    except sr.UnknownValueError:
        return None, 0
    except Exception:
        return None, -1


# --- 5. หน้าเข้าสู่ระบบเว่อร์อลังการ (3D Animated Dragon Login Page) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.snow()  # เอฟเฟกต์ละอองวิ้งๆ

    col1, col2, col3 = st.columns([1, 2.3, 1])

    with col2:
        # 🐉 ส่วนแสดงแอนิเมชันมังกรจีนเคลื่อนไหว 3D (Lottie Animation)
        dragon_json = load_lottieurl("https://assets10.lottiefiles.com/packages/lf20_5tl1xxee.json")
        if dragon_json:
            st_lottie(dragon_json, height=220, key="chinese_dragon_anim")
        else:
            st.markdown("<h1 style='text-align: center; font-size: 5rem;'>🐉</h1>", unsafe_allow_html=True)

        st.markdown(
            """
            <div class="login-box">
                <div class="floating-lantern">🏮</div> &nbsp;&nbsp;&nbsp; 
                <span class="chinese-header">學 中 文</span> 
                &nbsp;&nbsp;&nbsp; <div class="floating-lantern">🏮</div>
                <p class="sub-header">✨ แพลตฟอร์มฝึกภาษาจีนสุดอลังการด้วย AI ✨</p>
                <hr style="border-top: 1px solid #FFD700; margin: 15px 0;">
            """,
            unsafe_allow_html=True,
        )

        auth_mode = st.radio(
            "⛩️ เลือกรายการเข้าสู่ระบบ:",
            ["🧧 เข้าสู่ระบบ (Login)", "📜 สมัครสมาชิกใหม่ (Register)"],
            horizontal=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        if auth_mode == "🧧 เข้าสู่ระบบ (Login)":
            user = st.text_input("👤 ชื่อผู้ใช้งาน (Username):")
            passwd = st.text_input("🔑 รหัสผ่าน (Password):", type="password")
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("🐉 ก้าวสู่แดนมังกร (Login)", use_container_width=True):
                result = login_user(user, passwd)
                if result:
                    st.session_state.logged_in = True
                    st.session_state.username = user
                    st.balloons()
                    st.success(f"🎉 ยินดีต้อนรับจอมยุทธ์ {user} เข้าสู่สำนัก!")
                    st.rerun()
                else:
                    st.error("❌ ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง")

        else:
            new_user = st.text_input("✍️ ตั้งชื่อผู้ใช้งาน (Username):")
            new_passwd = st.text_input("🔐 ตั้งรหัสผ่าน (Password):", type="password")
            confirm_passwd = st.text_input("🔒 ยืนยันรหัสผ่าน:", type="password")
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("📜 ลงนามสมัครสมาชิก (Register)", use_container_width=True):
                if new_user and new_passwd:
                    if new_passwd != confirm_passwd:
                        st.error("⚠️ รหัสผ่านยืนยันไม่ตรงกัน")
                    else:
                        cursor.execute("SELECT * FROM users WHERE username = ?", (new_user,))
                        if cursor.fetchone():
                            st.warning("⚠️ ชื่อผู้ใช้นี้มีจอมยุทธ์ท่านอื่นใช้แล้ว")
                        else:
                            add_userdata(new_user, new_passwd)
                            st.success("🎉 ลงทะเบียนสำเร็จ! กรุณาสลับไปที่หน้าเข้าสู่ระบบ")
                            st.balloons()
                else:
                    st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน")

        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


# --- 6. เมนูหลักเมื่อ Login เข้าใช้งานสำเร็จแล้ว ---
st.sidebar.markdown(f"### 🐉 จอมยุทธ์: **{st.session_state.username}** 🧧")
if st.sidebar.button("🚪 ออกจากสำนัก (Logout)"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.pop("word", None)
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("➕ เพิ่มคำศัพท์เข้าคลัง 📖")
levels = ["Level 1 (เริ่มต้น)", "Level 2 (ปานกลาง)", "Level 3 (ขั้นสูง)"]
add_lvl = st.sidebar.selectbox("🎯 ระดับความยาก:", levels)
add_zh = st.sidebar.text_input("🈴 ภาษาจีน (จำเป็น):")
add_py = st.sidebar.text_input("📌 พินอิน (จำเป็น):")
add_th = st.sidebar.text_input("🗣️ คำอ่านไทย:")
add_mn = st.sidebar.text_input("💡 คำแปล (จำเป็น):")

if st.sidebar.button("💾 จารึกคำศัพท์ใหม่", use_container_width=True):
    if add_zh.strip() and add_py.strip() and add_mn.strip():
        cursor.execute(
            "INSERT INTO vocab (level, chinese, pinyin, thai_read, meaning) VALUES (?,?,?,?,?)",
            (add_lvl, add_zh.strip(), add_py.strip(), add_th.strip(), add_mn.strip()),
        )
        conn.commit()
        st.session_state.word = (add_zh.strip(), add_py.strip(), add_th.strip(), add_mn.strip())
        st.sidebar.success(f"บันทึก '{add_zh}' สำเร็จ!")
        st.rerun()
    else:
        st.sidebar.error("❌ กรุณากรอก ภาษาจีน, พินอิน และคำแปล ให้ครบถ้วน")

st.sidebar.markdown("---")
with st.sidebar.expander("📜 คัมภีร์คำศัพท์ทั้งหมดในระบบ"):
    cursor.execute("SELECT level, chinese, pinyin, meaning FROM vocab ORDER BY id DESC")
    all_data = cursor.fetchall()
    st.dataframe(all_data, column_config={"0": "ระดับ", "1": "จีน", "2": "พินอิน", "3": "คำแปล"})


# --- 7. แสดงผลหน้าต่างหลัก (Tabs) ---
st.markdown("<h1 style='text-align: center; color: #FFD700;'>🏮 🐼 สำนักฝึกทักษะภาษาจีน AI 🐉 🏮</h1>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(
    ["🎙️ ฝึกออกเสียง + AI", "✏️ สอบพินอิน", "🎮 ศึกจับคู่ (10 ข้อ)", "📊 ทำเนียบคะแนน"]
)

# --------------------------------------------------
# โหมด 1: ฝึกพูด
# --------------------------------------------------
with tab1:
    sel_lvl = st.selectbox("🎯 เลือกระดับวิชา:", levels, key="t1_lvl")

    if st.button("🎲 สุ่มคัมภีร์คำศัพท์"):
        cursor.execute("SELECT chinese, pinyin, thai_read, meaning FROM vocab WHERE level = ?", (sel_lvl,))
        words = cursor.fetchall()
        if words:
            st.session_state.word = random.choice(words)
        else:
            st.warning("ยังไม่มีคำศัพท์ในระดับนี้")

    if "word" in st.session_state:
        zh, py, th, mn = st.session_state.word

        st.markdown(
            f"""
            <div style='background: rgba(0,0,0,0.45); padding: 25px; border-radius: 20px; border: 2px solid #FFD700; text-align: center; margin-top: 15px;'>
                <h1 style='color: #FFD700; font-size: 4rem; margin: 0;'>{zh}</h1>
                <h3 style='color: #FF6B6B; margin-top: 10px;'>📌 พินอิน: {py}</h3>
                {f"<h4 style='color: #4DABF7;'>🗣️ คำอ่านไทย: {th}</h4>" if th else ""}
                <h3 style='color: #FFD43B;'>💡 คำแปล: {mn}</h3>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🔊 ฟังเสียงจากอาจารย์เจ้าของภาษา:")
        audio_fp = speak_chinese(zh)
        st.audio(audio_fp, format="audio/mp3")

        st.markdown("---")
        st.subheader("🎙️ บันทึกเสียงท้าประลองกับ AI:")
        recorded_audio = st.audio_input("กดปุ่มเพื่อเริ่มบันทึกเสียงพูดของคุณ")

        if recorded_audio:
            with st.spinner("🤖 AI ปัญญาประดิษฐ์กำลังวิเคราะห์เสียงของจอมยุทธ์..."):
                audio_bytes = recorded_audio.read()
                text_detected, accuracy = evaluate_speech(audio_bytes, zh)

                if accuracy == -1:
                    st.warning("⚠️ ไม่สามารถประมวลผลไฟล์เสียงได้ กรุณาลองใหม่อีกครั้ง")
                elif text_detected is None:
                    st.error("❌ AI ฟังเสียงของคุณไม่ชัดเจน ลองปรับไมโครโฟนแล้วพูดใหม่อีกครั้ง")
                else:
                    st.markdown(f"### 🤖 สิ่งที่ AI ถอดความได้: **{text_detected}**")
                    st.metric(label="🎯 คะแนนพลังความแม่นยำ (Accuracy)", value=f"{accuracy}%")

                    if accuracy >= 80:
                        st.balloons()
                        st.success("🎉 ยอดเยี่ยมยิ่งนัก! ออกเสียงได้เป๊ะดั่งเจ้าของภาษามาเอง")
                    elif accuracy >= 50:
                        st.info("👍 ออกเสียงได้ดีพอใช้! ฝึกเน้นจังหวะอีกนิดจะสมบูรณ์แบบ")
                    else:
                        st.warning("💪 วรรณยุกต์ยังไม่แม่นยำ ลองฟังเสียงอาจารย์แล้วฝึกซ้ำอีกรอบนะ!")

# --------------------------------------------------
# โหมด 2: ทายพินอิน
# --------------------------------------------------
with tab2:
    q_lvl = st.selectbox("🎯 เลือกระดับทดสอบ:", levels, key="t2_lvl")
    if st.button("🔄 เริ่มทำแบบทดสอบพินอิน"):
        cursor.execute("SELECT chinese, pinyin FROM vocab WHERE level = ?", (q_lvl,))
        words = cursor.fetchall()
        if len(words) >= 2:
            target = random.choice(words)
            st.session_state.quiz_zh = target[0]
            st.session_state.quiz_ans = target[1]

            other_pinyins = list(set([w[1] for w in words if w[1] != target[1]]))
            wrong_choices = random.sample(other_pinyins, min(3, len(other_pinyins)))

            choices = [target[1]] + wrong_choices
            random.shuffle(choices)
            st.session_state.choices = choices
        else:
            st.warning("ต้องมีคำศัพท์ในระดับนี้อย่างน้อย 2 คำขึ้นไปเพื่อสร้างแบบทดสอบ")

    if "quiz_zh" in st.session_state:
        st.markdown(
            f"""
            <div style='background: rgba(0,0,0,0.3); padding: 20px; border-radius: 15px; border: 1px solid #FFD700; margin-top: 15px;'>
                <h2>คำว่า: <span style='color: #FFD700;'>{st.session_state.quiz_zh}</span> พินอินคือข้อใด?</h2>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
        user_choice = st.radio("เลือกคำตอบที่ถูกต้อง:", st.session_state.choices)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🎯 ยืนยันคำตอบ"):
            if user_choice == st.session_state.quiz_ans:
                st.balloons()
                st.success("🎉 ถูกต้องแล้วจอมยุทธ์! ยอดเยี่ยมมาก")
            else:
                st.error(f"❌ ยังไม่ถูกต้อง! คำตอบที่แท้จริงคือ: {st.session_state.quiz_ans}")

# --------------------------------------------------
# โหมด 3: เกมจับคู่ (10 ข้อ) + บันทึกคะแนน
# --------------------------------------------------
with tab3:
    g_lvl = st.selectbox("🎯 เลือกระดับเกมจับคู่:", levels, key="t3_lvl")
    if st.button("🎮 เริ่มศึกจับคู่ประลองปัญญา (10 ข้อ)"):
        cursor.execute("SELECT chinese, meaning FROM vocab WHERE level = ?", (g_lvl,))
        all_v = cursor.fetchall()

        if len(all_v) >= 4:
            questions = random.sample(all_v, min(10, len(all_v)))
            st.session_state.game_items = questions

            q_options = {}
            all_meanings = list(set([v[1] for v in all_v]))

            for idx, (zh, mn) in enumerate(questions):
                wrong_pool = [m for m in all_meanings if m != mn]
                wrong_choices = random.sample(wrong_pool, min(3, len(wrong_pool)))
                opts = [mn] + wrong_choices
                random.shuffle(opts)
                q_options[idx] = opts

            st.session_state.q_options = q_options
            st.session_state.game_checked = False
            st.session_state.score_saved = False
        else:
            st.warning("ต้องมีคำศัพท์อย่างน้อย 4 คำขึ้นไปในระดับนี้เพื่อสร้างเกมจับคู่")

    if "game_items" in st.session_state:
        answers = {}
        for idx, (zh, mn) in enumerate(st.session_state.game_items, 1):
            st.markdown(f"#### **ข้อที่ {idx}: <span style='color: #FFD700;'>{zh}</span>**", unsafe_allow_html=True)
            opts = st.session_state.q_options[idx - 1]
            user_select = st.radio(f"เลือกคำแปลสำหรับข้อ {idx}:", opts, key=f"g_{idx}")
            answers[idx] = (user_select, mn, zh)
            st.markdown("---")

        if st.button("🏆 ตรวจผลการประลองและบันทึกคะแนน"):
            st.session_state.game_checked = True
            st.session_state.user_answers = answers

        if st.session_state.get("game_checked", False):
            score = 0
            st.subheader("📝 ผลการสรุปคะแนนประลอง:")

            for idx, (ans, correct, zh) in st.session_state.user_answers.items():
                if ans == correct:
                    score += 1
                    st.success(f"**ข้อ {idx} [{zh}]:** ถูกต้อง! ✅ ({ans})")
                else:
                    st.error(f"**ข้อ {idx} [{zh}]:** ผิด ❌ (คุณตอบ: {ans} | **เฉลยที่ถูกต้อง: {correct}**)")

            total_q = len(st.session_state.game_items)
            st.markdown(f"### 📊 คะแนนประลองรวม: **{score} / {total_q}** คะแนน")

            if not st.session_state.get("score_saved", False):
                save_score(st.session_state.username, g_lvl, score, total_q)
                st.session_state.score_saved = True
                st.balloons()
                st.success("💾 บันทึกคะแนนลงในทำเนียบยุทธภพเรียบร้อยแล้ว!")

# --------------------------------------------------
# โหมด 4: หน้าประวัติคะแนนของผู้ใช้ (Dashboard)
# --------------------------------------------------
with tab4:
    st.subheader(f"📊 ทำเนียบเกียรติยศของ {st.session_state.username} 🏆")
    cursor.execute(
        "SELECT level, score, total, created_at FROM scores WHERE username = ? ORDER BY id DESC",
        (st.session_state.username,)
    )
    user_scores = cursor.fetchall()

    if user_scores:
        st.dataframe(
            user_scores,
            column_config={
                "0": "ระดับความยาก",
                "1": "คะแนนที่ทำได้",
                "2": "คะแนนเต็ม",
                "3": "วัน-เวลาที่บันทึก"
            },
            use_container_width=True
        )
    else:
        st.info("ท่านยังไม่มีประวัติการทำคะแนน ลองไปร่วมศึกจับคู่ในแท็บด้านบนดูนะ!")
