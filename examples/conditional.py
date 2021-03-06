import sys
import argparse

import crayons

import torch
import torch.nn as nn
import torch.nn.functional as F

from torchvision.datasets import MNIST, CIFAR10
import torchvision.transforms as TF

import torchelie.nn as tnn
import torchelie.models
from torchelie.models import ClassCondResNetDebug
from torchelie.utils import nb_parameters
from torchelie.recipes.classification import Classification
from torchelie.optim import RAdamW

parser = argparse.ArgumentParser()
parser.add_argument('--cpu', action='store_true')
parser.add_argument('--dataset',
                    type=str,
                    choices=['mnist', 'cifar10'],
                    default='mnist')
parser.add_argument('--models', default='all')
parser.add_argument('--shapes-only', action='store_true')
opts = parser.parse_args()

device = 'cpu' if opts.cpu else 'cuda'


class TrueOrFakeLabelDataset:
    def __init__(self, dataset):
        self.dataset = dataset

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, i):
        x, y = self.dataset[i]
        if torch.randn(1).item() < 0:
            return x, 1, y
        return x, 0, torch.randint(0, 10, (1, )).item()


tfms = TF.Compose([TF.Resize(32), TF.ToTensor()])
if opts.dataset == 'mnist':
    ds = TrueOrFakeLabelDataset(
        MNIST('~/.cache/torch/mnist', download=True, transform=tfms))
    dt = TrueOrFakeLabelDataset(
        MNIST('~/.cache/torch/mnist',
              download=True,
              transform=tfms,
              train=False))
if opts.dataset == 'cifar10':
    ds = TrueOrFakeLabelDataset(
        CIFAR10('~/.cache/torch/cifar10', download=True, transform=tfms))
    dt = TrueOrFakeLabelDataset(
        CIFAR10('~/.cache/torch/cifar10',
                download=True,
                transform=tfms,
                train=False))
dl = torch.utils.data.DataLoader(ds,
                                 num_workers=4,
                                 batch_size=32,
                                 shuffle=True)
dlt = torch.utils.data.DataLoader(dt,
                                  num_workers=4,
                                  batch_size=32,
                                  shuffle=True)
if opts.models == 'all':
    nets = [ClassCondResNetDebug]
else:
    nets = [torchelie.models.__dict__[m] for m in opts.models.split(',')]


def summary(Net):
    clf = Net(1, 10, in_ch=1, debug=True).to(device)
    data = torch.randn(32, 1, 32, 32).to(device)
    labels = torch.randint(0, 10, (32, )).to(device)
    clf(data, labels)
    print('Nb parameters: {}'.format(nb_parameters(clf)))


class ConditionalClassification(nn.Module):
    def __init__(self, model):
        super(ConditionalClassification, self).__init__()
        self.model = model

    def forward(self, x, z):
        return self.model(x, z).squeeze()

    def make_optimizer(self):
        return RAdamW(self.model.parameters(), lr=1e-2)

    def train_step(self, batch, opt):
        x, y, z = batch
        x = x.expand(-1, 3, -1, -1)

        opt.zero_grad()
        out = self(x, z)
        loss = F.cross_entropy(out, y)
        loss.backward()
        opt.step()

        return {'loss': loss, 'pred': out}

    def validation_step(self, batch):
        x, y, z = batch
        x = x.expand(-1, 3, -1, -1)

        out = self(x, z)
        loss = F.cross_entropy(out, y)
        return {'loss': loss, 'pred': out}


def train_net(Net):
    model = Net(2, 10, in_ch=3)
    clf = Classification(ConditionalClassification(model)).to(device)
    _, res = clf(dl, dlt)
    print(res['acc'])


for Net in nets:
    print(crayons.yellow('---------------------------------'))
    print(crayons.yellow('-- ' + Net.__name__))
    print(crayons.yellow('---------------------------------'))

    if opts.shapes_only:
        summary(Net)
    else:
        train_net(Net)
