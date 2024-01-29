# -*- coding: utf-8 -*-
"""
Created on Thu Sep 14 14:47:49 2023

@author: ktakahashi
"""

import os
import sys

# import time

import numpy as np
import pandas as pd


def make_transition_v3(age_rank, le_rand, category, new_category):
    if(int(age_rank) <= 3):
        """ # 年齢階層 1 ~ 3 の場合は変化なし """
        return category
    else:
        if(le_rand < 0.2):
            """ # 遷移発生確率を満たした場合,新カテゴリへ """
            return new_category
        else:
            """ # 満たさない場合そのまま """
            return category


def category_transition(df_individual, df_trans, year, root_out):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 遷移対象判定用乱数を付与 """
    df_individual[f"遷移対象判定用乱数{year}"] = pd.Series(np.random.random(len(df_individual)), index = df_individual.index)

    """ # カテゴリ遷移用乱数列を追加する """
    df_individual[f"カテゴリ遷移用乱数{year}"] = pd.Series(np.random.random(len(df_individual)), index = df_individual.index)

    """ # 乱数をケース間で固定したいこころみ """
    np.random.seed(year)
    randlist = np.random.random(10000000)
    df_individual[f"遷移対象判定用乱数{year}"] = df_individual["Personal_UniqueId"].apply(lambda x:randlist[x])
    randlist = np.random.random(10000000)
    df_individual[f"カテゴリ遷移用乱数{year}"] = df_individual["Personal_UniqueId"].apply(lambda x:randlist[x])


    """ # 1期前の年齢に対してカテゴリ遷移を判定する """
    period = 1
    year1pb = year - period
    # print(year1pb)
    # year_index = f"{year1pb}-{year-2000}"
    
    # 年度に基づいて、社人研の遷移確率の年刻みを返す関数
    def get_year_range(year_index):
        # 最初の年
        start_year = (year_index // 5) * 5
        # 最後の年
        end_year = start_year + 5 - 2000
        # 年代の文字列を返す
        return f"{start_year}-{end_year}"
    year_index = get_year_range(year1pb)


    """ # 遷移確率パラメータから,計算対象年次だけに絞る """
    df_trans_y = df_trans[df_trans["年"] == year_index]
    
    """ # 個人データに遷移確率を割り付ける 
        # 一時的にレコード数が増えるので遷移確率を割り付ける個人データは別のデータフレームにする 
    """
    df_ind = pd.merge(df_individual, df_trans_y, how = "left", 
                      left_on = ["Gender", f"Age_Group{year1pb}", f"Marital_Status_Family_Position{year1pb}"],
                      right_on = ["性別", "年齢", "旧"])
    
    """ # 各レコードでカテゴリ遷移用の乱数との差分を取る """
    df_ind["diff"] = df_ind["累積確率"] - df_ind[f"カテゴリ遷移用乱数{year}"]
    
    """ # 差分が正になるものを抜き出す """
    df_ind = df_ind[(df_ind[f"Age_Group{year1pb}"] <= 3) | (df_ind["diff"] > 0)].reset_index(drop = True)
    
    """ # 個人ID毎に最初のレコードだけ残す """
    df_indagg = df_ind.groupby("Personal_UniqueId").first().reset_index()
    # print(df_indagg)
    # df_indagg.to_csv(rf"{root_out}/カテゴリ遷移計算agg_{year}.csv", index = False, encoding = "cp932")
    
    """ # 必要なものだけ残す """
    df_indagg = df_indagg[["Personal_UniqueId", "新"]]
    
    """ # もともとの個人データに割り付ける """
    df_individual = pd.merge(df_individual, df_indagg, how = "left", on = ["Personal_UniqueId"])
    
    """ # カテゴリの遷移後のコードを取得する """
    df_individual[f"Marital_Status_Family_Position{year}"] = pd.Series(np.vectorize(make_transition_v3)
                                                                       (df_individual[f"Age_Group{year1pb}"],
                                                                        df_individual[f"遷移対象判定用乱数{year}"],
                                                                        df_individual[f"Marital_Status_Family_Position{year1pb}"],
                                                                        df_individual["新"]))


    """ # カテゴリ99 = 死亡者をデータフレームから外す """
    # df_dead = df_individual[df_individual[f"Marital_Status_Family_Position{year}"] == 99]
    # df_dead.to_csv(rf"{root_out}/カテゴリ99_{year}.csv", index = False, encoding = "cp932")
    df_individual = df_individual[df_individual[f"Marital_Status_Family_Position{year}"] != 99].reset_index(drop = True)

    """ # 配偶関係の列を作成 """
    df_individual[f"Marital_Status{year}"] = df_individual[f"Marital_Status_Family_Position{year}"].astype(str).str[0:1].astype(int)
    
    """ # Family_Typeを作成 → カテゴリの2桁目 """
    df_individual[f"Family_Position{year}"] = df_individual[f"Marital_Status_Family_Position{year}"].astype(str).str[1:2].astype(int)
    
    """ # 出力 """
    # df_individual.to_csv(rf"{root_out}/カテゴリ遷移モデル_{year}.csv", index = False, encoding = "cp932")
    # sys.exit(0)
    """ # カテゴリ遷移計算終了 """
    return df_individual
    