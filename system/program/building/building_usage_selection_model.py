# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd


def get_prm(group, usage, key, df_prm):
    index_name = f"{group} {usage} {key}"
    
    try:
        prm = df_prm.loc[index_name, "param"]
    except KeyError:
        prm = 0.0
    
    return prm


def calc_eff(group, usage, hlp_area, clp_area, dnsta, const, dic_prm):
    """ # 用途選択効用関数 """
    
    """ # 辞書で受けたパラメータ一覧をデータフレームで受けなおす"""
    df_prm = dic_prm["prm"]
    
    """ # 計算に使うパラメータの辞書 """
    prm_keys = ["定数項", "商業地価x建物面積(m2)", "住宅地価x建物面積(m2)", "最寄り駅距離"]
    dic_prm = dict.fromkeys(prm_keys, 0)
    
    """ # パラメータのキーと引数の辞書 """
    dic_args = {"定数項":const, "商業地価x建物面積(m2)":clp_area, "住宅地価x建物面積(m2)":hlp_area, "最寄り駅距離":dnsta}

    """ # パラメータの取得 """
    for key in dic_prm.keys():
        dic_prm[key] = get_prm(group, usage, key, df_prm)
    
    """ # 効用の計算 """
    eff = 0.0
    for key in dic_prm.keys():
        eff += dic_prm[key] * dic_args[key]

    return eff
    
def calc_subtraction(h_eff, c_eff, a_eff, hc_eff, ha_eff):
    """ # オーバフローしないように調整する """
    """
        V = 709 まではexp(V)の計算が可能
        それ以上の場合、適当に引き算を入れる
        
        簡単のため2項ロジット
        V1, V2から計算される確率は
        P1 = exp(V1) / { exp(V1) + exp(V2) }
        分子・分母に同じ数をかけても比率は変わらない
        問題としては、Vが大きすぎることなので、ここで X = exp(-A)を分子・分母にかける
        すると、Viから同じ数を引くことに対応するので、
        P1' = exp(V1 - A) / { exp(V1 - A) + exp(V2 - A) }
        となる。
        この時、確率の比率に変化はない。
        
        オーバフロー対策として上記を用いる        
    """
    
    """ # 上限値の定義 """
    lim_up = 709
    
    """ # 一旦リストに入れる → 最大値、最小値が出しやすいので """
    nums = [h_eff, c_eff, a_eff, hc_eff, ha_eff]
    
    """ # 最大値、最小値を取得 """
    num_max = max(nums)
    num_min = min(nums)
    
    """ # underflowはなさそうなので、処理なし """
    if(num_max > lim_up):
        sub_n = abs(num_max - lim_up + 1) # バッファで1余計に引く
    else:
        sub_n = 0.0
    
    return sub_n
        
    

def calc_usagelgsm(df_build, df_prm, df_hlp, df_clp, df_lpv, year, period, outset):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 1期前の西暦を作る """
    year1pb = year - period

    """ # 最後に残す列のリスト """
    save_col = ["tatemono_code", f"yoto{year1pb}", "yotochiki", "usage_group", "AREA", "zone", "dist_Nsta",
                "住宅地価", "住宅地価x建物面積(m2)", "商業地価", "商業地価x建物面積(m2)",
                "log10_dist_Nsta", "定数項"]
            
    """ # 住宅地価と商業地価をマージする """
    df_build = pd.merge(df_build, df_hlp, how = "left", left_on = ["zone"], right_on = ["zone_code"])
    df_build = pd.merge(df_build, df_clp, how = "left", left_on = ["zone"], right_on = ["zone_code"])
    df_build = df_build.drop(["zone_code_x", "zone_code_y"], axis = 1)
    
    """ # 地価変化率をマージする """
    df_build = pd.merge(df_build, df_lpv, how = "left", left_on = ["zone"], right_on = ["zone_code"])
    
    """ # 商業地価の割引・割増 """
    df_build["商業地価"] = df_build["商業地価"] * df_build["都市機能誘導"]

    """ # 計算準備 """
    df_build["住宅地価x建物面積(m2)"] = df_build["住宅地価"] * df_build["AREA"] / 1000000
    df_build["商業地価x建物面積(m2)"] = df_build["商業地価"] * df_build["AREA"] / 1000000
    df_build["log10_dist_Nsta"] = np.log10(df_build["dist_Nsta"])
    df_build["定数項"] = 1
    
    """ # 用途別地域グループ別にログサムを計算する """
    use_list = ["住宅", "商業・商業系複合施設", "共同住宅", "店舗併用住宅", "店舗併用共同住宅"]

    dic_prm = {"prm":df_prm}
    """ # 用途別効用関数の計算 """
    for use in use_list:
        """ # 用途別効用 """
        col_eff = use + "_eff"
        save_col.append(col_eff)
        df_build[col_eff] = pd.Series(np.vectorize(calc_eff)
                                       (df_build["usage_group"], use, 
                                        df_build["住宅地価x建物面積(m2)"], df_build["商業地価x建物面積(m2)"],
                                        df_build["log10_dist_Nsta"], df_build["定数項"], dic_prm))
    
    """ # 用途別効用のチェック """
    """ # exp(V)のオーバフロー対策 """
    df_build["subtraction"] = pd.Series(np.vectorize(calc_subtraction)
                                        (df_build["住宅_eff"], df_build["商業・商業系複合施設_eff"],
                                         df_build["共同住宅_eff"], df_build["店舗併用住宅_eff"],
                                         df_build["店舗併用共同住宅_eff"]))
    save_col.append("subtraction")
    
    for use in use_list:
        df_build[f"{use}_eff"] = df_build[f"{use}_eff"] - df_build["subtraction"]
    
    """ # 用途別exp(V) """
    for use in use_list:
        df_build[f"{use}_exp"] = np.exp(df_build[f"{use}_eff"])
        save_col.append(f"{use}_exp")

    """ # Sigma exp(V) """
    df_build["sigma_expV"] = 0.0
    save_col.append("sigma_expV")
    for use in use_list:
        df_build["sigma_expV"] += df_build[f"{use}_exp"]
    
    """ # ログサム変数 """
    df_build[f"用途選択モデルログサム変数{year}"] = np.log(df_build["sigma_expV"])
    save_col.append(f"用途選択モデルログサム変数{year}")

    """ # 必要な列だけ残しておく """    
    df_build = df_build[save_col]
    
    """ # 出力 """
    if(outset["設定値"] == "T"):
        df_build.to_csv(rf"{outset['フォルダ名']}/用途選択ログサム_{year}.csv", index = False, encoding = "cp932")
    
    
    return df_build


def usage_select(bflag, rmflag, usage, p_home, p_comm, p_apart, p_hcom, p_hapa, rand, code):
    """ # 建設無し → 戻り値は現在の用途 """
    if(bflag == 0):
        if(rmflag == 1):
            """ # 除却フラグが立っていれば空地になるので """
            return "空地"
        else:
            """ # 建設が無く、除却フラグもなければ元のまま """
            return usage
    
    upper = 0
    """ # 辞書の形で用途とその確率を持っておく """
    dic_prob = {"住宅":p_home, "商業施設":p_comm, "共同住宅":p_apart, "店舗等併用住宅":p_hcom, "店舗等併用共同住宅":p_hapa}
    """ # 辞書のキーと値でループさせる """
    for u, p in dic_prob.items():
        """ # 確率の上限値を辞書から取ってきて足しこんでいく """
        upper += p
        
        if(rand <= upper):
            """ # ある時点で用途を返す """
            return u

def add_existflag(exist, rmflag, bflag, kaitai):
    """ # 「kaitai_year」が-1で無い場合、空地 """
    if(kaitai != -1):
        return 2
        
    if(bflag == 0):
        if(rmflag == 1):
            return 2
        else:
            return exist
    else:
        return 1


def building_usage_selection_model(df_build, df_lgsm, year, period, outset):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 1期前の西暦を作る """
    year1pb = year - period
    
    """ # df_lgsmの必要な列を残す """
    df_lgsm = df_lgsm[["tatemono_code", "住宅_exp", "商業・商業系複合施設_exp", "共同住宅_exp", "店舗併用住宅_exp", "店舗併用共同住宅_exp", "sigma_expV"]]
    
    """ # マージ """
    df_build = pd.merge(df_build, df_lgsm, how = "left", on = ["tatemono_code"])
    
    """ # 用途別に確率を計算 """
    use_list = ["住宅", "商業・商業系複合施設", "共同住宅", "店舗併用住宅", "店舗併用共同住宅"]
    for col in use_list:
        df_build[f"prob_{col}"] = df_build[f"{col}_exp"] / df_build["sigma_expV"]

    """ # 乱数の付与 """
    df_build["rand"] = pd.Series(np.random.random(len(df_build)), index = df_build.index)
    
    """ # 用途選択 """
    df_build[f"yoto{year}"] = pd.Series(np.vectorize(usage_select)
                                        (df_build[f"建設有無フラグ{year}"], df_build[f"除却フラグ{year}"], df_build[f"yoto{year1pb}"], 
                                          df_build["prob_住宅"], df_build["prob_商業・商業系複合施設"],
                                          df_build["prob_共同住宅"], df_build["prob_店舗併用住宅"],
                                          df_build["prob_店舗併用共同住宅"], df_build["rand"], df_build["tatemono_code"]))
    
    """ # 建物存在フラグの作成 """
    df_build[f"existing{year}"] = pd.Series(np.vectorize(add_existflag)
                                            (df_build[f"existing{year1pb}"], df_build[f"除却フラグ{year}"], 
                                             df_build[f"建設有無フラグ{year}"], df_build["kaitai_year"]))
        
    """ # 出力 """
    if(outset["設定値"] == "T"):
        df_build.to_csv(rf"{outset['フォルダ名']}/用途選択モデル_{year}.csv", index = False, encoding = "cp932")
    
    """ # 要らないものを落としておく """
    drop_col = ["住宅_exp", "商業・商業系複合施設_exp", "共同住宅_exp", "店舗併用住宅_exp", "店舗併用共同住宅_exp", "sigma_expV",
                "prob_住宅", "prob_商業・商業系複合施設", "prob_共同住宅", "prob_店舗併用住宅", "prob_店舗併用共同住宅",
                "rand"]
    df_build = df_build.drop(drop_col, axis = 1)
    
    """ # 返す """
    return df_build
    