import torch
from data_preprocess import get_train_transform, get_test_transform, Food101
from torch import nn
from model import MobileNet
from train import evaluate, train
import os

def main():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    CHECKPOINT_PATH = os.path.join(BASE_DIR, "weights", "best_food_model.pth")

    food = Food101(download=False)
    num_classes = len(food.get_train_dataset().classes)

    train_loader, test_loader = food.get_train_loader(), food.get_test_loader()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = MobileNet(device, num_classes, CHECKPOINT_PATH=CHECKPOINT_PATH, checkpoint=True)

    loss_fn = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0001)

    #train(model, train_loader, test_loader, loss_fn, optimizer, device)

    print(evaluate(test_loader, model, loss_fn, device))

if __name__ == '__main__':
    main()
