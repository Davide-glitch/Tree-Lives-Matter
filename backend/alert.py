import os
import time
import json
import numpy as np
import requests
from datetime import datetime, timedelta, timezone
from PIL import Image
from sentinelhub import SHConfig, SentinelHubRequest, MimeType, CRS, BBox, DataCollection
from web3 import Web3
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# ==============================
# FLASK + DATABASE SETUP
# ==============================
app = Flask(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/..
DB_PATH = os.path.join(PROJECT_ROOT, "frontend", "instance", "database.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# SQLAlchemy model for alerts
class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    forest = db.Column(db.String(100), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)
    percent_changed = db.Column(db.Float, nullable=False)
    ipfs_hash = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# CREATE TABLES INSIDE APP CONTEXT
with app.app_context():
    db.create_all()



# ==============================
# ORIGINAL CONFIGURATION & CREDENTIALS
# ==============================
# Sentinel Hub credentials
os.environ["SENTINEL_CLIENT_ID"] = "68ea348e-6434-402d-8931-578b3fffc951"
os.environ["SENTINEL_CLIENT_SECRET"] = "lg3mm9Ugun6kCJO5rtPOjpuPkPvRemvd"
os.environ["SENTINEL_INSTANCE_ID"] = "16896ddf-57bd-4b4e-9a43-4b25fbf4b642"

config = SHConfig()
config.sh_client_id = os.environ["SENTINEL_CLIENT_ID"]
config.sh_client_secret = os.environ["SENTINEL_CLIENT_SECRET"]

# Pinata credentials
PINATA_API_KEY = "ae6c4dcced202dd8f429"
PINATA_SECRET_API_KEY = "f8603cd4f6c785f96c543bfe393f77b5408deeb7849a1921b54f59496c0f13bb"

# Blockchain / Sepolia network
INFURA_URL = "https://sepolia.infura.io/v3/e711cc2abca045f583be9bc9d24bbdb3"
PRIVATE_KEY = ""  # <--- Your Metamask Sepolia private key here
ACCOUNT_ADDRESS = "0xae6bd60Cf0Cd7CF00a4116E99a473B9479cd401F"
CONTRACT_ADDRESS = "0x36E40d7644f24AEe41C61BEDC5234e54E91EdAa9"

# Admin email or endpoint for notifications
ADMIN_EMAIL = "admin@example.com"
ADMIN_WEBHOOK = "http://localhost:5000/api/alerts"

# Forests to monitor
FORESTS = [
    {"name": "Retezat North-East", "bbox": [25.70, 45.55, 25.80, 45.60]},
    {"name": "Danube - Forest", "bbox": [29.26, 45.20, 29.36, 45.30]}
]

# ==============================
# CONNECT TO BLOCKCHAIN
# ==============================
CONTRACT_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "eventId", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "ipfsHash", "type": "string"},
            {"indexed": False, "internalType": "int256", "name": "latitudeE6", "type": "int256"},
            {"indexed": False, "internalType": "int256", "name": "longitudeE6", "type": "int256"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "ndviChange", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "reporter", "type": "address"}
        ],
        "name": "EventLogged",
        "type": "event"
    },
    {
        "inputs": [
            {"internalType": "string", "name": "_ipfsHash", "type": "string"},
            {"internalType": "int256", "name": "_latitudeE6", "type": "int256"},
            {"internalType": "int256", "name": "_longitudeE6", "type": "int256"},
            {"internalType": "uint256", "name": "_timestamp", "type": "uint256"},
            {"internalType": "uint256", "name": "_ndviChange", "type": "uint256"}
        ],
        "name": "logEvent",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "events",
        "outputs": [
            {"internalType": "string", "name": "ipfsHash", "type": "string"},
            {"internalType": "int256", "name": "latitudeE6", "type": "int256"},
            {"internalType": "int256", "name": "longitudeE6", "type": "int256"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "uint256", "name": "ndviChange", "type": "uint256"},
            {"internalType": "address", "name": "reporter", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getTotalEvents",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

w3 = Web3(Web3.HTTPProvider(INFURA_URL))
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi= CONTRACT_ABI)  # Use your CONTRACT_ABI
print("🔗 Blockchain connected:", w3.is_connected())

# ==============================
# SENTINEL HUB FETCH
# ==============================
def fetch_ndvi_bands(bbox_coords, date):
    print(f"🛰️  Fetching Sentinel-2 data for {date}...")
    bbox = BBox(bbox=bbox_coords, crs=CRS.WGS84)
    evalscript = "return [B04, B08];"

    try:
        request = SentinelHubRequest(
            evalscript=evalscript,
            input_data=[SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A,
                time_interval=(f"{date}T00:00:00", f"{date}T23:59:59"),
                other_args={"dataFilter": {"maxCloudCoverage": 40}}
            )],
            responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
            bbox=bbox,
            size=(512, 512),
            config=config
        )
        data = request.get_data()
    except Exception as e:
        print("❌ SentinelHub request error:", e)
        return None

    if not data or len(data) == 0:
        print("⚠️ No Sentinel data returned for this date.")
        return None

    return np.array(data[0])

# ==============================
# NDVI & CHANGE DETECTION
# ==============================
def compute_ndvi(image):
    red = image[..., 0].astype(np.float32)
    nir = image[..., 1].astype(np.float32)
    return (nir - red) / (nir + red + 1e-10)

def detect_change(ndvi_before, ndvi_after, threshold=0.3):
    print("🔍 Detecting changes in vegetation...")
    delta = ndvi_after - ndvi_before
    deforestation_mask = delta < -threshold
    reforestation_mask = delta > threshold

    total_pixels = ndvi_before.size
    percent_deforestation = (np.sum(deforestation_mask) / total_pixels) * 100
    percent_reforestation = (np.sum(reforestation_mask) / total_pixels) * 100

    print(f"🌳 Deforestation: {percent_deforestation:.2f}% | 🌱 Reforestation: {percent_reforestation:.2f}%")
    return deforestation_mask, reforestation_mask, percent_deforestation, percent_reforestation

# ==============================
# PINATA INTEGRATION
# ==============================
def upload_to_pinata(change_mask, metadata):
    print("📤 Uploading change evidence to Pinata...")
    img = Image.fromarray((change_mask * 255).astype('uint8'))
    img.save("change_mask.png")

    headers = {"pinata_api_key": PINATA_API_KEY, "pinata_secret_api_key": PINATA_SECRET_API_KEY}

    # Upload image
    with open("change_mask.png", "rb") as fp:
        files = {"file": fp}
        response = requests.post("https://api.pinata.cloud/pinning/pinFileToIPFS", files=files, headers=headers)

    if response.status_code != 200:
        print("❌ Pinata upload error:", response.text)
        return None
    image_hash = response.json()["IpfsHash"]
    print(f"🖼️ Image uploaded to IPFS: {image_hash}")

    # Upload metadata JSON
    metadata_json = {
        "bbox": metadata["bbox"],
        "date_before": metadata["date_before"],
        "date_after": metadata["date_after"],
        "percent_deforestation": float(metadata["percent_deforestation"]),
        "percent_reforestation": float(metadata["percent_reforestation"]),
        "image_ipfs_hash": image_hash
    }
    meta_response = requests.post("https://api.pinata.cloud/pinning/pinJSONToIPFS", json=metadata_json, headers=headers)
    if meta_response.status_code == 200:
        metadata_hash = meta_response.json()["IpfsHash"]
        print(f"📦 Metadata uploaded to IPFS: {metadata_hash}")
        return metadata_hash
    else:
        print("❌ Metadata upload error:", meta_response.text)
        return None


# ==============================
# BLOCKCHAIN FUNCTIONS
# ==============================
def get_total_events():
    try:
        return contract.functions.getTotalEvents().call()
    except Exception as e:
        print("⚠️ Error fetching total events:", e)
        return 0

def get_events_for_forest(lat_center, lon_center, tolerance=0.01):
    """
    Returns a list of events on blockchain for a specific forest area.
    lat_center, lon_center: center coordinates of forest bbox
    tolerance: degrees to consider 'same forest'
    """
    total = get_total_events()
    events_for_forest = []

    for i in range(total):
        try:
            event = contract.functions.events(i).call()
            event_lat = event[1] / 1e6
            event_lon = event[2] / 1e6

            if abs(event_lat - lat_center) <= tolerance and abs(event_lon - lon_center) <= tolerance:
                events_for_forest.append(event)
        except Exception as e:
            print(f"⚠️ Error fetching event {i}: {e}")

    return events_for_forest

def register_initial_area(ipfs_hash, lat, lon):
    if not PRIVATE_KEY:
        print("⚠️ PRIVATE_KEY not set - skipping blockchain initial registration")
        return None

    timestamp = int(time.time())
    lat_e6 = int(lat * 1e6)
    lon_e6 = int(lon * 1e6)

    print("📝 Registering initial forest area on blockchain...")
    nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)
    txn = contract.functions.logEvent(ipfs_hash, lat_e6, lon_e6, timestamp, 0).build_transaction({
        "from": ACCOUNT_ADDRESS,
        "nonce": nonce,
        "gas": 300000,
        "gasPrice": w3.to_wei('30', 'gwei'),
        "chainId": 11155111
    })

    signed_txn = w3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"📡 Initial registration tx sent: {tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"✅ Initial registration confirmed in block: {receipt.blockNumber}")
    return receipt


def log_deforestation_event(ipfs_hash, lat, lon, ndvi_change_percent):
    if not PRIVATE_KEY:
        print("⚠️ PRIVATE_KEY not set - skipping blockchain transaction")
        return None

    timestamp = int(time.time())
    lat_e6 = int(lat * 1e6)
    lon_e6 = int(lon * 1e6)
    ndvi_scaled = int(ndvi_change_percent * 100)

    print("📝 Logging event to blockchain...")
    nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)
    txn = contract.functions.logEvent(ipfs_hash, lat_e6, lon_e6, timestamp, ndvi_scaled).build_transaction({
        "from": ACCOUNT_ADDRESS,
        "nonce": nonce,
        "gas": 300000,
        "gasPrice": w3.to_wei('30', 'gwei'),
        "chainId": 11155111
    })

    signed_txn = w3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"📡 Transaction sent: {tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"✅ Transaction confirmed in block: {receipt.blockNumber}")
    return receipt


# ==============================
# ALERT FUNCTION MODIFIED TO SAVE TO DB
# ==============================
def send_alert_to_admin(event_type, percent_changed, ipfs_hash, forest_name):
    alert_data = {
        "forest": forest_name,
        "alert": event_type,
        "percent_changed": percent_changed,
        "ipfs_hash": ipfs_hash,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "admin_email": ADMIN_EMAIL
    }
    
    print(f"🚨 ALERT: {event_type} detected in {forest_name} ({percent_changed:.2f}%)")
    
    # Save to database
    from backend.alert import db, Alert, app  # adjust import if needed
    with app.app_context():
        new_alert = Alert(
            forest=forest_name,
            alert_type=event_type,
            percent_changed=percent_changed,
            ipfs_hash=ipfs_hash
        )
        db.session.add(new_alert)
        db.session.commit()
    
    try:
        response = requests.post(ADMIN_WEBHOOK, json=alert_data, timeout=5)
        print(f"🔔 Alert webhook sent. Status code: {response.status_code}")
    except Exception as e:
        print("⚠️ Could not send webhook alert:", str(e))

# ==============================
# DAILY MONITORING PIPELINE
# ==============================
def daily_monitoring_pipeline(forest):
    USE_FIXED_DATES = True

    if USE_FIXED_DATES:
        date_yesterday = datetime(2025, 9, 23).date()
        date_today = datetime(2025, 9, 24).date()
    else:
        date_today  = datetime.now(timezone.utc).date()
        date_yesterday = date_today - timedelta(days=1)

    #Normalize both to strings right here
    date_today_str = date_today.isoformat()
    date_yesterday_str = date_yesterday.isoformat()

    forest_name = forest["name"]
    bbox = forest["bbox"]

    print("\n⏰ Scheduling daily monitoring...")
    print(f"🕒 Running scheduled monitoring for {date_today}")
    print(f"🌲 Monitoring {forest_name}...")

    before = fetch_ndvi_bands(bbox, date_yesterday)
    after = fetch_ndvi_bands(bbox, date_today)
    if before is None or after is None:
        print("❌ ERROR: Could not fetch Sentinel data for both dates.")
        return None

    ndvi_before = compute_ndvi(before)
    ndvi_after = compute_ndvi(after)

    deforestation_mask, reforestation_mask, percent_deforestation, percent_reforestation = detect_change(
        ndvi_before, ndvi_after, threshold=0.3
    )

    lat_center = (bbox[1] + bbox[3]) / 2
    lon_center = (bbox[0] + bbox[2]) / 2

    # STEP 1: INITIAL REGISTRATION
    events_for_this_forest = get_events_for_forest(lat_center, lon_center)
    if not events_for_this_forest:
        print("📍 No events found for this forest. Registering initial baseline...")

        metadata = {
            "bbox": bbox,
            "date_before": date_yesterday_str,
            "date_after": date_today_str,
            "percent_deforestation": percent_deforestation,
            "percent_reforestation": percent_reforestation,
            "note": "Initial baseline registration"
        }

        empty_mask = np.zeros_like(deforestation_mask, dtype=np.uint8)
        ipfs_hash = upload_to_pinata(empty_mask, metadata)

        if ipfs_hash:
            register_initial_area(ipfs_hash, lat_center, lon_center)

        return {"status": "Initial registration", "ipfs_hash": ipfs_hash}

    # STEP 2: ONLY LOG IF SIGNIFICANT CHANGE (>5%)
    event_type = None
    if percent_deforestation >= 5.0:
        event_type = "Deforestation"
        change_mask = deforestation_mask
        percent_changed = percent_deforestation
    elif percent_reforestation >= 5.0:
        event_type = "Reforestation"
        change_mask = reforestation_mask
        percent_changed = percent_reforestation
    else:
        print("ℹ️ No significant change detected (<5%).")
        return {
            "status": "No significant change",
            "deforestation": percent_deforestation,
            "reforestation": percent_reforestation
        }

    # Upload change to Pinata
    metadata = {
        "bbox": bbox,
        "date_before": date_yesterday_str,
        "date_after": date_today_str,
        "percent_deforestation": percent_deforestation,
        "percent_reforestation": percent_reforestation
    }
    ipfs_hash = upload_to_pinata(change_mask, metadata)

    if ipfs_hash:
        log_deforestation_event(ipfs_hash, lat_center, lon_center, percent_changed)
        send_alert_to_admin(event_type, percent_changed, ipfs_hash, forest_name)

    return {"status": event_type, "percent_changed": percent_changed, "ipfs_hash": ipfs_hash}


# ==============================
# RUN MONITORING
# ==============================
if __name__ == "__main__":
    print("🚀 Forest Monitoring System Initialized")
    for forest in FORESTS:
        daily_monitoring_pipeline(forest)
    print("\n=== 🌍 MONITORING COMPLETE ===")
