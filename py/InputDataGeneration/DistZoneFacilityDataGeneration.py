import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import nearest_points
import pandas as pd
import random
import pickle

def generate_random_points_in_polygon(polygon, num_points, zone_code):
    points = []
    min_x, min_y, max_x, max_y = polygon.bounds
    while len(points) < num_points:
        random_point = Point([random.uniform(min_x, max_x), random.uniform(min_y, max_y)])
        if polygon.contains(random_point):
            points.append((random_point, zone_code))
    return points

# コントロールファイル
filepaths = {}
with open('Control_Input.txt', 'r') as f:
    lines = f.readlines()  # ファイルから全ての行を読み込む

    # 1行目をinputpathに、2行目をoutputpathに格納
    filepaths["inputpath"] = lines[0].strip()
    filepaths["outputpath"] = lines[1].strip()

# ゾーンポリゴンデータの読み込み
zone = gpd.read_file(filepaths["inputpath"] + "/Zone_Polygon.shp").to_crs('EPSG:6678')

# Facilty_Point.csvデータの読み込みとGeoDataFrameへの変換
df = pd.read_csv(filepaths["inputpath"] + "/Facility_Point.csv", encoding="cp932")
points = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['lon'], df['lat'])).set_crs('EPSG:6668').to_crs('EPSG:6678')

# 保存するためのデータフレームの作成
result_df = pd.DataFrame()
result_df['zone_code'] = zone['zone_code']

column_mapping = {
    1: "Avg_Dist_Zone_to_Library",
    2: "Avg_Dist_Zone_to_Hospital",
    3: "Avg_Dist_Zone_to_Clinic",
    4: "Avg_Dist_Zone_to_ElementarySchool",
    5: "Avg_Dist_Zone_to_MiddleSchool",
    6: "Avg_Dist_Zone_to_PreSchool"
}

# 各ポリゴンに対してランダムな点を生成
random_points_per_polygon = [generate_random_points_in_polygon(polygon, 100, zone_code) 
                            for polygon, zone_code in zip(zone.geometry, zone['zone_code'])]

# random_points_per_polygonをpickleファイルとして保存
with open(filepaths["outputpath"]+'/random_points_per_polygon.pkl', 'wb') as file:
    pickle.dump(random_points_per_polygon, file)

# 各facility_typeごとに処理
for facility_type, column_name in column_mapping.items():
    specific_points = points[points['facility_type'] == facility_type]
    
    distances = []
    for random_point_list in random_points_per_polygon:
        polygon_distances = []
        for random_point, _ in random_point_list:
            nearest_geom = nearest_points(random_point, specific_points.geometry.unary_union)[1]
            distance = random_point.distance(nearest_geom)
            polygon_distances.append(distance)
        distances.append(sum(polygon_distances) / len(polygon_distances))
    
    result_df[column_name] = distances

# CSVとして保存
result_df.to_csv(filepaths["outputpath"]+"/Dist_Zone_Facility.csv", index=False, encoding="cp932")
