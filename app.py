import hashlib
import io
import random
import sqlite3
from datetime import datetime

from gtts import gTTS
import speech_recognition as sr
import streamlit as st

st.set_page_config(page_title="Chinese Practice 🐼", page_icon="🐼", layout="wide")

# --- 1. จัดการฐานข้อมูล SQLite ---
conn = sqlite3.connect("chinese_ai.db", check_same_thread=False)
cursor = conn.cursor()

# ตารางคำศัพท์
cursor.execute("""
    CREATE TABLE IF NOT EXISTS vocab (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level TEXT, chinese TEXT, pinyin TEXT, thai_read TEXT, meaning TEXT
    )
""")

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
        # Level 1 (เริ่มต้น)
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
        # Level 2 (ปานกลาง)
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
        # Level 3 (ขั้นสูง)
        ("Level 3 (ขั้นสูง)", "入乡随俗", "rù xiāng suí sú", "", "เข้าเมืองตาลิ่วต้องลิ่วตาตาม"),
        ("Level 3 (ขั้นสูง)", "失败是成功之母", "shī bài shì chéng gōng zhī mǔ", "", "ความล้มเหลวคือมารดาแห่งความสำเร็จ"),
        ("Level 3 (ขั้นสูง)", "千里之行，始于足下", "qiān lǐ zhī xíng, shǐ yú zú xià", "", "การเดินทางพันลี้เริ่มต้นที่ก้าวแรก"),
        ("Level 3 (ขั้นสูง)", "熟能生巧", "shú néng shēng qiǎo", "", "ฝึกฝนจนชำนาญจะเกิดความเชี่ยวชาญ"),
        ("Level 3 (ขั้นสูง)", "欲速则不达", "yù sù zé bù dá", "", "รีบร้อนเกินไปมักไม่สำเร็จ"),
        ("Level 3 (ขั้นสูง)", "知识就是力量", "zhī shi jiù shì lì liàng", "", "ความรู้คือพลัง"),
        ("Level 3 (ขั้นสูง)", "活到老，学到老", "huó dào lǎo, xué dào lǎo", "", "เรียนรู้ได้ตลอดชีวิตจนแก่"),
        ("Level 3 (ขั้นสูง)", "温故而知新", "wēn gù ér zhī xīn", "", "ทบทวนสิ่งเก่าทำให้รู้สิ่งใหม่"),
        ("Level 3 (ขั้นสูง)", "事实胜于雄辩", "shì shí shèng yú xióng biàn", "", "ข้อเท็จจริงมีน้ำหนักมากกว่าคำพูด"),
        ("Level 3 (ขั้นสูง)", "百闻不如一见", "bǎi wén bù rú yī jiàn", "", "สิบปากว่าไม่เท่าตาเห็น")
    ]
    cursor.executemany("INSERT INTO vocab (level, chinese, pinyin, thai_read, meaning) VALUES (?,?,?,?,?)", data)
    conn.commit()


# --- 2. ฟังก์ชันช่วยจัดการผู้ใช้และการเข้ารหัส ---
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


# --- 3. ฟังก์ชัน AI อ่านออกเสียงและประเมิน ---
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

        clean_expected = expected_text.replace("？", "").replace("！", "").replace("，", "").strip()
        correct_count = sum(1 for char in recognized_text if char in clean_expected)
        total_count = max(len(clean_expected), 1)
        accuracy = min(100, int((correct_count / total_count) * 100))

        return recognized_text, accuracy
    except sr.UnknownValueError:
        return None, 0
    except Exception:
        return None, -1


# --- 4. ระบบยืนยันตัวตน (Authentication Flow) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.title("🐼 ระบบฝึกภาษาจีน - เข้าสู่ระบบ")
    auth_mode = st.radio("เลือกทำรายการ:", ["เข้าสู่ระบบ (Login)", "สมัครสมาชิก (Register)"])

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if auth_mode == "เข้าสู่ระบบ (Login)":
            st.subheader("🔑 เข้าสู่ระบบ")
            user = st.text_input("ชื่อผู้ใช้งาน (Username)")
            passwd = st.text_input("รหัสผ่าน (Password)", type="password")
            if st.button("เข้าสู่ระบบ", use_container_width=True):
                result = login_user(user, passwd)
                if result:
                    st.session_state.logged_in = True
                    st.session_state.username = user
                    st.success(f"ยินดีต้อนรับคุณ {user}!")
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

        else:
            st.subheader("📝 สมัครสมาชิกใหม่")
            new_user = st.text_input("ตั้งชื่อผู้ใช้งาน (Username)")
            new_passwd = st.text_input("ตั้งรหัสผ่าน (Password)", type="password")
            confirm_passwd = st.text_input("ยืนยันรหัสผ่าน", type="password")
            if st.button("ลงทะเบียน", use_container_width=True):
                if new_user and new_passwd:
                    if new_passwd != confirm_passwd:
                        st.error("รหัสผ่านยืนยันไม่ตรงกัน")
                    else:
                        cursor.execute("SELECT * FROM users WHERE username = ?", (new_user,))
                        if cursor.fetchone():
                            st.warning("ชื่อผู้ใช้นี้มีในระบบแล้ว กรุณาใช้ชื่ออื่น")
                        else:
                            add_userdata(new_user, new_passwd)
                            st.success("สมัครสมาชิกสำเร็จ! กรุณาสลับไปหน้าเข้าสู่ระบบ")
                else:
                    st.error("กรุณากรอกข้อมูลให้ครบทุกช่อง")

    st.stop()


# --- 5. เมนูหลักเมื่อ Login เข้าใช้งานสำเร็จแล้ว ---
st.sidebar.markdown(f"### 👤 ผู้ใช้งาน: **{st.session_state.username}**")
if st.sidebar.button("🚪 ออกจากระบบ (Logout)"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.pop("word", None)
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("➕ เพิ่มคำศัพท์ใหม่")
levels = ["Level 1 (เริ่มต้น)", "Level 2 (ปานกลาง)", "Level 3 (ขั้นสูง)"]
add_lvl = st.sidebar.selectbox("ระดับความยาก:", levels)
add_zh = st.sidebar.text_input("ภาษาจีน (จำเป็น):")
add_py = st.sidebar.text_input("พินอิน (จำเป็น):")
add_th = st.sidebar.text_input("คำอ่านไทย:")
add_mn = st.sidebar.text_input("คำแปล (จำเป็น):")

if st.sidebar.button("💾 บันทึกคำใหม่", use_container_width=True):
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
with st.sidebar.expander("📖 ดูคลังคำศัพท์ทั้งหมดในระบบ"):
    cursor.execute("SELECT level, chinese, pinyin, meaning FROM vocab ORDER BY id DESC")
    all_data = cursor.fetchall()
    st.dataframe(all_data, column_config={"0": "ระดับ", "1": "จีน", "2": "พินอิน", "3": "คำแปล"})


# --- 6. แสดงผลหน้าต่างหลัก (Tabs) ---
st.title("🐼 แอพฝึกภาษาจีนพร้อม AI ประเมินเสียงพูด")
tab1, tab2, tab3, tab4 = st.tabs(
    ["🎙️ ฝึกพูด + AI ประเมิน", "✏️ ทายพินอิน", "🎮 เกมจับคู่ (10 ข้อ)", "📊 ประวัติคะแนนของฉัน"]
)

# --------------------------------------------------
# โหมด 1: ฝึกพูด
# --------------------------------------------------
with tab1:
    sel_lvl = st.selectbox("เลือกระดับทักษะ:", levels, key="t1_lvl")

    if st.button("🎲 สุ่มคำศัพท์"):
        cursor.execute("SELECT chinese, pinyin, thai_read, meaning FROM vocab WHERE level = ?", (sel_lvl,))
        words = cursor.fetchall()
        if words:
            st.session_state.word = random.choice(words)
        else:
            st.warning("ยังไม่มีคำศัพท์ในระดับนี้")

    if "word" in st.session_state:
        zh, py, th, mn = st.session_state.word

        st.markdown(f"<h1 style='text-align: center;'>{zh}</h1>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align: center; color: red;'>📌 พินอิน: {py}</h3>", unsafe_allow_html=True)
        if th:
            st.markdown(f"<h4 style='text-align: center; color: blue;'>🗣️ คำอ่านไทย: {th}</h4>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='text-align: center;'>💡 คำแปล: {mn}</h4>", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("🔊 ตัวอย่างการออกเสียง (เจ้าของภาษา):")
        audio_fp = speak_chinese(zh)
        st.audio(audio_fp, format="audio/mp3")

        st.markdown("---")
        st.subheader("🎙️ บันทึกเสียงของคุณเพื่อลองประเมิน:")
        recorded_audio = st.audio_input("กดปุ่มเพื่อบันทึกเสียงพูดของคุณ")

        if recorded_audio:
            with st.spinner("🤖 AI กำลังฟังและวิเคราะห์การออกเสียงของคุณ..."):
                audio_bytes = recorded_audio.read()
                text_detected, accuracy = evaluate_speech(audio_bytes, zh)

                if accuracy == -1:
                    st.warning("⚠️ ไม่สามารถประมวลผลไฟล์เสียงได้ กรุณาลองใหม่อีกครั้งครับ")
                elif text_detected is None:
                    st.error("❌ AI ฟังเสียงของคุณไม่ชัดเจน/ไม่เป็นคำ ลองปรับไมโครโฟนแล้วพูดใหม่อีกครั้งครับ")
                else:
                    st.markdown(f"### 🤖 สิ่งที่ AI ถอดความได้: **{text_detected}**")
                    st.metric(label="🎯 คะแนนความแม่นยำ (Accuracy)", value=f"{accuracy}%")

                    if accuracy >= 80:
                        st.success("🎉 ยอดเยี่ยมมาก! คุณออกเสียงได้อย่างแม่นยำใกล้เคียงเจ้าของภาษา")
                        st.balloons()
                    elif accuracy >= 50:
                        st.info("👍 ออกเสียงได้ดีพอใช้ได้! กดฟังตัวอย่างเสียงด้านบนแล้วลองอีกรอบนะ")
                    else:
                        st.warning("💪 ยังออกเสียงไม่ตรงนัก ลองฟังเสียงตัวอย่างแล้วฝึกเน้นเสียงวรรณยุกต์เพิ่มดูนะ!")

# --------------------------------------------------
# โหมด 2: ทายพินอิน
# --------------------------------------------------
with tab2:
    q_lvl = st.selectbox("เลือกระดับ:", levels, key="t2_lvl")
    if st.button("🔄 เริ่มข้อสอบพินอิน"):
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
            st.warning("จำเป็นต้องมีคำศัพท์ในระดับนี้อย่างน้อย 2 คำเพื่อทำแบบทดสอบ")

    if "quiz_zh" in st.session_state:
        st.subheader(f"คำว่า: **{st.session_state.quiz_zh}** พินอินคือข้อใด?")
        user_choice = st.radio("เลือกคำตอบ:", st.session_state.choices)
        if st.button("ส่งคำตอบ"):
            if user_choice == st.session_state.quiz_ans:
                st.success("ถูกต้องครับ! 🎉")
            else:
                st.error(f"ผิดครับ คำตอบคือ: {st.session_state.quiz_ans}")

# --------------------------------------------------
# โหมด 3: เกมจับคู่ (10 ข้อ) + บันทึกคะแนนอัตโนมัติ
# --------------------------------------------------
with tab3:
    g_lvl = st.selectbox("เลือกระดับเกม:", levels, key="t3_lvl")
    if st.button("🎮 เริ่มเล่นเกม (10 ข้อ)"):
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
            # 🔄 รีเซ็ตสถานะการบันทึกคะแนนเพื่อรองรับการเล่นเกมรอบใหม่
            st.session_state.score_saved = False 
        else:
            st.warning("ต้องมีคำศัพท์อย่างน้อย 4 คำขึ้นไปในระดับนี้เพื่อสร้างเกมจับคู่")

    if "game_items" in st.session_state:
        answers = {}
        for idx, (zh, mn) in enumerate(st.session_state.game_items, 1):
            st.write(f"**ข้อที่ {idx}: {zh}**")
            opts = st.session_state.q_options[idx - 1]
            user_select = st.radio(f"เลือกคำแปลสำหรับข้อ {idx}:", opts, key=f"g_{idx}")
            answers[idx] = (user_select, mn, zh)
            st.markdown("---")

        if st.button("🏆 ตรวจคะแนนและบันทึกผล"):
            st.session_state.game_checked = True
            st.session_state.user_answers = answers

        if st.session_state.get("game_checked", False):
            score = 0
            st.subheader("📝 ผลการตรวจทานและเฉลย:")

            for idx, (ans, correct, zh) in st.session_state.user_answers.items():
                if ans == correct:
                    score += 1
                    st.success(f"**ข้อ {idx} [{zh}]:** ถูกต้อง! ✅ (ตอบ: {ans})")
                else:
                    st.error(f"**ข้อ {idx} [{zh}]:** ผิด ❌ (คุณตอบ: {ans} | **เฉลยที่ถูกต้อง: {correct}**)")

            total_q = len(st.session_state.game_items)
            st.markdown(f"### 📊 คุณได้คะแนนทั้งหมด: **{score} / {total_q}** คะแนน")

            # 💾 บันทึกคะแนนลง Database เมื่อกดตรวจคะแนนรอบนี้เป็นครั้งแรก
            if not st.session_state.get("score_saved", False):
                save_score(st.session_state.username, g_lvl, score, total_q)
                st.session_state.score_saved = True
                st.balloons()
                st.success("💾 บันทึกคะแนนลงในประวัติผู้ใช้งานของคุณเรียบร้อยแล้ว!")

# --------------------------------------------------
# โหมด 4: หน้าประวัติคะแนนของผู้ใช้ (Dashboard)
# --------------------------------------------------
with tab4:
    st.subheader(f"📊 ประวัติการเล่นเกมของ {st.session_state.username}")
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
                "1": "คะแนนที่ได้",
                "2": "คะแนนเต็ม",
                "3": "วัน-เวลาที่บันทึก"
            },
            use_container_width=True
        )
    else:
        st.info("คุณยังไม่มีประวัติการทำคะแนน ลองไปเล่นโหมดเกมจับคู่ดูนะ!")
