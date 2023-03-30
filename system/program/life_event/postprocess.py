# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd


def postprocess(df_individual, year, period, outset):
    print("Function : ", sys._getframe().f_code.co_name)

    """ # 個人データの整理をする """
    """ # 判定用乱数とか前期のデータはもう要らないので、落とす """

    """ # 残すものは年次のついていないデータ """
    col_save = ["個人ユニークID", "世帯票_性別", "拡大係数", "個人ID"]
    
    """ # 残す列名を選ぶ """
    for col in df_individual.columns:
        """ # 年次が該当年で、「乱数」と「パラメータ」が列名にないもの """
        if(str(year) in col and ("乱数" not in col and "カテゴリ遷移パラメータ" not in col)):
            col_save.append(col)
    
    """ # ここで残すものだけにする """
    df_individual = df_individual[col_save]
    
    """ # 出力 """
    if(outset["設定値"] == "T"):
        df_out = df_individual.rename(columns = {f"カテゴリ{year}":"カテゴリ",
                                                f"配偶関係{year}":"配偶関係",
                                                f"世帯票_年齢{year}":"世帯票_年齢",
                                                f"世帯内最小年齢{year}":"世帯内最小年齢",
                                                f"年齢階層{year}":"年齢階層",
                                                f"出生有フラグ{year}":"出生有フラグ",
                                                f"最小子供年齢{year}":"最小子供年齢",
                                                f"転居発生有無フラグ{year}":"転居発生有無フラグ",
                                                f"現住所{year}":"現住所"
                                                })
        df_out["出生有フラグ"] = df_out["出生有フラグ"].fillna(0)
        df_out = df_out[["個人ID","現住所","世帯票_性別","世帯票_年齢","年齢階層","拡大係数","カテゴリ","配偶関係","世帯内最小年齢","出生有フラグ","転居発生有無フラグ"]].copy()
        df_out.to_csv(rf"{outset['フォルダ名']}/annual_individual_data_{year}.csv", index = False, encoding = "cp932")
        
    """ # ゾーン別人口更新 """
    return df_individual

