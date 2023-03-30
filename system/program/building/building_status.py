# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd


def transition_flag(exist_org, exist_now, exist_num, bflag_num, years):
    """ # 起点年次の状態判定 """
    if(exist_org == 1):
        code_org = "建物"
    else:
        code_org = "空地"

    """ # 終点年次の状態判定 """
    """ # 直前で、建物が存在しない場合を「0」に置き換えているので """
    if(exist_now == 0):
        code_now = "空地"
    else:
        """ # 建物が存在 """
        if(exist_num == years):
            """ # 経過年次数と建物存在年次数が一致 """
            if(bflag_num == 0):
                """ # 建設有無フラグが一回も立っていない """
                code_now = "建物（維持）"
            elif(bflag_num > 0):
                """ # 建設有無フラグが一回以上立っている """
                code_now = "建物（建て替え）"
            else:
                """ # 建設有無フラグの総数が負の数 """
                """ # あり得ないはずだけど念のため """
                print("total number of building flag is negative !!")
                print("program is something wrong !!")
                print("check flag add program !!")
                sys.exit(0)
        elif(exist_num < years):
            """ # 建物存在年次数が経過年次数より少ない """
            code_now = "建物（建て替え）"
        elif(exist_num > years):
            """ # 建物存在年次数が経過年次数より多い """
            """ # あり得ないはずだけど念のため """
            print("number of passed year is larger than the building existing year")
            print("something wrong in this check program !!")
            sys.exit(0)
    
    """ # 変遷コード作成 """
    code = f"{code_org} → {code_now}"
    return code


def building_status(df_build, df_status, year, outset):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 必要なフラグを残す """
    """ # 「tatemono_code」はマージのキー """
    df_tmp = df_build[["tatemono_code", f"existing{year}", f"除却フラグ{year}", f"建設有無フラグ{year}"]].copy()

    """ # 存在フラグのマージ """
    df_status = pd.merge(df_status, df_tmp, how = "left", on = ["tatemono_code"])
    
    """ # 変遷フラグの更新 """
    if(year == 2020):
        """ # 2020年時点をベースにする """
        df_status["変遷フラグ"] = df_status["existing2020"].apply(lambda x : "建物" if(x == 1) else "空地")
        df_status = df_status.drop(["existing2019"], axis = 1)
    else:
        """ # 各フラグの出現回数を計算する """
        df_status["num_exist"] = 0
        df_status["num_remove"] = 0
        df_status["num_build"] = 0
        for col in df_status.columns:
            if("existing" in col):
                """ # 存在しないフラグを0に置き換えて足しこむ → 存在する場合「1」なので、これで存在回数になる """
                df_status[col] = df_status[col].replace(2, 0)
                df_status["num_exist"] += df_status[col]
            elif("除却フラグ" in col):
                df_status[col] = df_status[col].replace(np.nan, 0)
                df_status["num_remove"] += df_status[col]
            elif("建設有無フラグ" in col):
                df_status["num_build"] += df_status[col]
            
        """ # フラグの総数を2020年からの経過年次で設定 """
        num = year - 2020 + 1

        """ # 変遷フラグの更新 """
        df_status["変遷フラグ"] = pd.Series(np.vectorize(transition_flag)
                                        (df_status["existing2020"], df_status[f"existing{year}"], 
                                        df_status["num_exist"], df_status["num_build"], num))        
    
    """ # 出力 """
    if(outset["設定値"] == "T"):
        df_status.to_csv(rf"{outset['フォルダ名']}/建物変遷フラグ_{year}.csv", index = False, encoding = "cp932")
            
    return df_status
    