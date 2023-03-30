# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd


def calc_eff(group, lgsm, hlp_area, stadist200, dic_prm):
    """ # パラメータを辞書で渡したので、データフレームで受けなおす """
    df_prm = dic_prm["prm"]
    
    if group == "G1":
        """ # パラメータを受け取り """
        const = df_prm.loc[f"{group} 定数項", "param"]
        var_lgsm = df_prm.loc[f"{group} 用途選択モデルログサム変数", "param"]
        """ # 効用計算 """
        eff = const + var_lgsm * lgsm
    elif group == "G2":
        """ # パラメータを受け取り """
        const = df_prm.loc[f"{group} 定数項", "param"]
        var_lparea = df_prm.loc[f"{group} 地価×面積", "param"]
        """ # 効用計算 """
        eff = const + var_lparea * hlp_area / 1000000
    elif group == "G3":
        """ # パラメータを受け取り """
        const = df_prm.loc[f"{group} 定数項", "param"]
        var_stadist200 = df_prm.loc[f"{group} 最寄り駅200mダミー", "param"]
        """ # 効用計算 """
        eff = const + var_stadist200 * stadist200
    elif group == "G4":
        """ # パラメータを受け取り """
        const = df_prm.loc[f"{group} 定数項", "param"]
        """ # 効用計算 """
        eff = const
    else:
        """ # パラメータを受け取り """
        const = df_prm.loc[f"{group} 定数項", "param"]
        var_lparea = df_prm.loc[f"{group} 地価×面積", "param"]
        """ # 効用計算 """
        eff = const + var_lparea * hlp_area / 1000000
        
    return eff

def add_buildflag(existing, rebuild_rand, rmflag, prob, prob_rand, kaitai):
    """ # 「kaitai_year」が-1だけを対象にする → -1で無いものは空地にする """
    if(kaitai != -1):
        return 0
    """ # 判定対象の建物に対して、建設対象か判定をする """
    if(existing == 1):
        """ # 1期前に建物がある場合 """
        if(rmflag == 1):
            """ # 除却フラグが立っている場合、乱数と比較して建設有無を判定 """
            """ # 閾値は調整の余地があるので、ハードコーディング """
            if(rebuild_rand < 0.365):
                """ # 閾値を満たしたので建設する """
                target = 1
            else:
                """ # 閾値を外したので、建設しない """
                target = 0
        else:
            """ # 除却フラグが立っていない場合は建設対象ではない """
            target = 0
    elif(existing == 2):
        """ # 建物が無い = 空地の場合、判定用乱数を用いて建設対象か判定 """
        if(rebuild_rand < 0.365):
            """ # 判定用乱数が条件を満たしたので、建設対象にする """
            target = 1
        else:
            """ # 建設対象条件を満たさないので、対象外 """
            target = 0
    
    """ # 建設対象に対して有無を判定する """
    if(target == 0):
        """ # 建設対象外 """
        return 0
    else:
        """ # 建設対象 """
        if(prob_rand <= prob):
            return 1
        else:
            return 0
    

def construction_model(df_build, df_prm, df_lgsm, year, period, outset):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 1期前の西暦を作る """
    year1pb = year - period
        
    """ # 用途選択ログサム変数をくっつける """
    df_build = pd.merge(df_build, df_lgsm[["tatemono_code", f"用途選択モデルログサム変数{year}", "住宅地価x建物面積(m2)"]], how = "left", on = ["tatemono_code"])
    
    """ # 建設有無の効用を計算する """
    dic_prm = {"prm":df_prm}
    df_build["建設効用"] = pd.Series(np.vectorize(calc_eff)
                                 (df_build["usage_group"], df_build[f"用途選択モデルログサム変数{year}"],
                                  df_build["住宅地価x建物面積(m2)"], df_build["最寄り駅200mダミー"], dic_prm))
    
    """ # 建設有無確率の計算 """
    df_build["建設確率"] = np.exp(df_build["建設効用"]) / (np.exp(df_build["建設効用"]) + np.exp(0))
    
    """ # 乱数の付与 """
    df_build[f"建て替え判定用乱数{year}"] = pd.Series(np.random.random(len(df_build)), index = df_build.index)
    
    """ # 乱数の付与 """
    df_build["rand"] = pd.Series(np.random.random(len(df_build)), index = df_build.index)
    
    """ # 建設有無判定 """
    df_build[f"建設有無フラグ{year}"] = pd.Series(np.vectorize(add_buildflag)
                                           (df_build[f"existing{year1pb}"], df_build[f"建て替え判定用乱数{year}"], df_build[f"除却フラグ{year}"],
                                            df_build["建設確率"], df_build["rand"], df_build["kaitai_year"]))
    
    """ # 新規建築数 """
    print(f"Number of construction at {year} : ", df_build[f"建設有無フラグ{year}"].sum())
    
    """ # 出力 """
    if(outset["設定値"] == "T"):
        df_build.to_csv(rf"{outset['フォルダ名']}/建設有無モデル_{year}.csv", index = False, encoding = "cp932")

    """ # 追加した一時列を落としておく """
    drop_col = ["建設効用", "建設確率", "rand"]
    df_build = df_build.drop(drop_col, axis = 1)

    """ # 返す """
    return df_build
