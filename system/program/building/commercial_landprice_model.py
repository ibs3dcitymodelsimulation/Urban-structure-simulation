# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd


def agg_reachable_zone_pop(df_reach, df_pop):
    """ # 到達可能圏域のデータフレームとそれにマージするデータフレームを渡して、ゾーン別人口を集計する """
    
    """ # flg = 1 が到達可能圏域 """
    df_reach = df_reach[df_reach["flg"] == 1].reset_index(drop = True)
    
    """ # 「dzone」側に人口をマージして """
    df_reach = pd.merge(df_reach, df_pop, how = "left", left_on = ["dzone"], right_on = ["zone_code"])
    
    """ # 「ozone」側で集計すればいい """
    df_reach_agg = df_reach.groupby(["ozone"], as_index = False).agg({"pop_all":"sum"})

    """ # 後のマージが楽なのでozoneをzone_codeにリネームしておく """
    df_reach_agg = df_reach_agg.rename(columns = {"ozone":"zone_code"})
        
    return df_reach_agg


def commercial_landprice_model(df_zone_org, df_pop, df_reach20min, df_reach40min, df_reachcar, df_prm, year, outset):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # コピー """
    df_zone = df_zone_org.copy()
    
    """ # 公共交通20分圏内到達可能人口の集計 """
    df_reach20min_agg = agg_reachable_zone_pop(df_reach20min, df_pop)
    
    """ # 公共交通40分圏内到達可能人口の集計 """
    df_reach40min_agg = agg_reachable_zone_pop(df_reach40min, df_pop)
    
    """ # 自動車到達可能ゾーンの人口集計 """
    df_reachcar_agg = agg_reachable_zone_pop(df_reachcar, df_pop)

    """ # ゾーンデータにマージする """
    df_zone = pd.merge(df_zone, df_reach20min_agg, how = "left", on = ["zone_code"])
    df_zone = pd.merge(df_zone, df_reach40min_agg, how = "left", on = ["zone_code"], suffixes = ("_20min", "_40min"))
    df_zone = pd.merge(df_zone, df_reachcar_agg, how = "left", on = ["zone_code"])
    df_zone = df_zone.rename(columns = {"pop_all":"pop_all_car"})

    """ # パラメータを一旦受けておく """
    var_reach40min = df_prm.loc["transit40_pop_all", "param"]
    var_reach20min = df_prm.loc["transit20_pop_all", "param"]
    var_reachcar = df_prm.loc["car5_pop_all", "param"]
    var_distUtu = df_prm.loc["ln(宇都宮駅距離)", "param"]
    const = df_prm.loc["切片", "param"]
    
    """ # 商業地価の計算 """
    df_zone["ln(商業地価)"] = const + var_reach40min * df_zone["pop_all_40min"] + var_reach20min * df_zone["pop_all_20min"] + var_reachcar * df_zone["pop_all_car"] + var_distUtu * np.log(df_zone["dist2Utu"])
    df_zone["商業地価"] = np.exp(df_zone["ln(商業地価)"])

    """ # 一旦出力 """
    if(outset["設定値"] == "T"):
        df_zone.to_csv(rf"{outset['フォルダ名']}/商業地価_{year}.csv", index = False, encoding = "cp932")

    """ # 使うのは商業地価だけなので、それだけ残しておく """
    df_clp = df_zone[["zone_code", "商業地価"]].copy()
    
    return df_clp
    