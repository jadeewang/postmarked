"""
Image Analysis for Postmarked

This service handles per-image analysis using OpenAI's Vision API.
For each image, it extracts:
- Scene classification (architecture, food, people, streets, nature, interiors)
- Segmented elements (sky, buildings, water, people, foreground/background)
- Low-level features (dominant colors, lighting, indoor/outdoor, time of day)
"""

import base64
import json
from openai import OpenAI


# Analysis prompt for GPT-4 Vision
ANALYSIS_PROMPT = """Analyze this travel photo and return a JSON object with the following structure:

{
    "scene_classification": {
        "primary_category": "<one of: architecture, food, people, streets_transit, nature_coast, nature_forest, nature_mountains, nature_general, interiors, other>",
        "secondary_categories": ["<list of other applicable categories>"],
        "confidence": <0.0-1.0>
    },
    "segmented_elements": {
        "sky": {"present": <bool>, "prominence": <0.0-1.0, how much of image>},
        "buildings": {"present": <bool>, "prominence": <0.0-1.0>},
        "water": {"present": <bool>, "prominence": <0.0-1.0>},
        "people": {"present": <bool>, "count": <approximate number>, "prominence": <0.0-1.0>},
        "vegetation": {"present": <bool>, "prominence": <0.0-1.0>},
        "food_drinks": {"present": <bool>, "prominence": <0.0-1.0>},
        "vehicles_transit": {"present": <bool>, "prominence": <0.0-1.0>},
        "foreground_focus": "<description of main foreground subject>",
        "background_description": "<description of background>"
    },
    "visual_features": {
        "dominant_colors": ["<top 3-5 color names, e.g., 'warm terracotta', 'ocean blue'>"],
        "color_temperature": "<warm, cool, neutral, mixed>",
        "lighting_condition": "<bright_daylight, golden_hour, overcast, night, indoor_artificial, indoor_natural>",
        "indoor_outdoor": "<indoor, outdoor, mixed>",
        "time_of_day": "<morning, midday, afternoon, sunset, evening, night, unclear>",
        "weather_apparent": "<sunny, cloudy, rainy, foggy, unclear>"
    },
    "mood_atmosphere": {
        "overall_mood": "<one of: vibrant, serene, bustling, intimate, dramatic, playful, nostalgic, adventurous>",
        "energy_level": "<high, medium, low>",
        "descriptive_tags": ["<3-5 mood/atmosphere descriptors>"]
    },
    "notable_elements": ["<list of 3-5 distinctive visual elements or subjects in the image>"]
}

Be precise and consistent. Return ONLY the JSON object, no additional text."""


def encode_image_to_base64(image_data: bytes) -> str:
    """Encode image bytes to base64 string."""
    return base64.b64encode(image_data).decode('utf-8')


def analyze_single_image(client: OpenAI, image_data: bytes, image_format: str = "jpeg") -> dict:
    """
    Analyze a single image using GPT-4 Vision.
    
    Args:
        client: OpenAI client instance
        image_data: Raw image bytes
        image_format: Image format (jpeg, png, etc.)
    
    Returns:
        Dictionary containing structured analysis results
    """
    base64_image = encode_image_to_base64(image_data)
    
    try:
        print(f"Calling GPT-4 Vision...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": ANALYSIS_PROMPT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{image_format};base64,{base64_image}",
                                "detail": "low"  # Use low detail to save tokens, sufficient for analysis
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000,
            temperature=0.2  # Low temperature for consistent analysis
        )
        print(f"Vision analysis complete!")
        
        # Parse the JSON response
        response_text = response.choices[0].message.content.strip()
        
        # Clean up response if it has markdown code blocks
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        analysis = json.loads(response_text)
        return {
            "success": True,
            "analysis": analysis
        }
        
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse vision response as JSON: {str(e)}",
            "raw_response": response_text if 'response_text' in locals() else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Image analysis failed: {str(e)}"
        }


def analyze_image_batch(client: OpenAI, images: list[tuple[bytes, str]]) -> list[dict]:
    """
    Analyze multiple images.
    
    Args:
        client: OpenAI client instance
        images: List of tuples (image_data, image_format)
    
    Returns:
        List of analysis results for each image
    """
    results = []
    for idx, (image_data, image_format) in enumerate(images):
        print(f"Analyzing image {idx + 1}/{len(images)}...")
        result = analyze_single_image(client, image_data, image_format)
        result["image_index"] = idx
        results.append(result)
    
    return results

