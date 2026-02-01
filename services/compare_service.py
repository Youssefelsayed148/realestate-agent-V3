from typing import Dict, Any, List, Optional, Tuple

def _min_max(values: List[Optional[float]]) -> Tuple[Optional[float], Optional[float]]:
    nums = [v for v in values if isinstance(v, (int, float))]
    if not nums:
        return None, None
    return min(nums), max(nums)

def summarize_project(p: Dict[str, Any]) -> Dict[str, Any]:
    prices = [u.get("price") for u in p.get("unit_types", [])]
    areas = [u.get("area") for u in p.get("unit_types", [])]
    min_price, max_price = _min_max(prices)
    min_area, max_area = _min_max(areas)

    return {
        "id": p["id"],
        "name": p["project_name"],
        "location": p.get("area"),
        "min_price": min_price,
        "max_price": max_price,
        "min_area": min_area,
        "max_area": max_area,
        "unit_types_count": len(p.get("unit_types", [])),
    }

def compare_projects(projects: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Works for 2+ projects
    summaries = [summarize_project(p) for p in projects]

    diffs: Dict[str, str] = {}

    # Price comparison (lowest min_price wins if available)
    priced = [s for s in summaries if s["min_price"] is not None]
    if len(priced) >= 2:
        cheapest = min(priced, key=lambda x: x["min_price"])
        most_exp = max(priced, key=lambda x: x["min_price"])
        diffs["price"] = f"{cheapest['name']} starts cheaper, while {most_exp['name']} has a higher entry price."
    else:
        diffs["price"] = "Not enough pricing data to compare entry prices."

    # Size comparison (largest max_area)
    sized = [s for s in summaries if s["max_area"] is not None]
    if len(sized) >= 2:
        largest = max(sized, key=lambda x: x["max_area"])
        smallest = min(sized, key=lambda x: x["max_area"])
        diffs["unit_sizes"] = f"{largest['name']} offers larger max unit sizes than {smallest['name']}."
    else:
        diffs["unit_sizes"] = "Not enough area data to compare unit sizes."

    # Variety comparison (unit types count)
    if len(summaries) >= 2:
        most_variety = max(summaries, key=lambda x: x["unit_types_count"])
        least_variety = min(summaries, key=lambda x: x["unit_types_count"])
        diffs["variety"] = f"{most_variety['name']} lists more unit options than {least_variety['name']}."

    # Simple summary text
    names = ", ".join([s["name"] for s in summaries])
    summary = f"Comparison of: {names}. Key differences focus on price, unit sizes, and unit variety based on available data."

    return {"summary": summary, "differences": diffs, "summaries": summaries}
