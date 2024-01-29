# -*- coding: utf-8 -*-
"""
Created on Wed Sep 13 11:39:39 2023

@author: ktakahashi
"""

import os
import sys
import time
import pickle

import numpy as np
import pandas as pd

import geopandas as gpd
import statsmodels.api as sm
from scipy.interpolate import griddata
from scipy.spatial import cKDTree
from shapely.ops import nearest_points

import functions.subfunctions as sf

def calculate_estimated_prices(gdf_build, model, df_zone, df_distbuildsta):
    """ # zoneの使う列だけコピーする """
    zone = df_zone[["zone_code", "ACCP_ln_std", "floorAreaRate", "Avg_Dist_sta_centre"]].copy()
    zone["Avg_Dist_sta_centre_ln"] = np.log(zone["Avg_Dist_sta_centre"])
    zone["floorAreaRate_ln"] = np.log(zone["floorAreaRate"])
    """ # 建物データにzoneと距離情報をマージ """
    gdf_build = pd.merge(gdf_build, df_distbuildsta, on = "buildingID", how = "left")
    gdf_build = pd.merge(gdf_build, zone, on = "zone_code", how = "left")
    gdf_build["roadwidth_ln"] = np.log(gdf_build["RoadWidth"]+1)
    
    """ # 説明変数の設定 """
    X = gdf_build[["roadwidth_ln", "ACCP_ln_std", "floorAreaRate_ln", "Avg_Dist_sta_centre_ln"]].copy()
    X["const"] = 1
    X = X[["const", "roadwidth_ln", "ACCP_ln_std", "floorAreaRate_ln", "Avg_Dist_sta_centre_ln"]]
    
    """ # モデルを使って推定 """
    gdf_build["predict_01"] = model.predict(X)
    # print(gdf_build)    
    # sys.exit(0)
    
    return gdf_build

def assign_actual_prices_to_nearest_buildings(land_prices, buildings_org):
    """
    入力:
        land_prices (GeoDataFrame): 地価情報を含むGeoDataFrame。
        buildings (GeoDataFrame): 建物情報を含むGeoDataFrame。
        
    出力:
        'actual_price'列を追加したGeoDataFrame。この列には実績地価が格納される。
        
    この関数は、最も近い建物に実績地価を割り当てます。
    """
    # 最も近い建物に実績地価を割り当てる内部関数
    def assign_nearest_building_price(land_point, buildings, land_prices):
        nearest_geom = nearest_points(land_point, buildings.unary_union)[1]
        nearest_building = buildings.loc[buildings.geometry == nearest_geom]
        nearest_building_id = nearest_building.index[0]
        price = float(land_prices.loc[land_prices.geometry == land_point, 'Price'].values[0])
        buildings.loc[nearest_building_id, 'actual_price'] = price

    """ # コピーして使う """
    buildings = buildings_org.copy()

    # 地価ポイントごとに最も近い建物に実績地価を割り当てる
    for point in land_prices.geometry:
        assign_nearest_building_price(point, buildings, land_prices)
    
    # 実績地価と予測地価の差（残差）を計算する
    buildings['residual'] = buildings['actual_price'].astype("float") - buildings['predict']
    
    return buildings

def assign_actual_prices_to_nearest_buildings_v2(land_prices, buildings_org):
    
    """ # コピーして使う """
    buildings = buildings_org.copy()
    
    """ # buildingに対してcKDTreeを使って空間的indexを作る """
    tree = cKDTree(buildings.geometry.apply(lambda geom:(geom.x, geom.y)).tolist())
    
    """ # Function to find the nearest building given a land point """
    def find_nearest_building(land_point):
        _, nearest_idx = tree.query((land_point.x, land_point.y))
        return buildings.iloc[nearest_idx]

    """ # Apply the function to each land point """
    nearest_buildings = land_prices.geometry.apply(find_nearest_building)

    """ # Merge the data to get the actual prices """
    merged_data = pd.merge(land_prices, nearest_buildings, left_index=True, right_index=True)
    merged_data = merged_data.rename(columns = {"Price":'actual_price'})
    
    """ # ここで、複数の実績地価が割り当てられている """
    """ # ひとまずこれまでの処理に合わせておく """
    merged_data = merged_data.groupby(["buildingID"], as_index = False).last()

    """ # Calculate residuals """
    merged_data['residual'] = np.log(merged_data['actual_price'].astype(float)) - np.log(merged_data['predict'])

    return merged_data

def interpolate_residuals(points_with_residuals):
    """
    入力:
        points_with_residuals (GeoDataFrame): 残差を持つ建物を含むGeoDataFrame。
        
    出力:
        grid_x, grid_y, grid_z (numpy arrays): x, y, z（残差）のグリッドデータ。
        
    この関数は、空間内挿を用いて各地点での残差を推定します。
    """

    # 残差があるポイントの座標と残差を取得する
    x = points_with_residuals['geometry'].x.dropna()
    y = points_with_residuals['geometry'].y.dropna()
    z = points_with_residuals['residual'].dropna()
    
    # グリッドデータを生成して、空間内挿を行う
    grid_x, grid_y = np.mgrid[min(x):max(x):100j, min(y):max(y):100j]
    grid_z = griddata((x, y), z, (grid_x, grid_y), method='linear')
    
    return grid_x, grid_y, grid_z

def apply_interpolated_residuals_to_buildings(grid_x, grid_y, grid_z, buildings):
    """
    入力:
        grid_x, grid_y, grid_z (numpy arrays): x, y, z（残差）のグリッドデータ。
        buildings (GeoDataFrame): 建物情報を含むGeoDataFrame。
        
    出力:
        'interpolated_residual'列を追加したGeoDataFrame。この列には内挿された残差が格納される。
        
    この関数は、内挿された残差を建物に適用します。
    """
    # グリッドの範囲を取得する
    grid_x_min, grid_x_max = grid_x.min(), grid_x.max()
    grid_y_min, grid_y_max = grid_y.min(), grid_y.max()
    
    # 内挿された残差を建物に適用する
    points = np.array(list(zip(grid_x.flatten(), grid_y.flatten())))
    buildings_xy = buildings['geometry'].apply(lambda p: (p.x, p.y)).tolist()
    buildings_xy = np.array(buildings_xy)
    mask = (buildings_xy[:, 0] >= grid_x_min) & (buildings_xy[:, 0] <= grid_x_max) & \
           (buildings_xy[:, 1] >= grid_y_min) & (buildings_xy[:, 1] <= grid_y_max)
    filtered_points = buildings_xy[mask]
    interpolated_residuals = griddata(points, grid_z.flatten(), filtered_points, method='nearest')
    buildings.loc[mask, 'interpolated_residual'] = interpolated_residuals
    
    # 残差が存在しない場合は、最も近い点の残差を使用する
    valid_points = buildings.dropna(subset=['interpolated_residual'])
    valid_points_xy = valid_points['geometry'].apply(lambda p: (p.x, p.y)).tolist()
    valid_points_z = valid_points['interpolated_residual'].values
    tree = cKDTree(valid_points_xy)
    mask_nan = buildings['interpolated_residual'].isna()
    buildings_nan_xy = buildings.loc[mask_nan, 'geometry'].apply(lambda p: (p.x, p.y)).tolist()
    buildings_nan_xy = np.array(buildings_nan_xy)
    distances, indices = tree.query(buildings_nan_xy)
    nearest_residuals = valid_points_z[indices]
    buildings.loc[mask_nan, 'interpolated_residual'] = nearest_residuals
    
    # 残差を上乗せした地価を計算
    buildings["Landprice_Commercial"] = np.exp(np.log(buildings["predict"]) + buildings["interpolated_residual"])
    
    return buildings


def commercial_landprice_model(dfs_dict, df_build_org, dict_prms, year, root_out, stdswitch):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # データを受ける """
    df_zone = dfs_dict["Zone"].copy()
    df_distbuildsta = dfs_dict["Dist_Building_Station"].copy()
    df_build = df_build_org.copy()
    model_path = dict_prms["商業地価モデル"]
    
    """ # ACPP標準化パラメータ """
    accp_meanstd = dfs_dict["ACCP平均標準偏差"]
    # print(accp_meanstd)
    
    """ # ACCP lnを作って """
    df_zone["ACCP_transit_ln"] = np.log(df_zone["ACCP_transit"])
    df_zone["ACCP_car_ln"] = np.log(df_zone["ACCP_car"])
    df_zone["ACCP_ln"] = np.log(df_zone["ACCP_transit"]+df_zone["ACCP_car"])
        
    """ # 標準化する """
    df_zone = sf.standardize(df_zone, accp_meanstd, list(accp_meanstd.index))

    """ # モデルの読み込み """
    with open(model_path, mode = "rb") as f:
        model = pickle.load(f)
    
    """ # 建物データにgeometryを作る """
    geometry = gpd.points_from_xy(df_build["Lon"], df_build["Lat"])
    gdf_build = gpd.GeoDataFrame(df_build, geometry = geometry)
        
    """ # 推定地価計算 """
    gdf_build = calculate_estimated_prices(gdf_build, model, df_zone, df_distbuildsta)
    time2 = time.perf_counter()
    
    """ # 推定地価の標準化を戻す """
    meanstd = dict_prms["商業地価平均標準偏差"]
    gdf_build["predict"] = np.exp(gdf_build["predict_01"] * meanstd.loc["ln_商業地価", "stds"] + meanstd.loc["ln_商業地価", "means"])

    if(stdswitch == True):
        """ # 地価データの読み込み """
        gdf_clp = dict_prms["商業地価データ"]
        
        """ # 実績地価の割り当て """
        # time1 = time.perf_counter()
        # gdf_buildv1 = assign_actual_prices_to_nearest_buildings(gdf_clp, gdf_build)
        # gdf_buildv1.to_csv(rf"{root_out}/実績地価v1.csv", index = False, encoding = "cp932")
        # time2 = time.perf_counter()
        # print("実績地価割り当て : ",time2 - time1)

        # time1 = time.perf_counter()
        gdf_buildv2 = assign_actual_prices_to_nearest_buildings_v2(gdf_clp, gdf_build)
        # gdf_buildv2.to_csv(rf"{root_out}/実績地価v2.csv", index = False, encoding = "cp932")
        gdf_build = pd.merge(gdf_build, gdf_buildv2[["buildingID", "actual_price", "residual"]],
                               how = "left", on = ["buildingID"])
        # gdf_build.to_csv(rf"{root_out}/実績地価v2merged.csv", index = False, encoding = "cp932")
        # time2 = time.perf_counter()
        # print("実績地価割り当て : ",time2 - time1)
        # sys.exit(0)

        
        """ # 残差を空間内挿 """
        # time1 = time.perf_counter()        
        points_with_residuals = gdf_build.dropna(subset=['residual'])
        grid_x, grid_y, grid_z = interpolate_residuals(points_with_residuals)
        # time2 = time.perf_counter()
        # print("残差空間内挿 : ",time2 - time1)

        """ # 内挿した残差を建物に適用 """
        # time1 = time.perf_counter()
        gdf_build = apply_interpolated_residuals_to_buildings(grid_x, grid_y, grid_z, gdf_build)
        # time2 = time.perf_counter()
        # print("残差適用 : ",time2 - time1)
        
        """ # 結果の保存 """
        dfs_dict["商業地価残差"] = gdf_build[["buildingID","interpolated_residual"]].copy()
        # dfs_dict["商業地価残差"].to_csv(rf"{root_out}/Building_LandPriceCommercialResidual.csv", index = False, encoding = "cp932")
        # sys.exit(0)
    else:
        """ # 残差の取得 """
        residual = dfs_dict["商業地価残差"]
        
        """ # 推計地価に残差をのせる """
        gdf_build = pd.merge(gdf_build, residual, on="buildingID", how="left")
        gdf_build["Landprice_Commercial"] = np.exp(np.log(gdf_build["predict"]) + gdf_build["interpolated_residual"])

    if(os.path.exists(r"output_swich")):
        gdf_build.to_csv(rf"{root_out}/{year}_建物別商業地価.csv", index = False, encoding = "cp932")

    
    return gdf_build

