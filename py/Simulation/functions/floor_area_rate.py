import pandas as pd
import functions.reconstruction_model as frc       # 建物除却,建設,用途選択

def calc_floor_area_rate(df_build, dfs_dict, root_out):

    # 読み込み
    building = df_build.copy()
    zone = dfs_dict["Zone"].copy()

    # BaseDataのBuilding.csvを読み込む
    # building = pd.read_csv('BaseData/Building.csv', encoding='cp932')

    # BaseDataのZone.csvを読み込む
    # zone = pd.read_csv('BaseData/Zone.csv', encoding='cp932')

    # buildingにzoneを結合する
    building = pd.merge(building, zone, on='zone_code', how='left')

    # 用途地域をグループに変換
    building['buildgroup'] = building['UseDistrict'].apply(frc.add_buildgroup)

    # SimtartgetFlagが1のものだけ抽出
    building = building[building['SimTargetFlag'] == 1].copy()

    # ConpletionFlag_Storeysが0のものだけ抽出
    building = building[building['ConpletionFlag_Storeys'] == 0].copy()

    # ConpletionFlag_Usageが0のものだけ抽出
    building = building[building['ConpletionFlag_Usage'] == 0].copy()

    # Usageが402,404,411,412,413,414に絞る
    building = building[building['Usage2020'].isin([402,404,411,412,413,414])].copy()

    # 404（商業複合）は402（商業）に統合
    building.loc[building['Usage2020'] == 404, 'Usage2020'] = 402

    # storeysAboveGroundが0のものを削除
    building = building[building['storeysAboveGround2020'] != 0].copy()

    # buildgroup別Usage別に、上下5％を除外
    groups = building.groupby(['buildgroup', 'Usage2020'])
    building = groups.apply(lambda group: 
        # Sort the group by 'storeysAboveGround2020'
        group.sort_values('storeysAboveGround2020')
        # Calculate the 5% and 95% quantiles
        .iloc[int(len(group)*0.05):int(len(group)*0.95)]
    ).reset_index(drop=True)

    # buildingから、buildgroup別Usageの階数割合を計算
    floorAreaRate = building.groupby(['buildgroup', 'Usage2020', 'storeysAboveGround2020'], as_index=False).size().reset_index()
    floorAreaRate['composition_ratio'] = floorAreaRate.groupby(['buildgroup', 'Usage2020'])['size'].transform(lambda x: x / x.sum())

    # buildingroupとUsage別にstoreysAboveGroundを昇順にソート、累積構成比を計算
    floorAreaRate.sort_values(['buildgroup', 'Usage2020', 'storeysAboveGround2020'], inplace=True)
    floorAreaRate['累積確率'] = floorAreaRate.groupby(['buildgroup', 'Usage2020'])['composition_ratio'].cumsum()
    
    # 列名の2020を削除
    floorAreaRate.rename(columns={'Usage2020': 'Usage', 'storeysAboveGround2020' : 'storeysAboveGround'}, inplace=True)

    # 出力
    # floorAreaRate.to_csv(rf"{root_out}/floor_area_rate.csv", index = False, encoding = "cp932")

    return floorAreaRate


