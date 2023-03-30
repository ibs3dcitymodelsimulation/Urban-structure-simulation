# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd


def get_prm(usage, prms):
    col_name = "param_" + usage
    
    const = prms["prm"].loc["定数項 除却", col_name]
    age = prms["prm"].loc["築年数 除却", col_name]
    
    return const, age


def calc_eff(exist, usage, age, prms):
    if(exist == 2):
        """ # 建物が無い場合除却不能なので、あり得ない値を返しておく """
        return -99.99
        
    """ # 用途に対してパラメータの取得 """
    var_const, var_age = get_prm(usage, prms)
    
    """ # 効用の計算 """
    eff = var_const + var_age * age
    
    return eff

def removing_flag(exist, jrand, prob, rand):
    if(exist == 2):
        """ # 建物は無いので、そのまま無い　→　除却フラグは立たない """
        return -2
    
    if(0.2 <= jrand < 1):
        """ # 除却発生条件その1 : 5年に一回発生を満たさない → 除却しない """
        return 0
    
    """ # 除却発生条件その1 : 5年に一回発生を満たす """
    if(rand <= prob):
        """ # 発生条件その2 : 乱数より除却発生確率が大きい → 除却 """
        return 1
    else:
        return 0

def removing_model(df_build, df_prm, year, period, outset):
    print("Function : ", sys._getframe().f_code.co_name)
        
    """ # 1期前の西暦を作る """
    year1pb = year - period
    
    """ # 効用関数の計算 """
    dic_prm = {"prm":df_prm}
    df_build["効用関数"] = pd.Series(np.vectorize(calc_eff)
                                 (df_build[f"existing{year1pb}"], df_build[f"yoto{year1pb}"], 
                                  df_build[f"building_age{year1pb}"], dic_prm))
    
    """ # 確率の計算 """
    df_build["効用関数"] = df_build["効用関数"].replace(-99.99, np.nan)
    
    """ # 選択確率の計算 """
    df_build["expV"] = df_build["効用関数"].apply(lambda x : 0 if np.isnan(x) == True else np.exp(x))
    df_build["prob"] = df_build["expV"] / (df_build["expV"] + np.exp(0))
    
    """ # 乱数の付与 """
    df_build[f"除却判定用乱数{year}"] = pd.Series(np.random.random(len(df_build)), index = df_build.index)
    
    """ # 乱数の付与 """
    df_build["rand"] = pd.Series(np.random.random(len(df_build)), index = df_build.index)

    """ # 除却有無判定 """
    df_build[f"除却フラグ{year}"] = pd.Series(np.vectorize(removing_flag)
                                         (df_build[f"existing{year1pb}"], df_build[f"除却判定用乱数{year}"], 
                                          df_build["prob"], df_build["rand"]))
    df_build[f"除却フラグ{year}"] = df_build[f"除却フラグ{year}"].replace(-2, np.nan)

    """ # 除却になった比率 """
    nu = len(df_build[(df_build[f"existing{year1pb}"] == 1) & (df_build[f"除却フラグ{year}"] == 1)])
    de = len(df_build[(df_build[f"existing{year1pb}"] == 1)])
    rate = nu / de
    print(f"number of removing : {df_build[f'除却フラグ{year}'].sum()}")
    print(f"removing rate : {rate * 100:.3f}")
    
    """ # 出力 """
    if(outset["設定値"] == "T"):
        df_build.to_csv(rf"{outset['フォルダ名']}/除却有無モデル_{year}.csv", index = False, encoding = "cp932")
    
    """ # ここで追加した列は持ち越す必要がないので、落としておく """
    drop_col = ["効用関数", "expV", "prob", "rand"]
    df_build = df_build.drop(drop_col, axis = 1)
    
    """ # 返す """
    return df_build
