# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd

def make_transition(year, sex, age_rank, category, rand, le_rand, df_trans):
    if(int(age_rank) <= 3):
        """ # 年齢階層 1 ~ 3 の場合は変化なし """
        return category
    else:
        """ # 遷移発生確率を満たした者に対して以下処理を入れる """
        if(le_rand < 0.2):
            """ # 変数に入れなおしてデータフレームとして扱えるようにしておく """
            df_trans = df_trans["trans"]
            """ # 遷移確率を抽出 """
            trans_prob = df_trans[(df_trans["年"] == year) & (df_trans["性別"] == sex) & (df_trans["年齢"] == age_rank) & (df_trans["旧"] == category)]
            """ # 抽出したデータフレームから新カテゴリのリストを作成する """
            new_category = trans_prob["新"].values.tolist()
            """ # 抽出したデータフレームから累積確率のリストを作る """
            prob_cum = trans_prob["累積確率"].values.tolist()

            """ # 累積確率を小さい方から順になめて、遷移先を確定 """
            for i in range(len(new_category)):
                if(prob_cum[i] >= rand):
                    return new_category[i]
                elif(i == len(new_category) - 1 and prob_cum[i] < rand):
                    sys.exit(f"category transition error !! {prob_cum[i]} < {rand}")
                else:
                    pass
        else:
            """ # 満たさない場合そのまま """
            return category

def category_transition(df_individual, df_trans, year, period, outset):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 遷移対象判定用乱数を付与 """
    df_individual[f"遷移対象判定用乱数{year}"] = pd.Series(np.random.random(len(df_individual)), index = df_individual.index)

    """ # カテゴリ遷移用乱数列を追加する """
    df_individual[f"カテゴリ遷移用乱数{year}"] = pd.Series(np.random.random(len(df_individual)), index = df_individual.index)
    
    """ # 1期前の年齢に対してカテゴリ遷移を判定する """
    year1pb = year - period
    # print(year1pb)
    year_index = f"{year1pb}-{year-2000}"

    """ # パラメータを辞書にして渡しにいく """
    dic_trans = {"trans":df_trans}
    df_individual[f"カテゴリ{year}"] = pd.Series(np.vectorize(make_transition)
                                             (year_index, 
                                              df_individual["世帯票_性別"], 
                                              df_individual[f"年齢階層{year1pb}"], 
                                              df_individual[f"カテゴリ{year1pb}"], 
                                              df_individual[f"カテゴリ遷移用乱数{year}"], 
                                              df_individual[f"遷移対象判定用乱数{year}"],
                                              dic_trans))

    """ # 配偶関係の列を作成 """
    df_individual[f"配偶関係{year}"] = df_individual[f"カテゴリ{year}"].astype(str).str[0:1].astype(int)
    
    """ # 出力 """
    if(outset["設定値"] == "T"):
        df_individual.to_csv(rf"{outset['フォルダ名']}/カテゴリ遷移モデル_{year}.csv", index = False, encoding = "cp932")
        
    """ # カテゴリ遷移計算終了 """
    return df_individual
    