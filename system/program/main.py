# -*- coding: utf-8 -*-

import os
import sys

import submodule.output_setting as out
import submodule.read_initial as ri
import simulation as si

def main():
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 出力先フォルダの作成 """
    df_outset = out.output_setting()
    
    """ # settingファイル読み込み """
    df_set = ri.read_setting()
    
    """ # controlファイルの読み込み """
    df_control = ri.read_control()

    """ # 設定値のチェック """
    ri.check_setting(df_set, df_control)
    
    """ # シミュレーション本体へ引き渡し """
    si.location_simulator(df_set, df_control, df_outset)

if(__name__ == "__main__"):
    main()
    print("\nシミュレーションが終了しました。outputフォルダを確認してください。")