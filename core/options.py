"""Static option lists, presets and the canned instruction texts used across the app.

Everything a dropdown shows lives here so the UI, the validators and the prompt
builder always agree on the same vocabulary.
"""
from __future__ import annotations

APP_NAME = "Product Image Prompt Builder"
APP_VERSION = "1.0.0"
PROJECT_FORMAT = "product-image-prompt-builder-project"
PROJECT_SCHEMA_VERSION = 1
PROJECT_SUFFIX = ".project.json"

MAX_PRODUCT_IMAGES = 15
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
IMAGE_FILTER = "Images (*.jpg *.jpeg *.png *.webp)"

# Labels that make a combo reveal a free-text field.
CUSTOM = "Custom"
OTHER = "Other"

# --------------------------------------------------------------------------- #
# Navigation / section ids (ordered). The UI builds its nav list from this.
# --------------------------------------------------------------------------- #
SECTIONS: list[tuple[str, str]] = [
    ("references", "Reference Images"),
    ("brief", "ChatGPT Brief"),
    ("product", "Product Details"),
    ("identity", "Identity Lock"),
    ("scene", "Scene & Environment"),
    ("state", "Product State"),
    ("contents", "Food / Liquid"),
    ("model", "Human Model"),
    ("camera", "Camera"),
    ("lighting", "Lighting"),
    ("composition", "Composition"),
    ("style", "Visual Style"),
    ("output", "Output Settings"),
    ("restrictions", "Restrictions"),
    ("preview", "JSON Preview"),
]

# --------------------------------------------------------------------------- #
# Product
# --------------------------------------------------------------------------- #
PRODUCT_CATEGORIES = [
    "Glass container", "Bottle", "Mug", "Bowl", "Lunch box", "Storage jar", "Tiffin", OTHER,
]
MATERIALS = [
    "Borosilicate glass", "Plastic", "Silicone", "Stainless steel", "Aluminium",
    "Ceramic", "Wood", OTHER,
]
TRANSPARENCY = ["Transparent", "Semi-transparent", "Opaque", "Mixed"]

# --------------------------------------------------------------------------- #
# Scene
# --------------------------------------------------------------------------- #
SCENE_TYPES = [
    "Kitchen", "Dining table", "Microwave", "Refrigerator", "Car interior", "Office",
    "Gym", "Outdoor", "Restaurant", "Cafe", "Bedroom", "Living room", "Studio",
    "Ecommerce", CUSTOM,
]
BACKGROUND_TYPES = ["Sharp", "Slightly blurred", "Strong depth of field", "Clean studio", "Natural environment"]
TIMES_OF_DAY = ["Morning", "Afternoon", "Evening", "Night", "Not applicable"]

# --------------------------------------------------------------------------- #
# Product state / contents
# --------------------------------------------------------------------------- #
PRODUCT_STATES = [
    "Closed", "Open", "Lid attached", "Lid removed", "Vent open", "Vent closed", "Empty",
    "Filled", "Stacked", "Being held", "Being carried", "Being used", "Inside appliance",
    "On table", OTHER,
]
CONTENT_TYPES = ["Food", "Liquid", "Both"]
FOOD_EXAMPLES = [
    "Chicken salad", "Noodles", "Coffee", "Juice", "Water", "Soup", "Fruits", "Rice", "Pasta",
]
FILL_LEVELS = ["25%", "50%", "75%", "90%", "Full"]
STEAM_LEVELS = ["None", "Subtle", "Visible"]

# --------------------------------------------------------------------------- #
# Human model
# --------------------------------------------------------------------------- #
GENDERS = ["Female", "Male", "Neutral", "Any"]
AGE_RANGES = ["Child", "Teen", "18–25", "25–35", "35–50", "50+", CUSTOM]
BODY_AREAS = ["Hands only", "Upper body", "Half body", "Full body"]
EXPRESSIONS = ["Natural", "Happy", "Neutral", "Focused", "Candid", CUSTOM]

# --------------------------------------------------------------------------- #
# Camera / lighting / composition / style
# --------------------------------------------------------------------------- #
CAMERA_ANGLES = [
    "Eye level", "Top-down", "3/4 front", "3/4 rear", "Side view", "Low angle", "High angle",
    "Close-up", "Macro", "Wide angle", "Over-the-shoulder", "POV", CUSTOM,
]
CAMERA_DISTANCES = ["Extreme close-up", "Close-up", "Medium", "Medium wide", "Wide"]
LENS_STYLES = ["24mm", "35mm", "50mm", "85mm", "Macro", "Auto"]
DEPTH_OF_FIELD = ["Deep focus", "Moderate", "Shallow", "Very shallow"]
PERSPECTIVES = ["Natural", "Slightly cinematic", "Ecommerce accurate", CUSTOM]

PRODUCT_POSITIONS = ["Center", "Left", "Right", "Foreground", "Midground", "Background", CUSTOM]
COMPOSITION_STYLES = [
    "Product hero", "Lifestyle", "Editorial", "Ecommerce", "UGC", "Advertising",
    "Premium commercial", "Minimal", CUSTOM,
]
FRAMINGS = ["Tight", "Medium", "Loose"]
TEXT_SPACE_POSITIONS = ["Top", "Bottom", "Left", "Right"]

LIGHTING_TYPES = [
    "Natural daylight", "Soft studio", "Hard studio", "Window light", "Warm indoor",
    "Cool indoor", "Golden hour", "Cinematic", "High-key", "Low-key", CUSTOM,
]
LIGHT_DIRECTIONS = ["Front", "Back", "Left", "Right", "Top", "Mixed"]
SHADOW_STYLES = ["Soft", "Natural", "Dramatic", "Minimal"]
REFLECTION_LEVELS = ["Natural", "Controlled", "High gloss", "Minimal"]
COLOUR_TEMPERATURES = ["Warm", "Neutral", "Cool"]

PHOTOGRAPHY_STYLES = [
    "Photorealistic", "Commercial", "Premium", "Lifestyle", "UGC", "Editorial", "Ecommerce",
    "Luxury", "Documentary", "Minimal", "Cinematic",
]
DEFAULT_REALISM = 9

# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
OUTPUT_PRESETS: list[tuple[str, int, int]] = [
    ("1080 × 1080", 1080, 1080),
    ("1080 × 1350", 1080, 1350),
    ("1080 × 1920", 1080, 1920),
    ("800 × 1067", 800, 1067),
    ("1920 × 1080", 1920, 1080),
]
PRESET_CUSTOM_LABEL = CUSTOM
INTENDED_USES = [
    "Meta Ads", "Instagram Post", "Instagram Story", "Website", "Amazon",
    "Google Merchant Center", "Ecommerce", "Print", "Internal", OTHER,
]
OUTPUT_QUALITIES = ["Standard", "High", "Maximum"]
MIN_OUTPUT_PX = 64
MAX_OUTPUT_PX = 16384

# --------------------------------------------------------------------------- #
# Canned instruction texts (verbatim from the product brief)
# --------------------------------------------------------------------------- #
IDENTITY_LOCK_TEXT = (
    "Use all uploaded product reference images together as a multi-angle reference set for the "
    "same exact product. Preserve the exact product geometry, proportions, dimensions, material, "
    "transparency, colours, lid structure, locking mechanism, vent, handles, silicone parts, logo "
    "placement, edges, curves, wall thickness and all visible construction details. Do not "
    "redesign, reinterpret, simplify, stretch, widen, shorten or substitute the product."
)

AI_LOOK_AVOIDANCE_TEXT = (
    "Avoid artificial AI-looking textures, excessive smoothness, unrealistic reflections, fake "
    "depth of field, warped anatomy, incorrect perspective and overly stylized Pinterest-like "
    "aesthetics."
)

PRODUCT_REFERENCE_ROLE = "exclusive source of truth for product identity"

DEFAULT_RESTRICTIONS = [
    "Do not change product geometry.",
    "Do not alter product proportions.",
    "Do not modify the lid.",
    "Do not modify the logo.",
    "Do not invent handles or accessories.",
    "Do not change product colours.",
    "Do not make transparent glass opaque.",
    "Do not substitute a generic product.",
    "Do not distort hands.",
    "Do not create extra fingers.",
    "Do not create duplicate products unless requested.",
    "Do not add unwanted text.",
    "Do not create unrealistic reflections.",
    "Do not make the scene excessively stylized.",
]
DEFAULT_RESTRICTIONS_TEXT = "\n".join(f"- {line}" for line in DEFAULT_RESTRICTIONS)

# Helper copy shown in the UI.
PRODUCT_REF_HELP = (
    "These images define the exact identity, geometry, proportions, construction, material, "
    "colour and details of the product."
)
