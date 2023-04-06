#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np

__all__ = ['mask','masked','fill_out_matrix']

def mask(size, mode='lower', diag=True):
    if mode == 'lower':  # 保留下三角（遮蔽上三角）
        mask = np.ones((size, size))
        if diag:  # 保留對角線
            for i in range(size):
                for j in range(i+1):
                    mask[i][j] = 0
        else:  # 遮蔽對角線
            for i in range(1, size):
                for j in range(i):
                    mask[i][j] = 0
    elif mode == 'upper':  # 保留上三角（遮蔽下三角）
        mask = np.zeros((size, size))
        if diag:  # 保留對角線
            for i in range(1, size):
                for j in range(i):
                    mask[i][j] = 1
        else:  # 遮蔽對角線
            for i in range(size):
                for j in range(i+1):
                    mask[i][j] = 1
    elif mode == 'ndiag':  # 僅遮蔽對角線
        mask = np.zeros((size, size))
        for i in range(size):
            mask[i][i] = 1
    else:
        print(f"Warning: mask() has no option '{mode}' for argument: 'mode'.")
        print("Please specify 'upper', 'lower', or 'ndiag' instead.")
        mask = np.zeros((size, size))
    return mask

def masked(mat, mask):
    mat_new = mat
    for i, row in enumerate(mat):
        for j, element in enumerate(row):
            if mask[i][j]:
                mat_new[i][j] = 0
    return mat_new

def fill_out_matrix(schemes, mtags, dict):
    mat = np.zeros((len(schemes), len(schemes)))
    for i, row in enumerate(mat):
        for j, element in enumerate(row):
            mtag = mtags[i][j]
            if mtag:
                mat[i][j] = dict[mtag]
    mat = pd.DataFrame(mat, index=schemes, columns=schemes)
    return mat