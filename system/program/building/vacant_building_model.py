# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd

from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN


def check_vb(vacant, house, withstore):
    if(vacant > house + withstore):
        return int(house + withstore)
    else:
        return int(vacant)


def vacant_building_model(df_build_org, df_zone_org, df_pop, df_prm, year, period, out_nzvb, out_vbf):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 建物データとゾーンデータをコピーして使う """
    df_build = df_build_org.copy()
    df_zone = df_zone_org["zone_code"].copy()
        
    """ # まずは、住宅、共同住宅、店舗併用住宅をゾーン別に集計 """
    """ # カウント用のダミー変数を作っておく """
    df_build["建物数"] = 1
    
    """ # ゾーン別用途別に集計 """
    dfp_build = pd.pivot_table(df_build, values = "建物数", index = "zone", columns = f"yoto{year}", aggfunc = sum)
    
    """ # 「0」埋めして、インデックスを戻す """
    dfp_build = dfp_build.fillna(0).reset_index()
    dfp_build = dfp_build.rename(columns = {"zone":"zone_code"})
    
    """ # ゾーンデータに人口と建物数をマージする """
    """ # 転居と建て替え次第で落ちている可能性があるので、オリジナルのゾーンデータにマージする方が安全と判断 """
    df_zone = pd.merge(df_zone, df_pop, how = "left", on = ["zone_code"])
    df_zone = pd.merge(df_zone, dfp_build, how = "left", on = ["zone_code"])

    """ # 「0」埋めしておく """
    df_zone = df_zone.fillna(0)
    
    """ # ゾーン別空家数の計算 """
    """ # パラメータを受ける """
    const = df_prm.loc["定数項", "param"]
    var_pop = df_prm.loc["pop_all", "param"]
    var_j = df_prm.loc["tatemonocount_j", "param"]
    var_kj = df_prm.loc["tatemonocount_kj", "param"]
    var_tj = df_prm.loc["tatemonocount_tj", "param"]
    
    """ # 計算 """
    df_zone["空家数_計算値"] = const + var_pop * df_zone["pop_all"] + var_j * df_zone["住宅"] + var_kj * df_zone["共同住宅"] + var_tj * df_zone["店舗等併用住宅"]

    """ # 小数点第1位を四捨五入で整数化 """
    df_zone["空家数_整数化"] = df_zone["空家数_計算値"].apply(lambda x: Decimal(str(x)).quantize(Decimal("0"), rounding = ROUND_HALF_UP))
    
    """ # 空家フラグを立てるのは「住宅と店舗等併用住宅のみ」なので、数のチェックをする """
    df_zone["空家数"] = pd.Series(np.vectorize(check_vb)
                               (df_zone["空家数_整数化"], df_zone["住宅"], df_zone["店舗等併用住宅"]))
    
    """ # 出力設定 """
    if(out_nzvb["設定値"] == "T"):
        df_zone.to_csv(rf"{out_nzvb['フォルダ名']}/ゾーン別空家数_{year}.csv", index = False, encoding = "cp932")
    
    """ # 空家フラグを立てる処理 """
    """ # 準備 : フラグ付与に必要な項目をデータフレームからコピー """
    df_target = df_build[["tatemono_code", "zone", f"yoto{year}", f"building_age{year}", f"existing{year}"]].copy()
    
    """ # 建物が存在している & フラグ付与対象の用途で抽出 """
    df_target = df_target[(df_target[f"existing{year}"] == 1) & (df_target[f"yoto{year}"].isin(["住宅", "店舗等併用住宅"]))].reset_index(drop = True)
    
    """ # フラグ用データフレームのリスト """
    list_df_flag = []
    
    """ # ゾーンに対してループ """
    for i in range(len(df_zone)):
        """ # ゾーンコードと対応する空家数を取得 """
        zone = df_zone.loc[i, "zone_code"]
        vacant = df_zone.loc[i, "空家数"]

        """ # データフレームの抽出 """
        df_tmp = df_target[df_target["zone"] == zone].reset_index(drop = True)
        
        """ # 古い順に並び替え → ageを降順 """
        """ # .head(n)でデータフレームの先頭からn行取得できるので、これで空家数分だけ抽出 """
        df_tmp = df_tmp.sort_values(f"building_age{year}", ascending = False).head(vacant)
        
        """ # リストに追加しておく """
        list_df_flag.append(df_tmp)
    
    """ # ゾーンのループ終わり """
    """ # リストにあるデータフレームを全部結合して、1つのデータフレームにする """
    df_flag = pd.concat(list_df_flag, axis = 0, ignore_index = True)

    """ # 空家フラグを入れて """
    df_flag[f"空家フラグ{year}"] = 1
    
    """ # ここで建物データにマージする """
    df_build = pd.merge(df_build, df_flag[["tatemono_code", f"空家フラグ{year}"]], how = "left", on = ["tatemono_code"])
    
    """ # 空家対象外には「NaN」が入っているので、「0」に置換する """
    df_build[f"空家フラグ{year}"] = df_build[f"空家フラグ{year}"].fillna(0)
    
    """ # カウント用のダミー変数が生き残っているので落とす """
    df_build = df_build.drop(["建物数"], axis = 1)
    
    """ # 出力設定 """
    if(out_vbf["設定値"] == "T"):
        df_build.to_csv(rf"{out_vbf['フォルダ名']}/空家フラグ付与_{year}.csv", index = False, encoding = "cp932")
    
    return df_build
