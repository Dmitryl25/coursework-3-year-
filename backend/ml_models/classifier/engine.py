import os
from pathlib import Path
from typing import List

import torch
from PIL import Image

from ml_models.classifier.data_preprocess import get_test_transform
from ml_models.classifier.model import MobileNet

CHECKPOINT_PATH = str(Path(__file__).parent / "weights" / "best_food_model.pth")
NUM_CLASSES = 101

# Классы Food101 в алфавитном порядке (как их возвращает torchvision.datasets.Food101)
FOOD101_CLASSES = [
    "apple_pie", "baby_back_ribs", "baklava", "beef_carpaccio", "beef_tartare",
    "beet_salad", "beignets", "bibimbap", "bread_pudding", "breakfast_burrito",
    "bruschetta", "caesar_salad", "cannoli", "caprese_salad", "carrot_cake",
    "ceviche", "cheese_plate", "cheesecake", "chicken_curry", "chicken_quesadilla",
    "chicken_wings", "chocolate_cake", "chocolate_mousse", "churros", "clam_chowder",
    "club_sandwich", "crab_cakes", "creme_brulee", "croque_madame", "cup_cakes",
    "deviled_eggs", "donuts", "dumplings", "edamame", "eggs_benedict",
    "escargots", "falafel", "filet_mignon", "fish_and_chips", "foie_gras",
    "french_fries", "french_onion_soup", "french_toast", "fried_calamari", "fried_rice",
    "frozen_yogurt", "garlic_bread", "gnocchi", "greek_salad", "grilled_cheese_sandwich",
    "grilled_salmon", "guacamole", "gyoza", "hamburger", "hot_and_sour_soup",
    "hot_dog", "huevos_rancheros", "hummus", "ice_cream", "lasagna",
    "lobster_bisque", "lobster_roll_sandwich", "macaroni_and_cheese", "macarons", "miso_soup",
    "mussels", "nachos", "omelette", "onion_rings", "oysters",
    "pad_thai", "paella", "pancakes", "panna_cotta", "peking_duck",
    "pho", "pizza", "pork_chop", "poutine", "prime_rib",
    "pulled_pork_sandwich", "ramen", "ravioli", "red_velvet_cake", "risotto",
    "samosa", "sashimi", "scallops", "seaweed_salad", "shrimp_and_grits",
    "spaghetti_bolognese", "spaghetti_carbonara", "spring_rolls", "steak", "strawberry_shortcake",
    "sushi", "tacos", "takoyaki", "tiramisu", "tuna_tartare", "waffles",
]

_classifier = None
_device = None
_transform = None


def classifier_init() -> None:
    global _classifier, _device, _transform
    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _classifier = MobileNet(
        _device, NUM_CLASSES,
        CHECKPOINT_PATH=CHECKPOINT_PATH,
        checkpoint=True,
    )
    _classifier.eval()
    _transform = get_test_transform()


def classify_image(image_path: str, top_k: int = 3) -> List[dict]:
    """
    Возвращает top_k предсказаний классификатора.
    Каждый элемент: {"class_name": str, "confidence": float}
    """
    image = Image.open(image_path).convert("RGB")
    tensor = _transform(image).unsqueeze(0).to(_device)

    with torch.inference_mode():
        outputs = _classifier(tensor)
        probs = torch.softmax(outputs, dim=1)
        top_probs, top_indices = probs.topk(min(top_k, NUM_CLASSES))

    return [
        {
            "class_name": FOOD101_CLASSES[idx.item()].replace("_", " "),
            "confidence": round(prob.item(), 4),
        }
        for prob, idx in zip(top_probs[0], top_indices[0])
    ]
