# -*- coding: utf-8 -*-
"""
Created on Thu Nov 30 11:50:51 2023

@author: ktakahashi
"""

import os
import sys

import numpy as np
import pandas as pd


def standardize(df_data, df_params, target_col):
    for col in target_col:
        ave = df_params.loc[col, "means"]
        std = df_params.loc[col, "stds"]
        col_std = col + "_std"
        df_data[col_std] = (df_data[col] - ave) / std
    
    return df_data


def overflow_check(lists):
    """ # 指数計算のオーバーフロー処理用 """
    lim_up = 700 # 上限の定義
    
    lmax = max(lists)
    if(lmax > lim_up):
        lists = [v - (lmax - lim_up) for v in lists]
    
    return lists

def minmax_normalize(df_data, df_params, target_col):
    for col in target_col:
        min_value = df_params.loc[col, "min"]
        max_value = df_params.loc[col, "max"]
        col_minmax = col + "_minmax"
        df_data[col_minmax] = (df_data[col] - min_value) / (max_value - min_value)

    return df_data

