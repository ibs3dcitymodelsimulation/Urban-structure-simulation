# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd

from chardet.universaldetector import UniversalDetector

def read_setting():
    print("Function : ", sys._getframe().f_code.co_name)

    df = pd.read_csv(r"../setting/setting.csv", encoding = "cp932", index_col = "名称")
    return df

def read_control():
    print("Function : ", sys._getframe().f_code.co_name)
    
    df = pd.read_csv(r"../setting/control.csv", encoding = "cp932", index_col = "指標名")
    return df

def check_setting(df, control):
    print("Function : ", sys._getframe().f_code.co_name)
    """ # OSSリリース用設定に変更 """
    df.loc["開始年", "設定値"] = 2019
    df.loc["間隔", "設定値"] = 1
    df.loc["乱数シード", "設定値"] = 1
    df.loc["推計外建物データの付与"] = 1
    df["設定値"] = df["設定値"].astype(int)
    
    """ # 終了年のチェック """
    if(df.loc["終了年", "設定値"] < 2021 or 2040 < df.loc["終了年", "設定値"]):
        print("終了年 : ", df.loc["終了年", "設定値"])
        print("終了年は 2021 ~ 2040 で設定して下さい")
        sys.exit(0)
    
    # """ # 開始・終了年のチェックだけ入れ込んでおく """
    # if(df.loc["開始年", "設定値"] < 2015 or 2039 < df.loc["開始年", "設定値"]):
    #     print("開始年 : ", df.loc["開始年", "設定値"])
    #     print("開始年は 2015 ~ 2039 で設定して下さい")
    #     sys.exit(0)

    # if(df.loc["終了年", "設定値"] < 2016 or 2040 < df.loc["終了年", "設定値"]):
    #     print("終了年 : ", df.loc["終了年", "設定値"])
    #     print("終了年は 2016 ~ 2040 で設定して下さい")
    #     sys.exit(0)
        
    # if(df.loc["終了年", "設定値"] <= df.loc["開始年", "設定値"]):
    #     print("開始年 : ", df.loc["開始年", "設定値"])
    #     print("終了年 : ", df.loc["終了年", "設定値"])
    #     print("終了年が開始年以前の設定となっています。設定を見直してください")
    #     sys.exit(0)

                    
def check_encoding(file_path):
    detector = UniversalDetector()
    with open(file_path, mode='rb') as f:
        for binary in f:
            detector.feed(binary)
            if detector.done:
                break
    detector.close()
    
    return detector.result['encoding']

def read_input(file):
    print("reading file :", file)
    
    """ # 拡張子を取得 → 読み込み関数を分けるため """
    ext = os.path.splitext(file)[1]
    
    """ # データフレームに読み込み """
    if(ext == ".csv"):
        try:
            df = pd.read_csv(file, encoding = "cp932", engine = "python")
        except UnicodeDecodeError as ue:
            encode = check_encoding(file)
            try:
                df = pd.read_csv(file, encoding = encode, engine = "python")
            except:
                print(f"{file} encoding can not detect")
                print("please check your file, sorry")
                sys.exit(0)
    elif(ext == ".xlsx" or ext == ".xls"):
        df = pd.read_excel(file)
    else:
        print("extention is not match csv or xlsx")
        sys.exit(0)
    
    return df

def set_randomseed(flag, year):
    if(flag == 0):
        """ # 乱数シードは0 """
        np.random.seed(0)
    elif(flag == 1):
        """ # 乱数シードはシミュレーション対象年 """
        np.random.seed(year)
    elif(flag == 2):
        """ # 乱数シードを乱数で指定 """
        np.random.seed(np.random.random)
    else:
        """ # 乱数シードの固定無し """
        pass

        