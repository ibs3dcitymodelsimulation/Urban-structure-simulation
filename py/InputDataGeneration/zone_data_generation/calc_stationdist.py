import os
import sys

import numpy as np
import pandas as pd
import geopandas as gpd

import random
from shapely.ops import nearest_points
from shapely.geometry import Point


def generate_random_points_in_polygon(polygon, num_points):
    points = []
    min_x, min_y, max_x, max_y = polygon.bounds
    while len(points) < num_points:
        random_point = Point([random.uniform(min_x, max_x), random.uniform(min_y, max_y)])
        if polygon.contains(random_point):
            points.append(random_point)
    return points

def calc_statdist(df_zone, df_poly_org, df_sta, crs_code):
    print("Function : ", sys._getframe().f_code.co_name)

    df_poly = df_poly_org.to_crs(crs_code)
    gdf_sta = gpd.GeoDataFrame(df_sta, geometry=gpd.points_from_xy(df_sta['Lon'], df_sta['Lat']))
    gdf_sta.set_crs(epsg=6668, inplace=True) 
    gdf_sta = gdf_sta.to_crs(epsg=crs_code)  

    ranks = np.sort(df_sta["Station_Flag"].unique())

    for rank in ranks:
        sta = gdf_sta[gdf_sta["Station_Flag"] == rank]
        results = []
        for _, poly_row in df_poly.iterrows():
            random_points = generate_random_points_in_polygon(poly_row['geometry'], 100)
            distances = []
            for point in random_points:
                nearest_geom = nearest_points(point, sta.geometry.unary_union)[1]
                distances.append(point.distance(nearest_geom))
            avg_distance = sum(distances) / len(distances)
            results.append({'zone_code': poly_row['zone_code'], f'rank{rank}_dist': avg_distance})
        
        df_tmp = pd.DataFrame(results)
        df_zone = pd.merge(df_zone, df_tmp, how="left", on="zone_code")

    df_zone = df_zone.rename(columns={"rank1_dist": "Avg_Dist_sta_centre",
                                      "rank2_dist": "Avg_Dist_sta_main",
                                      "rank3_dist": "Avg_Dist_sta_other"})

    return df_zone
