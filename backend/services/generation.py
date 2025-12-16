"""
Postcard Generation Service for Postmarked

This service handles the multimodal synthesis step:
- Generates a postcard image using DALL-E based on aggregated album analysis
- Generates a caption using GPT-4 based on the same aggregated data
- Applies user-selected style preferences
"""

import json
from openai import OpenAI


# Art style prompts for DALL-E
ART_STYLE_PROMPTS = {
    "watercolor_illustration": "watercolor illustration style, soft edges, flowing colors, artistic brushstrokes, paper texture, hand-painted aesthetic",
    "vintage_postcard": "vintage postcard style, retro illustration, 1950s travel poster aesthetic, slightly faded colors, nostalgic feel, classic typography-ready composition",
    "collage": "artistic collage style, layered paper cutouts, mixed media aesthetic, overlapping elements, textured surfaces, creative composition",
    "graphic_line_art": "graphic line art style, bold outlines, clean vector-like illustration, minimal shading, modern graphic design aesthetic, flat colors with strong contrast"
}

# Caption tone instructions
CAPTION_TONES = {
    "satirical": "Write in a satirical, witty tone that gently pokes fun at travel clichés while still being affectionate. Use irony and self-aware humor.",
    "artistic": "Write in an artistic, poetic tone that evokes imagery and emotion. Use metaphor and sensory language. Be evocative but not pretentious.",
    "dramatic": "Write in a dramatic, cinematic tone that makes the ordinary feel epic. Use bold statements and emotional weight.",
    "minimalist": "Write in a minimalist, understated tone. Be brief, subtle, and let silence speak. Use few words with maximum impact."
}


def generate_postcard_image(
    client: OpenAI,
    synthesis_data: dict,
    location_label: str,
    art_style: str,
    user_description: str = None
) -> dict:
    """
    Generate a postcard image using DALL-E 3 based on aggregated album analysis.
    
    Args:
        client: OpenAI client instance
        synthesis_data: The synthesis_prompt_data from aggregation
        location_label: User-provided location (e.g., "Lisbon, Fall 2025")
        art_style: One of: watercolor_illustration, vintage_postcard, collage, graphic_line_art
        user_description: Optional user description of the trip
    
    Returns:
        Dictionary containing the generated image URL and metadata
    """
    
    # Build the image generation prompt
    style_prompt = ART_STYLE_PROMPTS.get(art_style, ART_STYLE_PROMPTS["vintage_postcard"])
    
    # Extract key elements from synthesis data
    primary_scene = synthesis_data.get("primary_scene_type", "travel scene")
    secondary_scenes = synthesis_data.get("secondary_scene_types", [])
    dominant_elements = synthesis_data.get("dominant_visual_elements", [])
    colors = synthesis_data.get("color_palette", ["vibrant colors"])
    mood = synthesis_data.get("dominant_mood", "adventurous")
    mood_descriptors = synthesis_data.get("mood_descriptors", [])
    recurring_elements = synthesis_data.get("recurring_notable_elements", [])
    lighting = synthesis_data.get("lighting_style", "natural light")
    setting = synthesis_data.get("setting", "outdoor")
    time_of_day = synthesis_data.get("time_of_day", "daytime")
    color_temp = synthesis_data.get("color_temperature", "warm")
    
    # Build descriptive elements
    scene_description = primary_scene
    if secondary_scenes:
        scene_description += f" with hints of {', '.join(secondary_scenes[:2])}"
    
    element_list = dominant_elements[:4] if dominant_elements else ["architectural details"]
    color_list = colors[:4] if colors else ["warm tones"]
    
    # Construct the DALL-E prompt
    prompt_parts = [
        f"A stylized postcard illustration of {location_label}.",
        f"The scene captures a {scene_description}.",
        f"Key visual elements include: {', '.join(element_list)}.",
        f"Color palette features {', '.join(color_list)} with {color_temp} tones.",
        f"The mood is {mood}",
    ]
    
    if mood_descriptors:
        prompt_parts.append(f"with an atmosphere that feels {', '.join(mood_descriptors[:3])}")
    
    prompt_parts.append(f"Lighting: {lighting}, {time_of_day}.")
    
    if recurring_elements:
        prompt_parts.append(f"Include symbolic references to: {', '.join(recurring_elements[:4])}.")
    
    if user_description:
        prompt_parts.append(f"Trip essence: {user_description}")
    
    prompt_parts.append(f"Art style: {style_prompt}.")
    prompt_parts.append("This should look like a beautiful, professional travel postcard that summarizes a personal journey, NOT a generic tourist image. Symbolic and artistic, not photorealistic.")
    
    full_prompt = " ".join(prompt_parts)
    
    try:
        print("Starting DALL-E image generation...")
        response = client.images.generate(
            model="dall-e-3",
            prompt=full_prompt,
            size="1024x1024",  # DALL-E 3 only supports 1024x1024, 1024x1792, 1792x1024
            quality="standard",
            n=1
        )
        print("Image generation complete!")
        
        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt
        
        return {
            "success": True,
            "image_url": image_url,
            "original_prompt": full_prompt,
            "revised_prompt": revised_prompt,
            "art_style": art_style
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Image generation failed: {str(e)}",
            "original_prompt": full_prompt
        }


def generate_postcard_caption(
    client: OpenAI,
    synthesis_data: dict,
    location_label: str,
    caption_tone: str,
    user_description: str = None
) -> dict:
    """
    Generate a postcard caption using GPT-4 based on aggregated album analysis.
    
    Args:
        client: OpenAI client instance
        synthesis_data: The synthesis_prompt_data from aggregation
        location_label: User-provided location
        caption_tone: One of: satirical, artistic, dramatic, minimalist
        user_description: Optional user description of the trip
    
    Returns:
        Dictionary containing the generated caption
    """
    
    tone_instruction = CAPTION_TONES.get(caption_tone, CAPTION_TONES["artistic"])
    
    # Build context from synthesis data
    context_parts = [
        f"Location: {location_label}",
        f"Primary scene type: {synthesis_data.get('primary_scene_type', 'travel')}",
        f"Dominant mood: {synthesis_data.get('dominant_mood', 'adventurous')}",
        f"Energy level: {synthesis_data.get('energy_level', 'medium')}",
        f"Key visual elements: {', '.join(synthesis_data.get('dominant_visual_elements', []))}",
        f"Color palette: {', '.join(synthesis_data.get('color_palette', [])[:4])}",
        f"Recurring notable elements: {', '.join(synthesis_data.get('recurring_notable_elements', [])[:5])}",
        f"Setting: mostly {synthesis_data.get('setting', 'outdoor')}",
        f"Mood descriptors: {', '.join(synthesis_data.get('mood_descriptors', [])[:4])}"
    ]
    
    if user_description:
        context_parts.append(f"User's trip description: {user_description}")
    
    context = "\n".join(context_parts)
    
    prompt = f"""You are creating the text for a travel postcard. Based on the following aggregated analysis of someone's personal travel photo album, generate:

1. A formatted location label (can be stylized based on the tone)
2. A single-line postcard caption (one sentence, like what you'd write on the back of a postcard)

ALBUM ANALYSIS:
{context}

TONE INSTRUCTION:
{tone_instruction}

The caption should:
- Reflect the actual experience captured in the photos, not generic tourism
- Match the specified tone
- Be personal and evocative
- Be concise (one sentence, max ~15 words for the caption)

Return your response as a JSON object:
{{
    "location_label": "<stylized location label>",
    "caption": "<one-line postcard caption>",
    "tone_applied": "<the tone you used>"
}}

Return ONLY the JSON object."""

    try:
        print("Generating caption...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a creative writer specializing in evocative, personal travel writing. You craft captions that capture lived experiences rather than tourist clichés."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=200,
            temperature=0.8  # Higher temperature for creative output
        )
        print("Caption generation complete!")
        
        response_text = response.choices[0].message.content.strip()
        
        # Clean up response if it has markdown code blocks
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        caption_data = json.loads(response_text)
        
        return {
            "success": True,
            "location_label": caption_data.get("location_label", location_label),
            "caption": caption_data.get("caption", "Wish you were here."),
            "tone_applied": caption_data.get("tone_applied", caption_tone)
        }
        
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse caption response: {str(e)}",
            "raw_response": response_text if 'response_text' in locals() else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Caption generation failed: {str(e)}"
        }


def generate_complete_postcard(
    client: OpenAI,
    synthesis_data: dict,
    location_label: str,
    art_style: str,
    caption_tone: str,
    user_description: str = None
) -> dict:
    """
    Generate a complete postcard with both image and caption.
    
    Args:
        client: OpenAI client instance
        synthesis_data: The synthesis_prompt_data from aggregation
        location_label: User-provided location
        art_style: Art style for the image
        caption_tone: Tone for the caption
        user_description: Optional user description
    
    Returns:
        Dictionary containing the complete postcard data
    """
    
    # Generate image
    image_result = generate_postcard_image(
        client, synthesis_data, location_label, art_style, user_description
    )
    
    # Generate caption
    caption_result = generate_postcard_caption(
        client, synthesis_data, location_label, caption_tone, user_description
    )
    
    return {
        "success": image_result.get("success") and caption_result.get("success"),
        "image": image_result,
        "caption": caption_result,
        "input_parameters": {
            "location_label": location_label,
            "art_style": art_style,
            "caption_tone": caption_tone,
            "user_description": user_description
        }
    }

