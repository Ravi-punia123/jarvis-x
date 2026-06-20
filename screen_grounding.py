"""Screen grounding maps natural language targets to screen coordinates."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from vision import VisionManager


class ScreenGrounder:
    """Ground natural language UI targets to likely clickable coordinates."""

    def __init__(self, vision: Optional[VisionManager] = None):
        self.vision = vision or VisionManager()

    def ground(
        self,
        target: str,
        image_path: str = "",
        analysis: Optional[Dict[str, Any]] = None,
        active_window: str = "",
        min_confidence: float = 0.35,
    ) -> Dict[str, Any]:
        query = (target or "").strip()
        if not query:
            return {"success": False, "error": "Target is required"}

        if analysis is None:
            if image_path:
                analysis_result = self.vision.analyze_image(image_path, context="screen grounding")
            else:
                capture = self.vision.capture()
                if not capture.get("success"):
                    return {"success": False, "error": capture.get("error", "Capture failed")}
                analysis_result = self.vision.analyze(capture.get("path", ""))
            if not analysis_result.get("success"):
                return {"success": False, "error": analysis_result.get("error", "Analysis failed")}
            structured = analysis_result.get("data", {})
        else:
            structured = analysis

        candidates = self._ranked_candidates(query, structured, active_window=active_window)
        candidate = candidates[0] if candidates else None
        if not candidate:
            return {
                "success": False,
                "error": "No matching element found",
                "target": query,
            }

        if float(candidate.get("score", 0.0)) < float(min_confidence):
            return {
                "success": False,
                "error": "Best match below confidence threshold",
                "target": query,
                "best_score": candidate.get("score", 0.0),
                "threshold": min_confidence,
                "matches": candidates[:3],
            }

        center = self._center_from_bbox(candidate.get("bbox") or candidate.get("bounding_box"))
        return {
            "success": True,
            "target": query,
            "confidence": candidate.get("score", 0.0),
            "element_type": candidate.get("element_type", "unknown"),
            "label": candidate.get("label", ""),
            "bbox": candidate.get("bbox") or candidate.get("bounding_box"),
            "coordinates": center,
            "matches": candidates[:3],
        }

    def ground_all(self, target: str, analysis: Dict[str, Any], limit: int = 5, active_window: str = "") -> Dict[str, Any]:
        query = (target or "").strip()
        if not query:
            return {"success": False, "error": "Target is required"}
        ranked = self._ranked_candidates(query, analysis, active_window=active_window)
        return {"success": bool(ranked), "target": query, "matches": ranked[: max(1, int(limit))]}

    def _ranked_candidates(self, query: str, structured: Dict[str, Any], active_window: str = "") -> List[Dict[str, Any]]:
        elements: List[Dict[str, Any]] = []

        for window in structured.get("window_titles", []) or []:
            label = str(window.get("title", ""))
            elements.append(
                {
                    "element_type": "window",
                    "label": label,
                    "bbox": window.get("bbox") or window.get("bounding_box"),
                }
            )

        for button in structured.get("buttons", []) or []:
            if isinstance(button, dict):
                label = str(button.get("label", button.get("text", "")))
                bbox = button.get("bbox") or button.get("bounding_box")
            else:
                label = str(button)
                bbox = None
            elements.append({"element_type": "button", "label": label, "bbox": bbox})

        for region in structured.get("text_regions", []) or []:
            if isinstance(region, dict):
                label = str(region.get("text", ""))
                bbox = region.get("bbox") or region.get("bounding_box")
            else:
                label = str(region)
                bbox = None
            elements.append({"element_type": "text", "label": label, "bbox": bbox})

        for ui in structured.get("ui_elements", []) or []:
            if isinstance(ui, dict):
                label = str(ui.get("label", ui.get("description", "")))
                bbox = ui.get("bbox") or ui.get("bounding_box")
                element_type = str(ui.get("type", "ui_element"))
            else:
                label = str(ui)
                bbox = None
                element_type = "ui_element"
            elements.append({"element_type": element_type, "label": label, "bbox": bbox})

        scored: List[Dict[str, Any]] = []
        query_lower = query.lower()
        active_window_lower = active_window.lower().strip()

        for element in elements:
            label = str(element.get("label", "")).strip()
            if not label:
                continue
            label_lower = label.lower()
            score = SequenceMatcher(None, query_lower, label_lower).ratio()
            if query_lower in label_lower:
                score = max(score, 0.85)
            # Prefer matches that mention active window title context.
            if active_window_lower and active_window_lower in label_lower:
                score = min(1.0, score + 0.08)
            scored.append({**element, "score": round(float(score), 3)})

        return sorted(scored, key=lambda item: float(item.get("score", 0.0)), reverse=True)

    def _center_from_bbox(self, bbox: Any) -> Dict[str, int]:
        if isinstance(bbox, dict):
            left = int(bbox.get("left", bbox.get("x", 0)))
            top = int(bbox.get("top", bbox.get("y", 0)))
            width = int(bbox.get("width", 0))
            height = int(bbox.get("height", 0))
            return {"x": left + max(1, width) // 2, "y": top + max(1, height) // 2}

        if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
            left, top, width, height = [int(v) for v in bbox[:4]]
            return {"x": left + max(1, width) // 2, "y": top + max(1, height) // 2}

        return {"x": 0, "y": 0}
