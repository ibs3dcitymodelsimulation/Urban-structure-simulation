# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd


def add_prm(cat_year1pb, cat_year, prm):
    
    """ # 追加された人にはカテゴリがないので、適当に埋める """
    if(np.isnan(cat_year1pb)):
        cat_year1pb = 18 # 空いてそうだったので、適当に
    
    """ # マーカーを切り出す """
    marker_year1pb = str(cat_year1pb)[1:2]
    marker_year = str(cat_year)[1:2]
    
    """ # 遷移判定 """
    if(marker_year1pb in [2,3] and marker_year == 1):
        """ # 夫婦のみor夫婦と子→単身 """
        ind_name = "夫婦のみor夫婦と子→単身"
    elif(marker_year1pb == 1 and marker_year != 1):
        """ # 単身→単身以外 """
        ind_name = "単身→単身以外"
    elif(marker_year1pb == marker_year):
        """ # 世帯構成変化なし """
        ind_name = "世帯構成変化なし"
    else:
        """ # その他の世帯構成変化 """
        ind_name = "その他の世帯構成変化"
    
    """ # パラメータの取得 """
    try:
        var_cat = prm["prm"].loc[ind_name, "param"]
    except KeyError:
        var_cat = 0.0
    
    """ # パラメータを返す """
    return var_cat
    
def add_flag(prob, rand, cat):
    """ # カテゴリ「99(=死亡)」は転居しない """
    if(cat == 99):
        return 0
    
    if(rand <= prob):
        return 1
    else:
        return 0

def relocation_model(df_individual, df_prm, year, period, outset):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 1期前の西暦を作っておく """
    year1pb = year - period
    
    """ # 効用計算 """
    dic_prm = {"prm":df_prm}
    df_individual[f"カテゴリ遷移パラメータ{year}"] = pd.Series(np.vectorize(add_prm)
                                                    (df_individual[f"カテゴリ{year1pb}"],
                                                     df_individual[f"カテゴリ{year}"],
                                                     dic_prm))
    """ # 転居発生の定数項を受けておいて """
    var_const = dic_prm["prm"].loc["定数（転居発生）", "param"]

    """ # 効用関数の計算 """
    df_individual[f"転居発生効用{year}"] = var_const + df_individual[f"カテゴリ遷移パラメータ{year}"]
    
    """ # 転居発生確率の計算 """
    df_individual[f"転居発生確率{year}"] = np.exp(df_individual[f"転居発生効用{year}"]) / (np.exp(df_individual[f"転居発生効用{year}"]) + np.exp(0))
    
    """ # 転居発生判定用乱数 """
    df_individual[f"転居発生判定用乱数{year}"] = pd.Series(np.random.random(len(df_individual)), index = df_individual.index)
    
    """ # 転居発生有無フラグを付与 """
    df_individual[f"転居発生有無フラグ{year}"] = pd.Series(np.vectorize(add_flag)
                                                  (df_individual[f"転居発生確率{year}"], 
                                                   df_individual[f"転居発生判定用乱数{year}"],
                                                   df_individual[f"カテゴリ{year}"]))
    
    """ # 出力 """
    if(outset["設定値"] == "T"):
        df_individual.to_csv(rf"{outset['フォルダ名']}/転居発生有無モデル_{year}.csv", index = False, encoding = "cp932")
        
    """ # 転居発生有無判定終了 """
    return df_individual
