import torch
from torchvision import transforms
from torchvision import models
from torch import nn

RANDOM_STATE = 801
RESIZE_SIZE = 232
IMAGE_SIZE = 224
NORMALISE_IMAGENET = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                          std=[0.229, 0.224, 0.225])

class MobileNet(nn.Module):
    def __init__(self, device, num_classes,
                 CHECKPOINT_PATH="unknown", checkpoint=False,
                 pretrained=True, freeze_layers=False) -> None:
        super().__init__()
        self.device = device
        self.num_classes = num_classes
        if checkpoint:
            self.model = models.mobilenet_v3_large(weights=None)
            self.replace_last_layer()
            weights = torch.load(CHECKPOINT_PATH, map_location=self.device)
            if 'model_state_dict' in weights:
                state_dict = weights['model_state_dict']
            elif 'state_dict' in weights:
                state_dict = weights['state_dict']
            else:
                state_dict = weights
            self.model.load_state_dict(state_dict, strict=False)
        else:
            self.model = models.mobilenet_v3_large(pretrained=pretrained,
                                                   weights='IMAGENET1K_V2')
            self.replace_last_layer()

        self.model = self.model.to(self.device)

        if freeze_layers:
            self.freeze_weights_except_last_layer()
    
    def replace_last_layer(self):
        in_feat = self.model.classifier[-1].in_features
        self.model.classifier[-1] = nn.Linear(in_feat, self.num_classes) # type: ignore

    
    def freeze_weights_except_last_layer(self):
        for params in self.model.parameters():
            params.requires_grad = False
        
        for params in self.model.classifier[-1].parameters():
            params.requires_grad = True

    def unfreeze_nn(self):
        for params in self.model.parameters():
            params.requires_grad = True
    
    def forward(self, x):
        return self.model(x)
