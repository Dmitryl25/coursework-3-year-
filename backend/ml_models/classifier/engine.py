import os
import logging
from pathlib import Path
from typing import List

import torch
from PIL import Image

from ml_models.classifier.data_preprocess import get_test_transform
from ml_models.classifier.model import MobileNet

import time

logger = logging.getLogger(__name__)
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

FOOD101_RU = {
    "apple pie": "яблочный пирог",
    "baby back ribs": "свиные рёбрышки",
    "baklava": "пахлава",
    "beef carpaccio": "карпаччо из говядины",
    "beef tartare": "тартар из говядины",
    "beet salad": "салат из свёклы",
    "beignets": "пончики",
    "bibimbap": "бибимбап",
    "bread pudding": "хлебный пудинг",
    "breakfast burrito": "буррито на завтрак",
    "bruschetta": "брускетта",
    "caesar salad": "салат цезарь",
    "cannoli": "канноли",
    "caprese salad": "салат капрезе",
    "carrot cake": "морковный торт",
    "ceviche": "севиче",
    "cheese plate": "сырная тарелка",
    "cheesecake": "чизкейк",
    "chicken curry": "куриное карри",
    "chicken quesadilla": "кесадилья с курицей",
    "chicken wings": "куриные крылья",
    "chocolate cake": "шоколадный торт",
    "chocolate mousse": "шоколадный мусс",
    "churros": "чуррос",
    "clam chowder": "суп чаудер с моллюсками",
    "club sandwich": "клаб-сэндвич",
    "crab cakes": "крабовые котлеты",
    "creme brulee": "крем-брюле",
    "croque madame": "крок-мадам",
    "cup cakes": "капкейки",
    "deviled eggs": "фаршированные яйца",
    "donuts": "пончики",
    "dumplings": "пельмени",
    "edamame": "эдамаме",
    "eggs benedict": "яйца бенедикт",
    "escargots": "улитки по-бургундски",
    "falafel": "фалафель",
    "filet mignon": "филе миньон",
    "fish and chips": "рыба с картошкой",
    "foie gras": "фуа-гра",
    "french fries": "картофель фри",
    "french onion soup": "французский луковый суп",
    "french toast": "французские тосты",
    "fried calamari": "жареные кальмары",
    "fried rice": "жареный рис",
    "frozen yogurt": "замороженный йогурт",
    "garlic bread": "чесночный хлеб",
    "gnocchi": "ньокки",
    "greek salad": "греческий салат",
    "grilled cheese sandwich": "сэндвич с сыром на гриле",
    "grilled salmon": "лосось на гриле",
    "guacamole": "гуакамоле",
    "gyoza": "гёдза",
    "hamburger": "гамбургер",
    "hot and sour soup": "суп кисло-острый",
    "hot dog": "хот-дог",
    "huevos rancheros": "яйца ранчеро",
    "hummus": "хумус",
    "ice cream": "мороженое",
    "lasagna": "лазанья",
    "lobster bisque": "биск из лобстера",
    "lobster roll sandwich": "сэндвич с лобстером",
    "macaroni and cheese": "макароны с сыром",
    "macarons": "макаруны",
    "miso soup": "мисо-суп",
    "mussels": "мидии",
    "nachos": "начос",
    "omelette": "омлет",
    "onion rings": "луковые кольца",
    "oysters": "устрицы",
    "pad thai": "пад тай",
    "paella": "паэлья",
    "pancakes": "блины",
    "panna cotta": "панна котта",
    "peking duck": "утка по-пекински",
    "pho": "суп фо",
    "pizza": "пицца",
    "pork chop": "свиная отбивная",
    "poutine": "путин",
    "prime rib": "прайм-риб",
    "pulled pork sandwich": "сэндвич с тушёной свининой",
    "ramen": "рамэн",
    "ravioli": "равиоли",
    "red velvet cake": "торт красный бархат",
    "risotto": "ризотто",
    "samosa": "самоса",
    "sashimi": "сашими",
    "scallops": "морские гребешки",
    "seaweed salad": "салат из водорослей",
    "shrimp and grits": "креветки с кашей",
    "spaghetti bolognese": "спагетти болоньезе",
    "spaghetti carbonara": "спагетти карбонара",
    "spring rolls": "весенние роллы",
    "steak": "стейк",
    "strawberry shortcake": "клубничный пирог",
    "sushi": "суши",
    "tacos": "тако",
    "takoyaki": "такояки",
    "tiramisu": "тирамису",
    "tuna tartare": "тартар из тунца",
    "waffles": "вафли",
}

_classifier = None
_device = None
_transform = None


def classifier_init() -> None:
    global _classifier, _device, _transform
    logger.info("Loading MobileNet classifier...")
    start_time = time.time()

    if not os.path.exists(CHECKPOINT_PATH):
        logger.error(f"Checkpoint file not found: {CHECKPOINT_PATH}")
        raise FileNotFoundError(f"Classifier checkpoint not found at {CHECKPOINT_PATH}")

    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {_device}")

    try:
        _classifier = MobileNet(
            _device, NUM_CLASSES,
            CHECKPOINT_PATH=CHECKPOINT_PATH,
            checkpoint=True,
        )
        _classifier.eval()
        _transform = get_test_transform()
        load_time = time.time() - start_time
        logger.info(f"MobileNet classifier loaded on {_device} in {load_time:.2f}s")
    except Exception as e:
        logger.error(f"Failed to load classifier: {e}", exc_info=True)
        raise


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
