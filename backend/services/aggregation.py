"""
Album Aggregation Service for Postmarked

This service aggregates analysis results from multiple images to create
a unified summary of the travel album. It identifies:
- Most frequent scene types
- Most common segmented elements
- Average color palette
- Overall visual mood
- Dominant vs rare elements
"""

from collections import Counter, defaultdict
from typing import Any


def aggregate_album_analysis(image_analyses: list[dict]) -> dict:
    """
    Aggregate analysis results from multiple images into a unified album summary.
    
    Args:
        image_analyses: List of successful image analysis results
    
    Returns:
        Dictionary containing aggregated album-level insights
    """
    # Filter to only successful analyses
    valid_analyses = [
        a["analysis"] for a in image_analyses 
        if a.get("success") and a.get("analysis")
    ]
    
    if not valid_analyses:
        return {
            "success": False,
            "error": "No valid image analyses to aggregate"
        }
    
    total_images = len(valid_analyses)
    
    # Aggregate scene classifications
    scene_summary = _aggregate_scene_classifications(valid_analyses)
    
    # Aggregate segmented elements
    element_summary = _aggregate_segmented_elements(valid_analyses)
    
    # Aggregate visual features (colors, lighting, etc.)
    visual_summary = _aggregate_visual_features(valid_analyses)
    
    # Aggregate mood/atmosphere
    mood_summary = _aggregate_mood_atmosphere(valid_analyses)
    
    # Collect notable elements across all images
    notable_summary = _aggregate_notable_elements(valid_analyses)
    
    return {
        "success": True,
        "total_images_analyzed": total_images,
        "scene_summary": scene_summary,
        "element_summary": element_summary,
        "visual_summary": visual_summary,
        "mood_summary": mood_summary,
        "notable_elements": notable_summary,
        # Generate a structured prompt-ready summary
        "synthesis_prompt_data": _create_synthesis_prompt_data(
            scene_summary, element_summary, visual_summary, mood_summary, notable_summary
        )
    }


def _aggregate_scene_classifications(analyses: list[dict]) -> dict:
    """Aggregate scene classification data across all images."""
    primary_categories = Counter()
    all_categories = Counter()
    
    for analysis in analyses:
        scene = analysis.get("scene_classification", {})
        primary = scene.get("primary_category")
        if primary:
            primary_categories[primary] += 1
            all_categories[primary] += 1
        
        for secondary in scene.get("secondary_categories", []):
            all_categories[secondary] += 1
    
    total = len(analyses)
    
    # Calculate percentages and rank
    primary_ranked = [
        {"category": cat, "count": count, "percentage": round(count / total * 100, 1)}
        for cat, count in primary_categories.most_common()
    ]
    
    all_ranked = [
        {"category": cat, "count": count, "percentage": round(count / total * 100, 1)}
        for cat, count in all_categories.most_common()
    ]
    
    return {
        "primary_categories": primary_ranked,
        "all_categories": all_ranked,
        "dominant_scene_type": primary_ranked[0]["category"] if primary_ranked else "mixed",
        "scene_diversity": len(primary_categories)
    }


def _aggregate_segmented_elements(analyses: list[dict]) -> dict:
    """Aggregate segmented element data across all images."""
    element_presence = defaultdict(int)
    element_prominence_sum = defaultdict(float)
    people_count_total = 0
    people_images = 0
    
    elements_to_track = ["sky", "buildings", "water", "people", "vegetation", "food_drinks", "vehicles_transit"]
    
    for analysis in analyses:
        segments = analysis.get("segmented_elements", {})
        
        for element in elements_to_track:
            elem_data = segments.get(element, {})
            if elem_data.get("present"):
                element_presence[element] += 1
                prominence = elem_data.get("prominence", 0)
                element_prominence_sum[element] += prominence
                
                if element == "people":
                    count = elem_data.get("count", 0)
                    if count:
                        people_count_total += count
                        people_images += 1
    
    total = len(analyses)
    
    # Calculate presence rates and average prominence
    element_stats = {}
    for element in elements_to_track:
        presence = element_presence[element]
        element_stats[element] = {
            "presence_count": presence,
            "presence_rate": round(presence / total * 100, 1),
            "avg_prominence": round(element_prominence_sum[element] / presence, 2) if presence > 0 else 0
        }
    
    # Rank elements by presence
    ranked_elements = sorted(
        element_stats.items(),
        key=lambda x: (x[1]["presence_count"], x[1]["avg_prominence"]),
        reverse=True
    )
    
    dominant_elements = [elem for elem, stats in ranked_elements if stats["presence_rate"] >= 50]
    rare_elements = [elem for elem, stats in ranked_elements if 0 < stats["presence_rate"] < 20]
    
    return {
        "element_stats": element_stats,
        "ranked_by_presence": [{"element": e, **s} for e, s in ranked_elements],
        "dominant_elements": dominant_elements,
        "rare_elements": rare_elements,
        "people_presence": {
            "images_with_people": people_images,
            "avg_people_per_image": round(people_count_total / people_images, 1) if people_images > 0 else 0
        }
    }


def _aggregate_visual_features(analyses: list[dict]) -> dict:
    """Aggregate visual features (colors, lighting, etc.) across all images."""
    all_colors = []
    color_temperatures = Counter()
    lighting_conditions = Counter()
    indoor_outdoor = Counter()
    times_of_day = Counter()
    weather = Counter()
    
    for analysis in analyses:
        visual = analysis.get("visual_features", {})
        
        colors = visual.get("dominant_colors", [])
        all_colors.extend(colors)
        
        if temp := visual.get("color_temperature"):
            color_temperatures[temp] += 1
        if lighting := visual.get("lighting_condition"):
            lighting_conditions[lighting] += 1
        if io := visual.get("indoor_outdoor"):
            indoor_outdoor[io] += 1
        if tod := visual.get("time_of_day"):
            times_of_day[tod] += 1
        if w := visual.get("weather_apparent"):
            weather[w] += 1
    
    # Count and rank colors
    color_counts = Counter(all_colors)
    top_colors = [{"color": c, "count": n} for c, n in color_counts.most_common(8)]
    
    # Determine overall characteristics
    total = len(analyses)
    
    return {
        "color_palette": {
            "top_colors": top_colors,
            "unique_colors_mentioned": len(color_counts)
        },
        "color_temperature": {
            "distribution": dict(color_temperatures),
            "dominant": color_temperatures.most_common(1)[0][0] if color_temperatures else "mixed"
        },
        "lighting": {
            "distribution": dict(lighting_conditions),
            "dominant": lighting_conditions.most_common(1)[0][0] if lighting_conditions else "varied"
        },
        "setting": {
            "indoor_outdoor_distribution": dict(indoor_outdoor),
            "primary_setting": indoor_outdoor.most_common(1)[0][0] if indoor_outdoor else "mixed"
        },
        "time_of_day": {
            "distribution": dict(times_of_day),
            "most_common": times_of_day.most_common(1)[0][0] if times_of_day else "varied"
        },
        "weather": {
            "distribution": dict(weather),
            "most_common": weather.most_common(1)[0][0] if weather else "varied"
        }
    }


def _aggregate_mood_atmosphere(analyses: list[dict]) -> dict:
    """Aggregate mood and atmosphere data across all images."""
    moods = Counter()
    energy_levels = Counter()
    all_tags = []
    
    for analysis in analyses:
        mood_data = analysis.get("mood_atmosphere", {})
        
        if mood := mood_data.get("overall_mood"):
            moods[mood] += 1
        if energy := mood_data.get("energy_level"):
            energy_levels[energy] += 1
        
        tags = mood_data.get("descriptive_tags", [])
        all_tags.extend(tags)
    
    tag_counts = Counter(all_tags)
    
    return {
        "mood_distribution": dict(moods),
        "dominant_mood": moods.most_common(1)[0][0] if moods else "mixed",
        "secondary_moods": [m for m, _ in moods.most_common(3)[1:]] if len(moods) > 1 else [],
        "energy_distribution": dict(energy_levels),
        "overall_energy": energy_levels.most_common(1)[0][0] if energy_levels else "medium",
        "top_atmosphere_tags": [{"tag": t, "count": c} for t, c in tag_counts.most_common(10)],
        "mood_consistency": moods.most_common(1)[0][1] / len(analyses) if moods else 0
    }


def _aggregate_notable_elements(analyses: list[dict]) -> dict:
    """Aggregate notable elements across all images."""
    all_notable = []
    
    for analysis in analyses:
        notable = analysis.get("notable_elements", [])
        all_notable.extend(notable)
    
    # Count occurrences of notable elements
    notable_counts = Counter(all_notable)
    
    return {
        "all_notable_elements": [{"element": e, "count": c} for e, c in notable_counts.most_common(20)],
        "unique_notable_count": len(notable_counts),
        "recurring_elements": [e for e, c in notable_counts.items() if c >= 2]
    }


def _create_synthesis_prompt_data(
    scene_summary: dict,
    element_summary: dict,
    visual_summary: dict,
    mood_summary: dict,
    notable_summary: dict
) -> dict:
    """
    Create a structured data object optimized for generating prompts
    for image and caption synthesis.
    """
    # Extract key insights for prompt generation
    top_scene = scene_summary.get("dominant_scene_type", "travel scene")
    secondary_scenes = [
        cat["category"] for cat in scene_summary.get("primary_categories", [])[1:4]
    ]
    
    dominant_elements = element_summary.get("dominant_elements", [])
    
    colors = [c["color"] for c in visual_summary.get("color_palette", {}).get("top_colors", [])[:5]]
    
    dominant_mood = mood_summary.get("dominant_mood", "adventurous")
    secondary_moods = mood_summary.get("secondary_moods", [])
    top_tags = [t["tag"] for t in mood_summary.get("top_atmosphere_tags", [])[:5]]
    
    recurring = notable_summary.get("recurring_elements", [])[:10]
    
    return {
        "primary_scene_type": top_scene,
        "secondary_scene_types": secondary_scenes,
        "dominant_visual_elements": dominant_elements,
        "color_palette": colors,
        "color_temperature": visual_summary.get("color_temperature", {}).get("dominant", "mixed"),
        "lighting_style": visual_summary.get("lighting", {}).get("dominant", "natural"),
        "setting": visual_summary.get("setting", {}).get("primary_setting", "outdoor"),
        "time_of_day": visual_summary.get("time_of_day", {}).get("most_common", "daytime"),
        "dominant_mood": dominant_mood,
        "mood_descriptors": secondary_moods + top_tags,
        "energy_level": mood_summary.get("overall_energy", "medium"),
        "recurring_notable_elements": recurring,
        "has_people": element_summary.get("people_presence", {}).get("images_with_people", 0) > 0
    }

