# -*- coding: utf-8 -*-
"""
Created on Mon Sep 11 11:06:58 2023

@author: ktakahashi
"""

import os
import sys

import numpy as np
import pandas as pd

import functions.subfunctions as sf


def bidrent_model(dfs_dict, df_distfacil, dict_prms, year, root_out):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # コピーして使う """
    df_zone = dfs_dict["Zone"].copy()

    """ # パラメータの受け取り """
    df_prm = dict_prms["付け値地代パラメータ"].copy()
    df_PCS = dict_prms["付け値地代主成分"].copy()
    
    """ # 付け値地代用のデータフレームを作成 """
    df_brm = pd.merge(df_zone[["zone_code", "Avg_Dist_sta_centre", "Avg_Dist_sta_main", "Avg_Dist_sta_other", "ACC_transit", "ACC_car", "ACC_walk"]], df_distfacil,
                      how = "left", on = ["zone_code"])
    
    # print(df_brm)
    
    """ # 標準化 """
    """ # 標準化対象列名をdf_PCSから取得 """
    target_col = list(df_PCS.index)

    """ # 標準化パラメータの取得 """
    """ # 1つのデータフレームにまとめておく """
    avestds = pd.concat([dfs_dict["ゾーン別駅距離平均標準偏差"], dfs_dict["ゾーン別施設距離平均標準偏差"],
                         dfs_dict["ACC平均標準偏差"]])
    
    """ # 対象列を標準化する """
    df_brm = sf.standardize(df_brm, avestds, target_col)
    # print(df_brm)
    
    """ # 主成分作成 """
    for i in [1,2]:
        col = f"PC{i}"
        pc_name = f"rotation.{col}"
        df_brm[col] = 0.0
        for jcol in target_col:
            col_std = jcol + "_std"
            df_brm[col] += df_brm[col_std] * df_PCS.loc[jcol, pc_name]
        
    """ # 世帯属性別効用関数 """
    for i in range(0, 4):
        col = f"setai_{i}_{year}"
        df_brm[col] = df_prm.loc[f"asc_{i}", "param"] + \
                        df_prm.loc[f"b_PC1_{i}", "param"] * df_brm["PC1"] + \
                        df_prm.loc[f"b_PC2_{i}", "param"] * df_brm["PC2"]
    
    """ # ログサム """
    df_brm[f"lgsm{year}"] = 0.0
    for i in range(0, 4):
        df_brm[f"lgsm{year}"] += np.exp(df_brm[f"setai_{i}_{year}"])
    df_brm[f"lgsm{year}"] = np.log(df_brm[f"lgsm{year}"])
    
    """ # 検算用に出力 """
    if(os.path.exists(r"output_swich")):
        df_brm.to_csv(rf"{root_out}/{year}_付け値地代lgsm.csv", index = False, encoding = "cp932")

    """ # ゾーンデータにlgsmを割り付け """
    add_list = ["zone_code", f"setai_0_{year}", f"setai_1_{year}", f"setai_2_{year}", f"setai_3_{year}", f"lgsm{year}"]
    df_zone = pd.merge(df_zone, df_brm[add_list], how = "left", on = ["zone_code"])
    
    # print(df_zone)
    
    """ # 出力 """
    if(os.path.exists(r"output_swich")):
        df_zone.to_csv(f"{root_out}/{year}_付け値地代.csv", index = False, encoding = "cp932")
    
    return df_zone
    