import subprocess
from pathlib import Path

VIDEO_URL = (
    "https://dandiarchive.s3.amazonaws.com/blobs/"
    "a3e/fe8/a3efe8c5-0d2e-4be7-bdb1-3f0a32cbb62d"
)

START_TIME = 100
DURATION = 10

OUTPUT_DIR = Path("data/sample")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "body_100_110.mp4"

command = [
    "ffmpeg",
    "-ss", str(START_TIME),
    "-i", VIDEO_URL,
    "-t", str(DURATION),
    "-c:v", "libx264",
    "-an",
    "-y",
    str(OUTPUT_FILE),
]

print("Extracting video clip...")
print(f"Time: {START_TIME}–{START_TIME + DURATION} seconds")
print(f"Output: {OUTPUT_FILE}")

subprocess.run(command, check=True)

print("\nDone!")
print(f"Created: {OUTPUT_FILE}")