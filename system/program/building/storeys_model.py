# -*- coding: utf-8 -*-

import os
import sys

import math

import numpy as np
import pandas as pd

def build_group(code, usage):
    if(4 <= code <= 8 and usage != "住宅"):
        return 1
    elif(code == 9 and usage in ["住宅", "店舗等併用住宅"]):
        return 2
    elif(10 <= code <= 11 and usage != "住宅"):
        return 3
    elif(code == 9 and usage not in ["住宅", "店舗等併用住宅"]):
        return 4
    else:
        return 99

def calc_g4eff(grflag, roadwidth, const, prm_road):
    """ # グループ4以外は計算しない """
    if(grflag != 4):
        return -2.0
    
    eff = const + prm_road * roadwidth
    return eff

def calc_storey(exist, storey, bflag, gflag, g4eff, rand, prm):
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
        df_gprm = df_prm[df_prm["グループ"] == gflag].reset_index(drop = True)
        for i in range(len(df_gprm)):
            if(rand <= df_gprm.loc[i, "累積確率"]):
                return df_gprm.loc[i, "階数"]
    
    """ # グループ4の場合 """
    if(gflag == 4):
        storey = np.random.poisson(math.exp(g4eff))
        if(storey == 0):
            return 1
        else:
            return storey
    
    """ # グルーピングされないものは2階建て """
    return 2

def calc_floorarea(exist, farea, bflag, storey, area):
    if(exist == 2):
        return -2.0
    
    """ # 建設が無い場合、床面積は1期前と同じ """
    if(bflag == 0):
        return farea
    
    """ # 建設があった場合 """
    farea = storey * area
    return farea

def storeys_model(df_build, df_prm1, df_prm4, year, period, outset):
    print("Function : ", sys._getframe().f_code.co_name)
        
    """ # 1期前の西暦を作る """
    year1pb = year - period
    
    """ # まずは建物のグループ分け """
    df_build["build_group"] = pd.Series(np.vectorize(build_group)(df_build["usage_code"], df_build[f"yoto{year}"]))
    
    """ # 第4グループに対して階数の確率を計算する """
    df_build["group4_eff"] = pd.Series(np.vectorize(calc_g4eff)
                                       (df_build["build_group"], df_build["dorowidth"],
                                        df_prm4.loc["定数項", "param"], df_prm4.loc["zenmendorowidth", "param"]))
    df_build["group4_eff"] = df_build["group4_eff"].replace(-2.0, np.nan)
    
    """ # 階数判定用の乱数を付与 """
    df_build["rand"] = pd.Series(np.random.random(len(df_build)), index = df_build.index)
    
    """ # 階数判定 """
    dic_prm = {"prm":df_prm1}
    df_build[f"storey{year}"] = pd.Series(np.vectorize(calc_storey)
                                          (df_build[f"existing{year}"], df_build[f"storey{year1pb}"], 
                                           df_build[f"建設有無フラグ{year}"], df_build["build_group"],
                                           df_build["group4_eff"], df_build["rand"], dic_prm))
    df_build[f"storey{year}"] = df_build[f"storey{year}"].replace(-2, np.nan)
        
    """ # 出力 """
    if(outset["設定値"] == "T"):
        df_build.to_csv(rf"{outset['フォルダ名']}/階数モデル_{year}.csv", index = False, encoding = "cp932")
    
    """ # ここで追加した列を落としておく """
    drop_col = ["build_group", "group4_eff", "rand"]
    df_build = df_build.drop(drop_col, axis = 1)

    """ # 返す """
    return df_build
