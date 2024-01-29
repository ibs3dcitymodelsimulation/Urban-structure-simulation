# -*- coding: utf-8 -*-
"""
Created on Tue Sep 19 09:33:18 2023

@author: ktakahashi
"""

import os
import sys

import math
import numpy as np
import pandas as pd

from numpy.random import default_rng

def build_group(code, usage):
    # if(4 <= code <= 8 and usage != 411):
    if(code in [4,5,6,7,9] and usage != 411):
        return 1
    elif(code == 10 and usage in [411, 413]):
        return 2
    elif(code in [11, 12] and usage != 411):
        return 3
    elif(code == 10 and usage not in [411, 413]):
        return 4
    else:
        return 9

def calc_bg4eff(roadwidth, const, prm_road):
    """ # グループ4以外は計算しない """ # ここで全グループ共通に計算しないとPoisson分布に従う乱数が固定化されない、計算だけしておいて後で適用するか判断
    eff = const + prm_road * roadwidth
    return eff


def calc_storey(exist, storey, bflag, group, usage, gflag, storey_4new, rand, prm):
    
    if(exist == 2):
        return -2
    
    """ # 辞書で渡したパラメータをデータフレームで受けておく """
    df_prm = prm["prm"]
    
    """ # 建設が無い場合、階数は1期前と同じ """
    if(bflag == 0):
        return storey
    
    """ # 建設があった場合、グループで分かれる """
    if(gflag != 4):
        """ # グループ1~3の場合、累積確率をなめていって乱数が入った範囲 """
        df_gprm = df_prm[(df_prm["buildgroup"] == group)&(df_prm["Usage"] == usage)].reset_index(drop = True)
        for i in range(len(df_gprm)):
            if(rand <= df_gprm.loc[i, "累積確率"]):
                return df_gprm.loc[i, "storeysAboveGround"]
    
    """ # グループ4の場合 """
    if(gflag == 4):
        if(storey_4new == 0):
            return 1
        else:
            return storey_4new
    
    """ # グルーピングされないものは2階建て """
    return 2


def calc_floorarea(exist, bflag, foot, storey, simflag, area1pb):
    if(exist == 2): # 空地なら-1
        return -1.0
    
    elif(bflag == 1): # 建設したなら、延べ床を上書きする
        return foot * storey
    
    else: # それ以外は、１期前と同じ延べ床
        return area1pb


def storeys_model(df_build, dict_prms, year, root_out):
    print("Function : ", sys._getframe().f_code.co_name)
        
    """ # 1期前の西暦を作る """
    period = 1
    year1pb = year - period
    
    """ # パラメータを受ける """
    prms1 = dict_prms["階数割合"]
    prms4 = dict_prms["階数パラメータ"]
    
    """ # 建物のグループ分け """
    df_build["build_group"] = pd.Series(np.vectorize(build_group)(df_build["UseDistrict"], df_build[f"Usage{year}"]))

    df_build["RoadWidth"] = df_build["RoadWidth"].fillna(0)
    
    """ # グループ4に適用する階数の確率を計算 """
    df_build["bg4_eff"] = pd.Series(np.vectorize(calc_bg4eff)(df_build["RoadWidth"],
                                                              prms4.loc["定数項", "param"], prms4.loc["RoadWidth", "param"]))
    
    """ # 階数判定用の乱数を付与 """
    rng_1 = default_rng(seed=year) # 乱数シード
    df_build["rand"] = pd.Series(rng_1.random(len(df_build)), index = df_build.index)    
    # df_build.to_csv(rf"{root_out}/階数モデル効用_{year}.csv", index = False, encoding = "cp932")
    
    """ # 階数判定 """
    dic_prm = {"prm":prms1}
    rng_2 = default_rng(seed=year+1000) # 乱数シード
    df_build["storeys_new4"] = rng_2.poisson(np.exp(df_build["bg4_eff"]))

    df_build[f"storeysAboveGround{year}"] = pd.Series(np.vectorize(calc_storey)
                                                      (df_build[f"Existing{year}"], df_build[f"storeysAboveGround{year1pb}"], 
                                                       df_build[f"Buildingflag{year}"], 
                                                       df_build["Group"], df_build[f"Usage{year}"], df_build["build_group"],
                                                       df_build["storeys_new4"], df_build["rand"], dic_prm))

    """ # 延床面積 """
    df_build[f"totalFloorArea{year}"] = pd.Series(np.vectorize(calc_floorarea)
                                                  (df_build[f"Existing{year}"], df_build[f"Buildingflag{year}"],
                                                   df_build["FootprintArea"], df_build[f"storeysAboveGround{year}"],
                                                   df_build["SimTargetFlag"], df_build[f"totalFloorArea{year1pb}"]))

    """ # 出力 """
    if(os.path.exists(r"output_swich")):
        df_build.to_csv(rf"{root_out}/階数モデル_{year}.csv", index = False, encoding = "cp932")


    
    return df_build