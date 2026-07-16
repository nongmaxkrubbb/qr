# ระบบคิวโรงพยาบาลออนไลน์ + QR Code เช็คสถานะ

เว็บแอปสำหรับให้คนไข้กดรับบัตรคิว แล้วสแกน QR Code เพื่อดูสถานะคิวแบบ real-time ผ่านสมาร์ทโฟนของตัวเอง (ไม่ต้องนั่งรอฟังเรียกชื่อหน้าห้องตรวจ)

## วิธีติดตั้งและรัน (สำหรับการทดสอบ)

```bash
pip3 install flask "qrcode[pil]" werkzeug
python3 run.py
```

จากนั้นเปิดเบราว์เซอร์ไปที่ `http://localhost:5050`

- **หน้าแรก (`/`)** — คนไข้กดรับบัตรคิว จะได้ QR Code มาสแกน
- **หน้าสถานะ (`/status/<id>`)** — สแกน QR แล้วมาโผล่ตรงนี้ อัปเดตอัตโนมัติทุก 5 วิ
- **หน้าเข้าสู่ระบบเจ้าหน้าที่ (`/admin/login`)** — username: `admin` / password: `admin1234` (แนะนำให้เปลี่ยนก่อนใช้งานจริง)
- **หน้าเลือกแผนก (`/admin`)** — (ต้อง login ก่อน) เลือกห้องตรวจที่ประจำอยู่เพื่อจัดการคิว
- **หน้าจัดการคิวแต่ละแผนก (`/admin/room/<id>`)** — (ต้อง login ก่อน) เรียกคิวถัดไป / เสร็จสิ้น / ข้ามคิว เฉพาะคิวในแผนกของตัวเอง ป้องกันการกดเรียกคิวผิดห้อง
- **หน้าสถิติ (`/admin/dashboard`)** — สรุปจำนวนคิว, เวลารอเฉลี่ย, ช่วงเวลาคนแน่นที่สุด (ต้อง login ก่อน)

---

## การนำไปใช้งานจริง (Production)

ถ้าต้องการนำไปเปิดทดสอบหรือใช้งานจริงจัง แนะนำให้ใช้ Production Web Server และจำลองลิงก์ผ่าน Cloudflare เพื่อให้คนไข้สแกนด้วย 4G/5G ได้:

**สำหรับ Windows:**
```cmd
pip install waitress
waitress-serve --port=5050 run:app
cloudflared tunnel --url http://localhost:5050
```

**สำหรับ Mac / Linux:**
```bash
pip3 install gunicorn
gunicorn -w 4 -b 0.0.0.0:5050 run:app
cloudflared tunnel --url http://localhost:5050
```

*(ระบบได้มีการเพิ่ม `ProxyFix` เพื่อรองรับ URL สาธารณะจาก Cloudflare Tunnel หรือ Ngrok ไว้เรียบร้อยแล้ว ทำให้ลิงก์ใน QR Code ถูกต้องเสมอ)*

---

## โครงสร้างไฟล์ (อัปเดตล่าสุดใช้ Flask Blueprints)

```
qrqueue/
├── run.py                 # ไฟล์หลักสำหรับเปิดเซิร์ฟเวอร์
├── config.py              # เก็บค่าตั้งค่าและ Secret Keys
├── queue.db               # SQLite database (สร้างอัตโนมัติตอนรันครั้งแรก)
├── PROJECT_SUMMARY.md     # ไฟล์สรุปภาพรวม Architecture
├── app/
│   ├── __init__.py        # App Factory & ProxyFix config
│   ├── database.py        # ระบบเชื่อมต่อและสร้างตารางฐานข้อมูล
│   ├── utils.py           # ฟังก์ชันคำนวณต่างๆ และสร้าง QR Code
│   └── routes/
│       ├── user_routes.py # รูทของหน้าผู้ใช้งาน
│       └── admin_routes.py# รูทของหน้าแอดมิน
└── templates/
    ├── base.html          # โครงสร้าง Layout สไตล์พรีเมียม (Glassmorphism)
    ├── index.html         # หน้ารับบัตรคิวโรงพยาบาล
    ├── ticket.html        # หน้าแสดง QR Code หลังได้บัตร
    ├── status.html        # หน้าติดตามสถานะ (polling)
    ├── login.html         # หน้าเข้าสู่ระบบเจ้าหน้าที่
    ├── admin.html         # หน้าเมนูเลือกห้องตรวจ
    ├── admin_room.html    # หน้าจัดการคิวรายแผนก
    └── dashboard.html     # หน้าสรุปสถิติ
```

## Database Schema

**queue_types** — ประเภทแผนก (id, name, prefix)
*ค่าเริ่มต้น: A: ซักประวัติ, B: ตรวจโรคทั่วไป, C: เจาะเลือด, D: รับยา/การเงิน, E: ทันตกรรม*
**tickets** — บัตรคิวแต่ละใบ (id, queue_number, queue_type_id, status, created_at, called_at, completed_at)
**staff** — บัญชีเจ้าหน้าที่ (id, username, password_hash)

สถานะของ ticket มี 4 แบบ: `waiting` → `in_service` → `done` (หรือ `skipped`)

## จุดเด่นของโปรเจคนี้

1. **Architecture มาตรฐาน:** แยกโค้ดตามระบบ MVC ย่อยด้วย Flask Blueprints
2. **UI ทันสมัย:** ใช้สไตล์พรีเมียม (Kanit Font, Gradient, Glassmorphism) เหมาะกับการเป็นแอปยุคใหม่
3. **การคำนวณเวลารออัจฉริยะ:** ดึงค่าเฉลี่ยของแผนกนั้นๆ มาคูณกับคิวก่อนหน้า เพื่อให้คนไข้ประมาณการเวลาได้
4. **แยกแดชบอร์ดตามห้องตรวจ:** ป้องกันความผิดพลาดจากการรวมปุ่มเรียกคิวของทุกแผนกไว้ในหน้าเดียว
