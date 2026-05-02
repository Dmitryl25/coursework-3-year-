from torchvision import transforms, datasets
from torch.utils.data import DataLoader
from typing import Callable
import os

RANDOM_STATE = 801
RESIZE_SIZE = 232
IMAGE_SIZE = 224
NORMALISE_IMAGENET = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])

def get_train_transform() -> Callable:
    
    train_transform = transforms.Compose([
            transforms.RandomResizedCrop(size=IMAGE_SIZE),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.ToTensor(),
            NORMALISE_IMAGENET
        ])
    return train_transform

def get_test_transform():
    
    test_transform = transforms.Compose([
            transforms.Resize(size=RESIZE_SIZE), 
            transforms.CenterCrop(size=IMAGE_SIZE),
            transforms.ToTensor(),
            NORMALISE_IMAGENET
        ])
    
    return test_transform

class Food101():
    def __init__(self, download=True) -> None:
        base_path = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(base_path, "data")
        self.train_transform = get_train_transform()
        self.test_transform = get_test_transform()

        self.train_data = datasets.Food101(root=data_path, split="train", download=download, transform=self.train_transform)
        self.test_data = datasets.Food101(root=data_path, split="test", download=download, transform=self.test_transform)

        self.classes = max(len(self.train_data.classes), len(self.test_data.classes))

        self.train_loader = DataLoader(self.train_data, batch_size=64, shuffle=True, num_workers=2)
        self.test_loader = DataLoader(self.test_data, batch_size=64, shuffle=True, num_workers=2)
    
    def get_train_dataset(self):
        return self.train_data
    
    def get_test_dataset(self):
        return self.test_data

    def get_train_loader(self):
        return self.train_loader
    
    def get_test_loader(self):
        return self.test_loader
