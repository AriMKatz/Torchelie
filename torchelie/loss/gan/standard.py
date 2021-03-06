"""
Standard, non saturating, GAN loss from the original GAN paper

https://arxiv.org/abs/1406.2661

:math:`L_D(x_r, x_f) = - \log(1 - D(x_f)) - \log D(x_r)`

:math:`L_G(x_f) = -\log D(x_f)`
"""

import torch
import torch.nn.functional as F


def real(x):
    return F.binary_cross_entropy_with_logits(x, torch.ones_like(x))


def fake(x):
    return F.binary_cross_entropy_with_logits(x, torch.zeros_like(x))


def generated(x):
    return F.binary_cross_entropy_with_logits(x, torch.ones_like(x))
