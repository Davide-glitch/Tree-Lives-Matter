import os
import time
import json
import numpy as np
import requests
from PIL import Image
from dotenv import load_dotenv
from sentinelhub import SHConfig, SentinelHubRequest, MimeType, CRS, BBox, DataCollection
from web3 import Web3

# ==============================
# CONFIGURATION
# ==============================

"""Sensitive credentials are loaded from .env if present.
All integrations are optional. When keys are missing, steps are skipped gracefully.
"""

# Load .env from backend folder
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Sentinel Hub credentials (optional)
SENTINEL_CLIENT_ID = os.getenv("SENTINEL_CLIENT_ID")
SENTINEL_CLIENT_SECRET = os.getenv("SENTINEL_CLIENT_SECRET")

config = SHConfig()
if SENTINEL_CLIENT_ID and SENTINEL_CLIENT_SECRET:
    config.sh_client_id = SENTINEL_CLIENT_ID
    config.sh_client_secret = SENTINEL_CLIENT_SECRET
else:
    # Without credentials, Sentinel requests will be skipped
    config.sh_client_id = None
    config.sh_client_secret = None

# Pinata credentials (optional)
PINATA_API_KEY = os.getenv("PINATA_API_KEY")
PINATA_SECRET_API_KEY = os.getenv("PINATA_SECRET_API_KEY")

# Blockchain / SePolia network (optional)
INFURA_URL = os.getenv("INFURA_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")  # leave empty to disable signing
ACCOUNT_ADDRESS = os.getenv("ACCOUNT_ADDRESS")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
CONTRACT_ABI = json.loads("""[
    {
        "inputs": [
            {"internalType":"string","name":"_ipfsHash","type":"string"},
            {"internalType":"int256","name":"_latitudeE6","type":"int256"},
            {"internalType":"int256","name":"_longitudeE6","type":"int256"},
            {"internalType":"uint256","name":"_timestamp","type":"uint256"},
            {"internalType":"uint256","name":"_ndviChange","type":"uint256"}
        ],
        "name":"logEvent",
        "outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
        "stateMutability":"nonpayable",
        "type":"function"
    }
]""")

# Connect Web3 only if URL is provided
w3 = None
contract = None
if INFURA_URL:
    try:
        w3 = Web3(Web3.HTTPProvider(INFURA_URL))
        if w3.is_connected() and CONTRACT_ADDRESS:
            contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
        print("Blockchain connected:", w3.is_connected())
    except Exception as e:
        print("Blockchain connection error:", e)
        w3 = None
        contract = None

# ==============================
# SENTINEL HUB FETCH
# ==============================
def fetch_ndvi_bands(bbox_coords, date):
    if not (SENTINEL_CLIENT_ID and SENTINEL_CLIENT_SECRET):
        print("Sentinel credentials missing. Skipping SentinelHub request.")
        return None

    print(f"Fetching data for {date} ...")
    bbox = BBox(bbox=bbox_coords, crs=CRS.WGS84)

    evalscript = """
    // NDVI bands: B04=Red, B08=NIR
    return [B04, B08];
    """

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
        print("SentinelHub request error:", e)
        return None

    if not data or len(data) == 0:
        print("No data returned for this date.")
        return None

    print(f"Data received for {date}, shape: {np.array(data[0]).shape}")
    return np.array(data[0])

# ==============================
# NDVI(Normalized Difference Vegetation Index) COMPUTATION
# ==============================
def compute_ndvi(image):
    red = image[..., 0]
    nir = image[..., 1]
    ndvi = (nir - red) / (nir + red + 1e-10)
    return ndvi

# ==============================
# CHANGE DETECTION
# ==============================
def detect_change(ndvi_before, ndvi_after, threshold=0.2):
    print("Detecting change...")
    delta = np.abs(ndvi_after - ndvi_before)
    change_mask = delta > threshold
    percent_changed = (np.sum(change_mask) / change_mask.size) * 100
    print(f"Change detected: {percent_changed:.2f}% of area")
    return change_mask, percent_changed

# ==============================
# UPLOAD TO PINATA
# ==============================
def upload_to_pinata(change_mask, metadata):
    if not (PINATA_API_KEY and PINATA_SECRET_API_KEY):
        print("Pinata keys missing. Skipping IPFS upload.")
        return None

    print("Uploading evidence to Pinata...")
    img = Image.fromarray((change_mask * 255).astype('uint8'))
    img.save("change_mask.png")

    headers = {"pinata_api_key": PINATA_API_KEY, "pinata_secret_api_key": PINATA_SECRET_API_KEY}

    # Upload image
    with open("change_mask.png", "rb") as fp:
        files = {"file": fp}
        response = requests.post("https://api.pinata.cloud/pinning/pinFileToIPFS", files=files, headers=headers)

    if response.status_code != 200:
        print("Pinata image upload error:", response.text)
        return None
    image_hash = response.json()["IpfsHash"]
    print("Image uploaded to IPFS:", image_hash)

    # Upload metadata
    metadata_json = {
        "bbox": metadata["bbox"],
        "date_before": metadata["date_before"],
        "date_after": metadata["date_after"],
        "percent_changed": float(metadata["percent_changed"]),
        "image_ipfs_hash": image_hash
    }
    meta_response = requests.post("https://api.pinata.cloud/pinning/pinJSONToIPFS", json=metadata_json, headers=headers)
    if meta_response.status_code == 200:
        metadata_hash = meta_response.json()["IpfsHash"]
        print("Metadata uploaded to IPFS:", metadata_hash)
        return metadata_hash
    else:
        print("Metadata upload error:", meta_response.text)
        return None

# ==============================
# BLOCKCHAIN LOGGING
# ==============================
def log_deforestation_event(ipfs_hash, lat, lon, ndvi_change_percent):
    # Safety checks – skip if required keys are missing
    if not (w3 and contract and PRIVATE_KEY and ACCOUNT_ADDRESS):
        print("Blockchain keys or connection missing. Skipping on-chain logging.")
        return None

    timestamp = int(time.time())
    lat_e6 = int(lat * 1e6)
    lon_e6 = int(lon * 1e6)
    ndvi_scaled = int(ndvi_change_percent * 100)

    nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)
    txn = contract.functions.logEvent(ipfs_hash, lat_e6, lon_e6, timestamp, ndvi_scaled).build_transaction({
        "from": ACCOUNT_ADDRESS,
        "nonce": nonce,
        "gas": 300000,
        "gasPrice": w3.to_wei('30', 'gwei'),
        "chainId": 11155111
    })

    signed_txn = w3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)  # <-- updated for Web3.py v6+
    print("Transaction sent:", tx_hash.hex())

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction confirmed in block:", receipt.blockNumber)
    return receipt


# ==============================
# MAIN PIPELINE
# ==============================
def main_pipeline(bbox, date_before, date_after, threshold=0.2):
    print("=== Starting Pipeline ===")
    before = fetch_ndvi_bands(bbox, date_before)
    after = fetch_ndvi_bands(bbox, date_after)
    if before is None or after is None:
        print("ERROR: Could not fetch Sentinel data for both dates.")
        return {"error": "sentinel_missing_or_failed"}

    ndvi_before = compute_ndvi(before)
    ndvi_after = compute_ndvi(after)

    change_mask, percent_changed = detect_change(ndvi_before, ndvi_after, threshold)

    metadata = {
        "bbox": bbox,
        "date_before": date_before,
        "date_after": date_after,
        "percent_changed": percent_changed
    }

    ipfs_hash = upload_to_pinata(change_mask, metadata)

    if ipfs_hash:
        print("Logging event on blockchain...")
        lat_center = (bbox[1] + bbox[3]) / 2
        lon_center = (bbox[0] + bbox[2]) / 2
        receipt = log_deforestation_event(ipfs_hash, lat_center, lon_center, percent_changed)
        if receipt:
            print("Blockchain receipt:", receipt)

    return {
        "percent_changed": percent_changed,
        "ipfs_hash": ipfs_hash
    }

# ==============================
# RUN PIPELINE
# ==============================
if __name__ == "__main__":
    bbox = [25.0, 45.0, 25.05, 45.05]  # Replace with your AOI
    result = main_pipeline(bbox, "2025-09-01", "2025-09-15", threshold=0.3)
    print("\n=== FINAL RESULT ===")
    print(result)