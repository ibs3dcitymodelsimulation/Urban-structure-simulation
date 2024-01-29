import glob
import zipfile
import os


def compression(root_out):

    # root_outに存在するファイルのうち、「階数モデル」「建設モデル」「居住地選択モデル」「incoming」「outgoing」「建物別商業地価」を含むファイルを、それぞれzipに圧縮する
    import glob
    import zipfile
    import os

    # 定義する検索文字列
    search_strings = ["incoming", "outgoing", "階数モデル", "建設モデル", "居住地選択", "建物別商業地価", "building_面積つき", "建物統合確率", "付け値地代", "ACC", "zone"]

    # 圧縮対象ファイルリスト
    target_files = []
    for search_string in search_strings:
        csvs = glob.glob(rf"{root_out}/*{search_string}*.csv")
        pkls = glob.glob(rf"{root_out}/*{search_string}*.pkl")
        file = csvs + pkls
        target_files.append(file)

    # 圧縮するファイルが存在する場合は、zipファイルを作成する
    for i, files in enumerate(target_files):
        if len(files) > 0:
            search_string = search_strings[i]
            with zipfile.ZipFile(rf"{root_out}/{search_string}.zip", "w", compression=zipfile.ZIP_DEFLATED) as new_zip:
                for file in files:
                    new_zip.write(file, arcname=file.split("/")[-1])
            print(f"{search_string}.zipを作成しました。")
            for file in files:
                os.remove(file)
        else:
            pass

def save_as_zip(df, root_out, filename, year):
    csv_path = rf"{root_out}/{filename}{year}.csv"
    zip_path = rf"{root_out}/{filename}.zip"

    # DataFrameをCSVファイルとして保存
    df.to_csv(csv_path, index=False, encoding="cp932")

    # CSVファイルをZIPファイルに追加
    with zipfile.ZipFile(zip_path, "a", compression=zipfile.ZIP_DEFLATED) as new_zip:
        new_zip.write(csv_path, arcname=f"{filename}{year}.csv")

    # CSVファイルを削除
    os.remove(csv_path)


if __name__ == "__main__":
    root_out = r"\\Nas10\都市地域・環境部門\2023_P11172_都市局都市政策課_まちづくりのDXの推進に向けたユースケース開発実証業務（都市構造シミュレーション等）\5000_作業・データ処理\33_シミュレーション結果\20240102_仙台都市機能誘導容積率_sim0101"
    compression(root_out)