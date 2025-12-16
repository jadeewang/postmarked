"""
Postmarked Backend API

A Flask application that powers the Postmarked digital postcard generator.
This API handles:
1. Photo album upload and analysis
2. Album-level aggregation
3. Postcard image and caption generation
"""

import os
import io
import uuid
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

from services.image_analysis import analyze_single_image, analyze_image_batch
from services.aggregation import aggregate_album_analysis
from services.generation import (
    generate_postcard_image,
    generate_postcard_caption,
    generate_complete_postcard
)

# Load environment variables from .env file in the same directory as this script
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Initialize Flask app with static files
app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)  # Enable CORS for frontend

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Valid style options
VALID_ART_STYLES = ['watercolor_illustration', 'vintage_postcard', 'collage', 'graphic_line_art']
VALID_CAPTION_TONES = ['satirical', 'artistic', 'dramatic', 'minimalist']

# In-memory session storage (for simplicity - in production use Redis/DB)
sessions = {}


def get_openai_client():
    """Get OpenAI client instance."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_image_format(filename):
    """Get image format from filename."""
    ext = filename.rsplit('.', 1)[1].lower()
    if ext == 'jpg':
        return 'jpeg'
    return ext


@app.route('/')
def serve_frontend():
    """Serve the frontend."""
    return app.send_static_file('index.html')


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "postmarked-backend",
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/api/session/create', methods=['POST'])
def create_session():
    """Create a new session for the postcard creation workflow."""
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "created_at": datetime.utcnow().isoformat(),
        "status": "created",
        "images": [],
        "analyses": [],
        "aggregation": None,
        "postcard": None
    }
    return jsonify({
        "success": True,
        "session_id": session_id
    })


@app.route('/api/session/<session_id>/status', methods=['GET'])
def get_session_status(session_id):
    """Get the current status of a session."""
    if session_id not in sessions:
        return jsonify({"success": False, "error": "Session not found"}), 404
    
    session = sessions[session_id]
    return jsonify({
        "success": True,
        "session_id": session_id,
        "status": session["status"],
        "image_count": len(session["images"]),
        "analyses_count": len(session["analyses"]),
        "has_aggregation": session["aggregation"] is not None,
        "has_postcard": session["postcard"] is not None
    })


@app.route('/api/upload', methods=['POST'])
def upload_photos():
    """
    Upload photos for analysis.
    
    Expects:
    - session_id: Session identifier
    - files: Multiple image files
    
    Returns:
    - Image count and upload status
    """
    session_id = request.form.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({"success": False, "error": "Invalid or missing session_id"}), 400
    
    if 'files' not in request.files:
        return jsonify({"success": False, "error": "No files provided"}), 400
    
    files = request.files.getlist('files')
    
    if len(files) < 1:
        return jsonify({"success": False, "error": "At least 1 image is required"}), 400
    
    if len(files) > 3:
        return jsonify({"success": False, "error": "Maximum 3 images allowed (to manage API costs)"}), 400
    
    session = sessions[session_id]
    uploaded_count = 0
    errors = []
    
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            try:
                # Read image data
                image_data = file.read()
                image_format = get_image_format(file.filename)
                
                # Validate it's a real image
                img = Image.open(io.BytesIO(image_data))
                img.verify()
                
                # Store image data
                session["images"].append({
                    "filename": secure_filename(file.filename),
                    "format": image_format,
                    "data": image_data,
                    "size": len(image_data)
                })
                uploaded_count += 1
                
            except Exception as e:
                errors.append(f"Error processing {file.filename}: {str(e)}")
        else:
            if file.filename:
                errors.append(f"Invalid file type: {file.filename}")
    
    session["status"] = "images_uploaded"
    
    return jsonify({
        "success": uploaded_count > 0,
        "uploaded_count": uploaded_count,
        "total_images": len(session["images"]),
        "errors": errors if errors else None
    })


@app.route('/api/analyze', methods=['POST'])
def analyze_photos():
    """
    Analyze all uploaded photos in a session.
    
    Expects:
    - session_id: Session identifier
    
    Returns:
    - Analysis results for each image
    """
    data = request.get_json()
    session_id = data.get('session_id') if data else None
    
    if not session_id or session_id not in sessions:
        return jsonify({"success": False, "error": "Invalid or missing session_id"}), 400
    
    session = sessions[session_id]
    
    if not session["images"]:
        return jsonify({"success": False, "error": "No images uploaded"}), 400
    
    try:
        client = get_openai_client()
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
    # Analyze each image
    session["status"] = "analyzing"
    analyses = []
    
    for idx, img_data in enumerate(session["images"]):
        print(f"Analyzing image {idx + 1}/{len(session['images'])}: {img_data['filename']}")
        
        result = analyze_single_image(
            client,
            img_data["data"],
            img_data["format"]
        )
        result["image_index"] = idx
        result["filename"] = img_data["filename"]
        analyses.append(result)
    
    session["analyses"] = analyses
    session["status"] = "analyzed"
    
    # Count successes and failures
    successful = sum(1 for a in analyses if a.get("success"))
    failed = len(analyses) - successful
    
    return jsonify({
        "success": successful > 0,
        "total_analyzed": len(analyses),
        "successful": successful,
        "failed": failed,
        "analyses": analyses
    })


@app.route('/api/aggregate', methods=['POST'])
def aggregate_analysis():
    """
    Aggregate analysis results from all images.
    
    Expects:
    - session_id: Session identifier
    
    Returns:
    - Aggregated album-level summary
    """
    data = request.get_json()
    session_id = data.get('session_id') if data else None
    
    if not session_id or session_id not in sessions:
        return jsonify({"success": False, "error": "Invalid or missing session_id"}), 400
    
    session = sessions[session_id]
    
    if not session["analyses"]:
        return jsonify({"success": False, "error": "No analyses available. Run /api/analyze first."}), 400
    
    # Perform aggregation
    aggregation_result = aggregate_album_analysis(session["analyses"])
    
    session["aggregation"] = aggregation_result
    session["status"] = "aggregated"
    
    return jsonify({
        "success": aggregation_result.get("success", False),
        "aggregation": aggregation_result
    })


@app.route('/api/generate', methods=['POST'])
def generate_postcard():
    """
    Generate the final postcard image and caption.
    
    Expects:
    - session_id: Session identifier
    - location_label: User-provided location (e.g., "Lisbon, Fall 2025")
    - art_style: One of: watercolor_illustration, vintage_postcard, collage, graphic_line_art
    - caption_tone: One of: satirical, artistic, dramatic, minimalist
    - user_description: (Optional) User's description of the trip
    
    Returns:
    - Generated postcard with image URL and caption
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400
    
    session_id = data.get('session_id')
    location_label = data.get('location_label')
    art_style = data.get('art_style')
    caption_tone = data.get('caption_tone')
    user_description = data.get('user_description')  # Optional
    
    # Validate inputs
    if not session_id or session_id not in sessions:
        return jsonify({"success": False, "error": "Invalid or missing session_id"}), 400
    
    if not location_label:
        return jsonify({"success": False, "error": "location_label is required"}), 400
    
    if art_style not in VALID_ART_STYLES:
        return jsonify({
            "success": False,
            "error": f"Invalid art_style. Must be one of: {VALID_ART_STYLES}"
        }), 400
    
    if caption_tone not in VALID_CAPTION_TONES:
        return jsonify({
            "success": False,
            "error": f"Invalid caption_tone. Must be one of: {VALID_CAPTION_TONES}"
        }), 400
    
    session = sessions[session_id]
    
    if not session["aggregation"]:
        return jsonify({
            "success": False,
            "error": "No aggregation available. Run /api/aggregate first."
        }), 400
    
    if not session["aggregation"].get("success"):
        return jsonify({
            "success": False,
            "error": "Aggregation was not successful. Cannot generate postcard."
        }), 400
    
    try:
        client = get_openai_client()
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
    session["status"] = "generating"
    
    # Get synthesis data from aggregation
    synthesis_data = session["aggregation"].get("synthesis_prompt_data", {})
    
    # Generate complete postcard
    postcard_result = generate_complete_postcard(
        client=client,
        synthesis_data=synthesis_data,
        location_label=location_label,
        art_style=art_style,
        caption_tone=caption_tone,
        user_description=user_description
    )
    
    session["postcard"] = postcard_result
    session["status"] = "completed" if postcard_result.get("success") else "generation_failed"
    
    return jsonify({
        "success": postcard_result.get("success", False),
        "postcard": postcard_result
    })


@app.route('/api/regenerate', methods=['POST'])
def regenerate_postcard():
    """
    Regenerate postcard with different style options.
    Uses the existing aggregation data.
    
    Expects:
    - session_id: Session identifier
    - location_label: User-provided location
    - art_style: Art style for the image
    - caption_tone: Tone for the caption
    - user_description: (Optional) User's description
    - regenerate_image: (Optional) Whether to regenerate image (default: true)
    - regenerate_caption: (Optional) Whether to regenerate caption (default: true)
    
    Returns:
    - Regenerated postcard
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400
    
    session_id = data.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({"success": False, "error": "Invalid or missing session_id"}), 400
    
    session = sessions[session_id]
    
    if not session["aggregation"] or not session["aggregation"].get("success"):
        return jsonify({
            "success": False,
            "error": "No valid aggregation available."
        }), 400
    
    # Use existing parameters if not provided
    existing = session.get("postcard", {}).get("input_parameters", {})
    
    location_label = data.get('location_label', existing.get('location_label'))
    art_style = data.get('art_style', existing.get('art_style'))
    caption_tone = data.get('caption_tone', existing.get('caption_tone'))
    user_description = data.get('user_description', existing.get('user_description'))
    
    regenerate_image = data.get('regenerate_image', True)
    regenerate_caption = data.get('regenerate_caption', True)
    
    # Validate
    if not location_label:
        return jsonify({"success": False, "error": "location_label is required"}), 400
    
    if art_style not in VALID_ART_STYLES:
        return jsonify({
            "success": False,
            "error": f"Invalid art_style. Must be one of: {VALID_ART_STYLES}"
        }), 400
    
    if caption_tone not in VALID_CAPTION_TONES:
        return jsonify({
            "success": False,
            "error": f"Invalid caption_tone. Must be one of: {VALID_CAPTION_TONES}"
        }), 400
    
    try:
        client = get_openai_client()
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
    synthesis_data = session["aggregation"].get("synthesis_prompt_data", {})
    
    result = {
        "success": True,
        "image": session.get("postcard", {}).get("image"),
        "caption": session.get("postcard", {}).get("caption"),
        "input_parameters": {
            "location_label": location_label,
            "art_style": art_style,
            "caption_tone": caption_tone,
            "user_description": user_description
        }
    }
    
    # Regenerate image if requested
    if regenerate_image:
        from services.generation import generate_postcard_image
        image_result = generate_postcard_image(
            client, synthesis_data, location_label, art_style, user_description
        )
        result["image"] = image_result
        if not image_result.get("success"):
            result["success"] = False
    
    # Regenerate caption if requested
    if regenerate_caption:
        from services.generation import generate_postcard_caption
        caption_result = generate_postcard_caption(
            client, synthesis_data, location_label, caption_tone, user_description
        )
        result["caption"] = caption_result
        if not caption_result.get("success"):
            result["success"] = False
    
    session["postcard"] = result
    session["status"] = "completed" if result["success"] else "regeneration_failed"
    
    return jsonify({
        "success": result["success"],
        "postcard": result
    })


@app.route('/api/pipeline', methods=['POST'])
def full_pipeline():
    """
    Run the complete postcard generation pipeline in one request.
    This is a convenience endpoint that combines upload, analyze, aggregate, and generate.
    
    Expects:
    - files: Multiple image files
    - location_label: User-provided location
    - art_style: Art style for the image
    - caption_tone: Tone for the caption
    - user_description: (Optional) User's description
    
    Returns:
    - Complete postcard with all intermediate results
    """
    # Validate required fields
    location_label = request.form.get('location_label')
    art_style = request.form.get('art_style')
    caption_tone = request.form.get('caption_tone')
    user_description = request.form.get('user_description')
    
    if not location_label:
        return jsonify({"success": False, "error": "location_label is required"}), 400
    
    if art_style not in VALID_ART_STYLES:
        return jsonify({
            "success": False,
            "error": f"Invalid art_style. Must be one of: {VALID_ART_STYLES}"
        }), 400
    
    if caption_tone not in VALID_CAPTION_TONES:
        return jsonify({
            "success": False,
            "error": f"Invalid caption_tone. Must be one of: {VALID_CAPTION_TONES}"
        }), 400
    
    if 'files' not in request.files:
        return jsonify({"success": False, "error": "No files provided"}), 400
    
    files = request.files.getlist('files')
    
    if len(files) < 1:
        return jsonify({"success": False, "error": "At least 1 image is required"}), 400
    
    if len(files) > 3:
        return jsonify({"success": False, "error": "Maximum 3 images allowed (to manage API costs)"}), 400
    
    try:
        client = get_openai_client()
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
    # Create session
    session_id = str(uuid.uuid4())
    
    # Process images
    images = []
    upload_errors = []
    
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            try:
                image_data = file.read()
                image_format = get_image_format(file.filename)
                
                img = Image.open(io.BytesIO(image_data))
                img.verify()
                
                images.append({
                    "filename": secure_filename(file.filename),
                    "format": image_format,
                    "data": image_data
                })
            except Exception as e:
                upload_errors.append(f"Error processing {file.filename}: {str(e)}")
    
    if not images:
        return jsonify({
            "success": False,
            "error": "No valid images uploaded",
            "upload_errors": upload_errors
        }), 400
    
    # Analyze images
    print(f"Starting analysis of {len(images)} images...")
    analyses = []
    for idx, img in enumerate(images):
        print(f"Analyzing image {idx + 1}/{len(images)}: {img['filename']}")
        result = analyze_single_image(client, img["data"], img["format"])
        result["image_index"] = idx
        result["filename"] = img["filename"]
        analyses.append(result)
    
    successful_analyses = sum(1 for a in analyses if a.get("success"))
    if successful_analyses == 0:
        return jsonify({
            "success": False,
            "error": "All image analyses failed",
            "analyses": analyses
        }), 500
    
    # Aggregate
    print("Aggregating analysis results...")
    aggregation = aggregate_album_analysis(analyses)
    
    if not aggregation.get("success"):
        return jsonify({
            "success": False,
            "error": "Aggregation failed",
            "aggregation": aggregation
        }), 500
    
    # Generate postcard
    print("Generating postcard...")
    synthesis_data = aggregation.get("synthesis_prompt_data", {})
    postcard = generate_complete_postcard(
        client=client,
        synthesis_data=synthesis_data,
        location_label=location_label,
        art_style=art_style,
        caption_tone=caption_tone,
        user_description=user_description
    )
    
    # Store session
    sessions[session_id] = {
        "created_at": datetime.utcnow().isoformat(),
        "status": "completed" if postcard.get("success") else "generation_failed",
        "images": [{"filename": img["filename"], "format": img["format"]} for img in images],
        "analyses": analyses,
        "aggregation": aggregation,
        "postcard": postcard
    }
    
    return jsonify({
        "success": postcard.get("success", False),
        "session_id": session_id,
        "pipeline_summary": {
            "images_uploaded": len(images),
            "images_analyzed": len(analyses),
            "successful_analyses": successful_analyses,
            "upload_errors": upload_errors if upload_errors else None
        },
        "aggregation_summary": {
            "total_images": aggregation.get("total_images_analyzed"),
            "dominant_scene": aggregation.get("scene_summary", {}).get("dominant_scene_type"),
            "dominant_mood": aggregation.get("mood_summary", {}).get("dominant_mood"),
            "top_colors": [c["color"] for c in aggregation.get("visual_summary", {}).get("color_palette", {}).get("top_colors", [])[:5]]
        },
        "postcard": postcard
    })


@app.route('/api/styles', methods=['GET'])
def get_style_options():
    """Get available style options for postcard generation."""
    return jsonify({
        "art_styles": [
            {"value": "watercolor_illustration", "label": "Watercolor Illustration", "description": "Soft, flowing watercolor painting style"},
            {"value": "vintage_postcard", "label": "Vintage Postcard", "description": "Retro 1950s travel poster aesthetic"},
            {"value": "collage", "label": "Collage", "description": "Layered paper cutout mixed media style"},
            {"value": "graphic_line_art", "label": "Graphic Line Art", "description": "Bold outlines with flat colors"}
        ],
        "caption_tones": [
            {"value": "satirical", "label": "Satirical", "description": "Witty and self-aware humor"},
            {"value": "artistic", "label": "Artistic", "description": "Poetic and evocative"},
            {"value": "dramatic", "label": "Dramatic", "description": "Bold and cinematic"},
            {"value": "minimalist", "label": "Minimalist", "description": "Brief and understated"}
        ]
    })


if __name__ == '__main__':
    print("=" * 50)
    print("Postmarked Backend Server")
    print("=" * 50)
    print("\nAvailable endpoints:")
    print("  GET  /health              - Health check")
    print("  GET  /api/styles          - Get style options")
    print("  POST /api/session/create  - Create new session")
    print("  GET  /api/session/<id>/status - Get session status")
    print("  POST /api/upload          - Upload photos")
    print("  POST /api/analyze         - Analyze photos")
    print("  POST /api/aggregate       - Aggregate analysis")
    print("  POST /api/generate        - Generate postcard")
    print("  POST /api/regenerate      - Regenerate with new options")
    print("  POST /api/pipeline        - Full pipeline in one request")
    print("\nMake sure OPENAI_API_KEY is set in your environment or .env file")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5001)

