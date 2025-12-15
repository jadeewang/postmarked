#!/usr/bin/env python3
"""
Test script for Postmarked backend pipeline.
Place your test images in a folder and run this script.
"""

import requests
import sys
import os
from pathlib import Path

API_BASE = "http://localhost:5001"

def test_pipeline(image_folder: str, location: str = "My Trip, 2025"):
    """Test the full pipeline with images from a folder."""
    
    # Get all images from folder
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    image_folder = Path(image_folder)
    
    if not image_folder.exists():
        print(f"❌ Folder not found: {image_folder}")
        return
    
    images = [f for f in image_folder.iterdir() 
              if f.suffix.lower() in image_extensions]
    
    if not images:
        print(f"❌ No images found in {image_folder}")
        print(f"   Looking for: {', '.join(image_extensions)}")
        return
    
    print(f"📸 Found {len(images)} images:")
    for img in images[:10]:  # Show first 10
        print(f"   - {img.name}")
    if len(images) > 10:
        print(f"   ... and {len(images) - 10} more")
    
    # Step 1: Health check
    print("\n🏥 Checking server health...")
    try:
        resp = requests.get(f"{API_BASE}/health")
        if resp.status_code != 200:
            print(f"❌ Server not healthy: {resp.text}")
            return
        print("✅ Server is healthy")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running on port 5001?")
        return
    
    # Step 2: Create session
    print("\n📝 Creating session...")
    resp = requests.post(f"{API_BASE}/api/session/create")
    session_id = resp.json().get("session_id")
    print(f"✅ Session created: {session_id[:8]}...")
    
    # Step 3: Upload images
    print(f"\n📤 Uploading {len(images)} images...")
    files = [("files", (img.name, open(img, "rb"), f"image/{img.suffix[1:]}")) 
             for img in images]
    
    resp = requests.post(
        f"{API_BASE}/api/upload",
        data={"session_id": session_id},
        files=files
    )
    
    # Close file handles
    for _, (_, f, _) in files:
        f.close()
    
    result = resp.json()
    if not result.get("success"):
        print(f"❌ Upload failed: {result.get('error')}")
        return
    print(f"✅ Uploaded {result.get('uploaded_count')} images")
    
    # Step 4: Analyze images
    print("\n🔍 Analyzing images with GPT-4 Vision...")
    print("   (This may take a minute...)")
    resp = requests.post(
        f"{API_BASE}/api/analyze",
        json={"session_id": session_id}
    )
    result = resp.json()
    
    if not result.get("success"):
        print(f"❌ Analysis failed: {result.get('error')}")
        print(f"   Full response: {result}")
        return
    
    print(f"✅ Analyzed {result.get('successful')}/{result.get('total_analyzed')} images")
    
    # Show some analysis highlights
    for analysis in result.get("analyses", [])[:2]:
        if analysis.get("success"):
            a = analysis.get("analysis", {})
            scene = a.get("scene_classification", {}).get("primary_category", "unknown")
            mood = a.get("mood_atmosphere", {}).get("overall_mood", "unknown")
            print(f"   📷 {analysis.get('filename')}: {scene}, {mood}")
    
    # Step 5: Aggregate
    print("\n📊 Aggregating album analysis...")
    resp = requests.post(
        f"{API_BASE}/api/aggregate",
        json={"session_id": session_id}
    )
    result = resp.json()
    
    if not result.get("success"):
        print(f"❌ Aggregation failed: {result.get('error')}")
        return
    
    agg = result.get("aggregation", {})
    print(f"✅ Album Summary:")
    print(f"   🏞️  Dominant scene: {agg.get('scene_summary', {}).get('dominant_scene_type', 'mixed')}")
    print(f"   😊 Dominant mood: {agg.get('mood_summary', {}).get('dominant_mood', 'varied')}")
    print(f"   🎨 Top colors: {[c['color'] for c in agg.get('visual_summary', {}).get('color_palette', {}).get('top_colors', [])[:3]]}")
    
    # Step 6: Generate postcard
    print("\n🎨 Generating postcard...")
    print("   (Image generation takes ~30 seconds...)")
    resp = requests.post(
        f"{API_BASE}/api/generate",
        json={
            "session_id": session_id,
            "location_label": location,
            "art_style": "vintage_postcard",
            "caption_tone": "artistic"
        }
    )
    result = resp.json()
    
    if not result.get("success"):
        print(f"❌ Generation failed: {result}")
        return
    
    postcard = result.get("postcard", {})
    
    print("\n" + "=" * 50)
    print("🎉 POSTCARD GENERATED!")
    print("=" * 50)
    
    caption = postcard.get("caption", {})
    print(f"\n📍 Location: {caption.get('location_label', location)}")
    print(f"✉️  Caption: \"{caption.get('caption', 'Wish you were here.')}\"")
    
    image = postcard.get("image", {})
    if image.get("image_url"):
        print(f"\n🖼️  Image URL (valid for ~1 hour):")
        print(f"   {image.get('image_url')}")
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=" * 50)
        print("Postmarked Backend Test")
        print("=" * 50)
        print("\nUsage:")
        print("  python test_pipeline.py <image_folder> [location_label]")
        print("\nExamples:")
        print("  python test_pipeline.py ./my_trip_photos")
        print('  python test_pipeline.py ./lisbon_pics "Lisbon, Fall 2025"')
        print("\nMake sure the server is running:")
        print("  ./venv/bin/python app.py")
        sys.exit(1)
    
    folder = sys.argv[1]
    location = sys.argv[2] if len(sys.argv) > 2 else "My Trip, 2025"
    
    test_pipeline(folder, location)

