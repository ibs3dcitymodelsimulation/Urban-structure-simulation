# -*- coding: utf-8 -*-
"""
Created on Mon Aug 22 15:38:50 2022

@author: ktakahashi
"""

import os
import sys
import codecs

import numpy as np
import pandas as pd
import geopandas as gpd

from chardet.universaldetector import UniversalDetector

pd.set_option("display.max_columns",100)


def read_control(path, index = None):
    print("Function : ", sys._getframe().f_code.co_name)

    df = pd.read_csv(rf"{path}", encoding = "cp932", index_col = index)
    return df
                
def check_encoding(file_path):
    detector = UniversalDetector()
    with open(file_path, mode='rb') as f:
        for binary in f:
            detector.feed(binary)
            if detector.done:
                break
    detector.close()
    
    return detector.result['encoding']

def read_input(root_inp, file):
    print("reading file :", file)

    file = os.path.join(root_inp, file)
    
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
    elif(ext == ".shp"):
        df = gpd.read_file(file)
    else:
        print("extention is not match csv or xlsx")
        sys.exit(0)
    
    return df
