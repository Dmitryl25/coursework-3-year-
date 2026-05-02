import torch
import numpy as np



def evaluate(loader, model, criterion, device):
    running_loss, num_samples, num_correct = 0.0, 0, 0
    model.eval()
    
    with torch.inference_mode():
        for x, y in loader:
            x = x.to(device)
            y = y.to(device)
            
            outputs = model(x)
            loss = criterion(outputs, y)
            _, preds = outputs.max(1)

            num_samples += x.size(0)
            running_loss += loss.item() * x.size(0)
            num_correct += (preds == y).sum().item()

    avg_loss = running_loss / num_samples
    avg_acc = float(num_correct) / num_samples
    return avg_loss, avg_acc




def train(model, train_loader, test_loader, criterion, optimizer, device, epochs=5):
    model.train()
    best_acc = 0.0
    for epoch in range(epochs):
        running_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()

            outputs = model(images)
            loss = criterion(outputs, labels)

            loss.backward()
            optimizer.step()
            running_loss += loss.item()
        val_loss, val_acc = evaluate(test_loader, model, criterion, device)
        print(f"Эпоха {epoch+1}/{epochs} | Loss: {running_loss/len(train_loader):.4f} | Val Acc: {val_acc:.4f}")

        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), "best_food_model.pth")
            print(f"--> Сохранена лучшая модель с Acc: {best_acc:.4f}")

def get_pred(model, loader, device):
    model.eval()
    all_preds = []
    all_labels = []
    
    with torch.inference_mode():
        for x, y in loader:
            x = x.to(device, dtype=torch.float32)
            y = y.to(device, dtype=torch.long)

            scores = model(x)
            _, preds = scores.max(1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(y.cpu().numpy())

    return np.array(all_preds), np.array(all_labels)

    
