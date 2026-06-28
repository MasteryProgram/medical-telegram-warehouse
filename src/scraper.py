"""
Telegram Scraper for Ethiopian Medical & Pharmaceutical Channels
================================================================
Usage:
    python src/scraper.py --demo --path data --limit 15
    python src/scraper.py --path data --limit 200
"""

import os, csv, json, asyncio, argparse, logging, random, sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.datalake import write_channel_messages_json, write_manifest

load_dotenv()
api_id_str = os.getenv("Tg_API_ID")
api_hash   = os.getenv("Tg_API_HASH")
TODAY = datetime.today().strftime("%Y-%m-%d")
DEFAULT_CHANNEL_DELAY = 3.0
DEFAULT_MESSAGE_DELAY = 0.5

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
logger = logging.getLogger("telegram_scraper")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_DIR / f"scrape_{TODAY}.log", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(file_handler)
logger.addHandler(console_handler)

TARGET_CHANNELS = [
    "@lobelia4cosmetics",
    "@tikvahpharma",
    "@CheMed123",
    "@DoctorsET",
]

# =============================================================================
# LIVE SCRAPING
# =============================================================================

async def scrape_channel(client, channel, writer, base_path, date_str,
                         limit=100, message_delay=DEFAULT_MESSAGE_DELAY,
                         channel_delay=DEFAULT_CHANNEL_DELAY, max_retries=3):
    from telethon.tl.types import MessageMediaPhoto
    from telethon.errors import FloodWaitError

    channel_name = channel.strip("@")
    retries = 0

    while True:
        try:
            entity = await client.get_entity(channel)
            channel_title = entity.title
            messages = []

            channel_image_dir = os.path.join(base_path, "raw", "images", channel_name)
            os.makedirs(channel_image_dir, exist_ok=True)
            logger.info(f"Starting scrape of {channel} (limit={limit})")

            async for message in client.iter_messages(entity, limit=limit):
                image_path = None
                has_media = message.media is not None

                if has_media and isinstance(message.media, MessageMediaPhoto):
                    image_path = os.path.join(channel_image_dir, f"{message.id}.jpg")
                    try:
                        await client.download_media(message.media, image_path)
                    except Exception as e:
                        logger.warning(f"Failed to download image for msg {message.id}: {e}")
                        image_path = None

                message_dict = {
                    "message_id":    message.id,
                    "channel_name":  channel_name,
                    "channel_title": channel_title,
                    "message_date":  message.date.isoformat(),
                    "message_text":  message.message or "",
                    "has_media":     has_media,
                    "image_path":    image_path,
                    "views":         message.views or 0,
                    "forwards":      message.forwards or 0,
                }
                writer.writerow(list(message_dict.values()))
                messages.append(message_dict)

                if message_delay > 0:
                    await asyncio.sleep(message_delay)

            write_channel_messages_json(
                base_path=base_path, date_str=date_str,
                channel_name=channel_name, messages=messages,
            )
            logger.info(f"Finished scraping {channel}: {len(messages)} messages saved")
            if channel_delay > 0:
                await asyncio.sleep(channel_delay)
            return len(messages)

        except FloodWaitError as e:
            wait_seconds = max(int(getattr(e, "seconds", 0) or 0), 1)
            logger.warning(f"FloodWaitError on {channel}: sleeping {wait_seconds}s")
            await asyncio.sleep(wait_seconds)
            retries += 1
            if retries > max_retries:
                logger.error(f"Too many retries for {channel}. Skipping.")
                return 0
        except Exception as e:
            logger.error(f"Error scraping {channel}: {e}")
            return 0


async def scrape_all_channels(client, channels, base_path, limit=100,
                              message_delay=DEFAULT_MESSAGE_DELAY,
                              channel_delay=DEFAULT_CHANNEL_DELAY):
    await client.start()
    logger.info(f"Client authenticated. Scraping {len(channels)} channels...")

    csv_dir = os.path.join(base_path, "raw", "csv", TODAY)
    os.makedirs(csv_dir, exist_ok=True)
    os.makedirs(os.path.join(base_path, "raw", "telegram_messages", TODAY), exist_ok=True)
    os.makedirs(os.path.join(base_path, "raw", "images"), exist_ok=True)

    stats = {}
    with open(os.path.join(csv_dir, "telegram_data.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["message_id","channel_name","channel_title","message_date",
                         "message_text","has_media","image_path","views","forwards"])
        channel_counts = {}
        for channel in channels:
            logger.info(f"Scraping {channel}...")
            count = await scrape_channel(client, channel, writer, base_path,
                                         TODAY, limit, message_delay, channel_delay)
            stats[channel] = count
            channel_counts[channel.strip("@")] = count

        write_manifest(base_path=base_path, date_str=TODAY,
                       channel_message_counts=channel_counts)

    total = sum(stats.values())
    logger.info(f"Scraping complete. Total messages: {total}")
    for ch, count in stats.items():
        logger.info(f"  {ch}: {count} messages")
    return stats


# =============================================================================
# DEMO MODE
# =============================================================================

SAMPLE_MESSAGES = {
    "lobelia4cosmetics": {
        "title": "Lobelia Cosmetics & Health",
        "posts": [
            ("✨ New arrival: Neutrogena Hydro Boost Water Gel 50ml — 850 ETB. Perfect for dry skin this season! DM to order.", True),
            ("Lobelia pharmacy now stocks Cetaphil Moisturizing Cream 250g — 1,200 ETB. Dermatologist recommended for sensitive skin.", False),
            ("🌿 Natural shea butter, 100% pure and unrefined — 300 ETB / 200g jar. Great for hair and skin. Limited stock.", True),
            ("Vitamin C serum (20%) now available. Brightens skin, reduces dark spots. 650 ETB / 30ml. Order via DM.", True),
            ("Sunscreen SPF50+ available: La Roche-Posay Anthelios — 1,800 ETB. Best protection for Ethiopian sun exposure.", False),
            ("🧴 Baby Johnson's full range now in stock: lotion, shampoo, powder — from 180 ETB. Gentle for newborns.", True),
            ("Biotin supplement (10,000mcg) for hair growth — 550 ETB / 60 capsules. Many customers report great results!", False),
            ("Collagen peptide powder available — 1,400 ETB / 300g. Dissolves in water or juice. Improves skin elasticity.", True),
            ("Dermal filler info session this Saturday at Lobelia clinic. Free consultation. Limited slots — call to register.", False),
            ("Argan oil hair treatment — 100% pure Moroccan argan oil. 750 ETB / 100ml. Repairs damaged and frizzy hair.", True),
            ("New: Himalaya neem face wash 150ml — 220 ETB. Excellent for oily and acne-prone skin. All natural ingredients.", False),
            ("Evening primrose oil capsules (1000mg) — 480 ETB / 60 caps. Good for hormonal balance and skin health.", True),
            ("Hair relaxer kits (Dark & Lovely, ORS) now available from 350 ETB. All hair types covered.", False),
            ("Kojic acid soap for skin lightening — 180 ETB/bar. Proven to reduce melanin. Natural and safe formula.", True),
            ("Zinc + Vitamin D combo supplement — 420 ETB / 90 tablets. Immune support and bone health. Now in stock.", False),
        ],
    },
    "tikvahpharma": {
        "title": "Tikvah Ethiopia Pharma",
        "posts": [
            ("Paracetamol 500mg tablets (Panadol) — 45 ETB per pack of 20. Always available at Tikvah. #pharmacy", False),
            ("Amoxicillin 500mg capsules in stock — prescription required. 120 ETB per blister of 10 caps.", True),
            ("⚠️ Drug awareness: Never self-prescribe antibiotics. Resistance is a growing concern in Ethiopia. Consult a doctor first.", False),
            ("Metformin 500mg available for diabetes management — 85 ETB / 30 tablets. Requires valid prescription.", False),
            ("Insulin (Mixtard 30/70) now in stock. Refrigerated storage maintained. Contact us for pricing. Prescription needed.", True),
            ("Omeprazole 20mg capsules — for acid reflux and stomach ulcers. 95 ETB / 14 caps. OTC available.", False),
            ("Blood pressure medications in stock: Amlodipine, Enalapril, Losartan. All require prescription. Call for pricing.", True),
            ("Folic acid 5mg tablets (pregnancy supplement) — 35 ETB / 30 tabs. Essential for early pregnancy.", False),
            ("Tikvah now offers medication home delivery in Addis Ababa. Order via Telegram or call our hotline. T&Cs apply.", True),
            ("Azithromycin 500mg — 3-day pack for bacterial infections. 180 ETB. Prescription required from licensed doctor.", False),
            ("Oral Rehydration Salts (ORS) packets — 15 ETB each. Essential for diarrhea treatment. Always stock at home.", True),
            ("Multivitamin range available: Centrum, Supradyn, local generics — from 250 ETB. No prescription needed.", False),
            ("Antimalarial drugs (Coartem, Chloroquine) available. Important for travel to endemic regions. Ask our pharmacist.", True),
            ("Cough syrup options: Benylin, Actifed, local equivalents — from 85 ETB. All formulations available.", False),
            ("Tikvah Pharma tip: Store medications in a cool, dry place away from sunlight. Check expiry dates regularly.", True),
        ],
    },
    "CheMed123": {
        "title": "CheMed Medical Supplies",
        "posts": [
            ("Surgical gloves (latex, nitrile) available in bulk — box of 100: 650 ETB (nitrile) / 450 ETB (latex).", True),
            ("Digital thermometers in stock — 280 ETB each. Medical grade, accurate ±0.1°C. Bulk orders for clinics welcome.", False),
            ("Pulse oximeter (fingertip) — 850 ETB. SpO2 and heart rate monitoring. FDA-cleared. Fast delivery in Addis.", True),
            ("N95 respirator masks available — box of 20: 1,200 ETB. Suitable for medical staff and high-risk individuals.", False),
            ("Blood glucose monitors: Accu-Chek Active — 1,800 ETB including 10 test strips. DM for refill strip pricing.", True),
            ("Surgical face masks (3-ply) — box of 50: 200 ETB. All CheMed masks meet WHO quality standards.", False),
            ("IV cannulas (all gauges) and IV sets available for hospital procurement. Contact our B2B team for quotes.", True),
            ("Stethoscope (Littmann Classic III) — 4,500 ETB. Perfect for medical students and junior doctors.", True),
            ("Hand sanitizer gel 500ml (70% ethanol) — 180 ETB. Hospital and clinic bulk pricing available on request.", False),
            ("Wound care supplies: sterile gauze, bandages, antiseptic. Complete first aid kit — 650 ETB.", True),
            ("Nebulizer machine (portable) — 2,200 ETB. For asthma and respiratory conditions. Includes mask and tubing.", False),
            ("Weighing scales (digital baby scale) — 1,900 ETB. Accurate to 10g. Essential for newborn care.", True),
            ("Lancets and test strips for blood glucose — compatible with most meters. 50 strips: 380 ETB.", False),
            ("Syringe disposal containers (sharps boxes) — 5L: 120 ETB. Safe disposal for clinics and home dialysis.", True),
            ("CheMed bulk discount: 10% off orders above 10,000 ETB. 15% off above 50,000 ETB. Contact sales team.", False),
        ],
    },
    "DoctorsET": {
        "title": "Doctors Ethiopia",
        "posts": [
            ("Health tip: Drink at least 2 liters of water daily. Dehydration is often mistaken for hunger. Stay hydrated!", False),
            ("⚠️ Warning: Fake medicines are a serious problem in Ethiopia. Always buy from licensed pharmacies. #PatientSafety", True),
            ("Type 2 diabetes can be managed or even reversed with lifestyle changes. Diet, exercise, and medication all matter.", False),
            ("Blood pressure above 140/90 mmHg consistently = hypertension. Get checked. Treatment is available and affordable.", True),
            ("Malaria symptoms: fever, chills, headache, vomiting. If suspected, seek diagnosis immediately. Don't self-treat.", False),
            ("Mental health matters. Depression affects 1 in 5 Ethiopians. Seeking help is a sign of strength, not weakness.", True),
            ("Exclusive breastfeeding for first 6 months gives babies the best start. It also protects maternal health.", False),
            ("Tuberculosis (TB) is curable. Free TB treatment is available at all government health centers in Ethiopia.", True),
            ("COVID-19 boosters now recommended for over-60s and immunocompromised patients. Check your nearest health post.", False),
            ("Hand washing with soap for 20 seconds prevents up to 80% of common infections. Teach your children this habit.", True),
            ("HIV testing is free and confidential at all government hospitals. Know your status. Treatment is available.", False),
            ("Cervical cancer screening is available at major hospitals. Women aged 25–65 should screen every 3–5 years.", True),
            ("Gestational diabetes: all pregnant women should be screened at 24–28 weeks. Manageable with proper care.", False),
            ("Antibiotic resistance is a growing crisis. Finish your full course. Never share or reuse antibiotics.", True),
            ("Children's vaccination schedule reminder: make sure your child is up to date on all EPI vaccines.", False),
        ],
    },
}


def _create_placeholder_image(path, channel_name="", msg_id=0, text_snippet=""):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return

    COLORS = {
        "lobelia4cosmetics": (160, 40, 100),
        "tikvahpharma":      (30, 100, 170),
        "CheMed123":         (20, 130, 80),
        "DoctorsET":         (180, 100, 20),
    }
    img = Image.new("RGB", (400, 300), COLORS.get(channel_name, (70, 70, 70)))
    draw = ImageDraw.Draw(img)
    try:
        font_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except OSError:
        font_lg = font_sm = ImageFont.load_default()

    draw.text((20, 20), f"@{channel_name}", fill="white", font=font_lg)
    draw.text((20, 55), f"Message #{msg_id}", fill=(210, 210, 210), font=font_sm)

    words = text_snippet[:120].split()
    lines, line = [], ""
    for w in words:
        candidate = (line + " " + w).strip()
        if len(candidate) > 42:
            lines.append(line); line = w
        else:
            line = candidate
    if line: lines.append(line)

    y = 100
    for ln in lines[:5]:
        draw.text((20, y), ln, fill=(230, 230, 230), font=font_sm)
        y += 22

    draw.text((20, 270), "DEMO IMAGE", fill=(255, 255, 255), font=font_sm)
    img.save(path, "JPEG", quality=85)


def run_demo(base_path: str, limit: int) -> Dict[str, int]:
    logger.info("[DEMO MODE] Generating sample medical/pharma data")

    csv_dir = os.path.join(base_path, "raw", "csv", TODAY)
    os.makedirs(csv_dir, exist_ok=True)
    now = datetime.now(timezone.utc)
    channel_counts = {}

    with open(os.path.join(csv_dir, "telegram_data.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["message_id","channel_name","channel_title","message_date",
                         "message_text","has_media","image_path","views","forwards"])

        for channel_name, channel_data in SAMPLE_MESSAGES.items():
            posts = channel_data["posts"][:limit]
            messages = []

            channel_image_dir = os.path.join(base_path, "raw", "images", channel_name)
            os.makedirs(channel_image_dir, exist_ok=True)
            logger.info(f"[DEMO] Scraping @{channel_name} ({len(posts)} posts)")

            for i, (text, has_media) in enumerate(posts):
                msg_id = 2000 + i
                msg_date = (now - timedelta(hours=i * 3 + random.randint(0, 2))).isoformat()
                image_path = None

                if has_media:
                    image_path = os.path.join(channel_image_dir, f"{msg_id}.jpg")
                    _create_placeholder_image(image_path, channel_name, msg_id, text)

                views = random.randint(50, 5000)
                msg = {
                    "message_id": msg_id, "channel_name": channel_name,
                    "channel_title": channel_data["title"], "message_date": msg_date,
                    "message_text": text, "has_media": has_media,
                    "image_path": image_path, "views": views,
                    "forwards": random.randint(0, max(1, views // 10)),
                }
                messages.append(msg)
                writer.writerow(list(msg.values()))

            write_channel_messages_json(base_path=base_path, date_str=TODAY,
                                        channel_name=channel_name, messages=messages)
            channel_counts[channel_name] = len(messages)
            logger.info(f"[DEMO] Finished @{channel_name}: {len(messages)} messages saved")

    write_manifest(base_path=base_path, date_str=TODAY,
                   channel_message_counts=channel_counts)
    logger.info(f"[DEMO] Complete. Total: {sum(channel_counts.values())} messages")
    return channel_counts


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telegram Scraper — Ethiopian Medical Channels")
    parser.add_argument("--path",          type=str,   default="data")
    parser.add_argument("--limit",         type=int,   default=100)
    parser.add_argument("--message-delay", type=float, default=DEFAULT_MESSAGE_DELAY)
    parser.add_argument("--channel-delay", type=float, default=DEFAULT_CHANNEL_DELAY)
    parser.add_argument("--demo",          action="store_true")
    args = parser.parse_args()

    if args.demo:
        run_demo(args.path, args.limit)
    else:
        if not api_id_str or not api_hash:
            print("ERROR: Missing Tg_API_ID or Tg_API_HASH in .env")
            sys.exit(1)

        from telethon import TelegramClient
        client = TelegramClient("telegram_scraper_session", int(api_id_str), api_hash)
        logger.info("Telegram client initialized")

        async def main():
            async with client:
                await scrape_all_channels(client, TARGET_CHANNELS, args.path, args.limit,
                                          args.message_delay, args.channel_delay)
        asyncio.run(main())