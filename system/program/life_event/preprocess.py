# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd


""" # 遷移確率の事前処理関数 """
def pp_transitionprob(df):
    print("Function : ", sys._getframe().f_code.co_name)

    """ # 事前処理 1 : 確率が 0 以上のみに絞る """
    df = df[df["確率"] > 0].reset_index(drop = True)

    """ # 事前処理 2 : ソート """
    df = df.sort_values(["年", "性別", "年齢", "旧", "新"], ignore_index = True)

    """ # 事前処理 3 : 集計 """
    df_agg = df.groupby(["年", "性別", "年齢", "旧"], as_index = False).agg({"確率":sum})
    df_agg = df_agg.rename(columns = {"確率":"確率計"})

    """ # 事前処理 4 : 確率の対応付け """
    df = pd.merge(df, df_agg, on = ["年", "性別", "年齢", "旧"], validate = "m:1")

    """ # 事前処理 5 : 確率を補正 """
    df["確率補正"] = df["確率"] / df["確率計"]

    """ # 事前処理 6 : 年・性別・年齢・旧別の累積確率を計算 """
    df["累積確率"] = df.groupby(["年", "性別", "年齢", "旧"], as_index = False)["確率補正"].cumsum()

    """ # 事前処理 7 : 年齢ランクの最大値を取ってくる """
    agerank_max = df["年齢"].max()
    
    """ # キーと累積確率があればいい """
    df = df.drop(columns = ["確率", "確率計", "確率補正"])
    
    """ # キー["年", "性別", "年齢", "旧"]をユニークにしたい """
    df_keys = df[["年", "性別", "年齢", "旧"]].drop_duplicates().reset_index(drop = True)
    
    return df, df_keys, agerank_max
    
""" # 個人データの列名にシミュレーション開始年を追記する """
def pp_individual(df, ini_year):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 処理 1 : 列名の変更 """
    col_dic = {}
    for i in range(len(df.columns.values)):
        if(df.columns.values[i] not in ["個人ユニークID", "世帯票_性別", "拡大係数"]):
            col_dic[df.columns.values[i]] = df.columns.values[i] + str(ini_year)
    df = df.rename(columns = col_dic)
    
    """ # 処理 2 : indexから整理用個人ID(連番)を作成 """
    df["個人ID"] = df.index.astype(str).str.pad(7, fillchar = "0")
    
    return df

""" # パラメータファイル """
def pp_prmfile(df):
    df = df.set_index("variable")
    
    return df
