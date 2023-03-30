# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd


def bid_rent_model(df_zone_org, df_prm, df_pc, df_std, year, outset):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # ゾーンデータのコピー """
    df_zone = df_zone_org.copy()
    
    """ # 保存する列名のリスト """
    col_save = ["zone_code", "j_senyo", "j_tiki", "s_tiki"]
    
    """ # ログサム計算対象の列リストを作成する """
    pc_list = list(df_pc.index)
    
    """ # 標準化する """
    for col in pc_list:
        col_std = col + "_std"
        df_zone[col_std] = (df_zone[col] - df_std.loc[col, "mean"]) / df_std.loc[col, "std"]
    
    """ 
        # 主成分と説明変数とロット（世帯選択実績データ）を入れたらシミュレーションする関数
        ######################
        # 説明変数×主成分スコアの内積をとった主成分を用意する
        ######################
    """
    """ # 主成分作成 """
    for i in range(1,6):
        col_name = f"PC{i}"
        pc_name = f"rotation.{col_name}"
        df_zone[col_name] = 0.0
        for j in pc_list:
            col_std = j + "_std"
            df_zone[col_name] += df_pc.loc[j, pc_name] * df_zone[col_std]
    
    """ # 効用関数の作成 """
    for i in range(0,4):
        col_name = f"V{i}"
        col_save.append(col_name)
        df_zone[col_name] = df_prm.loc[f"asc_{i}","param"]
        for j in range(1,4):
            df_zone[col_name] += df_prm.loc[f"b_PC{j}_{i}","param"] * df_zone[f"PC{j}"]
    
    """ # ログサムの作成 """
    df_zone["lgsm"] = 0.0
    for i in range(0,4):
        df_zone["lgsm"] += np.exp(df_zone[f"V{i}"])
    df_zone["lgsm"] = np.log(df_zone["lgsm"])
    col_save.append("lgsm")
    
    """ # この時点で一旦出力 """
    if(outset["設定値"] == "T"):
        df_zone.to_csv(rf"{outset['フォルダ名']}/ゾーン別付け値地代モデルログサム変数_{year}.csv", index = False, encoding = "cp932")
    
    """ # 住宅地価の計算に使うものを返す """
    df_brm = df_zone[col_save].copy()
    
    return df_brm
