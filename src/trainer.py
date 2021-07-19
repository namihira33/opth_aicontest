import os
from datetime import datetime
import random

from tqdm import tqdm
import numpy as np
from sklearn.metrics import roc_auc_score

from torchvision import models,transforms
from PIL import Image

import torch
import torch.nn as nn
import torch.optim as optim

import config
from network import Vgg16
from Dataset import load_dataloader

torch.backends.cudnn.benchmark = True
device = torch.device('cuda:0')

class Trainer():
    def __init__(self, c):
        self.c = c
        now = '{:%y%m%d}'.format(datetime.today())
        log_path = os.path.join(config.LOG_DIR_PATH,
                                str(now) + '_' + c['model_name'])
        os.makedirs(log_path, exist_ok=True)

    def run(self):
        random.seed(self.c['seed'])
        torch.manual_seed(self.c['seed'])

        self.net = Vgg16().to(device)
        print(self.net.named_parameters())
        self.dataloaders = load_dataloader(
            self.c['bs'])

        params_to_update = []
        update_param_names = ["net.classifier.6.weight","net.classifier.6.bias"]

        for name,param in self.net.named_parameters():
            if name in update_param_names:
                param.requires_grad = True
                params_to_update.append(param)
            else:
                param.requires_grad = False
        print(params_to_update)

        self.optimizer = optim.SGD(params=params_to_update,lr=1e-3,momentum=0.9)
        self.criterion = nn.BCEWithLogitsLoss()

        for epoch in range(1, self.c['n_epoch']+1):
            self.execute_epoch(epoch, 'train')
            self.execute_epoch(epoch, 'test')
        
        img_file_path = "./data/ChestXray001.jpg"
        img = Image.open(img_file_path)

        transform = transforms.Compose([
            transforms.Resize(224),
            transforms.CenterCrop(224),
            transforms.ToTensor()
        ])

        transformed_img = transform(img)
        inp = transformed_img.unsqueeze_(0)
        out = self.net(inp.to(device))
        pred = out.detach().cpu().numpy()
        
        label = sigmoid(pred)[0]    
        threshold = 0.5
        if label < threshold:
            label = 0
        else:
            label = 1

        if label == 0 :
            print("This is a disease picture")
        else:
            print("This is a non-disease picture")
        


    def execute_epoch(self, epoch, phase):
        preds, labels, total_loss = [], [], 0
        if phase == 'train':
            self.net.train()
        else:
            self.net.eval()

        for inputs_, labels_ in tqdm(self.dataloaders[phase]):
            inputs_ = inputs_.to(device)
            labels_ = labels_.to(device)
            self.optimizer.zero_grad()

            with torch.set_grad_enabled(phase == 'train'):
                outputs_ = self.net(inputs_)
                loss = self.criterion(outputs_, labels_)

                if phase == 'train':
                    loss.backward(retain_graph=True)
                    self.optimizer.step()

            preds += [outputs_.detach().cpu().numpy()]
            labels += [labels_.detach().cpu().numpy()]
            for label in labels:
                if label[0] == 0:
                    print("non-Disease")
                else:
                    print("Disease")
            total_loss += float(loss.detach().cpu().numpy()) * len(inputs_)

        preds = np.concatenate(preds)
        labels = np.concatenate(labels)
        total_loss /= len(preds)
        auc = roc_auc_score(labels, preds)

        print(
            f'epoch: {epoch} phase: {phase} loss: {total_loss:.3f} auc: {auc:.3f}')