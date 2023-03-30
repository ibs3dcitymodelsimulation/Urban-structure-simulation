# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd


def parameter_standardized(df_zone, df_prmstd, col_name):
    """ # 変数を標準化する関数"""
    
    """ # パラメータを受け取る """
    v_mean = df_prmstd.loc[col_name, "mean"]
    v_std = df_prmstd.loc[col_name, "std"]
    df_zone[f"{col_name}_std"] = (df_zone[col_name] - v_mean) / v_std
    
    return df_zone
    
def residence_zone_select(zone1pb, mflag, fcategory, rand, dic_zone):
    """ # 転居なしの場合 """
    if(mflag == 0):
        return zone1pb
    
    """ # 転居有りの場合 """
    """ # 世帯類型を取得 : カテゴリの2桁目 """
    ftype = int(str(fcategory)[1:2])
    if(ftype == 1):
        """ # 単身世帯 """
        ftype = 0
    elif(ftype == 2):
        """ # 夫婦のみ世帯 """
        ftype = 1
    elif(ftype == 3):
        """ # 夫婦と子の世帯 """
        ftype = 2
    else:
        """ # その他の世帯 """
        ftype = 3
    
    """ # 確率を参照する列名を作成 """
    col_name = f"cumprob_{ftype}"
    
    """ # 世帯類型別ゾーン別の累積確率を下からなめて、当てはまった所のゾーンを返す """
    prob_min = 0.0
    zone = None
    for i in range(len(dic_zone["zone"])):
        prob_max = dic_zone["zone"].loc[i, col_name]
        if(prob_min <= rand < prob_max):
            zone = dic_zone["zone"].loc[i, "zone_code"]
            break
        else:
            prob_min = prob_max
    
    if(zone == None):
        print("zone selection is fail !!")
        print(f"rand = {rand}, ftype = {ftype}, prob_min = {prob_min}, prob_max = {prob_max}")
        sys.exit(0)
        
    return zone

def residence_select_model(df_individual, df_zone_org, df_brm_org, df_hlp, df_farea, df_lpv, df_prm, df_prmstd, year, period, outset, out_zoneselection):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 1期前の西暦 """
    year1pb = year - period
        
    """ # コピーしておく """
    df_zone = df_zone_org.copy()
    df_brm  = df_brm_org.copy()
        
    """ # ゾーンデータにマージする時に、ダミー変数が重複するので落としておく """
    df_brm = df_brm.drop(["j_senyo", "j_tiki", "s_tiki"], axis = 1)
    
    """ # ゾーンデータにマージしていく """
    df_zone = pd.merge(df_zone, df_brm, how = "left", on = ["zone_code"])
    df_zone = pd.merge(df_zone, df_hlp, how = "left", on = ["zone_code"])
    df_zone = pd.merge(df_zone, df_farea, how = "left", on = ["zone_code"])
    df_zone = pd.merge(df_zone, df_lpv, how = "left", on = ["zone_code"])
    
    """ # 0埋めしておく """
    df_zone = df_zone.fillna(0)
    
    """ # 住宅地価を割引・割増する """
    df_zone["住宅地価"] = df_zone["住宅地価"] * df_zone["居住誘導"]
    
    """ # 変数を標準化する """
    list_std = ["V0", "V1", "V2", "V3", "住宅地価", "farea_residence"]
    for name in list_std:
        df_zone = parameter_standardized(df_zone, df_prmstd, name)
    
    """ # 世帯類型別の効用計算 """
    """ # パラメータの受け取り """
    var_brm = df_prm.loc["付け値地代", "param"]
    var_hlp = df_prm.loc["住宅地価", "param"]
    var_rfa = df_prm.loc["住宅延べ床面積", "param"]
    
    for i in range(0, 4):
        brm_col = f"V{i}_std"
        df_zone[f"eff_{i}"] = var_brm * df_zone[brm_col] + var_hlp * df_zone["住宅地価_std"] + var_rfa * df_zone["farea_residence_std"]
    
    """ # 確率の計算 """
    for i in range(0, 4):
        df_zone[f"prob_{i}"] = np.exp(df_zone[f"eff_{i}"]) / np.exp(df_zone[f"eff_{i}"]).sum()
    
    """ # 累積確率の計算 """
    for i in range(0, 4):
        df_zone[f"cumprob_{i}"] = df_zone[f"prob_{i}"].cumsum()
    
    """ # 出力 """
    if(out_zoneselection["設定値"] == "T"):
        df_zone.to_csv(rf"{out_zoneselection['フォルダ名']}/ゾーン別選択確率{year}.csv", index = False, encoding = "cp932")
    
    """ # 必要なゾーンデータだけ残す """
    df_zone = df_zone[["zone_code", "cumprob_0", "cumprob_1", "cumprob_2", "cumprob_3",]]
    
    """ # 個人データに対して、移動先ゾーンを判定する """
    """ # ゾーン判定用乱数の付与 """
    df_individual[f"ゾーン選択用乱数{year}"] = pd.Series(np.random.random(len(df_individual)), index = df_individual.index)
    dic_zone = {"zone":df_zone}
    df_individual[f"現住所{year}"] = pd.Series(np.vectorize(residence_zone_select)
                                            (df_individual[f"現住所{year1pb}"],
                                             df_individual[f"転居発生有無フラグ{year}"],
                                             df_individual[f"カテゴリ{year}"],
                                             df_individual[f"ゾーン選択用乱数{year}"],
                                             dic_zone))

    """ # 出力 """
    if(outset["設定値"] == "T"):
        df_individual.to_csv(rf"{outset['フォルダ名']}/居住地選択モデル_{year}.csv", index = False, encoding = "cp932")
        
    """ # 転居発生有無判定終了 """
    return df_individual
    
