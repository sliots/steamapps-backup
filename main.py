import os
import csv
import subprocess


class SteamBackup:
    def __init__(self, steam_library, backup_dir, winrar_path, csv_file):
        self.steam_library = steam_library
        self.backup_dir = backup_dir
        self.winrar_path = winrar_path
        self.csv_file = csv_file
        self.backup_data = self.read_backup_csv()

    def read_backup_csv(self):
        backup_data = {}
        if os.path.exists(self.csv_file):
            with open(self.csv_file, 'r') as file:
                reader = csv.reader(file)
                for row in reader:
                    appid, buildid = row
                    backup_data[appid] = buildid
        return backup_data

    def write_backup_csv(self):
        with open(self.csv_file, 'w', newline='') as file:
            writer = csv.writer(file)
            for appid, buildid in self.backup_data.items():
                writer.writerow([appid, buildid])

    def backup_app(self, appid, installdir, buildid):
        app_dir = os.path.join(self.steam_library, "common", installdir)
        backup_filename = f"[{appid}][{buildid}]{installdir}.rar"
        backup_path = os.path.join(self.backup_dir, backup_filename)

        # 压缩文件
        subprocess.run([self.winrar_path, "a", "-EP1", "-IBCK", "-K", "-M5", "-MCX", "-MD4G", "-OI", "-S", backup_path, app_dir])

        # 更新 backup.csv
        self.backup_data[appid] = buildid
        self.write_backup_csv()

        print(f"App {installdir}:{appid}:{buildid} backed up successfully.")

    def run_backup(self):
        for acf_file in os.listdir(self.steam_library):
            if acf_file.startswith("appmanifest_") and acf_file.endswith(".acf"):
                acf_path = os.path.join(self.steam_library, acf_file)
                with open(acf_path, 'r') as file:
                    content = file.read()
                    appid = content.split('"appid"\t\t"')[1].split('"')[0]
                    installdir = content.split('"installdir"\t\t"')[1].split('"')[0]
                    buildid = content.split('"buildid"\t\t"')[1].split('"')[0]

                    if appid in self.backup_data and self.backup_data[appid] == buildid:
                        print(f"App {installdir}:{appid}:{buildid} already exists.")
                        continue

                    self.backup_app(appid, installdir, buildid)


# 设置参数
steam_library = r"D:\SteamLibrary\steamapps"
backup_dir = os.path.join(steam_library, "backup")
winrar_path = r"C:\Program Files\WinRAR\WinRAR.exe"
csv_file = os.path.join(backup_dir, "backup.csv")

# 创建 SteamBackup 实例并运行备份
steam_backup = SteamBackup(steam_library, backup_dir, winrar_path, csv_file)
steam_backup.run_backup()
