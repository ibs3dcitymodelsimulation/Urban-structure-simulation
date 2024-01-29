# -*- coding: utf-8 -*-
"""
Created on Mon Sep 11 13:25:17 2023

@author: ktakahashi
"""

import os
import sys

import numpy as np
import pandas as pd

import functions.subfunctions as sf



def house_landprice_model(dfs_dict, df_individual, dict_prms, year, root_out):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # コピーして使う """
    df_zone = dfs_dict["Zone"].copy()
    # print(df_zone)

    """ # 容積率 """
    df_zone["ln_floorAreaRate"] = np.log(df_zone["floorAreaRate"])

    """ # パラメータを受ける """
    df_prm = dict_prms["住宅地価パラメータ"]
    
    """ # 1期前 """
    period = 1
    year1pb = year - period
    
    """ # 標準化パラメータを受け取る """
    """ # 1つのデータフレームにまとめておく """
    avestds = pd.concat([dfs_dict["ACC平均標準偏差"], dfs_dict["ゾーン別駅距離平均標準偏差"], dfs_dict["商業地域ダミー平均標準偏差"], dfs_dict["容積率平均標準偏差"]])
    # print(avestds)
    
    """ # 住宅地価を戻すように標準化パラメータを受け取る """
    hlp_meanstd = dict_prms["住宅地価平均標準偏差"]
    
    """ # 用途地域ダミー変数をつける """
    df_zone["sgtiki"] = df_zone["UseDistrict"].apply(lambda x : 1 if x == 10 else 0)
    
    """ # ACCつくる """
    df_zone["ACC_transit_ln"] = np.log(df_zone["ACC_transit"]+1)
    df_zone["ACC_car_ln"] = np.log(df_zone["ACC_car"]+1)
    df_zone["ACC_walk_ln"] = np.log(df_zone["ACC_walk"]+1)
    df_zone["ACC_ln"] = np.log(df_zone["ACC_transit"] + df_zone["ACC_car"]+1)

    """ # 駅距離lnとっておく"""
    df_zone["Avg_Dist_sta_centre_ln"] = np.log(df_zone["Avg_Dist_sta_centre"])
    df_zone["Avg_Dist_sta_main_ln"] = np.log(df_zone["Avg_Dist_sta_main"])
    df_zone["Avg_Dist_sta_other_ln"] = np.log(df_zone["Avg_Dist_sta_other"])

    # """ # ゾーン別人口集計 """
    # df_indagg = df_individual.groupby([f"zone_code{year1pb}"], as_index = False).agg({"Expansion_Factor":"sum"})
    # df_indagg = df_indagg.rename(columns = {f"zone_code{year1pb}":"zone_code", "Expansion_Factor":"zone_pop"})
    
    # """ # 人口密度を計算する """
    # df_zone = pd.merge(df_zone, df_indagg, how = "left", on = ["zone_code"]).fillna(0)
    # df_zone["popdens"] = df_zone["zone_pop"] / (df_zone["AREA"] / 10000)
    
    """ # 変数の標準化 """
    df_zone = sf.standardize(df_zone, avestds, list(avestds.index))
    # print(df_zone)
    
    """ # 定数列を追加しておくとループ処理できるので """
    df_zone["const"] = 1

    
    """ # 地価の推定 : ln版 """
    df_zone["ln_landprice_house"] = 0.0
    for col in list(df_prm.index):
        df_zone["ln_landprice_house"] += df_zone[col] * df_prm.loc[col, "param"]
    
    """ # 地価の推定 """
    df_zone[f"landprice_house{year}"] = np.exp(df_zone["ln_landprice_house"] * hlp_meanstd.loc["ln_住宅地価", "stds"] + hlp_meanstd.loc["ln_住宅地価", "means"])
    
    """ # 出力 """
    if(os.path.exists(r"output_swich")):
        df_zone.to_csv(f"{root_out}/{year}_住宅地価計算.csv", index = False, encoding = "cp932")
    
    """ # 再度コピーして,必要なものだけマージして返す """
    df_res =  dfs_dict["Zone"].copy()
    save_list = ["zone_code", f"landprice_house{year}"]
    df_res = pd.merge(df_res, df_zone[save_list], how = "left", on = ["zone_code"])
    # print(df_res)
    
    return df_res

