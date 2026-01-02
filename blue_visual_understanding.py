"""
Blue Robot Enhanced Visual Understanding System
================================================

Makes Blue perceptive about what's actually happening:
- Activity detection: What people are doing together
- Emotional awareness: How people are feeling
- Object interactions: What objects mean in context
- Scene narratives: Full understanding of situations

This goes beyond "who" to understand "what's happening" and "why it matters"
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Activity:
    """Detected activity with participants and context"""
    activity_type: str  # e.g., "working", "playing", "building", "eating"
    participants: List[str]  # Who's involved
    objects: List[str]  # What objects are being used
    location: str  # Where (e.g., "desk", "floor", "kitchen")
    confidence: float  # 0.0 to 1.0
    description: str  # Natural language description
    suggested_assistance: Optional[str] = None  # What Blue could offer
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class EmotionalState:
    """Person's emotional state from visual cues"""
    person: str
    primary_emotion: str  # focused, stressed, excited, happy, tired, etc.
    confidence: float
    visual_cues: List[str]  # What suggested this emotion
    energy_level: str  # high, medium, low
    engagement_level: str  # engaged, neutral, distracted
    suggested_response: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class ObjectInteraction:
    """How people are interacting with objects"""
    person: str
    object_name: str
    interaction_type: str  # holding, using, examining, reaching for
    context_meaning: str  # What this means in context
    implications: List[str]  # What this suggests about needs/activities
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class SceneNarrative:
    """Complete understanding of the scene"""
    overall_activity: str  # High-level: "Family project time", "Solo work session"
    key_details: List[str]  # Important observations
    social_dynamics: str  # How people are relating
    atmosphere: str  # Overall mood/vibe
    time_context: str  # Morning routine, afternoon work, evening relaxation
    proactive_suggestions: List[str]  # What Blue could offer
    attention_priorities: List[str]  # What deserves focus
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

# ============================================================================
# VISUAL UNDERSTANDING ENGINE
# ============================================================================

class EnhancedVisualUnderstanding:
    """
    Analyzes visual scenes for deep contextual understanding.
    
    Goes beyond object detection to understand:
    - What activities are happening
    - How people are feeling
    - What objects mean in context
    - The overall situation and how Blue can help
    """
    
    def __init__(self):
        self.recent_activities: List[Activity] = []
        self.recent_emotions: List[EmotionalState] = []
        self.recent_interactions: List[ObjectInteraction] = []
        self.recent_narratives: List[SceneNarrative] = []
        
        # Knowledge bases for understanding
        self.activity_patterns = self._load_activity_patterns()
        self.emotion_indicators = self._load_emotion_indicators()
        self.object_contexts = self._load_object_contexts()
        self.time_contexts = self._load_time_contexts()
    
    def analyze_scene(self, vision_description: str, 
                     people_present: List[str] = None,
                     objects_visible: List[str] = None) -> Dict:
        """
        Comprehensive scene analysis.
        
        Args:
            vision_description: Raw description from vision model
            people_present: List of people detected
            objects_visible: List of objects detected
            
        Returns:
            Complete analysis with activities, emotions, interactions, narrative
        """
        
        # Extract entities if not provided
        if people_present is None:
            people_present = self._extract_people(vision_description)
        if objects_visible is None:
            objects_visible = self._extract_objects(vision_description)
        
        # Multi-faceted analysis
        activities = self.detect_activities(vision_description, people_present, objects_visible)
        emotions = self.analyze_emotions(vision_description, people_present)
        interactions = self.analyze_object_interactions(vision_description, people_present, objects_visible)
        narrative = self.generate_scene_narrative(vision_description, activities, emotions, interactions)
        
        # Store for learning
        self.recent_activities.extend(activities)
        self.recent_emotions.extend(emotions)
        self.recent_interactions.extend(interactions)
        self.recent_narratives.append(narrative)
        
        # Limit history
        self._prune_history()
        
        return {
            "activities": [asdict(a) for a in activities],
            "emotions": [asdict(e) for e in emotions],
            "object_interactions": [asdict(i) for i in interactions],
            "scene_narrative": asdict(narrative),
            "summary": self._create_summary(narrative, activities, emotions)
        }
    
    def detect_activities(self, description: str, 
                         people: List[str], 
                         objects: List[str]) -> List[Activity]:
        """
        Detect what activities are happening.
        
        Recognizes patterns like:
        - Building/creating together
        - Individual focused work
        - Group discussion
        - Playing/recreation
        - Eating/meal time
        - Learning/teaching moments
        """
        activities = []
        desc_lower = description.lower()
        
        # Multi-person collaborative activities
        if len(people) >= 2:
            # Building/creating together
            if any(word in desc_lower for word in ['building', 'creating', 'making', 'constructing', 'assembling']):
                activity = Activity(
                    activity_type="collaborative_creation",
                    participants=people,
                    objects=[obj for obj in objects if obj.lower() in ['blocks', 'lego', 'tools', 'materials', 'paper', 'craft']],
                    location=self._infer_location(description, objects),
                    confidence=0.85,
                    description=f"{' and '.join(people)} are building or creating something together",
                    suggested_assistance="Would you like me to set up some background music? Or find project ideas?"
                )
                activities.append(activity)
            
            # Playing together
            elif any(word in desc_lower for word in ['playing', 'game', 'toy', 'fun', 'laughing']):
                activity = Activity(
                    activity_type="play_together",
                    participants=people,
                    objects=[obj for obj in objects if obj.lower() in ['toy', 'game', 'ball', 'doll']],
                    location=self._infer_location(description, objects),
                    confidence=0.80,
                    description=f"{' and '.join(people)} are playing together",
                    suggested_assistance="I can suggest games or activities if you'd like!"
                )
                activities.append(activity)
            
            # Discussion/conversation
            elif any(word in desc_lower for word in ['talking', 'discussing', 'conversation', 'meeting', 'facing each other']):
                activity = Activity(
                    activity_type="discussion",
                    participants=people,
                    objects=[],
                    location=self._infer_location(description, objects),
                    confidence=0.75,
                    description=f"{' and '.join(people)} are having a conversation",
                    suggested_assistance="I can take notes if this is a meeting, or stay quiet if it's casual chat"
                )
                activities.append(activity)
            
            # Teaching/learning
            elif any(word in desc_lower for word in ['teaching', 'learning', 'showing', 'explaining', 'demonstrating']):
                activity = Activity(
                    activity_type="teaching_learning",
                    participants=people,
                    objects=objects,
                    location=self._infer_location(description, objects),
                    confidence=0.80,
                    description=f"Learning activity with {' and '.join(people)}",
                    suggested_assistance="I can look up information or answer questions if you need help!"
                )
                activities.append(activity)
        
        # Solo activities
        elif len(people) == 1:
            person = people[0]
            
            # Focused work
            if any(word in desc_lower for word in ['working', 'typing', 'computer', 'laptop', 'focused', 'desk', 'writing']):
                activity = Activity(
                    activity_type="focused_work",
                    participants=[person],
                    objects=[obj for obj in objects if obj.lower() in ['laptop', 'computer', 'keyboard', 'mouse', 'screen', 'desk', 'paper', 'pen']],
                    location="desk" if 'desk' in desc_lower else "workspace",
                    confidence=0.90,
                    description=f"{person} is in focused work mode",
                    suggested_assistance="I can help with research, set timers, or stay quiet so you can concentrate"
                )
                activities.append(activity)
            
            # Reading
            elif any(word in desc_lower for word in ['reading', 'book', 'document', 'article']):
                activity = Activity(
                    activity_type="reading",
                    participants=[person],
                    objects=[obj for obj in objects if 'book' in obj.lower() or 'paper' in obj.lower()],
                    location=self._infer_location(description, objects),
                    confidence=0.85,
                    description=f"{person} is reading",
                    suggested_assistance="I can look up related information or summarize topics if you need"
                )
                activities.append(activity)
            
            # Creative work
            elif any(word in desc_lower for word in ['drawing', 'painting', 'creating', 'art', 'craft', 'making']):
                activity = Activity(
                    activity_type="creative_work",
                    participants=[person],
                    objects=[obj for obj in objects if any(x in obj.lower() for x in ['paint', 'brush', 'canvas', 'paper', 'crayon', 'marker'])],
                    location=self._infer_location(description, objects),
                    confidence=0.85,
                    description=f"{person} is doing creative work",
                    suggested_assistance="I can play music to match your creative mood!"
                )
                activities.append(activity)
        
        # General activity detection
        if not activities:
            # Default to general presence
            activity = Activity(
                activity_type="general_presence",
                participants=people,
                objects=objects,
                location=self._infer_location(description, objects),
                confidence=0.60,
                description=f"{', '.join(people) if people else 'Someone'} is here",
                suggested_assistance="Let me know if you need anything!"
            )
            activities.append(activity)
        
        return activities
    
    def analyze_emotions(self, description: str, people: List[str]) -> List[EmotionalState]:
        """
        Analyze emotional states from visual cues.
        
        Detects:
        - Focus levels (focused, distracted)
        - Stress indicators (tense, relaxed)
        - Engagement (excited, bored, neutral)
        - Energy (energetic, tired)
        - Mood (happy, frustrated, calm)
        """
        emotions = []
        desc_lower = description.lower()
        
        for person in people:
            # Initialize default
            primary_emotion = "neutral"
            confidence = 0.5
            visual_cues = []
            energy = "medium"
            engagement = "neutral"
            suggested_response = None
            
            # FOCUSED / CONCENTRATED
            if any(word in desc_lower for word in ['focused', 'concentrating', 'intent', 'staring at screen', 'leaning forward']):
                primary_emotion = "focused"
                visual_cues.append("Concentrated posture and gaze")
                confidence = 0.80
                energy = "medium"
                engagement = "engaged"
                suggested_response = "I'll stay quiet and let you concentrate. Just say my name if you need me."
            
            # STRESSED / TENSE
            elif any(word in desc_lower for word in ['stressed', 'tense', 'frown', 'rubbing face', 'head in hands']):
                primary_emotion = "stressed"
                visual_cues.append("Tension in posture or facial expression")
                confidence = 0.75
                energy = "low"
                engagement = "struggling"
                suggested_response = "You look like you could use a break. Want me to set a timer or find something relaxing?"
            
            # EXCITED / ENERGETIC
            elif any(word in desc_lower for word in ['excited', 'animated', 'energetic', 'jumping', 'smiling', 'laughing']):
                primary_emotion = "excited"
                visual_cues.append("Animated movement and positive expression")
                confidence = 0.85
                energy = "high"
                engagement = "engaged"
                suggested_response = "You seem energized! Let me know if you want to tackle something fun."
            
            # HAPPY / CONTENT
            elif any(word in desc_lower for word in ['happy', 'smiling', 'relaxed', 'content', 'cheerful']):
                primary_emotion = "happy"
                visual_cues.append("Positive facial expression and relaxed body language")
                confidence = 0.80
                energy = "medium"
                engagement = "engaged"
                suggested_response = None  # No need to interrupt happiness
            
            # TIRED / FATIGUED
            elif any(word in desc_lower for word in ['tired', 'yawning', 'slouching', 'rubbing eyes', 'fatigue']):
                primary_emotion = "tired"
                visual_cues.append("Low energy posture and facial cues")
                confidence = 0.75
                energy = "low"
                engagement = "low"
                suggested_response = "You look tired. Maybe time for a break or some coffee?"
            
            # FRUSTRATED
            elif any(word in desc_lower for word in ['frustrated', 'angry', 'sighing', 'throwing hands up']):
                primary_emotion = "frustrated"
                visual_cues.append("Tension and negative expression")
                confidence = 0.70
                energy = "medium"
                engagement = "struggling"
                suggested_response = "Having a tough time? I can help if you need assistance with something."
            
            # CONFUSED
            elif any(word in desc_lower for word in ['confused', 'puzzled', 'scratching head', 'looking around']):
                primary_emotion = "confused"
                visual_cues.append("Uncertain body language")
                confidence = 0.70
                energy = "medium"
                engagement = "uncertain"
                suggested_response = "You look puzzled. Need help figuring something out?"
            
            emotion = EmotionalState(
                person=person,
                primary_emotion=primary_emotion,
                confidence=confidence,
                visual_cues=visual_cues,
                energy_level=energy,
                engagement_level=engagement,
                suggested_response=suggested_response
            )
            emotions.append(emotion)
        
        return emotions
    
    def analyze_object_interactions(self, description: str, 
                                   people: List[str], 
                                   objects: List[str]) -> List[ObjectInteraction]:
        """
        Analyze how people are interacting with objects and what it means.
        
        Examples:
        - Holding coffee mug → Morning routine, needs caffeine
        - Using laptop → Work mode, needs focus
        - Holding book → Learning/relaxing time
        - With food → Meal time, might be hungry
        """
        interactions = []
        desc_lower = description.lower()
        
        # Coffee/beverage interactions
        if any(obj.lower() in ['mug', 'cup', 'coffee', 'tea'] for obj in objects):
            for person in people:
                if any(word in desc_lower for word in ['holding', 'drinking', 'sipping']):
                    interaction = ObjectInteraction(
                        person=person,
                        object_name="coffee/beverage",
                        interaction_type="drinking",
                        context_meaning="Morning or break time - needs energy boost",
                        implications=[
                            "Likely morning work session or afternoon break",
                            "May appreciate calm music or focused environment",
                            "Probably settling in for productive time"
                        ]
                    )
                    interactions.append(interaction)
        
        # Computer/laptop interactions
        if any(obj.lower() in ['laptop', 'computer', 'keyboard', 'screen'] for obj in objects):
            for person in people:
                if 'typing' in desc_lower or 'using' in desc_lower or 'at computer' in desc_lower:
                    interaction = ObjectInteraction(
                        person=person,
                        object_name="computer",
                        interaction_type="using",
                        context_meaning="Active work or research mode",
                        implications=[
                            "Needs focus and minimal interruptions",
                            "May need information or research assistance",
                            "Document or email tools might be helpful",
                            "Could benefit from reminders to take breaks"
                        ]
                    )
                    interactions.append(interaction)
        
        # Book/reading material interactions
        if any(obj.lower() in ['book', 'paper', 'document', 'magazine'] for obj in objects):
            for person in people:
                if any(word in desc_lower for word in ['reading', 'holding book', 'looking at']):
                    interaction = ObjectInteraction(
                        person=person,
                        object_name="reading material",
                        interaction_type="reading",
                        context_meaning="Learning or relaxation time",
                        implications=[
                            "Quiet environment appreciated",
                            "May have questions about the content",
                            "Could want related information or discussion"
                        ]
                    )
                    interactions.append(interaction)
        
        # Phone interactions
        if any(obj.lower() in ['phone', 'smartphone', 'mobile'] for obj in objects):
            for person in people:
                if any(word in desc_lower for word in ['holding phone', 'looking at phone', 'on phone']):
                    interaction = ObjectInteraction(
                        person=person,
                        object_name="phone",
                        interaction_type="using",
                        context_meaning="Communication or casual browsing",
                        implications=[
                            "May be checking messages or social media",
                            "In between tasks or taking a break",
                            "Might be available for quick interactions"
                        ]
                    )
                    interactions.append(interaction)
        
        # Food interactions
        if any(obj.lower() in ['food', 'plate', 'bowl', 'sandwich', 'snack'] for obj in objects):
            for person in people:
                if any(word in desc_lower for word in ['eating', 'having', 'with food']):
                    interaction = ObjectInteraction(
                        person=person,
                        object_name="food",
                        interaction_type="eating",
                        context_meaning="Meal or snack time",
                        implications=[
                            "Taking a break from work",
                            "Social opportunity if multiple people",
                            "Probably more relaxed and available to chat"
                        ]
                    )
                    interactions.append(interaction)
        
        # Toy/play object interactions  
        if any(obj.lower() in ['toy', 'game', 'blocks', 'lego', 'doll', 'ball'] for obj in objects):
            for person in people:
                if any(word in desc_lower for word in ['playing', 'building', 'with toy']):
                    interaction = ObjectInteraction(
                        person=person,
                        object_name="play objects",
                        interaction_type="playing",
                        context_meaning="Play or creative time",
                        implications=[
                            "In creative/imaginative mode",
                            "Open to suggestions for activities",
                            "Good time for fun interactions"
                        ]
                    )
                    interactions.append(interaction)
        
        return interactions
    
    def generate_scene_narrative(self, description: str,
                                 activities: List[Activity],
                                 emotions: List[EmotionalState],
                                 interactions: List[ObjectInteraction]) -> SceneNarrative:
        """
        Generate complete narrative understanding of the scene.
        
        Synthesizes all analyses into a coherent story about what's happening.
        """
        # Determine overall activity
        if activities:
            primary_activity = activities[0]
            if primary_activity.activity_type == "collaborative_creation":
                overall = f"Family project time - {' and '.join(primary_activity.participants)} working together"
            elif primary_activity.activity_type == "focused_work":
                overall = f"Solo work session - {primary_activity.participants[0]} in the zone"
            elif primary_activity.activity_type == "play_together":
                overall = f"Play time - {' and '.join(primary_activity.participants)} having fun"
            elif primary_activity.activity_type == "discussion":
                overall = "Conversation in progress"
            else:
                overall = primary_activity.description
        else:
            overall = "General activity"
        
        # Key details
        key_details = []
        for activity in activities:
            key_details.append(f"Activity: {activity.description}")
        for emotion in emotions:
            if emotion.primary_emotion not in ['neutral']:
                key_details.append(f"{emotion.person} seems {emotion.primary_emotion}")
        for interaction in interactions[:3]:  # Top 3
            key_details.append(f"{interaction.person} {interaction.interaction_type} {interaction.object_name}")
        
        # Social dynamics
        if len(activities) > 0 and len(activities[0].participants) > 1:
            if activities[0].activity_type in ["collaborative_creation", "play_together"]:
                social_dynamics = "Collaborative and engaged together"
            elif activities[0].activity_type == "discussion":
                social_dynamics = "Active communication"
            else:
                social_dynamics = "Present together but independent activities"
        elif len(activities) > 0 and len(activities[0].participants) == 1:
            social_dynamics = "Solo activity - individual focus"
        else:
            social_dynamics = "Not determined"
        
        # Atmosphere
        emotion_summary = [e.primary_emotion for e in emotions]
        if all(e in ['focused', 'engaged'] for e in emotion_summary):
            atmosphere = "Concentrated and productive"
        elif any(e in ['excited', 'happy'] for e in emotion_summary):
            atmosphere = "Positive and energetic"
        elif any(e in ['stressed', 'frustrated'] for e in emotion_summary):
            atmosphere = "Tense or challenging"
        elif any(e in ['tired'] for e in emotion_summary):
            atmosphere = "Low energy, winding down"
        else:
            atmosphere = "Calm and neutral"
        
        # Time context
        time_context = self._infer_time_context(description, interactions)
        
        # Proactive suggestions
        suggestions = []
        
        # From activities
        for activity in activities:
            if activity.suggested_assistance:
                suggestions.append(activity.suggested_assistance)
        
        # From emotions
        for emotion in emotions:
            if emotion.suggested_response:
                suggestions.append(emotion.suggested_response)
        
        # From interactions
        for interaction in interactions:
            if "needs focus" in ' '.join(interaction.implications):
                suggestions.append("I can minimize distractions and help you stay focused")
            if "questions about" in ' '.join(interaction.implications):
                suggestions.append("I can answer questions or look things up if you need")
        
        # Attention priorities
        priorities = []
        for emotion in emotions:
            if emotion.primary_emotion in ['stressed', 'frustrated']:
                priorities.append(f"{emotion.person} may need support or a break")
            elif emotion.primary_emotion == 'focused':
                priorities.append(f"Maintain quiet for {emotion.person}'s concentration")
        
        if not priorities:
            priorities.append("Be available but non-intrusive")
        
        narrative = SceneNarrative(
            overall_activity=overall,
            key_details=key_details,
            social_dynamics=social_dynamics,
            atmosphere=atmosphere,
            time_context=time_context,
            proactive_suggestions=suggestions,
            attention_priorities=priorities
        )
        
        return narrative
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _extract_people(self, description: str) -> List[str]:
        """Extract people names from description"""
        # Simple extraction - looks for known names
        known_names = ['Alex', 'Stella', 'Emmy', 'Athena', 'Vilda']
        people = []
        for name in known_names:
            if name.lower() in description.lower():
                people.append(name)
        return people
    
    def _extract_objects(self, description: str) -> List[str]:
        """Extract object names from description"""
        # Common objects
        objects = []
        object_keywords = [
            'laptop', 'computer', 'screen', 'keyboard', 'mouse',
            'phone', 'mug', 'cup', 'coffee', 'tea',
            'book', 'paper', 'document', 'pen', 'pencil',
            'toy', 'game', 'blocks', 'lego',
            'desk', 'chair', 'table',
            'food', 'plate', 'bowl'
        ]
        desc_lower = description.lower()
        for obj in object_keywords:
            if obj in desc_lower:
                objects.append(obj)
        return objects
    
    def _infer_location(self, description: str, objects: List[str]) -> str:
        """Infer location from context"""
        desc_lower = description.lower()
        
        if 'desk' in desc_lower or any(o in objects for o in ['laptop', 'computer', 'desk']):
            return "desk/workspace"
        elif 'kitchen' in desc_lower or 'table' in desc_lower and any(o in objects for o in ['food', 'plate']):
            return "kitchen/dining"
        elif 'floor' in desc_lower or any(o in objects for o in ['toy', 'blocks', 'lego']):
            return "floor/play area"
        elif 'couch' in desc_lower or 'sofa' in desc_lower:
            return "living room"
        else:
            return "general area"
    
    def _infer_time_context(self, description: str, interactions: List[ObjectInteraction]) -> str:
        """Infer what time of day / type of session this is"""
        # Check for coffee/morning indicators
        if any(i.object_name == "coffee/beverage" for i in interactions):
            return "Morning work session or afternoon break"
        
        # Check for meal indicators
        if any(i.object_name == "food" for i in interactions):
            return "Meal time or snack break"
        
        # Check for computer work
        if any(i.object_name == "computer" and "work" in i.context_meaning for i in interactions):
            return "Active work period"
        
        # Check for play
        if any(i.object_name == "play objects" for i in interactions):
            return "Play/recreation time"
        
        # Check for reading
        if any(i.object_name == "reading material" for i in interactions):
            return "Learning or relaxation time"
        
        return "General activity period"
    
    def _prune_history(self):
        """Keep history manageable"""
        max_items = 50
        self.recent_activities = self.recent_activities[-max_items:]
        self.recent_emotions = self.recent_emotions[-max_items:]
        self.recent_interactions = self.recent_interactions[-max_items:]
        self.recent_narratives = self.recent_narratives[-20:]
    
    def _create_summary(self, narrative: SceneNarrative, 
                       activities: List[Activity],
                       emotions: List[EmotionalState]) -> str:
        """Create natural language summary"""
        parts = []
        
        # Overall situation
        parts.append(narrative.overall_activity)
        
        # Add emotion context
        for emotion in emotions:
            if emotion.primary_emotion not in ['neutral']:
                parts.append(f"{emotion.person} seems {emotion.primary_emotion}")
        
        # Add time/atmosphere context
        parts.append(f"Atmosphere: {narrative.atmosphere}")
        
        # Add a suggestion if we have one
        if narrative.proactive_suggestions:
            parts.append(f"I can help: {narrative.proactive_suggestions[0]}")
        
        return ". ".join(parts)
    
    # ========================================================================
    # KNOWLEDGE BASES (can be expanded)
    # ========================================================================
    
    def _load_activity_patterns(self) -> Dict:
        """Load patterns for recognizing activities"""
        return {
            "collaborative": ["building together", "working together", "playing together"],
            "focused_work": ["at computer", "typing", "concentrating", "desk work"],
            "creative": ["drawing", "painting", "making", "creating"],
            "learning": ["reading", "studying", "practicing"],
            "play": ["playing", "game", "toy", "fun"],
            "social": ["talking", "conversation", "discussion", "meeting"]
        }
    
    def _load_emotion_indicators(self) -> Dict:
        """Load indicators for recognizing emotions"""
        return {
            "focused": ["concentrated", "intent gaze", "leaning forward", "still"],
            "stressed": ["tense", "frowning", "head in hands", "pacing"],
            "excited": ["animated", "smiling", "energetic movement", "laughing"],
            "tired": ["slouching", "yawning", "rubbing eyes", "slow movement"],
            "frustrated": ["sighing", "tense posture", "quick movements", "frowning"],
            "happy": ["smiling", "relaxed", "open posture", "cheerful expression"]
        }
    
    def _load_object_contexts(self) -> Dict:
        """Load contexts for understanding object usage"""
        return {
            "computer": {"work": 0.8, "entertainment": 0.2},
            "coffee": {"morning": 0.7, "break": 0.3},
            "book": {"learning": 0.6, "relaxation": 0.4},
            "toy": {"play": 0.9, "teaching": 0.1},
            "food": {"meal": 0.7, "snack": 0.3}
        }
    
    def _load_time_contexts(self) -> Dict:
        """Load time-of-day contexts"""
        return {
            "morning": ["coffee", "starting", "beginning", "fresh"],
            "afternoon": ["break", "lunch", "midday", "working"],
            "evening": ["dinner", "relaxing", "winding down", "family time"]
        }

# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_enhanced_vision_instance = None

def get_enhanced_visual_understanding() -> EnhancedVisualUnderstanding:
    """Get or create singleton instance"""
    global _enhanced_vision_instance
    if _enhanced_vision_instance is None:
        _enhanced_vision_instance = EnhancedVisualUnderstanding()
    return _enhanced_vision_instance

# ============================================================================
# CONVENIENCE FUNCTIONS FOR INTEGRATION
# ============================================================================

def analyze_scene_from_vision(vision_description: str) -> Dict:
    """
    Main entry point for scene analysis.
    
    Takes a vision description and returns complete contextual understanding.
    """
    evu = get_enhanced_visual_understanding()
    return evu.analyze_scene(vision_description)

def get_current_narrative() -> Optional[SceneNarrative]:
    """Get the most recent scene narrative"""
    evu = get_enhanced_visual_understanding()
    if evu.recent_narratives:
        return evu.recent_narratives[-1]
    return None

def get_emotional_context(person: str = None) -> List[EmotionalState]:
    """Get recent emotional states, optionally filtered by person"""
    evu = get_enhanced_visual_understanding()
    if person:
        return [e for e in evu.recent_emotions if e.person == person][-5:]
    return evu.recent_emotions[-10:]

def get_activity_history(limit: int = 10) -> List[Activity]:
    """Get recent activities"""
    evu = get_enhanced_visual_understanding()
    return evu.recent_activities[-limit:]

# ============================================================================
# PROACTIVE ASSISTANCE INTEGRATION
# ============================================================================

def check_for_assistance_opportunities(scene_analysis: Dict) -> List[str]:
    """
    Analyze scene and identify opportunities where Blue can help.
    
    Returns list of specific assistance suggestions.
    """
    opportunities = []
    
    narrative = scene_analysis.get('scene_narrative', {})
    emotions = scene_analysis.get('emotions', [])
    activities = scene_analysis.get('activities', [])
    
    # From narrative suggestions
    opportunities.extend(narrative.get('proactive_suggestions', []))
    
    # From emotional states
    for emotion in emotions:
        if emotion.get('suggested_response'):
            opportunities.append(emotion['suggested_response'])
    
    # From activities
    for activity in activities:
        if activity.get('suggested_assistance'):
            opportunities.append(activity['suggested_assistance'])
    
    return opportunities

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Test the system
    evu = get_enhanced_visual_understanding()
    
    # Example scene 1: Work mode
    scene1 = "Alex is sitting at his desk, focused on his laptop screen, typing. Coffee mug beside him. Morning light coming through window."
    analysis1 = analyze_scene_from_vision(scene1)
    print("SCENE 1 - Work Mode:")
    print(json.dumps(analysis1, indent=2))
    print("\n" + "="*80 + "\n")
    
    # Example scene 2: Kids playing
    scene2 = "Emmy and Athena are on the floor building something together with Lego blocks. They're both smiling and talking animatedly."
    analysis2 = analyze_scene_from_vision(scene2)
    print("SCENE 2 - Kids Playing:")
    print(json.dumps(analysis2, indent=2))
    print("\n" + "="*80 + "\n")
    
    # Example scene 3: Stressed situation
    scene3 = "Alex is at his desk, head in hands, papers scattered around. Looks frustrated and tired."
    analysis3 = analyze_scene_from_vision(scene3)
    print("SCENE 3 - Stress:")
    print(json.dumps(analysis3, indent=2))

# ============================================================================
# ALIASES FOR BACKWARD COMPATIBILITY
# ============================================================================

# Alias for import compatibility with bluetools.py
get_visual_understanding = get_enhanced_visual_understanding

def get_enhanced_vision_context() -> str:
    """Get formatted context string for enhanced vision."""
    narrative = get_current_narrative()
    if narrative:
        return f"Scene: {narrative.overall_activity}. Atmosphere: {narrative.atmosphere}. {', '.join(narrative.key_details[:3])}"
    return ""
