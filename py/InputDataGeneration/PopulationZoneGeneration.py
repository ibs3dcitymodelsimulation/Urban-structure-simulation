# -*- coding: utf-8 -*-
"""
Created on Wed Feb  7 21:25:41 2024

@author: amizuno
"""

import sys

import geopandas as gpd
import pandas as pd

import glob

def calc_ZoneApportionment():
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # Control Inputの読み込み """
    with open(rf"Control_Input.txt", mode = "r") as ci:
        root_inp = next(ci).strip()
        root_out = next(ci).strip()
        crs_code = next(ci).strip()
       
    """ゾーンポリゴンの読み込み"""
    df_zone = gpd.read_file( root_inp + "/Zone_Polygon.shp", encoding="cp932")
    df_zone.to_crs(crs_code,inplace=True)
    
    """メッシュの読み込み"""
    mesh = pd.DataFrame()
    for i in glob.glob( root_inp + "/zone_mesh/*.shp"):
        mesh0 = gpd.read_file( i , encoding="cp932")
        mesh0.to_crs(crs_code,inplace=True)
        
        mesh = pd.concat([mesh,mesh0])

    mesh["MeshArea"] = mesh['geometry'].area

    """人口テキストの読み込み"""
    Pop=pd.DataFrame()
    for j in glob.glob( root_inp + "/pop_mesh/*.txt"):
        Pop0 = pd.read_table( j ,dtype="object",encoding="cp932",sep=",")
        Pop0.loc[0,"KEY_CODE"]="KEY_CODE"
        Pop0.loc[0,"HTKSYORI"]="HTKSYORI"
        Pop0.loc[0,"HTKSAKI"]="HTKSAKI"
        Pop0.loc[0,"GASSAN"]="GASSAN"
        
        # 1行目を列名に設定
        Pop0.columns = Pop0.iloc[0]
        # 1行目を削除
        Pop0 = Pop0.drop(Pop0.index[0])
        # インデックスをリセット
        Pop0.reset_index(drop=True, inplace=True)

        Pop0 = Pop0[["KEY_CODE","HTKSYORI","HTKSAKI","GASSAN",
                 "　人口（総数）","　人口（総数）　男","　人口（総数）　女",
                 "　０～１４歳人口　総数","　０～１４歳人口　男","　０～１４歳人口　女",
                 "　１５～６４歳人口　総数","　１５～６４歳人口　男","　１５～６４歳人口　女",
                 "　６５歳以上人口　総数","　６５歳以上人口　男","　６５歳以上人口　女"
                 ]]

        Pop0 = Pop0.replace("*",0)
        Pop0 = Pop0.fillna(0)
        
        Pop = pd.concat([Pop,Pop0])

    """メッシュと人口を結合"""
    mesh2 = pd.merge(mesh,Pop,on="KEY_CODE",how="inner")
    
    """按分処理の過程"""
    #####交差の実行#####
    #交差　→　ゾーンポリゴンとメッシュの分割
    mesh3 = gpd.overlay(mesh2, df_zone, how='intersection')

    #1)小地域ポリゴンがメッシュに占める割合（按分）
    mesh3["SpritArea"] = mesh3['geometry'].area
    mesh3["AreaRate"] = mesh3["SpritArea"] / mesh3["MeshArea"]

    #2)メッシュごとの男女別人口（年齢不詳込みの人口）
    mesh3["人口総数男1"] = mesh3["　人口（総数）　男"].astype(int)*mesh3["AreaRate"]
    mesh3["人口総数女1"] = mesh3["　人口（総数）　女"].astype(int)*mesh3["AreaRate"]

    #3)メッシュごとの性別年齢別人口の割合
    int_columns = ["　０～１４歳人口　男", "　１５～６４歳人口　男", "　６５歳以上人口　男", "　０～１４歳人口　女", "　１５～６４歳人口　女", "　６５歳以上人口　女"]
    mesh3[int_columns] = mesh3[int_columns].astype(int)

    allpops_man = mesh3["　０～１４歳人口　男"] + mesh3["　１５～６４歳人口　男"] + mesh3["　６５歳以上人口　男"]
    allpops_woman = mesh3["　０～１４歳人口　女"] + mesh3["　１５～６４歳人口　女"] + mesh3["　６５歳以上人口　女"]

    mesh3["0~14歳_男r"] = mesh3["　０～１４歳人口　男"] / allpops_man
    mesh3["0~14歳_女r"] = mesh3["　０～１４歳人口　女"] / allpops_woman
    mesh3["15~64歳_男r"] = mesh3["　１５～６４歳人口　男"] / allpops_man
    mesh3["15~64歳_女r"] = mesh3["　１５～６４歳人口　女"] / allpops_woman
    mesh3["65歳~_男r"] = mesh3["　６５歳以上人口　男"] / allpops_man
    mesh3["65歳~_女r"] = mesh3["　６５歳以上人口　女"] / allpops_woman
        
    #4)メッシュごとの性別年齢階級別人口の算出　※不明を割合で按分する
    mesh3["0~14歳_男"] = mesh3["人口総数男1"]*mesh3["0~14歳_男r"]
    mesh3["0~14歳_女"] = mesh3["人口総数女1"]*mesh3["0~14歳_女r"]
    mesh3["15~64歳_男"] = mesh3["人口総数男1"]*mesh3["15~64歳_男r"]
    mesh3["15~64歳_女"] = mesh3["人口総数女1"]*mesh3["15~64歳_女r"]
    mesh3["65歳~_男"] = mesh3["人口総数男1"]*mesh3["65歳~_男r"]
    mesh3["65歳~_女"] = mesh3["人口総数女1"]*mesh3["65歳~_女r"]

    #5-0)人口
    mesh3 = mesh3.fillna(0)
    allpops_man2 = sum(mesh3["0~14歳_男"]+mesh3["15~64歳_男"]+mesh3["65歳~_男"])
    allpops_woman2 = sum(mesh3["0~14歳_女"]+mesh3["15~64歳_女"]+mesh3["65歳~_女"])

    pop_0_14_men = sum(mesh3["0~14歳_男"]) / allpops_man2
    pop_15_64_men = sum(mesh3["15~64歳_男"]) / allpops_man2
    pop_65_men = sum(mesh3["65歳~_男"]) / allpops_man2
    pop_0_14_women = sum(mesh3["0~14歳_女"]) / allpops_woman2
    pop_15_64_women = sum(mesh3["15~64歳_女"]) / allpops_woman2
    pop_65_women = sum(mesh3["65歳~_女"]) / allpops_woman2
    
    #5-1)秘匿処理をしているものを対象に、5-0で出した割合で、メッシュごとの性別年齢階層別人口を算出する
    mesh3["0~14歳_男"].mask( mesh3["HTKSYORI"].isin(["2"]) , mesh3["人口総数男1"]*pop_0_14_men ,inplace=True)
    mesh3["0~14歳_女"].mask( mesh3["HTKSYORI"].isin(["2"]) , mesh3["人口総数女1"]*pop_0_14_women ,inplace=True)
    mesh3["15~64歳_男"].mask( mesh3["HTKSYORI"].isin(["2"]) , mesh3["人口総数男1"]*pop_15_64_men ,inplace=True)
    mesh3["15~64歳_女"].mask( mesh3["HTKSYORI"].isin(["2"]) , mesh3["人口総数女1"]*pop_15_64_women ,inplace=True)
    mesh3["65歳~_男"].mask( mesh3["HTKSYORI"].isin(["2"]) , mesh3["人口総数男1"]*pop_65_men ,inplace=True)
    mesh3["65歳~_女"].mask( mesh3["HTKSYORI"].isin(["2"]) , mesh3["人口総数女1"]*pop_65_women ,inplace=True)

    """アウトプットのための整形処理"""
    #ZonePolygonの番号から、整理
    zone2 = mesh3[["zone_code","0~14歳_男","0~14歳_女","15~64歳_男","15~64歳_女","65歳~_男","65歳~_女"]].groupby(["zone_code"] , as_index=False).agg("sum")
    zone2 = zone2.melt(id_vars="zone_code")

    zone2["age"]=0
    zone2["gender"]=0
    zone2["age"].mask( zone2["variable"].str.contains('15~64') , 1 ,inplace=True)
    zone2["age"].mask( zone2["variable"].str.contains('65歳~') , 2 ,inplace=True)
    zone2["gender"].mask( zone2["variable"].str.contains('男') , 1 ,inplace=True)
    zone2["gender"].mask( zone2["variable"].str.contains('女') , 2 ,inplace=True)

    zone2.rename(columns={"value":"pop"},inplace=True)

    zone2 = zone2[["zone_code","age","gender","pop"]]

    #整形
    pop_zone = pd.DataFrame()
    n=0    
    for k in df_zone["zone_code"].to_list():
        pop_zone0 = pd.DataFrame()
        pop_zone0.loc[n,"zone_code"] = k
        pop_zone0.loc[n+1,"zone_code"] = k
        pop_zone0.loc[n+2,"zone_code"] = k
        pop_zone0.loc[n+3,"zone_code"] = k
        pop_zone0.loc[n+4,"zone_code"] = k
        pop_zone0.loc[n+5,"zone_code"] = k
        
        pop_zone0.loc[n,"age"] = 0
        pop_zone0.loc[n+1,"age"] = 0
        pop_zone0.loc[n+2,"age"] = 1
        pop_zone0.loc[n+3,"age"] = 1
        pop_zone0.loc[n+4,"age"] = 2
        pop_zone0.loc[n+5,"age"] = 2
        
        pop_zone0.loc[n,"gender"] = 1
        pop_zone0.loc[n+1,"gender"] = 2
        pop_zone0.loc[n+2,"gender"] = 1
        pop_zone0.loc[n+3,"gender"] = 2
        pop_zone0.loc[n+4,"gender"] = 1
        pop_zone0.loc[n+5,"gender"] = 2
        
        pop_zone = pd.concat([pop_zone,pop_zone0])

    pop_zone = pd.merge(pop_zone,zone2,on=["zone_code","age","gender"],how="outer")
    
    #Inputファイルに吐き出し、個人データ生成機能へ
    pop_zone.to_csv( root_inp + "/Population_Zone.csv",index=False) 
    
    return pop_zone

if __name__ == '__main__':
    pop_zone = calc_ZoneApportionment()