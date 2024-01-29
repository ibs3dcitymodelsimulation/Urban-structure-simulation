# -*- coding: utf-8 -*-
"""
Created on Thu Sep 14 19:56:37 2023

@author: ktakahashi
"""

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
    if(marker_year1pb != 4 and marker_year == 4):
        """ # 夫婦と子の世帯以外→夫婦と子の世帯 """
        ind_name = "FromNonFamilyToFamily"
    elif(marker_year1pb != 3 and marker_year == 3):
        """ # 単身以外→単身 """
        ind_name = "FromNonSingleToSingle"
    elif(marker_year1pb == marker_year):
        """ # 世帯構成変化なし """
        ind_name = "NoHouseholdChange"
    else:
        """ # パラメータ対応なし """
        ind_name = "None"
    
    """ # パラメータの取得 """
    try:
        var_cat = prm["prm"].loc[ind_name, "param"]
    except KeyError:
        var_cat = 0.0
    
    """ # パラメータを返す """
    return var_cat
    # この処理によって、1行追加される
    # 遷移判定に該当するパラメータの値を引っ張ってくる
    # 該当しないものは0.0が入力され、効用関数の計算で、定数項+df_individual[f"カテゴリ遷移パラメータ{year}"]となる。
    
def add_flag(prob, rand, cat, income, applyrand):
    """ # Marital_Status_Family_Position「99(=死亡)」は転居しない """
    if(cat == 99):
        return 0

    """ # 転入者は必ずゾーン選択 """
    if(income == 1):
        return 1
    
    if(rand <= prob)and(applyrand<0.2): # 5年に1回なので
        return 1
    else:
        return 0
    
    # 個人データ、カテゴリ遷移のdf、シミュレーション対象年次(2021）、期の間隔、outsetは出力
def relocation_model(df_individual, df_prm, year, root_out):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # シードを年にする（転居発生モデル計算用） """
    np.random.seed(year)

    """ # 1期前の西暦を作っておく """
    period = 1
    year1pb = year - period
    
    """ # 効用計算 """
    dic_prm = {"prm":df_prm}
    df_individual[f"カテゴリ遷移パラメータ{year}"] = pd.Series(np.vectorize(add_prm)
                                                    (df_individual[f"Marital_Status_Family_Position{year1pb}"],
                                                     df_individual[f"Marital_Status_Family_Position{year}"],
                                                     dic_prm))
    
    """ # 転居発生の定数項を受けておいて """
    var_const = dic_prm["prm"].loc["parameter_constant", "param"]

    """ # 効用関数の計算 """
    df_individual[f"転居発生効用{year}"] = var_const + df_individual[f"カテゴリ遷移パラメータ{year}"]
    
    """ # 転居発生確率の計算 """
    df_individual[f"転居発生確率{year}"] = np.exp(df_individual[f"転居発生効用{year}"]) / (np.exp(df_individual[f"転居発生効用{year}"]) + np.exp(0))
    
    """ # 転居発生判定用乱数 """
    df_individual[f"転居発生判定用乱数{year}"] = pd.Series(np.random.random(len(df_individual)), index = df_individual.index)

    """ ★★★★★★★★ 転居発生判定乱数を個人ごと年ごとに固定しようとする試み　ここ外せば元のコードに戻る"""    
    np.random.seed(year + 20000)
    moving_rand = np.random.random(10000000)
    df_individual[f"転居発生判定用乱数{year}"] = df_individual["Personal_UniqueId"].apply(lambda x:moving_rand[x])

    
    """ # シードを年+1000にする（5年に1回の転居発生モデル適用判定用） """
    np.random.seed(year+1000)

    """ # 確率は「5年間で生じる確率」なので、20%の確率でモデルを適用する """
    df_individual["転居発生モデル適用乱数"] = pd.Series(np.random.random(len(df_individual)), index = df_individual.index)

    """ ★★★★★★★★ これも同様　ここ外せば元のコードに戻る"""    
    np.random.seed(year + 30000)
    moving_rand = np.random.random(10000000)
    df_individual[f"転居発生判定用乱数{year}"] = df_individual["Personal_UniqueId"].apply(lambda x:moving_rand[x])

    """ # 転居発生有無フラグを付与 """
    # 転居発生有無フラグをMoveDecisiontとする
    df_individual[f"MoveDecision{year}"] = pd.Series(np.vectorize(add_flag)
                                                  (df_individual[f"転居発生確率{year}"], 
                                                   df_individual[f"転居発生判定用乱数{year}"],
                                                   df_individual[f"Marital_Status_Family_Position{year}"],
                                                   df_individual["IncomingFlg"],
                                                   df_individual["転居発生モデル適用乱数"]))
    
    """ # 出力 """
    # df_individual.to_csv(rf"{root_out}/MoveDecision_{year}.csv", index = False, encoding = "cp932")
        
    """ # 転居発生有無判定終了 """
    return df_individual