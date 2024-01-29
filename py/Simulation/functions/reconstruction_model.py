# -*- coding: utf-8 -*-
"""
Created on Thu Sep 14 18:24:57 2023

@author: ktakahashi
"""

import os
import sys

import numpy as np
import pandas as pd
from scipy.special import logsumexp

import functions.subfunctions as sf
from numpy.random import default_rng


def add_buildgroup(usage):
    if(usage in [1,2,3,4]):
        return "G1"
    elif(usage in [5,6,7,8,99]):
        return "G2"
    elif(usage in [11,12,13]):
        return "G3"
    elif(usage in [9,10]):
        return "G4"
    else:
        return "None"


def calc_Vvary(v1, v2, v3, v4, v5, v6, exist, lmd):

    """ #  計算対象をリストに """
    if exist == 1:
        vslist = [v1, v2, v3, v4, v5, v6]
    elif exist == 2:
        vslist = [v1, v2, v3, v4, v5]

    """ # 先にlmdで割っておく """
    vslist = [v / lmd for v in vslist]
    
    """ # オーバーフローチェック """
    vslist = sf.overflow_check(vslist)
    
    """ # ログサム計算 """
    logsum = np.log(sum([np.exp(v) for v in vslist]))
        
    return lmd * logsum


def calc_prob(v1, v2, v3, v4, v5, v6, exist, name, lmd):
    if(exist==2 and name =="remove"):
        return 0.0

    if(exist==1):
        vslist = [v1, v2, v3, v4, v5, v6]
    elif(exist==2):
        vslist = [v1, v2, v3, v4, v5]
    
    """ # 先にlmdで割っておく """
    vslist = [v / lmd for v in vslist]
    
    """ # オーバーフローチェック """
    vslist = sf.overflow_check(vslist)
    
    """ # 分母計算 """
    denom = sum([np.exp(v) for v in vslist])
    
    """ # 分子の選択 """
    if(exist == 1 and name == "remove"):
        nem = vslist[5]
    else:
        n = int(name[-1]) - 1
        nem = vslist[n]
    # print(name, exist, nem)

    """ # 確率計算 """
    prob = np.exp(nem) / denom

    return prob
    

def calc_probNL1(V_vary, V_remain, V_lot, exist, name, bid = ""):

    if(exist == 1 and name == "V_lot"):
        """ # 建物が存在している場合,空地維持の確率は0 """
        return 0.0
    elif(exist == 2 and name == "V_remain"):
        """ # 建物が存在してない場合,建物維持の確率は0 """
        return 0.0
    
    if(exist == 1):
        vslist = [V_vary, V_remain]
    elif(exist == 2):
        vslist = [V_vary, V_lot]

    """ # オーバーフローチェック """
    vslist = sf.overflow_check(vslist)
    
    if(name == "V_vary"):
        nem = vslist[0]
    elif(name == "V_remain"):
        nem = vslist[1]
    elif(name == "V_lot"):
        nem = vslist[1]
    
    prob = np.exp(nem) / sum([np.exp(v) for v in vslist])

    return prob
        

def calc_usage(p1, p2, p3, p4, p5, p_remove, p_remain, p_lot, usage1pb, exist1pb, age1pb, rand, tflag, bid, applyrand):
    if(tflag == 0):
        """ # 建物がシミュレーション対象ではない """
        if(pd.isnull(usage1pb)):
            usage = -1
        else:
            usage = usage1pb

        if(pd.isnull(age1pb)):
            age = -1
        else:
            age = age1pb +1

        exist = exist1pb
        bflag = 0
    
        return usage, exist, age, bflag
    
    elif(applyrand > 0.2):
        """ # モデルを適用しない場合は前期と一緒 """
        usage = usage1pb
        if exist1pb == 2:
            age = -1
        else:
            age = age1pb + 1
        exist = exist1pb
        bflag = 0
        return usage, exist, age, bflag

    else:
    
        """ # 辞書の形で用途とその確率を持っておく """
        """
        ①住宅 (usage1) : 411
        ②共同住宅 (usage2) : 412
        ③商業施設 (usage3) : 402
        ④店舗併用住宅 (usage4) : 413
        ⑤店舗併用共同住宅 (usage5) : 414
        ⑥建物の除却 (build_removed) : nan : -1
        ⑦建物の維持 (build_remain) : usage1pb : -3
        ⑧空地の維持 (blank_lot) : nan : -2
        """
        dic_prob = {411:p1, 412:p2, 402:p3, 413:p4, 414:p5, -1:p_remove, -3:p_remain, -2:p_lot}

        """ # 確率 """
        prob = 0.0
        for u, p in dic_prob.items():
            prob += p
            if(rand <= prob):
                usage = u
                break
        
        if(usage == -1):
            """ # 建物除却 """
            usage = -1
            age = -1
            exist = 2
            bflag = 0
        elif(usage == -2):
            """ # 空地維持 """
            usage = -1
            age = -1
            exist = 2
            bflag = 0
        elif(usage == -3):
            """ # 建物維持 """
            usage = usage1pb
            age = age1pb + 1
            exist = 1
            bflag = 0
        else:
            """ # 変化 """
            """ # usageは決まっている """
            age = 1
            exist = 1
            bflag = 1
            
        return usage, exist, age, bflag


def calc_lgsm(v1, v2, v3, v4, v5):
    """ # リストに入れて """
    vslist = [v1, v2, v3, v4, v5]

    """ # オーバーフローチェック """
    vslist = sf.overflow_check(vslist)
    
    """ # ログサム計算 """
    logsum = np.log(sum([np.exp(v) for v in vslist]))
    
    return logsum


def reconstruction_model(df_zone, df_build_org, df_lpr, dict_prms, year, root_out):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # シードを年にする """
    rng_1 = default_rng(seed=year) # 用途選択
    rng_2 = default_rng(seed=year+1000) # モデル適用用
    rng_3 = default_rng(seed=year+500) # 統合判定用

    """ # 1期前 """
    period = 1
    year1pb = year - period

    """ # 必要なデータを取り出して使う """
    df_build = df_build_org.copy()
    
    """ # 商業地価をゾーン別に集計して平均値を求める """
    df_clp = df_build.groupby(["zone_code"], as_index = False).agg({"Landprice_Commercial":"mean"})
    df_clp = df_clp.rename(columns = {"Landprice_Commercial":"mean_clp_org"}).fillna(0)
    df_clp = pd.merge(df_clp, df_lpr[["zone_code", "ChangeRateCommercial"]], how = "left", on = ["zone_code"])
    
    if(os.path.exists(r"output_swich")):
        df_clp.to_csv(rf"{root_out}/ゾーン別商業地価_{year}.csv", index = False, encoding = "cp932")
    
    df_clp["mean_clp"] = df_clp["mean_clp_org"] * (100 + df_clp["ChangeRateCommercial"]) / 100
    
    """ # ゾーン別の平均商業地価を建物データに割り付け """
    df_build = pd.merge(df_build, df_clp, how = "left", on = ["zone_code"])
    
    """ # df_zoneを割り付ける際に,floorAreaRateが重なるのでいったん消しておく """
    df_build = df_build.drop(["floorAreaRate"], axis = 1)

    """ # 建物データのゾーンコードに用途地域を割り付け """
    df_build = pd.merge(df_build, df_zone, how = "left", on = ["zone_code"])
    # print(df_build)
    
    """ # 最短駅距離を求めておく """
    df_build['Dist_sta'] = df_build[['Dist_sta_centre', 'Dist_sta_main', 'Dist_sta_other']].min(axis = 1)
    
    """ # 建物にグループを振る """
    df_build["Group"] = pd.Series(np.vectorize(add_buildgroup)(df_build["UseDistrict"]))
    
    """ # グループごとに処理 """
    """ # 順番を戻せるようにseqを振っておく """
    df_build["seq"] = df_build.index + 1
    
    df_list = []
    cols = ["seq", "V_usage1", "V_usage2", "V_usage3", "V_usage4", "V_usage5", 
            "V_remove", "V_remain", "V_lot", "V_vary"]
    for i in range(1,5):
        """ # グループiだけ抜き出す """
        df_ex = df_build[df_build["Group"] == f"G{i}"].reset_index(drop = True)
        prms = dict_prms[f"G{i}_prms"]
        
        """ # 効用関数を計算する """
        df_ex["V_usage1"] = prms.loc["asc_usage1", "Estimate"] + \
                            prms.loc["b_landprice_usage1", "Estimate"] * df_ex[f"landprice_house{year}"] * df_ex["FootprintArea"] / 1000000 +\
                            prms.loc["b_distance_usage1", "Estimate"] * np.log(df_ex["Dist_sta"]) +\
                            prms.loc["b_yoseki_usage1", "Estimate"] * df_ex["floorAreaRate"] / 100

        df_ex["V_usage2"] = prms.loc["asc_usage2", "Estimate"] + \
                            prms.loc["b_landprice_usage2", "Estimate"] * df_ex[f"landprice_house{year}"] * df_ex["FootprintArea"] / 1000000 +\
                            prms.loc["b_distance_usage2", "Estimate"] * np.log(df_ex["Dist_sta"]) +\
                            prms.loc["b_yoseki_usage2", "Estimate"] * df_ex["floorAreaRate"] / 100
        
        df_ex["V_usage3"] = prms.loc["asc_usage3", "Estimate"] + \
                            prms.loc["b_landprice_usage3", "Estimate"] * df_ex["mean_clp"] * df_ex["FootprintArea"] / 1000000 +\
                            prms.loc["b_distance_usage3", "Estimate"] * np.log(df_ex["Dist_sta"]) +\
                            prms.loc["b_yoseki_usage3", "Estimate"] * df_ex["floorAreaRate"] / 100

        df_ex["V_usage4"] = prms.loc["asc_usage4", "Estimate"] + \
                            prms.loc["b_landprice_usage1", "Estimate"] * df_ex[f"landprice_house{year}"] * df_ex["FootprintArea"] / 1000000 +\
                            prms.loc["b_distance_usage1", "Estimate"] * np.log(df_ex["Dist_sta"]) +\
                            prms.loc["b_yoseki_usage1", "Estimate"] * df_ex["floorAreaRate"] / 100

        df_ex["V_usage5"] = prms.loc["asc_usage5", "Estimate"] + \
                            prms.loc["b_landprice_usage2", "Estimate"] * df_ex[f"landprice_house{year}"] * df_ex["FootprintArea"] / 1000000 +\
                            prms.loc["b_distance_usage2", "Estimate"] * np.log(df_ex["Dist_sta"]) +\
                            prms.loc["b_yoseki_usage2", "Estimate"] * df_ex["floorAreaRate"] / 100
        
        df_ex["V_remove"] = prms.loc["asc_build_removed", "Estimate"] + \
                            prms.loc["b_landprice_build_removed", "Estimate"] * df_ex[f"landprice_house{year}"] * df_ex["FootprintArea"] / 1000000 +\
                            prms.loc["b_distance_removed", "Estimate"] * np.log(df_ex["Dist_sta"]) +\
                            prms.loc["b_yoseki_build_removed", "Estimate"] * df_ex["floorAreaRate"] / 100 + \
                            prms.loc["b_age_build_removed", "Estimate"] * df_ex[f"BuildingAge{year1pb}"]
        
        df_ex["V_remain"] = prms.loc["asc_building_remain", "Estimate"] + \
                            prms.loc["b_distance_remain", "Estimate"] * np.log(df_ex["Dist_sta"])

        df_ex["V_lot"] = prms.loc["asc_blank_lot", "Estimate"] + \
                          prms.loc["b_landprice_blank_lot", "Estimate"] * df_ex[f"landprice_house{year}"] * df_ex["FootprintArea"] / 1000000 +\
                          prms.loc["b_distance_blank_lot", "Estimate"] * np.log(df_ex["Dist_sta"]) +\
                          prms.loc["b_yoseki_blank_lot", "Estimate"] * df_ex["floorAreaRate"] / 100
    
        df_ex["V_vary"] = pd.Series(np.vectorize(calc_Vvary)
                                    (df_ex["V_usage1"], df_ex["V_usage2"], df_ex["V_usage3"], 
                                      df_ex["V_usage4"], df_ex["V_usage5"], df_ex["V_remove"], df_ex[f"Existing{year1pb}"], 
                                      prms.loc["lambda_YT", "Estimate"]))
        
        """ # 空地ならremainの効用はnull、建物ならlotの効用はnull"""
        df_ex.loc[df_ex[f"Existing{year1pb}"]==1, "V_lot"] = np.nan
        df_ex.loc[df_ex[f"Existing{year1pb}"]==2, "V_remain"] = np.nan
        
        """ # リストにいれて """
        df_list.append(df_ex[cols])
    
    """ # データフレームに復元して,seqでマージする """
    df_Vs = pd.concat(df_list, ignore_index = True)
    df_build = pd.merge(df_build, df_Vs, how = "left", on = ["seq"])

    """ # V_usage1 ~ V_removeまでの確率を計算 """
    for col in ["V_usage1", "V_usage2", "V_usage3", "V_usage4", "V_usage5", "V_remove"]:
        col_name = col.split("_")[1]
        df_build[f"prob_{col_name}"] = pd.Series(np.vectorize(calc_prob)(
                                                  df_build["V_usage1"], df_build["V_usage2"], df_build["V_usage3"],
                                                  df_build["V_usage4"], df_build["V_usage5"], df_build["V_remove"],
                                                  df_build[f"Existing{year1pb}"], col_name, prms.loc["lambda_YT", "Estimate"]))

    """ # V_vary, V_remain, V_lotの確率を計算 """
    for col in ["vary", "remain", "lot"]:
        prob = "prob_" + col
        veff = "V_" + col
        df_build[prob] = pd.Series(np.vectorize(calc_probNL1)
                                   (df_build["V_vary"], df_build["V_remain"], df_build["V_lot"],
                                    df_build[f"Existing{year1pb}"], veff, df_build["buildingID"]))
    
    # df_build.to_csv(rf"{root_out}/建設モデル確率計算NL_{year}.csv", index = False, encoding = "cp932")
    
    """ # prob_usage1 ~ prob_removeまでの確率を更新 """
    for col in ["prob_usage1", "prob_usage2", "prob_usage3", "prob_usage4", "prob_usage5", "prob_remove"]:
        df_build[col] = df_build[col] * df_build["prob_vary"]        

    """ # 判定用の乱数を振る """
    df_build[f"建設用途判定用乱数{year}"] = pd.Series(rng_1.random(len(df_build)), index = df_build.index)

    """ # シードを年+1000にする """
    # np.random.seed(year + 1000)

    """ # 確率は「5年間で生じる確率」なので、20%の確率でモデルを適用する """
    df_build["建設モデル適用乱数"] = pd.Series(rng_2.random(len(df_build)), index = df_build.index)
    # df_build.to_csv(rf"{root_out}/建設モデル確率計算_{year}.csv", index = False, encoding = "cp932")
    
    """ # 建設,用途判定 """
    df_build[f"Usage{year}"], df_build[f"Existing{year}"], df_build[f"BuildingAge{year}"], df_build[f"Buildingflag{year}"]= pd.Series(np.vectorize(calc_usage)
                                                                                                      (df_build["prob_usage1"], df_build["prob_usage2"], df_build["prob_usage3"],
                                                                                                      df_build["prob_usage4"], df_build["prob_usage5"], df_build["prob_remove"],
                                                                                                      df_build["prob_remain"], df_build["prob_lot"],
                                                                                                      df_build[f"Usage{year1pb}"], df_build[f"Existing{year1pb}"], df_build[f"BuildingAge{year1pb}"],
                                                                                                      df_build[f"建設用途判定用乱数{year}"], df_build["SimTargetFlag"],
                                                                                                      df_build["buildingID"],df_build["建設モデル適用乱数"]))

    """ # 統合処理 : 5年に1回程度 """
    """ # IFP****** : 複数のfootprintを束ねた大きいfootprintを作っているもの """
    """ # 商業のIFP*****を対象に建物ごとのログサムを計算→確率を計算して累積確率が乱数を最初に超えた1つを抜き出す """
    """ # → simtargetflagを1にする & existing = 1にする """
    """ # 統合された建物の用途を決める : 対象は全ての用途 """
    """ # 統合された建物の場所にあった建物のsimtargetflagを0にする & existing = 2にする """
    """ # 建物の対応関係はIntegrated_buildingIDに入るはず """
    if(year % 5 == 0):
    # if(year % 1 == 0):
        """ # IDに IFP を含む & SimTargetFlag = 0 の建物を抜き出す : 一度統合対象になったものは外す """
        df_build_ifp = df_build[(df_build["buildingID"].str.contains("IFP")) & (df_build["SimTargetFlag"] == 0)].reset_index(drop = True)

        if(len(df_build_ifp) > 0):
            
            # """ # 用途地域が 商業 or 近隣商業 に制限する """
            # df_build_ifp = df_build_ifp[df_build_ifp["UseDistrict"].isin([8,9])].reset_index(drop = True)
            
            """ # このデータフレームに対してログサムを計算する """
            df_build_ifp[f"lgsm_union{year}"] = pd.Series(np.vectorize(calc_lgsm)
                                                        (df_build_ifp["V_usage1"], df_build_ifp["V_usage2"], df_build_ifp["V_usage3"],
                                                        df_build_ifp["V_usage4"], df_build_ifp["V_usage5"]))
            
            """ # 確率を計算する """
            df_build_ifp[f"prob_union{year}"] = np.exp(df_build_ifp[f"lgsm_union{year}"]) / np.exp(df_build_ifp[f"lgsm_union{year}"]).sum()
            
            """ # 累積確率にして """
            df_build_ifp[f"cumprob_union{year}"] = df_build_ifp[f"prob_union{year}"].cumsum()
            
            """ # 乱数を振る """
            # np.random.seed(year + 42)
            
            df_build_ifp[f"rand_union"] = pd.Series(rng_3.random(len(df_build_ifp)), index = df_build_ifp.index)
            
            """ # 差分を取って,最初に正になったものを残す """
            df_build_ifp["diff_rand_cum"] = df_build_ifp[f"cumprob_union{year}"] - df_build_ifp[f"rand_union"]
            if(os.path.exists(r"output_swich")):
                df_build_ifp.to_csv(rf"{root_out}/{year}_建物統合確率.csv", index = False, encoding = "cp932")

            df_build_ifp = df_build_ifp[df_build_ifp["diff_rand_cum"] > 0].reset_index(drop = True)
            
            """ # 用途はいったん店舗併用共同住宅414で決め打ち """
            # print(df_build_ifp.loc[0, "buildingID"])
            
            """ # 元のデータフレームのインデックス番号を取得する """
            """ # → seq - 1 でとれるはず """
            ifp_seq = df_build_ifp.loc[0, "seq"] - 1
            # print(df_build.loc[ifp_seq, "buildingID"])
            
            """ # 元のデータフレームの情報を更新する """
            df_build.loc[ifp_seq, "SimTargetFlag"] = 1
            df_build.loc[ifp_seq, f"Usage{year}"] = 414
            df_build.loc[ifp_seq, f"Existing{year}"] = 1
            df_build.loc[ifp_seq, f"BuildingAge{year}"] = 1
            df_build.loc[ifp_seq, f"Buildingflag{year}"] = 1
            
            """ # 被統合対象の建物をデータフレームから除外する(simtargetflag → 0にする) """
            exclude_building = df_build.loc[ifp_seq, "buildingID"]
            df_exclude = df_build[(~df_build["buildingID"].str.contains(exclude_building)) & (df_build["Integrated_buildingID"].isin([exclude_building]))].reset_index(drop = True)
            # print(df_exclude)
            for i in range(len(df_exclude)):
                exc_ind = df_exclude.loc[i, "seq"] - 1
                df_build.loc[exc_ind, "SimTargetFlag"] = 0
                df_build.loc[exc_ind, f"Usage{year}"] = np.nan
                df_build.loc[exc_ind, f"Existing{year}"] = 2
                df_build.loc[exc_ind, f"BuildingAge{year}"] = np.nan
                df_build.loc[exc_ind, f"Buildingflag{year}"] = 0
                
    if(os.path.exists(r"output_swich")):
        df_build.to_csv(rf"{root_out}/建設モデル_{year}.csv", index = False, encoding = "cp932")



    return df_build
    
    
