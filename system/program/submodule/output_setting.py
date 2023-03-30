# -*- coding: utf-8 -*-

import os
import sys

import pandas as pd

def output_setting():
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 出力設定を読み込む """
    df = pd.read_csv(r"../setting/output_setting.csv", encoding = "cp932")
    
    """ # OSSリリース用(2023/02/03) """
    """ # 出力ファイル設定を制限 """
    nn = len(df)
    list_le = ["カテゴリ遷移モデル", "有配偶率", "有配偶者出生率", "出生モデル", "居住形態モデル",
               "転居発生有無モデル", "ゾーン別選択確率", "居住地選択モデル"]
    for i in range(len(list_le)):
        df.loc[i + nn, "分類"] = "01_ライフイベント"
        df.loc[i + nn, "名称"] = list_le[i]
        df.loc[i + nn, "設定値"] = "F"
    
    nn = len(df)
    list_bd = ["付け値地代モデル", "住宅地価モデル", "商業地価モデル", "除却有無モデル", "用途選択ログサム",
               "建設有無モデル", "用途選択モデル", "建物年齢モデル", "階数モデル", "延べ床面積モデル",
               "建物高さモデル", "変遷フラグ", "ゾーン別空家数", "空家フラグ付与"]
    for i in range(len(list_bd)):
        df.loc[i + nn, "分類"] = "02_建物モデル"
        df.loc[i + nn, "名称"] = list_bd[i]
        df.loc[i + nn, "設定値"] = "F"
    
    nn = len(df)
    list_dt = ["年次別建物面積", "年次別建物数集計", "年次別ゾーン別人口"]
    for i in range(len(list_dt)):
        df.loc[i + nn, "分類"] = "03_年次別データ"
        df.loc[i + nn, "名称"] = list_dt[i]
        df.loc[i + nn, "設定値"] = "F"
        
    """ # 出力チェック """
    num_out = (df == "T").sum().sum()
    if(num_out == 0):
        print("None output !!")
        print("please at least one output setting !!")
        sys.exit(0)
    
    """ # フォルダ作成 """
    df["フォルダ名"] = "../output/" + df["分類"] + "/" + df["名称"]
    for i in range(len(df)):
        if(df.loc[i,"設定値"] == "T"):
            os.makedirs(df.loc[i,"フォルダ名"], exist_ok = True)

    """ # インデックスを変えておく """
    df = df.set_index("名称")

    return df
