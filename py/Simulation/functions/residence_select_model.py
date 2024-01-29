# -*- coding: utf-8 -*-
"""
Created on Fri Sep 15 10:28:44 2023

@author: ktakahashi
"""

import os
import sys

import time

import numpy as np
import pandas as pd
from scipy.stats import zscore

import functions.subfunctions as sf

import pickle
import zipfile
import functions.compress as fcp


def zone_select_v2(zone1pb, mflag, cat, rand, dic_prob):
    if(mflag == 0):
        """ # 転居なし → ゾーン変化なし """
        return zone1pb
    else:
        """ # 転居有り """
        """ # 世帯類型を取得 : カテゴリの2桁目 """
        ftype = int(str(cat)[1:2])
        if(ftype <= 3):
            """ # 単身世帯 : ftype 0 """
            """ # 夫婦のみ世帯 : ftype 1 """
            """ # 夫婦と子の世帯 : ftype 2 """
            ftype -= 1
        else:
            """ # その他の世帯 """
            ftype = 3

        """ # 確率を参照する列名を作成 """
        col_name = f"cumprob_s{ftype}"
        
        """ # データフレームに受けなおして """
        df_prob = dic_prob["prob"]
        
        """ # 乱数との差分を作って """
        df_prob["diff"] = df_prob[col_name] - rand
        
        """ # 差分が正になった最初のレコードインデックス """
        df_prob = df_prob[df_prob["diff"] > 0].reset_index(drop = True)
        zone = df_prob.loc[0, "zone_code"]
        return zone


def residence_select_model(df_individual, dfs_dict, dict_prms, year, root_out):
    print("Function : ", sys._getframe().f_code.co_name)

    """ # 1期前 """
    period = 1
    year1pb = year - period
    
    """ # とりだし """
    df_zone = dfs_dict["Zone"].copy()
    df_lpr = dfs_dict["Land_Price_Change_Rate"]
    meanstds = dict_prms["住宅地価平均標準偏差"]
    
    """ # ゾーンデータの使うものをコピーする """
    list_use = ["zone_code", "UseDistrict", f"landprice_house{year}", "AREA", 
                f"setai_0_{year}", f"setai_1_{year}", f"setai_2_{year}", f"setai_3_{year}", f"lgsm{year}"]
    df_zone = dfs_dict["Zone"][list_use].copy()
    
    # """ # 用途地域でダミー作成 """
    # df_zone["低層住居ダミー"] = df_zone["UseDistrict"].apply(lambda x : 1 if x in [1] else 0)
    # df_zone["中高層住居ダミー"] = df_zone["UseDistrict"].apply(lambda x : 1 if x in [3,4] else 0)
    # df_zone["住居地域ダミー"] = df_zone["UseDistrict"].apply(lambda x : 1 if x in [5,6] else 0)
    
    """ # 住宅床面積をhaに変換 """
    """ # ゾーン別住宅床面積は acc_compop で集計済 """
    df_zone = pd.merge(df_zone, dfs_dict["ゾーン別延べ床面積"], how = "left", on = ["zone_code"])
    df_zone["住宅延床面積"] = df_zone["住宅延床面積"].fillna(0) / 10000
    # print(df_zone)
    # sys.exit(0)
    
    """ # ゾーンデータに割引率を割り付け """
    df_zone = pd.merge(df_zone, df_lpr[["zone_code", "ChangeRateResidence"]], how = "left", on = ["zone_code"])

    """ # 割引地価を作る """
    df_zone["住宅地価"] = df_zone[f"landprice_house{year}"] * (100 - df_zone["ChangeRateResidence"]) / 100
    
    """ # 住宅地価の標準化 """
    # ふつうに標準化する
    df_zone["住宅地価_lnstd"] = zscore(np.log(df_zone["住宅地価"]))
    # df_zone = sf.standardize(df_zone, meanstds, ["住宅地価"]

    """ # ログサムとの差分の標準化 の列を作成 """
    for i in range(0, 4):
        df_zone[f"tukene_{i}_lgsm_std"] = zscore(df_zone[f"setai_{i}_{year}"] - df_zone[f"lgsm{year}"])

    """ # ゾーン別人口の集計 """
    # df_indagg = df_individual.groupby([f"zone_code{year1pb}"], as_index = False).agg({"Expansion_Factor":"sum"})
    # df_indagg = df_indagg.rename(columns = {f"zone_code{year1pb}":"zone_code", "Expansion_Factor":"pop"})
    # df_zone = pd.merge(df_zone, df_indagg, how = "left", on = ["zone_code"])
    # df_zone["pop"] = df_zone["pop"].fillna(0)
    # print(df_zone)
    # sys.exit(0)
    
    """ # ゾーン別世帯類型別効用関数の計算 """
    prms = dict_prms["居住地選択パラメータ"]
    for i in range(0, 4):
        """ 
            # i = 0 : 単身世帯 : setai_0
            # i = 1 : 夫婦世帯 : setai_1
            # i = 2 : 夫婦と子供世帯 : setai_2
            # i = 3 : その他世帯 : setai_3
        """
        col = f"V_s{i}"
        # 2401072200版
        # df_zone[col] = prms.loc["b_jutakuchika_lnstd", "param"] * df_zone["住宅地価_lnstd"] + \
        #                prms.loc["b_tukene_lgsm", "param"] * (df_zone[f"setai_{i}_{year}"] - df_zone[f"lgsm{year}"]) + \
        #                np.log(df_zone[f"AREA"]) + \
        #                prms.loc["b_jutaku_area_dens", "param"] * np.log(df_zone["住宅延床面積"] / df_zone["AREA"])
        
        # 2401072230版
        df_zone[col] = prms.loc["b_jutakuchika_lnstd", "param"] * df_zone["住宅地価_lnstd"] + \
                       prms.loc["b_tukene_lgsm", "param"] * (df_zone[f"tukene_{i}_lgsm_std"]) + \
                       np.log(df_zone[f"AREA"]) + \
                       prms.loc["b_jutaku_area_dens", "param"] * np.log(df_zone["住宅延床面積"] / df_zone["AREA"])

        # 240108版 ゾーン面積なし
        df_zone[col] = prms.loc["b_jutakuchika_lnstd", "param"] * df_zone["住宅地価_lnstd"] + \
                       prms.loc["b_tukene_lgsm", "param"] * (df_zone[f"tukene_{i}_lgsm_std"]) + \
                       prms.loc["b_jutaku_area_dens", "param"] * np.log(df_zone["住宅延床面積"] / df_zone["AREA"])


    """ # オーバーフロー対策 """
    lim_up = 709
    for i in range(0,4):
        if(df_zone[f"V_s{i}"].max() > lim_up):
            df_zone[f"V_s{i}"] = df_zone[f"V_s{i}"] - (df_zone[f"V_s{i}"].max() - lim_up)
    
    """ # ゾーン別世帯類型別の選択確率 """
    for i in range(0,4):
        df_zone[f"Prob_s{i}"] = np.exp(df_zone[f"V_s{i}"]) / np.exp(df_zone[f"V_s{i}"]).sum()
    
    """ # 累積確率にして """
    for i in range(0,4):
        df_zone[f"cumprob_s{i}"] = df_zone[f"Prob_s{i}"].cumsum()
    
    """ # 選択確率出力 """
    if(os.path.exists(r"output_swich")):
        df_zone.to_csv(rf"{root_out}/居住地選択_確率{year}.csv", index = False, encoding = "cp932")

    
    """ # ゾーン選択に必要な確率だけ残しておく """
    df_prob = df_zone[["zone_code", "cumprob_s0", "cumprob_s1", "cumprob_s2", "cumprob_s3"]].copy()
        
    """ # 個人データへゾーン選択用乱数付与 """
    # df_individual[f"ゾーン選択用乱数{year}"] = pd.Series(np.random.random(len(df_individual)), index = df_individual.index)
    
    """ ★★★★★★★★ 転居発生判定乱数を個人ごと年ごとに固定しようとする試み　ここ外せば元のコードに戻る"""
    np.random.seed(year + 10000)
    moving_rand = np.random.random(10000000)
    df_individual[f"ゾーン選択用乱数{year}"] = df_individual["Personal_UniqueId"].apply(lambda x:moving_rand[x])

    """ # ゾーン選択 """
    dic_prob = {"prob":df_prob}
    df_individual[f"zone_code{year}"] = pd.Series(np.vectorize(zone_select_v2)
                                                  (df_individual[f"zone_code{year1pb}"],
                                                   df_individual[f"MoveDecision{year}"],
                                                   df_individual[f"Marital_Status_Family_Position{year}"],
                                                   df_individual[f"ゾーン選択用乱数{year}"],
                                                   dic_prob))

    if(os.path.exists(r"output_swich")):
        df_individual.to_csv(rf"{root_out}/居住地選択モデル_{year}.csv", index = False, encoding = "cp932")    

    
    return df_individual
    
