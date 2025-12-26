"""Vision and camera intent detector."""

from typing import Dict, List, Optional
from .base import BaseDetector
from ..models import ToolIntent
from ..constants import ToolPriority


class VisionDetector(BaseDetector):
    """Detects camera, image viewing, and recognition intents."""

    def detect(self, message: str, msg_lower: str, context: Dict) -> List[ToolIntent]:
        intents = []

        camera_intent = self._detect_camera_intent(msg_lower, context)
        if camera_intent:
            intents.append(camera_intent)

        view_intent = self._detect_view_image_intent(msg_lower, context)
        if view_intent:
            intents.append(view_intent)

        recognition_intent = self._detect_recognition_intent(msg_lower, context)
        if recognition_intent:
            intents.append(recognition_intent)

        return intents

    def _detect_camera_intent(self, msg_lower: str, context: Dict) -> Optional[ToolIntent]:
        strong_signals = [
            'take a picture', 'take a photo', 'capture image', 'camera capture',
            'snap a photo', 'take screenshot', 'get an image'
        ]
        camera_keywords = ['camera', 'picture', 'photo', 'image', 'snapshot', 'capture']
        action_verbs = ['take', 'capture', 'snap', 'get', 'grab']

        confidence = 0.0
        reasons = []

        if any(s in msg_lower for s in strong_signals):
            confidence = 0.95
            reasons.append("explicit camera keywords")
        elif any(v in msg_lower for v in action_verbs) and any(k in msg_lower for k in camera_keywords):
            confidence = 0.85
            reasons.append("action verb + camera keyword")

        if confidence <= 0:
            return None

        return ToolIntent(
            tool_name='capture_camera_image',
            confidence=confidence,
            priority=ToolPriority.HIGH,
            reason=' | '.join(reasons),
            extracted_params={}
        )

    def _detect_view_image_intent(self, msg_lower: str, context: Dict) -> Optional[ToolIntent]:
        strong_signals = [
            'show me the image', 'display the picture', 'view the photo',
            'let me see', 'show the picture', 'display image'
        ]
        view_verbs = ['show', 'display', 'view', 'see', 'look at']
        image_nouns = ['image', 'picture', 'photo', 'screenshot']

        confidence = 0.0
        reasons = []

        if any(s in msg_lower for s in strong_signals):
            confidence = 0.90
            reasons.append("explicit view image keywords")
        elif any(v in msg_lower for v in view_verbs) and any(n in msg_lower for n in image_nouns):
            confidence = 0.80
            reasons.append("view verb + image noun")
        elif context.get('has_camera_in_history'):
            if any(v in msg_lower for v in view_verbs):
                confidence = 0.70
                reasons.append("view verb + camera context")

        if confidence <= 0:
            return None

        return ToolIntent(
            tool_name='view_image',
            confidence=confidence,
            priority=ToolPriority.MEDIUM,
            reason=' | '.join(reasons),
            extracted_params={}
        )

    def _detect_recognition_intent(self, msg_lower: str, context: Dict) -> Optional[ToolIntent]:
        face_signals = [
            'who is this', 'who is that', 'recognize face', 'identify person',
            'who am i looking at', "who's this", "who's that"
        ]
        place_signals = [
            'where is this', 'what place is this', 'recognize location',
            'identify place', 'where am i'
        ]

        confidence = 0.0
        reasons = []
        tool_name = None

        if any(s in msg_lower for s in face_signals):
            confidence = 0.90
            reasons.append("face recognition keywords")
            tool_name = 'recognize_face'
        elif any(s in msg_lower for s in place_signals):
            confidence = 0.90
            reasons.append("place recognition keywords")
            tool_name = 'recognize_place'

        if confidence <= 0:
            return None

        return ToolIntent(
            tool_name=tool_name,
            confidence=confidence,
            priority=ToolPriority.MEDIUM,
            reason=' | '.join(reasons),
            extracted_params={}
        )
